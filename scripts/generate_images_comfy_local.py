#!/usr/bin/env python3
"""
Generate premium local storyboard images through an existing ComfyUI install.

Default mode is SD 1.5 realistic/cinematic because it is the most stable path for
2GB VRAM. FLUX is intentionally not the default.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
WORK_ROOT = REPO_ROOT.parent


DEFAULT_POSITIVE_SUFFIX = (
    "clear natural human faces, anatomically correct eyes nose mouth and jaw, readable facial expression, "
    "consistent character identity across scenes, complete hands and feet when visible, separate bodies, believable pose and weight, "
    "cinematic composition, strong readable silhouette, clear foreground midground background, "
    "realistic lighting, warm practical light against cold toxic atmosphere, volumetric fog and dust, "
    "wet rusted metal, cracked concrete, torn fabric, soft bloom, atmospheric perspective, "
    "realistic shadows, subtle film grain, detailed environment, 35mm cinema lens, "
    "premium survival film still, emotional, immersive, muted natural colors, not oversaturated"
)

DEFAULT_NEGATIVE = (
    "low quality, blurry, jpeg artifacts, cartoon, anime, illustration, plastic skin, oversaturated, "
    "bad anatomy, deformed hands, distorted face, extra limbs, duplicate body, ugly face, text, "
    "watermark, logo, messy composition, flat lighting, bad perspective, AI artifacts, random dots, "
    "white speckles, noisy, over-sharpened, waxy skin, empty landscape, generic fantasy art, "
    "beauty portrait, fashion photo, clean clothes, modern city, cute pose, "
    "melted face, warped face, malformed face, asymmetrical eyes, crossed eyes, bad eyes, dead eyes, "
    "missing nose, broken nose, bad mouth, fused lips, extra teeth, duplicate face, two faces on one head, "
    "fused bodies, merged bodies, overlapping bodies, conjoined bodies, detached head, floating head, extra person fragment, "
    "extra arm, extra hand, extra leg, missing arm, missing hand, missing leg, missing foot, tangled limbs, broken wrists, broken elbows, broken knees, impossible pose, "
    "cropped face, face out of frame, hidden face, faceless, over-smoothed face, childlike doll face, "
    "solo glamour portrait, extreme close-up glamour crop, cropped body, random extra character, missing second character when scene needs two people, "
    "nude, naked, topless, exposed breasts, exposed nipples, areola, sideboob, underboob, cleavage focus, lingerie, two-piece bikini, string bikini, triangle bikini, bikini bottom, swimsuit bottom, swimwear, underwear, panties, thong, matching underwear set, see-through clothing, erotic pose, voyeuristic framing, "
    "masculine woman, woman with male facial structure, square male jaw on woman, heavy masculine brow on woman, gender ambiguous face, "
    "man wearing crop top, male crop top, man wearing strappy top, spaghetti straps on man, male bare midriff fashion, exposed male waist, feminine outfit on man"
)

LAM_TICH_CLOTHING_RULE = (
    "Lam Tich clothing rule: keep her clearly adult, attractive, feminine, and sexy in a wasteland way, but story-first; "
    "use a fitted thick-strap weathered survival top under torn scavenger layers, paired with rugged short shorts or torn utility shorts; "
    "when the scene beat calls for charm, confidence, temptation, intimacy, or a character spotlight, let her read sexy in a grounded wasteland way without fashion posing; "
    "never use a two-piece bikini, string bikini, bikini bottom, panties, matching underwear set, or swimsuit bottom. "
    "If the beat is danger, travel, group survival, barter, smoke, ash, injury, or action, reduce exposure slightly and prioritize practical torn scavenger clothing."
)

STORY_FIRST_VISUAL_RULE = (
    "Story-first visual rule: draw the exact current narration beat first, including the named action, prop, location, danger, injury, bargain, travel step, rationing, or reaction. "
    "Do not replace survival beats with glamour posing, pin-up posing, hero posing, fashion posing, or a generic standing portrait. "
    "The visible action must be the primary visual center, and posing is allowed only when the narration itself describes posing, tempting, performing, or standing for a reveal. "
    "Any attractive styling must support the story action and never override it."
)

FEMALE_SEXY_BEAT_RULE = (
    "Female sexy beat rule: if the narration explicitly makes an adult woman sexy, seductive, charming, tempting, intimate, or using attraction, preserve that story beat. "
    "Show femininity and allure through face, gaze, posture, character tension, and practical torn wasteland clothing with readable arms or legs when appropriate, while the narrated action remains clear. "
    "Never convert it into bikini, underwear, nudity, explicit exposure, beachwear, clean fashion posing, or a pose that replaces the story event."
)

ACTION_COMPLETENESS_RULE = (
    "Scene contract: the image must answer who is doing what, with which visible object, creature, wound, tool, door, water source, trade good, vehicle, animal, or monster, where it happens, and what story pressure changes right now. "
    "Hands, posture, spacing, props, body direction, wounds, tools, threats, and environment must make the narrated action readable. "
    "If the action cannot be read, do not substitute a standing portrait, hero pose, fashion pose, pin-up pose, or camera-facing model shot."
)

WASTELAND_ACTION_STYLE_RULE = (
    "Wasteland continuity rule: every scene must look like a dirty post-apocalyptic survival moment with grime, torn practical cloth, rust, dust, cracked concrete, salvage, scarcity, fatigue, and dangerous lived-in space. "
    "Even when a character is attractive, the frame must stay wasteland first and must not look like a clean studio, beachwear shoot, gym fashion shoot, cosplay portrait, or modern city fashion image."
)

BEAT_FIRST_VISUAL_RULE = (
    "Beat-first visual priority: choose the image center from the current story beat before choosing a character pose. "
    "Priority order is story beat, then main character only if they drive this beat, then location and objects, then supporting characters, then creatures or threats. "
    "If the beat is about a message, object, doorway, trade, medicine, water source, wound, animal, monster, tool, vehicle, weather, or crowd reaction, that event or object must be the foreground visual center even when Lam Tich or Tan Da is present. "
    "Do not force Lam Tich, Tan Da, or any main character into the center when the narration is actually about another person, object, creature, place, or survival event."
)

FEMALE_FACE_RULE = (
    "Female face rule: adult women must have unmistakably feminine faces with soft female facial structure, delicate jawline, balanced feminine eyes nose and mouth, "
    "no square male jaw, no heavy masculine brow, no male facial structure, while still carrying dirt, ash, fatigue, and wasteland realism."
)

MALE_WASTELAND_CLOTHING_RULE = (
    "Male character rule: adult men must read clearly masculine with strong male facial structure, broad shoulders, grounded wasteland toughness, and practical masculine clothing; "
    "use worn dark tactical coats, heavy scavenger jackets, layered practical shirts, long rugged pants, boots, belts, straps, armor scraps, dirty cloth wraps, and survival gear. "
    "Male characters must never inherit Lam Tich's fitted feminine tops, crop top, droptop, strappy top, spaghetti straps, bare-midriff clothing, exposed belly or waist, short shorts, feminine glamour outfit, bikini, or swimwear styling; no exposed male belly unless the narration explicitly shows a wound being treated."
)

RATIO_TO_SIZE = {
    "9:16": (512, 768),
    "3:4": (576, 768),
    "2:3": (512, 768),
    "1:1": (640, 640),
    "16:9": (1280, 720),
}

CHECKPOINT_PREFERENCES = [
    "realisticvision",
    "cyberrealistic",
    "epicrealism",
    "photon",
    "majicmixrealistic",
    "deliberate",
    "dreamshaper",
]

CHECKPOINT_AVOID = [
    "xl",
    "sdxl",
    "flux",
    "turbo",
    "lightning",
    "anime",
    "toon",
]

VAE_PREFERENCES = [
    "vae-ft-mse-840000-ema-pruned",
    "vae-ft-mse",
    "clearvae",
]

UPSCALER_PREFERENCES = [
    "4x-ultrasharp",
    "4x_foolhardy_remacri",
    "remacri",
    "realesrgan_x2plus",
    "realesrgan",
]


def request_json(base_url: str, path: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    request = urllib.request.Request(f"{base_url.rstrip('/')}{path}", data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"ComfyUI HTTP error {exc.code} at {path}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"ComfyUI is not reachable at {base_url}: {exc}") from exc
    return json.loads(raw.decode("utf-8")) if raw else {}


def download_bytes(base_url: str, path: str, timeout: int = 60) -> bytes:
    with urllib.request.urlopen(f"{base_url.rstrip('/')}{path}", timeout=timeout) as response:
        return response.read()


def resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def relpath(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())



def size_for_ratio(ratio: str) -> tuple[int, int]:
    return RATIO_TO_SIZE.get(ratio, RATIO_TO_SIZE["9:16"])


def scene_text_blob(scene: dict[str, Any]) -> str:
    values: list[str] = []
    for key in [
        "narration",
        "beat_subject",
        "scene_role",
        "scene_center_kind",
        "scene_center_subject",
        "scene_center_object",
        "scene_center_action",
        "scene_center_location",
        "visual_shot_type",
        "image_prompt",
        "comfy_prompt",
        "stability_prompt",
        "visual",
        "text",
    ]:
        value = scene.get(key)
        if isinstance(value, str):
            values.append(value)
    for key in ["visual_must_show", "visual_action", "visual_actions", "visual_setting", "visual_props", "local_prompt_frontload", "local_rescue_notes"]:
        value = scene.get(key)
        if isinstance(value, list):
            values.extend(str(item) for item in value if str(item).strip())
    return " ".join(values).lower()


def classify_story_beat(scene: dict[str, Any]) -> str:
    text = scene_text_blob(scene)
    center_kind = str(scene.get("scene_center_kind") or "").lower()
    shot_type = str(scene.get("visual_shot_type") or "").lower()
    if any(token in text for token in ["radio", "broadcast", "message", "transmission", "signal", "speaker", "loa", "tin nhan"]):
        return "message_signal"
    if any(token in text for token in ["water", "well", "rain barrel", "medicine", "bandage", "antidote", "ration", "food", "drink", "nuoc", "gieng", "thuoc"]):
        return "resource_survival"
    if any(token in text for token in ["trade", "bargain", "seller", "buyer", "market", "price", "crystal", "mutant teeth", "table", "stall", "doi hang", "mua ban"]):
        return "trade_object"
    if any(token in text for token in ["door", "gate", "threshold", "checkpoint", "entry", "guard", "lock", "wall", "cong", "cua"]):
        return "threshold_entry"
    if any(token in text for token in ["wound", "injured", "bleeding", "bandaged", "stretcher", "wheelchair", "carry", "drag", "keo", "bi thuong"]):
        return "injury_transport"
    if any(token in text for token in ["mutant", "beast", "monster", "dog", "hound", "claw", "fang", "attack", "threat", "hung thu", "quai"]):
        return "creature_threat"
    if any(token in text for token in ["child", "children", "ninh", "tieu mai", "tieu bao", "writing board", "small board", "dua tre", "tre con"]):
        return "child_exchange"
    if any(token in text for token in ["old man", "elder", "old woman", "grandmother", "tool", "repair", "lao", "nguoi gia"]):
        return "elder_tool"
    if center_kind in {"object-center", "evidence-center"} or any(token in shot_type for token in ["detail", "insert"]):
        return "object_evidence"
    if any(token in text for token in ["walk", "journey", "road", "rail", "train", "truck", "ruins", "rain", "ash", "dust storm", "travel", "di duong"]):
        return "location_transition"
    if any(token in text for token in ["reaction", "hesitates", "realizes", "stares", "listens", "fear", "anger", "shock", "phan ung"]):
        return "moral_reaction"
    if any(token in text for token in ["lam tich", "tan da", "main character", "hero", "she ", "he "]):
        return "character_action"
    return "story_event"


def beat_prompt_pack(scene: dict[str, Any]) -> dict[str, str]:
    beat = classify_story_beat(scene)
    object_text = str(scene.get("scene_center_object") or "").strip()
    action_text = str(scene.get("scene_center_action") or "").strip()
    subject_text = str(scene.get("scene_center_subject") or scene.get("beat_subject") or "").strip()
    location_text = str(scene.get("scene_center_location") or "").strip()
    required = {
        "message_signal": "radio, speaker, written message, signal device, or listening posture must be readable as the story trigger",
        "resource_survival": "water, medicine, ration, wound-care item, food, or survival resource must be foreground and readable",
        "trade_object": "trade goods, price object, seller-buyer exchange, table, stall, or payment must be foreground and readable",
        "threshold_entry": "door, gate, checkpoint, guard line, lock, entry terms, or blocked passage must be readable",
        "injury_transport": "injured body, wound, bandage, stretcher, wheelchair, carrying, dragging, or treatment action must be readable",
        "creature_threat": "creature, monster, animal threat, claws, fangs, attack direction, or hiding geometry must be readable",
        "child_exchange": "child scale, child faces, writing board, handed object, or child-to-child/adult exchange must be readable",
        "elder_tool": "elderly body language plus the relevant tool, repair, warning, or hand action must be readable",
        "object_evidence": "the specific evidence object, wound, small prop, hand action, or close detail must dominate the frame",
        "location_transition": "travel path, rail line, vehicle, weather, ruins, safe-zone wall, or environmental obstacle must be readable",
        "moral_reaction": "the emotional reaction must point toward the exact object, person, threat, or decision causing it",
        "character_action": "the named character's current action must be readable, not just their appearance",
        "story_event": "the exact narrated event must be readable through action, object, setting, and story pressure",
    }.get(beat, "the exact narrated event must be readable through action, object, setting, and story pressure")
    anchors = [item for item in [action_text, object_text, location_text, subject_text] if item]
    anchor_text = "; ".join(anchors[:4]) if anchors else required
    return {
        "beat": beat,
        "required_center": required,
        "anchor_text": anchor_text,
        "prompt": (
            f"beat type: {beat}; story beat source of truth: {anchor_text}; "
            f"foreground visual center must show: {required}; "
            "midground shows only the characters needed to perform or react to that beat; "
            "background shows the exact wasteland location and pressure."
        ),
    }


def append_scene_note(scene: dict[str, Any], key: str, note: str, limit: int = 8) -> None:
    values = scene.get(key)
    if not isinstance(values, list):
        values = []
    if note not in values:
        values.append(note)
    scene[key] = values[-limit:]


def scene_prompt(scene: dict[str, Any]) -> str:
    shot_type = str(scene.get("visual_shot_type") or "").strip().lower()
    must_show = [str(item).strip() for item in (scene.get("visual_must_show") or []) if str(item).strip()]
    local_rescue_notes = [
        str(item).strip()
        for item in (scene.get("local_rescue_notes") or [])
        if str(item).strip()
    ]
    local_prompt_frontload = [
        str(item).strip()
        for item in (scene.get("local_prompt_frontload") or [])
        if str(item).strip()
    ]
    raw_actions = scene.get("visual_action")
    if raw_actions is None:
        raw_actions = scene.get("visual_actions")
    actions = [str(item).strip() for item in (raw_actions or []) if str(item).strip()]
    setting = [str(item).strip() for item in (scene.get("visual_setting") or []) if str(item).strip()]
    props = [str(item).strip() for item in (scene.get("visual_props") or []) if str(item).strip()]
    narration = str(scene.get("narration") or "").strip()
    primary_subject = str(scene.get("beat_subject") or "").strip()
    scene_role = str(scene.get("scene_role") or "").strip().lower()
    scene_center_kind = str(scene.get("scene_center_kind") or "").strip().lower()
    scene_center_subject = str(scene.get("scene_center_subject") or "").strip()
    scene_center_object = str(scene.get("scene_center_object") or "").strip()
    scene_center_action = str(scene.get("scene_center_action") or "").strip()
    scene_center_location = str(scene.get("scene_center_location") or "").strip()
    fallback_prompt = (
        scene.get("comfy_prompt")
        or scene.get("image_prompt")
        or scene.get("stability_prompt")
        or scene.get("visual")
        or scene.get("text")
        or narration
        or ""
    )
    fallback_prompt = str(fallback_prompt).strip()
    if not any([fallback_prompt, must_show, actions, setting, props, primary_subject]):
        return ""

    beat_pack = beat_prompt_pack(scene)
    combined_text = " ".join([
        fallback_prompt,
        primary_subject,
        scene_center_subject,
        scene_center_object,
        scene_center_action,
        scene_center_location,
        *must_show,
        *actions,
        *setting,
        *props,
    ]).lower()
    named_people = 0
    people_tokens = [
        "lam tich", "tan da", "ninh", "tieu mai", "tieu ngo", "tieu bao", "a that", "a muc",
        "di man", "bach nhi", "thiet oa", "moc sanh", "la kieu", "hau seo"
    ]
    for token in people_tokens:
        if token in combined_text:
            named_people += 1
    if "seller and buyer" in combined_text or "seller and buyers" in combined_text or "group reaction" in combined_text:
        named_people = max(named_people, 2)
    if named_people == 0:
        if "the exact survivor or person described in the narration" in combined_text:
            named_people = 1
        elif "supporting character" in combined_text or "crowd" in combined_text or "survivor group" in combined_text:
            named_people = 2

    cast_notes: list[str] = []
    male_only_notes: list[str] = []
    female_only_notes: list[str] = []
    if "ninh" in combined_text:
        cast_notes.append("Ninh must read as a slight preteen mute boy survivor, clearly child-sized, carrying or using a small writing board, never as an adult man")
    if "tieu mai" in combined_text:
        cast_notes.append("Tieu Mai must read as a preteen girl survivor, clearly younger than the adults, not an adult woman")
    if "tieu bao" in combined_text:
        cast_notes.append("Tieu Bao must read as a very young child held or protected by adults, not an older teen or adult")
    if "a that" in combined_text:
        cast_notes.append("A That must read as a lean young adult male scavenger with restless nervous energy, not a child and not a middle-aged man")
        male_only_notes.append("A That only: lean young adult male scavenger, masculine rough survival clothing, nervous energy, never feminine clothing")
    if "di man" in combined_text:
        cast_notes.append("Di Man must read as an older practical wasteland woman protecting the children")
    if "bach nhi" in combined_text:
        cast_notes.append("Bach Nhi must read as a round-faced adult male trader with calculating politeness, not a soldier hero pose")
        male_only_notes.append("Bach Nhi only: adult male trader in layered wasteland trader clothing, never feminine clothing")
    adult_male_tokens = [
        "tan da", "a that", "bach nhi", "thiet oa", "hau seo", "a muc", "tieu ngo", "lao phung",
        "male", "man", "adult man", "men", "raider", "guard", "trader", "mercenary", "soldier",
        "nam", "dan ong", "nguoi dan ong", "nguoi nam", "nam gioi", "ten gac", "nguoi gac",
        "linh", "linh danh thue", "thuong nhan", "ong ta", "han ta", "thang", "lao "
    ]
    if any(token in combined_text for token in adult_male_tokens):
        male_only_notes.append(MALE_WASTELAND_CLOTHING_RULE)
    if "lam tich" in combined_text:
        female_only_notes.append("Lam Tich only: clearly adult woman with a readable unmistakably feminine face and grounded scavenger presence")
        female_only_notes.append(FEMALE_FACE_RULE)
        female_only_notes.append(LAM_TICH_CLOTHING_RULE)
    if "tan da" in combined_text:
        male_only_notes.append("Tan Da only: clearly adult injured man with grounded masculine facial structure")
        male_only_notes.append("Tan Da only: tall, muscular, masculine, righteous, and powerful in wasteland survival clothing: dark tactical coat or heavy scavenger jacket, layered practical shirt, long rugged pants, boots, belts, straps, armor scraps, dirty bandages only when wounded; never sport top, fitted feminine top, crop top, droptop, strappy top, bare midriff, exposed waist, short shorts, or feminine styling")
    if any(token in combined_text for token in ["ninh", "tieu mai", "a that"]):
        cast_notes.append("show every named child or companion from this scene together if they are named, do not replace them with generic adults or collapse them into one person")
    if "ninh" in combined_text or "tieu mai" in combined_text:
        cast_notes.append("if Ninh or Tieu Mai is present, their child height and child face must be obvious at first glance, never adult-proportioned")
    if "bach nhi" in combined_text and ("market bargaining" in shot_type or "trade" in combined_text):
        cast_notes.append("Bach Nhi must appear as the trader or host at the stall, with the visiting survivors clearly separate from him")
    if any(token in combined_text for token in ["gieng", "well", "hanging tin can", "co nuoc", "mui dong"]):
        cast_notes.append("the old well mouth or water source must stay visible in frame; do not replace the scene with a generic doorway or empty platform")
    if any(token in combined_text for token in ["writing board", "bang viet", "viet xau", "doc cham"]):
        cast_notes.append("the writing board must be visible and readable as the social focus of the scene, not hidden offscreen")
    if any(token in combined_text for token in ["crystals", "cracked stones", "mutant teeth", "dat len ban", "placed on the table"]):
        cast_notes.append("the trade goods on the table must be the visual center, with one owner presenting them, not duplicated people")

    action_text = " ".join(actions).lower()
    detail_focus = "close" in shot_type or "detail" in shot_type or "insert" in shot_type or scene_center_kind == "object-center"
    wide_focus = "wide" in shot_type or "establishing" in shot_type or "environment" in shot_type
    action_focus = any(token in shot_type for token in ["action", "threat", "movement", "predator", "doorway"]) or any(
        token in action_text for token in ["runs", "drags", "kicks", "passes through", "enters", "attacks", "hides", "crawls", "opens", "pulls", "stops", "pushes"]
    )
    reaction_focus = any(token in shot_type for token in ["reaction", "single", "emotion"]) or any(
        token in action_text for token in ["looks", "stares", "realizes", "hesitates", "decides", "watches", "turns away", "listens"]
    )
    market_focus = "market bargaining" in shot_type or "market exchange" in shot_type
    threshold_focus = "threshold negotiation" in shot_type or "guarded threshold" in shot_type or "doorway tension" in shot_type
    journey_focus = "journey shot" in shot_type or "radio-listening" in shot_type or "ration-stop" in shot_type
    discovery_focus = "resource discovery" in shot_type or "well" in shot_type
    transport_focus = "injured transport" in shot_type
    trade_goods_focus = any(token in combined_text for token in ["crystals", "cracked stones", "mutant teeth", "trade goods", "placed on the table"])
    child_exchange_focus = scene_center_kind == "exchange-center" and any(token in combined_text for token in ["ninh", "tieu mai"])
    child_present = any(token in combined_text for token in ["ninh", "tieu mai", "tieu bao", "tieu ngo"])
    single_presenter_focus = scene_center_kind == "object-center" and named_people <= 1

    story_subjects = []
    for item in [scene_center_subject, primary_subject, *must_show]:
        item = str(item).strip()
        if not item:
            continue
        low = item.lower()
        if any(token in low for token in [
            "lam tich", "tan da", "ninh", "tieu mai", "tieu ngo", "tieu bao", "a that", "a muc",
            "di man", "bach nhi", "thiet oa", "moc sanh", "la kieu", "hau seo", "the exact survivor"
        ]):
            if item not in story_subjects:
                story_subjects.append(item)
    if child_exchange_focus:
        story_subjects = [item for item in story_subjects if any(token in item.lower() for token in ["ninh", "tieu mai"])][:2]
    elif single_presenter_focus:
        story_subjects = story_subjects[:1]
    story_setting = [item for item in ([scene_center_location] + setting) if item and "District 17 wasteland survival setting" not in item][:2]
    def clean_fragment(text: str) -> str:
        text = str(text).strip()
        text = text.replace("literal story beat from the current narration:", "").strip()
        text = text.replace("sports-bikini-style top, top only", "fitted thick-strap weathered survival top")
        text = text.replace("sports-bikini-style top", "fitted thick-strap weathered survival top")
        text = text.replace("sport bikini top", "fitted thick-strap weathered survival top")
        text = re.sub(r"\bmale\b[^,.]{0,80}\b(crop top|droptop|strappy top|spaghetti straps|bare midriff|exposed waist|exposed belly)\b", "adult male in rugged layered wasteland clothing", text, flags=re.IGNORECASE)
        text = re.sub(r"\bman\b[^,.]{0,80}\b(crop top|droptop|strappy top|spaghetti straps|bare midriff|exposed waist|exposed belly)\b", "adult man in rugged layered wasteland clothing", text, flags=re.IGNORECASE)
        return text[:180]

    story_actions = [clean_fragment(item) for item in ([scene_center_action] + actions[:2]) if clean_fragment(item)]
    dedup_actions = []
    for item in story_actions:
        if item not in dedup_actions:
            dedup_actions.append(item)
    story_actions = dedup_actions[:2]
    story_props = [item for item in ([scene_center_object] + props[:2]) if item]
    dedup_props = []
    for item in story_props:
        if item not in dedup_props:
            dedup_props.append(item)
    story_props = dedup_props[:2]

    if detail_focus:
        face_control = (
            "story-specific insert or close detail shot, keep the narrated object or small action as the clear center of frame, show only the hands, object, wound, writing board, water source, doorway gap, face, or body parts actually needed by the narration, "
            "no extra characters, no repeated shelter overview, no glamour framing, no random second person"
        )
    elif market_focus:
        face_control = (
            "medium-wide market bargaining shot, rail-junction trading post readable, seller and buyer both visible when present, "
            "price board, goods, train-car stall, or locked water container visible if named, no solo glamour portrait, environment must read immediately"
        )
    elif threshold_focus:
        face_control = (
            "threshold confrontation shot, doorway or checkpoint readable, both sides of the exchange visible when present, "
            "distance, guard posture, and entry terms readable, no portrait-only crop, no flattened background"
        )
    elif journey_focus:
        face_control = (
            "journey or group-survival shot, environment and travel condition readable first, group spacing clear, wheelchair radio or ration object shown only if named, "
            "do not collapse into one-person portrait"
        )
    elif discovery_focus:
        face_control = (
            "discovery shot with environment plus object both readable, show what was found and who reacts to it, the discovered object must be unmistakable at a glance, "
            "not a headshot, not a glamour portrait, keep the discovery context in frame"
        )
    elif trade_goods_focus:
        face_control = (
            "object-centered trade-table shot, one presenter and the trade goods clearly visible on the table, crystals or mutant teeth readable at first glance, "
            "only one presenter unless the narration names another person, presenter's hands and upper body near the table, no duplicated presenter, no cloned second body, no portrait-only crop"
        )
    elif child_exchange_focus:
        face_control = (
            "child dialogue shot, exactly two children in frame: Ninh and Tieu Mai, clearly child-sized with the writing board visible between them, emotional exchange readable, "
            "no adult replacement, no adult body proportions, no glamorized posing"
        )
    elif single_presenter_focus:
        face_control = (
            "single-subject object-centered shot, exactly one character presenting or reacting to the object, the object must stay central and readable, "
            "no duplicated copy of the same person, no invented second presenter, no portrait-only crop"
        )
    elif transport_focus:
        face_control = (
            "injured transport shot, wheelchair or stretcher clearly visible with the injured person and nearby handler, "
            "body relationship readable, no portrait-only framing"
        )
    elif wide_focus:
        face_control = (
            "wide cinematic establishing shot, environment and threat geography readable first, characters only as large as needed for the current beat, "
            "do not collapse every scene back into a medium shelter two-shot"
        )
    elif action_focus:
        face_control = (
            "dynamic cinematic action shot with the current movement clearly readable, complete anatomy, readable hands and feet when visible, "
            "separate bodies, clear spacing between characters, no fused limbs, no overlapping torsos, no tangled poses"
        )
    elif named_people >= 2:
        face_control = (
            "multi-character story shot only because this scene truly needs multiple people, each named person clearly separated in space with readable role and age, "
            "no fixed left-right blocking unless the narration implies it, no repeated shelter tableau, no body overlap, no one merged into the other"
        )
    elif reaction_focus:
        face_control = (
            "medium or close reaction shot focused on the current emotional beat, one character only if the narration focuses on one character, "
            "face readable, posture readable, body anatomy natural, no glamour portrait"
        )
    else:
        face_control = (
            "story-accurate cinematic shot matching the current narration, clear natural adult Asian face when visible, "
            "half-body or medium framing preferred when anatomy is complex, complete limbs, no fused bodies, no repeated default composition"
        )

    prompt_parts = []
    if local_prompt_frontload:
        prompt_parts.append(
            "PRIORITY STORY LOCK FOR THIS EXACT SCENE ONLY: "
            + " / ".join(local_prompt_frontload[-5:])
        )
    prompt_parts.extend([
        BEAT_FIRST_VISUAL_RULE,
        beat_pack["prompt"],
        STORY_FIRST_VISUAL_RULE,
        FEMALE_SEXY_BEAT_RULE,
        ACTION_COMPLETENESS_RULE,
        WASTELAND_ACTION_STYLE_RULE,
        face_control,
        "cinematic post-apocalyptic survival frame, current scene only, no repeated shelter tableau, no default two-shot unless the scene truly needs two people",
    ])
    if "lam tich" in combined_text:
        prompt_parts.append("Lam Tich only wears a fitted thick-strap weathered survival top plus rugged shorts; never bikini bottoms or a two-piece swimsuit, and never let her clothing override the current story action")
    if male_only_notes:
        prompt_parts.append("Male characters only: masculine wasteland clothing with covered waist; do not copy Lam Tich clothing or feminine styling onto any male character")
    if scene_center_kind:
        prompt_parts.append(f"visual center for this scene: {scene_center_kind}")
    prompt_parts.append("required beat center checklist: " + beat_pack["required_center"])
    if story_subjects:
        if child_exchange_focus:
            prompt_parts.append("show exactly these two child subjects and nobody else in the foreground: " + "; ".join(story_subjects[:2]))
        elif single_presenter_focus:
            prompt_parts.append("show exactly one foreground presenter: " + story_subjects[0])
        else:
            prompt_parts.append("show these exact scene subjects: " + "; ".join(story_subjects[:3]))
    if story_setting:
        prompt_parts.append("exact setting for this scene: " + ", ".join(story_setting))
    if story_actions:
        prompt_parts.append("visible action in this frame: " + " / ".join(story_actions))
    elif narration:
        prompt_parts.append("narration source of truth for action: " + clean_fragment(narration))
    if story_props:
        prompt_parts.append("this object or prop must stay readable in frame: " + ", ".join(story_props))
    if local_rescue_notes:
        prompt_parts.append("local rescue notes for this exact scene only: " + " / ".join(local_rescue_notes[:6]))
    if not story_subjects and fallback_prompt:
        prompt_parts.append(clean_fragment(fallback_prompt))
    prompt = ", ".join(part for part in prompt_parts if part)
    if male_only_notes:
        prompt = f"{prompt}, {'; '.join(male_only_notes)}"
    if female_only_notes:
        prompt = f"{prompt}, {'; '.join(female_only_notes)}"
    if cast_notes:
        prompt = f"{prompt}, {'; '.join(cast_notes)}"
    positive_suffix = DEFAULT_POSITIVE_SUFFIX
    if child_present:
        positive_suffix = positive_suffix.replace("clear natural human faces", "clear natural child and adult faces with correct age proportions")
    if positive_suffix.lower() not in prompt.lower():
        prompt = f"{prompt}, {positive_suffix}"
    return prompt


def scene_reference_policy(scene: dict[str, Any], default_reference: str, default_denoise: float) -> tuple[str, float | None]:
    if not default_reference:
        return "", None
    shot_type = str(scene.get("visual_shot_type") or "").strip().lower()
    action_text = ", ".join(str(item).strip() for item in (scene.get("visual_action") or []) if str(item).strip()).lower()
    scene_id = str(scene.get("id") or "")
    if scene_id.endswith("001"):
        return default_reference, min(max(default_denoise, 0.30), 0.34)
    if "close" in shot_type or "detail" in shot_type:
        return "", None
    if "wide" in shot_type or "establishing" in shot_type:
        return default_reference, 0.42
    if "action" in shot_type or "predator" in shot_type or "threat" in shot_type or "hiding" in action_text:
        return default_reference, 0.52
    return default_reference, default_denoise


def node_choices(object_info: dict[str, Any], class_type: str, input_name: str) -> list[str]:
    node = object_info.get(class_type, {})
    required = node.get("input", {}).get("required", {})
    optional = node.get("input", {}).get("optional", {})
    spec = required.get(input_name) or optional.get(input_name) or []
    if isinstance(spec, list) and spec and isinstance(spec[0], list):
        return [str(item) for item in spec[0]]
    return []


def score_name(name: str, preferred: list[str], avoid: list[str] | None = None) -> int:
    lower = name.lower()
    score = 0
    for index, token in enumerate(preferred):
        if token in lower:
            score += 100 - index * 8
    for token in avoid or []:
        if token in lower:
            score -= 65
    if name.endswith(".safetensors"):
        score += 8
    if "pruned" in lower or "fp16" in lower:
        score += 5
    return score


def choose_model(requested: str, available: list[str], preferred: list[str], avoid: list[str] | None = None, required: bool = True) -> str:
    requested = requested.strip()
    if requested and requested.lower() != "auto":
        if requested in available:
            return requested
        if required:
            choices = "\n  - ".join(available[:30])
            raise SystemExit(f"Model not found in ComfyUI: {requested}\nAvailable examples:\n  - {choices}")
        return ""
    if not available:
        if required:
            raise SystemExit("No compatible model choices were reported by ComfyUI.")
        return ""
    return max(available, key=lambda name: score_name(name, preferred, avoid))


def choose_optional_model(requested: str, available: list[str], preferred: list[str], avoid: list[str] | None = None) -> str:
    requested = requested.strip()
    if requested and requested.lower() != "auto":
        return choose_model(requested, available, preferred, avoid, required=False)
    if not available:
        return ""
    best = max(available, key=lambda name: score_name(name, preferred, avoid))
    return best if score_name(best, preferred, avoid) > 0 else ""


def filter_loras(requested: list[str], available: list[str]) -> list[str]:
    if not requested:
        return []
    kept = []
    available_lookup = {name.lower(): name for name in available}
    for value in requested:
        name = value.split(":", 1)[0].strip()
        if name.lower() in available_lookup:
            kept.append(value.replace(name, available_lookup[name.lower()], 1))
        else:
            print(f"Skipping missing LoRA: {name}")
    return kept


def apply_preset(args: argparse.Namespace) -> None:
    if args.preset == "safe":
        if not args.width and not args.height:
            args.width, args.height = size_for_ratio(args.aspect_ratio)
        args.steps = min(args.steps, 20)
        args.hires_scale = min(args.hires_scale, 1.25)
        args.hires_steps = min(args.hires_steps, 8)
        args.vae_tile_size = min(args.vae_tile_size, 320)
    elif args.preset == "quality":
        if not args.width and not args.height:
            args.width, args.height = size_for_ratio(args.aspect_ratio)
        args.steps = max(args.steps, 26)
        args.hires_scale = max(args.hires_scale, 1.5)
        args.hires_steps = max(args.hires_steps, 12)


def inspect_comfy(args: argparse.Namespace) -> dict[str, Any]:
    request_json(args.comfy_url, "/system_stats", timeout=10)
    object_info = request_json(args.comfy_url, "/object_info", timeout=20)
    return {
        "checkpoints": node_choices(object_info, "CheckpointLoaderSimple", "ckpt_name"),
        "vaes": node_choices(object_info, "VAELoader", "vae_name"),
        "loras": node_choices(object_info, "LoraLoader", "lora_name"),
        "upscalers": node_choices(object_info, "UpscaleModelLoader", "model_name"),
        "samplers": node_choices(object_info, "KSampler", "sampler_name"),
        "schedulers": node_choices(object_info, "KSampler", "scheduler"),
    }


def resolve_local_models(args: argparse.Namespace) -> dict[str, Any]:
    inventory = inspect_comfy(args)
    args.checkpoint = choose_model(args.checkpoint, inventory["checkpoints"], CHECKPOINT_PREFERENCES, CHECKPOINT_AVOID, required=True)
    args.vae = choose_optional_model(args.vae, inventory["vaes"], VAE_PREFERENCES)
    args.upscale_model = choose_optional_model(args.upscale_model, inventory["upscalers"], UPSCALER_PREFERENCES)
    args.lora = filter_loras(args.lora, inventory["loras"])
    if inventory["samplers"] and args.sampler not in inventory["samplers"]:
        args.sampler = "euler_ancestral" if "euler_ancestral" in inventory["samplers"] else inventory["samplers"][0]
    if inventory["schedulers"] and args.scheduler not in inventory["schedulers"]:
        args.scheduler = "karras" if "karras" in inventory["schedulers"] else inventory["schedulers"][0]
    return inventory


def parse_loras(values: list[str]) -> list[tuple[str, float, float]]:
    loras = []
    for value in values:
        if not value.strip():
            continue
        parts = [part.strip() for part in value.split(":")]
        name = parts[0]
        model_strength = float(parts[1]) if len(parts) > 1 and parts[1] else 0.45
        clip_strength = float(parts[2]) if len(parts) > 2 and parts[2] else model_strength
        loras.append((name, model_strength, clip_strength))
    return loras


def add_loras(workflow: dict[str, Any], model_ref: list[Any], clip_ref: list[Any], loras: list[tuple[str, float, float]]) -> tuple[list[Any], list[Any], int]:
    next_id = max(int(key) for key in workflow) + 1
    for lora_name, model_strength, clip_strength in loras:
        node_id = str(next_id)
        next_id += 1
        workflow[node_id] = {
            "class_type": "LoraLoader",
            "inputs": {
                "model": model_ref,
                "clip": clip_ref,
                "lora_name": lora_name,
                "strength_model": model_strength,
                "strength_clip": clip_strength,
            },
        }
        model_ref = [node_id, 0]
        clip_ref = [node_id, 1]
    return model_ref, clip_ref, next_id


def maybe_tiled_decode(args: argparse.Namespace, workflow: dict[str, Any], samples_ref: list[Any], vae_ref: list[Any], node_id: int) -> tuple[list[Any], int]:
    if args.tiled_vae:
        workflow[str(node_id)] = {
            "class_type": "VAEDecodeTiled",
            "inputs": {
                "samples": samples_ref,
                "vae": vae_ref,
                "tile_size": args.vae_tile_size,
                "overlap": args.vae_overlap,
                "temporal_size": 64,
                "temporal_overlap": 8,
            },
        }
    else:
        workflow[str(node_id)] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": samples_ref, "vae": vae_ref},
        }
    return [str(node_id), 0], node_id + 1


def maybe_tiled_encode(args: argparse.Namespace, workflow: dict[str, Any], image_ref: list[Any], vae_ref: list[Any], node_id: int) -> tuple[list[Any], int]:
    if args.tiled_vae:
        workflow[str(node_id)] = {
            "class_type": "VAEEncodeTiled",
            "inputs": {
                "pixels": image_ref,
                "vae": vae_ref,
                "tile_size": args.vae_tile_size,
                "overlap": args.vae_overlap,
                "temporal_size": 64,
                "temporal_overlap": 8,
            },
        }
    else:
        workflow[str(node_id)] = {
            "class_type": "VAEEncode",
            "inputs": {"pixels": image_ref, "vae": vae_ref},
        }
    return [str(node_id), 0], node_id + 1


def prepare_reference_image(args: argparse.Namespace) -> str:
    if not args.reference_image:
        return ""
    source = Path(args.reference_image).expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"Reference image not found: {source}")
    args.comfy_input_dir.mkdir(parents=True, exist_ok=True)
    target = args.comfy_input_dir / f"auto_video_reference{source.suffix.lower() or '.png'}"
    shutil.copy2(source, target)
    return target.name


def build_sd15_workflow(args: argparse.Namespace, prompt: str, seed: int, width: int, height: int) -> dict[str, Any]:
    workflow: dict[str, Any] = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": args.checkpoint},
        }
    }
    model_ref: list[Any] = ["1", 0]
    clip_ref: list[Any] = ["1", 1]
    if args.vae:
        workflow["2"] = {
            "class_type": "VAELoader",
            "inputs": {"vae_name": args.vae},
        }
        vae_ref: list[Any] = ["2", 0]
    else:
        vae_ref = ["1", 2]
    model_ref, clip_ref, next_id = add_loras(workflow, model_ref, clip_ref, parse_loras(args.lora))

    pos_id = str(next_id)
    neg_id = str(next_id + 1)
    latent_id = str(next_id + 2)
    sampler_id = str(next_id + 3)
    next_id += 4
    workflow[pos_id] = {"class_type": "CLIPTextEncode", "inputs": {"clip": clip_ref, "text": prompt}}
    workflow[neg_id] = {"class_type": "CLIPTextEncode", "inputs": {"clip": clip_ref, "text": args.negative_prompt}}
    reference_filename = prepare_reference_image(args)
    if reference_filename:
        load_id = latent_id
        scale_id = str(next_id)
        encode_id = str(next_id + 1)
        next_id += 2
        workflow[load_id] = {"class_type": "LoadImage", "inputs": {"image": reference_filename}}
        workflow[scale_id] = {
            "class_type": "ImageScale",
            "inputs": {
                "image": [load_id, 0],
                "upscale_method": "lanczos",
                "width": width,
                "height": height,
                "crop": "center",
            },
        }
        workflow[encode_id] = {"class_type": "VAEEncode", "inputs": {"pixels": [scale_id, 0], "vae": vae_ref}}
        latent_ref = [encode_id, 0]
        first_denoise = args.reference_denoise
    else:
        workflow[latent_id] = {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}}
        latent_ref = [latent_id, 0]
        first_denoise = 1.0
    workflow[sampler_id] = {
        "class_type": "KSampler",
        "inputs": {
            "model": model_ref,
            "positive": [pos_id, 0],
            "negative": [neg_id, 0],
            "latent_image": latent_ref,
            "seed": seed,
            "steps": args.steps,
            "cfg": args.cfg,
            "sampler_name": args.sampler,
            "scheduler": args.scheduler,
            "denoise": first_denoise,
        },
    }

    image_ref, next_id = maybe_tiled_decode(args, workflow, [sampler_id, 0], vae_ref, next_id)

    if args.hires_scale > 1:
        scaled_w = int(width * args.hires_scale)
        scaled_h = int(height * args.hires_scale)
        scale_id = str(next_id)
        next_id += 1
        workflow[scale_id] = {
            "class_type": "ImageScale",
            "inputs": {
                "image": image_ref,
                "upscale_method": args.latent_upscale_method,
                "width": scaled_w,
                "height": scaled_h,
                "crop": "disabled",
            },
        }
        hires_latent_ref, next_id = maybe_tiled_encode(args, workflow, [scale_id, 0], vae_ref, next_id)
        hires_sampler_id = str(next_id)
        next_id += 1
        workflow[hires_sampler_id] = {
            "class_type": "KSampler",
            "inputs": {
                "model": model_ref,
                "positive": [pos_id, 0],
                "negative": [neg_id, 0],
                "latent_image": hires_latent_ref,
                "seed": seed + 1,
                "steps": args.hires_steps,
                "cfg": args.cfg,
                "sampler_name": args.sampler,
                "scheduler": args.scheduler,
                "denoise": args.hires_denoise,
            },
        }
        image_ref, next_id = maybe_tiled_decode(args, workflow, [hires_sampler_id, 0], vae_ref, next_id)

    if args.upscale_model:
        loader_id = str(next_id)
        upscale_id = str(next_id + 1)
        next_id += 2
        workflow[loader_id] = {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": args.upscale_model},
        }
        workflow[upscale_id] = {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {"upscale_model": [loader_id, 0], "image": image_ref},
        }
        image_ref = [upscale_id, 0]

    if args.final_width and args.final_height:
        final_scale_id = str(next_id)
        next_id += 1
        workflow[final_scale_id] = {
            "class_type": "ImageScale",
            "inputs": {
                "image": image_ref,
                "upscale_method": "lanczos",
                "width": args.final_width,
                "height": args.final_height,
                "crop": "center",
            },
        }
        image_ref = [final_scale_id, 0]

    save_id = str(next_id)
    workflow[save_id] = {
        "class_type": "SaveImage",
        "inputs": {"images": image_ref, "filename_prefix": args.prefix},
    }
    return workflow


def submit_and_wait(base_url: str, workflow: dict[str, Any], timeout: int, poll_seconds: float) -> dict[str, Any]:
    queued = request_json(base_url, "/prompt", {"prompt": workflow, "client_id": str(uuid.uuid4())}, timeout=30)
    prompt_id = queued.get("prompt_id")
    if not prompt_id:
        raise SystemExit(f"ComfyUI did not return prompt_id: {queued}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        history = request_json(base_url, f"/history/{prompt_id}", timeout=30)
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(poll_seconds)
    raise SystemExit(f"ComfyUI generation timed out after {timeout}s: {prompt_id}")


def extract_first_image(history_item: dict[str, Any]) -> dict[str, str]:
    for node_output in history_item.get("outputs", {}).values():
        images = node_output.get("images") or []
        if images:
            return images[0]
    raise SystemExit("ComfyUI finished but no output image was found.")


def copy_latest_output_image(output_dir: Path, prefix: str, started_at: float, output: Path) -> bool:
    if not output_dir.exists():
        return False
    candidates = sorted(
        (
            path
            for path in output_dir.rglob(f"{prefix}*.png")
            if path.is_file() and path.stat().st_mtime >= started_at - 2
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return False
    output.write_bytes(candidates[0].read_bytes())
    return True


def save_comfy_image(base_url: str, image_info: dict[str, str], output: Path) -> None:
    query = urllib.parse.urlencode(
        {
            "filename": image_info["filename"],
            "subfolder": image_info.get("subfolder", ""),
            "type": image_info.get("type", "output"),
        }
    )
    output.write_bytes(download_bytes(base_url, f"/view?{query}"))


def image_integrity_checks(path: Path) -> tuple[int, list[str]]:
    failures: list[str] = []
    score = 55
    if not path.exists():
        return 0, ["image file is missing"]
    size = path.stat().st_size
    if size < 50_000:
        failures.append(f"image file is too small ({size} bytes)")
    else:
        score += 20
    try:
        from PIL import Image, ImageStat  # type: ignore

        with Image.open(path) as image:
            width, height = image.size
            if width < 256 or height < 256:
                failures.append(f"image dimensions are too small ({width}x{height})")
            else:
                score += 10
            stat = ImageStat.Stat(image.convert("L").resize((64, 64)))
            brightness = float(stat.mean[0]) if stat.mean else 0.0
            variance = float(stat.var[0]) if stat.var else 0.0
            if variance < 18:
                failures.append("image looks nearly blank or flat by pixel variance")
            else:
                score += 10
            if brightness < 5 or brightness > 250:
                failures.append("image is almost fully black or white")
            else:
                score += 5
    except Exception:
        score += 10
    return min(score, 100), failures


def validate_generated_scene(scene: dict[str, Any], image_path: Path, prompt: str, attempt: int) -> dict[str, Any]:
    beat_pack = beat_prompt_pack(scene)
    prompt_lower = prompt.lower()
    failures: list[str] = []
    required_terms = [term.strip(" .,:;") for term in re.split(r",| or | and ", beat_pack["required_center"].lower()) if term.strip()]
    matched_terms = [term for term in required_terms if term and term in prompt_lower]
    if required_terms and not matched_terms:
        failures.append("prompt does not carry the inferred story-beat center strongly enough")
    if "generic standing portrait" not in prompt_lower and "no generic standing pose" not in prompt_lower:
        failures.append("prompt lacks explicit guard against generic standing/posing drift")
    if any(token in scene_text_blob(scene) for token in ["tan da", "male", "man", "nam", "dan ong"]):
        male_guard_terms = ["covered waist", "masculine wasteland clothing", "never sport top", "never feminine clothing"]
        if not any(term in prompt_lower for term in male_guard_terms):
            failures.append("prompt lacks male-clothing guardrail")
    image_score, image_failures = image_integrity_checks(image_path)
    failures.extend(image_failures)
    prompt_score = 35 if not failures[:2] else 20
    score = min(100, image_score + prompt_score)
    passed = score >= 40 and not image_failures and "prompt does not carry" not in " | ".join(failures)
    return {
        "status": "passed" if passed else "failed",
        "passed": passed,
        "attempt": attempt,
        "score_percent": score,
        "beat_type": beat_pack["beat"],
        "required_center": beat_pack["required_center"],
        "failures": failures,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "engine": "python-lightweight-beat-integrity-v1",
        "note": "This engine checks image integrity and story-beat prompt coverage after each generation; manual OpsBoard QA is still Codex visual review.",
    }


def retry_composition_strategy(scene: dict[str, Any], validation: dict[str, Any], attempt: int) -> str:
    beat = str(validation.get("beat_type") or "story_event")
    object_text = str(scene.get("scene_center_object") or "").strip()
    action_text = str(scene.get("scene_center_action") or "").strip()
    subject_text = str(scene.get("scene_center_subject") or scene.get("beat_subject") or "").strip()
    location_text = str(scene.get("scene_center_location") or "").strip()
    anchor = "; ".join(item for item in [action_text, object_text, location_text, subject_text] if item)
    beat_strategy = {
        "message_signal": "compose as an over-shoulder or hand-detail shot where the radio/message device is closest to camera and listeners react behind it",
        "resource_survival": "compose as dirty hands and the survival resource in the foreground, with thirst, injury, or ration pressure visible behind it",
        "trade_object": "compose as a trade-table shot with goods/payment between buyer and seller; hands point to the exact object, not faces posing",
        "threshold_entry": "compose across the door/gate/checkpoint line so the blocked passage and guard distance are readable",
        "injury_transport": "compose around the wound/stretcher/wheelchair/carrying action; body weight and helper hands must explain the injury",
        "creature_threat": "compose with the creature threat direction readable first, using claws/fangs/shadow/attack angle and survivor spacing",
        "child_exchange": "compose at child height with the writing board/handed object between the children or adult and child",
        "elder_tool": "compose around old hands, tool, repair/warning action, and aged posture, not a generic face portrait",
        "object_evidence": "compose as a close insert where the evidence object or hand action fills the foreground and only necessary body parts appear",
        "location_transition": "compose as a travel/route frame where road, rail, vehicle, weather, ruins, or obstacle leads the eye through the scene",
        "moral_reaction": "compose the reaction line-of-sight toward the cause, with cause visible in frame so emotion is not floating",
        "character_action": "compose the named character mid-action with hands, feet, tool, wound, or target visible, not a static model stance",
    }.get(beat, "compose the exact story event with foreground action/object, midground participants, and background wasteland pressure")
    attempt_strategy = [
        "use wider framing than the failed attempt so object, action, and location can all be read",
        "move the required object/action into the lower foreground and make character faces secondary",
        "reduce glamour lighting and pose energy; use documentary survival blocking with dirty practical motion",
        "simplify to one clear action and one clear object; remove any invented extra character or fashion pose",
    ][min(max(attempt - 1, 0), 3)]
    anchor_text = f" Scene anchors that must remain: {anchor}." if anchor else ""
    return f"{beat_strategy}; {attempt_strategy}.{anchor_text}"


def apply_validator_retry_notes(scene: dict[str, Any], validation: dict[str, Any], attempt: int) -> None:
    beat = str(validation.get("beat_type") or "story_event")
    required = str(validation.get("required_center") or "the exact narrated event")
    failures = "; ".join(str(item) for item in (validation.get("failures") or [])[:3])
    strategy = retry_composition_strategy(scene, validation, attempt)
    append_scene_note(
        scene,
        "local_prompt_frontload",
        f"Auto QA retry {attempt}: lock the story beat first ({beat}); foreground must show {required}. New composition for this retry: {strategy}",
    )
    append_scene_note(
        scene,
        "local_prompt_frontload",
        f"Auto QA retry {attempt}: this retry must be visibly different from the failed image by changing framing/blocking around the same story beat, not by changing the story.",
    )
    if failures:
        append_scene_note(scene, "local_rescue_notes", f"Auto QA retry {attempt} failed because: {failures}. Fix the same scene, same beat, same required object/action/location.")
    append_scene_note(scene, "local_rescue_notes", "Auto QA retry rule: do not switch to portrait, pose, bikini, crop-top, or character glamour unless narration explicitly says so.")
    scene["qa_rescue_mode"] = True
    scene["qa_retry_limit"] = max(int(scene.get("qa_retry_limit") or 1), attempt + 1)


def generate_scene(args: argparse.Namespace, scene: dict[str, Any], index: int, storyboard_dir: Path, assets_dir: Path) -> Path:
    output = resolve(storyboard_dir, scene["image"]) if scene.get("image") else assets_dir / f"scene-{index + 1:02d}.{args.output_format}"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not args.overwrite:
        scene["image"] = relpath(output, storyboard_dir)
        return output
    width, height = (args.width, args.height) if args.width and args.height else size_for_ratio(args.aspect_ratio)
    max_attempts = 1
    if args.qa_engine:
        max_attempts = max(1, min(5, int(scene.get("qa_retry_limit") or args.qa_retry_limit or 5)))
    final_validation: dict[str, Any] | None = None
    for attempt in range(1, max_attempts + 1):
        prompt = scene_prompt(scene)
        if not prompt:
            raise SystemExit(f"Scene {index + 1} has no image prompt.")
        seed = (args.seed + index + attempt - 1) if args.seed >= 0 else int(time.time() * 1000) % 2_147_483_647
        scene_reference_image, scene_reference_denoise = scene_reference_policy(scene, args.reference_image, args.reference_denoise)
        original_reference_image = args.reference_image
        original_reference_denoise = args.reference_denoise
        args.reference_image = scene_reference_image
        args.reference_denoise = scene_reference_denoise if scene_reference_denoise is not None else original_reference_denoise
        try:
            workflow = build_sd15_workflow(args, prompt, seed, width, height)
        finally:
            args.reference_image = original_reference_image
            args.reference_denoise = original_reference_denoise
        started_at = time.time()
        history = submit_and_wait(args.comfy_url, workflow, args.timeout, args.poll_seconds)
        try:
            save_comfy_image(args.comfy_url, extract_first_image(history), output)
        except SystemExit as exc:
            if "no output image was found" not in str(exc):
                raise
            if not copy_latest_output_image(args.comfy_output_dir, args.prefix, started_at, output):
                raise
        scene["image"] = relpath(output, storyboard_dir)
        scene["local_image"] = {
            "provider": "comfy-local",
            "mode": "sd15-low-vram",
            "checkpoint": args.checkpoint,
            "vae": args.vae,
            "loras": args.lora,
            "seed": seed,
            "size": f"{width}x{height}",
            "hires_scale": args.hires_scale,
            "upscale_model": args.upscale_model,
            "reference_image": str(Path(scene_reference_image).resolve()) if scene_reference_image else "",
            "reference_denoise": scene_reference_denoise if scene_reference_image else None,
        }
        if not args.qa_engine:
            return output
        final_validation = validate_generated_scene(scene, output, prompt, attempt)
        scene["local_image"]["validator"] = final_validation
        if final_validation["passed"]:
            return output
        if attempt < max_attempts:
            apply_validator_retry_notes(scene, final_validation, attempt)
            try:
                output.unlink()
            except FileNotFoundError:
                pass
            continue
        final_validation["status"] = "skipped_after_failed_attempts"
        final_validation["passed"] = False
        scene["local_image"]["validator"] = final_validation
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate storyboard images locally with a low-VRAM cinematic ComfyUI workflow.")
    parser.add_argument("--storyboard", type=Path)
    parser.add_argument("--comfy-url", default=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188"))
    parser.add_argument("--checkpoint", default=os.environ.get("SD15_CHECKPOINT", "auto"))
    parser.add_argument("--vae", default=os.environ.get("SD15_VAE", "auto"))
    parser.add_argument("--lora", action="append", default=[], help="Optional LoRA name or name:model_strength:clip_strength.")
    parser.add_argument("--preset", choices=["safe", "balanced", "quality"], default="balanced")
    parser.add_argument("--aspect-ratio", default="16:9")
    parser.add_argument("--width", type=int, default=0)
    parser.add_argument("--height", type=int, default=0)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--cfg", type=float, default=6.5)
    parser.add_argument("--sampler", default="dpmpp_2m")
    parser.add_argument("--scheduler", default="karras")
    parser.add_argument("--hires-scale", type=float, default=1.5)
    parser.add_argument("--hires-steps", type=int, default=10)
    parser.add_argument("--hires-denoise", type=float, default=0.34)
    parser.add_argument("--latent-upscale-method", default="lanczos")
    parser.add_argument("--tiled-vae", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--vae-tile-size", type=int, default=384)
    parser.add_argument("--vae-overlap", type=int, default=48)
    parser.add_argument("--upscale-model", default=os.environ.get("SD_UPSCALE_MODEL", "auto"))
    parser.add_argument("--final-width", type=int, default=1920)
    parser.add_argument("--final-height", type=int, default=1080)
    parser.add_argument("--negative-prompt", default=DEFAULT_NEGATIVE)
    parser.add_argument("--reference-image", default=os.environ.get("LOCAL_IMAGE_REFERENCE", ""), help="Optional local image used as img2img composition reference.")
    parser.add_argument("--reference-denoise", type=float, default=0.28, help="Img2img denoise for --reference-image. Lower keeps composition, higher changes more.")
    parser.add_argument("--comfy-input-dir", type=Path, default=WORK_ROOT / "ComfyUI_windows_portable_nvidia" / "ComfyUI_windows_portable" / "ComfyUI" / "input")
    parser.add_argument("--output-format", default="png")
    parser.add_argument("--prefix", default="auto-video-local")
    parser.add_argument("--comfy-output-dir", type=Path, default=WORK_ROOT / "ComfyUI_windows_portable_nvidia" / "ComfyUI_windows_portable" / "ComfyUI" / "output")
    parser.add_argument("--seed", type=int, default=23052026)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--qa-engine", action=argparse.BooleanOptionalAction, default=True, help="Run lightweight per-image QA after each generated scene and retry failed images.")
    parser.add_argument("--qa-retry-limit", type=int, default=5, help="Maximum per-scene QA retries before keeping the final image and continuing.")
    parser.add_argument("--inspect-only", action="store_true", help="Print ComfyUI model inventory and selected local settings, then exit.")
    parser.add_argument("--start-scene", type=int, default=1, help="1-based first scene to generate.")
    parser.add_argument("--end-scene", type=int, default=0, help="1-based last scene to generate. 0 means the final scene.")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    apply_preset(args)
    inventory = resolve_local_models(args)
    selected = {
        "provider": "comfy-local",
        "mode": "sd15-low-vram",
        "preset": args.preset,
        "checkpoint": args.checkpoint,
        "vae": args.vae or "checkpoint-embedded",
        "loras": args.lora,
        "upscale_model": args.upscale_model or "final-lanczos-only",
        "reference_image": str(Path(args.reference_image).resolve()) if args.reference_image else "",
        "reference_denoise": args.reference_denoise if args.reference_image else None,
        "steps": args.steps,
        "cfg": args.cfg,
        "sampler": args.sampler,
        "scheduler": args.scheduler,
        "hires_scale": args.hires_scale,
        "hires_denoise": args.hires_denoise,
        "tiled_vae": args.tiled_vae,
        "vae_tile_size": args.vae_tile_size,
        "final_size": f"{args.final_width}x{args.final_height}",
    }
    if args.inspect_only:
        print(json.dumps({"selected": selected, "inventory_counts": {key: len(value) for key, value in inventory.items()}, "inventory_preview": {key: value[:20] for key, value in inventory.items()}}, ensure_ascii=False, indent=2))
        return
    if not args.storyboard:
        parser.error("--storyboard is required unless --inspect-only is used.")

    storyboard = args.storyboard.resolve()
    storyboard_dir = storyboard.parent
    assets_dir = storyboard_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    config = json.loads(storyboard.read_text(encoding="utf-8-sig"))
    scenes = config.get("scenes") or []
    if not scenes:
        raise SystemExit("Storyboard has no scenes.")
    start_index = max(0, args.start_scene - 1)
    end_index = args.end_scene if args.end_scene else len(scenes)
    end_index = min(len(scenes), end_index)
    if start_index >= end_index:
        raise SystemExit(f"No scenes selected: start={args.start_scene}, end={args.end_scene or len(scenes)}")
    generated = []
    for index, scene in enumerate(scenes[start_index:end_index], start=start_index):
        path = generate_scene(args, scene, index, storyboard_dir, assets_dir)
        generated.append(str(path))
        print(f"Generated local SD image: {path}")
    storyboard.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**selected, "storyboard": str(storyboard), "images": generated}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

