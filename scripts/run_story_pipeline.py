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
    "dirty realistic characters in the exact story location implied by the narration, whether shelter interior, junkyard, station gate, tunnel, corridor, vehicle cover, ruined room, or open wasteland exterior, "
    "foreground story props, readable midground action, background world context that matches the current scene, "
    "warm practical light against cold toxic atmosphere when relevant, realistic grime, torn cloth, sweat, ash, dirty bandages, dark stains on cloth, "
    "35mm cinema lens, subtle film grain, muted natural colors, high contrast but not oversaturated, clear natural faces, no text, no watermark"
)

REFERENCE_IMAGE_RECIPE = (
    "Use the approved sample only as identity, face consistency, clothing material, lighting mood, and wasteland texture reference. "
    "Never reuse the same composition, same left-right blocking, same shelter layout, same pose, or same location unless the narration explicitly calls for it."
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
    "underboob, sideboob, cleavage focus, lingerie, two-piece bikini, string bikini, triangle bikini, bikini bottom, swimsuit bottom, swimwear, underwear, panties, thong, bra and panties set, matching underwear set, "
    "see-through clothing, wet revealing clothing, erotic pose, seductive pose, pin-up pose, reclining pin-up pose, spread legs, "
    "sexualized body, sexualized minor, childlike body, teen girl, underage, fetish, voyeuristic framing, "
    "focal point on breasts, focal point on buttocks, focal point on crotch, torso glamour shot, waist fetish framing, "
    "open jacket, unbuttoned jacket, open shirt, wardrobe malfunction, boudoir, sultry expression, bedroom eyes, glamour pose, visible chest skin, visible torso skin, visible stomach skin, "
    "androgynous face, gender ambiguous face, masculine woman, feminine man, gender swap, woman with male facial structure, man with feminine facial structure"
)

GENDER_CLARITY_RULE = (
    "Gender clarity rule: the word woman means a clearly adult female character with feminine face and body language; "
    "the word man means a clearly adult male character with masculine face, broad masculine body language, and wasteland toughness; "
    "maintain consistent character identity and body language from scene to scene; "
    "avoid random identity drift or face-swapping between scenes. "
    "Female sexy styling applies only to adult women such as Lam Tich; male characters must never inherit Lam Tich's sports-bikini-style top, crop top, short shorts, or feminine glamour outfit."
)

LAM_TICH_VISUAL = (
    "Lam Tich, a beautiful young Asian wasteland scavenger woman with a striking feminine face, tired expressive eyes, cracked lips, "
    "short black hair worn rough from survival, slim toned build, grounded sensuality without glamour posing, "
    "practical summer wasteland clothing with bare arms and readable legs: a weathered athletic survival crop top or thick-strap sports-bikini-style top, top only, under torn scavenger layers, paired with rugged short shorts or torn utility shorts, "
    "sporty and sexy but never a two-piece bikini, never bikini bottoms, never panties, never swimwear bottoms; when the story beat calls for charm, confidence, temptation, intimacy, or a character spotlight, let her read visibly seductive and glamorous in a grounded wasteland way, while nipples and intimate areas stay fully covered by fabric, "
    "stubborn survival dignity, attractive in a believable human way"
)

YOUTUBE_SAFE_VISUAL_RULE = (
    "YouTube-safe visual rule: practical survival clothing may expose arms, legs, shoulders, and some upper chest when the character design calls for it, "
    "but nipples, areola, buttocks, and crotch must always stay covered by fabric. "
    "No nudity, no exposed breasts, and no shot that treats the chest, buttocks, or crotch as the visual focus."
)

LAM_TICH_FACE_RULE = (
    "When Lam Tich is the scene focus, make her face readable and emotionally clear: expressive eyes, readable nose and mouth, "
    "short black hair not hiding the whole face, tired but memorable survival presence, no tiny unreadable face, "
    "beautiful and feminine in a grounded wasteland way, never a studio beauty-portrait."
)

TAN_DA_VISUAL = (
    "Tan Da, a tall muscular Asian male mercenary with a handsome upright face, strong brows, steady alert eyes, weathered jawline, "
    "broad shoulders, powerful build, rugged masculine wasteland clothing: worn dark tactical coat or heavy scavenger jacket, long practical pants, boots, belts, straps, armor scraps, dirty bandages at the abdomen when the narration calls for it, "
    "never a sports top, never crop top, never short shorts, never feminine styling, "
    "protective righteous presence, exhausted but still physically imposing, never villain-coded unless the story beat says so"
)

TAN_DA_FACE_RULE = (
    "When Tan Da is visible, keep his face readable and grounded: strong male structure, tired but steady eyes, no faceless blur, "
    "no feminine drift, no villain sneer unless the narration demands it."
)

ACTION_BEAT_VERBS = [
    "mo mat", "nhin", "thay", "cam", "nam lay", "giat", "keo", "lan", "bo", "chay", "dam", "chem",
    "can", "liem", "uong", "mo cua", "dong cua", "buoc vao", "qua cong", "vao sanh", "cho thang may",
    "vao phong", "keo thung", "dap", "ngoi xuong", "quay dau", "nho lai", "nhan ra", "quyet dinh",
]

