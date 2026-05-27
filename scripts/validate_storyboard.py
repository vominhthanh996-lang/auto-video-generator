#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


VIETNAMESE_HINTS = (
    "\u0103\u00e2\u0111\u00ea\u00f4\u01a1\u01b0"
    "\u00e1\u00e0\u1ea3\u00e3\u1ea1\u1ea5\u1ea7\u1ea9\u1eab\u1ead"
    "\u1eaf\u1eb1\u1eb3\u1eb5\u1eb7\u00e9\u00e8\u1ebb\u1ebd\u1eb9"
    "\u1ebf\u1ec1\u1ec3\u1ec5\u1ec7\u00ed\u00ec\u1ec9\u0129\u1ecb"
    "\u00f3\u00f2\u1ecf\u00f5\u1ecd\u1ed1\u1ed3\u1ed5\u1ed7\u1ed9"
    "\u1edb\u1edd\u1edf\u1ee1\u1ee3\u00fa\u00f9\u1ee7\u0169\u1ee5"
    "\u1ee9\u1eeb\u1eed\u1eef\u1ef1\u00fd\u1ef3\u1ef7\u1ef9\u1ef5"
)


def resolve(base, value):
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def probe_duration(path):
    if shutil.which("ffprobe") is None:
        return None
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def text_problems(text, language):
    problems = []
    if "\ufffd" in text:
        problems.append("replacement-character")
    question_marks = text.count("?")
    if question_marks >= 12:
        problems.append(f"too-many-question-marks:{question_marks}")
    if language.startswith("vi"):
        letters = re.findall(r"[A-Za-z\u00c0-\u1ef9]", text)
        accented = sum(1 for char in text.lower() if char in VIETNAMESE_HINTS)
        if len(letters) >= 40 and accented == 0:
            problems.append("missing-vietnamese-diacritics")
    return problems


def main():
    parser = argparse.ArgumentParser(description="Validate storyboard text, image assets, and audio assets before rendering.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--stage", choices=["text", "voice", "assets", "all"], default="all")
    parser.add_argument("--min-audio-seconds", type=float, default=1.0)
    args = parser.parse_args()

    storyboard = args.storyboard.resolve()
    base = storyboard.parent
    config = json.loads(storyboard.read_text(encoding="utf-8-sig"))
    scenes = config.get("scenes") or []
    language = str(config.get("language") or "").lower()
    errors = []
    warnings = []

    if not scenes:
        errors.append("Storyboard has no scenes.")

    if args.stage in {"text", "all"}:
        for index, scene in enumerate(scenes, 1):
            text = scene.get("narration") or scene.get("subtitle") or scene.get("text") or ""
            if not text.strip():
                errors.append(f"Scene {index:03d}: missing narration text.")
                continue
            for problem in text_problems(text, language):
                errors.append(f"Scene {index:03d}: text encoding looks broken: {problem}.")

    if args.stage in {"voice", "assets", "all"}:
        for index, scene in enumerate(scenes, 1):
            audio = resolve(base, scene.get("audio"))
            if args.stage in {"assets", "all"}:
                image = resolve(base, scene.get("image"))
                if not image or not image.exists():
                    errors.append(f"Scene {index:03d}: missing image: {image}")
            if not audio or not audio.exists():
                errors.append(f"Scene {index:03d}: missing audio: {audio}")
            elif audio.stat().st_size < 1024:
                errors.append(f"Scene {index:03d}: audio file is too small: {audio}")
            else:
                duration = probe_duration(audio)
                if duration is not None and duration < args.min_audio_seconds:
                    errors.append(f"Scene {index:03d}: audio too short: {duration:.2f}s")
                elif duration is None:
                    warnings.append(f"Scene {index:03d}: could not probe audio duration.")

    result = {"storyboard": str(storyboard), "scenes": len(scenes), "errors": errors, "warnings": warnings}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
