#!/usr/bin/env python3
import argparse
import asyncio
import json
import sys
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


async def main_async(args):
    storyboard_path = args.storyboard.resolve()
    storyboard_dir = storyboard_path.parent
    assets_dir = storyboard_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    config = json.loads(storyboard_path.read_text(encoding="utf-8-sig"))
    scenes = config.get("scenes") or []
    if not scenes:
        raise SystemExit("Storyboard has no scenes.")

    voice = VOICE_PRESETS.get(args.voice, args.voice)
    for index, scene in enumerate(scenes):
        text = scene.get("narration") or scene.get("subtitle") or scene.get("text")
        if not text:
            raise SystemExit(f"Scene {index + 1} has no narration/subtitle/text.")

        if scene.get("audio"):
            audio_path = resolve(storyboard_dir, scene["audio"])
        else:
            audio_path = assets_dir / f"scene-{index + 1:02d}.mp3"
        audio_path.parent.mkdir(parents=True, exist_ok=True)

        if not audio_path.exists() or args.overwrite:
            await synthesize(text, audio_path, voice, args.rate, args.pitch)

        scene["audio"] = relpath(audio_path, storyboard_dir)
        scene.setdefault("subtitle", text)

    storyboard_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"storyboard": str(storyboard_path), "scenes": len(scenes), "voice": voice}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Generate narration with Microsoft Edge TTS.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--voice", default="vi-female", help="Preset vi-female, vi-male, en-female, en-male, or full Edge voice name.")
    parser.add_argument("--rate", default="+0%")
    parser.add_argument("--pitch", default="+0Hz")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
