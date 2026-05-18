#!/usr/bin/env python3
import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


API_BASE = "https://gen.pollinations.ai"


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
    return scene.get("pollinations_prompt") or scene.get("image_prompt") or scene.get("visual") or scene.get("text") or scene.get("narration")


def download_image(prompt, output, args):
    query = {}
    key = os.environ.get("POLLINATIONS_API_KEY")
    if key:
        query["key"] = key
    if args.model:
        query["model"] = args.model
    if args.width:
        query["width"] = str(args.width)
    if args.height:
        query["height"] = str(args.height)
    if args.seed:
        query["seed"] = str(args.seed)
    if args.extra:
        query.update(json.loads(args.extra))

    path = urllib.parse.quote(prompt, safe="")
    url = f"{API_BASE}/image/{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(url, headers={"User-Agent": "auto-video-generator/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Pollinations API error {exc.code}: {detail}") from exc
    if "image" not in content_type.lower() and not data.startswith((b"\xff\xd8", b"\x89PNG")):
        raise SystemExit(f"Pollinations did not return an image. Content-Type: {content_type}")
    output.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description="Generate storyboard images with Pollinations AI.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--model", default="flux")
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=1920)
    parser.add_argument("--seed", default="")
    parser.add_argument("--output-format", default="jpg", choices=["jpg", "png"])
    parser.add_argument("--extra", default="", help="JSON object merged into query params.")
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
        download_image(prompt, image_path, args)
        scene["image"] = relpath(image_path, storyboard_dir)

    storyboard_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"storyboard": str(storyboard_path), "scenes": len(scenes), "model": args.model}, indent=2))


if __name__ == "__main__":
    main()
