#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import sys
import subprocess
import tempfile
import re
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
WORK_ROOT = REPO_ROOT.parent

EXTRA_PACKAGES = Path(os.environ.get("AUTO_VIDEO_EXTRA_PACKAGES", str(WORK_ROOT / "python-packages")))
if EXTRA_PACKAGES.exists():
    sys.path.insert(0, str(EXTRA_PACKAGES))

import edge_tts


VOICE_PRESETS = {
    "vi-female": "vi-VN-HoaiMyNeural",
    "vi-male": "vi-VN-NamMinhNeural",
    "en-female": "en-US-JennyNeural",
    "en-male": "en-US-GuyNeural",
}

TTS_TIMEOUT_SECONDS = int(os.environ.get("AUTO_VIDEO_TTS_TIMEOUT_SECONDS", "90"))

VOICE_STYLES = {
    "plain": {
        "rate": "+0%",
        "pitch": "+0Hz",
        "comma_pause": 0.08,
        "sentence_pause": 0.18,
        "paragraph_pause": 0.3,
    },
    "story-emotional": {
        "rate": "-3%",
        "pitch": "-2Hz",
        "comma_pause": 0.04,
        "sentence_pause": 0.16,
        "paragraph_pause": 0.32,
        "dialogue_pause": 0.12,
        "scene_pause": 0.42,
        "danger_rate": "-1%",
        "soft_rate": "-7%",
        "dialogue_rate": "-2%",
        "inner_rate": "-8%",
        "reveal_rate": "-5%",
        "list_rate": "-1%",
        "cliffhanger_pause": 0.32,
        "reveal_pause": 0.34,
        "inner_pause": 0.26,
        "list_pause": 0.07,
        "hook_rate_delta": 1,
        "release_rate_delta": -1,
        "max_rate_jump": 5,
        "max_pitch_jump": 3,
        "max_unit_chars": 700,
    },
    "wasteland-dark": {
        "rate": "+3%",
        "pitch": "-3Hz",
        "max_inserted_pause": 0.0,
        "tight_punctuation": True,
        "short_sentence_as_comma": True,
        "comma_pause": 0.025,
        "sentence_pause": 0.07,
        "paragraph_pause": 0.12,
        "dialogue_pause": 0.04,
        "scene_pause": 0.2,
        "danger_rate": "+5%",
        "soft_rate": "-2%",
        "dialogue_rate": "+4%",
        "inner_rate": "-4%",
        "reveal_rate": "+0%",
        "list_rate": "+4%",
        "cliffhanger_pause": 0.09,
        "reveal_pause": 0.1,
        "inner_pause": 0.08,
        "list_pause": 0.02,
        "hook_rate_delta": 2,
        "release_rate_delta": -1,
        "max_rate_jump": 5,
        "max_pitch_jump": 3,
        "max_unit_chars": 700,
    },
}

DANGER_WORDS = (
    "chó", "thú", "biến dị", "máu", "chết", "xác", "dao", "gầm gừ", "móng vuốt",
    "mưa đen", "nhiễm xạ", "vết thương", "sụp đổ", "giết", "săn người",
    "truy đuổi", "cắn", "rúng động", "nổ súng", "gào", "rít lên",
)

SOFT_WORDS = (
    "im lặng", "nhắm mắt", "thở", "một ngày", "rất lâu", "xa xa", "cô độc",
    "lặng lẽ", "yếu", "đói", "đau", "mệt", "bầu trời", "không ai",
    "một mình", "run lên", "khô họng", "sống thêm", "nhìn lên",
)

MALE_NAMES = ("tần dã", "hàn thiên dực", "hắn", "người đàn ông", "nam nhân", "cha")
FEMALE_NAMES = ("lâm tịch", "nàng", "cô", "thiếu nữ", "mẹ")

