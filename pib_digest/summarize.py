"""Ask Claude which releases carry data and for draft tweets, then check every number."""
import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass

from pib_digest.release import Release

CLAUDE_TIMEOUT_SECONDS = 300
_KEYS = ("prid", "headline", "previous", "takeaway", "tweet")
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_NUMBER_IN_DRAFT = re.compile(r"(?<![A-Za-z\d])\d[\d,]*(?:\.\d+)?")  # skip digits inside words: Q2, FY26
_YEAR = re.compile(r"^(19|20)\d\d$")


class SummaryError(Exception):
    def __init__(self, message: str, raw: str = "") -> None:
        super().__init__(message)
        self.raw = raw


@dataclass(frozen=True)
class Entry:
    prid: int
    headline: str
    previous: str | None
    takeaway: str
    tweet: str


@dataclass(frozen=True)
class CheckedEntry:
    entry: Entry
    unverified: list[str]


def build_prompt(template: str, releases: list[Release]) -> str:
    blocks = [f"=== PRID {r.prid} | {r.ministry} | {r.title}\n{r.text}" for r in releases]
    return template.rstrip() + "\n\n" + "\n\n".join(blocks) + "\n"


def run_claude(prompt: str, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> str:
    try:
        done = runner(
            ["claude", "-p"],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=CLAUDE_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise SummaryError("the `claude` command was not found on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise SummaryError(f"claude did not answer within {CLAUDE_TIMEOUT_SECONDS} seconds") from exc
    if done.returncode != 0:
        raise SummaryError(f"claude exited with {done.returncode}: {done.stderr.strip()}", done.stderr)
    return done.stdout


def parse_entries(raw: str) -> list[Entry]:
    body = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise SummaryError(f"claude did not return JSON: {exc}", raw) from exc
    if not isinstance(data, list):
        raise SummaryError("claude did not return a JSON list", raw)
    entries: list[Entry] = []
    for item in data:
        if not isinstance(item, dict) or any(k not in item for k in _KEYS):
            raise SummaryError(f"entry is missing one of {_KEYS}: {item!r}", raw)
        entries.append(
            Entry(int(item["prid"]), item["headline"], item["previous"], item["takeaway"], item["tweet"])
        )
    return entries


def _normalize(number: str) -> str:
    number = number.replace(",", "")
    return number.rstrip("0").rstrip(".") if "." in number else number


def unverified_numbers(text: str, source: str) -> list[str]:
    """Numbers in `text` that do not appear in `source`. Years are ignored."""
    known = {_normalize(n) for n in _NUMBER.findall(source)}
    missing: list[str] = []
    for found in _NUMBER_IN_DRAFT.findall(text):
        number = _normalize(found)
        if not _YEAR.match(number) and number not in known and number not in missing:
            missing.append(number)
    return missing


def summarize(
    releases: list[Release],
    template: str,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> list[CheckedEntry]:
    if not releases:
        return []
    raw = run_claude(build_prompt(template, releases), runner)
    by_prid = {r.prid: r for r in releases}
    checked: list[CheckedEntry] = []
    for entry in parse_entries(raw):
        release = by_prid.get(entry.prid)
        if release is None:
            raise SummaryError(f"claude returned an entry for unknown PRID {entry.prid}", raw)
        draft = " ".join(filter(None, (entry.headline, entry.previous, entry.takeaway, entry.tweet)))
        checked.append(CheckedEntry(entry, unverified_numbers(draft, f"{release.title} {release.text}")))
    return checked
