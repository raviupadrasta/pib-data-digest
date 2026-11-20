# PIB Data Digest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each morning at 10:00 IST, write a markdown digest of the data releases that PIB published the day before, with a draft tweet for each.

**Architecture:** A Python script reads the RSS feeds of chosen ministries, fetches each release page, keeps the releases dated the target day, and passes their text to `claude -p`. Claude returns JSON entries. The script checks every number in each entry against the release text, then writes `digests/YYYY-MM-DD.md`.

**Tech Stack:** Python (standard library only), `unittest`, Claude Code headless mode (`claude -p`).

**Spec:** `docs/superpowers/specs/2026-11-20-pib-data-digest-design.md`

> **Revision (2026-11-20, during build):** PIB has no per-ministry RSS feeds. Tasks 1 to 3 were built on PIB's dated release list instead (`pib_digest/http.py`, `listing.py`, `release.py`, `collect.py`; `Collected.warnings` replaces `cut_off`). See "Design change" in the spec. Tasks 4 to 6 are as written.

## Global Constraints

- Standard library only. No new dependencies. No browser automation.
- Run with the root venv: `/Users/raviupadrasta/Documents/GitHub/.venv/bin/python`. Tests: `python -m unittest discover -s tests`.
- No Anthropic API key. Model access only through `claude -p`.
- No secrets in the repo.
- Target day is the previous calendar day in IST (fixed offset +05:30, no DST). Do not use `zoneinfo` (Windows needs extra data).
- PIB redirects `pib.gov.in` to `www.pib.gov.in`. Send a browser-like `User-Agent`. Follow redirects.
- Each RSS feed holds at most 20 items, with title and link only. The release date comes from the release page.
- Python rules from the root CLAUDE.md: type hints on public functions, `pathlib`, `with` for files, `encoding="utf-8"`, no bare `except:`, script logic in functions, `if __name__ == "__main__":` guard.
- Do not commit unless Ravi asks. The plan has no commit steps for that reason. The project is not yet a git repo; Ravi will run `git init`.
- Repeatable: the same input gives the same digest file. Never edit source data.

## Review Focus

- A release page has no readable "Posted On" date: the release is skipped and listed under failures, not guessed.
- Hindi or Urdu releases in an English feed: kept out of the model prompt unless the text is mostly Latin script (cheap filter), so they do not produce garbled drafts.
- A day with no data releases: the digest file still exists and says so.
- Claude returns invalid JSON or an empty reply: the run fails loudly with the raw reply saved next to the digest; no partial digest.
- Number formats differ between the release and the draft (`1,23,456` vs `123456`, `5.5%` vs `5.5 per cent`): the check normalizes both before comparing.
- A feed fetch fails: retry once, then list the ministry under failures; the other ministries still run.
- Re-running for the same date overwrites the same file with the same structure.
- A weekday-only schedule: Monday must produce Friday, Saturday and Sunday files; a failed day must be retried on the next run, not skipped.

---

## File structure

- `ministries.json`: list of `{"name": str, "feed_url": str}`.
- `prompt.md`: fixed prompt text for Claude.
- `pib_digest/http.py`: `fetch_text`.
- `pib_digest/feeds.py`: ministry loading and feed parsing.
- `pib_digest/release.py`: release page parsing.
- `pib_digest/collect.py`: gather the target day's releases, cut-off check.
- `pib_digest/summarize.py`: prompt, `claude -p` call, JSON parsing, number check.
- `pib_digest/digest.py`: render and write the digest.
- `run_digest.py`: command line entry point.
- `tests/`: one `test_<module>.py` per module, with small fixture files in `tests/fixtures/`.
- `README.md`: how to run and schedule.

### Task 1: HTTP fetch and feed parsing

**Files:**
- Create: `pib_digest/__init__.py`, `pib_digest/http.py`, `pib_digest/feeds.py`, `ministries.json`
- Test: `tests/test_feeds.py`, `tests/fixtures/feed.xml`

