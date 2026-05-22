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
    "premium cinematic post-apocalyptic webnovel keyframe, YouTube story visual, "
    "one clear main subject, readable danger, emotional survival drama, "
    "foreground debris framing, midground character action, background ruined world, "
    "strong silhouette, warm practical light against cold toxic atmosphere, "
    "volumetric dust and fog, realistic wet rusted metal, cracked concrete, torn cloth, "
    "35mm cinema lens, shallow depth of field, dramatic rim light, subtle film grain, "
    "muted natural colors, high contrast but not oversaturated, no text, no watermark"
)

DEFAULT_NEGATIVE = (
    "low quality, blurry, jpeg artifacts, cartoon, anime, plastic skin, oversaturated, "
    "bad anatomy, deformed hands, distorted face, extra limbs, duplicate body, ugly face, "
    "text, watermark, logo, messy composition, flat lighting, bad perspective, AI artifacts, "
    "empty landscape, generic fantasy art, beauty portrait, clean clothes, modern city, "
    "white speckles, random colored dots, noisy artifacts, oversharpened, waxy skin"
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


def read_source(path):
    text = path.read_text(encoding="utf-8-sig")
    vietnamese_marks = sum(
        1
        for char in text.lower()
        if char
        in "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    )
    if text.count("?") >= 8 and vietnamese_marks == 0:
        raise SystemExit("Source text looks encoding-damaged. Save it as UTF-8 and try again.")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def has_any(text, words):
    return any(word in text for word in words)


def image_prompt(narration, style):
    compact = narration[:360].replace("\n", " ")
    lower = narration.lower()
    characters = []
    if "l\u00e2m t\u1ecbch" in lower:
        characters.append("a fragile young female wasteland scavenger, dirty torn coat, exhausted but alert, side or back view")
    if "t\u1ea7n d\u00e3" in lower or "ng\u01b0\u1eddi \u0111\u00e0n \u00f4ng" in lower or "l\u00ednh \u0111\u00e1nh thu\u00ea" in lower:
        characters.append("a wounded male mercenary in black tactical coat, half sitting in the debris, guarded expression")
    character_line = ", ".join(characters) if characters else "a lone survivor in torn wasteland clothes, small human silhouette against a hostile world"

    visual = "wide cinematic survival scene in a radioactive wasteland, red dusty sky, ruined vehicles, polluted haze"
    if has_any(lower, ["ch\u00f3", "th\u00fa", "bi\u1ebfn d\u1ecb", "g\u1ea7m g\u1eeb", "m\u00f3ng vu\u1ed1t"]):
        visual = "tense predator encounter, mutated two-jawed dogs tearing at a corpse beside an overturned truck, survivor hiding behind concrete"
    elif has_any(lower, ["b\u00e3i r\u00e1c", "\u0111\u1ed1ng r\u00e1c", "t\u1ee7 l\u1ea1nh", "t\u00fai nh\u1ef1a", "nh\u1eb7t r\u00e1c"]):
        visual = "scroll-stopping wasteland junkyard scene, rusted refrigerator, dead plastic bags, broken metal sheets, toxic red sky pressing down"
    elif has_any(lower, ["m\u01b0a", "m\u01b0a \u0111en", "m\u01b0a \u0111\u1ed9c"]):
        visual = "black toxic rain falling over ruined streets, wet reflective ground, corroded metal, survivor hiding under broken concrete"
    elif has_any(lower, ["ph\u1ebf th\u1ed5", "nhi\u1ec5m x\u1ea1", "\u0111\u1ea1i nhi\u1ec5m x\u1ea1", "\u00f4 nhi\u1ec5m", "b\u1ea7u tr\u1eddi \u0111\u1ecf"]):
        visual = "radioactive wasteland after a great contamination disaster, crimson polluted sky, ash wind, distant dead city edge"
    elif has_any(lower, ["t\u01b0\u1eddng", "th\u00e0nh", "c\u1ed5ng th\u00e0nh", "v\u00e0o th\u00e0nh"]):
        visual = "massive safe-zone wall far beyond a polluted wasteland, tiny survivor looking toward unreachable clean city lights"
    elif has_any(lower, ["th\u1ecbt h\u1ed9p", "\u0111\u1ed3 \u0103n", "b\u00e1nh", "k\u1eb9o", "n\u01b0\u1edbc s\u1ea1ch", "tinh th\u1ea1ch"]):
        visual = "close survival-detail shot, dirty hands reaching toward a precious can of meat and a tiny crystal among dust and blood"
    elif has_any(lower, ["m\u00e1u", "v\u1ebft th\u01b0\u01a1ng", "dao", "b\u0103ng", "gen s\u1ee5p \u0111\u1ed5"]):
        visual = "dark medical survival moment, wounded mercenary with black blood and torn tactical coat, scavenger holding a knife under harsh rim light"
    elif has_any(lower, ["g\u1ea7m xe", "c\u00f2i", "ba h\u01a1i", "m\u1ed9t h\u01a1i d\u00e0i"]):
        visual = "claustrophobic shot under an overturned truck, survivors pressed into mud while mutant claws scrape just outside"
    elif has_any(lower, ["xuy\u00ean kh\u00f4ng", "ch\u1ebft", "m\u1edf m\u1eaft", "k\u00fd \u1ee9c"]):
        visual = "surreal awakening after death in a wasteland junkyard, weak survivor lying among rust and ash, red sky reflected in frightened eyes"

    youtube_vibe = (
        "make it feel like a high-retention YouTube apocalypse story thumbnail but still cinematic, "
        "clear readable stakes in the first glance, emotional lonely survival vibe, not a clean wallpaper, "
        "not a random landscape, dramatic face mostly hidden or side angle, realistic Chinese/Vietnamese webnovel atmosphere"
    )
    return f"{visual}, {character_line}, {style}, {youtube_vibe}. Scene context: {compact}"


def add_unique(items, value):
    if value and value not in items:
        items.append(value)


def shot_type_for(narration, scene_index):
    lower = narration.lower()
    if scene_index == 1 or has_any(lower, ["bầu trời", "xa xa", "bức tường khổng lồ", "thành an toàn"]):
        return "wide establishing shot showing place and scale"
    if has_any(lower, ["thịt hộp", "kẹo", "tinh thạch", "còi", "dao", "than lọc", "vết thương"]):
        return "close survival-detail shot focused on hands, props, and immediate stakes"
    if has_any(lower, ["gầm xe", "trốn", "nín thở"]):
        return "low claustrophobic point-of-view shot from cover"
    if has_any(lower, ["chó", "thú", "gầm gừ", "móng vuốt", "xác"]):
        return "medium tense action shot with predator, victim, and survivor positions readable"
    return "medium cinematic story shot with clear blocking"


def visual_prompt_data(narration, style, continuity=None, scene_index=1):
    continuity = continuity or {}
    compact = narration[:420].replace("\n", " ")
    lower = narration.lower()
    characters = []
    setting = []
    props = []
    actions = []
    mood = []
    shot_type = shot_type_for(narration, scene_index)

    if "lâm tịch" in lower or "nàng" in lower:
        add_unique(characters, "Lam Tich, a fragile young female wasteland scavenger in a dirty torn coat, exhausted but stubborn")
    if "tần dã" in lower:
        add_unique(characters, "Tan Da, a wounded male mercenary in a black tactical coat, restrained and dangerous")
    elif "người đàn ông" in lower or "lính đánh thuê" in lower:
        add_unique(characters, "a wounded male mercenary in a black tactical coat")
    if not characters:
        add_unique(characters, "the exact survivor or person described in the narration, shown from side or back view")

    keyword_rules = [
        (["bãi rác", "đống rác", "nhặt rác"], setting, "radioactive junkyard outside the city"),
        (["tủ lạnh"], props, "rusted half-broken refrigerator"),
        (["túi nhựa"], props, "hardened dead plastic bags like old skin"),
        (["bầu trời đỏ", "trời màu đỏ"], setting, "heavy polluted crimson red sky"),
        (["phế thổ", "đại nhiễm xạ", "nhiễm xạ", "ô nhiễm"], setting, "contaminated post-apocalyptic wasteland"),
        (["mưa đen", "mưa độc"], setting, "black toxic rain residue and corroded wet surfaces"),
        (["bức tường khổng lồ", "thành an toàn", "vào thành", "cổng thành", "sau bức tường là thành"], setting, "distant massive safe-zone wall beyond the wasteland"),
        (["chó hai hàm", "chó", "thú biến dị", "biến dị", "gầm gừ", "móng vuốt"], actions, "mutated two-jawed dogs threatening the scene"),
        (["xác", "người chết"], props, "fresh human corpse on the ground"),
        (["xe tải lật"], props, "overturned truck beside the corpse"),
        (["bức tường bê tông", "tường bê tông"], props, "collapsed concrete wall used as cover"),
        (["gầm xe"], actions, "survivors hiding under the vehicle"),
        (["còi"], props, "small metal whistle"),
        (["thịt hộp"], props, "precious sealed can of meat"),
        (["bánh nén", "bánh"], props, "compressed ration biscuit"),
        (["kẹo"], props, "small unwrapped candy"),
        (["tinh thạch"], props, "tiny crystal shard"),
        (["dao"], props, "survival knife in a dirty hand"),
        (["máu đen", "máu"], props, "dark blood stains"),
        (["vết thương"], actions, "close survival treatment of a serious wound"),
        (["gen sụp đổ"], mood, "body-horror genetic collapse tension"),
        (["nước", "lon rỉ"], props, "rusty water can and unsafe scavenged water"),
        (["than lọc"], props, "used poison-filtering charcoal"),
        (["sợ", "nín thở", "run"], mood, "breathless fear and survival tension"),
        (["im lặng", "một ngày", "sống thêm"], mood, "quiet lonely survival melancholy"),
    ]
    for words, target, phrase in keyword_rules:
        if has_any(lower, words):
            add_unique(target, phrase)

    if has_any(lower, ["mở mắt", "tỉnh lại", "xuyên không", "chết một lần"]):
        add_unique(actions, "surreal awakening after death, weak body lying among rust and ash")
    if has_any(lower, ["lục", "túi", "chạm vào", "rút"]):
        add_unique(actions, "dirty hands searching a pocket for survival supplies")
    if has_any(lower, ["kéo", "bò", "trốn"]):
        add_unique(actions, "desperate crawling and hiding from danger")
    if has_any(lower, ["nhìn", "xa xa"]):
        add_unique(actions, "small survivor looking toward something unreachable in the distance")

    if not setting:
        add_unique(setting, "hostile radioactive wasteland environment matching the narration")
    if not actions:
        add_unique(actions, "the exact action described in the narration, not a generic pose")
    if not mood:
        add_unique(mood, "tense cinematic survival mood")

    must_show = []
    for source in (characters, setting, actions, props):
        for item in source:
            add_unique(must_show, item)
    must_show = must_show[:9]

    prompt = (
        "Faithfully illustrate this exact story beat from the narration, not a generic apocalypse wallpaper. "
        f"CONTINUITY FROM PREVIOUS SCENE: {continuity.get('summary', 'start of sequence')}. "
        f"MUST SHOW: {', '.join(must_show)}. "
        f"Characters: {', '.join(characters)}. "
        f"Setting: {', '.join(setting)}. "
        f"Shot type: {shot_type}. "
        f"Action: {', '.join(actions)}. "
        f"Previous action handoff: {continuity.get('last_action', 'none')}. "
        f"Persistent visual anchors: {', '.join(continuity.get('anchors', [])[:6]) if continuity.get('anchors') else 'keep character design and world style consistent'}. "
        f"Important props: {', '.join(props) if props else 'only props described by the narration'}. "
        f"Mood: {', '.join(mood)}. "
        "Composition must make the story action readable at first glance, with foreground story objects, midground characters, and background world context. "
        "Keep spatial logic from the previous scene unless the narration clearly changes location. "
        "Avoid unrelated cabins, clean modern streets, fantasy armor, random portraits, extra characters, or objects not implied by the narration. "
        f"{style}. Scene context: {compact}"
    )
    return {
        "prompt": prompt,
        "must_show": must_show,
        "setting": setting,
        "actions": actions,
        "props": props,
        "shot_type": shot_type,
    }


def update_visual_continuity(previous, visual):
    anchors = list(previous.get("anchors") or [])
    for key in ("must_show", "setting", "props"):
        for item in visual.get(key) or []:
            if any(token in item.lower() for token in ["lam tich", "tan da", "junkyard", "crimson red sky", "overturned truck", "concrete wall", "safe-zone wall", "can of meat"]):
                add_unique(anchors, item)
    anchors = anchors[-8:]
    last_action = ", ".join((visual.get("actions") or [])[:2]) or previous.get("last_action", "none")
    summary_parts = []
    if anchors:
        summary_parts.append("anchors: " + ", ".join(anchors[:5]))
    if last_action:
        summary_parts.append("last action: " + last_action)
    return {
        "anchors": anchors,
        "last_action": last_action,
        "summary": "; ".join(summary_parts) if summary_parts else "continue same story world and character identity",
    }


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
    continuity = {"summary": "start of the story sequence", "anchors": [], "last_action": "none"}
    for index, narration in enumerate(groups, 1):
        visual = visual_prompt_data(narration, style, continuity, index)
        current_continuity = dict(continuity)
        scenes.append(
            {
                "id": f"scene-{index:03d}",
                "duration": 12,
                "image": f"assets/scene-{index:03d}.png",
                "audio": f"assets/scene-{index:03d}.mp3",
                "narration": narration,
                "subtitle": narration if args.subtitles else "",
                "text": args.title if index == 1 and args.title_overlay else "",
                "image_prompt": visual["prompt"],
                "visual_must_show": visual["must_show"],
                "visual_setting": visual["setting"],
                "visual_action": visual["actions"],
                "visual_props": visual["props"],
                "visual_shot_type": visual["shot_type"],
                "visual_continuity": current_continuity,
                "negative_prompt": DEFAULT_NEGATIVE,
            }
        )
        continuity = update_visual_continuity(continuity, visual)

    config = {
        "title": args.title or source.stem,
        "language": args.language,
        "font": "Arial",
        "word_count": word_count,
        "words_per_image_target": args.words_per_image,
        "visual_continuity_version": 1,
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
        must = html.escape(", ".join(scene.get("visual_must_show") or [])[:220])
        cards.append(f"<figure><img src='{image}'><figcaption><b>{index:03d}</b>. {text}<br><span>{must}</span></figcaption></figure>")
    page = """<!doctype html>
<meta charset="utf-8">
<title>Contact Sheet</title>
<style>
body{font-family:Arial,sans-serif;background:#111;color:#eee;margin:24px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}
figure{margin:0;background:#1c1c1c;padding:10px;border-radius:6px}
img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}
figcaption{font-size:12px;line-height:1.35;margin-top:8px;color:#ccc}
figcaption span{display:block;margin-top:6px;color:#8fd0ff}
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
    creationflags = 0
    if sys.platform == "win32" and (args.run_mode == "work" or args.gentle_mode):
        creationflags = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
    subprocess.Popen(
        [str(python), "-s", str(main), "--windows-standalone-build", "--lowvram"],
        cwd=str(comfy_root),
        stdout=out,
        stderr=err,
        creationflags=creationflags,
    )
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
    parser.add_argument("--voice-style", choices=["plain", "story-emotional", "wasteland-dark"], default="story-emotional")
    parser.add_argument("--character-bible", type=Path, help="Optional JSON file with persistent character voice traits.")
    parser.add_argument("--words-per-image", type=int, default=32)
    parser.add_argument("--min-scenes", type=int, default=50)
    parser.add_argument("--max-scenes", type=int, default=90)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--image-preset", choices=["safe", "balanced", "quality"], default="balanced")
    parser.add_argument(
        "--run-mode",
        choices=["work", "overnight"],
        default="overnight",
        help="work = lighter background generation; overnight = faster batch generation.",
    )
    parser.add_argument("--gentle-mode", action="store_true", help="Run image generation more politely for 2GB VRAM machines.")
    parser.add_argument("--image-delay", type=float, default=0.0, help="Seconds to pause between image batches.")
    parser.add_argument("--image-priority", choices=["normal", "below-normal", "idle"], default="normal")
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
    if args.run_mode == "work" or args.gentle_mode:
        args.batch_size = 1
        if args.image_delay <= 0:
            args.image_delay = 8
        if args.image_priority == "normal":
            args.image_priority = "below-normal"
    elif args.run_mode == "overnight":
        if args.batch_size == 1:
            args.batch_size = 5
        if args.image_delay <= 0:
            args.image_delay = 0
        if args.image_priority == "normal":
            args.image_priority = "normal"

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
        "--delay-between-batches",
        str(args.image_delay),
        "--process-priority",
        args.image_priority,
    ]
    voice_cmd = [
        sys.executable,
        str(scripts / "generate_voice_edge.py"),
        "--storyboard",
        str(storyboard),
        "--voice",
        args.voice,
        "--voice-style",
        args.voice_style,
    ]
    character_bible = args.character_bible or (project / "character_voice_bible.json")
    if character_bible.exists():
        voice_cmd.extend(["--character-bible", str(character_bible)])
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
