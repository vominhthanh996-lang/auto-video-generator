#!/usr/bin/env python3
import argparse
import asyncio
import json
import sys
import subprocess
import tempfile
from pathlib import Path


EXTRA_PACKAGES = Path(r"E:\ThanhMV\python-packages")
if EXTRA_PACKAGES.exists():
    sys.path.insert(0, str(EXTRA_PACKAGES))

import edge_tts


VOICE_PRESETS = {
    "vi-female": "vi-VN-HoaiMyNeural",
    "vi-male": "vi-VN-NamMinhNeural",
    "en-female": "en-US-JennyNeural",
    "en-male": "en-US-GuyNeural",
}


def resolve(base, value):
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def relpath(path, base):
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


async def synthesize(text, output, voice, rate, pitch):
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(output))


def split_text(text, max_chars=650):
    pieces = []
    current = []
    size = 0
    for part in text.replace("\n", " ").split(". "):
        part = part.strip()
        if not part:
            continue
        if not part.endswith((".", "?", "!", ":")):
            part += "."
        if current and size + len(part) > max_chars:
            pieces.append(" ".join(current))
            current = [part]
            size = len(part)
        else:
            current.append(part)
            size += len(part)
    if current:
        pieces.append(" ".join(current))
    return pieces or [text]


async def synthesize_resilient(text, output, voice, rate, pitch):
    last_error = None
    for _ in range(5):
        try:
            await synthesize(text, output, voice, rate, pitch)
            return
        except Exception as exc:
            last_error = exc
            if output.exists() and output.stat().st_size == 0:
                output.unlink()
            await asyncio.sleep(2)

    parts = split_text(text)
    if len(parts) == 1:
        words = text.split()
        if len(words) > 8:
            midpoint = len(words) // 2
            parts = [" ".join(words[:midpoint]), " ".join(words[midpoint:])]
        else:
            raise last_error

    with tempfile.TemporaryDirectory(prefix="edge-tts-") as temp_name:
        temp_dir = Path(temp_name)
        chunk_paths = []
        for index, part in enumerate(parts, 1):
            chunk_path = temp_dir / f"chunk-{index:03d}.mp3"
            await synthesize(part, chunk_path, voice, rate, pitch)
            chunk_paths.append(chunk_path)
        list_path = temp_dir / "concat.txt"
        list_path.write_text("".join(f"file '{path.as_posix()}'\n" for path in chunk_paths), encoding="utf-8")
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(output)], check=True)


async def main_async(args):
    storyboard_path = args.storyboard.resolve()
    storyboard_dir = storyboard_path.parent
    assets_dir = storyboard_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    config = json.loads(storyboard_path.read_text(encoding="utf-8-sig"))
    scenes = config.get("scenes") or []
    if not scenes:
        raise SystemExit("Storyboard has no scenes.")

    subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent / "validate_storyboard.py"), "--storyboard", str(storyboard_path), "--stage", "text"],
        check=True,
    )

    voice = VOICE_PRESETS.get(args.voice, args.voice)
    start_index = max(0, args.start_scene - 1)
    end_index = args.end_scene if args.end_scene else len(scenes)
    end_index = min(len(scenes), end_index)
    for index, scene in enumerate(scenes[start_index:end_index], start=start_index):
        text = scene.get("narration") or scene.get("subtitle") or scene.get("text")
        if not text:
            raise SystemExit(f"Scene {index + 1} has no narration/subtitle/text.")

        if scene.get("audio"):
            audio_path = resolve(storyboard_dir, scene["audio"])
        else:
            audio_path = assets_dir / f"scene-{index + 1:02d}.mp3"
        audio_path.parent.mkdir(parents=True, exist_ok=True)

        needs_audio = not audio_path.exists() or audio_path.stat().st_size < 1024 or args.overwrite
        if needs_audio:
            print(f"Generating voice scene {index + 1}/{len(scenes)}: {audio_path}", flush=True)
            await synthesize_resilient(text, audio_path, voice, args.rate, args.pitch)

        scene["audio"] = relpath(audio_path, storyboard_dir)
        scene.setdefault("subtitle", text)

    storyboard_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent / "validate_storyboard.py"), "--storyboard", str(storyboard_path), "--stage", "assets"],
        check=True,
    )
    print(json.dumps({"storyboard": str(storyboard_path), "scenes": len(scenes), "voice": voice}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Generate narration with Microsoft Edge TTS.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--voice", default="vi-female", help="Preset vi-female, vi-male, en-female, en-male, or full Edge voice name.")
    parser.add_argument("--rate", default="+0%")
    parser.add_argument("--pitch", default="+0Hz")
    parser.add_argument("--start-scene", type=int, default=1)
    parser.add_argument("--end-scene", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
