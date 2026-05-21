#!/usr/bin/env python3
import argparse
import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path


API_BASE = "https://api.openai.com/v1"


def api_key():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("OPENAI_API_KEY is not set.")
    return key


def post_json(path, payload, accept=None):
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key()}",
        "Content-Type": "application/json",
    }
    if accept:
        headers["Accept"] = accept
    request = urllib.request.Request(f"{API_BASE}{path}", data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.read(), response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"OpenAI API error {exc.code}: {detail}") from exc


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


def generate_image(scene, index, storyboard_dir, assets_dir, model, size, quality):
    image_path = resolve(storyboard_dir, scene["image"]) if scene.get("image") else assets_dir / f"scene-{index + 1:02d}.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    if image_path.exists():
        return image_path

    prompt = scene.get("image_prompt") or scene.get("visual") or scene.get("text") or scene.get("narration")
    if not prompt:
        raise SystemExit(f"Scene {index + 1} has no image prompt.")

    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
    }
    raw, _ = post_json("/images/generations", payload)
    data = json.loads(raw.decode("utf-8"))
    b64 = data["data"][0]["b64_json"]
    image_path.write_bytes(base64.b64decode(b64))
    return image_path


def generate_audio(scene, index, storyboard_dir, assets_dir, model, voice, instructions):
    audio_path = resolve(storyboard_dir, scene["audio"]) if scene.get("audio") else assets_dir / f"scene-{index + 1:02d}.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    if audio_path.exists():
        return audio_path

    text = scene.get("narration") or scene.get("subtitle") or scene.get("text")
    if not text:
        raise SystemExit(f"Scene {index + 1} has no narration text.")

    payload = {
        "model": model,
        "input": text,
        "voice": voice,
        "instructions": instructions,
        "response_format": "wav",
    }
    raw, _ = post_json("/audio/speech", payload, accept="audio/wav")
    audio_path.write_bytes(raw)
    return audio_path


def main():
    parser = argparse.ArgumentParser(description="Generate storyboard images and narration with OpenAI.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--image-model", default="gpt-image-2")
    parser.add_argument("--image-size", default="1024x1536")
    parser.add_argument("--image-quality", default="low")
    parser.add_argument("--tts-model", default="gpt-4o-mini-tts")
    parser.add_argument("--voice", default="coral")
    parser.add_argument("--voice-instructions", default="Speak clearly with warm, natural pacing.")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    storyboard_path = args.storyboard.resolve()
    storyboard_dir = storyboard_path.parent
    assets_dir = storyboard_dir / "assets"
    config = json.loads(storyboard_path.read_text(encoding="utf-8-sig"))
    scenes = config.get("scenes") or []
    if not scenes:
        raise SystemExit("Storyboard has no scenes.")

    for index, scene in enumerate(scenes):
        if args.overwrite:
            if scene.get("image"):
                image_path = resolve(storyboard_dir, scene["image"])
                if image_path.exists():
                    image_path.unlink()
            if scene.get("audio"):
                audio_path = resolve(storyboard_dir, scene["audio"])
                if audio_path.exists():
                    audio_path.unlink()
        image = generate_image(scene, index, storyboard_dir, assets_dir, args.image_model, args.image_size, args.image_quality)
        audio = generate_audio(scene, index, storyboard_dir, assets_dir, args.tts_model, args.voice, args.voice_instructions)
        scene["image"] = relpath(image, storyboard_dir)
        scene["audio"] = relpath(audio, storyboard_dir)
        scene.setdefault("subtitle", scene.get("narration", ""))

    storyboard_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"storyboard": str(storyboard_path), "scenes": len(scenes)}, indent=2))


if __name__ == "__main__":
    main()
