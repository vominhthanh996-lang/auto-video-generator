#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Audit storyboard visual prompts for story-beat coverage.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--min-must-show", type=int, default=3)
    args = parser.parse_args()

    config = json.loads(args.storyboard.read_text(encoding="utf-8-sig"))
    warnings = []
    for index, scene in enumerate(config.get("scenes") or [], 1):
        must_show = scene.get("visual_must_show") or []
        actions = scene.get("visual_action") or []
        shot_type = scene.get("visual_shot_type") or ""
        continuity = scene.get("visual_continuity") or {}
        prompt = scene.get("image_prompt") or ""
        narration = scene.get("narration") or ""
        if len(must_show) < args.min_must_show:
            warnings.append(
                {
                    "scene": scene.get("id") or f"scene-{index:03d}",
                    "issue": "weak visual_must_show",
                    "must_show": must_show,
                    "narration_preview": narration[:180],
                }
            )
        if "MUST SHOW:" not in prompt:
            warnings.append(
                {
                    "scene": scene.get("id") or f"scene-{index:03d}",
                    "issue": "prompt missing MUST SHOW contract",
                    "narration_preview": narration[:180],
                }
            )
        if "CONTINUITY FROM PREVIOUS SCENE:" not in prompt:
            warnings.append(
                {
                    "scene": scene.get("id") or f"scene-{index:03d}",
                    "issue": "prompt missing continuity contract",
                    "narration_preview": narration[:180],
                }
            )
        if not actions:
            warnings.append(
                {
                    "scene": scene.get("id") or f"scene-{index:03d}",
                    "issue": "missing visual action",
                    "narration_preview": narration[:180],
                }
            )
        if not shot_type:
            warnings.append(
                {
                    "scene": scene.get("id") or f"scene-{index:03d}",
                    "issue": "missing shot type",
                    "narration_preview": narration[:180],
                }
            )
        if index > 1 and not continuity.get("anchors"):
            warnings.append(
                {
                    "scene": scene.get("id") or f"scene-{index:03d}",
                    "issue": "missing continuity anchors",
                    "narration_preview": narration[:180],
                }
            )
        if "generic apocalypse wallpaper" not in prompt:
            warnings.append(
                {
                    "scene": scene.get("id") or f"scene-{index:03d}",
                    "issue": "prompt missing anti-generic instruction",
                    "narration_preview": narration[:180],
                }
            )

    result = {"storyboard": str(args.storyboard), "scenes": len(config.get("scenes") or []), "warnings": warnings}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
