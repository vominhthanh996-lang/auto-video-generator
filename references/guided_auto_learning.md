# Guided Auto Learning

Use this workflow when one thread is creating or rendering a video and another thread is used to improve the pipeline.

## Why

The old overnight learning runner is too broad for production decisions. It can collect generic links, repeat old ideas, or append lessons that have not been checked against a real video output. Treat it as research only, not as a source of truth.

## Roles

- Create-video thread: builds storyboard, assets, voice, subtitles, and final MP4.
- Learning thread: reviews real artifacts, identifies failures, writes fixes or action items, and updates reusable notes only after evidence exists.

## Evidence First

Before changing pipeline logic, collect at least one concrete artifact:

- `storyboard.json`
- `voice-plan.json`
- contact sheet
- rendered MP4
- sample images
- user feedback about a specific scene

Do not promote a rule because a search result says it. Promote it only when it explains a real failure or improves a real sample.

## Review Loop

1. Identify the project folder being rendered.
2. Read `storyboard.json`, `voice-plan.json`, and any bible files.
3. Compare 3-5 representative scenes against the generated image/audio.
4. Classify failures:
   - text/storyboard issue
   - voice pacing or character-lane issue
   - image prompt issue
   - continuity issue
   - render/subtitle/layout issue
   - packaging/title/thumbnail issue
5. Write a short finding with evidence.
6. Apply the smallest useful fix:
   - update project bible or storyboard for project-specific fixes;
   - update scripts only for repeatable pipeline bugs;
   - update director notes only for reusable rules.

## What To Avoid

- Do not auto-append learning logs every 30 minutes.
- Do not commit generic lessons without checking a real artifact.
- Do not overwrite source assets from a previous part unless explicitly requested.
- Do not treat "cinematic" as success if the image misses the narration beat.
- Do not let one genre's lessons become global defaults for every story.

## Output Format For This Thread

Use this structure when giving feedback:

```text
Finding:
Evidence:
Impact:
Fix:
Applies to:
```

`Applies to` should be one of: current project only, story series, voice generator, image generator, renderer, documentation.
