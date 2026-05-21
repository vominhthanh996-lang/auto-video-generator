#!/usr/bin/env python3
import argparse
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from video_presets import apply_video_format, preset_for


BASE_STYLE = (
    "cinematic realistic story illustration, consistent characters, premium film still, "
    "dramatic lighting, atmospheric depth, realistic textures, muted natural colors, "
    "35mm cinema lens, subtle film grain, no text, no watermark"
)

DEFAULT_NEGATIVE = (
    "low quality, blurry, jpeg artifacts, cartoon, anime, plastic skin, oversaturated, "
    "bad anatomy, deformed hands, distorted face, extra limbs, duplicate body, ugly face, "
    "text, watermark, logo, messy composition, flat lighting, bad perspective, AI artifacts"
)


def run(cmd, env=None):
    print("+ " + " ".join(str(part) for part in cmd), flush=True)
    subprocess.run(cmd, check=True, env=env)


def slugify(value):
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return value or "story-video"


def resolve(base, value):
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def read_source(path):
    text = path.read_text(encoding="utf-8-sig")
    vietnamese_marks = sum(1 for char in text.lower() if char in "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")
    if text.count("?") >= 8 and vietnamese_marks == 0:
        raise SystemExit("Source text looks encoding-damaged. Save it as UTF-8 and try again.")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def split_sentences(text):
    pieces = []
    for paragraph in re.split(r"\n+", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph.split()) <= 14:
            pieces.append(paragraph)
            continue
        parts = re.split(r"(?<=[.!?。！？])\s+", paragraph)
        pieces.extend(part.strip() for part in parts if part.strip())
    return pieces


def group_for_scenes(text, min_scenes, max_scenes, words_per_image):
    pieces = split_sentences(text)
    word_count = len(re.findall(r"\S+", text))
    target = round(word_count / words_per_image)
    target = max(min_scenes, min(max_scenes, target))
    target_words = max(18, math.ceil(word_count / target))

    groups = []
    current = []
    current_words = 0
    for piece in pieces:
        words = len(re.findall(r"\S+", piece))
        if current and current_words + words > target_words and len(groups) < target - 1:
            groups.append(" ".join(current))
            current = [piece]
            current_words = words
        else:
            current.append(piece)
            current_words += words
    if current:
        groups.append(" ".join(current))
    return groups, word_count


def image_prompt(narration, style):
    compact = narration[:320].replace("\n", " ")
    lower = narration.lower()
    visual = "cinematic scene matching the narration"
    if "mưa" in lower:
        visual = "rainy cinematic environment with wet reflections"
    elif "phế thổ" in lower or "nhiễm xạ" in lower:
        visual = "post apocalyptic radioactive wasteland, red dusty sky, ruined city edge"
    elif "chó" in lower or "thú" in lower:
        visual = "tense survival scene with mutated animals in ruined wasteland"
    elif "tường" in lower or "thành" in lower:
        visual = "distant giant city wall beyond polluted wasteland"
    elif "thịt hộp" in lower or "đồ ăn" in lower:
        visual = "close cinematic survival scene focused on precious food supplies"
    elif "máu" in lower or "vết thương" in lower:
        visual = "dark tense wounded survivor scene, realistic blood, dramatic shadows"
    return f"{visual}, {style}. Narration mood: {compact}"


def build_storyboard(args):
    source = args.source.resolve()
    text = read_source(source)
    project = args.project.resolve() if args.project else Path(args.root).resolve() / slugify(args.title or source.stem)
    assets = project / "assets"
    output = project / "output"
    assets.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    (project / "source.txt").write_text(text, encoding="utf-8")

    groups, word_count = group_for_scenes(text, args.min_scenes, args.max_scenes, args.words_per_image)
    style = args.style or BASE_STYLE
    scenes = []
    for index, narration in enumerate(groups, 1):
        scenes.append(
            {
                "id": f"scene-{index:03d}",
                "duration": 12,
                "image": f"assets/scene-{index:03d}.png",
                "audio": f"assets/scene-{index:03d}.mp3",
                "narration": narration,
                "subtitle": narration if args.subtitles else "",
                "text": args.title if index == 1 and args.title_overlay else "",
                "image_prompt": image_prompt(narration, style),
                "negative_prompt": DEFAULT_NEGATIVE,
            }
        )

    config = {
        "title": args.title or source.stem,
        "language": args.language,
        "font": "Arial",
        "word_count": word_count,
        "words_per_image_target": args.words_per_image,
        "scenes": scenes,
        "music": None,
    }
    apply_video_format(config, args.format)
    storyboard = project / "storyboard.json"
    storyboard.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return project, storyboard, config


def count_assets(storyboard, key):
    base = storyboard.parent
    config = json.loads(storyboard.read_text(encoding="utf-8-sig"))
    count = 0
    for scene in config.get("scenes") or []:
        value = scene.get(key)
        if value and resolve(base, value).exists():
            count += 1
    return count, len(config.get("scenes") or [])


def probe_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def sync_durations(storyboard, pad):
    base = storyboard.parent
    config = json.loads(storyboard.read_text(encoding="utf-8-sig"))
    for scene in config.get("scenes") or []:
        audio = scene.get("audio")
        if not audio:
            continue
        duration = probe_duration(resolve(base, audio))
        if duration:
            scene["duration"] = round(duration + pad, 2)
            scene["audio_duration"] = round(duration, 2)
    storyboard.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def write_contact_sheet(project, storyboard):
    config = json.loads(storyboard.read_text(encoding="utf-8-sig"))
    cards = []
    for index, scene in enumerate(config.get("scenes") or [], 1):
        image = html.escape(scene.get("image") or "")
        text = html.escape((scene.get("narration") or "")[:180])
        cards.append(f"<figure><img src='{image}'><figcaption>{index:03d}. {text}</figcaption></figure>")
    page = """<!doctype html>
<meta charset="utf-8">
<title>Contact Sheet</title>
<style>
body{font-family:Arial,sans-serif;background:#111;color:#eee;margin:24px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}
figure{margin:0;background:#1c1c1c;padding:10px;border-radius:6px}
img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}
figcaption{font-size:12px;line-height:1.35;margin-top:8px;color:#ccc}
</style>
<div class="grid">""" + "\n".join(cards) + "</div>"
    path = project / "contact-sheet.html"
    path.write_text(page, encoding="utf-8")
    return path