SUPPORTING_CHARACTER_RULES = [
    ("La Kieu", ["la kieu"], "La Kieu, a dangerous adult wasteland raider leader with a hard face and controlled menace"),
    ("Ninh", ["ninh"], "Ninh, a slight preteen mute boy survivor carrying a writing board, clearly child-sized with a wary hungry face"),
    ("Tieu Mai", ["tieu mai"], "Tieu Mai, a preteen girl survivor, clearly a child with alert eyes and quick reactions"),
    ("Tieu Ngo", ["tieu ngo"], "Tieu Ngo, a wounded boy survivor protecting the younger child while trying not to show pain"),
    ("Tieu Bao", ["tieu bao"], "Tieu Bao, a very young child held close by the adults during danger"),
    ("A That", ["a that"], "A That, a lean young male scavenger with cracked lips, nervous humor, and quick restless movements"),
    ("A Muc", ["a muc"], "A Muc, a guarded teenage scavenger boy with a hook tool and sharp suspicious eyes"),
    ("Di Man", ["di man"], "Di Man, an older wasteland woman with a severe practical face and protective posture toward the children"),
    ("Bach Nhi", ["bach nhi"], "Bach Nhi, a round-faced adult male trader with a polite smile that feels cold and calculating"),
    ("Thiet Oa", ["thiet oa"], "Thiet Oa, a hardened adult scavenger with a hammer and blunt no-nonsense body language"),
    ("Moc Sanh", ["moc sanh"], "Moc Sanh, a young adult woman with machine grease on her face and a guarded weapon-ready stance"),
    ("Chim Xam", ["chim xam"], "the Chim Xam survivor group moving as a tired, wounded, mistrustful column"),
    ("guard outside the shelter", ["nguoi gac", "ke gac", "ten gac"], "the armed guard or watcher described by the narration"),
    ("scarred raider", ["hau seo"], "Hau Seo, a scarred adult raider with a threatening posture"),
    ("the crowd in District 17", ["dam dong", "nguoi dan", "nhung nguoi xung quanh"], "a tense crowd of wasteland civilians in District 17"),
    ("the robber group", ["dam cuop"], "a rough robber group closing in together"),
]


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
        parts = [part.strip() for part in re.split(r"(?<=[.!?。！？…;:])\s+", compact) if part.strip()]
        if not parts:
            continue
        for part in parts:
            plain = normalize_vi(part)
            is_short_action = len(part.split()) <= 8 and has_any(plain, ACTION_BEAT_VERBS)
            is_short_reaction = len(part.split()) <= 5 and has_any(plain, ["roi", "khung lai", "chet lang", "nho lai", "giat minh"])
            if len(part.split()) <= 6 and not is_short_action and not is_short_reaction and units and not units[-1].startswith("#"):
                units[-1] = f"{units[-1]} {part}".strip()
            else:
                units.append(part)
    return units


def extract_character_mentions(text):
    plain = normalize_vi(text)
    mentions = []
    if has_any(plain, ["lam tich", "co gai", "nu chinh", "nang"]):
        mentions.append(("lam-tich", "Lam Tich", LAM_TICH_VISUAL))
    if has_any(plain, ["tan da", "nguoi dan ong", "linh danh thue", "han"]):
        mentions.append(("tan-da", "Tan Da", TAN_DA_VISUAL))
    if has_any(plain, ["con cho", "cho hai ham", "thu bien di", "lon giap bun", "quai vat"]) and not has_any(plain, ["rang cho hai ham", "tui nho rang cho", "tui rang cho"]):
        mentions.append(("monster", "the monster or mutant beast in the narration", "the exact monster described by the narration"))
    for label, tokens, visual_ref in SUPPORTING_CHARACTER_RULES:
        if has_any(plain, tokens):
            mentions.append((slugify(label), label, visual_ref))
    deduped = []
    seen = set()
    for item in mentions:
        if item[0] in seen:
            continue
        seen.add(item[0])
        deduped.append(item)
    return deduped


def character_visual_descriptor(label):
    if not label:
        return ""
    plain = normalize_vi(label)
    for _, tokens, visual_ref in SUPPORTING_CHARACTER_RULES:
        if has_any(plain, tokens):
            return visual_ref
    if "lam tich" in plain:
        return LAM_TICH_VISUAL
    if "tan da" in plain:
        return TAN_DA_VISUAL
    return label


def piece_profile(piece):
    plain = normalize_vi(piece)
    subject_tokens = [item[0] for item in extract_character_mentions(piece)]
    if has_any(plain, ["doi nguoi", "dam cuop", "nguoi gac"]) and "supporting-cast" not in subject_tokens:
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
                "luc nay", "ngay sau do", "bat dau", "tiep theo", "ve phia", "re sang",
                "buoc vao", "qua cong", "mo cua", "vao sanh", "cho thang may", "vao phong"
            ],
        ),
        "location_shift": location_shift,
        "object_focus": object_focus,
        "emotional_beat": emotional_beat,
        "action_beat": has_any(plain, ACTION_BEAT_VERBS),
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



def beat_weight(profile):
    weight = 0
    if profile["dialogue"]:
        weight += 2
    if profile["location_shift"]:
        weight += 3
    if profile["object_focus"]:
        weight += 2
    if profile["emotional_beat"]:
        weight += 2
    if profile["action_beat"]:
        weight += 2
    if profile["transition"]:
        weight += 1
    if profile["subjects"]:
        weight += 1
    return weight



def group_for_scenes(text, min_scenes, max_scenes, words_per_image):
    pieces = split_story_units(text)
    word_count = len(re.findall(r"\S+", text))
    natural_beat_count = sum(
        1
        for piece in pieces
        if not piece.lstrip().startswith("#")
        and beat_weight(piece_profile(piece)) >= 2
    )

    groups = []
    current = []
    current_words = 0
    pending_heading = None
    hard_limit_words = max(34, int(words_per_image * 1.9))

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
            profile = piece_profile(piece)
            pending_heading = None

        if current:
            current_text = " ".join(current)
            current_profile = piece_profile(current_text)
            current_weight = beat_weight(current_profile)
            next_weight = beat_weight(profile)

            current_has_real_beat = current_weight >= 2 or current_words >= 12 or len(current) >= 2
            subject_shift = bool(profile["subjects"]) and bool(current_profile["subjects"]) and profile["subjects"] != current_profile["subjects"]
            dialogue_switch = profile["dialogue"] and current_has_real_beat and not current_profile["dialogue"] and current_words >= 10
            location_switch = profile["location_shift"] and current_has_real_beat
            object_switch = profile["object_focus"] and current_has_real_beat and (
                current_profile["action_beat"] or current_profile["dialogue"] or current_profile["emotional_beat"]
            )
            reaction_switch = profile["emotional_beat"] and current_has_real_beat and not current_profile["emotional_beat"] and current_words >= 12
            action_switch = profile["action_beat"] and current_has_real_beat and (
                current_profile["action_beat"] or current_profile["dialogue"] or current_profile["object_focus"]
            )
            transition_switch = profile["transition"] and current_has_real_beat and current_words >= 14
            beat_density_split = current_has_real_beat and next_weight >= 4 and current_weight >= 4 and current_words >= 16
            too_long = current_words + words > hard_limit_words or len(current) >= 3

            if (
                too_long
                or subject_shift
                or dialogue_switch
                or location_switch
                or object_switch
                or reaction_switch
                or action_switch
                or transition_switch
                or beat_density_split
            ):
                groups.append(current_text)
                current = [piece]
                current_words = words
                continue

        current.append(piece)
        current_words += words

    if current:
        groups.append(" ".join(current))

    effective_max = max_scenes

    if effective_max > 0:
        while len(groups) > effective_max:
            merge_index = None
            merge_size = None
            for index in range(len(groups) - 1):
                left_profile = piece_profile(groups[index])
                right_profile = piece_profile(groups[index + 1])
                if left_profile["heading"] or right_profile["heading"]:
                    continue
                if beat_weight(left_profile) >= 5 and beat_weight(right_profile) >= 5 and (left_profile["location_shift"] or right_profile["location_shift"] or left_profile["subjects"] != right_profile["subjects"]):
                    continue
                size = len(re.findall(r"\S+", groups[index])) + len(re.findall(r"\S+", groups[index + 1]))
                if merge_size is None or size < merge_size:
                    merge_index = index
                    merge_size = size
            if merge_index is None:
                break
            groups[merge_index : merge_index + 2] = [groups[merge_index] + " " + groups[merge_index + 1]]

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

