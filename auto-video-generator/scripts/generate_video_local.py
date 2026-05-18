#!/usr/bin/env python3
import argparse
import json
import math
import random
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


WIDTH_DEFAULT = 1080
HEIGHT_DEFAULT = 1920
FPS_DEFAULT = 30


def ffmpeg_path():
    found = shutil.which("ffmpeg")
    if found:
        return found
    winget = Path(
        r"C:\Users\thanh\AppData\Local\Microsoft\WinGet\Packages"
        r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
        r"\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
    )
    if winget.exists():
        return str(winget)
    raise SystemExit("ffmpeg was not found on PATH.")


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


def cover_resize(image, width, height):
    scale = max(width / image.width, height / image.height)
    size = (math.ceil(image.width * scale), math.ceil(image.height * scale))
    image = image.resize(size, Image.Resampling.LANCZOS)
    left = (image.width - width) // 2
    top = (image.height - height) // 2
    return image.crop((left, top, left + width, top + height))


def make_vignette(width, height):
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    edge = max(120, min(width, height) // 6)
    for i in range(edge):
        alpha = int(185 * (i / edge) ** 2)
        draw.rectangle((i, i, width - i, height - i), outline=alpha, width=2)
    return Image.eval(mask.filter(ImageFilter.GaussianBlur(edge // 2)), lambda p: min(185, p))


def draw_rain(draw, frame_index, width, height, layer, rng):
    speed = 26 + layer * 12
    count = 100 + layer * 70
    length = 32 + layer * 18
    alpha = 32 + layer * 16
    offset = (frame_index * speed) % (height + 240)
    for i in range(count):
        x = (i * 83 + layer * 137 + rng.randint(0, 35)) % (width + 260) - 130
        y = (i * 151 + offset + rng.randint(0, 45)) % (height + 240) - 120
        draw.line((x, y, x - 22, y + length), fill=(190, 225, 255, alpha), width=1 + layer)


def fog_layer(frame_index, width, height):
    fog = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(fog)
    for i in range(10):
        x = int((i * 220 + frame_index * (0.7 + i * 0.03)) % (width + 500)) - 260
        y = int(height * 0.14 + i * height * 0.07 + 22 * math.sin(frame_index * 0.025 + i))
        draw.ellipse((x, y, x + 560, y + 170), fill=(205, 220, 235, 14 + (i % 3) * 5))
    return fog.filter(ImageFilter.GaussianBlur(38))


def lightning_factor(t):
    flashes = [1.15, 3.85, 7.25, 9.15]
    value = 0.0
    for flash in flashes:
        d = abs(t - flash)
        if d < 0.08:
            value = max(value, 1.0 - d / 0.08)
        elif 0.15 < d < 0.22:
            value = max(value, 0.45 * (1.0 - (d - 0.15) / 0.07))
    return value


def render_scene(image_path, output_path, width, height, fps, duration, effects):
    base = cover_resize(Image.open(image_path).convert("RGB"), width, height)
    frames = int(fps * duration)
    vignette = make_vignette(width, height)
    rng = random.Random(42)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg_path(),
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert process.stdin is not None
    try:
        for frame_index in range(frames):
            t = frame_index / fps
            progress = frame_index / max(1, frames - 1)
            zoom = 1.0 + 0.075 * progress
            crop_w = int(width / zoom)
            crop_h = int(height / zoom)
            drift_x = int(18 * math.sin(progress * math.pi * 0.7))
            drift_y = int(22 * progress)
            left = (width - crop_w) // 2 + drift_x
            top = (height - crop_h) // 2 + drift_y
            frame = base.crop((left, top, left + crop_w, top + crop_h)).resize((width, height), Image.Resampling.LANCZOS)

            flicker = 1.0 + 0.025 * math.sin(t * 2.1 * math.pi) + 0.012 * math.sin(t * 9.3)
            frame = ImageEnhance.Brightness(frame).enhance(flicker)
            frame = ImageEnhance.Contrast(frame).enhance(1.04).convert("RGBA")

            if effects in ("storm", "rain", "cinematic"):
                overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                rain_draw = ImageDraw.Draw(overlay)
                draw_rain(rain_draw, frame_index, width, height, 0, rng)
                draw_rain(rain_draw, frame_index, width, height, 1, rng)
                frame = Image.alpha_composite(frame, overlay)
                frame = Image.alpha_composite(frame, fog_layer(frame_index, width, height))
                flash = lightning_factor(t)
                if flash > 0:
                    frame = Image.alpha_composite(frame, Image.new("RGBA", (width, height), (165, 205, 255, int(95 * flash))))

            shade = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            shade.putalpha(vignette)
            frame = Image.alpha_composite(frame, shade).convert("RGB")
            process.stdin.write(frame.tobytes())
    finally:
        process.stdin.close()
        returncode = process.wait()
    if returncode != 0:
        raise SystemExit(f"ffmpeg failed with exit code {returncode}")


def concat(inputs, output):
    list_file = output.parent / "local_concat_list.txt"
    list_file.write_text("".join(f"file '{path.resolve().as_posix()}'\n" for path in inputs), encoding="utf-8")
    subprocess.run([ffmpeg_path(), "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output)], check=True)


def main():
    parser = argparse.ArgumentParser(description="Create local cinematic motion from storyboard keyframes.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--effects", default="storm", choices=["storm", "rain", "cinematic", "push"])
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    storyboard = args.storyboard.resolve()
    base_dir = storyboard.parent
    config = json.loads(storyboard.read_text(encoding="utf-8-sig"))
    width = int(config.get("width", WIDTH_DEFAULT))
    height = int(config.get("height", HEIGHT_DEFAULT))
    fps = int(config.get("fps", FPS_DEFAULT))
    output_dir = base_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    final_output = args.output.resolve() if args.output else output_dir / "local-video.mp4"

    scene_outputs = []
    for index, scene in enumerate(config.get("scenes") or []):
        if not scene.get("image"):
            raise SystemExit(f"Scene {index + 1} has no image. Generate images before local video fallback.")
        image = resolve(base_dir, scene["image"])
        if not image.exists():
            raise SystemExit(f"Scene {index + 1} image not found: {image}")
        duration = float(scene.get("duration", 10))
        scene_output = output_dir / f"local-scene-{index + 1:02d}.mp4"
        if args.overwrite or not scene_output.exists():
            render_scene(image, scene_output, width, height, fps, duration, args.effects)
        scene["local_video"] = relpath(scene_output, base_dir)
        scene_outputs.append(scene_output)

    if len(scene_outputs) == 1:
        if args.overwrite or not final_output.exists():
            shutil.copy2(scene_outputs[0], final_output)
    else:
        concat(scene_outputs, final_output)
    config["local_video"] = relpath(final_output, base_dir)
    storyboard.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"storyboard": str(storyboard), "output": str(final_output), "scenes": len(scene_outputs)}, indent=2))


if __name__ == "__main__":
    main()
