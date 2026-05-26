#!/usr/bin/env python3
import argparse
import json
import math
import random
import re
import shutil
import subprocess
import wave
from pathlib import Path


SAMPLE_RATE = 44100
DEFAULT_SFX_LIBRARY = Path(r"E:\ThanhMV\sfx-library")


SUSPENSE_WORDS = (
    "bong", "dot nhien", "im lang", "nin tho", "hoi hop", "nguy hiem",
    "phia sau", "run ray", "so hai", "khung lai", "ke nao do", "thu gi do",
    "khong dam tho", "dang den gan", "quay lai", "mo mat", "chet cham hon",
)

FOOTSTEP_WORDS = (
    "buoc chan", "mot buoc", "hai buoc", "tung buoc", "buoc vao", "buoc den",
    "tieng buoc", "dat chan",
)

SCRAPE_WORDS = (
    "cao", "cao nhe", "cao len", "cao qua", "keo le", "mong vuot",
)

AMBIENCE_WORDS = ("mua den", "bao", "gio rit", "gio lanh", "gio manh", "sam", "set")

SFX_ASSET_NAMES = {
    "footsteps": ("footstep", "footsteps", "step", "steps", "buoc-chan", "tieng-buoc"),
    "scrape": ("door-scrape", "door_scrape", "scrape", "scratch", "cao-cua", "cao", "creak"),
    "suspense": ("suspense-drone", "tension-drone", "dark-ambience", "horror-bed", "hoi-hop-nen"),
    "rain": ("rain", "mua"),
    "wind": ("wind", "gio"),
}

SFX_CONTEXTS = {
    "footsteps": {
        "dirt": ("dirt", "gravel", "stone", "debris", "ground", "forest", "grass", "leaf", "leaves", "twig", "moss"),
        "wood": ("wood", "wooden", "floor", "plank", "parquet"),
        "concrete": ("concrete", "cement", "hallway", "indoor"),
        "metal": ("metal", "metallic", "steel"),
        "snow": ("snow",),
        "sand": ("sand",),
    },
    "scrape": {
        "cloth": ("cloth", "fabric", "canvas", "burlap", "coat", "jacket", "rustle"),
        "claw": ("claw", "scratch", "scrape", "nail", "talon"),
        "door": ("door", "creak", "squeak"),
        "metal": ("metal", "metallic", "steel"),
        "stone": ("stone", "concrete", "wall", "rock"),
        "cardboard": ("cardboard",),
    },
    "suspense": {
        "drone": ("drone", "ambience", "atmosphere", "tension", "horror-bed", "dark"),
        "sting": ("sting", "hit", "impact", "rise"),
    },
}


VI_ASCII = str.maketrans(
    "áàảãạăắằẳẵặâấầẩẫậđéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ"
    "ÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ",
    "aaaaaaaaaaaaaaaaadeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyy"
    "AAAAAAAAAAAAAAAAADEEEEEEEEEEEIIIIIOOOOOOOOOOOOOOOOOUUUUUUUUUUUYYYYY",
)


def require_tool(name):
    if shutil.which(name) is None:
        raise SystemExit(f"Missing required tool on PATH: {name}")


def resolve(base, value):
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def relpath(path, base):
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def normalize(text):
    return " ".join(str(text or "").translate(VI_ASCII).lower().split())


def has_any(text, words):
    return any(word in text for word in words)


def contains_terms(text, terms):
    for term in terms:
        normalized_term = normalize(term)
        if " " in normalized_term:
            if normalized_term in text:
                return True
        elif re.search(rf"\b{re.escape(normalized_term)}\b", text):
            return True
    return False


def probe_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        return max(0.1, float(result.stdout.strip()))
    except ValueError:
        return 0.1


