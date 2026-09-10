from datetime import date
from decimal import Decimal

from scheduler.engine import display_days, duration_days, plan_jobs
from scheduler.models import ConstructorSpec, Job


def _job(**kwargs) -> Job:
    base = dict(
        order_id=1,
        item_id=1,
        order_priority=1,
        item_priority=1,
        launch_date=date(2026, 8, 3),
        contract_date=date(2026, 8, 1),
        qty=1,
        area_m2=Decimal("12.5"),
        linear_m=Decimal("125"),
        procurement_needed=True,
    )
    base.update(kwargs)
    return Job(**base)


def test_excel_durations() -> None:
    """Excel volumes / daily power. Display uses half-up; Excel ROUNDDOWN gave 2.23 for 179/80."""
    assert display_days(duration_days(Decimal("2.7"), Decimal("1"), Decimal("2"))) == Decimal("5.40")
    assert display_days(duration_days(Decimal("1"), Decimal("1"), Decimal("2"))) == Decimal("2.00")
    assert display_days(duration_days(Decimal("200"), Decimal("100"), Decimal("1"))) == Decimal("2.00")
    assert display_days(duration_days(Decimal("780"), Decimal("500"), Decimal("1"))) == Decimal("1.56")
    assert display_days(duration_days(Decimal("209"), Decimal("140"), Decimal("1"))) == Decimal("1.49")
    assert display_days(duration_days(Decimal("25"), Decimal("30"), Decimal("1"))) == Decimal("0.83")
    assert display_days(duration_days(Decimal("5"), Decimal("4"), Decimal("1"))) == Decimal("1.25")
    assert duration_days(Decimal("179"), Decimal("80"), Decimal("1")) == Decimal("179") / Decimal("80")


def test_construction_two_working_days_from_monday() -> None:
    slots = plan_jobs([_job(procurement_needed=False)], constructors=[ConstructorSpec(id=1)])
    construction = next(row for row in slots if row.center_code == "construction")
    assert construction.start == date(2026, 8, 3)
    assert construction.finish == date(2026, 8, 4)
    assert all(row.center_code != "complectation" for row in slots)


def test_complectation_is_one_order_slot_for_two_items() -> None:
    jobs = [
        _job(item_id=1, item_priority=1, area_m2=Decimal("10"), linear_m=Decimal("100")),
        _job(item_id=2, item_priority=2, area_m2=Decimal("10"), linear_m=Decimal("100")),
    ]
    slots = plan_jobs(jobs, constructors=[ConstructorSpec(id=1)])
    gates = [row for row in slots if row.center_code == "complectation"]
    assert len(gates) == 2
    assert gates[0].start == gates[1].start
    assert gates[0].finish == gates[1].finish


def test_second_item_waits_for_saw_capacity() -> None:
    jobs = [
        _job(order_id=1, item_id=1, area_m2=Decimal("100"), linear_m=Decimal("1000"), procurement_needed=False),
        _job(order_id=2, item_id=2, order_priority=2, area_m2=Decimal("100"), linear_m=Decimal("1000"), procurement_needed=False),
    ]
    slots = plan_jobs(jobs, constructors=[ConstructorSpec(id=1), ConstructorSpec(id=2)])
    saw = sorted((row for row in slots if row.center_code == "saw"), key=lambda row: row.item_id)
    assert saw[0].start == saw[0].finish
    assert saw[1].start > saw[0].finish


def test_constructor_wip_second_order_waits() -> None:
    jobs = [
        _job(order_id=1, item_id=1, procurement_needed=False),
        _job(order_id=2, item_id=2, order_priority=2, procurement_needed=False),
    ]
    slots = plan_jobs(jobs, constructors=[ConstructorSpec(id=1)])
    cons = {row.order_id: row for row in slots if row.center_code == "construction"}
    assert cons[1].finish < cons[2].start


def test_higher_kpd_finishes_earlier() -> None:
    slow = plan_jobs([_job()], constructors=[ConstructorSpec(id=1, efficiency=Decimal("0.5"))])
    fast = plan_jobs([_job()], constructors=[ConstructorSpec(id=1, efficiency=Decimal("1"))])
    slow_c = next(row for row in slow if row.center_code == "construction")
    fast_c = next(row for row in fast if row.center_code == "construction")
    assert fast_c.finish < slow_c.finish


def test_priority_order_goes_first() -> None:
    jobs = [
        _job(order_id=2, item_id=2, order_priority=3, procurement_needed=False),
        _job(order_id=1, item_id=1, order_priority=1, procurement_needed=False),
    ]
    slots = plan_jobs(jobs, constructors=[ConstructorSpec(id=1)])
    cons = {row.order_id: row for row in slots if row.center_code == "construction"}
    assert cons[1].start <= cons[2].start
    assert cons[1].finish <= cons[2].start
