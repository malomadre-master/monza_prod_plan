from collections import defaultdict
from collections.abc import Callable
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from scheduler.models import (
    DEFAULT_CENTERS,
    SHOP_ROUTE,
    CenterSpec,
    ConstructorSpec,
    Job,
    Slot,
)
from scheduler.working_calendar import first_working_day_on_or_after, next_working_day

ZERO = Decimal("0")
ONE = Decimal("1")
TWO_PLACES = Decimal("0.01")
MAX_SCAN_DAYS = 366 * 3

DayFactor = Callable[[date], Decimal]


def daily_capacity(qty: Decimal, days: Decimal) -> Decimal:
    if days <= ZERO:
        raise ValueError("capacity_days must be > 0")
    return qty / days


def duration_days(volume: Decimal, qty: Decimal, days: Decimal) -> Decimal:
    """Exact working-day duration. Display rounding is separate."""
    return volume / daily_capacity(qty, days)


def display_days(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def person_day_factor(person_id: int, absences: dict[int, set[date]] | None) -> DayFactor:
    missing = absences.get(person_id, set()) if absences else set()

    def factor(day: date) -> Decimal:
        return ZERO if day in missing else ONE

    return factor


def staff_day_factor(staff: list[tuple[int, Decimal]], absences: dict[int, set[date]] | None) -> DayFactor:
    """Present weight / assigned weight. No staff → full capacity every day."""
    if not staff:
        return lambda _day: ONE
    total = sum((efficiency for _uid, efficiency in staff), ZERO)
    if total <= ZERO:
        return lambda _day: ONE
    missing = absences or {}

    def factor(day: date) -> Decimal:
        present = sum((efficiency for uid, efficiency in staff if day not in missing.get(uid, set())), ZERO)
        return present / total

    return factor


class _Load:
    def __init__(self, daily: Decimal, factor: DayFactor | None = None):
        self.daily = daily
        self.factor = factor or (lambda _day: ONE)
        self.used: dict[date, Decimal] = defaultdict(lambda: ZERO)

    def allocate(
        self,
        volume: Decimal,
        earliest: date,
        holidays: set[date] | None = None,
        extra_work: set[date] | None = None,
    ) -> tuple[date, date]:
        if volume <= ZERO:
            day = first_working_day_on_or_after(earliest, holidays, extra_work)
            return day, day
        remaining = volume
        day = first_working_day_on_or_after(earliest, holidays, extra_work)
        start: date | None = None
        last = day
        scanned = 0
        while remaining > ZERO:
            scanned += 1
            if scanned > MAX_SCAN_DAYS:
                raise ValueError("no capacity in the planning horizon")
            free = (self.daily * self.factor(day)) - self.used[day]
            if free <= ZERO:
                day = next_working_day(day, holidays, extra_work)
                continue
            take = remaining if remaining <= free else free
            self.used[day] += take
            if start is None:
                start = day
            last = day
            remaining -= take
            if remaining > ZERO:
                day = next_working_day(day, holidays, extra_work)
        assert start is not None
        return start, last


def _volume(job: Job, unit: str) -> Decimal:
    if unit == "item":
        return Decimal(job.qty)
    if unit == "m2":
        return job.area_m2
    if unit == "linear_m":
        return job.linear_m
    if unit == "order":
        return Decimal("1")
    raise ValueError(f"unknown unit {unit}")


def _centers_by_code(centers: tuple[CenterSpec, ...] | list[CenterSpec]) -> dict[str, CenterSpec]:
    return {row.code: row for row in centers}


def plan_jobs(
    jobs: list[Job],
    *,
    constructors: list[ConstructorSpec] | None = None,
    centers: tuple[CenterSpec, ...] | list[CenterSpec] | None = None,
    holidays: set[date] | None = None,
    extra_work: set[date] | None = None,
    absences: dict[int, set[date]] | None = None,
    center_staff: dict[str, list[tuple[int, Decimal]]] | None = None,
) -> list[Slot]:
    """Finite-capacity plan. Construction is per order; shop steps are per item."""
    if not jobs:
        return []
    specs = _centers_by_code(centers or DEFAULT_CENTERS)
    pool = constructors or [ConstructorSpec(id=1)]
    construction = specs["construction"]
    complectation = specs["complectation"]
    staff = center_staff or {}
    shop_loads = {
        code: _Load(
            daily_capacity(specs[code].capacity_qty, specs[code].capacity_days),
            staff_day_factor(staff.get(code, []), absences),
        )
        for code in SHOP_ROUTE
    }
    complect_load = _Load(
        daily_capacity(complectation.capacity_qty, complectation.capacity_days),
        staff_day_factor(staff.get("complectation", []), absences),
    )
    constructor_loads = {
        person.id: _Load(
            daily_capacity(construction.capacity_qty, construction.capacity_days) * person.efficiency,
            person_day_factor(person.id, absences),
        )
        for person in pool
    }

    ordered = sorted(
        jobs,
        key=lambda job: (job.order_priority, job.item_priority, job.launch_date, job.contract_date, job.item_id),
    )
    slots: list[Slot] = []
    construction_done: dict[int, date] = {}
    complect_done: dict[int, date] = {}

    orders: dict[int, list[Job]] = defaultdict(list)
    for job in ordered:
        orders[job.order_id].append(job)

    seen_order: set[int] = set()
    for job in ordered:
        if job.order_id in seen_order:
            continue
        seen_order.add(job.order_id)
        siblings = orders[job.order_id]
        volume = sum((Decimal(row.qty) for row in siblings), ZERO)
        earliest = first_working_day_on_or_after(job.launch_date, holidays, extra_work)
        person_id, start, finish = _assign_constructor(
            constructor_loads, volume, earliest, holidays, extra_work
        )
        _ = person_id
        construction_done[job.order_id] = finish
        for row in siblings:
            slots.append(
                Slot(job.order_id, row.item_id, "construction", Decimal(row.qty), start, finish)
            )

        if any(row.procurement_needed for row in siblings):
            c_start, c_finish = complect_load.allocate(Decimal("1"), finish, holidays, extra_work)
            complect_done[job.order_id] = c_finish
            for row in siblings:
                if row.procurement_needed:
                    slots.append(Slot(job.order_id, row.item_id, "complectation", Decimal("1"), c_start, c_finish))

    for job in ordered:
        ready = construction_done[job.order_id]
        if job.procurement_needed and job.order_id in complect_done:
            ready = max(ready, complect_done[job.order_id])
        cursor = ready
        for code in SHOP_ROUTE:
            spec = specs[code]
            volume = _volume(job, spec.unit)
            start, finish = shop_loads[code].allocate(volume, cursor, holidays, extra_work)
            slots.append(Slot(job.order_id, job.item_id, code, volume, start, finish))
            cursor = finish
    return slots


def _assign_constructor(
    loads: dict[int, _Load],
    volume: Decimal,
    earliest: date,
    holidays: set[date] | None,
    extra_work: set[date] | None,
) -> tuple[int, date, date]:
    best: tuple[date, int, date, date] | None = None
    for person_id, load in loads.items():
        snapshot = dict(load.used)
        start, finish = load.allocate(volume, earliest, holidays, extra_work)
        load.used.clear()
        load.used.update(snapshot)
        candidate = (finish, person_id, start, finish)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    assert best is not None
    _, person_id, start, finish = best
    start, finish = loads[person_id].allocate(volume, earliest, holidays, extra_work)
    return person_id, start, finish
