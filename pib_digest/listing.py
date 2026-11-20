"""PIB's dated release list (allRel.aspx), read with a plain form POST."""
import html
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pib_digest.http import Session

BASE = "https://www.pib.gov.in"
LISTING_URL = f"{BASE}/allRel.aspx?reg=3&lang=1"  # reg=3 is PIB Delhi, lang=1 is English
FORM = "ctl00$ContentPlaceHolder1$"

_BLOCK = re.compile(r"<h3 class='font104'>(.*?)</h3>(.*?)(?=<h3 class='font104'>|$)", re.S)
_RELEASE = re.compile(r"<a title='(.*?)' href='/PressReleaseDetail\.aspx\?PRID=(\d+)'", re.S)


@dataclass(frozen=True)
class ListingItem:
    prid: int
    title: str
    url: str
    ministry: str


def load_ministries(path: Path) -> list[str]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse_listing(page: str) -> list[ListingItem]:
    items: list[ListingItem] = []
    for heading, body in _BLOCK.findall(page):
        ministry = _clean(heading)
        for title, prid in _RELEASE.findall(body):
            items.append(
                ListingItem(
                    prid=int(prid),
                    title=_clean(title),
                    url=f"{BASE}/PressReleaseIframePage.aspx?PRID={prid}",
                    ministry=ministry,
                )
            )
    return items


def _hidden(page: str, name: str) -> str:
    match = re.search(rf'name="{re.escape(name)}"[^>]*value="([^"]*)"', page)
    return html.unescape(match.group(1)) if match else ""


def fetch_listing(day: date, session: Session | None = None) -> list[ListingItem]:
    session = session or Session()
    page = session.get(LISTING_URL)
    fields = {
        "__EVENTTARGET": f"{FORM}ddlday",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": _hidden(page, "__VIEWSTATE"),
        "__VIEWSTATEGENERATOR": _hidden(page, "__VIEWSTATEGENERATOR"),
        "__EVENTVALIDATION": _hidden(page, "__EVENTVALIDATION"),
        "ctl00$Bar1$ddlregion": "3",
        "ctl00$Bar1$ddlLang": "1",
        f"{FORM}hydregionid": "3",
        f"{FORM}hydLangid": "1",
        f"{FORM}ddlMinistry": "0",  # 0 = all ministries; we filter by heading name later
        f"{FORM}ddlday": str(day.day),
        f"{FORM}ddlMonth": str(day.month),
        f"{FORM}ddlYear": str(day.year),
    }
    return parse_listing(session.post(LISTING_URL, fields))
