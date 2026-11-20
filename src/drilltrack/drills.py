"""Read a drill log (CSV) and compute timing statistics and overdue buildings."""
from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

COLUMNS = ("date", "building", "drill_type", "evac_seconds", "headcount", "issues")


class DrillError(ValueError):
    """Raised when the drill log cannot be used."""


@dataclass(frozen=True)
class Drill:
    """One evacuation drill."""

    day: date
    building: str
    drill_type: str
    seconds: int
    headcount: int
    issues: str


@dataclass(frozen=True)
class Summary:
    """Timing statistics for one building."""

    building: str
    count: int
    mean: float
    median: float
    best: int
    worst: int
    within_target: int
    last_drill: date


def parse_date(text: str) -> date:
    """Parse YYYY-MM-DD."""
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise DrillError(f"bad date '{text}', use YYYY-MM-DD") from exc


def load(path: str | Path) -> list[Drill]:
    """Read the CSV log. Rows are returned sorted by date."""
    try:
        handle = open(path, newline="", encoding="utf-8")
    except OSError as exc:
        raise DrillError(f"cannot read {path}: {exc}") from exc
    with handle:
        reader = csv.DictReader(handle)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise DrillError(f"missing column(s): {', '.join(missing)}")
        drills = []
        for number, row in enumerate(reader, start=2):
            try:
                seconds = int(row["evac_seconds"])
                headcount = int(row["headcount"])
            except ValueError as exc:
                raise DrillError(f"line {number}: seconds and headcount must be whole numbers") from exc
            if seconds <= 0 or headcount < 0:
                raise DrillError(f"line {number}: seconds must be above 0 and headcount not negative")
            if not row["building"].strip():
                raise DrillError(f"line {number}: building is empty")
            drills.append(Drill(parse_date(row["date"]), row["building"].strip(),
                                row["drill_type"].strip(), seconds, headcount, row["issues"].strip()))
    if not drills:
        raise DrillError("the log has no drills")
    return sorted(drills, key=lambda d: (d.day, d.building))


def summarize(drills: list[Drill], target: int) -> list[Summary]:
    """One Summary per building, sorted by building name."""
    result = []
    for building in sorted({d.building for d in drills}):
        rows = [d for d in drills if d.building == building]
        times = [d.seconds for d in rows]
        result.append(Summary(building, len(rows), statistics.mean(times), statistics.median(times),
                              min(times), max(times), sum(t <= target for t in times),
                              max(d.day for d in rows)))
    return result


def trend(drills: list[Drill], building: str) -> list[tuple[Drill, int | None]]:
    """Drills of one building with the change in seconds since the previous drill."""
    rows = [d for d in drills if d.building == building]
    if not rows:
        raise DrillError(f"no drills for building '{building}'")
    return [(d, None if i == 0 else d.seconds - rows[i - 1].seconds) for i, d in enumerate(rows)]


def overdue(drills: list[Drill], today: date, interval_days: int) -> list[tuple[str, date, int]]:
    """Buildings whose last drill is older than the interval: (building, last drill, days since)."""
    limit = timedelta(days=interval_days)
    result = []
    for s in summarize(drills, 0):
        age = today - s.last_drill
        if age > limit:
            result.append((s.building, s.last_drill, age.days))
    return sorted(result, key=lambda row: -row[2])