def has_dialogue_signals(text):
    return any(mark in text for mark in ['"', "“", "”", "‘", "’"]) or has_any(normalize_vi(text), ["noi", "hoi", "dap", "quat", "thot", "gioi thieu"])


def classify_primary_scene_beat(narration):
    plain = normalize_vi(narration)
    if has_any(plain, ["anh den xe trang loa", "nga tu mua", "tieng phanh", "dien thoai tren mat duong"]):
        return "memory-flashback"
    if has_any(plain, ["mom cho thoi rua cach mat", "ham duoi cua no tach lam hai", "dam thang vao mat no", "lan vao duoi gam xe"]):
        return "predator-threat"
    if has_any(plain, ["ga xam", "tram doi do", "bang gia", "mot gao nuoc", "mot lieu thuoc", "tin mot cau", "bach nhi"]):
        return "market-bargain"
    if has_any(plain, ["radio", "ngan thu", "thu hoi", "tin hieu gen"]):
        return "radio-warning"
    if has_any(plain, ["nuoc chi con mot vach", "khong chia nuoc", "moi nguoi mot ngum", "binh nuoc", "tan da uong thuoc"]):
        return "ration-stop"
    if has_any(plain, ["gieng cu", "mieng gieng", "lon sat treo bang day", "cua kho", "ngoai vach", "vach trang", "bo dao xuong", "tre con vao truoc", "tra gia", "thang nhai duoi gieng"]):
        return "threshold-negotiation"
    if has_any(plain, ["tinh thach", "hat giong", "mau banh", "thit hop", "thuoc", "radio song lai", "moc sat"]):
        return "resource-discovery"
    if has_any(plain, ["mui am", "mui bun", "reu chet", "gio am", "hoi nuoc", "hoi am"]):
        return "water-scent"
    if has_any(plain, ["dau giay", "hoa van tam giac", "quan vai", "vet chan", "vet in trong bui do"]):
        return "track-discovery"
    if has_any(plain, ["vet thuong", "sot", "mo hoi lanh", "bang", "mau", "bi can", "dau den mat toi"]):
        return "medical-strain"
    if has_any(plain, ["duong ray", "duong ray cu", "doi chim xam", "ca doan", "doan nguoi", "di ve phia nam"]) or (has_any(plain, ["xe lan", "truc xe", "vong banh", "cot ket"]) and has_any(plain, ["doc duong", "di ve phia nam", "ca doan", "doan nguoi", "duong ray"])):
        return "journey-column"
    if has_dialogue_signals(narration):
        if has_any(plain, ["khong", "ta", "nguoi", "vi sao", "neu", "bo dao", "vao truoc", "tra gia"]):
            return "group-dialogue"
    if has_any(plain, ["nhan ra", "hieu ra", "quyet dinh", "ngan nguoi", "nho lai", "bat an", "lanh gay"]):
        return "decision-reaction"
    if has_any(plain, ["nap hop", "ban tay", "dao", "cai coi", "binh kim loai", "lop nuoc mong"]):
        return "object-detail"
    return "story-beat"


