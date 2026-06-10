#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".webp"]

APPROVED_WASTELAND_REFERENCE = (
    "Use Thanh's approved visual benchmark: a cinematic 16:9 wasteland shelter scene where the dirty but beautiful "
    "young scavenger woman sits/kneels in the left third, the injured black-clad man lies or half-reclines in the "
    "right third, a warm oil lantern glows between them, torn tarp/canvas frames the top and right side, foreground "
    "has rusty bucket/bottle/scrap survival props, and the background opens to a hazy ruined industrial wasteland. "
    "Warm amber practical light contrasts with pale cold daylight; faces remain readable, anatomically natural, gritty, emotional, and realistic."
)


def resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def scene_score(scene: dict) -> int:
    text = " ".join(
        str(scene.get(key, ""))
        for key in (
            "narration",
            "prompt",
            "visual_must_show",
            "visual_action",
            "visual_props",
            "visual_shot_type",
        )
    ).lower()
    score = 0
    for word in [
        "mở mắt",
        "chết",
        "máu",
        "xác",
        "chó",
        "quái",
        "gầm xe",
        "dao",
        "thịt hộp",
        "nắm chặt",
        "kéo",
        "tấn công",
        "nguy hiểm",
        "lần đầu",
        "bầu trời",
        "thành",
        "nhân vật",
    ]:
        if word in text:
            score += 3
    if "close" in text or "pov" in text or "low" in text:
        score += 1
    return score


def clean_prompt(prompt: str) -> str:
    return re.sub(r"\s+", " ", prompt).strip()


