# Learning Notes

Use this file for guided learning from the matching create-video work.

## Current Mode

- Create-video work happens in the other thread.
- This thread reviews artifacts and turns real failures into fixes.
- Do not use overnight learning output as trusted guidance.

## Review Template

```text
Finding:
Evidence:
Impact:
Fix:
Applies to:
```

## Findings

Finding:
Voice has too much dead air between sentences.

Evidence:
User feedback on 2026-05-25: "khoảng thời gian nghỉ giữa các câu thấy khá lâu".

Impact:
Long-form narration feels slow and loses flow, especially when the script is split into many short performance units.

Fix:
Reduced `story-emotional` and `wasteland-dark` pause values, made `wasteland-dark` the default voice style, and wired longform rendering to pass `--voice-style`.

Applies to:
voice generator
