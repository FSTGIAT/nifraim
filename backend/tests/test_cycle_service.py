"""Monthly cycle date math — every scenario from the cycle plan (A–H + edges).

Pure functions only (no DB): `first_cycle_for`, `latest_cycle`, `next_cycle`,
`cycle_period`, `maslaka_first_auto`, `production_source_for_cycle`.
"""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.services.cycle_service import (
    cycle_moment,
    cycle_period,
    first_cycle_for,
    latest_cycle,
    maslaka_first_auto,
    next_cycle,
    production_source_for_cycle,
)

IL = ZoneInfo("Asia/Jerusalem")


def il(y, m, d, h=12, mi=0):
    """Naive UTC (like the DB stores) for an Israel wall-clock time."""
    return datetime(y, m, d, h, mi, tzinfo=IL).astimezone(timezone.utc).replace(tzinfo=None)


def aware(y, m, d, h=12, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=IL)


def test_cycle_moment_is_21st_0600_israel():
    assert cycle_moment(2026, 10) == datetime(2026, 10, 21, 6, 0, tzinfo=IL)


def test_period_is_previous_month_with_year_rollover():
    assert cycle_period(2026, 10) == date(2026, 9, 1)
    assert cycle_period(2027, 1) == date(2026, 12, 1)


def test_scenario_A_signup_19_9_first_cycle_21_10():
    assert first_cycle_for(il(2026, 9, 19)) == (2026, 10)
    # 21/10 downloads September
    assert cycle_period(*first_cycle_for(il(2026, 9, 19))) == date(2026, 9, 1)


def test_first_cycle_is_always_next_month_whatever_the_day():
    assert first_cycle_for(il(2026, 9, 1)) == (2026, 10)
    assert first_cycle_for(il(2026, 9, 21, 5, 59)) == (2026, 10)
    assert first_cycle_for(il(2026, 9, 21, 7)) == (2026, 10)
    assert first_cycle_for(il(2026, 9, 30, 23, 30)) == (2026, 10)


def test_latest_and_next_cycle_around_the_fire_moment():
    assert latest_cycle(aware(2026, 10, 21, 5, 59)) == (2026, 9)
    assert latest_cycle(aware(2026, 10, 21, 6, 0)) == (2026, 10)
    assert next_cycle(aware(2026, 10, 21, 5, 59)) == (2026, 10)
    assert next_cycle(aware(2026, 10, 21, 6, 0)) == (2026, 11)


def test_dec_to_jan_rollover():
    assert next_cycle(aware(2026, 12, 25)) == (2027, 1)
    assert latest_cycle(aware(2027, 1, 5)) == (2026, 12)
    assert first_cycle_for(il(2026, 12, 22)) == (2027, 1)
    # 31/12 23:30 Israel is still December locally (UTC is 21:30)
    assert first_cycle_for(il(2026, 12, 31, 23, 30)) == (2027, 1)


def test_maslaka_cutoff_27th():
    # scenario A: submitted 19/9 (before 27) → 15/10 (September production)
    assert maslaka_first_auto(il(2026, 9, 19)) == date(2026, 10, 15)
    # 26th still before the cutoff
    assert maslaka_first_auto(il(2026, 9, 26)) == date(2026, 10, 15)
    # scenario B: 27th/28th → slips a month
    assert maslaka_first_auto(il(2026, 9, 27)) == date(2026, 11, 15)
    assert maslaka_first_auto(il(2026, 9, 28)) == date(2026, 11, 15)
    # rollover
    assert maslaka_first_auto(il(2026, 12, 30)) == date(2027, 2, 15)
    assert maslaka_first_auto(None) is None


def test_scenario_A_shiyuch_on_time_first_cycle_fully_automatic():
    # signed + שיוך 19/9 → מסלקה Sep production 15/10 → 21/10 Sep נפרעים: match
    first = maslaka_first_auto(il(2026, 9, 19))
    assert cycle_period(*first_cycle_for(il(2026, 9, 19))) == date(2026, 9, 1)
    assert production_source_for_cycle(2026, 10, first) == "maslaka"


def test_scenario_B_late_shiyuch_first_cycle_manual():
    # שיוך submitted 28/9 → מסלקה from 15/11 → 21/10 upload Sep manually
    first = maslaka_first_auto(il(2026, 9, 28))
    assert production_source_for_cycle(2026, 10, first) == "manual"
    assert production_source_for_cycle(2026, 11, first) == "maslaka"


def test_shiyuch_submitted_after_signup_month():
    # signed 19/9 but only submitted שיוך on 5/10 → מסלקה 15/11
    first = maslaka_first_auto(il(2026, 10, 5))
    assert production_source_for_cycle(2026, 10, first) == "manual"
    assert production_source_for_cycle(2026, 11, first) == "maslaka"


def test_scenario_E_no_shiyuch_always_manual():
    assert production_source_for_cycle(2027, 6, None) == "manual"


def test_scenario_H_old_user_already_past_first_cycle():
    assert cycle_moment(*first_cycle_for(il(2025, 3, 1))) < aware(2026, 9, 28)
