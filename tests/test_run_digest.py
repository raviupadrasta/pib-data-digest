import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import run_digest
from pib_digest.collect import Collected
from pib_digest.http import FetchError
from pib_digest.release import Release
from pib_digest.summarize import CheckedEntry, Entry, SummaryError


def release_for(day: date) -> Release:
    return Release(1, "t", "Ministry of Finance", "https://x/1", day, "GST was 100 crore")


def good_collect(ministries, day):
    return Collected(releases=[release_for(day)])


def good_summarize(releases, template):
    return [CheckedEntry(Entry(1, "GST 100 crore", None, "k", "tw 100"), []) for _ in releases[:1]]


class MainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        quiet = mock.patch("builtins.print")  # main() reports progress with print
        quiet.start()
        self.addCleanup(quiet.stop)

    def names(self) -> list[str]:
        return sorted(p.name for p in self.out.iterdir())

    def run_main(self, *extra, collect=good_collect, summ=good_summarize, yesterday=date(2026, 11, 15)):
        with mock.patch.object(run_digest, "collect", collect), \
             mock.patch.object(run_digest, "summarize", summ), \
             mock.patch.object(run_digest, "yesterday_ist", lambda: yesterday):
            return run_digest.main(["--out-dir", str(self.out), *extra])

    def test_main_end_to_end_with_fakes(self):
        self.assertEqual(self.run_main("--date", "2026-11-19"), 0)
        self.assertEqual(self.names(), ["2026-11-19.md"])
        self.assertIn("GST 100 crore", (self.out / "2026-11-19.md").read_text(encoding="utf-8"))

    def test_main_catch_up_writes_one_file_per_day(self):
        (self.out / "2026-11-12.md").write_text("old", encoding="utf-8")  # Thursday
        self.assertEqual(self.run_main(), 0)  # yesterday is Sunday the 15th
        self.assertEqual(self.names(), ["2026-11-12.md", "2026-11-13.md", "2026-11-14.md", "2026-11-15.md"])

    def test_main_up_to_date_does_nothing(self):
        (self.out / "2026-11-15.md").write_text("old", encoding="utf-8")
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(self.names(), ["2026-11-15.md"])

    def test_main_invalid_claude_reply_saves_raw_and_returns_nonzero(self):
        def bad_summarize(releases, template):
            raise SummaryError("not json", "Sorry, no")

        self.assertEqual(self.run_main("--date", "2026-11-19", summ=bad_summarize), 1)
        self.assertEqual(self.names(), ["2026-11-19.raw.txt"])
        self.assertEqual((self.out / "2026-11-19.raw.txt").read_text(encoding="utf-8"), "Sorry, no")

    def test_main_listing_failure_writes_no_file_and_returns_nonzero(self):
        def bad_collect(ministries, day):
            raise FetchError("down")

        self.assertEqual(self.run_main("--date", "2026-11-19", collect=bad_collect), 1)
        self.assertEqual(self.names(), [])

    def test_main_failure_on_second_day_keeps_first_file_and_writes_no_later_file(self):
        (self.out / "2026-11-12.md").write_text("old", encoding="utf-8")

        def collect(ministries, day):
            if day == date(2026, 11, 14):
                raise FetchError("down")
            return good_collect(ministries, day)

        self.assertEqual(self.run_main(collect=collect), 1)
        self.assertEqual(self.names(), ["2026-11-12.md", "2026-11-13.md"])

    def test_main_rerun_same_date_gives_same_file(self):
        self.run_main("--date", "2026-11-19")
        first = (self.out / "2026-11-19.md").read_bytes()
        self.run_main("--date", "2026-11-19")
        self.assertEqual((self.out / "2026-11-19.md").read_bytes(), first)


if __name__ == "__main__":
    unittest.main()