CHARACTER_ARCHETYPES = {
    "honest": {
        "hints": ("thật thà", "chân thật", "thành thật", "ngây ngô", "chất phác"),
        "rate_delta": -2,
        "pitch_delta": 0,
        "pause_delta": 0.03,
    },
    "righteous": {
        "hints": ("chính khí", "ngay thẳng", "chính trực", "kiên định", "bảo vệ", "không lùi"),
        "rate_delta": -1,
        "pitch_delta": -1,
        "pause_delta": 0.02,
    },
    "evil": {
        "hints": ("tà ác", "ác độc", "nham hiểm", "tàn nhẫn", "độc ác", "sát ý"),
        "rate_delta": -4,
        "pitch_delta": -3,
        "pause_delta": 0.05,
    },
    "hypocrite": {
        "hints": ("giả nhân giả nghĩa", "đạo mạo", "ra vẻ", "miệng thì", "ngoài mặt", "giả vờ tử tế"),
        "rate_delta": -3,
        "pitch_delta": 1,
        "pause_delta": 0.04,
    },
    "flattering": {
        "hints": ("nịnh nọt", "lấy lòng", "xun xoe", "cười nịnh", "dạ dạ", "vâng vâng"),
        "rate_delta": 3,
        "pitch_delta": 2,
        "pause_delta": -0.04,
    },
    "spoiled": {
        "hints": ("nhõng nhẽo", "làm nũng", "phụng phịu", "dỗi", "hờn", "nũng nịu"),
        "rate_delta": -1,
        "pitch_delta": 3,
        "pause_delta": 0.03,
    },
    "cold": {
        "hints": ("lạnh lùng", "lạnh nhạt", "vô cảm", "bình tĩnh", "không cảm xúc", "lạnh xuống"),
        "rate_delta": -5,
        "pitch_delta": -2,
        "pause_delta": 0.04,
    },
    "afraid": {
        "hints": ("run rẩy", "sợ hãi", "hoảng", "kinh hãi", "tái mặt", "nín thở"),
        "rate_delta": 4,
        "pitch_delta": 2,
        "pause_delta": -0.02,
    },
}

INNER_WORDS = (
    "nàng nghĩ", "hắn nghĩ", "trong đầu", "trong lòng", "ký ức", "nhớ rõ",
    "nàng biết", "hắn biết", "chỉ có", "nếu như", "có lẽ", "vậy mà",
)

REVEAL_WORDS = (
    "không phải", "thật ra", "hóa ra", "cuối cùng", "đột nhiên", "ngay lúc đó",
    "đúng lúc đó", "bỗng", "nhưng", "vậy mà", "chỉ là", "thịt hộp",
)

LIST_MARKERS = (
    "thứ nhất", "thứ hai", "tiếp theo", "sau đó", "cuối cùng", "ngoài ra",
)


