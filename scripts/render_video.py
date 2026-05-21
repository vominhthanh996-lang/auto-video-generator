#!/usr/bin/env python3
import argparse
import json
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from video_presets import VIDEO_PRESETS, apply_video_format


def run(cmd):
    subprocess.run(cmd, check=True)


def require_tool(name):
    if shutil.which(name) is None:
        raise SystemExit(f"Missing required tool on PATH: {name}")


def resolve(base, value):
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def ffmpeg_escape(text):
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(",", "\\,")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def draw_text_filter(text, font, y_expr, size_expr, box_alpha="0.55"):
    escaped = ffmpeg_escape(text)
    font_key = "fontfile" if Path(str(font)).exists() else "font"
    return (
        "drawtext="
        f"{font_key}='{ffmpeg_escape(font)}':"
        f"text='{escaped}':"
        "fontcolor=white:"
        f"fontsize={size_expr}:"
        "line_spacing=12:"
        "box=1:"
        f"boxcolor=black@{box_alpha}:"
        "boxborderw=28:"
        "x=(w-text_w)/2:"
        f"y={y_expr}"
    )


def make_scene(storyboard_dir, scene, index, config, temp_dir):
    image = resolve(storyboard_dir, scene.get("image"))
    audio = resolve(storyboard_dir, scene.get("audio"))
    if not image or not image.exists():
        raise SystemExit(f"Scene {index + 1} image not found: {image}")
    if not audio or not audio.exists():
        raise SystemExit(f"Scene {index + 1} audio not found: {audio}")

    duration = float(scene.get("duration", 4))
    width = int(config.get("width", 1080))
    height = int(config.get("height", 1920))
    fps = int(config.get("fps", 30))
    font = config.get("font", "Arial")
    if font == "Arial":
        windows_arial = Path(r"C:\Windows\Fonts\arial.ttf")
        if windows_arial.exists():
            font = str(windows_arial)
    output = temp_dir / f"scene_{index:03d}.mp4"

    filters = [
        f"scale={width}:{height}:force_original_aspect_ratio=increase",
        f"crop={width}:{height}",
        "setsar=1",
    ]

    headline = scene.get("text")
    if headline:
        filters.append(draw_text_filter(headline, font, "h*0.12", "min(w\\,h)/16", "0.50"))

    subtitle = scene.get("subtitle") or scene.get("narration")
    if subtitle:
        filters.append(draw_text_filter(subtitle, font, "h-text_h-h*0.10", "min(w\\,h)/28", "0.62"))

    vf = ",".join(filters)
    run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-t",
            str(duration),
            "-i",
            str(image),
            "-i",
            str(audio),
            "-vf",
            vf,
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(output),
        ]
    )
    return output


def concat_scenes(scene_files, output):
    list_file = output.parent / "concat_list.txt"
    list_file.write_text(
        "".join(f"file '{path.as_posix()}'\n" for path in scene_files),
        encoding="utf-8",
    )
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output)])


def probe(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size",
            "-show_entries",
            "stream=codec_type,width,height",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description="Render a narrated image storyboard to MP4.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--format", choices=sorted(VIDEO_PRESETS), help="Override output preset: tiktok=1080x1920 9:16, youtube=1920x1080 16:9")
    args = parser.parse_args()

    require_tool("ffmpeg")
    require_tool("ffprobe")

    storyboard_path = args.storyboard.resolve()
    storyboard_dir = storyboard_path.parent
    config = json.loads(storyboard_path.read_text(encoding="utf-8"))
    if args.format:
        apply_video_format(config, args.format)
    scenes = config.get("scenes") or []
    if not scenes:
        raise SystemExit("Storyboard has no scenes.")
    run([sys.executable, str(Path(__file__).resolve().parent / "validate_storyboard.py"), "--storyboard", str(storyboard_path), "--stage", "all"])

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="auto-video-") as temp_name:
        temp_dir = Path(temp_name)
        scene_files = [make_scene(storyboard_dir, scene, i, config, temp_dir) for i, scene in enumerate(scenes)]
        concat_scenes(scene_files, output)

    info = probe(output)
    print(json.dumps({"output": str(output), "probe": info}, indent=2))


if __name__ == "__main__":
    main()