def find_sfx_asset(library, cue, preferred_terms=()):
    if not library or not library.exists():
        return None
    names = SFX_ASSET_NAMES.get(cue, (cue,))
    candidates = []
    for suffix in ("*.wav", "*.mp3", "*.m4a", "*.aac", "*.flac", "*.ogg"):
        candidates.extend(library.rglob(suffix))
    matches = []
    for path in sorted(candidates):
        stem = normalize(path.stem)
        if any(name in stem for name in names):
            duration = probe_duration(path)
            if duration > 0.1:
                matches.append((duration, path))
    if preferred_terms:
        preferred = [
            (duration, path)
            for duration, path in matches
            if any(term in normalize(path.stem) for term in preferred_terms)
        ]
        if preferred:
            return sorted(preferred, key=lambda item: item[0])[0][1]
    if matches:
        return sorted(matches, key=lambda item: item[0])[0][1]
    return None


def sfx_context_for_cue(text, cue):
    normalized = normalize(text)
    if cue == "scrape":
        if contains_terms(normalized, ("bat", "vai", "leu", "tam bat", "ao", "quan", "ao khoac")):
            return "cloth"
        if contains_terms(normalized, ("mong vuot", "mong", "vuot", "cao qua be tong", "cao qua tuong")):
            return "claw"
        if contains_terms(normalized, ("cua", "canh cua", "ban le")):
            return "door"
        if contains_terms(normalized, ("sat", "kim loai", "thep", "xe", "thung xe")):
            return "metal"
        if contains_terms(normalized, ("be tong", "tuong", "da", "gach")):
            return "stone"
        return "claw"
    if cue == "footsteps":
        if contains_terms(normalized, ("tuyet", "bang")):
            return "snow"
        if contains_terms(normalized, ("cat", "bai bien")):
            return "sand"
        if contains_terms(normalized, ("san go", "go", "nha", "san")):
            return "wood"
        if contains_terms(normalized, ("kim loai", "sat", "thep")):
            return "metal"
        if contains_terms(normalized, ("be tong", "xi mang", "hanh lang", "nha ga")):
            return "concrete"
        return "dirt"
    if cue == "suspense":
        if contains_terms(normalized, ("dot nhien", "bat ngo", "giat minh", "mo mat", "phia sau")):
            return "sting"
        return "drone"
    return "general"


def preferred_terms_for_cue(text, cue):
    context = sfx_context_for_cue(text, cue)
    return SFX_CONTEXTS.get(cue, {}).get(context, ())


def asset_matches_context(path, cue, context):
    terms = SFX_CONTEXTS.get(cue, {}).get(context, ())
    if not terms:
        return True
    stem = normalize(path.stem)
    return any(term in stem for term in terms)


def cue_positions(text, duration, cue):
    normalized = normalize(text)
    if not normalized:
        return []
    if cue == "footsteps":
        triggers = ("mot buoc", "hai buoc", "tieng buoc", "buoc chan", "tung buoc", "buoc vao", "buoc den")
    elif cue == "scrape":
        triggers = ("cao nhe", "cao len", "cao qua", "tieng cao", "mong vuot")
    else:
        triggers = ()
    positions = []
    for trigger in triggers:
        start = 0
        while True:
            index = normalized.find(trigger, start)
            if index < 0:
                break
            ratio = index / max(1, len(normalized))
            positions.append(max(0.15, min(duration - 0.25, ratio * duration)))
            start = index + len(trigger)
    return sorted(set(round(pos, 2) for pos in positions))