**Interfaces:**
- Produces:
  - `class FetchError(Exception)`
  - `def fetch_text(url: str, retries: int = 1) -> str` (raises `FetchError` after retries)
  - `@dataclass(frozen=True) class Ministry: name: str; feed_url: str`
  - `@dataclass(frozen=True) class FeedItem: prid: int; title: str; url: str`
  - `def load_ministries(path: Path) -> list[Ministry]`
  - `def parse_feed(xml_text: str) -> list[FeedItem]`

- [ ] **Step 1: Find the feed URLs.** Open `https://www.pib.gov.in/RssMain.aspx` (the PIB RSS index) with `curl -L`. For each ministry in the spec list (Statistics and Programme Implementation, Finance, Commerce and Industry, Labour and Employment, Agriculture, Power, Petroleum and Natural Gas, Consumer Affairs), find its English feed URL. Confirm each URL returns English titles. Write them to `ministries.json`. If a ministry has no English feed, leave it out and tell Ravi.
- [ ] **Step 2: Write failing tests** in `tests/test_feeds.py` using a saved real feed in `tests/fixtures/feed.xml`: `test_parse_feed_returns_items` (count equals items in fixture; first item has `prid` as int from `PRID=` in the link), `test_parse_feed_strips_bom` (fixture starts with a BOM), `test_load_ministries_reads_json`.
- [ ] **Step 3: Run** `python -m unittest tests.test_feeds`. Expected: FAIL (module not found).
- [ ] **Step 4: Implement** the signatures above. `fetch_text` uses `urllib.request` with a browser-like `User-Agent` and decodes UTF-8. `parse_feed` uses `xml.etree.ElementTree` after removing a leading BOM.
- [ ] **Step 5: Run** the tests. Expected: PASS.

### Task 2: Release page parsing

**Files:**
- Create: `pib_digest/release.py`
- Test: `tests/test_release.py`, `tests/fixtures/release.html`, `tests/fixtures/release_no_date.html`

**Interfaces:**
- Consumes: `FeedItem`, `fetch_text` from Task 1.
- Produces:
  - `@dataclass(frozen=True) class Release: prid: int; title: str; url: str; posted: date | None; text: str`
  - `def parse_release(html: str, item: FeedItem) -> Release`
  - `def fetch_release(item: FeedItem) -> Release`

- [ ] **Step 1: Inspect a real release page** (`PressReleasePage.aspx?PRID=<id>` and `PressReleaseIframePage.aspx?PRID=<id>`). Choose the URL that holds the body text in the raw HTML. Save one real page as `tests/fixtures/release.html` and a copy with the date line removed as `release_no_date.html`.
- [ ] **Step 2: Write failing tests:** `test_parse_release_reads_posted_date` (asserts the exact `date` in the fixture), `test_parse_release_text_has_body_not_markup` (asserts a known sentence is in `text` and `"<div"` is not), `test_parse_release_missing_date_gives_none`.
- [ ] **Step 3: Run** the tests. Expected: FAIL.
- [ ] **Step 4: Implement** with `html.parser.HTMLParser` (no new dependency). Read the "Posted On" date with a regex on the visible text. Return `posted=None` if it is not found. Collapse whitespace in `text`.
- [ ] **Step 5: Run** the tests. Expected: PASS.

### Task 3: Collect the target day

**Files:**
- Create: `pib_digest/collect.py`
- Test: `tests/test_collect.py`

**Interfaces:**
- Consumes: `Ministry`, `FeedItem`, `parse_feed`, `Release`, `fetch_release`, `FetchError`.
- Produces:
  - `@dataclass class Collected: releases: list[Release]; cut_off: list[str]; failures: list[str]`
  - `def collect(ministries: list[Ministry], day: date, fetch_feed=fetch_text, fetch_rel=fetch_release) -> Collected`
  - `def yesterday_ist(now: datetime | None = None) -> date`
  - `def days_to_cover(out_dir: Path, yesterday: date, cap: int = 7) -> list[date]` (days after the latest `YYYY-MM-DD.md` in `out_dir`, up to `yesterday`, oldest first; `[yesterday]` if the folder has no digest; `[]` if already up to date; only the last `cap` days if the gap is longer)

