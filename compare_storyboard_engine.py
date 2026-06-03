#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUNTIME_PYTHON = ROOT
DEFAULT_CASES = {
    "tap02p1": {
        "source": Path(r"E:\ThanhMV\auto-video-generator\projects\storyboards\tap-02-storyboards\phan-01-duong-ray-khong-dan-ve-nha\source.txt"),
        "highlights": [14, 34, 69],
    },
    "tap02p2": {
        "source": Path(r"E:\ThanhMV\auto-video-generator\projects\storyboards\tap-02-storyboards\phan-02-ga-xam\source.txt"),
        "highlights": [12, 22, 29, 47],
    },
    "tap02p3": {
        "source": Path(r"E:\ThanhMV\auto-video-generator\projects\storyboards\tap-02-storyboards\phan-03-doan-thiet-oa\source.txt"),
        "highlights": [1, 24, 31, 34],
    },
    "tap02p4": {
        "source": Path(r"E:\ThanhMV\auto-video-generator\projects\storyboards\tap-02-storyboards\phan-04-duong-ham-so-4\source.txt"),
        "highlights": [52, 64, 139, 145],
    },
    "tap02p5": {
        "source": Path(r"E:\ThanhMV\auto-video-generator\projects\storyboards\tap-02-storyboards\phan-05-nguoi-cua-ngan-thu\source.txt"),
        "highlights": [5, 8, 16, 25, 29, 30],
    },
    "tap02p6": {
        "source": Path(r"E:\ThanhMV\auto-video-generator\projects\storyboards\tap-02-storyboards\phan-06-can-cu-tam\source.txt"),
        "highlights": [12, 31, 33, 42, 45, 51],
    },
}

GENERIC_DIALOGUE_SHOT = "dialogue beat shot with the current speaker, listener, and the emotional exchange clearly readable"


def run(cmd, cwd=None):
    subprocess.run(cmd, cwd=cwd, check=True)


def run_capture(cmd, cwd=None):
    return subprocess.check_output(cmd, cwd=cwd)


def export_ref_file(ref: str, relpath: str, out_path: Path):
    try:
        data = run_capture(["git", "show", f"{ref}:{relpath}"], cwd=ROOT)
        out_path.write_bytes(data)
        return True
    except subprocess.CalledProcessError:
        return False


def prepare_baseline_tree(ref: str, tmpdir: Path) -> Path:
    script_dir = tmpdir / "baseline"
    script_dir.mkdir(parents=True, exist_ok=True)
    needed = [
        "run_story_pipeline.py",
        "validate_storyboard.py",
        "path_defaults.py",
        "video_presets.py",
    ]
    for rel in needed:
        target = script_dir / rel
        ok = export_ref_file(ref, rel, target)
        if not ok:
            shutil.copy2(ROOT / rel, target)
    return script_dir


def build_storyboard(script_dir: Path, source: Path, project_dir: Path):
    project_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(script_dir / "run_story_pipeline.py"),
        "--source",
        str(source),
        "--project",
        str(project_dir),
        "--words-per-image",
        "24",
        "--min-scenes",
        "0",
        "--max-scenes",
        "160",
        "--skip-images",
        "--skip-voice",
        "--skip-sfx",
        "--skip-render",
    ]
    run(cmd, cwd=ROOT)
    return project_dir / "storyboard.json"


