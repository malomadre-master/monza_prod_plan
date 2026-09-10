from datetime import date, timedelta
from decimal import Decimal

ZERO = Decimal("0")
ONE = Decimal("1")


def is_working_day(day: date, holidays: set[date] | None = None) -> bool:
    """Mon–Fri, minus explicit holidays."""
    if day.weekday() >= 5:
        return False
    if holidays and day in holidays:
        return False
    return True


def first_working_day_on_or_after(day: date, holidays: set[date] | None = None) -> date:
    cursor = day
    while not is_working_day(cursor, holidays):
        cursor += timedelta(days=1)
    return cursor


def next_working_day(day: date, holidays: set[date] | None = None) -> date:
    return first_working_day_on_or_after(day + timedelta(days=1), holidays)


def add_working_days(start: date, days: float | Decimal, holidays: set[date] | None = None) -> date:
    """Advance `days` working days after `start` (start itself is not consumed).

    Friday + 1 working day = Monday. Fractional leftover still lands on that working day.
    """
    remaining = Decimal(str(days)) if not isinstance(days, Decimal) else days
    if remaining <= ZERO:
        return first_working_day_on_or_after(start, holidays)
    cursor = start
    while remaining > ZERO:
        cursor += timedelta(days=1)
        if is_working_day(cursor, holidays):
            remaining -= ONE
    return cursor