- [ ] **Step 1: Write failing tests** with fake fetch functions: `test_collect_keeps_only_target_day`, `test_collect_dedups_same_prid_across_ministries`, `test_collect_flags_cut_off_when_20_items_all_target_day`, `test_collect_no_cut_off_when_older_item_present`, `test_collect_feed_failure_listed_and_others_continue`, `test_collect_release_without_date_listed_as_failure`, `test_yesterday_ist_at_0430_utc_is_previous_ist_day` (04:30 UTC is 10:00 IST; assert the date), `test_yesterday_ist_late_utc_evening_rolls_forward` (20:00 UTC is 01:30 IST next day), `test_days_to_cover_monday_gives_fri_sat_sun` (latest file is Thursday, yesterday is Sunday), `test_days_to_cover_empty_folder_gives_yesterday`, `test_days_to_cover_up_to_date_gives_empty`, `test_days_to_cover_caps_at_seven_days`, `test_days_to_cover_ignores_raw_and_other_files` (`.raw.txt` and unrelated names do not count as digests).
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** A ministry is "cut off" when its feed has exactly 20 items and every fetched release is dated the target day. Failure strings read `"<ministry>: <reason>"` or `"PRID <id>: no posted date"`.
- [ ] **Step 4: Run.** Expected: PASS.

### Task 4: Summarize with Claude, and check the numbers

**Files:**
- Create: `prompt.md`, `pib_digest/summarize.py`
- Test: `tests/test_summarize.py`

**Interfaces:**
- Consumes: `Release`.
- Produces:
  - `class SummaryError(Exception)`
  - `@dataclass(frozen=True) class Entry: prid: int; headline: str; previous: str | None; takeaway: str; tweet: str`
  - `@dataclass(frozen=True) class CheckedEntry: entry: Entry; unverified: list[str]`
  - `def build_prompt(template: str, releases: list[Release]) -> str`
  - `def run_claude(prompt: str, runner=subprocess.run) -> str`
  - `def parse_entries(raw: str) -> list[Entry]` (raises `SummaryError`)
  - `def unverified_numbers(text: str, source: str) -> list[str]`
  - `def summarize(releases: list[Release], template: str, runner=subprocess.run) -> list[CheckedEntry]`

- [ ] **Step 1: Check headless mode works on this machine.** Run `echo "say ok" | claude -p`. Expected: a text reply. If it fails on the work laptop, stop and tell Ravi. The spec marks this as untested.
- [ ] **Step 2: Write `prompt.md`.** It must tell Claude to: reply with a JSON list only; include a release only if it announces new data (numbers a researcher would cite); use only numbers that appear in that release; give `previous` only if the release states it, else `null`; write one tweet per entry with the number, the change and no hashtags beyond one; return `[]` if there is no data release. Each release in the prompt is marked with its PRID.
- [ ] **Step 3: Write failing tests:** `test_parse_entries_reads_json_list`, `test_parse_entries_accepts_code_fenced_json`, `test_parse_entries_rejects_invalid_json` (raises `SummaryError`), `test_parse_entries_empty_list_is_ok`, `test_unverified_numbers_flags_number_missing_from_source` (`"CPI 5.5%"` vs source without 5.5), `test_unverified_numbers_normalizes_indian_commas` (`1,23,456` in source, `123456` in tweet passes), `test_unverified_numbers_normalizes_per_cent` (`5.5 per cent` in source, `5.5%` in tweet passes), `test_summarize_uses_runner_and_checks_each_entry` (fake runner returns canned JSON), `test_run_claude_nonzero_exit_raises_summary_error`.
- [ ] **Step 4: Run.** Expected: FAIL.
- [ ] **Step 5: Implement.** `run_claude` calls `["claude", "-p"]` with the prompt on stdin and a timeout of 300 seconds. `unverified_numbers` extracts numeric tokens from `text` and returns those not found, after normalizing, in `source`. Skip single digits that are part of words (for example "Q2") and four-digit years.
- [ ] **Step 6: Run.** Expected: PASS.

