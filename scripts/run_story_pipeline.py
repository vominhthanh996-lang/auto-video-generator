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

from path_defaults import default_comfy_root, default_projects_root, default_temp_root
from video_presets import apply_video_format, preset_for


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
WORK_ROOT = REPO_ROOT.parent


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
    "Lam Tich sits or kneels in the left third, her tired adult face readable in three-quarter profile; "
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
    ", nude, naked, topless, shirtless woman, bare chest, bare torso, exposed breasts, exposed nipples, areola, "
    "underboob, sideboob, cleavage focus, exposed navel, full bare abdomen, lingerie, bikini, underwear, bra, bralette, crop top, deep neckline, off-shoulder, bare shoulders, collarbone, clavicle, "
    "see-through clothing, wet revealing clothing, erotic pose, seductive pose, pin-up pose, reclining pin-up pose, spread legs, "
    "sexualized body, sexualized minor, childlike body, teen girl, underage, fetish, voyeuristic framing, "
    "focal point on breasts, focal point on buttocks, focal point on crotch, torso glamour shot, waist fetish framing, "
    "open jacket, unbuttoned jacket, open shirt, wardrobe malfunction, boudoir, sultry expression, bedroom eyes, glamour pose, visible chest skin, visible torso skin, visible stomach skin, "
    "androgynous face, gender ambiguous face, masculine woman, feminine man, gender swap, woman with male facial structure, man with feminine facial structure"
)

GENDER_CLARITY_RULE = (
    "Gender clarity rule: the word woman means a clearly adult female character with feminine face and body language; "
    "the word man means a clearly adult male character with masculine face and body language; "
    "do not blend masculine and feminine facial structure, do not make the woman look male, and do not make the man look female."
)

LAM_TICH_VISUAL = (
    "Lam Tich, a beautiful young adult Asian wasteland scavenger woman, early twenties, short black hair in a rough layered crop or short bob, "
    "soft tired clearly feminine facial features under soot and grime, clear wary eyes, cracked lips, exceptionally beautiful readable female face, refined delicate features, subtly glamorous and quietly captivating without being sexualized, "
    "slim survival-worn body in a lightweight summer wasteland outfit, breathable fitted short-sleeve or sleeveless outer layer over a secure dark inner top that fully covers chest and torso, "
    "allow a modest natural neckline and tasteful collarbone hint, never as the focal point, no explicit cleavage, "
    "practical short bottoms or rugged shorts with boots, tasteful visibility of arms and legs appropriate for heat, quiet stubborn survival dignity, cinematic but believable in the wasteland, not explicit, not doll-like"
)

YOUTUBE_SAFE_VISUAL_RULE = (
    "YouTube-safe visual rule: Lam Tich is depicted as an adult woman, not underage; keep her beautiful through face, "
    "short-hair silhouette, emotion, lighting, posture, and wasteland costume; allow only a mild tasteful feminine presence, never sexualized framing; practical survival clothing must fully cover chest and torso; no nudity, no lingerie, "
    "no bare chest, no exposed breasts, no nipple detail, no cleavage focus, no exposed navel, no full bare abdomen, no spread-leg pose, "
    "no erotic pose, no reclining pin-up pose, no voyeuristic framing, and no composition that makes breasts, buttocks, crotch, or bare skin the focal point. "
    "If any neckline or collarbone hint is visible, it must remain tasteful, brief, fully non-fetishized, and never the focus of the shot."
)

LAM_TICH_FACE_RULE = (
    "When Lam Tich is the scene focus, her face must be clearly visible, readable, and recognizably beautiful: "
    "clear feminine facial structure, expressive eyes, readable nose and mouth, appealing but grounded expression, "
    "short black hair framing the face without hiding it, no face obscured by heavy shadow, no face turned fully away, "
    "no tiny unreadable face, no helmet-like hair covering the face, and no composition that reduces her to a distant silhouette "
    "unless the narration explicitly requires an environment-first insert or long-distance scale shot."
)

TAN_DA_VISUAL = (
    "Tan Da, an injured Asian male mercenary with a clear sharply rendered male face, strong straight brows, "
    "steady righteous eyes, clear jawline, high cheekbone structure, clearly masculine features, exceptionally handsome weathered face, principled protective aura, restrained masculine dignity, wet messy black hair, black tactical coat, "
    "broad shoulders, strong forearms, athletic V-shaped muscular build, visible male strength through clothing without sexualized framing, "
    "lying or half-reclining because he cannot stand, feverish but still upright in spirit, abdomen wrapped with dirty bandages, not villainous"
)

