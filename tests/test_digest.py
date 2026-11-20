import tempfile
import unittest
from datetime import date
from pathlib import Path

from pib_digest.digest import render_digest, write_digest
from pib_digest.release import Release
from pib_digest.summarize import CheckedEntry, Entry

DAY = date(2026, 11, 19)
RELEASE = Release(
    101, "CPI for October 2026", "Ministry of Statistics & Programme Implementation",
    "https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=101", DAY, "text",
)
ENTRY = Entry(101, "CPI inflation 5.5% in October", "5.1% in September", "Inflation edged up.", "India CPI: 5.5% in Oct.")


class RenderDigestTest(unittest.TestCase):
    def test_render_lists_headline_previous_takeaway_link_tweet(self):
        text = render_digest(DAY, [(CheckedEntry(ENTRY, []), RELEASE)], [], [])
        for expected in (
            "2026-11-19",
            "CPI inflation 5.5% in October",
            "5.1% in September",
            "Inflation edged up.",
            "https://www.pib.gov.in/PressReleaseDetail.aspx?PRID=101",
            "India CPI: 5.5% in Oct.",
            "Ministry of Statistics & Programme Implementation",
        ):
            self.assertIn(expected, text)
        self.assertNotIn("CHECK", text)

    def test_render_marks_unverified_numbers_with_warning(self):
        text = render_digest(DAY, [(CheckedEntry(ENTRY, ["6.9"]), RELEASE)], [], [])
        self.assertIn("CHECK", text)
        self.assertIn("6.9", text)

    def test_render_omits_previous_line_when_none(self):
        entry = Entry(101, "h", None, "t", "tw")
        text = render_digest(DAY, [(CheckedEntry(entry, []), RELEASE)], [], [])
        self.assertNotIn("Previous", text)

    def test_render_empty_day_says_no_data_releases(self):
        self.assertIn("No data releases", render_digest(DAY, [], [], []))

    def test_render_lists_warnings_and_failures(self):
        text = render_digest(DAY, [], ["listing empty"], ["PRID 7: boom"])
        self.assertIn("listing empty", text)
        self.assertIn("PRID 7: boom", text)


class WriteDigestTest(unittest.TestCase):
    def test_write_digest_same_input_same_file(self):
        with tempfile.TemporaryDirectory() as d:
            text = render_digest(DAY, [(CheckedEntry(ENTRY, []), RELEASE)], [], [])
            first = write_digest(DAY, text, Path(d) / "out").read_bytes()
            path = write_digest(DAY, text, Path(d) / "out")
            self.assertEqual(path.name, "2026-11-19.md")
            self.assertEqual(path.read_bytes(), first)


if __name__ == "__main__":
    unittest.main()