def make_silence(path, duration):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r={SAMPLE_RATE}:cl=mono",
            "-t",
            str(duration),
            "-c:a",
            "pcm_s16le",
            str(path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def overlay_asset(base_path, asset_path, output_path, start, duration, volume):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    delay_ms = max(0, int(start * 1000))
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(base_path),
            "-i",
            str(asset_path),
            "-filter_complex",
            (
                f"[1:a]silenceremove=start_periods=1:start_threshold=-45dB,"
                f"atrim=0:{duration},asetpts=PTS-STARTPTS,"
                f"highpass=f=70,lowpass=f=9000,dynaudnorm=f=120:g=15,"
                f"volume={volume},volume=14dB,adelay={delay_ms}:all=1[sfx];"
                "[0:a][sfx]amix=inputs=2:duration=first:dropout_transition=0,alimiter=limit=0.92[a]"
            ),
            "-map",
            "[a]",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def build_sfx_from_assets(path, duration, cues, library, volume, text):
    current = path.with_suffix(".base.wav")
    make_silence(current, duration)
    used = []
    missing = []
    schedules = {
        "suspense": [],
        "rain": [(0.0, duration, 0.18)],
        "wind": [(0.0, duration, 0.16)],
    }
    for cue in cues:
        context = sfx_context_for_cue(text, cue)
        preferred_terms = preferred_terms_for_cue(text, cue)
        asset = find_sfx_asset(library, cue, preferred_terms)
        if not asset:
            missing.append({"cue": cue, "context": context, "reason": "missing asset"})
            continue
        if not asset_matches_context(asset, cue, context):
            missing.append({"cue": cue, "context": context, "reason": f"wrong context asset: {asset.name}"})
            continue
        cue_schedule = schedules.get(cue)
        if cue_schedule is None:
            event_times = cue_positions(text, duration, cue)
            if not event_times:
                event_times = [duration * 0.45]
            cue_schedule = [(event_time, 0.7 if cue == "footsteps" else 0.9, 0.68 if cue == "footsteps" else 0.62) for event_time in event_times[:4]]
        if not cue_schedule:
            missing.append(cue)
            continue
        for cue_index, (start, length, cue_volume) in enumerate(cue_schedule, 1):
            if start >= duration - 0.2:
                continue
            next_path = path.with_name(f"{path.stem}-{cue}-{cue_index}.wav")
            overlay_asset(current, asset, next_path, start, min(length, duration - start), volume * cue_volume)
            if current.name != path.with_suffix(".base.wav").name and current.exists():
                current.unlink()
            current = next_path
        used.append({"cue": cue, "context": context, "asset": str(asset)})
    if used:
        shutil.move(str(current), str(path))
    elif current.exists():
        current.unlink()
    return used, missing


def envelope(t, start, length, attack=0.02, release=0.08):
    if t < start or t > start + length:
        return 0.0
    local = t - start
    if local < attack:
        return local / max(attack, 0.001)
    if local > length - release:
        return max(0.0, (length - local) / max(release, 0.001))
    return 1.0


def add_thump(samples, start, duration, volume):
    count = len(samples)
    start_i = int(start * SAMPLE_RATE)
    length = int(duration * SAMPLE_RATE)
    for i in range(max(0, start_i), min(count, start_i + length)):
        t = (i - start_i) / SAMPLE_RATE
        decay = math.exp(-9.0 * t)
        tone = math.sin(2 * math.pi * 78 * t) + 0.35 * math.sin(2 * math.pi * 145 * t)
        samples[i] += volume * decay * tone


def add_footstep(samples, start, volume, rng):
    count = len(samples)
    start_i = int(start * SAMPLE_RATE)
    length = int(0.34 * SAMPLE_RATE)
    last = 0.0
    for i in range(max(0, start_i), min(count, start_i + length)):
        t = (i - start_i) / SAMPLE_RATE
        heel = math.exp(-24.0 * t) * math.sin(2 * math.pi * 72 * t)
        toe_delay = max(0.0, t - 0.09)
        toe = math.exp(-30.0 * toe_delay) * math.sin(2 * math.pi * 115 * toe_delay) if t > 0.09 else 0.0
        grit = rng.uniform(-1.0, 1.0)
        last = 0.68 * last + 0.32 * grit
        crunch_env = envelope(t, 0.035, 0.2, 0.015, 0.13)
        samples[i] += volume * (0.62 * heel + 0.35 * toe + 0.13 * crunch_env * (grit - last))


def add_scrape(samples, start, duration, volume, rng):
    count = len(samples)
    start_i = int(start * SAMPLE_RATE)
    length = int(duration * SAMPLE_RATE)
    last = 0.0
    for i in range(max(0, start_i), min(count, start_i + length)):
        t = (i - start_i) / SAMPLE_RATE
        env = envelope(t, 0, duration, 0.03, 0.1)
        noise = rng.uniform(-1.0, 1.0)
        last = 0.82 * last + 0.18 * noise
        samples[i] += volume * env * (noise - last)


def add_door_scrape(samples, start, duration, volume, rng):
    count = len(samples)
    start_i = int(start * SAMPLE_RATE)
    length = int(duration * SAMPLE_RATE)
    last = 0.0
    for i in range(max(0, start_i), min(count, start_i + length)):
        t = (i - start_i) / SAMPLE_RATE
        env = envelope(t, 0, duration, 0.08, 0.18)
        wobble = 0.65 + 0.35 * math.sin(2 * math.pi * 6.5 * t)
        creak = math.sin(2 * math.pi * (420 + 90 * math.sin(2 * math.pi * 1.4 * t)) * t)
        noise = rng.uniform(-1.0, 1.0)
        last = 0.9 * last + 0.1 * noise
        scratch = noise - last
        samples[i] += volume * env * (0.42 * wobble * creak + 0.58 * scratch)
    add_thump(samples, start + duration + 0.05, 0.18, volume * 1.4)


def generate_sfx(path, duration, cues, intensity):
    rng = random.Random(1337)
    count = int(duration * SAMPLE_RATE)
    samples = [0.0] * count

    if "suspense" in cues:
        for i in range(count):
            t = i / SAMPLE_RATE
            fade = min(1.0, t / 1.2, (duration - t) / 1.2 if duration > 1.2 else 1.0)
            drone = math.sin(2 * math.pi * 46 * t) * 0.35 + math.sin(2 * math.pi * 91 * t) * 0.15
            noise = rng.uniform(-1.0, 1.0) * 0.08
            samples[i] += intensity * 0.055 * fade * (drone + noise)

    if "rain" in cues:
        last = 0.0
        for i in range(count):
            noise = rng.uniform(-1.0, 1.0)
            last = 0.92 * last + 0.08 * noise
            samples[i] += intensity * 0.025 * (noise - last)

    if "wind" in cues:
        last = 0.0
        for i in range(count):
            t = i / SAMPLE_RATE
            gust = 0.55 + 0.45 * math.sin(2 * math.pi * 0.11 * t)
            noise = rng.uniform(-1.0, 1.0)
            last = 0.985 * last + 0.015 * noise
            samples[i] += intensity * 0.035 * gust * last

    if "footsteps" in cues:
        step_times = [0.55, 1.25, 2.05, 2.85]
        if duration > 8:
            step_times.extend([4.15, 5.0])
        for step in step_times:
            if step < duration - 0.25:
                add_footstep(samples, step, intensity * 0.22, rng)

    if "scrape" in cues:
        for start in (1.2, 3.3):
            if start < duration - 0.35:
                add_door_scrape(samples, start, 0.72, intensity * 0.065, rng)

    peak = max(0.001, max(abs(value) for value in samples))
    scale = min(1.0, 0.18 / peak)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for value in samples:
            sample = int(max(-1.0, min(1.0, value * scale)) * 32767)
            frames.extend(sample.to_bytes(2, "little", signed=True))
        wav.writeframes(frames)


def suspense_score(text):
    score = 0
    score += sum(1 for word in SUSPENSE_WORDS if word in text)
    score += 1 if "..." in text or "…" in text else 0
    score += 1 if "?" in text or "!" in text else 0
    return score


def detect_cues(text):
    normalized = normalize(text)
    cues = []
    tense = suspense_score(normalized) >= 2
    if tense and not has_any(normalized, FOOTSTEP_WORDS) and not has_any(normalized, SCRAPE_WORDS):
        cues.append("suspense")
    if has_any(normalized, FOOTSTEP_WORDS):
        cues.append("footsteps")
    if has_any(normalized, SCRAPE_WORDS):
        cues.append("scrape")
    if tense and has_any(normalized, AMBIENCE_WORDS):
        if "mua" in normalized or "bao" in normalized or "sam" in normalized or "set" in normalized:
            cues.append("rain")
        if "gio" in normalized:
            cues.append("wind")
    return cues


def mix_audio(voice_path, sfx_path, output_path, sfx_volume):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(voice_path),
            "-i",
            str(sfx_path),
            "-filter_complex",
            f"[1:a]volume={sfx_volume}[sfx];[0:a][sfx]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.96[a]",
            "-map",
            "[a]",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "3",
            str(output_path),
        ],
        check=True,
    )


