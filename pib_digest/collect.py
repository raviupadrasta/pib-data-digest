"""Gather one day's releases from the chosen ministries, and pick the days to cover."""
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from pib_digest.http import FetchError
from pib_digest.listing import ListingItem, fetch_listing
from pib_digest.release import Release, fetch_release

IST = timezone(timedelta(hours=5, minutes=30))  # India has no daylight saving
_DIGEST_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")


@dataclass
class Collected:
    releases: list[Release] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().lower()


def collect(
    ministries: list[str],
    day: date,
    fetch_list: Callable[[date], list[ListingItem]] = fetch_listing,
    fetch_rel: Callable[[ListingItem], Release] = fetch_release,
) -> Collected:
    """A failed listing fetch raises FetchError: the day must stay undone so the next run retries it."""
    listing = fetch_list(day)
    result = Collected()
    if not listing:
        result.warnings.append(
            f"PIB listing for {day} has no releases (holiday, or PIB changed the page): check by hand."
        )
        return result
    wanted = {_norm(m) for m in ministries}
    seen: set[int] = set()
    for it in listing:
        if _norm(it.ministry) not in wanted or it.prid in seen:
            continue
        seen.add(it.prid)
        try:
            release = fetch_rel(it)
        except FetchError as exc:
            result.failures.append(f"PRID {it.prid} ({it.ministry}): {exc}")
            continue
        if release.posted is None or release.posted == day:
            result.releases.append(release)
    return result


def yesterday_ist(now: datetime | None = None) -> date:
    now = now or datetime.now(timezone.utc)
    return now.astimezone(IST).date() - timedelta(days=1)


def days_to_cover(out_dir: Path, yesterday: date, cap: int = 7) -> list[date]:
    latest: date | None = None
    if out_dir.is_dir():
        for path in out_dir.iterdir():
            match = _DIGEST_NAME.match(path.name)
            if match:
                found = date.fromisoformat(match.group(1))
                latest = found if latest is None or found > latest else latest
    start = yesterday if latest is None else latest + timedelta(days=1)
    span = (yesterday - start).days + 1
    if span <= 0:
        return []
    span = min(span, cap)
    return [yesterday - timedelta(days=n) for n in range(span - 1, -1, -1)]
