"""Render the digest as markdown and write it to digests/YYYY-MM-DD.md."""
from datetime import date
from pathlib import Path

from pib_digest.release import Release
from pib_digest.summarize import CheckedEntry

RELEASE_PAGE = "https://www.pib.gov.in/PressReleaseDetail.aspx?PRID={prid}"


def render_digest(
    day: date,
    entries: list[tuple[CheckedEntry, Release]],
    warnings: list[str],
    failures: list[str],
) -> str:
    lines = [f"# PIB data digest: {day.isoformat()} ({day:%A})", ""]
    if not entries:
        lines += ["No data releases from the chosen ministries.", ""]
    for number, (checked, release) in enumerate(entries, start=1):
        entry = checked.entry
        lines += [f"## {number}. {entry.headline}", "", f"- Ministry: {release.ministry}"]
        if entry.previous:
            lines.append(f"- Previous: {entry.previous}")
        lines += [
            f"- Takeaway: {entry.takeaway}",
            f"- Source: {RELEASE_PAGE.format(prid=release.prid)}",
            "",
            "Draft tweet:",
            "",
            f"> {entry.tweet}",
            "",
        ]
        if checked.unverified:
            numbers = ", ".join(checked.unverified)
            lines += [f"**CHECK before posting:** these numbers are not in the release text: {numbers}.", ""]
    if warnings:
        lines += ["## Warnings", ""] + [f"- {w}" for w in warnings] + [""]
    if failures:
        lines += ["## Failures", ""] + [f"- {f}" for f in failures] + [""]
    return "\n".join(lines)


def write_digest(day: date, text: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{day.isoformat()}.md"
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path