def infer_narration_location(narration, continuity=None):
    continuity = continuity or {}
    plain = normalize_vi(narration)
    if has_any(plain, ["bai rac", "dong xe phe lieu", "nhat rac", "gam xe", "xe tai lat", "tu lanh gay cua"]):
        return "a filthy radioactive junkyard with scrap heaps, overturned vehicles, and black contaminated dirt"
    if has_any(plain, ["ga xam", "tram doi do", "bang gia", "toa tau bo hoang", "nhanh ray cu", "bach nhi"]):
        return "Gray Station, a harsh rail-junction trading post built from abandoned train cars, scrap walls, and guarded stalls"
    if has_any(plain, ["radio", "ngan thu", "thu hoi", "tin hieu gen"]) and continuity.get("location"):
        return continuity.get("location")
    if has_any(plain, ["khu 17 chay", "lua boc", "khoi den", "mai leu chay", "can leu rach"]):
        return "burning lanes of District 17 with smoke, torn shelters, and fleeing survivors"
    if has_any(plain, ["gan leu", "truoc leu", "ngoai leu", "leu lam tich"]):
        return "the shelter perimeter with a tarp doorway, scrap supports, and wary visitors approaching"
    if has_any(plain, ["cua leu", "trong leu", "goc leu", "leu rach"]):
        return "a poor tarp shelter interior made from torn canvas, patched plastic, and scrap poles"
    if has_any(plain, ["tram loc so 9", "tram loc", "nha may nuoc", "be loc", "duong ong", "ong nuoc", "ong chinh", "tuong sap", "doc be tong", "cong tram"]):
        return "the ruined water-filter station with broken concrete basins, exposed pipes, and the station gate"
    if has_any(plain, ["gieng cu", "mieng gieng", "lon sat treo bang day"]):
        return "the old well area with broken concrete, hanging tin can, and signs someone is already below"
    if has_any(plain, ["cua kho", "nha kho", "kho chua", "vach trang", "ngoai vach", "bo dao xuong"]):
        return "a guarded warehouse threshold or checkpoint where entry terms are being enforced"
    if has_any(plain, ["duong ray", "duong ray cu", "ray gi", "doi chim xam", "ca doan", "doan nguoi", "di ve phia nam"]) or (has_any(plain, ["xe lan", "truc xe", "vong banh", "cot ket"]) and has_any(plain, ["doc duong", "di ve phia nam", "ca doan", "doan nguoi", "duong ray"])):
        return "an old railway line cutting south through ash, red dust, and rusted wasteland debris"
    if has_any(plain, ["toa nha", "nha cao tang", "cao oc", "chung cu", "biet thu", "hanh lang", "sanh", "thang may"]):
        return "the building interior or exterior exactly described by the current narration"
    if has_any(plain, ["duong pho", "ngo hem", "hem", "con pho"]):
        return "the ruined street or alley exactly described by the current narration"
    return continuity.get("location", "story-defined location matching the narration")



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
        (["ga xam", "tram doi do", "bang gia", "nhanh ray cu", "toa tau bo hoang", "bach nhi"], "Gray Station, a brutal trading post assembled from abandoned train cars and scrap walls at a rail junction"),
        (["toa thu nhat", "toa thu hai", "toa thu ba", "toa thu tu", "rem den"], "a cramped station interior where each train car functions as a separate stall, clinic, or hidden room"),
        (["duong ray", "duong ray cu", "doc duong ray"], "an old railway line cutting south through ash, red dust, and rusted wasteland debris"),
        (["xe lan", "truc xe", "vong banh", "cot ket"], "a damaged wheelchair or improvised stretcher carrying an injured survivor"),
        (["doi chim xam", "ca doan", "doan nguoi"], "a wounded survivor column moving together on foot through the wasteland"),
        (["radio", "ngan thu", "thu hoi"], "a battered survival radio carrying fragmented distant transmissions"),
        (["cua leu", "trong leu", "goc leu", "leu rach"], "a poor tarp shelter interior made from torn canvas, patched plastic, wire, and scrap poles"),
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
        (["mom cho thoi rua cach mat"], "Lam Tich opens her eyes to a rotten dog snout hanging terrifyingly close above her face under the rust-red sky"),
        (["ham duoi cua no tach lam hai", "hai hang rang", "luoi cua bi be cong"], "the frame studies the mutant dog's split lower jaw and saw-like crooked teeth at close range"),
        (["thu bien di cap gi", "thich an xac moi chet"], "Lam Tich's fractured memory identifies the creature as a rust-grade two-jawed mutant that feeds on the freshly dead"),
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
        (["khong chia nuoc", "tieu bao khong di noi"], "Di Man halts the column, lowers Tieu Bao, and insists the last water be rationed so the child can keep moving"),
        (["ta cung khong di noi", "nguoi con noi duoc"], "A That jokes weakly through cracked lips while the adults argue over who still has enough strength to keep walking"),
        (["lay binh nuoc ra", "ba vach", "hom qua con hon hai vach"], "Lam Tich takes out the scarred metal bottle and everyone sees how fast the carved water marks have fallen"),
        (["day binh chi con", "lop nuoc mong", "nuoc trong binh khong trong"], "the frame studies the cloudy thin layer of water left at the bottom of the battered metal bottle"),
        (["moi nguoi mot ngum nho", "tan da uong thuoc", "nguoi im"], "Lam Tich takes control of the rationing, assigning each sip while forcing Tan Da to drink for the medicine"),
        (["ta khong uong", "no cua nguoi chua tra xong", "muon chet cung phai xep hang"], "Lam Tich stares Tan Da down and forces him to accept the sip while the others fall silent around them"),
        (["anh uong di", "dua lai bang hai tay", "tra mot mon no moi"], "Tan Da finally takes a tiny sip and returns the bottle with both hands like he is repaying a debt"),
        (["phia truoc co gio am", "huong nao", "ben phai duong ray", "cot dien gay nghieng"], "Ninh signs about damp wind ahead, the group turns, and Lam Tich tests the air toward the leaning power poles"),
        (["nham mat", "tho ngoi", "mui sat gi va tro"], "Lam Tich closes her eyes, breathes in, and separates the first false smell of rust and ash from any trace of hidden moisture"),
        (["nguoi que nhin xe lan", "nhin xe lan phia sau nang"], "the crippled newcomer notices the wheelchair or stretcher behind Lam Tich and reacts with immediate calculation"),
    ]
    for words, phrase in specific_rules:
        if has_any(plain, words):
            add_unique(actions, phrase)

    sequence_rules = [
        (["cam chai nuoc", "cam nuoc", "cam nap hop", "nang nap hop"], "a hand reaches for the water container"),
        (["mo nap", "bat nap", "go nap"], "the container cap or lid is opened"),
        (["dua len moi", "dua ben moi"], "the opened water is raised toward the lips"),
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
    ]
    for words, phrase in sequence_rules:
        if has_any(plain, words):
            add_unique(actions, phrase)

    if not actions:
        focus = scene_state.get("focus", "")
        if focus == "journey-column":
            actions = ["show the wounded survivor column dragging itself south along the old railway line with the wheelchair and group strain clearly readable"]
        elif focus == "radio-warning":
            actions = ["show the group reacting to a battered radio transmission in the exact current location described by the narration"]
        elif focus == "ration-stop":
            actions = ["show the group stopping briefly to ration the last water, with each person\'s need and tension visible in the current story location"]
        elif focus == "water-scent":
            actions = ["show the scouts testing the damp smell in the air and realizing it may lead to water or a trap in this exact place"]
        elif focus == "track-discovery":
            actions = ["show the scout dropping low and pointing out the faint tracks or trace marks exactly described by the narration"]
        elif focus == "well-discovery":
            actions = ["show the old well revealed behind broken concrete, with the hanging tin can implying someone is already below"]
        elif focus == "survival-introduction":
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
        "location": infer_narration_location(narration, continuity),
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
    elif has_any(plain, ["liem mau tren tay", "liem tay minh", "mom cho thoi rua", "ham duoi cua no tach lam hai", "thu bien di cap gi"]):
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
    primary_beat = classify_primary_scene_beat(narration)
    if state["focus"] == "interaction" and primary_beat == "market-bargain":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "market-bargain"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "radio-warning":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "radio-warning"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "ration-stop":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "ration-stop"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "water-scent":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "water-scent"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "track-discovery":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "track-discovery"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "threshold-negotiation":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "threshold-negotiation"
        state["threat"] = "high"
    elif state["focus"] == "interaction" and primary_beat == "resource-discovery":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "resource-discovery"
        state["threat"] = continuity.get("threat", "medium")
    elif state["focus"] == "interaction" and primary_beat == "medical-strain":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "medical-strain"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "group-dialogue":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "group-dialogue"
        state["threat"] = continuity.get("threat", "medium")
    elif state["focus"] == "interaction" and primary_beat == "decision-reaction":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "decision-reaction"
    elif state["focus"] == "interaction" and primary_beat == "object-detail":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "object-detail"
    elif state["focus"] == "interaction" and has_any(plain, ["gieng cu", "mieng gieng", "lon sat treo bang day"]):
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "well-discovery"
        state["threat"] = "high"
    elif state["focus"] == "interaction" and (has_any(plain, ["duong ray", "duong ray cu", "doi chim xam", "ca doan", "doan nguoi", "di ve phia nam"]) or (has_any(plain, ["xe lan", "truc xe", "vong banh", "cot ket"]) and has_any(plain, ["doc duong", "di ve phia nam", "ca doan", "doan nguoi", "duong ray"]))):
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "journey-column"
        state["threat"] = "medium"
        state["lam_tich_position"] = "moving with the survivor column beside the wheelchair or among the group"
        state["tan_da_position"] = "seated in the damaged wheelchair if present in the narration"
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
    mentions = extract_character_mentions(narration)
    mention_labels = [item[1] for item in mentions if item[1] not in {"the monster or mutant beast in the narration"}]
    if len(mention_labels) >= 2:
        return " and ".join(mention_labels[:2])
    if len(mention_labels) == 1:
        return mention_labels[0]
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