TAN_DA_FACE_RULE = (
    "When Tan Da is the scene focus or appears clearly in frame, his face must read like a heroic male lead: "
    "clear jawline, strong brows, steady righteous eyes, handsome weathered features, no soft feminine face, no villain sneer, "
    "no hidden face, no muddy blur, no faceless shadow unless the narration explicitly requires concealment. "
    "His posture and silhouette must still communicate strength, broad shoulders, and masculine presence even when injured."
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


def split_story_units(text):
    units = []
    for raw_paragraph in re.split(r"\n+", text):
        paragraph = raw_paragraph.strip()
        if not paragraph:
            continue
        if paragraph.startswith("#"):
            units.append(paragraph)
            continue
        compact = re.sub(r"\s+", " ", paragraph).strip()
        if not compact:
            continue
        # Dialogue and short reaction lines should survive as standalone visual beats.
        if compact.startswith(('"', "'", "-", "“", "‘")) and len(compact.split()) <= 28:
            units.append(compact)
            continue
        parts = [part.strip() for part in re.split(r"(?<=[.!?。！？…])\s+", compact) if part.strip()]
        if not parts:
            continue
        for part in parts:
            if len(part.split()) <= 6 and units and not units[-1].startswith("#"):
                units[-1] = f"{units[-1]} {part}".strip()
            else:
                units.append(part)
    return units


def piece_profile(piece):
    plain = normalize_vi(piece)
    subject_tokens = []
    if has_any(plain, ["lam tich", "co gai", "nu chinh", "nang"]):
        subject_tokens.append("lam-tich")
    if has_any(plain, ["tan da", "nguoi dan ong", "linh danh thue", "han"]):
        subject_tokens.append("tan-da")
    if has_any(plain, ["con cho", "cho hai ham", "thu bien di", "lon giap bun", "quai vat"]):
        subject_tokens.append("monster")
    if has_any(plain, ["ninh", "chim xam", "la kieu", "doi nguoi", "dam cuop", "nguoi gac"]):
        subject_tokens.append("supporting-cast")
    location_shift = has_any(
        plain,
        [
            "vao", "buoc vao", "qua cong", "ra ngoai", "di qua", "di vao", "den truoc", "trong phong",
            "hanh lang", "sanh", "thang may", "duoi gam xe", "ngoai cua", "tren duong", "bai rac",
            "khu 17", "trong leu", "ngoai leu", "dem xuong", "mua den", "trong muong"
        ],
    )
    object_focus = has_any(
        plain,
        [
            "thit hop", "chai nuoc", "nap hop", "manh kinh", "thanh sat", "vet thuong", "bang gac",
            "tinh thach", "cua", "buc tuong", "thang may", "ban tay", "cai xac", "mui mau", "giay"
        ],
    )
    emotional_beat = has_any(
        plain,
        [
            "kinh hai", "so hai", "chet lang", "ngan nguoi", "bong hieu ra", "nhan ra", "nho lai",
            "do du", "quyet dinh", "thay may man", "thay tuyet vong", "tuc gian", "bat an"
        ],
    )
    return {
        "heading": piece.lstrip().startswith("#"),
        "dialogue": piece.startswith(('"', "'", "-", "“", "‘")),
        "transition": has_any(
            plain,
            [
                "sau do", "ngay khoanh khac", "roi", "ben ngoai", "trong luc", "mot luc sau",
                "lam tich", "tan da", "con cho", "nguoi dan ong", "cai xac", "mui", "bau troi",
                "bai rac", "gam xe", "xe tai", "mo mat", "bo day", "nhin quanh", "cam lay",
                "dam", "lan", "chay", "vao", "qua cong", "mo cua", "cho thang may"
            ],
        ),
        "location_shift": location_shift,
        "object_focus": object_focus,
        "emotional_beat": emotional_beat,
        "subjects": subject_tokens,
        "visual": has_any(
            plain,
            [
                "nam", "ngoi", "dung", "bo", "lan", "mo mat", "liem", "can", "gam gu", "nhin", "thay",
                "cam", "nam lay", "dam", "dap", "keo", "uong", "nha", "phong", "sanh", "hanh lang",
                "bai rac", "gam xe", "xe tai", "xac", "cho", "thung", "tu lanh", "bau troi", "lua", "khoi", "mua"
            ],
        ),
    }


def group_for_scenes(text, min_scenes, max_scenes, words_per_image):
    pieces = split_story_units(text)
    word_count = len(re.findall(r"\S+", text))
    groups = []
    current = []
    current_words = 0
    pending_heading = None
    soft_limit = max(18, int(words_per_image * 1.1))
    hard_limit_words = max(28, int(words_per_image * 1.55))
    for piece in pieces:
        words = len(re.findall(r"\S+", piece))
        profile = piece_profile(piece)
        if profile["heading"]:
            if current:
                groups.append(" ".join(current))
                current = []
                current_words = 0
            pending_heading = piece
            continue
        if pending_heading:
            piece = f"{pending_heading}\n{piece}"
            words = len(re.findall(r"\S+", piece))
            pending_heading = None
        if current:
            current_profile = piece_profile(" ".join(current))
            next_profile = profile
            current_complete = current_words >= max(10, soft_limit - 8) or len(current) >= 2
            over_limit = current_words >= soft_limit or len(current) >= 3
            subject_shift = bool(next_profile["subjects"]) and bool(current_profile["subjects"]) and next_profile["subjects"] != current_profile["subjects"]
            strong_new_beat = (
                next_profile["location_shift"]
                or subject_shift
                or next_profile["dialogue"]
                or (next_profile["object_focus"] and current_profile["visual"] and current_complete)
                or (next_profile["emotional_beat"] and current_complete)
                or (next_profile["transition"] and current_complete)
                or (next_profile["visual"] and current_profile["visual"] and current_complete and current_words >= max(12, soft_limit - 4))
            )
            if over_limit or (strong_new_beat and current_complete) or current_words + words > hard_limit_words:
                groups.append(" ".join(current))
                current = [piece]
                current_words = words
                continue
        current.append(piece)
        current_words += words
    if current:
        groups.append(" ".join(current))

    if max_scenes > 0:
        while len(groups) > max_scenes:
            merge_index = None
            merge_size = None
            for index in range(len(groups) - 1):
                if groups[index].lstrip().startswith("#") or groups[index + 1].lstrip().startswith("#"):
                    continue
                size = len(re.findall(r"\S+", groups[index])) + len(re.findall(r"\S+", groups[index + 1]))
                if merge_size is None or size < merge_size:
                    merge_index = index
                    merge_size = size
            if merge_index is None:
                break
            groups[merge_index : merge_index + 2] = [groups[merge_index] + " " + groups[merge_index + 1]]

    if min_scenes > 0:
        while len(groups) < min_scenes:
            split_index = None
            split_parts = None
            max_parts = 0
            for index, group in enumerate(groups):
                if group.lstrip().startswith("#"):
                    continue
                parts = [part.strip() for part in split_sentences(group) if part.strip()]
                if len(parts) > max_parts:
                    max_parts = len(parts)
                    split_index = index
                    split_parts = parts
            if split_index is None or not split_parts or len(split_parts) < 2:
                break
            midpoint = max(1, len(split_parts) // 2)
            for candidate in range(1, len(split_parts)):
                left = " ".join(split_parts[:candidate])
                right = " ".join(split_parts[candidate:])
                left_words = len(re.findall(r"\S+", left))
                right_words = len(re.findall(r"\S+", right))
                if left_words >= 8 and right_words >= 8:
                    midpoint = candidate
                    break
            groups[split_index : split_index + 1] = [" ".join(split_parts[:midpoint]), " ".join(split_parts[midpoint:])]

    return groups, word_count


def has_any(text, words):
    for word in words:
        pattern = r"(?<!\w)" + re.escape(word).replace(r"\ ", r"\s+") + r"(?!\w)"
        if re.search(pattern, text):
            return True
    return False


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


def narration_visual_lines(narration, limit=2):
    lines = []
    candidates = split_sentences(narration)
    scored = []
    for index, sentence in enumerate(candidates):
        plain = normalize_vi(sentence)
        score = 0
        if has_any(plain, [
            "nam", "ngoi", "dung", "bo", "chay", "lan", "bo day", "mo mat", "nhin", "thay", "cam", "nam lay",
            "dam", "dap", "keo", "day", "mo cua", "qua cong", "vao", "uom", "uong", "liem", "can", "gam gu",
            "xac", "cho", "thu", "nha", "phong", "sanh", "hanh lang", "thang may", "bai rac", "gam xe", "xe tai",
            "bau troi", "mua", "lua", "khoi", "mau", "vet thuong", "thit hop", "nuoc", "tuong", "cua", "thung"
        ]):
            score += 3
        if has_any(plain, ["co le", "khong biet vi sao", "ky uc", "nghi rang", "sau nay", "the gioi cu", "dang so hon"]):
            score -= 1
        if len(plain.split()) <= 4:
            score -= 1
        scored.append((score, index, sentence.strip()))
    picked = [sentence for score, _, sentence in scored if score >= 2]
    if not picked:
        picked = [sentence.strip() for sentence in candidates[:limit] if sentence.strip()]
    return picked[:limit]


def literal_story_action(narration):
    lines = narration_visual_lines(narration, limit=2)
    if not lines:
        return ""
    return " / ".join(lines)


def audio_anchor_lines(narration, limit=3):
    anchors = []
    for line in narration_visual_lines(narration, limit=limit + 2):
        stripped = re.sub(r"\s+", " ", line.strip())
        if stripped and stripped not in anchors:
            anchors.append(stripped)
        if len(anchors) >= limit:
            break
    return anchors


def story_setting_details(narration, continuity=None):
    continuity = continuity or {}
    plain = normalize_vi(narration)
    details = []
    building_context = has_any(plain, ["toa nha", "nha cao tang", "cao oc", "chung cu", "biet thu", "toa thanh", "buc tuong", "cong thanh"])

    setting_rules = [
        (["bai rac", "dong xe phe lieu", "nhat rac"], "a filthy radioactive junkyard with scrap piles, broken appliances, black dirt, and metal wreckage"),
        (["tu lanh gay cua", "thung kim loai ri set", "xe tai lat", "gam xe"], "specific junkyard cover objects such as a broken refrigerator, rusted metal drum, and overturned truck"),
        (["bau troi tren dau mau do", "nuoc ri sat"], "a polluted rust-red sky hanging low over the junkyard"),
        (["nha do nat", "can nha do nat", "phong oc do nat", "biet thu do nat"], "a ruined collapsed house with broken walls, exposed rebar, dust, and abandoned wreckage"),
        (["toa nha cao tang", "nha cao tang", "cao oc", "chung cu cao tang"], "a tall multi-storey building rising from the wasteland skyline"),
        (["toa thanh khong lo", "buc tuong khong lo", "thanh khong lo", "cong thanh"], "a colossal fortified city wall dominating the horizon"),
        (["qua cong", "buoc qua cong", "cong vao", "di qua cong"], "a clear gate or threshold that characters can physically pass through"),
        (["sanh", "dai sanh", "tien sanh"], "an interior lobby or main hall that matches the building described by the story"),
        (["thang may", "cho thang may"], "an elevator area or elevator doors in the building interior"),
        (["hanh lang", "di qua hanh lang"], "a corridor leading deeper into the building"),
        (["vao phong", "mo cua phong", "cua phong"], "a specific interior room that matches the story beat"),
        (["nha kho", "kho chua"], "a warehouse-like interior with storage clutter and industrial decay"),
        (["san thuong", "mai nha"], "a rooftop or upper-level open area connected to the current building"),
        (["duong pho", "ngo hem", "hem", "con pho"], "a ruined street or alley matching the current movement path"),
        (["cua leu", "trong leu", "leu"], "a poor tarp shelter interior made from torn canvas, patched plastic, wire, and scrap poles"),
    ]
    for words, phrase in setting_rules:
        if has_any(plain, words):
            add_unique(details, phrase)
    if building_context and has_any(plain, ["dep", "sang trong", "hao nhoang", "xa hoa", "nguy nga"]):
        add_unique(details, "the described building should look genuinely impressive and high-status within the wasteland world")

    if not details and continuity.get("location") and not has_any(plain, ["tinh lai", "liem", "mom cho", "cho hai ham", "thit hop", "cai xac", "gam xe", "dong xe phe lieu", "mo mat o day", "than the muoi sau tuoi", "trong mot bai rac"]):
        add_unique(details, continuity["location"])

    return details


def story_action_sequence(narration, scene_state, continuity=None):
    continuity = continuity or {}
    plain = normalize_vi(narration)
    actions = []

    specific_rules = [
        (["tinh lai", "liem mau tren tay", "liem tay minh"], "Lam Tich lies weak in the junkyard and wakes as a two-jawed mutated dog licks the blood on her hand"),
        (["luot qua ke ngon tay", "cay nhe lop mau da kho", "vet nut sau trong long ban tay"], "the two-jawed dog slowly licks between Lam Tich's fingers and worries at the dried blood in her cracked palm"),
        (["mo mat", "mom cho thoi rua cach mat"], "Lam Tich opens her eyes to a rotten dog snout hanging terrifyingly close above her face under the rust-red sky"),
        (["ham duoi cua no tach lam hai", "hai hang rang", "luoi cua bi be cong"], "the frame studies the mutant dog's split lower jaw and saw-like crooked teeth at close range"),
        (["cho hai ham", "thu bien di cap gi", "thich an xac moi chet"], "Lam Tich's fractured memory identifies the creature as a rust-grade two-jawed mutant that feeds on the freshly dead"),
        (["khong sua", "thu xem nang da chet han chua", "lam tich cung khong dong"], "Lam Tich lies perfectly still, pretending to be dead while the mutated dog tests whether she is still alive"),
        (["con cho lai liem tay", "nin tho den muc nguc gan nhu no tung"], "Lam Tich holds her breath while the two-jawed dog returns to lick her hand again"),
        (["quay dau", "gam gu voi hai con khac", "can xe mot cai xac"], "the mutated dog turns away from Lam Tich and snarls at two other dogs tearing at a corpse behind the scrap vehicles"),
        (["bi thuong lui lai", "mui mau kich thich", "quay dau ve phia nang"], "the wounded dog recoils while the other two abandon the corpse and slowly turn their attention toward Lam Tich"),
        (["nhat nua manh kinh vo", "dam thang vao mat no"], "Lam Tich snatches up a shard of broken glass and drives it into the mutant dog's eye"),
        (["lan sang ben", "mong vuot cao xuong", "va lung vao thung kim loai ri set"], "Lam Tich rolls aside as claws rip through the place she was lying and she crashes into a rusted metal drum"),
        (["co hong bat ra mot tieng ho khan", "khong duoc ho", "khong duoc keu"], "Lam Tich slams into a rusted drum, fights down a cough, and forces herself to stay silent so the predators do not hear her"),
        (["trong mot bai rac", "than the muoi sau tuoi"], "Lam Tich realizes she is in a teenage scavenger body lying in a filthy radioactive junkyard"),
        (["anh den xe trang loa", "nga tu mua", "tieng phanh", "dien thoai tren mat duong"], "a violent memory flashback of Lam Tich dying at a rain-soaked intersection under white headlights and screeching brakes"),
        (["mo mat o day", "than the muoi sau tuoi", "nguoi chet khong duoc chon"], "Lam Tich wakes fully into the new teenage body and understands she is trapped in a junkyard world where corpses are looted before burial"),
        (["bo day", "da tren canh tay noi tung cham den"], "Lam Tich struggles up from the trash-strewn ground in a weak irradiated body"),
        (["nam lay thanh sat", "thanh sat cong"], "Lam Tich grabs a bent iron bar from the junk pile to defend herself"),
        (["de no can vao ong tay ao rach", "dap thanh sat xuong cai chan truoc"], "Lam Tich sacrifices her torn sleeve to the bite and smashes the iron bar down onto the mutant dog's front leg"),
        (["lan vao duoi gam xe", "vai bi canh sat cua rach"], "Lam Tich dives under an overturned truck to escape the attacking dogs"),
        (["nam ngua", "hai tay cam thanh sat", "choc thang vao cai mom tach doi"], "lying on her back under the truck, Lam Tich thrusts the iron bar straight into the split maw"),
        (["mui do an hong", "thit nau chin bi nhot trong hop sat"], "under the truck, Lam Tich catches the smell of sealed cooked meat and realizes there is canned food nearby"),
        (["thit hop", "mot hop thit con niem phong"], "Lam Tich fixes on a precious sealed can of meat as a life-or-death survival prize"),
        (["cai xac bi bay cho gam", "tui ao trong phong len"], "Lam Tich crawls toward the mauled corpse and notices the inner pocket bulging with a light square object"),
    ]
    for words, phrase in specific_rules:
        if has_any(plain, words):
            add_unique(actions, phrase)

    sequence_rules = [
        (["cam chai nuoc", "cam nuoc", "cam nap hop", "nang nap hop"], "a hand reaches for the water container"),
        (["mo nap", "bat nap", "go nap"], "the container cap or lid is opened"),
        (["dua len moi", "dua ben moi"], "the opened water is raised toward the lips"),
        (["uong", "nuot"], "the character drinks the water"),
        (["di vao nha", "tien vao nha", "buoc vao nha"], "the character moves toward and enters the building"),
        (["qua cong", "buoc qua cong", "di qua cong"], "the character passes through the gate or main threshold"),
        (["vao sanh", "di vao sanh"], "the character crosses into the lobby"),
        (["cho thang may", "dung cho thang may"], "the character stops and waits at the elevator"),
        (["mo cua phong", "vao phong", "day cua phong"], "the character opens the room and enters deeper inside"),
        (["mo cua", "day cua", "keo cua"], "the character opens a door or barrier"),
        (["lang nghe", "ap tai", "nhin qua khe"], "the character listens closely and checks the threat ahead"),
        (["cam dao", "rut dao"], "the character grips a knife and prepares to act"),
        (["keo thung", "keo vat", "keo tam vai", "drag"], "the character drags an object into position"),
        (["dap nghieng", "da vang", "hat do", "huc do"], "the character forcefully kicks or knocks something aside"),
        (["ngoi xuong", "quy xuong"], "the character lowers down into the next beat"),
    ]
    for words, phrase in sequence_rules:
        if has_any(plain, words):
            add_unique(actions, phrase)

    if not actions:
        focus = scene_state.get("focus", "")
        if focus == "survival-introduction":
            if has_any(plain, ["ban tay vang", "khong gian linh tuyen", "di nang nghich thien", "can cu an toan", "nguoi che cho"]):
                actions = ["show Lam Tich's imagined transmigration fantasy contrasted against the brutal wasteland reality waiting for her"]
            elif has_any(plain, ["dat bi o nhiem", "nuoc bi o nhiem", "khong khi bi o nhiem", "mua den", "thuc an qua han"]):
                actions = ["show the poisoned wasteland conditions named in the narration: contaminated ground, tainted water, toxic air, and black-rain danger"]
            elif has_any(plain, ["dong vat bien di", "san nguoi", "long nguoi", "khong co phap luat", "ke song sot", "nguoi chet"]):
                actions = ["show a wasteland where mutated beasts hunt openly and human cruelty feels as dangerous as the monsters"]
            elif has_any(plain, ["than the gay yeu", "sap chet vi nhiem xa", "co gai nhat rac ngoai thanh"]):
                actions = ["show Lam Tich trapped in a weak irradiated scavenger body shaped by hunger, ash, and life outside the city wall"]
            else:
                actions = ["show the exact survival reality established by the current narration instead of a generic pose or title card"]
        elif focus == "water-detail":
            actions = ["Lam Tich studies the last two sips of dirty water and the charcoal residue in the lid"]
        elif focus == "tan-da-condition":
            actions = ["Tan Da lies feverish in the corner while Lam Tich watches his condition and the bleeding cloth"]
        elif focus == "doorway-threat":
            actions = ["Lam Tich listens at the door, watches silhouettes through the torn metal gap, and prepares to defend the shelter"]
        elif focus == "ash-bluff":
            actions = ["Lam Tich drags the ash bucket to the entrance and kicks it so gray ash pours through the gap toward the men outside"]
        else:
            literal = literal_story_action(narration)
            if literal:
                actions = [f"literal story beat from the current narration: {literal}"]
            else:
                actions = ["show the exact visible beat described by the current narration, not a generic pose"]

    previous_action = continuity.get("last_action", "none")
    handoff = f"continue naturally from previous beat: {previous_action}" if previous_action and previous_action != "none" else "start this scene at the first visible beat described by the narration"
    return actions, handoff


def detect_scene_state(narration, continuity=None):
    continuity = continuity or {}
    plain = normalize_vi(narration)
    state = {
        "location": continuity.get("location", "story-defined location matching the narration"),
        "focus": "interaction",
        "threat": continuity.get("threat", "low"),
        "lam_tich_position": continuity.get("lam_tich_position", "position defined by the current narration"),
        "tan_da_position": continuity.get("tan_da_position", ""),
        "door_state": continuity.get("door_state", ""),
        "prop_focus": [],
    }
    if has_any(plain, ["mo mat o day", "than the muoi sau tuoi", "trong mot bai rac", "nguoi chet khong duoc chon"]):
        state["location"] = "a filthy radioactive junkyard where Lam Tich wakes in a teenage scavenger body"
        state["focus"] = "rebirth-junkyard"
        state["threat"] = "high"
        state["lam_tich_position"] = "reeling from rebirth shock while trapped in a junkyard body that is not her own"
        add_unique(state["prop_focus"], "junkyard ground, corpse-looting world logic, and the fragile teenage body")
    elif has_any(plain, ["anh den xe trang loa", "nga tu mua", "tieng phanh", "dien thoai tren mat duong"]):
        state["location"] = "a rain-soaked city intersection from Lam Tich's pre-apocalypse death memory"
        state["focus"] = "memory-flashback"
        state["threat"] = "internal"
        state["lam_tich_position"] = "caught in the instant of impact in a remembered past-life street scene"
        add_unique(state["prop_focus"], "white headlights, wet asphalt, dropped phone, and scattered handbag")
    elif has_any(plain, ["liem mau tren tay", "liem tay minh", "mom cho thoi rua", "ham duoi cua no tach lam hai", "cho hai ham", "thu bien di cap gi"]):
        state["location"] = "a filthy radioactive junkyard with scrap heaps, corpse remains, and mutated dogs closing in"
        state["focus"] = "dog-awakening"
        state["threat"] = "high"
        state["lam_tich_position"] = "lying weak on the junk-strewn ground or frozen beneath the dog's snout"
        state["tan_da_position"] = ""
        state["door_state"] = ""
        add_unique(state["prop_focus"], "blood on Lam Tich's hand")
        add_unique(state["prop_focus"], "mutated two-jawed dog at arm's reach")
    elif has_any(plain, ["quay dau", "gam gu voi hai con khac", "can xe mot cai xac", "dong xe phe lieu"]):
        state["location"] = "a junkyard standoff beside scrap vehicles where several mutated dogs fight over a corpse"
        state["focus"] = "dog-pack"
        state["threat"] = "high"
        state["lam_tich_position"] = "frozen low to the ground while watching the dogs shift attention around the corpse"
        add_unique(state["prop_focus"], "corpse being torn apart behind the scrap vehicles")
        add_unique(state["prop_focus"], "multiple two-jawed dogs in the same kill zone")
    elif has_any(plain, ["dam thang vao mat no", "mong vuot cao xuong", "lan sang ben", "thanh sat cong", "lan vao duoi gam xe", "choc thang vao cai mom tach doi"]):
        state["location"] = "inside a junkyard killing ground beside scrap piles and an overturned truck"
        state["focus"] = "dog-attack"
        state["threat"] = "high"
        state["lam_tich_position"] = "fighting for her life on the trash-strewn ground or under the overturned truck"
        add_unique(state["prop_focus"], "bent iron bar or broken glass used as a weapon")
        add_unique(state["prop_focus"], "overturned truck and claw marks in black dirt")
    elif has_any(plain, ["mui do an hong", "thit nau chin", "thit hop", "mot hop thit con niem phong", "cai xac bi bay cho gam", "tui ao trong phong len"]):
        state["location"] = "the junkyard beside a mauled corpse and scrap vehicles"
        state["focus"] = "corpse-loot"
        state["threat"] = "high"
        state["lam_tich_position"] = "crawling out from cover and watching the corpse the dogs were eating"
        add_unique(state["prop_focus"], "mauled corpse in black tactical clothing")
        add_unique(state["prop_focus"], "sealed can of meat hidden in the inner pocket")
    elif has_any(plain, ["xuyen khong", "mat the", "dai nhiem xa", "khong co phap luat", "chi co ke song sot", "nhat rac ngoai thanh"]):
        state["location"] = "open post-apocalyptic wasteland outside the safe city"
        state["focus"] = "survival-introduction"
        state["threat"] = "ambient"
        state["lam_tich_position"] = "moving through the wasteland or bracing herself in the open"
        state["tan_da_position"] = ""
        state["door_state"] = ""
    if state["focus"] == "interaction" and has_any(plain, ["khu 17 chay", "lua boc", "khoi den", "dan bo chay", "mai leu chay", "ten thep", "chay ruc"]):
        state["location"] = "burning scrap-lane alleys of District 17 with smoke, fire, and fleeing survivors"
        state["focus"] = "mass-chaos"
        state["threat"] = "high"
        state["lam_tich_position"] = "moving through smoke, fire, and panicked crowds"
        state["tan_da_position"] = ""
        state["door_state"] = ""
    if state["focus"] == "interaction" and has_any(plain, ["ngoai cua leu", "qua khe ton", "bong nguoi", "hau seo", "tieng buoc chan"]):
        state["location"] = "at the shelter doorway with outside shadows pressing close"
        state["focus"] = "doorway-threat"
        state["threat"] = "high"
        state["lam_tich_position"] = "standing between the doorway and Tan Da"
    elif state["focus"] == "interaction" and has_any(plain, ["nap hop", "hai ngum", "than loc", "nuoc sach", "nuoc vang nhat", "mui ri sat trong nap"]):
        state["location"] = "inside the shelter around the last dirty water"
        state["focus"] = "water-detail"
        state["prop_focus"] = ["dirty water", "metal lid", "charcoal dust", "dirty cloth filter"]
    elif state["focus"] == "interaction" and has_any(plain, ["nguoi han nong", "sot cao", "gen sup do", "vet thuong bung", "nua than duoi", "khong the nhuc nhich"]):
        state["location"] = "inside the shelter near Tan Da's sickbed corner"
        state["focus"] = "tan-da-condition"
        state["threat"] = "internal"
    elif state["focus"] == "interaction" and has_any(plain, ["keo thung", "dap nghieng", "tro xam", "nam do"]):
        state["location"] = "at the shelter entrance while ash spills outside"
        state["focus"] = "ash-bluff"
        state["threat"] = "high"
        state["door_state"] = "partly opened to spill ash through the metal gap"
    elif state["focus"] == "interaction" and has_any(plain, ["ban tay vang", "khong gian linh tuyen", "di nang nghich thien", "can cu an toan", "nguoi che cho"]):
        state["location"] = "open post-apocalyptic wasteland outside the safe city"
        state["focus"] = "bitter-realization"
        state["threat"] = "ambient"
        state["lam_tich_position"] = "standing alone in the wasteland, comparing fantasy hope to brutal reality"
    elif state["focus"] == "interaction" and has_any(plain, ["di xa", "van khong dong", "ngoi xuong canh han", "de nguy hiem lang xuong"]):
        state["location"] = "inside the shelter after the threat recedes"
        state["focus"] = "aftermath"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and has_any(plain, ["nha do nat", "can nha do nat", "vao nha", "trong nha"]):
        state["location"] = "inside or immediately around the ruined house described by the story"
        state["focus"] = "location-transition"
    elif state["focus"] == "interaction" and has_any(plain, ["toa nha cao tang", "cao oc", "chung cu cao tang"]):
        state["location"] = "at the tall building described by the story"
        state["focus"] = "location-transition"
    elif state["focus"] == "interaction" and has_any(plain, ["qua cong", "cong vao", "buoc qua cong"]):
        state["location"] = "at the main gate or threshold described by the story"
        state["focus"] = "location-transition"
    elif state["focus"] == "interaction" and has_any(plain, ["vao sanh", "dai sanh", "tien sanh"]):
        state["location"] = "inside the main lobby described by the story"
        state["focus"] = "location-transition"
    elif state["focus"] == "interaction" and has_any(plain, ["cho thang may", "thang may"]):
        state["location"] = "at the elevator area inside the building"
        state["focus"] = "location-transition"
    elif state["focus"] == "interaction" and has_any(plain, ["vao phong", "mo cua phong", "cua phong"]):
        state["location"] = "inside the specific room described by the story"
        state["focus"] = "location-transition"

    if has_any(plain, ["cam dao", "con dao gay", "luoi mo"]):
        add_unique(state["prop_focus"], "broken knife hidden in Lam Tich's hand")
    if has_any(plain, ["cai coi den", "cai coi", "coi den"]):
        add_unique(state["prop_focus"], "small dark whistle")
    return state


def infer_beat_goal(narration, scene_state, actions, props):
    plain = normalize_vi(narration)
    focus = scene_state.get("focus", "")
    if focus == "survival-introduction":
        return "establish the wasteland rules and the protagonist's disadvantage"
    if focus == "bitter-realization":
        return "contrast fantasy expectations with the actual brutal world"
    if focus == "memory-flashback":
        return "show the remembered death that explains the current shock"
    if focus == "rebirth-junkyard":
        return "show Lam Tich realizing the new body and corpse-looting world"
    if focus in {"dog-awakening", "dog-pack", "dog-attack"}:
        return "show the exact predator threat and the survival response"
    if focus == "corpse-loot":
        return "show the food-or-die choice around corpse loot"
    if focus == "water-detail":
        return "show the value and scarcity of the remaining water"
    if focus == "tan-da-condition":
        return "show Tan Da's condition clearly enough for the audience to understand the risk"
    if focus == "doorway-threat":
        return "show the danger outside and Lam Tich reading it in time"
    if focus == "ash-bluff":
        return "show the improvised bluff that pushes the threat away"
    if focus == "aftermath":
        return "show the brief release after danger without breaking the tension"
    if has_any(plain, ["qua cong", "vao sanh", "cho thang may", "vao phong"]):
        return "show the correct step of movement through the current location sequence"
    if props:
        return "show the key survival object named by the narration and why it matters"
    if actions:
        return "show the current action beat clearly enough that the audience can follow the plot without reading"
    return "show the current narrated beat with a clear visual objective"


def infer_primary_subject(narration, scene_state):
    plain = normalize_vi(narration)
    focus = scene_state.get("focus", "")
    if focus in {"tan-da-condition", "aftermath"} or "tan da" in plain or "nguoi dan ong" in plain or "linh danh thue" in plain:
        if "lam tich" in plain or "nang" in plain:
            return "Lam Tich and Tan Da"
        return "Tan Da"
    if focus in {"dog-awakening", "dog-pack", "dog-attack"}:
        return "Lam Tich and the mutated dogs"
    if focus == "corpse-loot":
        return "Lam Tich and the corpse loot"
    if focus == "memory-flashback":
        return "Lam Tich in the death memory"
    return "Lam Tich"


def infer_primary_object(props, narration):
    if props:
        return props[0]
    anchors = audio_anchor_lines(narration, limit=1)
    return anchors[0] if anchors else ""


def scene_beat_metadata(narration, scene_state, actions, setting, props, continuity=None):
    continuity = continuity or {}
    return {
        "beat_type": scene_state.get("focus", "interaction"),
        "beat_goal": infer_beat_goal(narration, scene_state, actions, props),
        "beat_subject": infer_primary_subject(narration, scene_state),
        "beat_object": infer_primary_object(props, narration),
        "beat_location": setting[0] if setting else scene_state.get("location", ""),
        "audio_anchor_lines": audio_anchor_lines(narration, limit=3),
        "transition_from_previous": continuity.get("last_action", "none"),
    }


def shot_type_for(narration, scene_index):
    lower = narration.lower()
    plain = normalize_vi(narration)
    if has_any(plain, ["anh den xe trang loa", "nga tu mua", "tieng phanh", "dien thoai tren mat duong"]):
        return "flashback insert shot at a rain-soaked intersection with the fatal impact details clearly readable"
    if has_any(plain, ["mo mat o day", "than the muoi sau tuoi", "trong mot bai rac", "nguoi chet khong duoc chon"]):
        return "medium rebirth shot showing Lam Tich awakening in the junkyard and grasping the horror of the new body and world"
    if has_any(plain, ["liem mau tren tay", "liem tay minh", "mom cho thoi rua cach mat", "ham duoi cua no tach lam hai"]):
        return "close threat shot showing Lam Tich on the ground and the mutated dog's muzzle or split jaw clearly readable"
    if has_any(plain, ["quay dau", "gam gu voi hai con khac", "can xe mot cai xac", "dong xe phe lieu"]):
        return "medium threat shot showing Lam Tich's cover position, the dogs, and the corpse behind the scrap vehicles"
    if has_any(plain, ["dam thang vao mat no", "mong vuot cao xuong", "lan vao duoi gam xe", "choc thang vao cai mom tach doi"]):
        return "violent survival action shot with body positions, weapon, and predator attack clearly readable"
    if has_any(plain, ["thit hop", "cai xac bi bay cho gam", "tui ao trong phong len"]):
        return "medium survival discovery shot showing the corpse, pocket target, and surrounding danger"
    if has_any(plain, ["khu 17 chay", "chay len", "lua", "khoi", "gao", "bo chay", "ten thep"]):
        return "wide or medium survival action shot with burning shelters, fleeing survivors, and attack direction readable"
    if has_any(plain, ["nap hop", "hai ngum", "than loc", "nuoc sach", "nuoc vang nhat", "mui ri sat trong nap"]):
        return "close insert shot on water, metal lid, dirty cloth filter, and trembling hands"
    if has_any(plain, ["nguoi han nong", "sot cao", "gen sup do", "vet thuong bung", "nua than duoi", "khong the nhuc nhich"]):
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

    mentions_lam_tich = "lam tich" in plain or has_any(plain, ["nang", "co gai", "nu chinh"])
    mentions_tan_da = "tan da" in plain or "nguoi dan ong" in plain or "linh danh thue" in plain
    if mentions_lam_tich:
        add_unique(characters, LAM_TICH_VISUAL)
    if mentions_tan_da:
        add_unique(characters, TAN_DA_VISUAL)
    if not characters:
        continuity_text = " ".join(continuity.get("anchors", []))
        if "Lam Tich" in continuity_text:
            add_unique(characters, LAM_TICH_VISUAL)
        if "Tan Da" in continuity_text and (
            "two-shot" in shot_type or scene_state["focus"] in {"tan-da-condition", "aftermath", "doorway-threat"}
        ):
            add_unique(characters, TAN_DA_VISUAL)
    if not characters:
        add_unique(characters, "the exact survivor or person described in the narration, shown from side or back view")

    add_unique(setting, scene_state["location"])
    add_unique(setting, "District 17 wasteland survival setting")
    for detail in story_setting_details(narration, continuity):
        add_unique(setting, detail)

    keyword_rules = [
        (["khu 17"], setting, "District 17 wasteland outside the safe city, dirty scrap tents and ruined industrial silhouettes"),
        (["nap hop", "hai ngum", "nuoc sach"], props, "small metal can lid holding the last two sips of yellowish filtered water"),
        (["vang nhat", "bui than", "than loc", "mui ri sat trong nap"], props, "murky yellow water with charcoal dust and rusty metallic residue"),
        (["vet thuong bung", "mau van tham", "gen sup do"], props, "dirty abdominal bandage with dark stains and faint toxic veins under the skin"),
        (["tieng buoc chan", "bong nguoi", "hau seo"], props, "door gap, torn cloth curtain, and hostile silhouettes outside"),
        (["keo thung", "tro xam", "nam do"], props, "rusted ash bucket filled with stove ash and bone dust"),
        (["cam dao", "con dao gay"], props, "broken survival knife hidden in Lam Tich's hand"),
        (["coi den", "cai coi"], props, "small dark whistle"),
        (["bai rac", "dong xe phe lieu", "thung kim loai ri set", "tu lanh gay cua"], setting, "a filthy junkyard of scrap heaps, rusted appliances, broken metal drums, and black contaminated dirt"),
        (["bau troi tren dau mau do", "nuoc ri sat", "troi tren dau mau do"], setting, "a polluted rust-red sky hanging over the junkyard"),
        (["cho hai ham", "mom cho thoi rua", "ham duoi cua no tach lam hai", "thu bien di cap gi"], props, "a mutated two-jawed dog with a split lower jaw, rotten muzzle, yellow foam, and saw-like crooked teeth"),
        (["cai xac bi bay cho gam", "nguoi dan ong mac ao khoac chien thuat mau den"], props, "a mauled man's corpse in torn black tactical clothing"),
        (["xe tai lat", "gam xe"], props, "an overturned truck that serves as desperate cover"),
        (["manh kinh vo"], props, "a shard of broken glass in Lam Tich's hand"),
        (["thanh sat cong"], props, "a bent iron bar scavenged from the junk pile"),
        (["thit hop", "hop thit"], props, "a sealed can of meat hidden in the corpse's inner pocket"),
    ]
    for words, target, phrase in keyword_rules:
        if has_any(plain, words):
            add_unique(target, phrase)

    focus = scene_state["focus"]
    if focus == "survival-introduction":
        characters = [LAM_TICH_VISUAL]
        mood = ["bleak introduction, exhaustion, and disbelief at the apocalypse"]
    elif focus == "memory-flashback":
        characters = [LAM_TICH_VISUAL]
        mood = ["violent intrusive memory of death before the wasteland body-awakening"]
    elif focus == "rebirth-junkyard":
        characters = [LAM_TICH_VISUAL]
        mood = ["rebirth shock, body-dislocation, and immediate junkyard survival horror"]
    elif focus == "dog-awakening":
        characters = [LAM_TICH_VISUAL]
        mood = ["predatory stillness, shock, and waking terror in the junkyard"]
    elif focus == "dog-attack":
        characters = [LAM_TICH_VISUAL]
        mood = ["violent survival panic and desperate split-second reactions"]
    elif focus == "dog-pack":
        characters = [LAM_TICH_VISUAL]
        mood = ["predators circling the corpse while Lam Tich waits for a narrow survival opening"]
    elif focus == "corpse-loot":
        characters = [LAM_TICH_VISUAL]
        mood = ["hunger, danger, and ruthless survival calculation beside the corpse"]
    elif focus == "mass-chaos":
        mood = ["mass panic, fire, smoke, and survival under attack"]
    elif focus == "bitter-realization":
        characters = [LAM_TICH_VISUAL]
        mood = ["bitter realization, loneliness, and harsh contrast between fantasy and reality"]
    elif focus == "water-detail":
        characters = [LAM_TICH_VISUAL]
        mood = ["thirst, hesitation, and fragile survival calculation"]
    elif focus == "tan-da-condition":
        add_unique(characters, TAN_DA_VISUAL)
        mood = ["fever, weakness, and dread of gene collapse"]
    elif focus == "doorway-threat":
        add_unique(characters, LAM_TICH_VISUAL)
        mood = ["immediate danger at the shelter entrance"]
    elif focus == "ash-bluff":
        add_unique(characters, LAM_TICH_VISUAL)
        mood = ["desperate bluff using fear of red fungus"]
    elif focus == "aftermath":
        add_unique(characters, LAM_TICH_VISUAL)
        add_unique(characters, TAN_DA_VISUAL)
        mood = ["short-lived relief with dread still hanging in the shelter"]
    elif has_any(plain, ["dua nap hop", "ben moi", "uong", "nhuong nuoc"]):
        mood = ["intimate survival trust under exhaustion"]

    actions, handoff = story_action_sequence(narration, scene_state, continuity)
    mood = mood or ["tense cinematic survival mood"]

    for prop in scene_state.get("prop_focus", []):
        add_unique(props, prop)

    must_show = []
    for source in (characters, setting, actions, props):
        for item in source:
            add_unique(must_show, item)
    must_show = must_show[:8]

    reference_recipe = "Use the approved sample only as character identity, face quality, and clothing material reference, never as a fixed composition, repeated pose, or repeated location"
    scene_state_parts = [f"location={scene_state['location']}", f"threat={scene_state['threat']}"]
    if any("Lam Tich" in item for item in characters):
        scene_state_parts.append(f"Lam Tich position={scene_state['lam_tich_position']}")
    if any("Tan Da" in item for item in characters) and scene_state.get("tan_da_position"):
        scene_state_parts.append(f"Tan Da position={scene_state['tan_da_position']}")
    if scene_state.get("door_state") and "door" in scene_state["location"]:
        scene_state_parts.append(f"door state={scene_state['door_state']}")
    beat_meta = scene_beat_metadata(narration, scene_state, actions, setting, props, continuity)
    prompt = (
        "Premium cinematic realistic wasteland story frame with strong story accuracy and scene-to-scene continuity. "
        f"{GENDER_CLARITY_RULE} "
        f"{reference_recipe}. "
        "Do not turn every scene into the same two-character shelter shot. "
        "The current narration is the highest-priority source of truth. "
        "The frame must illustrate the exact beat being narrated right now. "
        f"Beat goal: {beat_meta['beat_goal']}. "
        f"CONTINUITY FROM PREVIOUS SCENE: {continuity.get('summary', 'start of sequence')}. "
        f"Current scene state: {'; '.join(scene_state_parts)}. "
        f"MUST SHOW: {', '.join(must_show)}. "
        f"Characters: {', '.join(characters)}. "
        f"Setting: {', '.join(setting)}. "
        f"Shot type: {shot_type}. "
        f"Action: {', '.join(actions)}. "
        f"Previous action handoff: {handoff}. "
        f"Persistent visual anchors: {', '.join(continuity.get('anchors', [])[:4]) if continuity.get('anchors') else 'keep character design and world style consistent'}. "
        f"Important props: {', '.join(props) if props else 'only props described by the narration'}. "
        f"Mood: {', '.join(mood)}. "
        "The environment must follow the exact story description: if the narration says a ruined house, show a ruined house; if it says a tall beautiful building, show a tall beautiful building in wasteland context; if it says a colossal city wall, show that colossal city wall clearly. "
        "If the narration describes a sequence of movement, show the correct current step of that sequence rather than resetting to a generic pose. "
        "Use grounded Asian webnovel casting, realistic dirty survival clothing, readable faces only when the story beat needs the face visible, and keep spatial logic consistent from one scene to the next. "
        f"{LAM_TICH_FACE_RULE} "
        f"{TAN_DA_FACE_RULE} "
        "Lam Tich may wear a heat-appropriate summer wasteland outfit with secure chest coverage, modest neckline, visible arms, and visible legs, but do not expose breasts, nipples, navel, or full abdomen, and do not frame her like a glamour portrait. "
        "Prefer insert shots for objects, doorway shots for outside threats, single shots for illness, and two-shots only when the relationship beat is the real focus. "
        f"{style}. Scene context: {compact}"
    )
    return {
        "prompt": prompt,
        "characters": characters,
        "must_show": must_show,
        "setting": setting,
        "actions": actions,
        "props": props,
        "shot_type": shot_type,
        "scene_state": scene_state,
        "beat_meta": beat_meta,
    }


def update_visual_continuity(previous, visual):
    anchors = list(previous.get("anchors") or [])
    for key in ("characters", "setting"):
        for item in visual.get(key) or []:
            if any(token in item.lower() for token in ["lam tich", "tan da", "district 17", "wasteland", "junkyard", "tarp shelter", "safe city", "house", "building", "lobby", "elevator", "room", "gate", "city wall", "overturned truck", "corpse"]):
                add_unique(anchors, item)
    anchors = anchors[-6:]
    last_action = ", ".join((visual.get("actions") or [])[:2]) or previous.get("last_action", "none")
    scene_state = visual.get("scene_state") or {}
    summary_parts = []
    if anchors:
        summary_parts.append("stable anchors: " + ", ".join(anchors[:4]))
    if scene_state.get("location"):
        summary_parts.append("location: " + scene_state["location"])
    if last_action:
        summary_parts.append("next visual handoff: " + last_action)
    return {
        "anchors": anchors,
        "last_action": last_action,
        "location": scene_state.get("location", previous.get("location", "story-defined location matching the narration")),
        "threat": scene_state.get("threat", previous.get("threat", "low")),
        "lam_tich_position": scene_state.get("lam_tich_position", previous.get("lam_tich_position", "position defined by the current narration")),
        "tan_da_position": scene_state.get("tan_da_position", previous.get("tan_da_position", "")),
        "door_state": scene_state.get("door_state", previous.get("door_state", "")),
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
        "location": "story-defined location matching the narration",
        "threat": "low",
        "lam_tich_position": "position defined by the current narration",
        "tan_da_position": "",
        "door_state": "",
    }
    for index, narration in enumerate(groups, 1):
        visual = visual_prompt_data(narration, style, continuity, index)
        current_continuity = dict(continuity)
        beat_meta = visual.get("beat_meta") or {}
        scenes.append(
            {
                "id": f"scene-{index:03d}",
                "duration": 6,
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
                "beat_type": beat_meta.get("beat_type", "interaction"),
                "beat_goal": beat_meta.get("beat_goal", ""),
                "beat_subject": beat_meta.get("beat_subject", ""),
                "beat_object": beat_meta.get("beat_object", ""),
                "beat_location": beat_meta.get("beat_location", ""),
                "audio_anchor_lines": beat_meta.get("audio_anchor_lines", []),
                "transition_from_previous": beat_meta.get("transition_from_previous", "none"),
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
    ensure_character_voice_bible(project, text, args.voice)
    return project, storyboard, config


def ensure_character_voice_bible(project, text, narrator_voice):
    bible_path = project / "character_voice_bible.json"
    if bible_path.exists():
        return bible_path

    plain = normalize_vi(text)
    characters = {}
    if "lam tich" in plain:
        characters["Lâm Tịch"] = {
            "gender": "female",
            "voice": "vi-female",
            "aliases": ["Lam Tich", "lâm tịch", "nàng", "cô gái", "cô"],
            "traits": ["honest", "afraid", "cold"],
            "voice_note": "fragile but stubborn, soft inner voice, sharper under survival pressure",
        }
    if "tan da" in plain:
        characters["Tần Dã"] = {
            "gender": "male",
            "voice": "vi-male",
            "aliases": ["Tan Da", "tần dã", "hắn", "người đàn ông", "lính đánh thuê"],
            "traits": ["cold", "righteous"],
            "voice_note": "low, restrained, calm under threat, speaks little",
        }
    if "hau seo" in plain:
        characters["Hậu Sẹo"] = {
            "gender": "male",
            "voice": "vi-male",
            "aliases": ["Hau Seo", "hậu sẹo", "sẹo ca"],
            "traits": ["evil"],
            "voice_note": "rough and threatening, but not theatrical",
        }
    if "lao phung" in plain:
        characters["Lão Phùng"] = {
            "gender": "male",
            "voice": "vi-male",
            "aliases": ["Lao Phung", "lão phùng", "ông già"],
            "traits": ["cold"],
            "voice_note": "dry, old, pragmatic",
        }

    bible = {
        "narrator": {
            "voice": narrator_voice or "vi-female",
            "voice_note": "stable dark wasteland narrator lane",
        },
        "defaults": {
            "dialogue_voice": "vi-female",
            "male_dialogue_voice": "vi-male",
            "female_dialogue_voice": "vi-female",
            "neutral_dialogue_voice": "vi-female",
        },
        "characters": characters,
    }
    bible_path.write_text(json.dumps(bible, ensure_ascii=False, indent=2), encoding="utf-8")
    return bible_path


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
    voice_plan_path = base / "voice-plan.json"
    voice_plan = {}
    if voice_plan_path.exists():
        try:
            voice_plan = json.loads(voice_plan_path.read_text(encoding="utf-8-sig"))
        except Exception:
            voice_plan = {}
    scene_plan_map = {item.get("id"): item for item in voice_plan.get("scenes", []) if item.get("id")}
    for scene in config.get("scenes") or []:
        audio = scene.get("audio")
        if not audio:
            continue
        duration = probe_duration(resolve(base, audio))
        if duration:
            scene["duration"] = round(duration + pad, 2)
            scene["audio_duration"] = round(duration, 2)
        plan = scene_plan_map.get(scene.get("id"))
        if plan:
            scene["audio_units"] = plan.get("plan", [])
            scene["audio_anchor_lines"] = scene.get("audio_anchor_lines") or plan.get("audio_anchor_lines", [])
            scene["timing_source"] = "voice-plan"
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
    parser.add_argument("--source", type=Path, help="UTF-8 story text file.")
    parser.add_argument("--title", default="")
    parser.add_argument("--project", type=Path)
    parser.add_argument("--root", default=str(default_projects_root(REPO_ROOT)))
    parser.add_argument("--format", choices=["youtube", "tiktok"], default="youtube")
    parser.add_argument("--language", default="vi")
    parser.add_argument("--voice", default="vi-female")
    parser.add_argument("--voice-style", choices=["plain", "story-emotional", "wasteland-dark"], default="wasteland-dark")
    parser.add_argument("--character-bible", type=Path, help="Optional JSON file with persistent character voice traits.")
    parser.add_argument("--words-per-image", type=int, default=24)
    parser.add_argument("--min-scenes", type=int, default=60)
    parser.add_argument("--max-scenes", type=int, default=120)
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
    parser.add_argument("--comfy-root", default=str(default_comfy_root(REPO_ROOT)))
    parser.add_argument("--skip-images", action="store_true")
    parser.add_argument("--skip-voice", action="store_true")
    parser.add_argument("--skip-sfx", action="store_true", help="Skip subtle story-aware sound effects under narration.")
    parser.add_argument("--sfx-volume", type=float, default=0.45, help="SFX mix volume after cleanup. Try 0.35-0.65.")
    parser.add_argument("--skip-render", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if not args.source and not args.project:
        parser.error("the following arguments are required: --source (or provide --project for an existing storyboard project)")
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
    if args.source:
        project, storyboard, config = build_storyboard(args)
    else:
        project = args.project.resolve()
        storyboard = project / "storyboard.json"
        if not storyboard.exists():
            raise SystemExit(f"Storyboard not found in project: {storyboard}")
        config = json.loads(storyboard.read_text(encoding="utf-8-sig"))
    env = dict(os.environ)
    env["TEMP"] = str(default_temp_root(REPO_ROOT))
    env["TMP"] = env["TEMP"]
    Path(env["TEMP"]).mkdir(parents=True, exist_ok=True)

    scripts = Path(__file__).resolve().parent
    if args.source:
        run([sys.executable, str(scripts / "validate_storyboard.py"), "--storyboard", str(storyboard), "--stage", "text"], env=env)

    if args.source and args.image_mode == "hybrid-manual":
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

    if args.source:
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

    if args.source:
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

    output_stem = args.title or (args.source.stem if args.source else project.name)
    output = project / "output" / f"{slugify(output_stem)}-{args.format}.mp4"
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

