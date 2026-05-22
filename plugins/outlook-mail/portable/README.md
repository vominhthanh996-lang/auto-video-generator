# Outlook Mail Reporter

Portable Windows tool for reading Outlook Desktop mail from all folders and writing a daily Markdown report.

## Requirements

- Windows
- Classic Outlook Desktop installed and signed in
- Outlook profile can be opened on the machine
- PowerShell 5+

This tool reads mail through the local Outlook COM session. It does not need Microsoft Graph, Azure app registration, or a client ID.

## Quick start

1. Extract this folder anywhere, for example `D:\OutlookMailReporter`.
2. Open Outlook Desktop and keep the account signed in.
3. Double-click `Start-UI.bat` for the UI, or `Run-Now.bat` for command-line report.
4. Reports will be saved in the `reports` folder.

## UI mode

`Start-UI.bat` opens a small Windows UI:

- **Non-AI offline report**: no API key required.
- **Read mail with AI**: uses `OPENAI_API_KEY` from the current Windows user.
- If no API key exists, paste one into the UI and click **Save Key**.

Both modes export:

- Markdown report: `mail-report-YYYY-MM-DD.md`
- Excel workbook: `mail-report-YYYY-MM-DD-HHMMSS.xlsx`
- Raw JSON: `mail-report-YYYY-MM-DD-HHMMSS.json`

## Schedule

In the UI, choose the time checkboxes and click **Install** under **Automatic schedule**.

Default times:

- 08:10
- 11:45
- 15:45

The schedule uses the selected mode:

- Non-AI: no key needed.
- AI: requires `OPENAI_API_KEY` saved first.

You can also double-click `Install-Schedule.bat` for the legacy non-AI schedule.

Each run reads the last 24 hours from the time it starts.

Reports are saved into one file per day:

```text
reports\mail-report-YYYY-MM-DD.md
```

Raw JSON exports are also saved for debugging or AI summarization.

## Uninstall schedule

Double-click `Uninstall-Schedule.bat`.

## Notes

- The computer must be on and the user should be logged into Windows.
- If Outlook is closed, the script will try to start it. If Outlook prompts for a profile or password, the run may fail.
- The Markdown report is rule-based. For AI-quality summaries, feed the JSON export to Codex/ChatGPT/OpenAI API.
