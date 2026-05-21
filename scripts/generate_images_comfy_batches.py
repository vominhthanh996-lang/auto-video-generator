#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(cmd):
    subprocess.run(cmd, check=True)


def count_existing_images(storyboard):
    base = storyboard.parent
    data = json.loads(storyboard.read_text(encoding="utf-8-sig"))
    count = 0
    for scene in data.get("scenes") or []:
        image = scene.get("image")
        if not image:
            continue
        path = Path(image)
        if not path.is_absolute():
            path = base / path
        if path.exists():
            count += 1
    return count, len(data.get("scenes") or [])


def main():
    parser = argparse.ArgumentParser(description="Generate local ComfyUI images in small resumable batches.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--aspect-ratio", default="9:16")
    parser.add_argument("--final-width", type=int, default=1080)
    parser.add_argument("--final-height", type=int, default=1920)
    parser.add_argument("--preset", choices=["safe", "balanced", "quality"], default="balanced")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    storyboard = args.storyboard.resolve()
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")

    _, total = count_existing_images(storyboard)
    start = 1
    while start <= total:
        end = min(total, start + args.batch_size - 1)
        cmd = [
            sys.executable,
            str(Path(__file__).resolve().parent / "generate_images_comfy_local.py"),
            "--storyboard",
            str(storyboard),
            "--aspect-ratio",
            args.aspect_ratio,
            "--final-width",
            str(args.final_width),
            "--final-height",
            str(args.final_height),
            "--preset",
            args.preset,
            "--start-scene",
            str(start),
            "--end-scene",
            str(end),
        ]
        if args.overwrite:
            cmd.append("--overwrite")
        print(f"Generating image batch {start}-{end}/{total}", flush=True)
        run(cmd)
        existing, _ = count_existing_images(storyboard)
        print(json.dumps({"images": existing, "total": total}, ensure_ascii=False), flush=True)
        start = end + 1


if __name__ == "__main__":
    main()
