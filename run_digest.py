"""Write the PIB data digest for the days since the last digest (default) or for one day."""
import argparse
from datetime import date
from pathlib import Path

from pib_digest.collect import collect, days_to_cover, yesterday_ist
from pib_digest.digest import render_digest, write_digest
from pib_digest.http import FetchError
from pib_digest.listing import load_ministries
from pib_digest.summarize import SummaryError, summarize

ROOT = Path(__file__).resolve().parent  # paths do not depend on where a scheduler starts the script


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, help="one day, YYYY-MM-DD")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "digests")
    args = parser.parse_args(argv)

    days = [args.date] if args.date else days_to_cover(args.out_dir, yesterday_ist())
    if not days:
        print("Digests are up to date.")
        return 0
    ministries = load_ministries(ROOT / "ministries.json")
    template = (ROOT / "prompt.md").read_text(encoding="utf-8")

    for day in days:
        try:
            collected = collect(ministries, day)
            checked = summarize(collected.releases, template)
        except FetchError as exc:
            print(f"{day}: could not read PIB: {exc}")  # no file, so the next run retries this day
            return 1
        except SummaryError as exc:
            print(f"{day}: summary failed: {exc}")
            if exc.raw:
                args.out_dir.mkdir(parents=True, exist_ok=True)
                (args.out_dir / f"{day.isoformat()}.raw.txt").write_text(exc.raw, encoding="utf-8")
            return 1
        by_prid = {r.prid: r for r in collected.releases}
        entries = [(c, by_prid[c.entry.prid]) for c in checked]
        text = render_digest(day, entries, collected.warnings, collected.failures)
        print(write_digest(day, text, args.out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