def subject_prompt_label(subject):
    if not subject:
        return ""
    if " and " in subject:
        return " and ".join(character_visual_descriptor(part.strip()) for part in subject.split(" and "))
    return character_visual_descriptor(subject)


LOCATION_ANCHOR_TOKENS = [
    "shelter", "junkyard", "railway", "track", "station", "warehouse", "well", "lobby",
    "corridor", "room", "building", "gate", "threshold", "city wall", "district 17",
    "burning lanes", "train car", "checkpoint", "interior", "exterior",
]


def keep_continuity_anchor(item):
    plain = normalize_vi(item)
    if not plain:
        return False
    if "district 17 wasteland survival setting" in item.lower():
        return True
    if any(token in plain for token in [
        "lam tich", "tan da", "ninh", "tieu mai", "tieu ngo", "tieu bao", "a that", "a muc",
        "di man", "bach nhi", "thiet oa", "moc sanh", "la kieu", "hau seo", "child survivor",
        "young male scavenger", "older wasteland woman", "adult male trader", "survivor group",
    ]):
        return True
    if any(token in plain for token in LOCATION_ANCHOR_TOKENS):
        return False
    return False


def prune_characters_for_scene(characters, scene_center, scene_state, narration):
    plain = normalize_vi(narration)
    center_subject = normalize_vi(scene_center.get("subject", ""))
    kind = scene_center.get("kind", "subject-center")
    filtered = []

    if kind == "exchange-center" and has_any(plain, ["viet xau", "doc cham", "khong noi duoc", "khong noi", "bang viet"]):
        preferred = ["ninh", "tieu mai"]
        for item in characters:
            item_plain = normalize_vi(item)
            if any(token in item_plain for token in preferred):
                add_unique(filtered, item)
        return filtered or characters

    if kind == "object-center" and has_any(plain, ["dat len ban", "vien tinh thach", "rang cho hai ham", "tui nho rang cho"]):
        preferred = ["lam tich"]
        for item in characters:
            item_plain = normalize_vi(item)
            if any(token in item_plain for token in preferred):
                add_unique(filtered, item)
        return filtered or characters

    if kind in {"object-center", "reaction-center"} and center_subject:
        subject_tokens = [part.strip() for part in center_subject.split(" and ") if part.strip()]
        for item in characters:
            item_plain = normalize_vi(item)
            if any(token in item_plain for token in subject_tokens):
                add_unique(filtered, item)
        return filtered or characters

    return characters


def infer_primary_object(props, narration):
    if props:
        return props[0]
    return ""


def clean_story_fragment(text, limit=180):
    text = str(text or "").strip()
    text = re.sub(r"(?mi)^\s*##\s*ch(?:u|ư)ong\b.*$", "", text).strip()
    text = text.replace("literal story beat from the current narration:", "").strip()
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def infer_scene_center(narration, scene_state, actions, props, shot_type):
    plain = normalize_vi(narration)
    focus = scene_state.get("focus", "interaction")
    subject = infer_primary_subject(narration, scene_state)
    location = scene_state.get("location", "story-defined location matching the narration")
    action = clean_story_fragment(actions[0] if actions else infer_beat_goal(narration, scene_state, actions, props))
    obj = infer_primary_object(props, narration)
    kind = "subject-center"

    if focus in {"well-discovery", "resource-discovery", "track-discovery", "object-detail", "water-detail"}:
        kind = "object-center"
    elif focus in {"market-bargain", "threshold-negotiation", "group-dialogue"}:
        kind = "exchange-center"
    elif focus in {"journey-column", "radio-warning", "ration-stop", "doorway-threat", "ash-bluff", "dog-attack", "dog-pack", "medical-strain"}:
        kind = "action-center"
    elif focus in {"decision-reaction", "tan-da-condition", "aftermath", "memory-flashback", "bitter-realization"}:
        kind = "reaction-center"
    elif "wide" in shot_type or "establishing" in shot_type or focus in {"survival-introduction", "location-transition", "mass-chaos"}:
        kind = "location-center"

    if has_any(plain, ["gieng cu", "mieng gieng", "lon sat treo bang day", "mui dong"]):
        obj = "the old well mouth, hanging tin can, or hidden water source described in the narration"
        kind = "object-center"
    elif has_any(plain, ["bang viet", "tam bang", "viet len bang"]):
        obj = "Ninh's small writing board with the exact message or gesture described in the narration"
        kind = "object-center"
    elif kind == "exchange-center" and has_any(plain, ["viet xau", "doc cham", "khong noi duoc", "khong noi"]):
        obj = "Ninh's writing board as the object the others are reacting to"
    elif kind == "exchange-center" and has_any(plain, ["bang gia", "tra gia", "mot gao nuoc", "mot lieu thuoc"]):
        obj = "the trade board, ration terms, or goods being negotiated in the scene"
    elif kind == "exchange-center" and has_any(plain, ["dua nuoc", "gao nuoc", "nuoc trong", "thay day"]):
        obj = "the clean water or ladle being offered, withheld, or inspected in the current exchange"
    elif kind == "exchange-center" and has_any(plain, ["toa thu nhat", "ban nuoc loc", "qua may cu", "bach nhi dua ho vao trong"]):
        obj = "the first Gray Station stall or train-car counter being shown to the newcomers"
    elif has_any(plain, ["vien tinh thach", "rang cho hai ham", "dat len ban", "tui nho rang cho"]):
        obj = "the crystals, cracked stones, or bag of mutant teeth being placed on the table for trade"
        kind = "object-center"
    elif has_any(plain, ["radio", "ngan thu", "thu hoi", "tin hieu gen"]):
        obj = "the battered survival radio carrying the exact warning or message from the narration"
    elif has_any(plain, ["xe lan", "truc xe", "vong banh", "cot ket"]):
        obj = "the damaged wheelchair or improvised transport carrying the injured person"
    elif has_any(plain, ["dau giay", "vet chan", "hoa van tam giac", "quan vai"]):
        obj = "the exact footprints, cloth mark, or track clue the narration describes"
        kind = "object-center"
    elif has_any(plain, ["mui am", "vung nuoc doc", "mot vach nuoc", "bo qua bat cu mui am nao"]):
        obj = "the faint damp-air clue or possible poisoned water source the group is deciding whether to trust"
        kind = "object-center"
    elif kind == "object-center" and not obj:
        obj = "the exact object, proof, or survival clue described in the current narration"

    return {
        "kind": kind,
        "subject": subject,
        "object": obj,
        "action": action,
        "location": location,
    }


