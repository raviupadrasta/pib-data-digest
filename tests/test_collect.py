import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from pib_digest.collect import collect, days_to_cover, yesterday_ist
from pib_digest.http import FetchError
from pib_digest.listing import ListingItem
from pib_digest.release import Release

DAY = date(2026, 11, 19)
FIN = "Ministry of Finance"
MOSPI = "Ministry of Statistics & Programme Implementation"
HEALTH = "Ministry of Health and Family Welfare"


def item(prid: int, ministry: str) -> ListingItem:
    return ListingItem(prid, f"title {prid}", f"https://x/{prid}", ministry)


def release_of(it: ListingItem, posted: date | None = DAY) -> Release:
    return Release(it.prid, it.title, it.ministry, it.url, posted, f"text {it.prid}")


class CollectTest(unittest.TestCase):
    def run_collect(self, items, ministries=(FIN, MOSPI), fetch_rel=None):
        return collect(list(ministries), DAY, lambda day: items, fetch_rel or release_of)

    def test_collect_keeps_only_chosen_ministries(self):
        c = self.run_collect([item(1, FIN), item(2, HEALTH), item(3, MOSPI)])
        self.assertEqual([r.prid for r in c.releases], [1, 3])

    def test_collect_dedups_same_prid_listed_twice(self):
        c = self.run_collect([item(1, FIN), item(1, MOSPI)])
        self.assertEqual([r.prid for r in c.releases], [1])

    def test_collect_matches_names_ignoring_case_and_spacing(self):
        c = self.run_collect([item(1, FIN)], ministries=["  ministry  of FINANCE "])
        self.assertEqual([r.prid for r in c.releases], [1])

    def test_collect_empty_listing_warns(self):
        c = self.run_collect([])
        self.assertEqual(c.releases, [])
        self.assertEqual(len(c.warnings), 1)
        self.assertIn("no releases", c.warnings[0])

    def test_collect_non_empty_listing_without_chosen_ministry_has_no_warning(self):
        c = self.run_collect([item(2, HEALTH)])
        self.assertEqual((c.releases, c.warnings), ([], []))

    def test_collect_release_failure_listed_and_others_continue(self):
        def fetch_rel(it):
            if it.prid == 1:
                raise FetchError("boom")
            return release_of(it)

        c = self.run_collect([item(1, FIN), item(3, MOSPI)], fetch_rel=fetch_rel)
        self.assertEqual([r.prid for r in c.releases], [3])
        self.assertEqual(len(c.failures), 1)
        self.assertIn("1", c.failures[0])

    def test_collect_drops_release_dated_other_day(self):
        c = self.run_collect([item(1, FIN)], fetch_rel=lambda it: release_of(it, date(2026, 11, 10)))
        self.assertEqual(c.releases, [])

    def test_collect_keeps_release_without_date(self):
        c = self.run_collect([item(1, FIN)], fetch_rel=lambda it: release_of(it, None))
        self.assertEqual([r.prid for r in c.releases], [1])

    def test_collect_listing_failure_raises(self):
        def bad_listing(day):
            raise FetchError("down")

        with self.assertRaises(FetchError):
            collect([FIN], DAY, bad_listing, release_of)


class YesterdayTest(unittest.TestCase):
    def test_yesterday_ist_at_0430_utc_is_previous_ist_day(self):
        now = datetime(2026, 11, 20, 4, 30, tzinfo=timezone.utc)  # 10:00 IST
        self.assertEqual(yesterday_ist(now), date(2026, 11, 19))

    def test_yesterday_ist_late_utc_evening_rolls_forward(self):
        now = datetime(2026, 11, 19, 20, 0, tzinfo=timezone.utc)  # 01:30 IST on the 20th
        self.assertEqual(yesterday_ist(now), date(2026, 11, 19))


class DaysToCoverTest(unittest.TestCase):
    def folder(self, *names: str) -> Path:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: [p.unlink() for p in d.iterdir()] or d.rmdir())
        for n in names:
            (d / n).write_text("x", encoding="utf-8")
        return d

    def test_days_to_cover_monday_gives_fri_sat_sun(self):
        d = self.folder("2026-11-12.md")  # Thursday
        self.assertEqual(
            days_to_cover(d, date(2026, 11, 15)),  # Sunday
            [date(2026, 11, 13), date(2026, 11, 14), date(2026, 11, 15)],
        )

    def test_days_to_cover_empty_folder_gives_yesterday(self):
        self.assertEqual(days_to_cover(self.folder(), date(2026, 11, 19)), [date(2026, 11, 19)])

    def test_days_to_cover_missing_folder_gives_yesterday(self):
        self.assertEqual(days_to_cover(Path("/nonexistent/digests"), date(2026, 11, 19)), [date(2026, 11, 19)])

    def test_days_to_cover_up_to_date_gives_empty(self):
        self.assertEqual(days_to_cover(self.folder("2026-11-19.md"), date(2026, 11, 19)), [])

    def test_days_to_cover_caps_at_seven_days(self):
        days = days_to_cover(self.folder("2026-10-01.md"), date(2026, 11, 19))
        self.assertEqual(len(days), 7)
        self.assertEqual(days[-1], date(2026, 11, 19))
        self.assertEqual(days[0], date(2026, 11, 13))

    def test_days_to_cover_ignores_raw_and_other_files(self):
        d = self.folder("2026-11-18.md", "2026-11-19.raw.txt", "notes.md")
        self.assertEqual(days_to_cover(d, date(2026, 11, 19)), [date(2026, 11, 19)])


if __name__ == "__main__":
    unittest.main()
