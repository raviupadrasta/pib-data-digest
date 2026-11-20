import unittest
import urllib.error

from pib_digest.http import FetchError, Session


class FlakySession(Session):
    """Fails `failures` times, then returns a page."""

    def __init__(self, failures: int) -> None:
        super().__init__()
        self.failures = failures
        self.calls = 0

    def _send(self, request):
        self.calls += 1
        if self.calls <= self.failures:
            raise urllib.error.URLError("boom")
        return "page"


class SessionTest(unittest.TestCase):
    def test_get_retries_once_then_succeeds(self):
        s = FlakySession(failures=1)
        self.assertEqual(s.get("https://example.test/"), "page")
        self.assertEqual(s.calls, 2)

    def test_get_raises_fetch_error_after_retry(self):
        s = FlakySession(failures=2)
        with self.assertRaises(FetchError):
            s.get("https://example.test/")
        self.assertEqual(s.calls, 2)

    def test_post_retries_once_then_succeeds(self):
        s = FlakySession(failures=1)
        self.assertEqual(s.post("https://example.test/", {"a": "1"}), "page")


if __name__ == "__main__":
    unittest.main()
