from datetime import date, timedelta


def is_working_day(day: date) -> bool:
    """Mon–Fri. Holidays are applied by the production calendar later."""
    return day.weekday() < 5


def add_working_days(start: date, days: float) -> date:
    """Advance `days` working days (5/2). Fractional remainder is not applied yet."""
    remaining = int(days)
    cursor = start
    while remaining > 0:
        cursor += timedelta(days=1)
        if is_working_day(cursor):
            remaining -= 1
    return cursor