### Task 5: Digest file and command line

**Files:**
- Create: `pib_digest/digest.py`, `run_digest.py`
- Test: `tests/test_digest.py`, `tests/test_run_digest.py`

**Interfaces:**
- Consumes: `Collected`, `CheckedEntry`, `Release`, `collect`, `summarize`, `yesterday_ist`, `load_ministries`.
- Produces:
  - `def render_digest(day: date, entries: list[tuple[CheckedEntry, Release]], cut_off: list[str], failures: list[str]) -> str`
  - `def write_digest(day: date, text: str, out_dir: Path) -> Path` (writes `out_dir/YYYY-MM-DD.md`)
  - `def main(argv: list[str] | None = None) -> int` in `run_digest.py`, with `--date YYYY-MM-DD` (one day only; default is `days_to_cover(out_dir, yesterday_ist())`, one digest file per day, oldest first, stop at the first failing day) and `--out-dir` (default `digests`)

- [ ] **Step 1: Write failing tests:** `test_render_lists_headline_previous_takeaway_link_tweet` (assert each appears for one entry), `test_render_marks_unverified_numbers_with_warning` (text contains the unverified number and the word "CHECK"), `test_render_empty_day_says_no_data_releases`, `test_render_lists_cut_off_ministries_and_failures`, `test_write_digest_same_input_same_file` (write twice, bytes equal), `test_main_end_to_end_with_fakes` (patch `collect` and `summarize`, run `main(["--date", "2026-11-19", "--out-dir", tmp])`, assert the file exists), `test_main_invalid_claude_reply_saves_raw_and_returns_nonzero` (raw reply saved as `YYYY-MM-DD.raw.txt`, no digest file written), `test_main_catch_up_writes_one_file_per_day` (latest file Thursday, run on Monday: Friday, Saturday and Sunday files exist), `test_main_failure_on_second_day_keeps_first_file_and_writes_no_later_file`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement** the signatures. In `main`, catch `SummaryError` only (not bare `except`).
- [ ] **Step 4: Run** all tests: `python -m unittest discover -s tests`. Expected: all PASS.

### Task 6: Real run, README and schedule

**Files:**
- Create: `README.md`, `.gitignore` (add `digests/*.raw.txt`)

- [ ] **Step 1: Run for real** for yesterday: `python run_digest.py`. Expected: `digests/<yesterday>.md` exists. Open it and compare each number in each draft with the PIB page. Report any mismatch to Ravi.
- [ ] **Step 2: Run for a known data day.** Pick a past day with a CPI or GDP release and run `python run_digest.py --date <day>`. Expected: that release appears with the right headline number.
- [ ] **Step 3: Write `README.md`:** how to run by hand, how to edit `ministries.json`, and how to schedule at 10:00 for macOS (`launchd` plist) and Windows (Task Scheduler). The scheduled command uses the absolute path of the venv Python.
- [ ] **Step 4: Ask Ravi** which OS the work laptop runs, then set up only that scheduler entry with him.

---

## Self-review

- Spec coverage: daily 10:00 run and previous day (Task 3, 6); per-release fields and draft tweet (Task 4, 5); markdown file (Task 5); ministry list in `ministries.json` (Task 1); cut-off warning (Task 3, 5); no silent miss on fetch failure (Task 3, 5); number accuracy (Task 4, 5); retry once (Task 1); tests for day filter and cut-off check (Task 3); no secrets, stdlib only (Global Constraints).
- Interfaces match across tasks: `Release`, `Collected`, `CheckedEntry` names are used the same way in Tasks 3 to 5.
- Open item for the builder: the RSS item has no date, so the script fetches every release page in a feed (up to 20 per ministry, about 160 fetches a day). That is acceptable for one daily run.
