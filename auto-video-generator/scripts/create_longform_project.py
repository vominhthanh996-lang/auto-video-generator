#!/usr/bin/env python3
import argparse
import json
import math
import re
from pathlib import Path


ASPECTS = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
}


def slugify(value):
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return value or "longform-video"


def default_scene(chapter, scene, duration, style, language):
    scene_id = f"ch{chapter:02d}-sc{scene:03d}"
    return {
        "id": scene_id,
        "duration": duration,
        "image_prompt": f"{style}. Scene placeholder {scene_id}. Replace with a specific visual prompt. No text, no watermark.",
        "narration": f"[{language}] Replace with narration for {scene_id}.",
        "text": "",
        "subtitle": f"[{language}] Replace with narration for {scene_id}.",
    }


def chapter_storyboard(title, chapter, scene_count, scene_duration, aspect, fps, style, language):
    width, height = ASPECTS.get(aspect, ASPECTS["9:16"])
    return {
        "title": f"{title} - Chapter {chapter:02d}",
        "chapter": chapter,
        "width": width,
        "height": height,
        "fps": fps,
        "background_color": "#111111",
        "font": "Arial",
        "scenes": [
            default_scene(chapter, scene + 1, scene_duration, style, language)
            for scene in range(scene_count)
        ],
        "music": None,
    }


def main():
    parser = argparse.ArgumentParser(description="Create a long-form video project scaffold.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--root", default=r"E:\ThanhMV\video-projects")
    parser.add_argument("--minutes", type=int, default=30)
    parser.add_argument("--chapter-minutes", type=int, default=5)
    parser.add_argument("--scene-duration", type=int, default=12)
    parser.add_argument("--aspect", default="9:16", choices=sorted(ASPECTS))
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--language", default="Vietnamese")
    parser.add_argument("--style", default="cinematic realistic story illustration, consistent characters, dramatic lighting")
    args = parser.parse_args()

    if args.minutes < 1:
        raise SystemExit("--minutes must be >= 1")
    if args.chapter_minutes < 1:
        raise SystemExit("--chapter-minutes must be >= 1")
    if args.scene_duration < 3:
        raise SystemExit("--scene-duration must be >= 3")

    root = Path(args.root).resolve()
    project_dir = root / slugify(args.title)
    project_dir.mkdir(parents=True, exist_ok=True)

    total_seconds = args.minutes * 60
    chapter_seconds = args.chapter_minutes * 60
    chapter_count = math.ceil(total_seconds / chapter_seconds)

    chapters = []
    for chapter in range(1, chapter_count + 1):
        remaining = total_seconds - ((chapter - 1) * chapter_seconds)
        this_chapter_seconds = min(chapter_seconds, remaining)
        scene_count = math.ceil(this_chapter_seconds / args.scene_duration)
        chapter_dir = project_dir / f"chapter-{chapter:02d}"
        (chapter_dir / "assets").mkdir(parents=True, exist_ok=True)
        (chapter_dir / "output").mkdir(parents=True, exist_ok=True)
        storyboard = chapter_storyboard(
            args.title,
            chapter,
            scene_count,
            args.scene_duration,
            args.aspect,
            args.fps,
            args.style,
            args.language,
        )
        storyboard_path = chapter_dir / "storyboard.json"
        storyboard_path.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
        chapters.append(
            {
                "chapter": chapter,
                "dir": chapter_dir.as_posix(),
                "storyboard": storyboard_path.as_posix(),
                "output": (chapter_dir / "output" / f"chapter-{chapter:02d}.mp4").as_posix(),
                "target_seconds": this_chapter_seconds,
                "scene_count": scene_count,
            }
        )

    manifest = {
        "title": args.title,
        "target_minutes": args.minutes,
        "chapter_minutes": args.chapter_minutes,
        "scene_duration": args.scene_duration,
        "aspect": args.aspect,
        "fps": args.fps,
        "language": args.language,
        "style": args.style,
        "chapters": chapters,
        "final_output": (project_dir / "final" / "final.mp4").as_posix(),
    }
    (project_dir / "final").mkdir(exist_ok=True)
    manifest_path = project_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"project": project_dir.as_posix(), "manifest": manifest_path.as_posix(), "chapters": chapter_count}, indent=2))


if __name__ == "__main__":
    main()
