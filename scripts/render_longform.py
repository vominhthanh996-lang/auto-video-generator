#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable


def run(cmd, env=None):
    completed = subprocess.run(cmd, text=True, capture_output=True, env=env)
    if completed.returncode != 0:
        raise SystemExit(
            "Command failed:\n"
            + " ".join(str(part) for part in cmd)
            + "\nSTDOUT:\n"
            + completed.stdout
            + "\nSTDERR:\n"
            + completed.stderr
        )
    return completed


def load_manifest(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def process_chapter(chapter, args, env):
    storyboard = Path(chapter["storyboard"]).resolve()
    output = Path(chapter["output"]).resolve()
    if output.exists() and not args.overwrite:
        return {"chapter": chapter["chapter"], "skipped": True, "output": str(output)}

    if not args.skip_voice:
        run(
            [
                PYTHON,
                str(ROOT / "generate_voice_edge.py"),
                "--storyboard",
                str(storyboard),
                "--voice",
                args.voice,
                "--voice-style",
                args.voice_style,
                "--overwrite",
            ],
            env=env,
        )

    if not args.skip_images:
        cmd = [
            PYTHON,
            str(ROOT / "generate_with_fallback.py"),
            "--storyboard",
            str(storyboard),
            "--kind",
            "image",
        ]
        if args.image_providers:
            cmd.extend(["--providers", args.image_providers])
        if args.overwrite_images:
            cmd.append("--overwrite")
        run(cmd, env=env)

    run(
        [
            PYTHON,
            str(ROOT / "render_video.py"),
            "--storyboard",
            str(storyboard),
            "--output",
            str(output),
        ],
        env=env,
    )
    return {"chapter": chapter["chapter"], "skipped": False, "output": str(output)}


def main():
    parser = argparse.ArgumentParser(description="Render a long-form project chapter by chapter.")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--voice", default="vi-female")
    parser.add_argument("--voice-style", choices=["plain", "story-emotional", "wasteland-dark"], default="wasteland-dark")
    parser.add_argument("--image-providers", default="stability,runway,openai,replicate,fal")
    parser.add_argument("--chapter", type=int, default=0, help="Render only one chapter number.")
    parser.add_argument("--skip-voice", action="store_true")
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--overwrite-images", action="store_true")
    parser.add_argument("--no-concat", action="store_true")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = load_manifest(manifest_path)
    env = os.environ.copy()

    chapters = manifest["chapters"]
    if args.chapter:
        chapters = [chapter for chapter in chapters if chapter["chapter"] == args.chapter]
        if not chapters:
            raise SystemExit(f"Chapter {args.chapter} not found.")

    results = [process_chapter(chapter, args, env) for chapter in chapters]

    final_output = None
    if not args.no_concat and not args.chapter:
        run([PYTHON, str(ROOT / "concat_videos.py"), "--manifest", str(manifest_path)], env=env)
        final_output = manifest["final_output"]

    print(json.dumps({"manifest": str(manifest_path), "chapters": results, "final_output": final_output}, indent=2))


if __name__ == "__main__":
    main()
