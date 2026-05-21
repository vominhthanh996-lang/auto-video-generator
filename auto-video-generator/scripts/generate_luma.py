#!/usr/bin/env python3
import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


API_BASE = "https://api.lumalabs.ai/dream-machine/v1"


def api_key():
    value = os.environ.get("LUMAAI_API_KEY")
    if not value:
        raise SystemExit("LUMAAI_API_KEY is not set.")
    return value


def request_json(method, path_or_url, payload=None):
    url = path_or_url if path_or_url.startswith("http") else f"{API_BASE}{path_or_url}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "auto-video-generator/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Luma API error {exc.code}: {detail}") from exc


def relpath(path, base):
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def get_nested(obj, *keys):
    current = obj
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def video_url(generation):
    return (
        get_nested(generation, "assets", "video")
        or get_nested(generation, "asset", "video")
        or generation.get("video")
        or generation.get("url")
    )


def wait_generation(generation_id, timeout=1200, interval=8):
    deadline = time.time() + timeout
    while True:
        generation = request_json("GET", f"/generations/{generation_id}")
        state = (generation.get("state") or generation.get("status") or "").lower()
        if state in ("completed", "succeeded", "success"):
            return generation
        if state in ("failed", "canceled", "cancelled"):
            raise SystemExit(f"Luma generation ended with state {state}: {json.dumps(generation, indent=2)}")
        if time.time() > deadline:
            raise SystemExit(f"Luma generation timed out: {generation_id}")
        time.sleep(interval)


def download(url, output):
    request = urllib.request.Request(url, headers={"User-Agent": "auto-video-generator/1.0"})
    with urllib.request.urlopen(request, timeout=300) as response:
        output.write_bytes(response.read())


def scene_prompt(scene):
    return scene.get("luma_prompt") or scene.get("video_prompt") or scene.get("image_prompt") or scene.get("visual") or scene.get("text") or scene.get("narration")


def main():
    parser = argparse.ArgumentParser(description="Generate storyboard videos with Luma Dream Machine.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--model", default="ray-flash-2", help="ray-flash-2 or ray-2")
    parser.add_argument("--resolution", default="720p", help="540p, 720p, 1080, or 4k")
    parser.add_argument("--duration", default="5s", help="Usually 5s or 9s depending on model/account.")
    parser.add_argument("--aspect-ratio", default="9:16")
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    storyboard_path = args.storyboard.resolve()
    storyboard_dir = storyboard_path.parent
    output_dir = storyboard_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    config = json.loads(storyboard_path.read_text(encoding="utf-8-sig"))
    scenes = config.get("scenes") or []
    if not scenes:
        raise SystemExit("Storyboard has no scenes.")

    videos = []
    for index, scene in enumerate(scenes):
        output_path = output_dir / f"luma-scene-{index + 1:02d}.mp4"
        if output_path.exists() and not args.overwrite:
            scene["luma_video"] = relpath(output_path, storyboard_dir)
            videos.append(scene["luma_video"])
            continue
        prompt = scene_prompt(scene)
        if not prompt:
            raise SystemExit(f"Scene {index + 1} has no prompt.")
        payload = {
            "prompt": prompt,
            "model": args.model,
            "resolution": args.resolution,
            "duration": args.duration,
            "aspect_ratio": args.aspect_ratio,
        }
        generation = request_json("POST", "/generations", payload)
        generation_id = generation.get("id")
        if not generation_id:
            raise SystemExit(f"Luma create returned no id: {json.dumps(generation, indent=2)}")
        generation = wait_generation(generation_id, timeout=args.timeout)
        url = video_url(generation)
        if not url:
            raise SystemExit(f"Luma completed generation has no video URL: {json.dumps(generation, indent=2)}")
        download(url, output_path)
        scene["luma_generation_id"] = generation_id
        scene["luma_video"] = relpath(output_path, storyboard_dir)
        videos.append(scene["luma_video"])

    config["luma_videos"] = videos
    storyboard_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"storyboard": str(storyboard_path), "scenes": len(scenes), "model": args.model}, indent=2))


if __name__ == "__main__":
    main()
