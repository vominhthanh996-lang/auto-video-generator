#!/usr/bin/env python3
import argparse
import base64
import json
import mimetypes
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


API_BASE = "https://api.dev.runwayml.com/v1"
API_VERSION = "2024-11-06"


def api_key():
    value = os.environ.get("RUNWAYML_API_SECRET")
    if not value:
        raise SystemExit("RUNWAYML_API_SECRET is not set.")
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
            "Content-Type": "application/json",
            "X-Runway-Version": API_VERSION,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Runway API error {exc.code}: {detail}") from exc


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


def data_uri(path):
    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    encoded = base64.b64encode(Path(path).read_bytes()).decode("utf-8")
    return f"data:{content_type};base64,{encoded}"


def first_output_url(task):
    output = task.get("output")
    if isinstance(output, str):
        return output
    if isinstance(output, list) and output:
        return output[0]
    return None


def wait_task(task_id, timeout=900, interval=5):
    deadline = time.time() + timeout
    while True:
        task = request_json("GET", f"/tasks/{task_id}")
        status = task.get("status")
        if status == "SUCCEEDED":
            return task
        if status in ("FAILED", "CANCELED"):
            raise SystemExit(f"Runway task ended with status {status}: {json.dumps(task, indent=2)}")
        if time.time() > deadline:
            raise SystemExit(f"Runway task timed out: {task_id}")
        time.sleep(interval)


def download(url, output):
    request = urllib.request.Request(url, headers={"User-Agent": "auto-video-generator/1.0"})
    with urllib.request.urlopen(request, timeout=300) as response:
        output.write_bytes(response.read())


def scene_prompt(scene):
    return scene.get("runway_prompt") or scene.get("image_prompt") or scene.get("visual") or scene.get("text") or scene.get("narration")


def generate_images(args, config, storyboard_dir):
    assets_dir = storyboard_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for index, scene in enumerate(config.get("scenes") or []):
        image_path = resolve(storyboard_dir, scene["image"]) if scene.get("image") else assets_dir / f"scene-{index + 1:02d}.png"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        if image_path.exists() and not args.overwrite:
            scene["image"] = relpath(image_path, storyboard_dir)
            continue
        prompt = scene_prompt(scene)
        if not prompt:
            raise SystemExit(f"Scene {index + 1} has no prompt.")
        payload = {
            "model": args.image_model,
            "promptText": prompt,
            "ratio": args.image_ratio,
        }
        task = request_json("POST", "/text_to_image", payload)
        task = wait_task(task["id"], timeout=args.timeout)
        url = first_output_url(task)
        if not url:
            raise SystemExit(f"Runway image task returned no output URL: {json.dumps(task, indent=2)}")
        download(url, image_path)
        scene["image"] = relpath(image_path, storyboard_dir)


def generate_videos(args, config, storyboard_dir):
    output_dir = storyboard_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    videos = []
    for index, scene in enumerate(config.get("scenes") or []):
        video_path = output_dir / f"runway-scene-{index + 1:02d}.mp4"
        if video_path.exists() and not args.overwrite:
            videos.append(relpath(video_path, storyboard_dir))
            continue
        prompt = scene.get("video_prompt") or scene_prompt(scene)
        if not prompt:
            raise SystemExit(f"Scene {index + 1} has no prompt.")
        payload = {
            "model": args.video_model,
            "promptText": prompt,
            "ratio": args.video_ratio,
            "duration": args.duration,
        }
        if scene.get("image") and not args.text_only_video:
            image_path = resolve(storyboard_dir, scene["image"])
            if not image_path.exists():
                raise SystemExit(f"Scene {index + 1} prompt image not found: {image_path}")
            payload["promptImage"] = data_uri(image_path)
        task = request_json("POST", "/image_to_video", payload)
        task = wait_task(task["id"], timeout=args.timeout)
        url = first_output_url(task)
        if not url:
            raise SystemExit(f"Runway video task returned no output URL: {json.dumps(task, indent=2)}")
        download(url, video_path)
        scene["runway_video"] = relpath(video_path, storyboard_dir)
        videos.append(relpath(video_path, storyboard_dir))
    config["runway_videos"] = videos


def main():
    parser = argparse.ArgumentParser(description="Generate storyboard images or videos with Runway.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--mode", choices=["image", "video"], default="image")
    parser.add_argument("--image-model", default="gen4_image_turbo")
    parser.add_argument("--image-ratio", default="720:1280")
    parser.add_argument("--video-model", default="gen4.5")
    parser.add_argument("--video-ratio", default="720:1280")
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--text-only-video", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    storyboard_path = args.storyboard.resolve()
    storyboard_dir = storyboard_path.parent
    config = json.loads(storyboard_path.read_text(encoding="utf-8-sig"))
    if not config.get("scenes"):
        raise SystemExit("Storyboard has no scenes.")

    if args.mode == "image":
        generate_images(args, config, storyboard_dir)
    else:
        generate_videos(args, config, storyboard_dir)

    storyboard_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"storyboard": str(storyboard_path), "mode": args.mode, "scenes": len(config["scenes"])}, indent=2))


if __name__ == "__main__":
    main()
