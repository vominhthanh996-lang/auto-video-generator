#!/usr/bin/env python3
import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path


API_BASE = "https://api.stability.ai"


RATIO_TO_SIZE = {
    "9:16": (768, 1344),
    "16:9": (1344, 768),
    "1:1": (1024, 1024),
    "4:3": (1152, 896),
    "3:4": (896, 1152),
}


def api_key():
    value = os.environ.get("STABILITY_API_KEY")
    if not value:
        raise SystemExit("STABILITY_API_KEY is not set.")
    return value


def multipart_body(fields, boundary):
    chunks = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks)


def post_multipart(path, fields, accept="image/*"):
    boundary = "----auto-video-generator-stability"
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        data=multipart_body(fields, boundary),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Accept": accept,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "auto-video-generator/1.0",
            "Stability-Client-ID": "auto-video-generator",
            "Stability-Client-Version": "1.0.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            return response.read(), response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Stability API error {exc.code}: {detail}") from exc


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


def scene_prompt(scene):
    return scene.get("stability_prompt") or scene.get("image_prompt") or scene.get("visual") or scene.get("text") or scene.get("narration")


def size_for_ratio(ratio):
    return RATIO_TO_SIZE.get(ratio, RATIO_TO_SIZE["9:16"])


def generate_core(args, prompt, output):
    fields = {
        "prompt": prompt,
        "output_format": args.output_format,
    }
    if args.aspect_ratio:
        fields["aspect_ratio"] = args.aspect_ratio
    if args.negative_prompt:
        fields["negative_prompt"] = args.negative_prompt
    if args.seed:
        fields["seed"] = args.seed
    raw, _ = post_multipart("/v2beta/stable-image/generate/core", fields)
    output.write_bytes(raw)


def generate_sdxl(args, prompt, output):
    width, height = size_for_ratio(args.aspect_ratio)
    payload = {
        "text_prompts": [{"text": prompt}],
        "cfg_scale": args.cfg_scale,
        "height": height,
        "width": width,
        "samples": 1,
        "steps": args.steps,
    }
    request = urllib.request.Request(
        f"{API_BASE}/v1/generation/{args.engine}/text-to-image",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "auto-video-generator/1.0",
            "Stability-Client-ID": "auto-video-generator",
            "Stability-Client-Version": "1.0.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Stability API error {exc.code}: {detail}") from exc

    import base64

    artifact = data["artifacts"][0]
    output.write_bytes(base64.b64decode(artifact["base64"]))


def main():
    parser = argparse.ArgumentParser(description="Generate storyboard images with Stability AI.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--api", choices=["core", "sdxl"], default="core")
    parser.add_argument("--engine", default="stable-diffusion-xl-1024-v1-0")
    parser.add_argument("--aspect-ratio", default="9:16")
    parser.add_argument("--output-format", default="png")
    parser.add_argument("--negative-prompt", default="")
    parser.add_argument("--cfg-scale", type=float, default=7)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--seed", default="")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    storyboard_path = args.storyboard.resolve()
    storyboard_dir = storyboard_path.parent
    assets_dir = storyboard_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    config = json.loads(storyboard_path.read_text(encoding="utf-8-sig"))
    scenes = config.get("scenes") or []
    if not scenes:
        raise SystemExit("Storyboard has no scenes.")

    for index, scene in enumerate(scenes):
        image_path = resolve(storyboard_dir, scene["image"]) if scene.get("image") else assets_dir / f"scene-{index + 1:02d}.{args.output_format}"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        if image_path.exists() and not args.overwrite:
            scene["image"] = relpath(image_path, storyboard_dir)
            continue
        prompt = scene_prompt(scene)
        if not prompt:
            raise SystemExit(f"Scene {index + 1} has no prompt.")
        if args.api == "core":
            generate_core(args, prompt, image_path)
        else:
            generate_sdxl(args, prompt, image_path)
        scene["image"] = relpath(image_path, storyboard_dir)

    storyboard_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"storyboard": str(storyboard_path), "scenes": len(scenes), "api": args.api}, indent=2))


if __name__ == "__main__":
    main()
