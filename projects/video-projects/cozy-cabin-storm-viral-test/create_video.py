#!/usr/bin/env python3
import math
import random
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parent
INPUT_IMAGE = ROOT / "assets" / "scene-01.png"
OUTPUT_VIDEO = ROOT / "output" / "cozy-cabin-storm-local.mp4"

WIDTH = 1080
HEIGHT = 1920
FPS = 30
DURATION = 10
FRAMES = FPS * DURATION


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


def cover_resize(image):
    scale = max(WIDTH / image.width, HEIGHT / image.height)
    size = (math.ceil(image.width * scale), math.ceil(image.height * scale))
    image = image.resize(size, Image.Resampling.LANCZOS)
    left = (image.width - WIDTH) // 2
    top = (image.height - HEIGHT) // 2
    return image.crop((left, top, left + WIDTH, top + HEIGHT))


def make_vignette():
    mask = Image.new("L", (WIDTH, HEIGHT), 0)
    draw = ImageDraw.Draw(mask)
    for i in range(180):
        alpha = int(180 * (i / 180) ** 2)
        draw.rectangle((i, i, WIDTH - i, HEIGHT - i), outline=alpha, width=2)
    return Image.eval(mask.filter(ImageFilter.GaussianBlur(80)), lambda p: min(180, p))


def draw_rain(draw, frame_index, layer, rng):
    speed = 26 + layer * 12
    count = 120 + layer * 70
    length = 34 + layer * 18
    alpha = 34 + layer * 16
    offset = (frame_index * speed) % (HEIGHT + 240)
    for i in range(count):
        x = (i * 83 + layer * 137 + rng.randint(0, 35)) % (WIDTH + 260) - 130
        y = (i * 151 + offset + rng.randint(0, 45)) % (HEIGHT + 240) - 120
        draw.line((x, y, x - 22, y + length), fill=(190, 225, 255, alpha), width=1 + layer)


def fog_layer(frame_index):
    fog = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(fog)
    for i in range(10):
        x = int((i * 220 + frame_index * (0.7 + i * 0.03)) % (WIDTH + 500)) - 260
        y = int(260 + i * 130 + 22 * math.sin(frame_index * 0.025 + i))
        color = (205, 220, 235, 15 + (i % 3) * 5)
        draw.ellipse((x, y, x + 560, y + 170), fill=color)
    return fog.filter(ImageFilter.GaussianBlur(38))


def lightning_factor(t):
    flashes = [1.15, 3.85, 7.25]
    value = 0.0
    for flash in flashes:
        d = abs(t - flash)
        if d < 0.08:
            value = max(value, 1.0 - d / 0.08)
        elif 0.15 < d < 0.22:
            value = max(value, 0.45 * (1.0 - (d - 0.15) / 0.07))
    return value


def render():
    if not INPUT_IMAGE.exists():
        raise SystemExit(f"Missing keyframe: {INPUT_IMAGE}")
    OUTPUT_VIDEO.parent.mkdir(parents=True, exist_ok=True)

    base = cover_resize(Image.open(INPUT_IMAGE).convert("RGB"))
    vignette = make_vignette()
    rng = random.Random(42)

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
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(OUTPUT_VIDEO),
    ]

    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert process.stdin is not None
    try:
        for frame_index in range(FRAMES):
            t = frame_index / FPS
            progress = frame_index / max(1, FRAMES - 1)
            zoom = 1.0 + 0.075 * progress
            crop_w = int(WIDTH / zoom)
            crop_h = int(HEIGHT / zoom)
            drift_x = int(18 * math.sin(progress * math.pi * 0.7))
            drift_y = int(22 * progress)
            left = (WIDTH - crop_w) // 2 + drift_x
            top = (HEIGHT - crop_h) // 2 + drift_y
            frame = base.crop((left, top, left + crop_w, top + crop_h)).resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)

            flicker = 1.0 + 0.025 * math.sin(t * 2.1 * math.pi) + 0.012 * math.sin(t * 9.3)
            frame = ImageEnhance.Brightness(frame).enhance(flicker)
            frame = ImageEnhance.Contrast(frame).enhance(1.04)
            frame = frame.convert("RGBA")

            overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            rain_draw = ImageDraw.Draw(overlay)
            draw_rain(rain_draw, frame_index, 0, rng)
            draw_rain(rain_draw, frame_index, 1, rng)
            frame = Image.alpha_composite(frame, overlay)
            frame = Image.alpha_composite(frame, fog_layer(frame_index))

            flash = lightning_factor(t)
            if flash > 0:
                lightning = Image.new("RGBA", (WIDTH, HEIGHT), (165, 205, 255, int(95 * flash)))
                frame = Image.alpha_composite(frame, lightning)

            shade = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            shade.putalpha(vignette)
            frame = Image.alpha_composite(frame, shade).convert("RGB")
            process.stdin.write(frame.tobytes())
    finally:
        process.stdin.close()
        returncode = process.wait()
    if returncode != 0:
        raise SystemExit(f"ffmpeg failed with exit code {returncode}")
    print(OUTPUT_VIDEO)


if __name__ == "__main__":
    render()
