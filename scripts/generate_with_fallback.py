#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable


IMAGE_PROVIDERS = [
    {
        "name": "openai",
        "env": "OPENAI_API_KEY",
        "cmd": [PYTHON, str(ROOT / "generate_assets_openai.py")],
    },
    {
        "name": "replicate",
        "env": "REPLICATE_API_TOKEN",
        "cmd": [PYTHON, str(ROOT / "generate_images_replicate.py")],
    },
    {
        "name": "fal",
        "env": "FAL_KEY",
        "cmd": [PYTHON, str(ROOT / "generate_images_fal.py")],
    },
    {
        "name": "stability",
        "env": "STABILITY_API_KEY",
        "cmd": [PYTHON, str(ROOT / "generate_images_stability.py")],
    },
    {
        "name": "pollinations",
        "env": "POLLINATIONS_API_KEY",
        "cmd": [PYTHON, str(ROOT / "generate_images_pollinations.py")],
    },
    {
        "name": "runway",
        "env": "RUNWAYML_API_SECRET",
        "cmd": [PYTHON, str(ROOT / "generate_runway.py"), "--mode", "image"],
    },
]


VIDEO_PROVIDERS = [
    {
        "name": "runway",
        "env": "RUNWAYML_API_SECRET",
        "cmd": [PYTHON, str(ROOT / "generate_runway.py"), "--mode", "video"],
    },
    {
        "name": "luma",
        "env": "LUMAAI_API_KEY",
        "cmd": [PYTHON, str(ROOT / "generate_luma.py")],
    },
    {
        "name": "local",
        "env": "",
        "cmd": [PYTHON, str(ROOT / "generate_video_local.py")],
    },
]


def env_candidates(name):
    if not name:
        return [{"slot": "local", "value": ""}]
    candidates = []
    seen = set()
    base_value = os.environ.get(name)
    if base_value:
        candidates.append({"slot": name, "value": base_value})
        seen.add(base_value)
    csv_value = os.environ.get(f"{name}_LIST")
    if csv_value:
        for index, value in enumerate([item.strip() for item in csv_value.split(",") if item.strip()], start=1):
            if value not in seen:
                candidates.append({"slot": f"{name}_LIST[{index}]", "value": value})
                seen.add(value)
    for index in range(1, 21):
        value = os.environ.get(f"{name}_{index}")
        if value and value not in seen:
            candidates.append({"slot": f"{name}_{index}", "value": value})
            seen.add(value)
    return candidates


def append_common(cmd, storyboard, overwrite):
    result = [*cmd, "--storyboard", str(storyboard)]
    if overwrite:
        result.append("--overwrite")
    return result


def run_provider(provider, storyboard, overwrite, candidate):
    cmd = append_common(provider["cmd"], storyboard, overwrite)
    env = os.environ.copy()
    if provider["env"] and candidate["value"]:
        env[provider["env"]] = candidate["value"]
    completed = subprocess.run(cmd, text=True, capture_output=True, env=env)
    return {
        "provider": provider["name"],
        "key_slot": candidate["slot"],
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def provider_by_name(providers, names):
    wanted = [name.strip().lower() for name in names.split(",") if name.strip()]
    if not wanted:
        return providers
    lookup = {provider["name"]: provider for provider in providers}
    missing = [name for name in wanted if name not in lookup]
    if missing:
        raise SystemExit(f"Unknown provider(s): {', '.join(missing)}")
    return [lookup[name] for name in wanted]


def main():
    parser = argparse.ArgumentParser(description="Generate images/videos by trying providers in fallback order.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--kind", choices=["image", "video"], required=True)
    parser.add_argument("--providers", default="", help="Comma-separated override, e.g. stability,runway.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--continue-on-success", action="store_true", help="Run all available providers instead of stopping after first success.")
    args = parser.parse_args()

    storyboard = args.storyboard.resolve()
    providers = IMAGE_PROVIDERS if args.kind == "image" else VIDEO_PROVIDERS
    providers = provider_by_name(providers, args.providers)

    attempts = []
    successes = []
    for provider in providers:
        candidates = env_candidates(provider["env"])
        if not candidates and provider.get("optional_env"):
            candidates = [{"slot": "no-key", "value": ""}]
        if not candidates:
            attempts.append({"provider": provider["name"], "skipped": True, "reason": f"{provider['env']} missing"})
            continue
        for candidate in candidates:
            attempt = run_provider(provider, storyboard, args.overwrite, candidate)
            attempts.append(attempt)
            if attempt["returncode"] == 0:
                successes.append(provider["name"])
                if not args.continue_on_success:
                    break
        if successes and not args.continue_on_success:
            break

    result = {
        "kind": args.kind,
        "storyboard": str(storyboard),
        "success": bool(successes),
        "successes": successes,
        "attempts": attempts,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not successes:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