def sanitize_for_chatgpt(text: str) -> str:
    text = str(text or "")
    replacements = [
        (r"\bgore\b", "graphic injury"),
        (r"\bopen wounds?\b", "covered injury"),
        (r"\bmutilation\b", "visible danger"),
        (r"\bexposed organs?\b", "serious injury"),
        (r"\bexplicit violence\b", "direct violence"),
        (r"\bviolent\b", "dangerous"),
        (r"\bblack blood\b", "dark injury stains"),
        (r"\bdark blood stains\b", "dark injury stains"),
        (r"\bblood-stained\b", "dirt-stained"),
        (r"\bblood\b", "injury marks"),
        (r"\bfresh human corpse on the ground\b", "an ominous covered bundle in the distance"),
        (r"\bhuman corpse\b", "covered bundle"),
        (r"\bcorpse\b", "ominous covered bundle"),
        (r"\bdead body\b", "covered bundle"),
        (r"\bbody-horror genetic collapse tension\b", "tense radiation sickness atmosphere"),
        (r"\bgenetic collapse\b", "radiation sickness"),
        (r"\bbody horror\b", "medical survival tension"),
        (r"\bseeping\b", "showing through"),
        (r"\btorn flesh\b", "serious injury covered by bandages"),
        (r"\bmutated two-jawed dogs tearing at\b", "mutated scavenger dogs threatening"),
        (r"\btearing at\b", "menacing"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    vietnamese_replacements = [
        ("máu đen", "vệt thương tối"),
        ("máu", "vết thương"),
        ("xác người", "một bóng người được phủ vải ở xa"),
        ("xác chết", "một bóng người được phủ vải ở xa"),
        ("người chết", "người bất động được phủ vải"),
        ("xác", "bóng người phủ vải"),
        ("thịt nát", "vết thương nặng đã được che bằng băng bẩn"),
        ("gen sụp đổ", "bệnh nhiễm xạ nặng"),
        ("chó hai hàm đang cúi đầu xé", "chó biến dị đang đe dọa gần"),
        ("xé", "đe dọa"),
    ]
    for source, replacement in vietnamese_replacements:
        text = re.sub(re.escape(source), replacement, text, flags=re.IGNORECASE)
    return clean_prompt(text)


def manual_filename(index: int) -> str:
    return f"manual-scene-{index:03d}.png"


def build_chatgpt_prompt(scene: dict, index: int, width: int, height: int) -> str:
    base_prompt = sanitize_for_chatgpt(scene.get("prompt") or scene.get("image_prompt") or "")
    must_show = sanitize_for_chatgpt(str(scene.get("visual_must_show", "")))
    action = sanitize_for_chatgpt(str(scene.get("visual_action", "")))
    continuity = sanitize_for_chatgpt(str(scene.get("visual_continuity", "")))
    narration = sanitize_for_chatgpt(str(scene.get("narration", "")))
    return f"""Create one cinematic story illustration for scene {index}.

Output requirement:
- Aspect ratio/resolution target: {width}x{height}
- No text, no subtitles, no watermark, no logo
- Ultra realistic cinematic style, not anime, not cartoon
- Keep character identity and clothing consistent if this is part of a series
- The image must match the narration exactly, not just look beautiful
- Keep it platform-safe: imply danger through posture, lighting, dirt, bandages, covered shapes, and atmosphere; do not show direct injury detail or active harm.
- Faces matter: use clear natural eyes, nose, mouth, and jaw; no melted features, no warped face, no broken anatomy.

Approved visual benchmark:
{APPROVED_WASTELAND_REFERENCE}

Composition rule:
- For Lâm Tịch + Tần Dã shelter scenes, follow the benchmark composition unless the narration clearly changes location.
- Lâm Tịch: left side, beautiful youthful maiden face, soft natural delicate features under grime, clear tired eyes, torn gray-brown scavenger clothes, hungry and exhausted, pretty but still believable in the wasteland.
- Tần Dã: right side, lying or half-reclining because he cannot stand, black tactical clothing, bandaged abdomen, righteous/protective expression.
- Keep oil lantern / dirty survival props / torn tarp / ruined wasteland depth whenever they fit the scene.
- If the story beat implies severe danger or injury, depict it as survival aftermath: dirty bandages, dark stains on cloth, covered bundles in the distance, anxious faces, and tense blocking.

Narration context:
{narration}

MUST SHOW:
{must_show or "The exact subject, location, action, and props described by the narration."}

Current action:
{action or "Show the main action in the narration clearly."}

Continuity from previous scene:
{continuity or "Maintain the same story world, character design, clothing, props, and atmosphere."}

Image prompt:
{base_prompt}
"""


def existing_manual_image(manual_dir: Path, index: int) -> Path | None:
    stem = f"manual-scene-{index:03d}"
    for ext in IMAGE_EXTS:
        candidate = manual_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare manual ChatGPT image prompts for hybrid image generation.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--ratio", type=float, default=0.5, help="Fraction of scenes assigned to manual ChatGPT images.")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--overwrite-assignments", action="store_true")
    parser.add_argument("--import-existing", action="store_true", help="Attach existing manual images to storyboard if found.")
    args = parser.parse_args()

    storyboard = args.storyboard.resolve()
    base = storyboard.parent
    manual_dir = base / "assets" / "manual-chatgpt"
    manual_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(storyboard.read_text(encoding="utf-8-sig"))
    scenes = data.get("scenes") or []
    if not scenes:
        raise SystemExit("Storyboard has no scenes.")

    target_count = max(1, round(len(scenes) * max(0.0, min(1.0, args.ratio))))
    existing_manual = [
        index
        for index, scene in enumerate(scenes, start=1)
        if scene.get("image_provider") == "manual-chatgpt"
    ]
    if args.overwrite_assignments or not existing_manual:
        ranked = sorted(range(1, len(scenes) + 1), key=lambda i: (scene_score(scenes[i - 1]), -i), reverse=True)
        selected = set(ranked[:target_count])
        for index, scene in enumerate(scenes, start=1):
            if index in selected:
                scene["image_provider"] = "manual-chatgpt"
                scene["manual_image_expected"] = f"assets/manual-chatgpt/{manual_filename(index)}"
                if not scene.get("image") or args.overwrite_assignments:
                    scene["image"] = scene["manual_image_expected"]
            elif scene.get("image_provider") == "manual-chatgpt":
                scene.pop("image_provider", None)
                scene.pop("manual_image_expected", None)

    assignments = []
    for index, scene in enumerate(scenes, start=1):
        if scene.get("image_provider") != "manual-chatgpt":
            continue
        found = existing_manual_image(manual_dir, index)
        if found and args.import_existing:
            scene["image"] = str(found.relative_to(base)).replace("\\", "/")
            scene["manual_image_status"] = "found"
        else:
            scene["manual_image_status"] = "needed"
        assignments.append(
            {
                "scene": index,
                "expected_file": f"assets/manual-chatgpt/{manual_filename(index)}",
                "status": scene["manual_image_status"],
                "prompt": build_chatgpt_prompt(scene, index, args.width, args.height),
            }
        )

    prompts_md = base / "chatgpt_image_prompts.md"
    manifest = base / "manual-chatgpt-manifest.json"
    lines = [
        "# Manual ChatGPT Image Prompts",
        "",
        f"Storyboard: `{storyboard}`",
        f"Manual folder: `{manual_dir}`",
        "",
        "Create images in ChatGPT app, then save each file using the exact expected filename.",
        "After files are saved, rerun this script with `--import-existing`, then render/validate.",
        "",
    ]
    for item in assignments:
        lines.extend(
            [
                f"## Scene {item['scene']:03d}",
                "",
                f"Expected file: `{item['expected_file']}`",
                "",
                "```text",
                item["prompt"].strip(),
                "```",
                "",
            ]
        )
    prompts_md.write_text("\n".join(lines), encoding="utf-8")
    manifest.write_text(json.dumps({"manual_dir": str(manual_dir), "assignments": assignments}, ensure_ascii=False, indent=2), encoding="utf-8")
    storyboard.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"storyboard": str(storyboard), "manual_dir": str(manual_dir), "prompts": str(prompts_md), "manual_scenes": len(assignments)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
