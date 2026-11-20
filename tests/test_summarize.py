import json
import subprocess
import unittest
from datetime import date

from pib_digest.release import Release
from pib_digest.summarize import (
    Entry,
    SummaryError,
    build_prompt,
    parse_entries,
    run_claude,
    summarize,
    unverified_numbers,
)

CPI = Release(
    prid=101,
    title="Consumer Price Index for October 2026",
    ministry="Ministry of Statistics & Programme Implementation",
    url="https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=101",
    posted=date(2026, 11, 12),
    text="All-India CPI inflation was 5.5 per cent in October 2026 against 5.1 per cent in September 2026.",
)
ENTRY = {
    "prid": 101,
    "headline": "CPI inflation 5.5% in October",
    "previous": "5.1% in September",
    "takeaway": "Inflation edged up from September.",
    "tweet": "India CPI inflation: 5.5% in Oct 2026 vs 5.1% in Sep.",
}


def fake_runner(stdout: str, returncode: int = 0, stderr: str = ""):
    calls: list[dict] = []

    def runner(cmd, **kwargs):
        calls.append({"cmd": cmd, **kwargs})
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)

    runner.calls = calls  # type: ignore[attr-defined]
    return runner


class ParseEntriesTest(unittest.TestCase):
    def test_parse_entries_reads_json_list(self):
        entries = parse_entries(json.dumps([ENTRY]))
        self.assertEqual(entries, [Entry(101, ENTRY["headline"], ENTRY["previous"], ENTRY["takeaway"], ENTRY["tweet"])])

    def test_parse_entries_accepts_code_fenced_json(self):
        self.assertEqual(len(parse_entries("```json\n" + json.dumps([ENTRY]) + "\n```")), 1)

    def test_parse_entries_rejects_invalid_json(self):
        with self.assertRaises(SummaryError) as ctx:
            parse_entries("Sorry, I cannot")
        self.assertEqual(ctx.exception.raw, "Sorry, I cannot")

    def test_parse_entries_empty_list_is_ok(self):
        self.assertEqual(parse_entries("[]"), [])

    def test_parse_entries_rejects_entry_missing_key(self):
        bad = {k: v for k, v in ENTRY.items() if k != "tweet"}
        with self.assertRaises(SummaryError):
            parse_entries(json.dumps([bad]))

    def test_parse_entries_null_previous_becomes_none(self):
        entries = parse_entries(json.dumps([{**ENTRY, "previous": None}]))
        self.assertIsNone(entries[0].previous)


class UnverifiedNumbersTest(unittest.TestCase):
    def test_flags_number_missing_from_source(self):
        self.assertEqual(unverified_numbers("CPI 5.5%", "inflation was 4.2 per cent"), ["5.5"])

    def test_normalizes_indian_commas(self):
        self.assertEqual(unverified_numbers("Collections Rs 123456 crore", "Rs 1,23,456 crore"), [])

    def test_normalizes_per_cent(self):
        self.assertEqual(unverified_numbers("CPI 5.5%", "5.5 per cent in October"), [])

    def test_ignores_years_and_digits_inside_words(self):
        self.assertEqual(unverified_numbers("Q2 FY26 data for 2026", "no figures"), [])

    def test_sentence_final_number_with_period(self):
        self.assertEqual(unverified_numbers("Inflation hit 5.5.", "was 5.5 per cent"), [])

    def test_rounded_number_is_flagged(self):
        self.assertEqual(unverified_numbers("GDP grew 7.5%", "GDP grew 7.48 per cent"), ["7.5"])


class RunClaudeTest(unittest.TestCase):
    def test_run_claude_passes_prompt_on_stdin_and_returns_stdout(self):
        runner = fake_runner("[]")
        self.assertEqual(run_claude("hello", runner), "[]")
        self.assertEqual(runner.calls[0]["cmd"], ["claude", "-p"])
        self.assertEqual(runner.calls[0]["input"], "hello")

    def test_run_claude_nonzero_exit_raises_summary_error(self):
        with self.assertRaises(SummaryError) as ctx:
            run_claude("hello", fake_runner("", returncode=1, stderr="not logged in"))
        self.assertIn("not logged in", str(ctx.exception))

    def test_run_claude_missing_binary_raises_summary_error(self):
        def runner(cmd, **kwargs):
            raise FileNotFoundError("claude")

        with self.assertRaises(SummaryError):
            run_claude("hello", runner)

    def test_run_claude_timeout_raises_summary_error(self):
        def runner(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 300)

        with self.assertRaises(SummaryError):
            run_claude("hello", runner)


class SummarizeTest(unittest.TestCase):
    def test_build_prompt_has_template_and_each_release(self):
        prompt = build_prompt("RULES", [CPI])
        self.assertIn("RULES", prompt)
        self.assertIn("PRID 101", prompt)
        self.assertIn(CPI.ministry, prompt)
        self.assertIn(CPI.text, prompt)

    def test_summarize_uses_runner_and_checks_each_entry(self):
        wrong = {**ENTRY, "tweet": "CPI inflation 6.9% in Oct 2026."}
        runner = fake_runner(json.dumps([ENTRY, {**wrong, "prid": 101}]))
        checked = summarize([CPI], "RULES", runner)
        self.assertEqual([c.unverified for c in checked], [[], ["6.9"]])
        self.assertIn(CPI.text, runner.calls[0]["input"])

    def test_summarize_no_releases_does_not_call_claude(self):
        runner = fake_runner("[]")
        self.assertEqual(summarize([], "RULES", runner), [])
        self.assertEqual(runner.calls, [])

    def test_summarize_unknown_prid_raises(self):
        with self.assertRaises(SummaryError):
            summarize([CPI], "RULES", fake_runner(json.dumps([{**ENTRY, "prid": 999}])))


if __name__ == "__main__":
    unittest.main()