def resolve(base, value):
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def relpath(path, base):
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def run_quiet(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


async def synthesize(text, output, voice, rate, pitch):
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await asyncio.wait_for(communicate.save(str(output)), timeout=TTS_TIMEOUT_SECONDS)


def parse_rate(rate):
    try:
        return int(str(rate).replace("%", ""))
    except ValueError:
        return 0


def parse_pitch(pitch):
    try:
        return int(str(pitch).replace("Hz", ""))
    except ValueError:
        return 0


def format_rate(value):
    value = max(-35, min(20, int(value)))
    return f"{value:+d}%"


def format_pitch(value):
    value = max(-12, min(12, int(value)))
    return f"{value:+d}Hz"


def limited_step(current, previous, max_jump):
    if previous is None:
        return current
    if current > previous + max_jump:
        return previous + max_jump
    if current < previous - max_jump:
        return previous - max_jump
    return current


def load_learning(path):
    if not path or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_character_bible(path):
    if not path or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data


def apply_learning(profile, learning):
    adjusted = dict(profile)
    if not learning:
        return adjusted
    adjusted["rate"] = format_rate(parse_rate(adjusted["rate"]) + int(learning.get("rate_delta", 0)))
    adjusted["comma_pause"] = max(0.02, adjusted["comma_pause"] + float(learning.get("comma_pause_delta", 0)))
    adjusted["sentence_pause"] = max(0.05, adjusted["sentence_pause"] + float(learning.get("sentence_pause_delta", 0)))
    adjusted["paragraph_pause"] = max(0.1, adjusted["paragraph_pause"] + float(learning.get("paragraph_pause_delta", 0)))
    return adjusted


def is_dialogue(text):
    stripped = text.strip()
    return stripped.startswith(("\"", "'", "“", "‘", "「", "『", "-", "–")) or stripped.endswith(("\"", "”", "」", "』"))


def dialogue_lane(text):
    lower = text.lower()
    if any(name in lower for name in MALE_NAMES):
        return "male"
    if any(name in lower for name in FEMALE_NAMES):
        return "female"
    return "neutral"


def is_scene_break(text):
    stripped = text.strip()
    if not stripped:
        return False
    return stripped.startswith(("#", "Chương ", "Phần ")) or stripped in {"***", "---"}


def is_cliffhanger(text):
    stripped = text.strip()
    if stripped.endswith(("?", "!", "…", "...")):
        return True
    return len(stripped.split()) <= 8 and not is_dialogue(stripped)


def has_word(text, words):
    lower = text.lower()
    return any(word in lower for word in words)


def detect_archetype(text):
    lower = text.lower()
    for name, spec in CHARACTER_ARCHETYPES.items():
        if any(hint in lower for hint in spec["hints"]):
            return name
    return ""


def detect_archetypes(text, profile):
    found = []
    for _character_name, character in matched_characters(text, profile):
        found.extend(character.get("traits") or [])
    keyword = detect_archetype(text)
    if keyword:
        found.append(keyword)
    deduped = []
    for trait in found:
        if trait in CHARACTER_ARCHETYPES and trait not in deduped:
            deduped.append(trait)
    return deduped


def matched_characters(text, profile):
    lower = text.lower()
    matches = []
    bible = (profile.get("_character_bible") or {}).get("characters") or {}
    for character_name, character in bible.items():
        aliases = [character_name]
        aliases.extend(character.get("aliases") or [])
        if any(str(alias).lower() in lower for alias in aliases):
            matches.append((character_name, character))
    return matches


def resolve_voice(value):
    if not value:
        return None
    return VOICE_PRESETS.get(value, value)


def character_voice(character):
    return resolve_voice((character or {}).get("voice"))


def voice_for_character(character_name, profile):
    bible = (profile.get("_character_bible") or {}).get("characters") or {}
    return character_voice(bible.get(character_name))


def speaker_from_context(text, profile):
    matches = matched_characters(text, profile)
    if not matches:
        return None
    return matches[0][0]


def unit_opens_dialogue(text):
    return any(mark in text for mark in ('"', "“", "‘", "「", "『"))


def unit_closes_dialogue(text):
    stripped = text.rstrip()
    return stripped.endswith('"') or any(mark in text for mark in ("”", "’", "」", "』"))


def voice_for_text(text, default_voice, profile, speaker_hint=None):
    bible = profile.get("_character_bible") or {}
    narrator = (bible.get("narrator") or {}).get("voice")
    narrator_voice = resolve_voice(narrator) or default_voice
    if not is_dialogue(text):
        return narrator_voice
    if speaker_hint:
        voice = voice_for_character(speaker_hint, profile)
        resolved = resolve_voice(voice)
        if resolved:
            return resolved
    for _character_name, character in matched_characters(text, profile):
        voice = resolve_voice(character.get("voice"))
        if voice:
            return voice
    lane = dialogue_lane(text)
    defaults = bible.get("defaults") or {}
    voice = defaults.get(f"{lane}_dialogue_voice") or defaults.get("dialogue_voice")
    resolved = resolve_voice(voice)
    if resolved:
        return resolved
    return narrator_voice


def archetype_delta(traits, key):
    return sum(CHARACTER_ARCHETYPES[trait].get(key, 0) for trait in traits)


def learning_delta(text, traits, profile, key):
    learning = profile.get("_learning") or {}
    total = 0
    for character_name, _character in matched_characters(text, profile):
        total += learning.get("characters", {}).get(character_name, {}).get(key, 0)
    for trait in traits:
        total += learning.get("traits", {}).get(trait, {}).get(key, 0)
    return total


def is_inner_voice(text):
    return has_word(text, INNER_WORDS)


def is_reveal(text):
    return has_word(text, REVEAL_WORDS)


def is_list_like(text):
    stripped = text.strip().lower()
    if has_word(stripped, LIST_MARKERS):
        return True
    return len(re.findall(r"[,;，；]", stripped)) >= 3 and len(stripped.split()) >= 18


def line_gap(text, profile):
    archetypes = detect_archetypes(text, profile)
    if is_scene_break(text):
        return profile.get("scene_pause", profile["paragraph_pause"])
    if is_dialogue(text):
        base = profile.get("dialogue_pause", profile["sentence_pause"])
        base += archetype_delta(archetypes, "pause_delta")
        base += learning_delta(text, archetypes, profile, "sentence_pause_delta")
        minimum_gap = 0.02 if profile.get("tight_punctuation") else 0.08
        return max(minimum_gap, base)
    if is_cliffhanger(text):
        return profile.get("cliffhanger_pause", profile["sentence_pause"] + 0.15)
    if is_reveal(text):
        return profile.get("reveal_pause", profile["sentence_pause"] + 0.2)
    if is_inner_voice(text):
        return profile.get("inner_pause", profile["sentence_pause"] + 0.1)
    if is_list_like(text):
        return profile.get("list_pause", profile["comma_pause"])
    if "\n\n" in text:
        return profile["paragraph_pause"]
    if profile.get("tight_punctuation") and text.endswith(("?", "!", ":", "...")):
        return profile["sentence_pause"]
    if text.endswith(("?", "!", ":", "…", "...")):
        return profile["sentence_pause"] + 0.15
    if text.endswith((".", "。")):
        return profile["sentence_pause"]
    if text.endswith((",", ";", "，", "；")):
        return profile["comma_pause"]
    return profile["comma_pause"]


def split_performance_units(text, max_chars=180):
    normalized = re.sub(r"[ \t]+", " ", text.strip())
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    max_chars = max(700, int(max_chars))
    quote_pattern = re.compile(r'(".*?"|â€œ.*?â€|ã€Œ.*?ã€|ã€Ž.*?ã€)')
    merged_pieces = []
    for paragraph in re.split(r"\n\n+", normalized):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        position = 0
        blocks = []
        for match in quote_pattern.finditer(paragraph):
            if match.start() > position:
                blocks.append(paragraph[position:match.start()].strip())
            blocks.append(match.group(0).strip())
            position = match.end()
        if position < len(paragraph):
            blocks.append(paragraph[position:].strip())
        for block in [item for item in blocks if item]:
            if len(block) <= max_chars:
                merged_pieces.append(block)
                continue
            current = ""
            for sentence in re.split(r"(?<=[.!?â€¦ã€‚ï¼ï¼Ÿ])\s+", block):
                sentence = sentence.strip()
                if not sentence:
                    continue
                if current and len(current) + len(sentence) + 1 > max_chars:
                    merged_pieces.append(current.strip())
                    current = sentence
                else:
                    current = f"{current} {sentence}".strip()
            if current:
                merged_pieces.append(current.strip())
    return merged_pieces or [text]
    pieces = []
    for paragraph in re.split(r"(\n\n+)", normalized):
        if not paragraph.strip():
            continue
        parts = re.split(r"(?<=[.!?:;,…\"”」』])\s+", paragraph.strip())
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if len(part) <= max_chars:
                pieces.append(part)
                continue
            clauses = re.split(r"(?<=[,;，；])\s+", part)
            current = ""
            for clause in clauses:
                if current and len(current) + len(clause) > max_chars:
                    pieces.append(current.strip())
                    current = clause
                else:
                    current = f"{current} {clause}".strip()
            if current:
                pieces.append(current.strip())
    return pieces or [text]


def prepare_tts_text(text, profile):
    if not profile.get("tight_punctuation"):
        return text
    spoken = re.sub(r"[ \t]+", " ", text.strip())
    spoken = re.sub(r"\s*[,，]\s*", ", ", spoken)
    spoken = re.sub(r"\s*[;；:：]\s*", ", ", spoken)
    if profile.get("short_sentence_as_comma"):
        spoken = re.sub(r"\s*[.。]\s+(?=\S)", ", ", spoken)
        spoken = re.sub(r"\s*[!?！？]\s+(?=\S)", ", ", spoken)
    else:
        spoken = re.sub(r"\s*[.。]\s+(?=\S)", ". ", spoken)
        spoken = re.sub(r"\s*[!?！？]\s+(?=\S)", "! ", spoken)
    spoken = re.sub(r",\s*,+", ", ", spoken)
    spoken = re.sub(r"\s+", " ", spoken)
    return spoken.strip()


def sanitize_for_tts_fallback(text):
    spoken = text.strip()
    replacements = {
        '"': " ",
        "“": " ",
        "”": " ",
        "‘": " ",
        "’": " ",
        "「": " ",
        "」": " ",
        "『": " ",
        "』": " ",
    }
    for old, new in replacements.items():
        spoken = spoken.replace(old, new)
    spoken = re.sub(r"[#*_`~]+", " ", spoken)
    spoken = re.sub(r"\s*[-–—]\s*", ", ", spoken)
    spoken = re.sub(r"\s*[;:]\s*", ", ", spoken)
    spoken = re.sub(r"\s*[!?]+\s*", ". ", spoken)
    spoken = re.sub(r"\s*[.]+\s*", ". ", spoken)
    spoken = re.sub(r"\s*,\s*,+", ", ", spoken)
    spoken = re.sub(r"\s+", " ", spoken)
    return spoken.strip(" ,.")


def has_spoken_content(text):
    cleaned = sanitize_for_tts_fallback(text)
    return bool(re.search(r"[\w\u00C0-\u024F]", cleaned))


def rate_for_text(text, profile):
    archetypes = detect_archetypes(text, profile)
    if archetypes:
        base = profile.get("dialogue_rate" if is_dialogue(text) else "rate", profile["rate"])
        return format_rate(parse_rate(base) + archetype_delta(archetypes, "rate_delta") + learning_delta(text, archetypes, profile, "rate_delta"))
    if is_dialogue(text):
        return profile.get("dialogue_rate", profile["rate"])
    if has_word(text, DANGER_WORDS):
        return profile.get("danger_rate", profile["rate"])
    if is_inner_voice(text):
        return profile.get("inner_rate", profile["soft_rate"])
    if is_reveal(text):
        return profile.get("reveal_rate", profile["rate"])
    if is_list_like(text):
        return profile.get("list_rate", profile["rate"])
    if has_word(text, SOFT_WORDS):
        return profile.get("soft_rate", profile["rate"])
    return profile["rate"]


def pitch_for_text(text, profile):
    base = profile["pitch"]
    archetypes = detect_archetypes(text, profile)
    if not is_dialogue(text):
        if archetypes:
            return format_pitch(parse_pitch(base) + archetype_delta(archetypes, "pitch_delta") + learning_delta(text, archetypes, profile, "pitch_delta"))
        return base
    lane = dialogue_lane(text)
    value = parse_pitch(base)
    if lane == "male":
        value -= 2
    if lane == "female":
        value += 1
    value += archetype_delta(archetypes, "pitch_delta") + learning_delta(text, archetypes, profile, "pitch_delta")
    return format_pitch(value)


def classify_unit(text, profile=None):
    archetype_names = detect_archetypes(text, profile or {})
    archetype_suffix = "-".join(archetype_names)
    if is_scene_break(text):
        return "scene-break"
    if is_dialogue(text):
        suffix = f"-{archetype_suffix}" if archetype_suffix else ""
        return f"dialogue-{dialogue_lane(text)}{suffix}"
    if archetype_suffix:
        return f"archetype-{archetype_suffix}"
    if has_word(text, DANGER_WORDS):
        return "danger"
    if is_inner_voice(text):
        return "inner"
    if is_reveal(text):
        return "reveal"
    if is_list_like(text):
        return "list"
    if has_word(text, SOFT_WORDS):
        return "soft"
    if is_cliffhanger(text):
        return "cliffhanger"
    return "narration"


def apply_scene_arc(rate, pitch, index, total, profile, unit_type):
    rate_value = parse_rate(rate)
    pitch_value = parse_pitch(pitch)
    if total <= 1:
        return format_rate(rate_value), format_pitch(pitch_value)
    progress = index / max(1, total - 1)
    if index == 0 and unit_type in {"narration", "soft", "inner", "reveal"}:
        rate_value += int(profile.get("hook_rate_delta", 0))
    elif progress >= 0.82 and unit_type in {"narration", "soft", "inner", "reveal", "cliffhanger"}:
        rate_value += int(profile.get("release_rate_delta", 0))
    return format_rate(rate_value), format_pitch(pitch_value)


def smooth_performance_plan(raw_plan, profile):
    smoothed = []
    previous_rate = None
    previous_pitch = None
    max_rate_jump = int(profile.get("max_rate_jump", 5))
    max_pitch_jump = int(profile.get("max_pitch_jump", 3))
    for item in raw_plan:
        rate_value = parse_rate(item["rate"])
        pitch_value = parse_pitch(item["pitch"])
        if item["type"].startswith("dialogue"):
            previous_rate = rate_value
            previous_pitch = pitch_value
            smoothed.append(item)
            continue
        rate_value = limited_step(rate_value, previous_rate, max_rate_jump)
        pitch_value = limited_step(pitch_value, previous_pitch, max_pitch_jump)
        item = dict(item)
        item["rate"] = format_rate(rate_value)
        item["pitch"] = format_pitch(pitch_value)
        previous_rate = rate_value
        previous_pitch = pitch_value
        smoothed.append(item)
    return smoothed


def make_silence(path, seconds):
    if seconds <= 0:
        return
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-t",
            f"{seconds:.3f}",
            "-q:a",
            "9",
            "-acodec",
            "libmp3lame",
            str(path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def trim_chunk_silence(path, aggressive=False):
    temp_path = path.with_name(f"{path.stem}-trim{path.suffix}")
    threshold = "-42dB" if aggressive else "-38dB"
    stop_duration = "0.10" if aggressive else "0.14"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(path),
            "-af",
            f"silenceremove=start_periods=1:start_silence=0:start_threshold={threshold}:stop_periods=-1:stop_duration={stop_duration}:stop_threshold={threshold}",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "3",
            str(temp_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    temp_path.replace(path)


async def synthesize_performed(text, output, voice, profile):
    units = split_performance_units(text, int(profile.get("max_unit_chars", 180)))
    units = [unit for unit in units if has_spoken_content(unit)]
    if not units:
        units = [text]
    if len(units) == 1:
        selected_voice = voice_for_text(text, voice, profile)
        await synthesize_resilient(prepare_tts_text(text, profile), output, selected_voice, profile["rate"], profile["pitch"])
        trim_chunk_silence(output, aggressive=bool(profile.get("tight_punctuation")))
        return [{"type": classify_unit(text, profile), "voice": selected_voice, "rate": profile["rate"], "pitch": profile["pitch"], "pause_after": 0}]

    with tempfile.TemporaryDirectory(prefix="edge-tts-perform-") as temp_name:
        temp_dir = Path(temp_name)
        concat_items = []
        raw_plan = []
        speaker_hint = None
        active_dialogue_speaker = None
        max_inserted_pause = profile.get("max_inserted_pause")
        for index, unit in enumerate(units):
            hinted = speaker_from_context(unit, profile)
            if hinted and not is_dialogue(unit):
                speaker_hint = hinted
            if unit_opens_dialogue(unit) and speaker_hint:
                active_dialogue_speaker = speaker_hint
            unit_type = classify_unit(unit, profile)
            if active_dialogue_speaker and not unit_type.startswith("dialogue"):
                unit_type = f"dialogue-{active_dialogue_speaker}"
            rate, pitch = apply_scene_arc(rate_for_text(unit, profile), pitch_for_text(unit, profile), index, len(units), profile, unit_type)
            gap = line_gap(unit, profile)
            if max_inserted_pause is not None:
                gap = min(gap, float(max_inserted_pause))
            if active_dialogue_speaker:
                selected_voice = voice_for_character(active_dialogue_speaker, profile) or voice_for_text(unit, voice, profile, speaker_hint)
            else:
                selected_voice = voice_for_text(unit, voice, profile, speaker_hint)
            raw_plan.append(
                {
                    "unit": unit,
                    "type": unit_type,
                    "voice": selected_voice,
                    "rate": rate,
                    "pitch": pitch,
                    "pause_after": round(gap, 3),
                }
            )
            if active_dialogue_speaker and unit_closes_dialogue(unit):
                active_dialogue_speaker = None
        plan = smooth_performance_plan(raw_plan, profile)
        for index, item in enumerate(plan, 1):
            voice_path = temp_dir / f"voice-{index:03d}.mp3"
            await synthesize_resilient(prepare_tts_text(item["unit"], profile), voice_path, item["voice"], item["rate"], item["pitch"])
            trim_chunk_silence(voice_path, aggressive=bool(profile.get("tight_punctuation")))
            concat_items.append(voice_path)
            gap = item["pause_after"]
            if gap > 0 and index < len(units):
                silence_path = temp_dir / f"silence-{index:03d}.mp3"
                make_silence(silence_path, gap)
                concat_items.append(silence_path)
        list_path = temp_dir / "concat.txt"
        list_path.write_text("".join(f"file '{path.as_posix()}'\n" for path in concat_items), encoding="utf-8")
        run_quiet(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c:a", "libmp3lame", "-q:a", "3", str(output)])
        trim_chunk_silence(output, aggressive=bool(profile.get("tight_punctuation")))
    return [{key: value for key, value in item.items() if key != "unit"} for item in plan]


def split_text(text, max_chars=650):
    pieces = []
    current = []
    size = 0
    for part in text.replace("\n", " ").split(". "):
        part = part.strip()
        if not part:
            continue
        if not part.endswith((".", "?", "!", ":")):
            part += "."
        if current and size + len(part) > max_chars:
            pieces.append(" ".join(current))
            current = [part]
            size = len(part)
        else:
            current.append(part)
            size += len(part)
    if current:
        pieces.append(" ".join(current))
    return pieces or [text]


async def synthesize_resilient(text, output, voice, rate, pitch):
    last_error = None
    for _ in range(5):
        try:
            await synthesize(text, output, voice, rate, pitch)
            return
        except Exception as exc:
            last_error = exc
            if output.exists() and output.stat().st_size == 0:
                output.unlink()
            await asyncio.sleep(2)

    fallback_text = sanitize_for_tts_fallback(text)
    if fallback_text and fallback_text != text:
        for _ in range(3):
            try:
                await synthesize(fallback_text, output, voice, rate, pitch)
                return
            except Exception as exc:
                last_error = exc
                if output.exists() and output.stat().st_size == 0:
                    output.unlink()
                await asyncio.sleep(1)

    parts = split_text(fallback_text or text)
    if len(parts) == 1:
        words = text.split()
        if len(words) > 8:
            midpoint = len(words) // 2
            parts = [" ".join(words[:midpoint]), " ".join(words[midpoint:])]
        else:
            raise last_error

    with tempfile.TemporaryDirectory(prefix="edge-tts-") as temp_name:
        temp_dir = Path(temp_name)
        chunk_paths = []
        for index, part in enumerate(parts, 1):
            chunk_path = temp_dir / f"chunk-{index:03d}.mp3"
            await synthesize(part, chunk_path, voice, rate, pitch)
            chunk_paths.append(chunk_path)
        list_path = temp_dir / "concat.txt"
        list_path.write_text("".join(f"file '{path.as_posix()}'\n" for path in chunk_paths), encoding="utf-8")
        run_quiet(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c:a", "libmp3lame", "-q:a", "3", str(output)])


async def main_async(args):
    storyboard_path = args.storyboard.resolve()
    storyboard_dir = storyboard_path.parent
    assets_dir = storyboard_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    config = json.loads(storyboard_path.read_text(encoding="utf-8-sig"))
    scenes = config.get("scenes") or []
    if not scenes:
        raise SystemExit("Storyboard has no scenes.")

    subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent / "validate_storyboard.py"), "--storyboard", str(storyboard_path), "--stage", "text"],
        check=True,
    )

    voice = VOICE_PRESETS.get(args.voice, args.voice)
    style = dict(VOICE_STYLES[args.voice_style])
    if args.rate != "auto":
        style["rate"] = args.rate
    if args.pitch != "auto":
        style["pitch"] = args.pitch
    learning = load_learning(args.learning_file)
    style = apply_learning(style, learning)
    style["_learning"] = learning
    style["_character_bible"] = load_character_bible(args.character_bible)
    start_index = max(0, args.start_scene - 1)
    end_index = args.end_scene if args.end_scene else len(scenes)
    end_index = min(len(scenes), end_index)
    warnings = []
    voice_plan = {
        "storyboard": str(storyboard_path),
        "voice": voice,
        "voice_style": args.voice_style,
        "style": style,
        "scenes": [],
        "warnings": warnings,
    }
    generated_count = 0
    failed_count = 0
    for index, scene in enumerate(scenes[start_index:end_index], start=start_index):
        text = scene.get("narration") or scene.get("subtitle") or scene.get("text")
        if not text:
            raise SystemExit(f"Scene {index + 1} has no narration/subtitle/text.")

        if scene.get("audio"):
            audio_path = resolve(storyboard_dir, scene["audio"])
        else:
            audio_path = assets_dir / f"scene-{index + 1:02d}.mp3"
        audio_path.parent.mkdir(parents=True, exist_ok=True)

        needs_audio = not audio_path.exists() or audio_path.stat().st_size < 1024 or args.overwrite
        plan = None
        generated = False
        failed = False
        if needs_audio:
            print(f"Generating voice scene {index + 1}/{len(scenes)}: {audio_path}", flush=True)
            try:
                plan = await synthesize_performed(text, audio_path, voice, style)
                generated = True
                generated_count += 1
            except Exception as exc:
                failed = True
                failed_count += 1
                warning = {
                    "scene": index + 1,
                    "id": scene.get("id") or f"scene-{index + 1:03d}",
                    "error": str(exc),
                }
                warnings.append(warning)
                print(f"WARNING scene {index + 1} voice failed: {exc}", file=sys.stderr, flush=True)
                if audio_path.exists() and audio_path.stat().st_size < 1024:
                    try:
                        audio_path.unlink()
                    except OSError:
                        pass

        if not failed:
            scene["audio"] = relpath(audio_path, storyboard_dir)
        scene.setdefault("subtitle", text)
        voice_plan["scenes"].append(
            {
                "id": scene.get("id") or f"scene-{index + 1:03d}",
                "audio": scene.get("audio", relpath(audio_path, storyboard_dir)),
                "generated": generated,
                "failed": failed,
                "unit_count": len(plan or split_performance_units(text, int(style.get("max_unit_chars", 180)))),
                "plan": plan or [],
            }
        )

    storyboard_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    voice_plan["summary"] = {
        "range": {"start_scene": start_index + 1, "end_scene": end_index},
        "generated": generated_count,
        "failed": failed_count,
        "warnings": len(warnings),
    }
    if start_index == 0 and end_index == len(scenes):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent / "validate_storyboard.py"), "--storyboard", str(storyboard_path), "--stage", "voice"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            validation_warning = (result.stderr or result.stdout or "").strip()
            voice_plan["validation_warning"] = validation_warning
            print(f"WARNING voice validation incomplete; generated={generated_count}, failed={failed_count}", file=sys.stderr, flush=True)
    (storyboard_dir / "voice-plan.json").write_text(json.dumps(voice_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"storyboard": str(storyboard_path), "scenes": len(scenes), "voice": voice, "voice_style": args.voice_style, "generated": generated_count, "failed": failed_count, "warnings": len(warnings)}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Generate narration with Microsoft Edge TTS.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--voice", default="vi-female", help="Preset vi-female, vi-male, en-female, en-male, or full Edge voice name.")
    parser.add_argument("--voice-style", choices=sorted(VOICE_STYLES), default="wasteland-dark")
    parser.add_argument("--learning-file", type=Path, default=REPO_ROOT / "config" / "voice_learning.json")
    parser.add_argument("--character-bible", type=Path, default=None)
    parser.add_argument("--rate", default="auto")
    parser.add_argument("--pitch", default="auto")
    parser.add_argument("--start-scene", type=int, default=1)
    parser.add_argument("--end-scene", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()

