#!/usr/bin/env python3

VIDEO_PRESETS = {
    "tiktok": {
        "label": "TikTok / YouTube Shorts / Reels",
        "aspect": "9:16",
        "width": 1080,
        "height": 1920,
        "fps": 30,
    },
    "youtube": {
        "label": "YouTube landscape",
        "aspect": "16:9",
        "width": 1920,
        "height": 1080,
        "fps": 30,
    },
}

ASPECTS = {preset["aspect"]: (preset["width"], preset["height"]) for preset in VIDEO_PRESETS.values()}
ASPECTS["1:1"] = (1080, 1080)


def normalize_format(value):
    if not value:
        return None
    key = value.strip().lower()
    aliases = {
        "short": "tiktok",
        "shorts": "tiktok",
        "youtube-shorts": "tiktok",
        "reels": "tiktok",
        "yt": "youtube",
        "landscape": "youtube",
        "16:9": "youtube",
        "9:16": "tiktok",
    }
    return aliases.get(key, key)


def preset_for(value):
    key = normalize_format(value)
    if key not in VIDEO_PRESETS:
        choices = ", ".join(sorted(VIDEO_PRESETS))
        raise ValueError(f"Unknown video format '{value}'. Use one of: {choices}")
    return VIDEO_PRESETS[key]


def apply_video_format(config, value):
    preset = preset_for(value)
    config["video_format"] = normalize_format(value)
    config["aspect"] = preset["aspect"]
    config["width"] = preset["width"]
    config["height"] = preset["height"]
    config["fps"] = int(config.get("fps") or preset["fps"])
    return config
