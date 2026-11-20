import re
import unittest
from datetime import date
from pathlib import Path

from pib_digest.listing import ListingItem
from pib_digest.release import fetch_release, parse_release

FIXTURE = (Path(__file__).parent / "fixtures" / "release.html").read_text(encoding="utf-8")
ITEM = ListingItem(
    prid=2338313,
    title="Union Health Ministry Proposes Amendment to Drugs Rules, 1945",
    url="https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=2338313",
    ministry="Ministry of Health and Family Welfare",
)


class ParseReleaseTest(unittest.TestCase):
    def test_parse_release_reads_posted_date(self):
        self.assertEqual(parse_release(FIXTURE, ITEM).posted, date(2026, 11, 19))

    def test_parse_release_text_has_body_not_markup(self):
        text = parse_release(FIXTURE, ITEM).text
        self.assertIn("has proposed an amendment to the Drugs Rules, 1945", text)
        self.assertNotIn("<div", text)
        self.assertNotIn("<p", text)

    def test_parse_release_text_stops_before_site_footer(self):
        text = parse_release(FIXTURE, ITEM).text
        self.assertTrue(text.rstrip().endswith("November 2026/ 4"))
        self.assertNotIn("2338313)", text)

    def test_parse_release_missing_date_gives_none(self):
        page = re.sub(r"\d{1,2} NOV 2026 \d{1,2}:\d{2}[AP]M", "", FIXTURE)
        self.assertIsNone(parse_release(page, ITEM).posted)

    def test_parse_release_keeps_listing_fields(self):
        release = parse_release(FIXTURE, ITEM)
        self.assertEqual((release.prid, release.title, release.ministry, release.url),
                         (ITEM.prid, ITEM.title, ITEM.ministry, ITEM.url))


class FakeSession:
    def __init__(self) -> None:
        self.requested = ""

    def get(self, url: str) -> str:
        self.requested = url
        return FIXTURE


class FetchReleaseTest(unittest.TestCase):
    def test_fetch_release_gets_iframe_page(self):
        s = FakeSession()
        release = fetch_release(ITEM, s)
        self.assertEqual(s.requested, ITEM.url)
        self.assertEqual(release.posted, date(2026, 11, 19))


if __name__ == "__main__":
    unittest.main()
