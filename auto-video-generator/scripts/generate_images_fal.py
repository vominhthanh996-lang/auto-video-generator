#!/usr/bin/env python3
import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path


FAL_RUN_BASE = "https://fal.run"


IMAGE_SIZE_BY_ASPECT = {
    "9:16": "portrait_16_9",
    "16:9": "landscape_16_9",
    "1:1": "square_hd",
    "4:3": "landscape_4_3",
    "3:4": "portrait_4_3",
}


def fal_key():
    value = os.environ.get("FAL_KEY")
    if not value:
        raise SystemExit("FAL_KEY is not set.")
    return value


def post_fal(endpoint, payload):
    url = f"{FAL_RUN_BASE}/{endpoint.strip('/')}"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Key {fal_key()}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"fal.ai API error {exc.code}: {detail}") from exc


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


def first_url(output):
    if isinstance(output, str):
        return output
    if isinstance(output, list) and output:
        return first_url(output[0])
    if isinstance(output, dict):
        if output.get("url"):
            return output["url"]
        for key in ("images", "image", "output"):
            if key in output:
                return first_url(output[key])
    return None


def download(url, output):
    request = urllib.request.Request(url, headers={"User-Agent": "auto-video-generator/1.0"})
    with urllib.request.urlopen(request, timeout=180) as response:
        output.write_bytes(response.read())


def build_payload(prompt, args):
    payload = {
        "prompt": prompt,
        "num_images": 1,
        "output_format": args.output_format,
    }
    if args.image_size:
        payload["image_size"] = args.image_size
    elif args.aspect_ratio:
        payload["image_size"] = IMAGE_SIZE_BY_ASPECT.get(args.aspect_ratio, args.aspect_ratio)
    if args.num_inference_steps:
        payload["num_inference_steps"] = args.num_inference_steps
    if args.extra:
        payload.update(json.loads(args.extra))
    return payload


def main():
    parser = argparse.ArgumentParser(description="Generate storyboard images with fal.ai.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--endpoint", default="fal-ai/flux/schnell")
    parser.add_argument("--aspect-ratio", default="9:16")
    parser.add_argument("--image-size", default="")
    parser.add_argument("--output-format", default="png")
    parser.add_argument("--num-inference-steps", type=int, default=4)
    parser.add_argument("--extra", default="", help="JSON object merged into each fal input payload.")
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
        if scene.get("image"):
            image_path = resolve(storyboard_dir, scene["image"])
        else:
            image_path = assets_dir / f"scene-{index + 1:02d}.{args.output_format}"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        if image_path.exists() and not args.overwrite:
            scene["image"] = relpath(image_path, storyboard_dir)
            continue

        prompt = scene.get("image_prompt") or scene.get("visual") or scene.get("text") or scene.get("narration")
        if not prompt:
            raise SystemExit(f"Scene {index + 1} has no image prompt.")

        result = post_fal(args.endpoint, build_payload(prompt, args))
        image_url = first_url(result)
        if not image_url:
            raise SystemExit(f"Could not find image URL in fal.ai output: {json.dumps(result, indent=2)}")
        download(image_url, image_path)
        scene["image"] = relpath(image_path, storyboard_dir)

    storyboard_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"storyboard": str(storyboard_path), "scenes": len(scenes), "endpoint": args.endpoint}, indent=2))


if __name__ == "__main__":
    main()
