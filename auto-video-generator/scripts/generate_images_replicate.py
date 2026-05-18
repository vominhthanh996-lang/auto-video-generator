#!/usr/bin/env python3
import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


API_BASE = "https://api.replicate.com/v1"


def token():
    value = os.environ.get("REPLICATE_API_TOKEN")
    if not value:
        raise SystemExit("REPLICATE_API_TOKEN is not set.")
    return value


def request_json(method, url, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token()}",
            "Content-Type": "application/json",
            "Prefer": "wait",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Replicate API error {exc.code}: {detail}") from exc


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


def normalize_output(output):
    if isinstance(output, str):
        return output
    if isinstance(output, list) and output:
        first = output[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return first.get("url") or first.get("image")
    if isinstance(output, dict):
        for key in ("url", "image", "output"):
            if output.get(key):
                return normalize_output(output[key])
    return None


def download(url, output):
    request = urllib.request.Request(url, headers={"User-Agent": "auto-video-generator/1.0"})
    with urllib.request.urlopen(request, timeout=180) as response:
        output.write_bytes(response.read())


def create_prediction(model, input_payload):
    owner, name = model.split("/", 1)
    url = f"{API_BASE}/models/{owner}/{name}/predictions"
    return request_json("POST", url, {"input": input_payload})


def wait_prediction(prediction, interval=2, timeout=300):
    deadline = time.time() + timeout
    while prediction.get("status") not in ("succeeded", "failed", "canceled"):
        if time.time() > deadline:
            raise SystemExit(f"Replicate prediction timed out: {prediction.get('id')}")
        time.sleep(interval)
        prediction = request_json("GET", prediction["urls"]["get"])
    if prediction.get("status") != "succeeded":
        raise SystemExit(f"Replicate prediction did not succeed: {json.dumps(prediction, indent=2)}")
    return prediction


def build_input(prompt, args):
    payload = {
        args.prompt_field: prompt,
    }
    if args.aspect_ratio:
        payload["aspect_ratio"] = args.aspect_ratio
    if args.output_format:
        payload["output_format"] = args.output_format
    if args.extra:
        payload.update(json.loads(args.extra))
    return payload


def main():
    parser = argparse.ArgumentParser(description="Generate storyboard images with Replicate.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--model", default="black-forest-labs/flux-schnell")
    parser.add_argument("--prompt-field", default="prompt")
    parser.add_argument("--aspect-ratio", default="9:16")
    parser.add_argument("--output-format", default="png")
    parser.add_argument("--extra", default="", help="JSON object merged into each model input.")
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
            image_path = assets_dir / f"scene-{index + 1:02d}.png"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        if image_path.exists() and not args.overwrite:
            scene["image"] = relpath(image_path, storyboard_dir)
            continue

        prompt = scene.get("image_prompt") or scene.get("visual") or scene.get("text") or scene.get("narration")
        if not prompt:
            raise SystemExit(f"Scene {index + 1} has no image prompt.")

        prediction = create_prediction(args.model, build_input(prompt, args))
        prediction = wait_prediction(prediction)
        output_url = normalize_output(prediction.get("output"))
        if not output_url:
            raise SystemExit(f"Could not find image URL in Replicate output: {json.dumps(prediction, indent=2)}")
        download(output_url, image_path)
        scene["image"] = relpath(image_path, storyboard_dir)

    storyboard_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"storyboard": str(storyboard_path), "scenes": len(scenes), "model": args.model}, indent=2))


if __name__ == "__main__":
    main()
