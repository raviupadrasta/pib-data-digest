"""One PIB press release: the date and the body text."""
import html
import re
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser

from pib_digest.http import Session
from pib_digest.listing import ListingItem

_FOOTER = re.compile(r"\((?:Release ID|रिलीज़ आईडी):.*$")  # PIB appends release id and language links
_DATE = re.compile(r"(\d{1,2} [A-Za-z]{3} \d{4}) \d{1,2}:\d{2}\s*[AP]M")


@dataclass(frozen=True)
class Release:
    prid: int
    title: str
    ministry: str
    url: str
    posted: date | None
    text: str


class _BodyParser(HTMLParser):
    """Collects the body text: everything after the date line (id="PrDateTime")
    and before the hidden print copy (id="PdfDiv"), which repeats the body."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._date_div_depth = 0  # >0 while inside the date div
        self._capturing = False
        self._done = False
        self._skip = 0  # inside <script> or <style>

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._skip += 1
        elif tag == "div":
            ids = dict(attrs).get("id")
            if self._date_div_depth:
                self._date_div_depth += 1
            elif ids == "PrDateTime":
                self._date_div_depth = 1
            elif ids == "PdfDiv" and self._capturing:
                self._capturing = False
                self._done = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)
        elif tag == "div" and self._date_div_depth:
            self._date_div_depth -= 1
            if not self._date_div_depth and not self._done:
                self._capturing = True

    def handle_data(self, data: str) -> None:
        if self._capturing and not self._skip:
            self.parts.append(data)


def _posted(page: str) -> date | None:
    match = re.search(r'id="PrDateTime"[^>]*>(.*?)</div>', page, re.S)
    found = _DATE.search(html.unescape(match.group(1))) if match else None
    if not found:
        return None
    return datetime.strptime(found.group(1), "%d %b %Y").date()


def parse_release(page: str, item: ListingItem) -> Release:
    parser = _BodyParser()
    parser.feed(page)
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    text = _FOOTER.sub("", text).strip()
    return Release(item.prid, item.title, item.ministry, item.url, _posted(page), text)


def fetch_release(item: ListingItem, session: Session | None = None) -> Release:
    session = session or Session()
    return parse_release(session.get(item.url), item)