def prioritize_visual_elements(characters, setting, actions, props, center):
    must_show = []
    kind = center.get("kind", "subject-center")
    subject = center.get("subject", "")
    obj = center.get("object", "")
    action = center.get("action", "")
    location = center.get("location", "")

    priority_groups = []
    if kind == "object-center":
        priority_groups = [[obj], [subject], [action], [location]]
    elif kind == "exchange-center":
        priority_groups = [[subject], [action], [obj], [location]]
    elif kind == "location-center":
        priority_groups = [[location], [subject], [action], [obj]]
    elif kind == "reaction-center":
        priority_groups = [[subject], [action], [location], [obj]]
    else:
        priority_groups = [[subject], [action], [location], [obj]]

    for group in priority_groups:
        for item in group:
            add_unique(must_show, item)
    for source in (characters, setting, actions, props):
        for item in source:
            add_unique(must_show, item)
    return must_show[:8]


def scene_beat_metadata(narration, scene_state, actions, setting, props, continuity=None):
    continuity = continuity or {}
    scene_center = infer_scene_center(
        narration,
        scene_state,
        actions,
        props,
        shot_type_for(narration, 0),
    )
    return {
        "beat_type": scene_state.get("focus", "interaction"),
        "beat_goal": infer_beat_goal(narration, scene_state, actions, props),
        "beat_subject": infer_primary_subject(narration, scene_state),
        "beat_object": infer_primary_object(props, narration),
        "beat_location": setting[0] if setting else scene_state.get("location", ""),
        "audio_anchor_lines": audio_anchor_lines(narration, limit=3),
        "transition_from_previous": continuity.get("last_action", "none"),
        "scene_center_kind": scene_center.get("kind", "subject-center"),
        "scene_center_subject": scene_center.get("subject", ""),
        "scene_center_object": scene_center.get("object", ""),
        "scene_center_action": scene_center.get("action", ""),
        "scene_center_location": scene_center.get("location", ""),
    }


def infer_scene_role(narration, scene_state, actions, props, shot_type):
    plain = normalize_vi(narration)
    focus = scene_state.get("focus", "")
    if "insert" in shot_type or ("close" in shot_type and props and not actions):
        return "insert"
    if has_any(plain, ["dam dong", "nguoi dan", "nhung nguoi xung quanh", "dam cuop", "nhieu nguoi"]):
        return "crowd-reaction"
    if focus in {"mass-chaos", "dog-attack", "dog-pack"} or "action" in shot_type or "threat" in shot_type:
        return "action"
    if focus in {"memory-flashback", "rebirth-junkyard", "bitter-realization"}:
        return "reveal"
    if has_any(plain, ["nhan ra", "hieu ra", "quyet dinh", "do du", "nho lai"]):
        return "decision-reaction"
    if has_any(plain, ["qua cong", "vao sanh", "cho thang may", "vao phong", "mo cua", "buoc vao"]):
        return "movement-step"
    if props:
        return "proof-object"
    if has_any(plain, ["noi", "hoi", "dap", "\"", "“", "‘"]):
        return "dialogue"
    if "wide" in shot_type or "establishing" in shot_type:
        return "establishing"
    return "story-beat"


def thumbnail_hook_score(narration, scene_role, props):
    plain = normalize_vi(narration)
    score = 0
    if scene_role in {"reveal", "decision-reaction", "proof-object", "crowd-reaction"}:
        score += 2
    if has_any(plain, ["khong phai", "hoa ra", "that ra", "cuoi cung", "quyet khong", "biet khong", "bong"]):
        score += 2
    if has_any(plain, ["dam dong", "nguoi dan", "truong thon", "hau seo", "la kieu"]):
        score += 1
    if props:
        score += 1
    return min(score, 5)


