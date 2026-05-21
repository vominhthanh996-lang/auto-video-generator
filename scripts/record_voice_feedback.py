#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


DEFAULT_PATH = Path(r"E:\ThanhMV\auto-video-generator\config\voice_learning.json")


def load(path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8-sig"))
    return {
        "rate_delta": 0,
        "comma_pause_delta": 0.0,
        "sentence_pause_delta": 0.0,
        "paragraph_pause_delta": 0.0,
        "samples": 0,
        "notes": [],
    }


def clamp(value, low, high):
    return max(low, min(high, value))


def main():
    parser = argparse.ArgumentParser(description="Record voice feedback and gently tune future narration pacing.")
    parser.add_argument(
        "--feedback",
        required=True,
        choices=["too-fast", "too-slow", "too-flat", "too-dramatic", "not-cold-enough", "not-evil-enough", "too-fake", "good"],
    )
    parser.add_argument("--character", default="", help="Optional character name for character-specific learning.")
    parser.add_argument("--trait", default="", help="Optional trait/archetype for trait-specific learning.")
    parser.add_argument("--note", default="")
    parser.add_argument("--learning-file", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()

    data = load(args.learning_file)
    data["samples"] = int(data.get("samples", 0)) + 1
    target = data
    if args.character:
        target = data.setdefault("characters", {}).setdefault(args.character, {"samples": 0})
        target["samples"] = int(target.get("samples", 0)) + 1
    elif args.trait:
        target = data.setdefault("traits", {}).setdefault(args.trait, {"samples": 0})
        target["samples"] = int(target.get("samples", 0)) + 1

    if args.feedback == "too-fast":
        target["rate_delta"] = clamp(int(target.get("rate_delta", 0)) - 3, -18, 8)
        target["sentence_pause_delta"] = clamp(float(target.get("sentence_pause_delta", 0)) + 0.08, -0.25, 0.6)
        target["paragraph_pause_delta"] = clamp(float(target.get("paragraph_pause_delta", 0)) + 0.1, -0.3, 0.8)
    elif args.feedback == "too-slow":
        target["rate_delta"] = clamp(int(target.get("rate_delta", 0)) + 3, -18, 8)
        target["sentence_pause_delta"] = clamp(float(target.get("sentence_pause_delta", 0)) - 0.06, -0.25, 0.6)
        target["paragraph_pause_delta"] = clamp(float(target.get("paragraph_pause_delta", 0)) - 0.08, -0.3, 0.8)
    elif args.feedback == "too-flat":
        target["comma_pause_delta"] = clamp(float(target.get("comma_pause_delta", 0)) + 0.03, -0.12, 0.25)
        target["sentence_pause_delta"] = clamp(float(target.get("sentence_pause_delta", 0)) + 0.08, -0.25, 0.6)
    elif args.feedback == "too-dramatic":
        target["comma_pause_delta"] = clamp(float(target.get("comma_pause_delta", 0)) - 0.03, -0.12, 0.25)
        target["sentence_pause_delta"] = clamp(float(target.get("sentence_pause_delta", 0)) - 0.08, -0.25, 0.6)
    elif args.feedback == "not-cold-enough":
        target["rate_delta"] = clamp(int(target.get("rate_delta", 0)) - 2, -18, 8)
        target["pitch_delta"] = clamp(int(target.get("pitch_delta", 0)) - 1, -8, 8)
        target["sentence_pause_delta"] = clamp(float(target.get("sentence_pause_delta", 0)) + 0.05, -0.25, 0.6)
    elif args.feedback == "not-evil-enough":
        target["rate_delta"] = clamp(int(target.get("rate_delta", 0)) - 3, -18, 8)
        target["pitch_delta"] = clamp(int(target.get("pitch_delta", 0)) - 2, -8, 8)
        target["sentence_pause_delta"] = clamp(float(target.get("sentence_pause_delta", 0)) + 0.08, -0.25, 0.6)
    elif args.feedback == "too-fake":
        target["pitch_delta"] = clamp(int(target.get("pitch_delta", 0)) // 2, -8, 8)
        target["comma_pause_delta"] = clamp(float(target.get("comma_pause_delta", 0)) - 0.02, -0.12, 0.25)
    if args.note:
        notes = target.setdefault("notes", [])
        notes.append(args.note)
        target["notes"] = notes[-20:]

    args.learning_file.parent.mkdir(parents=True, exist_ok=True)
    args.learning_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
