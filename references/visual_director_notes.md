# Visual Director Notes

Use this guide for story-to-video image generation.

## Goal

Images must match the narration first, then look cinematic. A beautiful image that does not match the audio breaks retention.

## Core Rules

- Every scene needs concrete story beats, not only a mood prompt.
- Each image prompt should include `MUST SHOW`.
- Preserve continuity anchors across nearby scenes.
- Keep character identity, costume, wounds, props, and location stable unless the story changes them.
- Action must advance logically from the previous image.
- Do not jump randomly between unrelated locations.
- Shot type should support the beat: establishing, medium action, close detail, hiding POV, etc.

## Continuity Anchors

Reuse 2-6 anchors across adjacent scenes:

- main character appearance
- current location
- key prop
- recent action state
- threat position
- visible injury or costume state

Examples:

- `Lam Tich`
- `dirty torn coat`
- `radioactive junkyard`
- `overturned truck`
- `collapsed concrete wall`
- `mutated two-jawed dogs`
- `sealed can of meat`

## Story Beat Prompt Contract

Each visual prompt should include:

- continuity from previous scene
- characters
- setting
- action
- important props
- shot type
- mood
- anti-generic instruction

## Review Workflow

Before generating all images:

1. Create/update storyboard.
2. Run visual audit.
3. Generate 3-5 sample images.
4. Open contact sheet and compare each image to `MUST SHOW`.
5. Only then run the full batch.

For long videos, do not judge only by beauty. Judge by:

- Does the image show the exact event in the narration?
- Does it inherit the previous scene?
- Does the character look like the same person?
- Are required props visible?
- Is the action readable without reading the prompt?
