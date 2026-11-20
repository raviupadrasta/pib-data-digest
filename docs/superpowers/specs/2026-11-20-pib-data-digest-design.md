# PIB data digest: design

Date: 2026-11-20. Status: awaiting approval.

## Intent and why
Ravi leads research and content. He wants to post or tweet about government data releases on the same day they come out. Each morning, an agent finds the data releases that PIB (pib.gov.in) published the day before. It writes one digest with a draft tweet for each release. Speed and accuracy matter most. A wrong number in a post is worse than a late post.

## Goals
- Run once a day at 10:00 IST. Cover the previous calendar day (IST).
- Catch up after gaps (weekends, holidays, laptop off). By default, cover every day from the day after the latest digest file up to yesterday. Cap at 7 days. Write one digest file per day. A weekday-only schedule then loses nothing: Monday covers Friday, Saturday and Sunday.
- For each data release, give: headline number, previous value and change, one-line takeaway, PIB link, draft tweet.
- Write the digest to a dated markdown file in the repo.
- Run on Ravi's work laptop with no extra database.

## Non-goals
- No posting to X or any other service. Ravi reviews and posts himself.
- No charts and no database (a later step, if wanted).
- No coverage of ministries outside the list below.

## Anti-goals
- A number in a draft that does not appear in the source release.
- A silent miss. If a feed shows signs of cutting off the day, the digest says so.

## Constraints
- Work laptop. Needs only plain HTTPS downloads. No browser automation.
- No secrets in the repo.
- Model access is through Claude Code in headless mode (`claude -p`). No Anthropic API key, so no separate bill. Not yet tested on the work setup.
- PIB redirects `pib.gov.in` to `www.pib.gov.in`. Use redirects and a browser-like User-Agent.
- Each PIB RSS feed has only the latest 20 items, with titles and links only. The release body comes from the release page.

## Approaches considered
1. General RSS feed only. Simple, but 20 items misses most of a day. Rejected.
2. Browser automation on the dated listing page. Sees the full day, but needs a browser tool at work and breaks when the page changes. Rejected.
3. RSS feeds for chosen ministries, then fetch each new release page. Chosen by Ravi. Works because data-heavy ministries publish few releases a day.

## Design (Ravi chose approach 3; the rest is my call)
Flow, run by `run_digest.py`. First, pick the days to cover: `--date` gives one day; otherwise the catch-up rule above. Then, for each day in order, run steps 1 to 5. If a day fails, stop. That day has no file, so the next run starts from it.
1. Read the RSS feed of each ministry on the list.
2. Keep items from the target day. Fetch each release page and keep the text.
3. If a feed returned 20 items and all are from the target day, mark that feed "possibly cut off" in the digest.
4. Pass the release texts to `claude -p` with a fixed prompt. The prompt tells Claude to: drop releases without new data; use only numbers that appear in the text; give the previous value only if the release states it; write one draft tweet per data release.
5. Write `digests/YYYY-MM-DD.md`. If no data releases exist, the file says so.

Starting ministry list (my call): Statistics and Programme Implementation (CPI, GDP, IIP), Finance (GST, tax, fiscal data), Commerce and Industry (trade, FDI), Labour and Employment (EPFO, PLFS), Agriculture, Power, Petroleum and Natural Gas, Consumer Affairs. Ravi can edit the list in `ministries.json`.

Repo layout (my call): `run_digest.py`, `ministries.json`, `prompt.md`, `digests/`, `docs/`. Python with the standard library only. Scheduling: Windows Task Scheduler or macOS launchd, set up after the script works by hand.

Re-runs are repeatable. The script never edits an old digest unless run again for the same date, and it then writes the same file.

## Left to the builder
- Find the correct feed URL and language parameter for each ministry.
- Choose how to detect the target day from feed dates.
- Handle a failed fetch: retry once, then list the failure in the digest.
- Write tests for the day filter and the cut-off check.

## Design change found while building (2026-11-20)
PIB has no per-ministry RSS feeds. `RssMain.aspx?ModId=N` takes a module id, and the only useful feed (`ModId=6`) mixes all ministries and holds 20 items. Approach 3 changes in one way and keeps its intent (plain downloads, no browser, chosen ministries only):
- The script posts PIB's dated release list form (`allRel.aspx`, English, PIB Delhi) for the target day. It gets the whole day in one request, grouped by ministry. It keeps the ministries in `ministries.json` (heading names).
- The 20-item cut-off check is not needed. A warning shows when the listing is empty.
- A failed listing fetch stops the run for that day and writes no file, so the next run retries it.
