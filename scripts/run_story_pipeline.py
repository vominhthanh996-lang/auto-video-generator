#!/usr/bin/env python3
import argparse
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from video_presets import apply_video_format, preset_for


BASE_STYLE = (
    "premium cinematic post-apocalyptic wasteland webnovel keyframe, grounded survival drama, "
    "dirty realistic characters inside a torn tarp shelter or ruined junkyard when the scene implies shelter, "
    "rusted barrels, broken plastic sheets, patched canvas, muddy floor, scavenged metal bowls, oil lantern or weak practical light, "
    "foreground survival props, midground character action, background ruined industrial wasteland and dusty sky, "
    "warm amber practical light against cold polluted daylight, realistic grime, torn cloth, sweat, ash, dirty bandages, dark stains on cloth, "
    "35mm cinema lens, shallow depth of field, dramatic rim light, subtle film grain, muted natural colors, "
    "high contrast but not oversaturated, clear natural faces, readable eyes nose mouth and jaw, no text, no watermark"
)

REFERENCE_IMAGE_RECIPE = (
    "Reference composition recipe from Thanh's approved ChatGPT sample: cinematic 16:9 shelter interior, "
    "Lam Tich sits or kneels in the left third, her dirty but beautiful face readable in three-quarter profile; "
    "Tan Da lies or half-reclines in the right third, black tactical clothing, bandaged injured abdomen, clear side-profile face; "
    "a warm oil lantern glows between them as the visual anchor; torn tarp walls and hanging patched canvas frame the top and right side; "
    "foreground has rusty bucket, bottle, scraps, dirty survival props; background opens to a ruined industrial wasteland with haze and distant structures; "
    "lighting is warm amber lantern plus pale cold daylight from outside, deep shadows, realistic grime, no clean studio look"
)

DEFAULT_NEGATIVE = (
    "low quality, blurry, jpeg artifacts, cartoon, anime, plastic skin, oversaturated, "
    "bad anatomy, deformed hands, distorted face, extra limbs, duplicate body, ugly face, "
    "text, watermark, logo, messy composition, flat lighting, bad perspective, AI artifacts, "
    "empty landscape, generic fantasy art, beauty portrait, clean clothes, modern city, "
    "white speckles, random colored dots, noisy artifacts, oversharpened, waxy skin, "
    "blurred face, faceless character, hidden male face, villain face, idol makeup, porcelain skin, "
    "cropped head, head out of frame, face out of frame, missing female character, missing male character, "
    "single standing man, random gun pose"
    ", melted face, warped face, malformed face, asymmetrical eyes, crossed eyes, bad eyes, dead eyes, "
    "missing nose, broken nose, bad mouth, fused lips, duplicate face, two faces on one head, "
    "over-smoothed face, childlike doll face, face too far away, tiny unreadable face"
)

LAM_TICH_VISUAL = (
    "Lam Tich, a beautiful fragile sixteen-year-old Asian wasteland scavenger girl with a lovely youthful maiden look, "
    "soft delicate facial features under soot and grime, clear pretty eyes that still look tired and wary, cracked lips, "
    "messy black hair tied back with loose strands, slim malnourished body, dirty torn gray-brown coat, "
    "quiet stubborn survival beauty, pretty but believable in the wasteland, not glamorous, not clean, not doll-like"
)

TAN_DA_VISUAL = (
    "Tan Da, an injured Asian male mercenary with a clear sharply rendered face, strong straight brows, "
    "steady righteous eyes, principled protective aura, restrained masculine dignity, wet messy black hair, black tactical coat, "
    "lying or half-reclining because he cannot stand, feverish but still upright in spirit, abdomen wrapped with dirty bandages, not villainous"
)


def run(cmd, env=None):
    print("+ " + " ".join(str(part) for part in cmd), flush=True)
    subprocess.run(cmd, check=True, env=env)


def slugify(value):
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return value or "story-video"


def resolve(base, value):
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def read_source(path):
    text = path.read_text(encoding="utf-8-sig")
    vietnamese_marks = sum(1 for char in text.lower() if char in "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")
    if text.count("?") >= 8 and vietnamese_marks == 0:
        raise SystemExit("Source text looks encoding-damaged. Save it as UTF-8 and try again.")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def split_sentences(text):
    pieces = []
    for paragraph in re.split(r"\n+", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph.split()) <= 14:
            pieces.append(paragraph)
            continue
        parts = re.split(r"(?<=[.!?。！？])\s+", paragraph)
        pieces.extend(part.strip() for part in parts if part.strip())
    return pieces


def group_for_scenes(text, min_scenes, max_scenes, words_per_image):
    pieces = split_sentences(text)
    word_count = len(re.findall(r"\S+", text))
    target = round(word_count / words_per_image)
    target = max(min_scenes, min(max_scenes, target))
    target_words = max(18, math.ceil(word_count / target))

    groups = []
    current = []
    current_words = 0
    for piece in pieces:
        words = len(re.findall(r"\S+", piece))
        if current and current_words + words > target_words and len(groups) < target - 1:
            groups.append(" ".join(current))
            current = [piece]
            current_words = words
        else:
            current.append(piece)
            current_words += words
    if current:
        groups.append(" ".join(current))
    return groups, word_count


def image_prompt(narration, style):
    compact = narration[:320].replace("\n", " ")
    lower = narration.lower()
    visual = "cinematic scene matching the narration"
    if "mưa" in lower:
        visual = "rainy cinematic environment with wet reflections"
    elif "phế thổ" in lower or "nhiễm xạ" in lower:
        visual = "post apocalyptic radioactive wasteland, red dusty sky, ruined city edge"
    elif "chó" in lower or "thú" in lower:
        visual = "tense survival scene with mutated animals in ruined wasteland"
    elif "tường" in lower or "thành" in lower:
        visual = "distant giant city wall beyond polluted wasteland"
    elif "thịt hộp" in lower or "đồ ăn" in lower:
        visual = "close cinematic survival scene focused on precious food supplies"
    elif "máu" in lower or "vết thương" in lower:
        visual = "dark tense wounded survivor scene, realistic blood, dramatic shadows"
    return f"{visual}, {style}. Narration mood: {compact}"


