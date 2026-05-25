#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".webp"]


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


def manual_filename(index: int) -> str:
    return f"manual-scene-{index:03d}.png"


def build_chatgpt_prompt(scene: dict, index: int, width: int, height: int) -> str:
    base_prompt = clean_prompt(scene.get("prompt") or scene.get("image_prompt") or "")
    must_show = clean_prompt(str(scene.get("visual_must_show", "")))
    action = clean_prompt(str(scene.get("visual_action", "")))
    continuity = clean_prompt(str(scene.get("visual_continuity", "")))
    narration = clean_prompt(str(scene.get("narration", "")))
    return f"""Create one cinematic story illustration for scene {index}.

Output requirement:
- Aspect ratio/resolution target: {width}x{height}
- No text, no subtitles, no watermark, no logo
- Ultra realistic cinematic style, not anime, not cartoon
- Keep character identity and clothing consistent if this is part of a series
- The image must match the narration exactly, not just look beautiful

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
