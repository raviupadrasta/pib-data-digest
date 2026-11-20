"""Plain HTTPS access to pib.gov.in. PIB blocks clients without a browser-like User-Agent."""
import http.cookiejar
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "Mozilla/5.0 (compatible; pib-data-digest)"
TIMEOUT_SECONDS = 40


class FetchError(Exception):
    """A page could not be fetched, even after one retry."""


class Session:
    """One cookie jar for the whole run, because the listing form is a GET then a POST."""

    def __init__(self) -> None:
        jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def _send(self, request: urllib.request.Request) -> str:
        with self._opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8-sig", "replace")

    def _send_with_retry(self, request: urllib.request.Request) -> str:
        last: OSError | None = None
        for _ in range(2):
            try:
                return self._send(request)
            except OSError as exc:  # URLError, HTTPError and timeouts are all OSError
                last = exc
        raise FetchError(f"{request.full_url}: {last}")

    def get(self, url: str) -> str:
        return self._send_with_retry(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}))

    def post(self, url: str, fields: dict[str, str]) -> str:
        request = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(fields).encode("utf-8"),
            headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
        )
        return self._send_with_retry(request)