def maybe_start_comfy(args):
    if not args.start_comfy:
        return
    try:
        subprocess.run(["powershell", "-Command", "Invoke-WebRequest -Uri 'http://127.0.0.1:8188/object_info' -UseBasicParsing -TimeoutSec 3"], check=True, capture_output=True)
        return
    except Exception:
        pass
    comfy_root = Path(args.comfy_root)
    python = comfy_root / "python_embeded" / "python.exe"
    main = comfy_root / "ComfyUI" / "main.py"
    log_dir = Path(args.root) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    out = open(log_dir / "comfyui-pipeline-out.log", "w", encoding="utf-8")
    err = open(log_dir / "comfyui-pipeline-err.log", "w", encoding="utf-8")
    subprocess.Popen([str(python), "-s", str(main), "--windows-standalone-build", "--lowvram"], cwd=str(comfy_root), stdout=out, stderr=err)
    for _ in range(36):
        time.sleep(5)
        try:
            subprocess.run(["powershell", "-Command", "Invoke-WebRequest -Uri 'http://127.0.0.1:8188/object_info' -UseBasicParsing -TimeoutSec 3"], check=True, capture_output=True)
            return
        except Exception:
            pass
    raise SystemExit("ComfyUI did not start on http://127.0.0.1:8188")


def main():
    parser = argparse.ArgumentParser(description="Run the local story-video pipeline with resumable image/audio stages.")
    parser.add_argument("--source", required=True, type=Path, help="UTF-8 story text file.")
    parser.add_argument("--title", default="")
    parser.add_argument("--project", type=Path)
    parser.add_argument("--root", default=r"E:\ThanhMV\video-projects")
    parser.add_argument("--format", choices=["youtube", "tiktok"], default="youtube")
    parser.add_argument("--language", default="vi")
    parser.add_argument("--voice", default="vi-female")
    parser.add_argument("--words-per-image", type=int, default=32)
    parser.add_argument("--min-scenes", type=int, default=50)
    parser.add_argument("--max-scenes", type=int, default=90)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--image-preset", choices=["safe", "balanced", "quality"], default="balanced")
    parser.add_argument("--style", default="")
    parser.add_argument("--subtitles", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--title-overlay", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--duration-pad", type=float, default=0.35)
    parser.add_argument("--start-comfy", action="store_true")
    parser.add_argument("--comfy-root", default=r"E:\ThanhMV\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable")
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--skip-voice", action="store_true")
    parser.add_argument("--skip-render", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    preset = preset_for(args.format)
    project, storyboard, config = build_storyboard(args)
    env = dict(os.environ)
    env["TEMP"] = str(Path(args.root).resolve().parent / "temp") if "video-projects" in args.root else r"E:\ThanhMV\temp"
    env["TMP"] = env["TEMP"]
    Path(env["TEMP"]).mkdir(parents=True, exist_ok=True)

    scripts = Path(__file__).resolve().parent
    run([sys.executable, str(scripts / "validate_storyboard.py"), "--storyboard", str(storyboard), "--stage", "text"], env=env)

    maybe_start_comfy(args)

    image_cmd = [
        sys.executable,
        str(scripts / "generate_images_comfy_batches.py"),
        "--storyboard",
        str(storyboard),
        "--batch-size",
        str(args.batch_size),
        "--aspect-ratio",
        preset["aspect"],
        "--final-width",
        str(preset["width"]),
        "--final-height",
        str(preset["height"]),
        "--preset",
        args.image_preset,
    ]
    voice_cmd = [sys.executable, str(scripts / "generate_voice_edge.py"), "--storyboard", str(storyboard), "--voice", args.voice]
    if args.overwrite:
        image_cmd.append("--overwrite")
        voice_cmd.append("--overwrite")

    processes = []
    if not args.skip_images:
        processes.append(("images", subprocess.Popen(image_cmd, env=env)))
    if not args.skip_voice:
        processes.append(("voice", subprocess.Popen(voice_cmd, env=env)))
    for name, process in processes:
        code = process.wait()
        if code != 0:
            raise SystemExit(f"{name} stage failed with exit code {code}")

    sync_durations(storyboard, args.duration_pad)
    run([sys.executable, str(scripts / "validate_storyboard.py"), "--storyboard", str(storyboard), "--stage", "all"], env=env)
    contact_sheet = write_contact_sheet(project, storyboard)

    output = project / "output" / f"{slugify(args.title or args.source.stem)}-{args.format}.mp4"
    if not args.skip_render:
        run([sys.executable, str(scripts / "render_video.py"), "--storyboard", str(storyboard), "--output", str(output), "--format", args.format], env=env)

    image_count, total = count_assets(storyboard, "image")
    audio_count, _ = count_assets(storyboard, "audio")
    summary = {
        "project": str(project),
        "storyboard": str(storyboard),
        "format": args.format,
        "resolution": f"{preset['width']}x{preset['height']}",
        "scenes": total,
        "images": image_count,
        "audio": audio_count,
        "contact_sheet": str(contact_sheet),
        "output": str(output) if output.exists() else None,
        "duration": probe_duration(output) if output.exists() else None,
    }
    (project / "pipeline-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
