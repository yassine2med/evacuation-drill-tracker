from datetime import date

import pytest

from drilltrack.cli import main
from drilltrack.drills import DrillError, load, overdue, parse_date, summarize, trend

SAMPLE = "data/drills.csv"


def test_load_sorted_by_date():
    drills = load(SAMPLE)
    assert len(drills) == 8
    assert drills == sorted(drills, key=lambda d: (d.day, d.building))


def test_summary_statistics_for_building_a():
    a = next(s for s in summarize(load(SAMPLE), 300) if s.building == "Building A")
    assert a.count == 3
    assert a.best == 287 and a.worst == 372
    assert a.median == 331
    assert round(a.mean) == 330
    assert a.within_target == 1
    assert a.last_drill == date(2026, 9, 15)


def test_trend_shows_change_since_previous():
    rows = trend(load(SAMPLE), "Building A")
    assert [change for _, change in rows] == [None, -41, -44]


def test_trend_unknown_building():
    with pytest.raises(DrillError):
        trend(load(SAMPLE), "Nowhere")


def test_overdue_lists_only_old_buildings_oldest_first():
    rows = overdue(load(SAMPLE), date(2026, 11, 19), 180)
    assert [r[0] for r in rows] == ["Building C", "Building B"]
    assert rows[0][2] == (date(2026, 11, 19) - date(2025, 6, 20)).days


def test_overdue_boundary_is_strictly_older():
    drills = load(SAMPLE)
    exactly_180 = date(2027, 4, 19)
    assert "Annex" not in [r[0] for r in overdue(drills, exactly_180, 180)]
    assert "Annex" in [r[0] for r in overdue(drills, date(2027, 4, 20), 180)]


def test_bad_date():
    with pytest.raises(DrillError):
        parse_date("19/11/2026")


def test_missing_column(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("date,building\n2026-01-01,A\n")
    with pytest.raises(DrillError, match="missing column"):
        load(f)


def test_bad_number_and_negative_values(tmp_path):
    header = "date,building,drill_type,evac_seconds,headcount,issues\n"
    f = tmp_path / "x.csv"
    f.write_text(header + "2026-01-01,A,fire,fast,10,\n")
    with pytest.raises(DrillError, match="whole numbers"):
        load(f)
    f.write_text(header + "2026-01-01,A,fire,-5,10,\n")
    with pytest.raises(DrillError, match="above 0"):
        load(f)


def test_empty_log_and_missing_file(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text("date,building,drill_type,evac_seconds,headcount,issues\n")
    with pytest.raises(DrillError, match="no drills"):
        load(f)
    with pytest.raises(DrillError):
        load(tmp_path / "missing.csv")


def test_cli_summary_output(capsys):
    assert main(["summary", SAMPLE, "--target", "300"]) == 0
    out = capsys.readouterr().out
    assert "Building A" in out and "1 of 3" in out


def test_cli_overdue_exit_code(capsys):
    assert main(["overdue", SAMPLE, "--today", "2026-11-19"]) == 1
    assert "2 building(s) overdue" in capsys.readouterr().out
    assert main(["overdue", SAMPLE, "--today", "2026-11-19", "--interval-days", "900"]) == 0