def load_storyboard(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def metrics(data: dict):
    scenes = data["scenes"]
    shot_counts = Counter(s.get("visual_shot_type", "") for s in scenes)
    focus_counts = Counter(s.get("beat_type") or s.get("focus_beat", "") for s in scenes)
    return {
        "scene_count": len(scenes),
        "generic_dialogue": shot_counts.get(GENERIC_DIALOGUE_SHOT, 0),
        "top_shots": shot_counts.most_common(8),
        "top_focus": focus_counts.most_common(8),
    }


def scene_summary(scene: dict):
    return {
        "narration": scene.get("narration", ""),
        "focus": scene.get("beat_type") or scene.get("focus_beat", ""),
        "setting": scene.get("visual_setting", []),
        "action": scene.get("visual_action", []),
        "shot": scene.get("visual_shot_type", ""),
        "center_subject": scene.get("scene_center_subject", ""),
        "center_object": scene.get("scene_center_object", ""),
    }


def compare_case(case_name: str, baseline_data: dict, current_data: dict, highlights):
    result = {
        "baseline_metrics": metrics(baseline_data),
        "current_metrics": metrics(current_data),
        "highlights": [],
    }
    for idx in highlights:
        if idx <= len(baseline_data["scenes"]) and idx <= len(current_data["scenes"]):
            result["highlights"].append(
                {
                    "scene": idx,
                    "baseline": scene_summary(baseline_data["scenes"][idx - 1]),
                    "current": scene_summary(current_data["scenes"][idx - 1]),
                }
            )
    return result


def render_markdown(report: dict) -> str:
    lines = []
    lines.append(f"# Storyboard Engine Compare Report")
    lines.append("")
    lines.append(f"- Baseline ref: `{report['baseline_ref']}`")
    lines.append(f"- Current ref: working tree at `{report['current_head']}`")
    lines.append(f"- Generated: `{report['generated_at']}`")
    lines.append("")
    for case_name, case_data in report["cases"].items():
        lines.append(f"## {case_name}")
        b = case_data["baseline_metrics"]
        c = case_data["current_metrics"]
        lines.append("")
        lines.append(f"- Scenes: `{b['scene_count']}` -> `{c['scene_count']}`")
        lines.append(f"- Generic dialogue shots: `{b['generic_dialogue']}` -> `{c['generic_dialogue']}`")
        lines.append("")
        lines.append("### Top Shots")
        lines.append("")
        lines.append("| baseline | current |")
        lines.append("|---|---|")
        for i in range(max(len(b["top_shots"]), len(c["top_shots"]))):
            left = ""
            right = ""
            if i < len(b["top_shots"]):
                left = f"`{b['top_shots'][i][0]}` {b['top_shots'][i][1]}"
            if i < len(c["top_shots"]):
                right = f"`{c['top_shots'][i][0]}` {c['top_shots'][i][1]}"
            lines.append(f"| {left} | {right} |")
        lines.append("")
        lines.append("### Highlight Scenes")
        lines.append("")
        for item in case_data["highlights"]:
            lines.append(f"#### Scene {item['scene']}")
            lines.append("")
            lines.append(f"**Narration**: {item['current']['narration']}")
            lines.append("")
            lines.append(f"- Baseline focus: `{item['baseline']['focus']}`")
            lines.append(f"- Current focus: `{item['current']['focus']}`")
            lines.append(f"- Baseline shot: `{item['baseline']['shot']}`")
            lines.append(f"- Current shot: `{item['current']['shot']}`")
            lines.append(f"- Baseline setting: `{'; '.join(item['baseline']['setting'])}`")
            lines.append(f"- Current setting: `{'; '.join(item['current']['setting'])}`")
            lines.append(f"- Baseline action: `{'; '.join(item['baseline']['action'])}`")
            lines.append(f"- Current action: `{'; '.join(item['current']['action'])}`")
            lines.append(f"- Baseline center object: `{item['baseline']['center_object']}`")
            lines.append(f"- Current center object: `{item['current']['center_object']}`")
            lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compare a baseline storyboard engine ref against the current working tree across multiple parts.")
    parser.add_argument("--baseline-ref", required=True, help="Git ref or tag to compare against, e.g. checkpoint-storyboard-engine-2026-06-02")
    parser.add_argument("--cases", nargs="*", default=list(DEFAULT_CASES.keys()), help="Subset of default cases to compare")
    args = parser.parse_args()

    cases = {name: DEFAULT_CASES[name] for name in args.cases}
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    compare_root = ROOT / "scratch" / "compare_reports" / now
    baseline_root = compare_root / "baseline"
    current_root = compare_root / "current"
    compare_root.mkdir(parents=True, exist_ok=True)

    current_head = run_capture(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT).decode().strip()

    temp_root = compare_root / "_tmp_baseline"
    if temp_root.exists():
        shutil.rmtree(temp_root)
    baseline_script_dir = prepare_baseline_tree(args.baseline_ref, temp_root)
    report = {
        "baseline_ref": args.baseline_ref,
        "current_head": current_head,
        "generated_at": now,
        "cases": {},
    }

    for case_name, cfg in cases.items():
        baseline_storyboard = build_storyboard(baseline_script_dir, cfg["source"], baseline_root / case_name)
        current_storyboard = build_storyboard(ROOT, cfg["source"], current_root / case_name)
        baseline_data = load_storyboard(baseline_storyboard)
        current_data = load_storyboard(current_storyboard)
        report["cases"][case_name] = compare_case(case_name, baseline_data, current_data, cfg["highlights"])

    (compare_root / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (compare_root / "report.md").write_text(render_markdown(report), encoding="utf-8")
    print(str(compare_root / "report.md"))


if __name__ == "__main__":
    main()
