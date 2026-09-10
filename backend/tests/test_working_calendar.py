from datetime import date

from scheduler.working_calendar import add_working_days, is_working_day


def test_weekend_is_not_working() -> None:
    assert not is_working_day(date(2026, 8, 2))  # Sunday
    assert is_working_day(date(2026, 8, 3))  # Monday


def test_add_working_days_skips_weekend() -> None:
    # Friday + 1 working day = Monday
    assert add_working_days(date(2026, 8, 7), 1) == date(2026, 8, 10)
