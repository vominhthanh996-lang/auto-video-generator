# Voice Director Notes

These notes guide narration generation for Vietnamese long-form story videos.

## Current Target

- Genre: wasteland apocalypse, survival, transmigration, slow-burn tension.
- Voice shape: calm, dark, intimate, emotionally heavy, not theatrical.
- Preferred preset: `wasteland-dark`.
- Keep part 1 assets untouched unless the user explicitly asks to regenerate them.

## Learned Pacing Rules

- Do not read every sentence at one fixed speed.
- Keep a stable base pace, then adjust subtly by context.
- Use silence as punctuation, especially at scene breaks and cliffhangers.
- Do not over-pause after every comma; that sounds artificial.
- Action/danger can be a little tighter and faster.
- Inner monologue should slow down and soften.
- Dialogue needs a separate rhythm from narration.
- Reveals should land with a small pause after them.
- Lists of supplies/actions should move faster so they do not feel sleepy.
- Scene breaks need an obvious pause because the visual text cue disappears in audio.

## Detector Map

- `danger`: threats, blood, mutant beasts, pursuit, weapons.
- `soft`: loneliness, pain, exhaustion, survival reflection.
- `inner`: thoughts, memories, self-awareness, emotional reasoning.
- `reveal`: sudden turns, discoveries, "không phải", "đột nhiên", "thật ra".
- `list`: inventory, repeated actions, preparation sequences.
- `dialogue`: quoted or dash-prefixed speech.
- `cliffhanger`: short punch lines, questions, exclamations, ellipses.

## Future Tool Hook

When an interactive voice-review module is added, it should write feedback to:

`E:\ThanhMV\auto-video-generator\config\voice_learning.json`

Recommended feedback labels:

- `too-fast`
- `too-slow`
- `too-flat`
- `too-dramatic`
- `good`

The generator reads that file and applies small deltas to rate and pause timing.
