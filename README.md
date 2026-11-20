# PIB data digest

This tool reads the press releases that PIB (pib.gov.in) published on a day. It finds the releases that announce new data. It writes one markdown file for each day, with a draft tweet for each data release.

You review the file and post yourself. The tool never posts.

## How it works

1. The tool opens PIB's dated release list (`allRel.aspx`) with a plain form request. It gets every release of the day.
2. It keeps the releases of the ministries in `ministries.json`.
3. It reads each release page.
4. It asks Claude (`claude -p`) which releases announce data, and for a draft tweet for each.
5. It checks that every number in a draft appears in the release text. If a number does not appear, the digest shows **CHECK before posting** under that item.
6. It writes `digests/YYYY-MM-DD.md`.

## Requirements

- Python 3.10 or newer. No packages to install.
- Claude Code installed, signed in, and on the `PATH`. Test with: `echo "say ok" | claude -p`.

## Run by hand

```
python run_digest.py                  # every day since the last digest, up to yesterday (IST)
python run_digest.py --date 2026-11-12  # one day
```

By default the tool catches up. If the latest file is Thursday and today is Monday, it writes Friday, Saturday and Sunday. The limit is 7 days. If a day fails, the tool stops. That day has no file, so the next run starts from it.

If Claude returns bad output, the tool saves the reply as `digests/YYYY-MM-DD.raw.txt` and writes no digest for that day.

## Change the ministries

Edit `ministries.json`. Use the exact ministry heading from PIB's release list, for example `Ministry of Finance`. Case and spacing do not matter.

## Schedule it at 10:00 on weekdays

Use the full path to Python. Catch-up covers weekends and days when the laptop was off.

### macOS (launchd)

A ready file is in `scheduling/com.pib-data-digest.plist`. It uses the root `.venv` Python, because the macOS system `python3` is often 3.9, which is too old. Copy it to `~/Library/LaunchAgents/`. Check that the `PATH` line includes the folder from `which claude`. The listing below shows the same file with placeholder paths.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.pib-data-digest</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/python3</string>
    <string>/FULL/PATH/TO/pib-data-digest/run_digest.py</string>
  </array>
  <key>EnvironmentVariables</key><dict>
    <key>PATH</key><string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/Users/YOU/.local/bin</string>
  </dict>
  <key>StartCalendarInterval</key><array>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>10</integer><key>Minute</key><integer>0</integer></dict>
  </array>
  <key>StandardOutPath</key><string>/tmp/pib-data-digest.log</string>
  <key>StandardErrorPath</key><string>/tmp/pib-data-digest.log</string>
</dict></plist>
```

Load it: `launchctl load ~/Library/LaunchAgents/com.pib-data-digest.plist`.

The `PATH` entry matters. launchd starts jobs with a short `PATH`, and the job must find `claude`.

### Windows (Task Scheduler)

```
schtasks /Create /TN "PIB data digest" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 10:00 /TR "C:\full\path\to\python.exe C:\full\path\to\pib-data-digest\run_digest.py"
```

In Task Scheduler, open the task and turn on "Run task as soon as possible after a scheduled start is missed".

## Tests

```
python -m unittest discover -s tests
```

## Known limits

- PIB has no per-ministry feeds, so the tool reads the dated release list. If PIB changes that page, the tool shows the warning "PIB listing ... has no releases". Check PIB by hand when you see it.
- The tool reads PIB's English release list for the Delhi region (`reg=3`, `lang=1`).
- Years are not checked by the number check. A wrong year in a draft is not flagged.
- Check each draft against the PIB link before you post.