def shot_type_for(narration, scene_index):
    lower = narration.lower()
    plain = normalize_vi(narration)
    primary_beat = classify_primary_scene_beat(narration)
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
    if has_any(plain, ["khu 17 chay", "lua boc", "khoi den", "gao thet", "bo chay", "mai leu chay", "chay ruc", "can leu rach"]):
        return "wide or medium survival action shot with burning shelters, fleeing survivors, and attack direction readable"
    if primary_beat == "market-bargain":
        return "market exchange shot with seller, visitors, trade goods, and power balance clearly readable"
    if primary_beat == "radio-warning":
        return "tense radio-listening shot with the moving group reacting to the transmission"
    if primary_beat == "ration-stop":
        return "ration-stop shot with the last water, the group gathered close, and social tension clearly readable"
    if primary_beat == "water-scent":
        return "close reaction shot as the scouts catch the smell of hidden moisture and test whether it is real water or poison"
    if primary_beat == "track-discovery":
        return "ground-tracking insert shot focused on the exact tracks or trace marks described in the narration"
    if has_any(plain, ["gieng cu", "mieng gieng", "mui dong", "lon sat treo bang day"]):
        return "well discovery shot showing the well mouth, hanging tin can, scout reaction, and the hidden danger around the water source"
    if primary_beat == "threshold-negotiation":
        return "guarded threshold shot with both sides of the negotiation and the barrier or water access point clearly readable"
    if primary_beat == "resource-discovery":
        return "discovery shot with the newly found object, location context, and the first reaction clearly readable"
    if primary_beat == "medical-strain":
        return "close survival-detail shot focused on pain, bandages, wounds, and the body cost of continuing"
    if primary_beat == "group-dialogue":
        return "dialogue beat shot with the current speaker, listener, and the emotional exchange clearly readable"
    if primary_beat == "decision-reaction":
        return "close or medium reaction shot centered on the choice or realization changing the next move"
    if primary_beat == "object-detail":
        return "close survival-detail shot focused on the named object and why it matters right now"
    if has_any(plain, ["gieng cu", "mieng gieng", "lon sat treo bang day"]):
        return "discovery shot revealing the old well, hanging tin can, and the danger that someone may already be below"
    if has_any(plain, ["xe lan", "truc xe", "vong banh", "cot ket"]) and not has_any(plain, ["duong ray", "duong ray cu", "doi chim xam", "ca doan", "doan nguoi", "di ve phia nam"]):
        return "injured transport shot with the wheelchair or stretcher and the nearby characters' strain clearly readable"
    if has_any(plain, ["duong ray", "duong ray cu", "ray gi", "doi chim xam", "ca doan", "doan nguoi", "di ve phia nam"]) or (has_any(plain, ["xe lan", "truc xe", "vong banh", "cot ket"]) and has_any(plain, ["doc duong", "di ve phia nam", "ca doan", "doan nguoi", "duong ray"])):
        return "journey shot on the old railway line with group movement, wheelchair, and survival strain clearly readable"
    if has_any(plain, ["nap hop", "hai ngum", "than loc", "nuoc sach", "nuoc vang nhat", "mui ri sat trong nap"]):
        return "close insert shot on water, metal lid, dirty cloth filter, and trembling hands"
    if has_any(plain, ["nguoi han nong", "sot cao", "gen sup do", "vet thuong bung", "nua than duoi", "khong the nhuc nhich"]):
        return "medium single on Tan Da in the shelter corner with illness and wound clearly readable"
    if has_any(plain, ["dua nap hop", "dua binh nuoc", "ben moi", "anh uong di", "nhuong nuoc", "dua lai bang hai tay"]):
        return "intimate medium two-shot focused on the exchange of water between Lam Tich and Tan Da"
    if has_any(plain, ["ngoai cua leu", "qua khe ton", "bong nguoi", "hau seo", "tieng buoc chan", "mo cua"]):
        return "doorway tension shot with Lam Tich inside and threatening silhouettes outside"
    if has_any(plain, ["keo thung", "dap nghieng", "tro xam", "nam do"]):
        return "action shot at the shelter entrance as ash spills outward and everyone reacts"
    if has_any(plain, ["di xa", "quay dau", "ngoi xuong canh han", "dem nay ta co the sot lan hai"]):
        return "quiet aftermath two-shot inside the shelter with danger lingering after the footsteps leave"
    if has_dialogue_signals(narration):
        return "dialogue beat shot with the current speaker, listener, and the emotional exchange clearly readable"
    if has_any(plain, ["nhin", "quay mat", "ngung lai", "lang nghe", "nuot nuoc bot", "bat an", "im lang", "dong cung", "nheo mat"]):
        return "close or medium reaction shot centered on the current emotional beat and what the character notices"
    if has_any(plain, ["di vong qua", "dat dao xuong", "mo cua", "keo", "day", "bo vao", "dung truoc", "ngoi xom"]):
        return "medium movement-action shot with the body action and spatial relationship clearly readable"
    if scene_index == 1 or has_any(lower, ["báº§u trá»i", "xa xa", "bá»©c tÆ°á»ng khá»•ng lá»“", "thÃ nh an toÃ n"]):
        return "wide establishing shot showing place and scale"
    if has_any(lower, ["thá»‹t há»™p", "káº¹o", "tinh tháº¡ch", "cÃ²i", "dao", "than lá»c", "váº¿t thÆ°Æ¡ng"]):
        return "close survival-detail shot focused on hands, props, and immediate stakes"
    if has_any(lower, ["gáº§m xe", "trá»‘n", "nÃ­n thá»Ÿ"]):
        return "low claustrophobic point-of-view shot from cover"
    if has_any(lower, ["chÃ³", "thÃº", "gáº§m gá»«", "mÃ³ng vuá»‘t", "xÃ¡c"]):
        return "medium tense action shot with predator, victim, and survivor positions readable"
    return "story-accurate cinematic shot focused on the main narrated subject, action, and setting"


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

    mentions = extract_character_mentions(narration)
    mention_keys = {item[0] for item in mentions}
    for _, _, visual_ref in mentions:
        add_unique(characters, visual_ref)
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
        (["nap hop", "hai ngum", "nuoc sach"], props, "small metal can lid holding the last two sips of yellowish filtered water"),
        (["vang nhat", "bui than", "than loc", "mui ri sat trong nap"], props, "murky yellow water with charcoal dust and rusty metallic residue"),
        (["vet thuong bung", "mau van tham", "gen sup do"], props, "dirty abdominal bandage with dark stains and faint toxic veins under the skin"),
        (["tieng buoc chan", "bong nguoi", "hau seo"], props, "door gap, torn cloth curtain, and hostile silhouettes outside"),
        (["keo thung", "tro xam", "nam do"], props, "rusted ash bucket filled with stove ash and bone dust"),
        (["cam dao", "con dao gay"], props, "broken survival knife hidden in Lam Tich's hand"),
        (["coi den", "cai coi"], props, "small dark whistle"),
        (["mom cho thoi rua", "ham duoi cua no tach lam hai", "thu bien di cap gi"], props, "a mutated two-jawed dog with a split lower jaw, rotten muzzle, yellow foam, and saw-like crooked teeth"),
        (["cai xac bi bay cho gam", "nguoi dan ong mac ao khoac chien thuat mau den"], props, "a mauled man's corpse in torn black tactical clothing"),
        (["xe tai lat", "gam xe"], props, "an overturned truck that serves as desperate cover"),
        (["manh kinh vo"], props, "a shard of broken glass in Lam Tich's hand"),
        (["thanh sat cong"], props, "a bent iron bar scavenged from the junk pile"),
        (["thit hop", "hop thit"], props, "a sealed can of meat hidden in the corpse's inner pocket"),
        (["bang viet", "tam bang", "viet len bang"], props, "Ninh's small writing board, readable as the object carrying his message"),
        (["lon sat treo bang day", "mieng gieng", "gieng cu"], props, "the old well mouth and hanging tin can"),
        (["bang gia", "tra gia", "mot gao nuoc", "mot lieu thuoc"], props, "the trade board, ration terms, or goods being exchanged"),
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
    elif focus == "market-bargain":
        mood = ["cold barter logic, price pressure, and social danger behind polite trade"]
    elif focus == "journey-column":
        mood = ["exhaustion, pain, and hard forward movement through smoke and ash"]
    elif focus == "radio-warning":
        mood = ["tension, dread, and everyone listening for survival information"]
    elif focus == "ration-stop":
        mood = ["fatigue, thirst, and social pressure around the last water"]
    elif focus == "water-scent":
        mood = ["cautious hope, suspicion, and scouting tension around possible water"]
    elif focus == "track-discovery":
        mood = ["alertness and caution as the scouts realize someone else reached the area first"]
    elif focus == "market-bargain":
        mood = ["cold barter logic, controlled smiles, and danger hidden inside trade etiquette"]
    elif focus == "well-discovery":
        mood = ["discovery, danger, and the sense that an unseen person may already control the water source"]
    elif focus == "water-detail":
        characters = [LAM_TICH_VISUAL]
        mood = ["thirst, hesitation, and fragile survival calculation"]
    elif focus == "tan-da-condition":
        characters = [TAN_DA_VISUAL]
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
    elif has_any(plain, ["dua nap hop", "dua binh nuoc", "anh uong di", "nhuong nuoc", "dua lai bang hai tay"]):
        mood = ["intimate survival trust under exhaustion"]

    actions, handoff = story_action_sequence(narration, scene_state, continuity)
    mood = mood or ["tense cinematic survival mood"]

    for prop in scene_state.get("prop_focus", []):
        add_unique(props, prop)

    scene_center = infer_scene_center(narration, scene_state, actions, props, shot_type)
    characters = prune_characters_for_scene(characters, scene_center, scene_state, narration)
    must_show = prioritize_visual_elements(characters, setting, actions, props, scene_center)

    reference_recipe = "Use the approved sample only as face identity and clothing-material reference, never as a fixed composition, repeated pose, repeated location, or repeated body blocking"
    scene_state_parts = [f"location={scene_state['location']}", f"threat={scene_state['threat']}"]
    if any("Lam Tich" in item for item in characters):
        scene_state_parts.append(f"Lam Tich position={scene_state['lam_tich_position']}")
    if any("Tan Da" in item for item in characters) and scene_state.get("tan_da_position"):
        scene_state_parts.append(f"Tan Da position={scene_state['tan_da_position']}")
    if scene_state.get("door_state") and "door" in scene_state["location"]:
        scene_state_parts.append(f"door state={scene_state['door_state']}")
    beat_meta = scene_beat_metadata(narration, scene_state, actions, setting, props, continuity)
    scene_role = infer_scene_role(narration, scene_state, actions, props, shot_type)
    hook_score = thumbnail_hook_score(narration, scene_role, props)
    setting_text = ", ".join(setting[:3]) if setting else scene_state["location"]
    action_text = ", ".join(actions[:3]) if actions else beat_meta["beat_goal"]
    prop_text = ", ".join(props[:3]) if props else "only the props named by the narration"
    continuity_anchors = [item for item in (continuity.get("anchors") or []) if keep_continuity_anchor(item)]
    anchors_text = ", ".join(continuity_anchors[:3]) if continuity_anchors else "keep identity and world continuity only"
    scene_excerpt = " / ".join(audio_anchor_lines(narration, limit=2)) or compact[:180]
    prompt = (
        "Cinematic realistic wasteland story frame, current narration is the source of truth. "
        f"Show this exact beat: {beat_meta['beat_goal']}. "
        f"Scene center: {scene_center['kind']} centered on {scene_center['subject'] or 'the current narrated subject'}"
        f"{'; central object: ' + scene_center['object'] if scene_center['object'] else ''}. "
        f"Visible action now: {scene_center['action']}. "
        f"Primary subject: {subject_prompt_label(beat_meta['beat_subject'])}. "
        f"Setting: {scene_center['location'] or setting_text}. "
        f"Shot: {shot_type}. "
        f"Props that must read clearly: {prop_text}. "
        f"Carry over only this continuity from the previous scene: {handoff}; anchors: {anchors_text}. "
        "Do not reset to a generic pose or repeated shelter composition. "
        "Environment must follow the exact story description, and movement scenes must show the correct current step in the sequence. "
        f"{GENDER_CLARITY_RULE} "
        f"{LAM_TICH_FACE_RULE} "
        f"{TAN_DA_FACE_RULE} "
        f"{YOUTUBE_SAFE_VISUAL_RULE} "
        f"{reference_recipe}. "
        f"Mood: {', '.join(mood[:2])}. "
        f"Story excerpt: {scene_excerpt}. "
        f"{style}"
    )
    return {
        "prompt": prompt,
        "characters": characters,
        "must_show": must_show,
        "setting": setting,
        "actions": actions,
        "props": props,
        "shot_type": shot_type,
        "scene_center": scene_center,
        "scene_state": scene_state,
        "beat_meta": beat_meta,
        "scene_role": scene_role,
        "thumbnail_hook_score": hook_score,
    }


