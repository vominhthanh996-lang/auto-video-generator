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
- Preserve a continuous narrator identity across the whole scene.
- Smooth rate/pitch jumps between adjacent narration units.
- Use a slower hook cadence at the beginning of a scene.
- Use a darker release cadence near the end of a reflective scene.
- Use silence as punctuation, especially at scene breaks and cliffhangers.
- Do not over-pause after every comma; that sounds artificial.
- Keep normal sentence gaps tight. Heavy emotion should come from pitch, rate, and delivery, not long silence after every sentence.
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

## Character Archetypes

Character differentiation should stay subtle. The goal is not cartoon acting; the listener should recognize personality through rhythm and restraint.

- `honest`: slightly slower, open, sincere, plain cadence.
- `righteous`: steady, firm, grounded, less decorative.
- `evil`: lower, slower, heavier pauses, controlled threat.
- `hypocrite`: polite and smooth on the surface, controlled pauses, slightly too neat.
- `flattering`: faster, brighter, eager, shorter pauses.
- `spoiled`: softer and slightly higher, a little stretched, but not childish unless the text says so.
- `cold`: lower, slower, distant, fewer emotional spikes.
- `afraid`: faster and higher, shorter pauses, breathless tension.

Avoid overacting:

- Do not make all female dialogue squeaky.
- Do not make villains obviously monstrous unless the story already reveals that.
- Do not reveal a hidden hypocrite too early through an exaggerated voice.
- Keep narration voice stable; only dialogue and strongly tagged character moments should shift.

## Continuous Narrator Flow

The narrator should feel like one person guiding the listener through the whole video.

- First line of a scene: slightly slower, inviting, clear.
- Middle narration: steady and listenable, with only small emotional waves.
- End of scene: slightly slower or heavier if reflective, tighter if action continues.
- Avoid sudden jumps in pitch/rate between adjacent narration units.
- Dialogue can depart from the narrator lane, then return smoothly.
- If many consecutive units are all intense, preserve one stable danger pace instead of escalating every sentence.

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

## Character Memory Hook

For part 2 onward, a project can include:

`character_voice_bible.json`

The generator will automatically use it when running `run_story_pipeline.py`.

Each character can have:

- `gender`
- `aliases`
- `traits`
- `voice_note`

This matters because a long story should not rediscover a character's voice from scratch every scene. A cold male survivor should stay cold across chapters unless the story explicitly changes him.

Feedback can target one character or one trait:

```powershell
python scripts\record_voice_feedback.py --character "Tần Dã" --feedback not-cold-enough
python scripts\record_voice_feedback.py --trait hypocrite --feedback too-fake
```

The generator reads these deltas from `voice_learning.json` and applies them only when that character or trait is detected.
