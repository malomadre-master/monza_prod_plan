from datetime import date
from decimal import Decimal

from scheduler.working_calendar import add_working_days, first_working_day_on_or_after, is_working_day


def test_weekend_is_not_working() -> None:
    assert not is_working_day(date(2026, 8, 2))  # Sunday
    assert is_working_day(date(2026, 8, 3))  # Monday


def test_add_working_days_skips_weekend() -> None:
    # Friday + 1 working day = Monday
    assert add_working_days(date(2026, 8, 7), 1) == date(2026, 8, 10)


def test_add_working_days_fraction_lands_on_that_day() -> None:
    monday = date(2026, 8, 3)
    assert add_working_days(monday, Decimal("2")) == date(2026, 8, 5)
    assert add_working_days(monday, Decimal("1.56")) == date(2026, 8, 5)


def test_sunday_aligns_to_monday() -> None:
    assert first_working_day_on_or_after(date(2026, 8, 2)) == date(2026, 8, 3)


def test_holiday_is_not_working() -> None:
    holiday = date(2026, 8, 3)
    assert not is_working_day(holiday, holidays={holiday})
    assert first_working_day_on_or_after(holiday, holidays={holiday}) == date(2026, 8, 4)


def test_extra_work_makes_saturday_working() -> None:
    saturday = date(2026, 8, 8)
    assert not is_working_day(saturday)
    assert is_working_day(saturday, extra_work={saturday})
    assert first_working_day_on_or_after(saturday, extra_work={saturday}) == saturday
