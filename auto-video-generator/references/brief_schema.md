# Storyboard Schema

Create a JSON file with this shape:

```json
{
  "title": "Video title",
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "background_color": "#111111",
  "font": "Arial",
  "scenes": [
    {
      "id": "scene-01",
      "duration": 5,
      "image": "assets/scene-01.png",
      "audio": "assets/scene-01.wav",
      "narration": "Voiceover text for this scene.",
      "text": "Short on-screen text",
      "subtitle": "Voiceover text for subtitles."
    }
  ],
  "music": null
}
```

Fields:

- `width`, `height`: output resolution. Use `1080x1920` for 9:16, `1080x1080` for 1:1, and `1920x1080` for 16:9.
- `fps`: use 30 unless the user asks otherwise.
- `scenes[].duration`: seconds. Keep this close to the narration length.
- `scenes[].image`: local path to the generated scene image.
- `scenes[].audio`: local path to the generated narration audio for the scene.
- `scenes[].text`: short visual headline burned into the video.
- `scenes[].subtitle`: subtitle text shown near the bottom.
- `music`: optional local music path. Keep narration louder than music.

## Long-Form Manifest

Long-form projects use a `manifest.json` file that points to chapter storyboards.

```json
{
  "title": "Story title",
  "target_minutes": 30,
  "chapter_minutes": 5,
  "scene_duration": 12,
  "aspect": "9:16",
  "fps": 30,
  "language": "Vietnamese",
  "style": "cinematic realistic story illustration",
  "chapters": [
    {
      "chapter": 1,
      "storyboard": "chapter-01/storyboard.json",
      "output": "chapter-01/output/chapter-01.mp4",
      "target_seconds": 300,
      "scene_count": 25
    }
  ],
  "final_output": "final/final.mp4"
}
```

Use `scripts/create_longform_project.py` to create this structure. Edit each chapter storyboard with real narration and prompts before rendering.