def read_source(path):
    text = path.read_text(encoding="utf-8-sig")
    vietnamese_marks = sum(
        1
        for char in text.lower()
        if char
        in "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    )
    if text.count("?") >= 8 and vietnamese_marks == 0:
        raise SystemExit("Source text looks encoding-damaged. Save it as UTF-8 and try again.")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def has_any(text, words):
    return any(word in text for word in words)


def normalize_vi(text):
    decomposed = unicodedata.normalize("NFD", text.lower())
    ascii_text = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return ascii_text.replace("đ", "d")


def image_prompt(narration, style):
    compact = narration[:360].replace("\n", " ")
    lower = narration.lower()
    characters = []
    if "l\u00e2m t\u1ecbch" in lower:
        characters.append(LAM_TICH_VISUAL)
    if "t\u1ea7n d\u00e3" in lower or "ng\u01b0\u1eddi \u0111\u00e0n \u00f4ng" in lower or "l\u00ednh \u0111\u00e1nh thu\u00ea" in lower:
        characters.append(TAN_DA_VISUAL)
    character_line = ", ".join(characters) if characters else "a lone survivor in torn wasteland clothes, small human silhouette against a hostile world"

    visual = "wide cinematic survival scene in a radioactive wasteland, red dusty sky, ruined vehicles, polluted haze"
    if has_any(lower, ["ch\u00f3", "th\u00fa", "bi\u1ebfn d\u1ecb", "g\u1ea7m g\u1eeb", "m\u00f3ng vu\u1ed1t"]):
        visual = "tense predator encounter, mutated scavenger dogs threatening near an overturned truck, survivor hiding behind concrete"
    elif has_any(lower, ["b\u00e3i r\u00e1c", "\u0111\u1ed1ng r\u00e1c", "t\u1ee7 l\u1ea1nh", "t\u00fai nh\u1ef1a", "nh\u1eb7t r\u00e1c"]):
        visual = "scroll-stopping wasteland junkyard scene, rusted refrigerator, dead plastic bags, broken metal sheets, toxic red sky pressing down"
    elif has_any(lower, ["m\u01b0a", "m\u01b0a \u0111en", "m\u01b0a \u0111\u1ed9c"]):
        visual = "black toxic rain falling over ruined streets, wet reflective ground, corroded metal, survivor hiding under broken concrete"
    elif has_any(lower, ["ph\u1ebf th\u1ed5", "nhi\u1ec5m x\u1ea1", "\u0111\u1ea1i nhi\u1ec5m x\u1ea1", "\u00f4 nhi\u1ec5m", "b\u1ea7u tr\u1eddi \u0111\u1ecf"]):
        visual = "radioactive wasteland after a great contamination disaster, crimson polluted sky, ash wind, distant dead city edge"
    elif has_any(lower, ["t\u01b0\u1eddng", "th\u00e0nh", "c\u1ed5ng th\u00e0nh", "v\u00e0o th\u00e0nh"]):
        visual = "massive safe-zone wall far beyond a polluted wasteland, tiny survivor looking toward unreachable clean city lights"
    elif has_any(lower, ["th\u1ecbt h\u1ed9p", "\u0111\u1ed3 \u0103n", "b\u00e1nh", "k\u1eb9o", "n\u01b0\u1edbc s\u1ea1ch", "tinh th\u1ea1ch"]):
        visual = "close survival-detail shot, dirty hands reaching toward a precious can of meat and a tiny crystal among dust and ash"
    elif has_any(lower, ["m\u00e1u", "v\u1ebft th\u01b0\u01a1ng", "dao", "b\u0103ng", "gen s\u1ee5p \u0111\u1ed5"]):
        visual = "dark medical survival moment, injured mercenary with dirty bandages and torn tactical coat, scavenger holding a knife under harsh rim light"
    elif has_any(lower, ["g\u1ea7m xe", "c\u00f2i", "ba h\u01a1i", "m\u1ed9t h\u01a1i d\u00e0i"]):
        visual = "claustrophobic shot under an overturned truck, survivors pressed into mud while mutant claws scrape just outside"
    elif has_any(lower, ["xuy\u00ean kh\u00f4ng", "ch\u1ebft", "m\u1edf m\u1eaft", "k\u00fd \u1ee9c"]):
        visual = "surreal awakening after death in a wasteland junkyard, weak survivor lying among rust and ash, red sky reflected in frightened eyes"

    youtube_vibe = (
        "make it feel like a high-retention YouTube apocalypse story thumbnail but still cinematic, "
        "clear readable stakes in the first glance, emotional lonely survival vibe, not a clean wallpaper, "
        "not a random landscape, dramatic face mostly hidden or side angle, realistic Chinese/Vietnamese webnovel atmosphere"
    )
    return f"{visual}, {character_line}, {style}, {youtube_vibe}. Scene context: {compact}"


def add_unique(items, value):
    if value and value not in items:
        items.append(value)


def shot_type_for(narration, scene_index):
    lower = narration.lower()
    plain = normalize_vi(narration)
    if has_any(plain, ["dua nap hop", "ben moi", "hai ngum", "nhuong nuoc", "nhin hai ngum nuoc"]):
        return "approved reference medium two-shot: girl on left, wounded man reclining on right, lantern between them, faces readable"
    if scene_index == 1 or has_any(lower, ["bầu trời", "xa xa", "bức tường khổng lồ", "thành an toàn"]):
        return "wide establishing shot showing place and scale"
    if has_any(lower, ["thịt hộp", "kẹo", "tinh thạch", "còi", "dao", "than lọc", "vết thương"]):
        return "close survival-detail shot focused on hands, props, and immediate stakes"
    if has_any(lower, ["gầm xe", "trốn", "nín thở"]):
        return "low claustrophobic point-of-view shot from cover"
    if has_any(lower, ["chó", "thú", "gầm gừ", "móng vuốt", "xác"]):
        return "medium tense action shot with predator, victim, and survivor positions readable"
    return "medium cinematic story shot with clear blocking"


def visual_prompt_data(narration, style, continuity=None, scene_index=1):
    continuity = continuity or {}
    compact = narration[:420].replace("\n", " ")
    lower = narration.lower()
    plain = normalize_vi(narration)
    characters = []
    setting = []
    props = []
    actions = []
    mood = []
    shot_type = shot_type_for(narration, scene_index)

    if "lâm tịch" in lower or "nàng" in lower or "cô" in lower:
        add_unique(characters, LAM_TICH_VISUAL)
    if "tần dã" in lower or "hắn" in lower:
        add_unique(characters, TAN_DA_VISUAL)
    elif "người đàn ông" in lower or "lính đánh thuê" in lower:
        add_unique(characters, TAN_DA_VISUAL)
    # Accent-safe story anchors. These keep chapter 2 from drifting into generic
    # apocalypse wallpaper when the source text is proper UTF-8 Vietnamese.
    if "lam tich" in plain or "nang" in plain or "co" in plain:
        characters = [
            item for item in characters
            if "exact survivor" not in item.lower() and "lone survivor" not in item.lower()
        ]
        add_unique(
            characters,
            LAM_TICH_VISUAL,
        )
    if "tan da" in plain or "nguoi dan ong" in plain or "linh danh thue" in plain or "han" in plain:
        add_unique(
            characters,
            TAN_DA_VISUAL,
        )
    if not characters:
        continuity_text = " ".join(continuity.get("anchors", []))
        if "Lam Tich" in continuity_text:
            add_unique(characters, LAM_TICH_VISUAL)
        if "Tan Da" in continuity_text:
            add_unique(characters, TAN_DA_VISUAL)
    if not characters:
        add_unique(characters, "the exact survivor or person described in the narration, shown from side or back view")

    keyword_rules = [
        (["bãi rác", "đống rác", "nhặt rác"], setting, "radioactive junkyard outside the city"),
        (["tủ lạnh"], props, "rusted half-broken refrigerator"),
        (["túi nhựa"], props, "hardened dead plastic bags like old skin"),
        (["bầu trời đỏ", "trời màu đỏ"], setting, "heavy polluted crimson red sky"),
        (["phế thổ", "đại nhiễm xạ", "nhiễm xạ", "ô nhiễm"], setting, "contaminated post-apocalyptic wasteland"),
        (["mưa đen", "mưa độc"], setting, "black toxic rain residue and corroded wet surfaces"),
        (["bức tường khổng lồ", "thành an toàn", "vào thành", "cổng thành", "sau bức tường là thành"], setting, "distant massive safe-zone wall beyond the wasteland"),
        (["chó hai hàm", "chó", "thú biến dị", "biến dị", "gầm gừ", "móng vuốt"], actions, "mutated two-jawed dogs threatening the scene"),
        (["xác", "người chết"], props, "ominous covered body-shaped bundle on the ground"),
        (["xe tải lật"], props, "overturned truck beside the corpse"),
        (["bức tường bê tông", "tường bê tông"], props, "collapsed concrete wall used as cover"),
        (["gầm xe"], actions, "survivors hiding under the vehicle"),
        (["còi"], props, "small metal whistle"),
        (["thịt hộp"], props, "precious sealed can of meat"),
        (["bánh nén", "bánh"], props, "compressed ration biscuit"),
        (["kẹo"], props, "small unwrapped candy"),
        (["tinh thạch"], props, "tiny crystal shard"),
        (["dao"], props, "survival knife in a dirty hand"),
        (["máu đen", "máu"], props, "dark stains on dirty cloth"),
        (["vết thương"], actions, "close survival treatment of a serious wound"),
        (["gen sụp đổ"], mood, "tense radiation sickness atmosphere"),
        (["nước", "lon rỉ"], props, "rusty water can and unsafe scavenged water"),
        (["than lọc"], props, "used poison-filtering charcoal"),
        (["sợ", "nín thở", "run"], mood, "breathless fear and survival tension"),
        (["im lặng", "một ngày", "sống thêm"], mood, "quiet lonely survival melancholy"),
    ]
    for words, target, phrase in keyword_rules:
        if has_any(lower, words):
            add_unique(target, phrase)

    ascii_keyword_rules = [
        (["leu", "goc leu", "cua leu", "day dong"], setting, "inside a poor wasteland tarp shelter made from torn canvas, copper wire, rusted poles, patched plastic sheets"),
        (["khu 17"], setting, "District 17 wasteland outside the safe city, dirty scrap tents and ruined industrial silhouettes"),
        (["nap hop", "hai ngum", "nuoc", "nuoc sach"], props, "small metal can lid holding the last two sips of yellowish filtered water"),
        (["vang nhat", "bui than", "mui ri sat", "than loc"], props, "murky yellow water with charcoal dust and rusty metallic residue"),
        (["tan da nam", "nguoi han nong", "khong the nhuc nhich", "nua than duoi"], actions, "Tan Da lying in the shelter corner, feverish and unable to move his lower body"),
        (["vet thuong bung", "mau van tham", "duong tim xanh", "gen sup do"], actions, "injured abdomen wrapped in dirty cloth, dark stains visible on fabric, blue-purple radiation sickness lines under the skin"),
        (["dua nap hop", "ben moi", "uong"], actions, "Lam Tich carefully raising the metal can lid to Tan Da's lips"),
        (["con lai co uong", "nhuong nuoc"], actions, "tense intimate survival moment as the wounded man leaves the last water for the girl"),
        (["mat do", "bui", "khong khoc"], mood, "suppressed emotion, red dusty eyes, refusing to admit weakness"),
        (["tieng buoc chan", "ba nguoi", "ngoai cua leu"], actions, "three threatening footsteps outside the shelter entrance"),
        (["cam dao", "con dao gay", "luoi mo"], props, "broken survival knife gripped tightly in Lam Tich's dirty hand"),
    ]
    for words, target, phrase in ascii_keyword_rules:
        if has_any(plain, words):
            add_unique(target, phrase)

    if has_any(lower, ["mở mắt", "tỉnh lại", "xuyên không", "chết một lần"]):
        add_unique(actions, "surreal awakening after death, weak body lying among rust and ash")
    if has_any(lower, ["lục", "túi", "chạm vào", "rút"]):
        add_unique(actions, "dirty hands searching a pocket for survival supplies")
    if has_any(lower, ["kéo", "bò", "trốn"]):
        add_unique(actions, "desperate crawling and hiding from danger")
    if has_any(lower, ["nhìn", "xa xa"]):
        add_unique(actions, "small survivor looking toward something unreachable in the distance")

    if not setting:
        add_unique(setting, "hostile radioactive wasteland environment matching the narration")
    if not actions:
        add_unique(actions, "the exact action described in the narration, not a generic pose")
    if not mood:
        add_unique(mood, "tense cinematic survival mood")

    must_show = []
    for source in (characters, setting, actions, props):
        for item in source:
            add_unique(must_show, item)
    must_show = must_show[:9]

    reference_recipe = (
        REFERENCE_IMAGE_RECIPE
        if "two-shot" in shot_type or "medium cinematic story shot" in shot_type or scene_index == 1
        else "Use the approved sample only as character identity and material-language reference, not as a fixed repeated composition"
    )
    shot_composition_rule = (
        "For emotional survival beats, use the approved reference medium two-shot: Lam Tich left, Tan Da reclining right, lantern centered, dirty props in foreground, wasteland depth behind. "
        if "two-shot" in shot_type or "medium cinematic story shot" in shot_type
        else "Vary camera framing according to the shot type and action, and do not repeat the same two-character shelter composition when the scene is a close detail, wide establishing view, or action beat. "
    )

    prompt = (
        "Premium cinematic realistic wasteland story frame with clear natural human faces and readable story blocking. "
        "Visual benchmark: gritty cinematic survival frame like a high-budget wasteland film still, beautiful but grimy scavenger girl beside injured righteous black-clad man inside a torn tarp shelter, oil lantern glow, rusted barrels, muddy floor, ruined industrial wasteland visible outside when relevant. "
        f"{reference_recipe}. "
        "Prioritize story accuracy, body language, dirty props, readable interaction, consistent faces, and clear facial identity over generic wallpaper. "
        "Faces must be close enough to read: natural eyes, natural nose, natural mouth, no melted features, no warped anatomy. "
        f"CONTINUITY FROM PREVIOUS SCENE: {continuity.get('summary', 'start of sequence')}. "
        f"MUST SHOW: {', '.join(must_show)}. "
        f"Characters: {', '.join(characters)}. "
        f"Setting: {', '.join(setting)}. "
        f"Shot type: {shot_type}. "
        f"Action: {', '.join(actions)}. "
        f"Previous action handoff: {continuity.get('last_action', 'none')}. "
        f"Persistent visual anchors: {', '.join(continuity.get('anchors', [])[:6]) if continuity.get('anchors') else 'keep character design and world style consistent'}. "
        f"Important props: {', '.join(props) if props else 'only props described by the narration'}. "
        f"Mood: {', '.join(mood)}. "
        "Composition must make the story action readable at first glance, with foreground story objects, midground characters, and background world context. "
        f"{shot_composition_rule}"
        "When both Lam Tich and Tan Da are in the scene, keep their body positions consistent with the reference; do not make Tan Da stand, do not crop heads or hide faces. "
        "Use grounded Asian webnovel casting, natural faces, dirty damaged clothes, readable faces when characters are visible, no idol makeup, no clean fantasy armor. "
        "Lam Tich should have a beautiful youthful maiden face, soft and memorable, but must remain weak, hungry, dirty, and believable in the wasteland. "
        "Tan Da must not look like a faceless villain; show a clearer righteous protective expression whenever his face appears. "
        "Keep spatial logic from the previous scene unless the narration clearly changes location. "
        "Avoid unrelated cabins, clean modern streets, fantasy armor, random portraits, extra characters, or objects not implied by the narration. "
        f"{style}. Scene context: {compact}"
    )
    return {
        "prompt": prompt,
        "must_show": must_show,
        "setting": setting,
        "actions": actions,
        "props": props,
        "shot_type": shot_type,
    }


def update_visual_continuity(previous, visual):
    anchors = list(previous.get("anchors") or [])
    for key in ("must_show", "setting", "props"):
        for item in visual.get(key) or []:
            if any(token in item.lower() for token in ["lam tich", "tan da", "junkyard", "crimson red sky", "overturned truck", "concrete wall", "safe-zone wall", "can of meat"]):
                add_unique(anchors, item)
    anchors = anchors[-8:]
    last_action = ", ".join((visual.get("actions") or [])[:2]) or previous.get("last_action", "none")
    summary_parts = []
    if anchors:
        summary_parts.append("anchors: " + ", ".join(anchors[:5]))
    if last_action:
        summary_parts.append("last action: " + last_action)
    return {
        "anchors": anchors,
        "last_action": last_action,
        "summary": "; ".join(summary_parts) if summary_parts else "continue same story world and character identity",
    }


def build_storyboard(args):
    source = args.source.resolve()
    text = read_source(source)
    project = args.project.resolve() if args.project else Path(args.root).resolve() / slugify(args.title or source.stem)
    assets = project / "assets"
    output = project / "output"
    assets.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    (project / "source.txt").write_text(text, encoding="utf-8")

    groups, word_count = group_for_scenes(text, args.min_scenes, args.max_scenes, args.words_per_image)
    style = args.style or BASE_STYLE
    scenes = []
    continuity = {"summary": "start of the story sequence", "anchors": [], "last_action": "none"}
    for index, narration in enumerate(groups, 1):
        visual = visual_prompt_data(narration, style, continuity, index)
        current_continuity = dict(continuity)
        scenes.append(
            {
                "id": f"scene-{index:03d}",
                "duration": 12,
                "image": f"assets/scene-{index:03d}.png",
                "audio": f"assets/scene-{index:03d}.mp3",
                "narration": narration,
                "subtitle": narration if args.subtitles else "",
                "text": args.title if index == 1 and args.title_overlay else "",
                "image_prompt": visual["prompt"],
                "visual_must_show": visual["must_show"],
                "visual_setting": visual["setting"],
                "visual_action": visual["actions"],
                "visual_props": visual["props"],
                "visual_shot_type": visual["shot_type"],
                "visual_continuity": current_continuity,
                "negative_prompt": DEFAULT_NEGATIVE,
            }
        )
        continuity = update_visual_continuity(continuity, visual)

    config = {
        "title": args.title or source.stem,
        "language": args.language,
        "font": "Arial",
        "word_count": word_count,
        "words_per_image_target": args.words_per_image,
        "visual_continuity_version": 1,
        "scenes": scenes,
        "music": None,
    }
    apply_video_format(config, args.format)
    storyboard = project / "storyboard.json"
    storyboard.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return project, storyboard, config


def detect_scene_state(narration, continuity=None):
    continuity = continuity or {}
    plain = normalize_vi(narration)
    state = {
        "location": continuity.get("location", "inside the tarp shelter"),
        "focus": "interaction",
        "threat": continuity.get("threat", "low"),
        "lam_tich_position": continuity.get("lam_tich_position", "near the lantern inside the shelter"),
        "tan_da_position": continuity.get("tan_da_position", "lying in the shelter corner"),
        "door_state": continuity.get("door_state", "closed with torn cloth and wire"),
        "prop_focus": [],
    }
    if has_any(plain, ["ngoai cua leu", "qua khe ton", "bong nguoi", "hau seo", "tieng buoc chan"]):
        state["location"] = "at the shelter doorway with outside shadows pressing close"
        state["focus"] = "doorway-threat"
        state["threat"] = "high"
        state["lam_tich_position"] = "standing between the doorway and Tan Da"
    elif has_any(plain, ["nap hop", "hai ngum", "vang nhat", "bui than", "than loc", "mui ri sat"]):
        state["location"] = "inside the shelter around the last dirty water"
        state["focus"] = "water-detail"
        state["prop_focus"] = ["dirty water", "metal lid", "charcoal dust", "dirty cloth filter"]
    elif has_any(plain, ["nguoi han nong", "sot", "gen sup do", "vet thuong bung", "nua than duoi"]):
        state["location"] = "inside the shelter near Tan Da's sickbed corner"
        state["focus"] = "tan-da-condition"
        state["threat"] = "internal"
    elif has_any(plain, ["keo thung", "dap nghieng", "tro xam", "nam do"]):
        state["location"] = "at the shelter entrance while ash spills outside"
        state["focus"] = "ash-bluff"
        state["threat"] = "high"
        state["door_state"] = "partly opened to spill ash through the metal gap"
    elif has_any(plain, ["di xa", "van khong dong", "quay dau", "ngoi xuong canh han"]):
        state["location"] = "inside the shelter after the threat recedes"
        state["focus"] = "aftermath"
        state["threat"] = "medium"

    if has_any(plain, ["cam dao", "con dao gay", "luoi mo"]):
        add_unique(state["prop_focus"], "broken knife hidden in Lam Tich's hand")
    if has_any(plain, ["cai coi den", "cai coi", "coi den"]):
        add_unique(state["prop_focus"], "small dark whistle")
    return state


def shot_type_for(narration, scene_index):
    lower = narration.lower()
    plain = normalize_vi(narration)
    if has_any(plain, ["nap hop", "hai ngum", "vang nhat", "bui than", "than loc", "mui ri sat"]):
        return "close insert shot on water, metal lid, dirty cloth filter, and trembling hands"
    if has_any(plain, ["nguoi han nong", "sot", "gen sup do", "vet thuong bung", "nua than duoi"]):
        return "medium single on Tan Da in the shelter corner with illness and wound clearly readable"
    if has_any(plain, ["dua nap hop", "ben moi", "uong", "con lai co uong", "nhuong nuoc"]):
        return "intimate medium two-shot focused on the exchange of water between Lam Tich and Tan Da"
    if has_any(plain, ["ngoai cua leu", "qua khe ton", "bong nguoi", "hau seo", "tieng buoc chan", "mo cua"]):
        return "doorway tension shot with Lam Tich inside and threatening silhouettes outside"
    if has_any(plain, ["keo thung", "dap nghieng", "tro xam", "nam do"]):
        return "action shot at the shelter entrance as ash spills outward and everyone reacts"
    if has_any(plain, ["di xa", "quay dau", "ngoi xuong canh han", "dem nay ta co the sot lan hai"]):
        return "quiet aftermath two-shot inside the shelter with danger lingering after the footsteps leave"
    if scene_index == 1 or has_any(lower, ["báº§u trá»i", "xa xa", "bá»©c tÆ°á»ng khá»•ng lá»“", "thÃ nh an toÃ n"]):
        return "wide establishing shot showing place and scale"
    if has_any(lower, ["thá»‹t há»™p", "káº¹o", "tinh tháº¡ch", "cÃ²i", "dao", "than lá»c", "váº¿t thÆ°Æ¡ng"]):
        return "close survival-detail shot focused on hands, props, and immediate stakes"
    if has_any(lower, ["gáº§m xe", "trá»‘n", "nÃ­n thá»Ÿ"]):
        return "low claustrophobic point-of-view shot from cover"
    if has_any(lower, ["chÃ³", "thÃº", "gáº§m gá»«", "mÃ³ng vuá»‘t", "xÃ¡c"]):
        return "medium tense action shot with predator, victim, and survivor positions readable"
    return "medium cinematic story shot with clear blocking"


def visual_prompt_data(narration, style, continuity=None, scene_index=1):
    continuity = continuity or {}
    compact = narration[:420].replace("\n", " ")
    lower = narration.lower()
    plain = normalize_vi(narration)
    characters = []
    setting = []
    props = []
    actions = []
    mood = []
    shot_type = shot_type_for(narration, scene_index)
    scene_state = detect_scene_state(narration, continuity)

    if "lam tich" in plain:
        add_unique(characters, LAM_TICH_VISUAL)
    if "tan da" in plain or "nguoi dan ong" in plain or "linh danh thue" in plain:
        add_unique(characters, TAN_DA_VISUAL)
    if not characters:
        continuity_text = " ".join(continuity.get("anchors", []))
        if "Lam Tich" in continuity_text:
            add_unique(characters, LAM_TICH_VISUAL)
        if "Tan Da" in continuity_text:
            add_unique(characters, TAN_DA_VISUAL)
    if not characters:
        add_unique(characters, "the exact survivor or person described in the narration, shown from side or back view")

    add_unique(setting, scene_state["location"])
    add_unique(setting, "District 17 wasteland survival setting")

    keyword_rules = [
        (["khu 17"], setting, "District 17 wasteland outside the safe city, dirty scrap tents and ruined industrial silhouettes"),
        (["nuoc", "nap hop"], props, "small metal can lid holding the last two sips of yellowish filtered water"),
        (["vang nhat", "bui than", "mui ri sat", "than loc"], props, "murky yellow water with charcoal dust and rusty metallic residue"),
        (["vet thuong bung", "mau van tham", "gen sup do"], props, "dirty abdominal bandage with dark stains and faint toxic veins under the skin"),
        (["tieng buoc chan", "bong nguoi", "hau seo"], props, "door gap, torn cloth curtain, and hostile silhouettes outside"),
        (["keo thung", "tro xam", "nam do"], props, "rusted ash bucket filled with stove ash and bone dust"),
        (["cam dao", "con dao gay"], props, "broken survival knife hidden in Lam Tich's hand"),
        (["coi den", "cai coi"], props, "small dark whistle"),
    ]
    for words, target, phrase in keyword_rules:
        if has_any(plain, words):
            add_unique(target, phrase)

    focus = scene_state["focus"]
    if focus == "water-detail":
        characters = [LAM_TICH_VISUAL]
        actions = ["Lam Tich studies the last two sips of dirty water and the charcoal residue in the lid"]
        mood = ["thirst, hesitation, and fragile survival calculation"]
    elif focus == "tan-da-condition":
        add_unique(characters, TAN_DA_VISUAL)
        actions = ["Tan Da lies feverish in the corner while Lam Tich watches his condition and the bleeding cloth"]
        mood = ["fever, weakness, and dread of gene collapse"]
    elif focus == "doorway-threat":
        add_unique(characters, LAM_TICH_VISUAL)
        actions = ["Lam Tich listens at the door, watches silhouettes through the torn metal gap, and prepares to defend the shelter"]
        mood = ["immediate danger at the shelter entrance"]
    elif focus == "ash-bluff":
        add_unique(characters, LAM_TICH_VISUAL)
        actions = ["Lam Tich drags the ash bucket to the entrance and kicks it so gray ash pours through the gap toward the men outside"]
        mood = ["desperate bluff using fear of red fungus"]
    elif focus == "aftermath":
        add_unique(characters, LAM_TICH_VISUAL)
        add_unique(characters, TAN_DA_VISUAL)
        actions = ["after the footsteps leave, Lam Tich sits back beside Tan Da and the two measure the next danger together"]
        mood = ["short-lived relief with dread still hanging in the shelter"]
    else:
        if has_any(plain, ["dua nap hop", "ben moi", "uong", "nhuong nuoc"]):
            actions = ["Lam Tich raises the metal lid to Tan Da's lips and the two share the last water carefully"]
            mood = ["intimate survival trust under exhaustion"]
        elif has_any(plain, ["quay dau", "nhin han", "hoi"]):
            actions = ["the exact action described in the narration, with character positions inherited from the previous scene"]
        else:
            actions = ["the exact action described in the narration, with character positions inherited from the previous scene"]
        mood = mood or ["tense cinematic survival mood"]

    for prop in scene_state.get("prop_focus", []):
        add_unique(props, prop)

    must_show = []
    for source in (characters, setting, actions, props):
        for item in source:
            add_unique(must_show, item)
    must_show = must_show[:8]

    reference_recipe = (
        REFERENCE_IMAGE_RECIPE
        if "two-shot" in shot_type or scene_index == 1
        else "Use the approved sample only as character identity, face quality, clothing language, and shelter material reference, not as a fixed repeated composition"
    )
    prompt = (
        "Premium cinematic realistic wasteland story frame with strong story accuracy and scene-to-scene continuity. "
        f"{reference_recipe}. "
        "Do not turn every scene into the same two-character shelter shot. "
        "The frame must illustrate the exact beat being narrated right now. "
        f"CONTINUITY FROM PREVIOUS SCENE: {continuity.get('summary', 'start of sequence')}. "
        f"Current scene state: location={scene_state['location']}; threat={scene_state['threat']}; Lam Tich position={scene_state['lam_tich_position']}; Tan Da position={scene_state['tan_da_position']}; door state={scene_state['door_state']}. "
        f"MUST SHOW: {', '.join(must_show)}. "
        f"Characters: {', '.join(characters)}. "
        f"Setting: {', '.join(setting)}. "
        f"Shot type: {shot_type}. "
        f"Action: {', '.join(actions)}. "
        f"Previous action handoff: {continuity.get('last_action', 'none')}. "
        f"Persistent visual anchors: {', '.join(continuity.get('anchors', [])[:6]) if continuity.get('anchors') else 'keep character design and world style consistent'}. "
        f"Important props: {', '.join(props) if props else 'only props described by the narration'}. "
        f"Mood: {', '.join(mood)}. "
        "Use grounded Asian webnovel casting, realistic dirty survival clothing, readable faces only when the story beat needs the face visible, and keep spatial logic consistent from one scene to the next. "
        "Prefer insert shots for objects, doorway shots for outside threats, single shots for illness, and two-shots only when the relationship beat is the real focus. "
        f"{style}. Scene context: {compact}"
    )
    return {
        "prompt": prompt,
        "must_show": must_show,
        "setting": setting,
        "actions": actions,
        "props": props,
        "shot_type": shot_type,
        "scene_state": scene_state,
    }


def update_visual_continuity(previous, visual):
    anchors = list(previous.get("anchors") or [])
    for key in ("must_show", "setting", "props"):
        for item in visual.get(key) or []:
            if any(token in item.lower() for token in ["lam tich", "tan da", "shelter", "water", "knife", "whistle", "ash bucket", "door gap"]):
                add_unique(anchors, item)
    anchors = anchors[-8:]
    last_action = ", ".join((visual.get("actions") or [])[:2]) or previous.get("last_action", "none")
    scene_state = visual.get("scene_state") or {}
    summary_parts = []
    if anchors:
        summary_parts.append("anchors: " + ", ".join(anchors[:5]))
    if last_action:
        summary_parts.append("last action: " + last_action)
    if scene_state.get("location"):
        summary_parts.append("location: " + scene_state["location"])
    return {
        "anchors": anchors,
        "last_action": last_action,
        "location": scene_state.get("location", previous.get("location", "inside the shelter")),
        "threat": scene_state.get("threat", previous.get("threat", "low")),
        "lam_tich_position": scene_state.get("lam_tich_position", previous.get("lam_tich_position", "near the lantern inside the shelter")),
        "tan_da_position": scene_state.get("tan_da_position", previous.get("tan_da_position", "lying in the shelter corner")),
        "door_state": scene_state.get("door_state", previous.get("door_state", "closed with torn cloth and wire")),
        "summary": "; ".join(summary_parts) if summary_parts else "continue same story world and character identity",
    }


def build_storyboard(args):
    source = args.source.resolve()
    text = read_source(source)
    project = args.project.resolve() if args.project else Path(args.root).resolve() / slugify(args.title or source.stem)
    assets = project / "assets"
    output = project / "output"
    assets.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    (project / "source.txt").write_text(text, encoding="utf-8")

    groups, word_count = group_for_scenes(text, args.min_scenes, args.max_scenes, args.words_per_image)
    style = args.style or BASE_STYLE
    scenes = []
    continuity = {
        "summary": "start of the story sequence",
        "anchors": [],
        "last_action": "none",
        "location": "inside the tarp shelter",
        "threat": "low",
        "lam_tich_position": "near the lantern inside the shelter",
        "tan_da_position": "lying in the shelter corner",
        "door_state": "closed with torn cloth and wire",
    }
    for index, narration in enumerate(groups, 1):
        visual = visual_prompt_data(narration, style, continuity, index)
        current_continuity = dict(continuity)
        scenes.append(
            {
                "id": f"scene-{index:03d}",
                "duration": 12,
                "image": f"assets/scene-{index:03d}.png",
                "audio": f"assets/scene-{index:03d}.mp3",
                "narration": narration,
                "subtitle": narration if args.subtitles else "",
                "text": args.title if index == 1 and args.title_overlay else "",
                "image_prompt": visual["prompt"],
                "visual_must_show": visual["must_show"],
                "visual_setting": visual["setting"],
                "visual_action": visual["actions"],
                "visual_props": visual["props"],
                "visual_shot_type": visual["shot_type"],
                "visual_continuity": current_continuity,
                "negative_prompt": DEFAULT_NEGATIVE,
            }
        )
        continuity = update_visual_continuity(continuity, visual)

    config = {
        "title": args.title or source.stem,
        "language": args.language,
        "font": "Arial",
        "word_count": word_count,
        "words_per_image_target": args.words_per_image,
        "visual_continuity_version": 2,
        "scenes": scenes,
        "music": None,
    }
    apply_video_format(config, args.format)
    storyboard = project / "storyboard.json"
    storyboard.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return project, storyboard, config


def count_assets(storyboard, key):
    base = storyboard.parent
    config = json.loads(storyboard.read_text(encoding="utf-8-sig"))
    count = 0
    for scene in config.get("scenes") or []:
        value = scene.get(key)
        if value and resolve(base, value).exists():
            count += 1
    return count, len(config.get("scenes") or [])


def missing_manual_images(storyboard):
    base = storyboard.parent
    config = json.loads(storyboard.read_text(encoding="utf-8-sig"))
    missing = []
    for index, scene in enumerate(config.get("scenes") or [], start=1):
        if scene.get("image_provider") != "manual-chatgpt":
            continue
        image = scene.get("image") or scene.get("manual_image_expected")
        path = Path(image)
        if not path.is_absolute():
            path = base / path
        if not path.exists():
            missing.append({"scene": index, "path": str(path)})
    return missing


def probe_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def sync_durations(storyboard, pad):
    base = storyboard.parent
    config = json.loads(storyboard.read_text(encoding="utf-8-sig"))
    for scene in config.get("scenes") or []:
        audio = scene.get("audio")
        if not audio:
            continue
        duration = probe_duration(resolve(base, audio))
        if duration:
            scene["duration"] = round(duration + pad, 2)
            scene["audio_duration"] = round(duration, 2)
    storyboard.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def write_contact_sheet(project, storyboard):
    config = json.loads(storyboard.read_text(encoding="utf-8-sig"))
    cards = []
    for index, scene in enumerate(config.get("scenes") or [], 1):
        image = html.escape(scene.get("image") or "")
        text = html.escape((scene.get("narration") or "")[:180])
        must = html.escape(", ".join(scene.get("visual_must_show") or [])[:220])
        cards.append(f"<figure><img src='{image}'><figcaption><b>{index:03d}</b>. {text}<br><span>{must}</span></figcaption></figure>")
    page = """<!doctype html>
<meta charset="utf-8">
<title>Contact Sheet</title>
<style>
body{font-family:Arial,sans-serif;background:#111;color:#eee;margin:24px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}
figure{margin:0;background:#1c1c1c;padding:10px;border-radius:6px}
img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}
figcaption{font-size:12px;line-height:1.35;margin-top:8px;color:#ccc}
figcaption span{display:block;margin-top:6px;color:#8fd0ff}
</style>
<div class="grid">""" + "\n".join(cards) + "</div>"
    path = project / "contact-sheet.html"
    path.write_text(page, encoding="utf-8")
    return path


def maybe_start_comfy(args):
    if not args.start_comfy:
        return
    try:
        subprocess.run(["powershell", "-Command", "Invoke-WebRequest -Uri 'http://127.0.0.1:8188/object_info' -UseBasicParsing -TimeoutSec 3"], check=True, capture_output=True)
        return
    except Exception:
        pass
    comfy_root = Path(args.comfy_root)
    python = comfy_root / "python_embeded" / "python.exe"
    main = comfy_root / "ComfyUI" / "main.py"
    log_dir = Path(args.root) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    out = open(log_dir / "comfyui-pipeline-out.log", "w", encoding="utf-8")
    err = open(log_dir / "comfyui-pipeline-err.log", "w", encoding="utf-8")
    creationflags = 0
    if sys.platform == "win32" and (args.run_mode == "work" or args.gentle_mode):
        creationflags = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
    subprocess.Popen(
        [str(python), "-s", str(main), "--windows-standalone-build", "--lowvram"],
        cwd=str(comfy_root),
        stdout=out,
        stderr=err,
        creationflags=creationflags,
    )
    for _ in range(36):
        time.sleep(5)
        try:
            subprocess.run(["powershell", "-Command", "Invoke-WebRequest -Uri 'http://127.0.0.1:8188/object_info' -UseBasicParsing -TimeoutSec 3"], check=True, capture_output=True)
            return
        except Exception:
            pass
    raise SystemExit("ComfyUI did not start on http://127.0.0.1:8188")


def main():
    parser = argparse.ArgumentParser(description="Run the local story-video pipeline with resumable image/audio stages.")
    parser.add_argument("--source", required=True, type=Path, help="UTF-8 story text file.")
    parser.add_argument("--title", default="")
    parser.add_argument("--project", type=Path)
    parser.add_argument("--root", default=r"E:\ThanhMV\video-projects")
    parser.add_argument("--format", choices=["youtube", "tiktok"], default="youtube")
    parser.add_argument("--language", default="vi")
    parser.add_argument("--voice", default="vi-female")
    parser.add_argument("--voice-style", choices=["plain", "story-emotional", "wasteland-dark"], default="wasteland-dark")
    parser.add_argument("--character-bible", type=Path, help="Optional JSON file with persistent character voice traits.")
    parser.add_argument("--words-per-image", type=int, default=32)
    parser.add_argument("--min-scenes", type=int, default=50)
    parser.add_argument("--max-scenes", type=int, default=90)
    parser.add_argument("--batch-size", type=int, default=5)
    parser.add_argument("--image-preset", choices=["safe", "balanced", "quality"], default="balanced")
    parser.add_argument("--image-reference", default="", help="Optional local reference image for ComfyUI img2img composition lock.")
    parser.add_argument("--image-reference-denoise", type=float, default=0.28)
    parser.add_argument("--image-mode", choices=["comfy", "hybrid-manual"], default="comfy")
    parser.add_argument("--manual-image-ratio", type=float, default=0.5, help="For hybrid-manual, fraction of scenes assigned to ChatGPT manual images.")
    parser.add_argument("--import-manual-images", action="store_true", help="Attach existing manual ChatGPT images before validation/render.")
    parser.add_argument("--wait-for-manual-images", action="store_true", help="Stop after preparing prompts if manual images are still missing.")
    parser.add_argument(
        "--run-mode",
        choices=["work", "overnight"],
        default="overnight",
        help="work = lighter background generation; overnight = faster batch generation.",
    )
    parser.add_argument("--gentle-mode", action="store_true", help="Run image generation more politely for 2GB VRAM machines.")
    parser.add_argument("--image-delay", type=float, default=0.0, help="Seconds to pause between image batches.")
    parser.add_argument("--image-priority", choices=["normal", "below-normal", "idle"], default="normal")
    parser.add_argument("--style", default="")
    parser.add_argument("--subtitles", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--title-overlay", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--duration-pad", type=float, default=0.35)
    parser.add_argument("--start-comfy", action="store_true")
    parser.add_argument("--comfy-root", default=r"E:\ThanhMV\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable")
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--skip-voice", action="store_true")
    parser.add_argument("--skip-sfx", action="store_true", help="Skip subtle story-aware sound effects under narration.")
    parser.add_argument("--sfx-volume", type=float, default=0.45, help="SFX mix volume after cleanup. Try 0.35-0.65.")
    parser.add_argument("--skip-render", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.run_mode == "work" or args.gentle_mode:
        args.batch_size = 1
        if args.image_delay <= 0:
            args.image_delay = 8
        if args.image_priority == "normal":
            args.image_priority = "below-normal"
    elif args.run_mode == "overnight":
        if args.batch_size == 1:
            args.batch_size = 5
        if args.image_delay <= 0:
            args.image_delay = 0
        if args.image_priority == "normal":
            args.image_priority = "normal"

    preset = preset_for(args.format)
    project, storyboard, config = build_storyboard(args)
    env = dict(os.environ)
    env["TEMP"] = str(Path(args.root).resolve().parent / "temp") if "video-projects" in args.root else r"E:\ThanhMV\temp"
    env["TMP"] = env["TEMP"]
    Path(env["TEMP"]).mkdir(parents=True, exist_ok=True)

    scripts = Path(__file__).resolve().parent
    run([sys.executable, str(scripts / "validate_storyboard.py"), "--storyboard", str(storyboard), "--stage", "text"], env=env)

    if args.image_mode == "hybrid-manual":
        manual_cmd = [
            sys.executable,
            str(scripts / "prepare_manual_chatgpt_images.py"),
            "--storyboard",
            str(storyboard),
            "--ratio",
            str(args.manual_image_ratio),
            "--width",
            str(preset["width"]),
            "--height",
            str(preset["height"]),
        ]
        if args.import_manual_images:
            manual_cmd.append("--import-existing")
        run(manual_cmd, env=env)

    maybe_start_comfy(args)

    image_cmd = [
        sys.executable,
        str(scripts / "generate_images_comfy_batches.py"),
        "--storyboard",
        str(storyboard),
        "--batch-size",
        str(args.batch_size),
        "--aspect-ratio",
        preset["aspect"],
        "--final-width",
        str(preset["width"]),
        "--final-height",
        str(preset["height"]),
        "--preset",
        args.image_preset,
        "--reference-denoise",
        str(args.image_reference_denoise),
        "--delay-between-batches",
        str(args.image_delay),
        "--process-priority",
        args.image_priority,
    ]
    if args.image_reference:
        image_cmd.extend(["--reference-image", args.image_reference])
    voice_cmd = [
        sys.executable,
        str(scripts / "generate_voice_edge.py"),
        "--storyboard",
        str(storyboard),
        "--voice",
        args.voice,
        "--voice-style",
        args.voice_style,
    ]
    character_bible = args.character_bible or (project / "character_voice_bible.json")
    if character_bible.exists():
        voice_cmd.extend(["--character-bible", str(character_bible)])
    if args.overwrite:
        image_cmd.append("--overwrite")
        voice_cmd.append("--overwrite")
    if args.image_mode == "hybrid-manual":
        image_cmd.append("--skip-manual")

    processes = []
    if not args.skip_images:
        processes.append(("images", subprocess.Popen(image_cmd, env=env)))
    if not args.skip_voice:
        processes.append(("voice", subprocess.Popen(voice_cmd, env=env)))
    for name, process in processes:
        code = process.wait()
        if code != 0:
            raise SystemExit(f"{name} stage failed with exit code {code}")

    if not args.skip_sfx:
        sfx_cmd = [
            sys.executable,
            str(scripts / "add_story_sfx.py"),
            "--storyboard",
            str(storyboard),
            "--volume",
            str(args.sfx_volume),
        ]
        if args.overwrite:
            sfx_cmd.append("--overwrite")
        run(sfx_cmd, env=env)

    sync_durations(storyboard, args.duration_pad)
    missing_manual = missing_manual_images(storyboard) if args.image_mode == "hybrid-manual" else []
    if missing_manual:
        summary_path = project / "manual-chatgpt-missing.json"
        summary_path.write_text(json.dumps({"missing": missing_manual}, ensure_ascii=False, indent=2), encoding="utf-8")
        message = (
            f"Hybrid manual mode is waiting for {len(missing_manual)} ChatGPT image(s). "
            f"Use prompts in {project / 'chatgpt_image_prompts.md'} and save files into "
            f"{project / 'assets' / 'manual-chatgpt'}. Missing list: {summary_path}"
        )
        if args.wait_for_manual_images or not args.import_manual_images:
            raise SystemExit(message)
        print(message, flush=True)
    validation_stage = "all"
    if args.skip_images and args.skip_voice:
        validation_stage = "text"
    elif args.skip_images:
        validation_stage = "voice"
    elif args.skip_voice:
        validation_stage = "assets"

    run(
        [
            sys.executable,
            str(scripts / "validate_storyboard.py"),
            "--storyboard",
            str(storyboard),
            "--stage",
            validation_stage,
        ],
        env=env,
    )
    contact_sheet = write_contact_sheet(project, storyboard)

    output = project / "output" / f"{slugify(args.title or args.source.stem)}-{args.format}.mp4"
    if not args.skip_render:
        run([sys.executable, str(scripts / "render_video.py"), "--storyboard", str(storyboard), "--output", str(output), "--format", args.format], env=env)

    image_count, total = count_assets(storyboard, "image")
    audio_count, _ = count_assets(storyboard, "audio")
    summary = {
        "project": str(project),
        "storyboard": str(storyboard),
        "format": args.format,
        "resolution": f"{preset['width']}x{preset['height']}",
        "scenes": total,
        "images": image_count,
        "audio": audio_count,
        "contact_sheet": str(contact_sheet),
        "output": str(output) if output.exists() else None,
        "duration": probe_duration(output) if output.exists() else None,
    }
    (project / "pipeline-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