def update_visual_continuity(previous, visual):
    anchors = []
    for item in previous.get("anchors") or []:
        if keep_continuity_anchor(item):
            add_unique(anchors, item)
    for item in visual.get("characters") or []:
        if keep_continuity_anchor(item):
            add_unique(anchors, item)
    add_unique(anchors, "District 17 wasteland survival setting")
    anchors = anchors[-4:]
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
        if re.search(r"(?mi)^\s*##\s*ch(?:u|ư)ong\b", narration):
            continuity = {
                "summary": "chapter transition: reset location continuity and follow the new narration literally",
                "anchors": continuity.get("anchors", [])[-2:],
                "last_action": "none",
                "location": "story-defined location matching the narration",
                "threat": "low",
                "lam_tich_position": "position defined by the current narration",
                "tan_da_position": "",
                "door_state": "",
            }
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
                "scene_role": visual.get("scene_role", "story-beat"),
                "thumbnail_hook_score": visual.get("thumbnail_hook_score", 0),
                "beat_type": beat_meta.get("beat_type", "interaction"),
                "beat_goal": beat_meta.get("beat_goal", ""),
                "beat_subject": beat_meta.get("beat_subject", ""),
                "beat_object": beat_meta.get("beat_object", ""),
                "beat_location": beat_meta.get("beat_location", ""),
                "scene_center_kind": beat_meta.get("scene_center_kind", "subject-center"),
                "scene_center_subject": beat_meta.get("scene_center_subject", ""),
                "scene_center_object": beat_meta.get("scene_center_object", ""),
                "scene_center_action": beat_meta.get("scene_center_action", ""),
                "scene_center_location": beat_meta.get("scene_center_location", ""),
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


