import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from pib_digest.listing import ListingItem, fetch_listing, load_ministries, parse_listing

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_html() -> str:
    return (FIXTURES / "listing.html").read_text(encoding="utf-8")


class ParseListingTest(unittest.TestCase):
    def test_parse_listing_returns_every_release(self):
        self.assertEqual(len(parse_listing(fixture_html())), 20)

    def test_parse_listing_attaches_ministry_and_unescapes_ampersand(self):
        items = parse_listing(fixture_html())
        mospi = [i for i in items if i.ministry == "Ministry of Statistics & Programme Implementation"]
        self.assertEqual(len(mospi), 1)
        self.assertEqual(mospi[0].prid, 2338694)

    def test_parse_listing_builds_iframe_page_url(self):
        item = next(i for i in parse_listing(fixture_html()) if i.prid == 2338520)
        self.assertEqual(item.url, "https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=2338520")
        self.assertTrue(item.title.startswith("DRI seizes over 71 kg heroin"))
        self.assertEqual(item.ministry, "Ministry of Finance")

    def test_parse_listing_empty_page_gives_empty_list(self):
        self.assertEqual(parse_listing("<html></html>"), [])


class LoadMinistriesTest(unittest.TestCase):
    def test_load_ministries_reads_names(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "m.json"
            p.write_text(json.dumps(["Ministry of Finance"]), encoding="utf-8")
            self.assertEqual(load_ministries(p), ["Ministry of Finance"])


class FakeSession:
    def __init__(self) -> None:
        self.posted: dict[str, str] = {}

    def get(self, url: str) -> str:
        return (
            '<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="VS1" />'
            '<input type="hidden" name="__VIEWSTATEGENERATOR" id="__VIEWSTATEGENERATOR" value="GEN1" />'
            '<input type="hidden" name="__EVENTVALIDATION" id="__EVENTVALIDATION" value="EV1" />'
        )

    def post(self, url: str, fields: dict[str, str]) -> str:
        self.posted = fields
        return fixture_html()


class FetchListingTest(unittest.TestCase):
    def test_fetch_listing_posts_target_day_for_all_ministries(self):
        s = FakeSession()
        items = fetch_listing(date(2026, 11, 9), s)
        self.assertEqual(len(items), 20)
        f = s.posted
        self.assertEqual(f["ctl00$ContentPlaceHolder1$ddlday"], "9")
        self.assertEqual(f["ctl00$ContentPlaceHolder1$ddlMonth"], "11")
        self.assertEqual(f["ctl00$ContentPlaceHolder1$ddlYear"], "2026")
        self.assertEqual(f["ctl00$ContentPlaceHolder1$ddlMinistry"], "0")
        self.assertEqual(f["__VIEWSTATE"], "VS1")
        self.assertEqual(f["__EVENTVALIDATION"], "EV1")


if __name__ == "__main__":
    unittest.main()