def main():
    parser = argparse.ArgumentParser(description="Add subtle story-aware SFX under narration audio.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--volume", type=float, default=0.45, help="SFX mix volume after per-sample cleanup. Try 0.35-0.65.")
    parser.add_argument("--intensity", type=float, default=0.7, help="Generated SFX intensity before final mix.")
    parser.add_argument("--sfx-library", type=Path, default=DEFAULT_SFX_LIBRARY, help="Folder with real SFX assets. Prefer real samples over generated placeholders.")
    parser.add_argument("--allow-generated-sfx", action="store_true", help="Use synthetic fallback SFX if a real SFX asset is missing.")
    parser.add_argument("--keep-sfx-assets", action="store_true", help="Keep intermediate SFX layer files for debugging.")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    require_tool("ffmpeg")
    require_tool("ffprobe")

    storyboard_path = args.storyboard.resolve()
    storyboard_dir = storyboard_path.parent
    data = json.loads(storyboard_path.read_text(encoding="utf-8-sig"))
    scenes = data.get("scenes") or []
    report = {"storyboard": str(storyboard_path), "scenes": []}

    for index, scene in enumerate(scenes, 1):
        text = scene.get("narration") or scene.get("subtitle") or ""
        cues = detect_cues(text)
        voice_audio = scene.get("voice_audio") or scene.get("audio")
        voice_path = resolve(storyboard_dir, voice_audio)
        if not cues or not voice_path or not voice_path.exists():
            report["scenes"].append({"scene": index, "cues": cues, "mixed": False})
            continue

        stem = Path(scene.get("id") or f"scene-{index:03d}").stem
        sfx_path = storyboard_dir / "assets" / "sfx" / f"{stem}-sfx-layer.wav"
        mixed_path = storyboard_dir / "assets" / f"{stem}-final-audio.mp3"
        if mixed_path.exists() and not args.overwrite:
            scene["voice_audio"] = relpath(voice_path, storyboard_dir)
            scene["audio"] = relpath(mixed_path, storyboard_dir)
            report["scenes"].append(
                {
                    "scene": index,
                    "cues": cues,
                    "mixed": True,
                    "reused": True,
                    "clean_voice": scene["voice_audio"],
                    "final_audio": scene["audio"],
                }
            )
            continue

        duration = probe_duration(voice_path)
        used_assets = []
        missing_assets = []
        if not args.dry_run:
            used_assets, missing_assets = build_sfx_from_assets(sfx_path, duration, cues, args.sfx_library, args.volume, text)
            if not used_assets and args.allow_generated_sfx:
                generate_sfx(sfx_path, duration, cues, args.intensity)
            elif not used_assets:
                report["scenes"].append(
                    {
                        "scene": index,
                        "cues": cues,
                        "mixed": False,
                        "duration": round(duration, 2),
                        "clean_voice": relpath(voice_path, storyboard_dir),
                        "missing_real_sfx": missing_assets or cues,
                        "message": f"Add real SFX files to {args.sfx_library} or rerun with --allow-generated-sfx.",
                    }
                )
                continue
            mix_audio(voice_path, sfx_path, mixed_path, 1.0)
            scene["voice_audio"] = relpath(voice_path, storyboard_dir)
            scene["audio"] = relpath(mixed_path, storyboard_dir)
            if not args.keep_sfx_assets:
                for temp_sfx in sfx_path.parent.glob(f"{stem}-sfx-layer*"):
                    if temp_sfx.exists():
                        temp_sfx.unlink()
        report["scenes"].append(
            {
                "scene": index,
                "cues": cues,
                "mixed": not args.dry_run,
                "duration": round(duration, 2),
                "clean_voice": relpath(voice_path, storyboard_dir),
                "final_audio": relpath(mixed_path, storyboard_dir),
                "used_real_sfx": used_assets,
                "missing_real_sfx": missing_assets,
            }
        )

    report_path = storyboard_dir / "sfx-plan.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.dry_run:
        storyboard_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
