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
    "explicit underboob, explicit sideboob, cleavage focus, lingerie, two-piece bikini, string bikini, triangle bikini, bikini bottom, swimsuit bottom, swimwear, underwear, panties, thong, bra and panties set, matching underwear set, "
    "see-through clothing, wet revealing clothing, erotic pose, seductive pose, reclining pin-up pose, spread legs, "
    "sexualized body, sexualized minor, childlike body, teen girl, underage, fetish, voyeuristic framing, "
    "focal point on breasts, focal point on buttocks, focal point on crotch, torso glamour shot, waist fetish framing, "
    "open jacket with breasts exposed, open shirt with breasts exposed, wardrobe malfunction, boudoir, fetish glamour pose, "
    "androgynous face, gender ambiguous face, masculine woman, feminine man, gender swap, woman with male facial structure, man with feminine facial structure, square male jaw on woman, heavy masculine brow on woman"
)

GENDER_CLARITY_RULE = (
    "Gender clarity rule: the word woman means a clearly adult female character with unmistakably feminine face, soft female facial structure, delicate jawline, balanced feminine eyes nose and mouth, and feminine body language; "
    "the word man means a clearly adult male character with masculine face, broad masculine body language, and wasteland toughness; "
    "maintain consistent character identity and body language from scene to scene; "
    "avoid random identity drift or face-swapping between scenes. "
    "Female sexy styling applies only to adult women such as Lam Tich; male characters must never inherit Lam Tich's sports-bikini-style top, crop top, bare-midriff clothing, short shorts, or feminine glamour outfit."
)

STORY_FIRST_VISUAL_RULE = (
    "Story-first visual rule: the narration beat is more important than posing or attractiveness; show the exact current action, prop, location, danger, injury, bargain, travel step, rationing, or reaction described by the story. "
    "Do not turn survival, injury, danger, travel, or group scenes into glamour posing, pin-up posing, hero posing, fashion posing, or a generic standing portrait. "
    "Attractive styling is allowed only when it supports the current story beat and must never replace the narrated action."
)

LAM_TICH_VISUAL = (
    "Lam Tich, a beautiful young Asian wasteland scavenger woman with an unmistakably feminine face, soft delicate female facial structure, no masculine jaw, no heavy male brow, tired expressive eyes, cracked lips, "
    "short black hair worn rough from survival, slim toned build, grounded sensuality without glamour posing, "
    "practical summer wasteland clothing with bare arms and readable legs: a weathered athletic survival crop top or thick-strap sports-bikini-style top, top only, under torn scavenger layers, paired with rugged short shorts or torn utility shorts, "
    "sporty and sexy but never a two-piece bikini, never bikini bottoms, never panties, never swimwear bottoms; when the story beat calls for charm, confidence, temptation, intimacy, or a character spotlight, let her read visibly seductive and glamorous in a grounded wasteland way, subtle wasteland pin-up energy without explicit fetish framing, "
    "stubborn survival dignity, attractive in a believable human way"
)

YOUTUBE_SAFE_VISUAL_RULE = (
    "YouTube-safe visual rule: practical survival clothing may expose arms, legs, shoulders, and some upper chest when the character design calls for it, "
    "but nipples, areola, buttocks, and crotch must always stay covered by fabric. "
    "No nudity, no exposed breasts, and no shot that treats the chest, buttocks, or crotch as the visual focus."
)

LAM_TICH_FACE_RULE = (
    "When Lam Tich is the scene focus, make her face readable, emotionally clear, and obviously feminine: soft feminine jawline, no square male jaw, no masculine brow ridge, expressive eyes, readable nose and mouth, "
    "short black hair not hiding the whole face, tired but memorable survival presence, no tiny unreadable face, "
    "beautiful and feminine in a grounded wasteland way, never a studio beauty-portrait."
)

TAN_DA_VISUAL = (
    "Tan Da, a tall muscular Asian male survivor with a handsome upright face, strong brows, steady alert eyes, weathered jawline, "
    "broad shoulders, powerful build, rugged masculine wasteland clothing: worn dark tactical coat or heavy scavenger jacket, layered practical shirt, long practical pants, boots, belts, straps, armor scraps, dirty bandages at the abdomen only when the narration calls for the wound, "
    "never a sports top, never sports-bikini-style top, never crop top, never bare midriff, never exposed belly fashion, never short shorts, never feminine styling, "
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

VIETNAMESE_MARKS = "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
MOJIBAKE_MARKERS = ["Ã", "Ä", "á»", "áº", "Æ", "Â"]

SUPPORTING_CHARACTER_RULES = [
    ("La Kieu", ["la kieu"], "La Kieu, a dangerous adult wasteland raider leader with a hard face and controlled menace"),
    ("Ninh", ["ninh"], "Ninh, a slight preteen mute boy survivor carrying a writing board, clearly child-sized with a wary hungry face and rough scavenger clothing, never school-uniform styled"),
    ("Tieu Mai", ["tieu mai"], "Tieu Mai, a preteen girl survivor, clearly a child with alert eyes, quick reactions, and rough scavenger clothing, never school-uniform styled"),
    ("Tieu Ngo", ["tieu ngo"], "Tieu Ngo, a wounded boy survivor protecting the younger child while trying not to show pain, clearly child-sized and never school-uniform styled"),
    ("Tieu Bao", ["tieu bao"], "Tieu Bao, a very young child held close by the adults during danger, clearly a little child and never school-uniform styled"),
    ("A That", ["a that"], "A That, a lean young male scavenger with cracked lips, nervous humor, and quick restless movements"),
    ("A Muc", ["a muc"], "A Muc, a guarded teenage scavenger boy with a hook tool and sharp suspicious eyes"),
    ("Di Man", ["di man"], "Di Man, an older wasteland woman with a severe practical face and protective posture toward the children"),
    ("Bach Nhi", ["bach nhi"], "Bach Nhi, a round-faced adult male trader with a polite smile that feels cold and calculating"),
    ("Thiet Oa", ["thiet oa"], "Thiet Oa, a hardened adult scavenger with a hammer and blunt no-nonsense body language"),
    ("Moc Sanh", ["moc sanh"], "Moc Sanh, a young adult woman with machine grease on her face and a guarded weapon-ready stance"),
    ("Lao Phung", ["lao phung"], "Lao Phung, an older male mechanic with callused hands, blunt speech, and practical repair instincts"),
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


def count_vietnamese_marks(text):
    return sum(1 for char in text.lower() if char in VIETNAMESE_MARKS)


def maybe_repair_mojibake(text):
    best = text
    best_score = count_vietnamese_marks(text)
    current = text
    for _ in range(3):
        changed = False
        for source_encoding in ("cp1252", "latin1"):
            try:
                repaired = current.encode(source_encoding, errors="strict").decode("utf-8", errors="strict")
            except Exception:
                continue
            repaired_score = count_vietnamese_marks(repaired)
            if repaired_score > best_score:
                best = repaired
                best_score = repaired_score
                current = repaired
                changed = True
                break
        if not changed:
            break
    return best


def read_source(path):
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig", errors="strict")
    if sum(text.count(token) for token in MOJIBAKE_MARKERS) >= 3:
        text = maybe_repair_mojibake(text)
    text = unicodedata.normalize("NFC", text).replace("\ufeff", "")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    vietnamese_marks = count_vietnamese_marks(text)
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
        parts = re.split(r'(?<=[.!?。！？])(?:["”’\'])?\s+', paragraph)
        pieces.extend(part.strip() for part in parts if part.strip())
    return pieces


def split_story_units(text):
    raw_paragraphs = []
    for raw_paragraph in re.split(r"\n+", text):
        paragraph = raw_paragraph.strip()
        if not paragraph:
            continue
        raw_paragraphs.append(paragraph)

    clustered_paragraphs = []
    cluster = []
    cluster_words = 0
    for paragraph in raw_paragraphs:
        if paragraph.startswith("#"):
            if cluster:
                clustered_paragraphs.append(" ".join(cluster).strip())
                cluster = []
                cluster_words = 0
            clustered_paragraphs.append(paragraph)
            continue
        plain = normalize_vi(paragraph)
        words = len(re.findall(r"\S+", paragraph))
        profile = piece_profile(paragraph)
        standalone_break = (
            profile["location_shift"]
            or profile["named_object"]
            or profile["focus_tag"] in {
                "route-planning",
                "market-bargain",
                "threshold-negotiation",
                "board-exchange",
                "human-valuation",
                "insect-combat",
                "hazard-crossing",
                "authority-introduction",
                "camp-rules-recital",
                "law-recital",
            }
        )
        short_bridge_paragraph = (
            words <= 14
            and (
                profile["dialogue"]
                or profile["emotional_beat"]
                or profile["question"]
                or profile["command_like"]
                or has_any(plain, ["nhin", "liec", "nghe", "ngui", "gat dau", "lac dau", "quay mat", "quay dau"])
            )
            and not standalone_break
        )
        if not cluster:
            cluster = [paragraph]
            cluster_words = words
            continue
        cluster_text = " ".join(cluster).strip()
        cluster_profile = piece_profile(cluster_text)
        cluster_complete = scene_completeness(cluster_profile, cluster_words)
        cluster_focus = cluster_profile["focus_tag"]
        profile_focus = profile["focus_tag"]
        focus_conflict = (
            cluster_focus
            and profile_focus
            and cluster_focus != profile_focus
            and cluster_complete >= 2
            and profile_focus not in {"interaction", "decision-reaction", "object-detail"}
        )
        keep_chain = (
            short_bridge_paragraph
            or (words <= 12 and cluster_complete <= 1 and not standalone_break)
            or (cluster_words <= 20 and words <= 18 and not standalone_break and not focus_conflict)
            or (
                words <= 16
                and profile["dialogue"]
                and cluster_words <= 24
                and cluster_complete <= 2
                and not standalone_break
            )
            or (
                words <= 16
                and has_any(plain, ["nhin", "liec", "nghe", "ngui", "gat dau", "lac dau", "quay mat", "quay dau"])
                and cluster_words <= 28
                and not standalone_break
            )
        )
        if keep_chain and cluster_words + words <= 58:
            cluster.append(paragraph)
            cluster_words += words
        else:
            clustered_paragraphs.append(cluster_text)
            cluster = [paragraph]
            cluster_words = words
    if cluster:
        clustered_paragraphs.append(" ".join(cluster).strip())

    units = []
    for paragraph in clustered_paragraphs:
        if paragraph.startswith("#"):
            continue
        compact = re.sub(r"\s+", " ", paragraph).strip()
        if not compact:
            continue
        # Only keep ultra-short probe dialogue standalone; longer dialogue should
        # flow through the normal beat-chain logic instead of exploding into fragments.
        if (
            compact.startswith(('"', "'", "-", "“", "‘"))
            and len(compact.split()) <= 12
            and (
                "?" in compact
                or compact.endswith(":")
                or has_any(normalize_vi(compact), ["ten?", "duong nao", "co phai", "la ai", "vi sao", "the nao"])
            )
        ):
            units.append(compact)
            continue
        parts = [part.strip() for part in re.split(r'(?<=[.!?。！？…;])(?:["”’\'])?\s+', compact) if part.strip()]
        if not parts:
            continue
        paragraph_units = []
        chain = []
        chain_words = 0
        for part in parts:
            words = len(re.findall(r"\S+", part))
            profile = piece_profile(part)
            plain = normalize_vi(part)
            if not chain:
                chain = [part]
                chain_words = words
                continue
            chain_text = " ".join(chain).strip()
            chain_profile = piece_profile(chain_text)
            chain_complete = scene_completeness(chain_profile, chain_words)
            part_complete = scene_completeness(profile, words)
            strong_focus_break = (
                chain_profile["focus_tag"]
                and profile["focus_tag"]
                and chain_profile["focus_tag"] != profile["focus_tag"]
                and chain_complete >= 2
                and part_complete >= 2
                and profile["focus_tag"] not in {"interaction", "decision-reaction", "object-detail", "group-dialogue"}
            )
            subject_break = (
                bool(chain_profile["subjects"])
                and bool(profile["subjects"])
                and chain_profile["subjects"] != profile["subjects"]
                and chain_complete >= 2
                and part_complete >= 2
            )
            micro_followup = (
                words <= 14
                and (
                    profile["dialogue"]
                    or profile["question"]
                    or profile["command_like"]
                    or profile["emotional_beat"]
                    or has_any(plain, ["nhin", "liec", "nghe", "ngui", "gat dau", "lac dau", "quay mat", "quay dau", "im lang", "tho ra", "nuot", "run tay"])
                )
                and not profile["location_shift"]
            )
            same_subject_chain = bool(chain_profile["subjects"]) and chain_profile["subjects"] == profile["subjects"]
            allow_chain = (
                (chain_complete <= 2 or chain_words <= 20 or micro_followup or same_subject_chain)
                and not strong_focus_break
                and not subject_break
                and not profile["location_shift"]
                and chain_words + words <= 52
            )
            if allow_chain:
                chain.append(part)
                chain_words += words
            else:
                paragraph_units.append(chain_text)
                chain = [part]
                chain_words = words
        if chain:
            paragraph_units.append(" ".join(chain).strip())
        for part in paragraph_units:
            plain = normalize_vi(part)
            is_short_action = len(part.split()) <= 8 and has_any(plain, ACTION_BEAT_VERBS)
            is_short_reaction = len(part.split()) <= 5 and has_any(plain, ["roi", "khung lai", "chet lang", "nho lai", "giat minh"])
            is_micro_bridge_action = (
                len(part.split()) <= 7
                and has_any(plain, ["nhin", "liec", "nghe", "gat dau", "lac dau", "quay mat", "quay dau", "tho ra", "ngap ngung"])
                and not has_any(plain, ["bang viet", "gieng", "radio", "xe lan", "vien tinh thach", "rang cho", "mot gao nuoc", "mot lieu thuoc"])
            )
            if (len(part.split()) <= 6 and not is_short_action and not is_short_reaction and units and not units[-1].startswith("#")) or (
                is_micro_bridge_action and units and not units[-1].startswith("#")
            ):
                units[-1] = f"{units[-1]} {part}".strip()
            else:
                units.append(part)
    merged_units = []
    index = 0
    while index < len(units):
        current = units[index].strip()
        plain_current = normalize_vi(current)
        should_merge_forward = False
        if index + 1 < len(units):
            if current.endswith(":"):
                should_merge_forward = True
            elif len(current.split()) <= 4 and re.fullmatch(r'["“”]?ten\??["“”]?', plain_current):
                should_merge_forward = True
            elif len(current.split()) <= 6 and has_any(plain_current, ["hoi:", "dap:", "noi:", "noi nho:", "quat:", "thot:", "gioi thieu:"]):
                should_merge_forward = True
        if should_merge_forward:
            merged_units.append(f"{current} {units[index + 1].strip()}".strip())
            index += 2
            continue
        merged_units.append(current)
        index += 1
    final_units = []
    index = 0
    while index < len(merged_units):
        current = merged_units[index].strip()
        plain_current = normalize_vi(current)
        short_quoted = (
            len(current.split()) <= 4
            and any(mark in current for mark in ['"', "“", "”"])
        )
        quote_focus = infer_fragment_focus(plain_current)
        quote_is_probe = (
            "?" in current
            or has_any(plain_current, ["ten?", "co phai", "la ai", "duong nao", "vi sao", "the nao"])
        )
        naming_punch = has_any(plain_current, ["ten?", "kho den vang", "hac nha 07"])
        merge_short_quote = short_quoted and (
            quote_is_probe
            or (len(current.split()) <= 2 and not quote_focus)
        )
        if index + 1 < len(merged_units) and (merge_short_quote or naming_punch):
            nxt = merged_units[index + 1].strip()
            final_units.append(f"{current} {nxt}".strip())
            index += 2
            continue
        final_units.append(current)
        index += 1
    compressed_units = []
    for current in final_units:
        current = current.strip()
        if not current:
            continue
        if not compressed_units:
            compressed_units.append(current)
            continue
        profile = piece_profile(current)
        words = len(re.findall(r"\S+", current))
        current_plain = normalize_vi(current)
        short_glance_named_object = (
            words <= 16
            and has_any(current_plain, ["nhin", "liec", "nghe", "ngui", "do", "thu", "xem"])
            and has_any(current_plain, ["xe lan", "tui bot", "hat giong", "bang viet", "radio", "vien tinh thach", "bat nuoc", "binh nuoc", "dao", "vet thuong"])
        )
        terse_dialogue_reply = (
            words <= 6
            and profile["dialogue"]
            and not profile["location_shift"]
            and not profile["named_object"]
        )
        bridge_like = (
            words <= 8
            and not profile["heading"]
            and not profile["location_shift"]
            and (
                profile["dialogue"]
                or profile["emotional_beat"]
                or profile["command_like"]
                or profile["question"]
                or profile["focus_tag"] in {"interaction", "object-detail", "decision-reaction"}
                or has_any(normalize_vi(current), ["nhin", "liec", "gat dau", "lac dau", "quay mat", "quay dau", "liem moi", "im duoc", "mo to mat"])
            )
            and (not profile["named_object"] or short_glance_named_object)
        )
        if not (bridge_like or terse_dialogue_reply or short_glance_named_object):
            compressed_units.append(current)
            continue
        previous = compressed_units[-1]
        previous_profile = piece_profile(previous)
        previous_words = len(re.findall(r"\S+", previous))
        previous_complete = scene_completeness(previous_profile, previous_words)
        previous_plain = normalize_vi(previous)
        repeated_glance_chain = (
            has_any(previous_plain, ["nhin", "liec", "nghe", "ngui"])
            and has_any(current_plain, ["nhin", "liec", "nghe", "ngui"])
            and words <= 16
        )
        combined_words = previous_words + words
        incompatible_focus = (
            previous_profile["focus_tag"]
            and profile["focus_tag"]
            and previous_profile["focus_tag"] != profile["focus_tag"]
            and previous_complete >= 2
            and profile["focus_tag"] not in {"interaction", "object-detail", "decision-reaction"}
        )
        allowed_combined_words = 46 if terse_dialogue_reply else 38
        if (
            not previous_profile["heading"]
            and combined_words <= allowed_combined_words
            and (not incompatible_focus or repeated_glance_chain)
            and not profile["location_shift"]
        ):
            compressed_units[-1] = f"{previous} {current}".strip()
        else:
            compressed_units.append(current)
    return compressed_units


def extract_character_mentions(text):
    plain = normalize_vi(text)
    mentions = []
    if has_any(plain, ["lam tich"]):
        mentions.append(("lam-tich", "Lam Tich", LAM_TICH_VISUAL))
    if has_any(plain, ["tan da", "tan ca"]):
        mentions.append(("tan-da", "Tan Da", TAN_DA_VISUAL))
    if has_any(plain, ["con cho", "cho hai ham", "thu bien di", "lon giap bun", "quai vat"]) and not has_any(plain, ["rang cho hai ham", "tui nho rang cho", "tui rang cho", "tui rang", "rang trong tui", "bag of mutant teeth"]):
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


def infer_fragment_focus(plain):
    if has_any(plain, ["buoc vai vao day", "buoc mieng vai", "tha xuong gieng", "nghe tieng kim loai cham vao", "day rung nhe", "keo len tu tu"]):
        return "well-probe"
    if has_any(plain, ["tam thep nho", "dong chu mo", "nuoc co nguoi giu", "tre con vao truoc", "nguoi lon tra gia sau", "chu mo hoen gi"]):
        return "written-water-warning"
    if has_any(plain, ["co mui nguoi", "co nguoi dang o duoi", "o mot minh", "thang nhai duoi gieng", "mot minh duoi do"]):
        return "hidden-survivor-probe"
    if has_any(plain, ["xac nguoi troi duoi day", "loc bang xac", "mui mau trong nuoc sach", "nuoc sach co mui mau", "mui xac thoi hoi len"]):
        return "poisoned-water-discovery"
    if has_any(plain, ["muon o lai phai theo luat", "khong ban nguoi", "do chung phai bao", "nuoc chia theo viec va benh", "ai giau dao hai doi", "khong ban nguoi qua dem"]):
        return "camp-rules-recital"
    if has_any(plain, ["se co nguoi phan", "van nhan", "co tay con vet xich", "vua thoat khoi vong so", "giu nguoi"]):
        return "acceptance-risk"
    if has_any(plain, ["moi lan gap nga re", "keo mot nguoi ra", "ra lenh di vao", "nen sap", "khong ai keo kip", "keo day sang nhanh c 1", "nhanh c 1"]):
        return "forced-route-test"
    if has_any(plain, ["dua vao goc kin", "ong thuoc gen qua han", "hai ong thuoc gen", "dat truoc mat han", "thuoc gen qua han"]):
        return "treatment-setup"
    if has_any(plain, ["hat giong", "nuoc dung cho hat", "it nuoc cho nguoi", "bat chao", "ho ngung suong", "nuoc dau vao", "mang nuoc dau vao"]):
        return "base-resource-balance"
    if has_any(plain, ["them nguoi, them nuoc", "them ban do", "them no", "them ke thu", "giu mot noi vua moi co ten", "khong con chay khoi nha chay"]):
        return "gain-cost-summary"
    if has_any(plain, ["rang no nghien sat", "tieng ken ket", "a that tai mat", "nghien sat"]):
        return "creature-threat"
    if has_any(plain, ["bang viet", "viet xau", "doc cham", "khong noi duoc", "khong noi", "tam bang"]):
        return "board-exchange"
    if has_any(plain, ["bang dieu khien", "bang khoa", "cat dien", "hai cua co the ket", "he thong khoa cu", "den xanh do tren tran", "phong dem", "khoa cu", "nem vien tinh thach", "mang dien ho", "tia sang xanh no tung", "chap mach", "no xanh", "cat vao mach dien"]):
        return "control-sabotage"
    if has_any(plain, ["sup gen", "loi trong co the", "de qua lau se hong", "hong co the cuu", "gen do sap", "khong phau thuat kip", "giam hieu suat sinh hoc"]):
        return "diagnostic-pressure"
    if has_any(plain, ["ho so ghi ma so", "ho so khong biet dau", "kho ban", "chua gap dung gia", "dung nguoi re hon", "khong con gia tri", "giam hieu suat", "de dieu khien", "thu hoi it dau", "nguoi bi ban", "gia tri truy tim"]):
        return "human-valuation"
    if has_any(plain, ["khai ten", "viec biet lam", "co no voi ai", "xep hang", "ghi ten viec", "hang tiep nhan"]):
        return "intake-registration"
    if has_any(plain, ["sup gen", "loi trong co the", "de qua lau se hong", "hong co the cuu", "gen do sap", "khong phau thuat kip", "giam hieu suat sinh hoc"]):
        return "diagnostic-pressure"
    if has_any(plain, ["dung can cu", "can ten", "ten noi nay", "kho den vang", "kho nay khong thanh trai cuu te", "nghe ngheo qua", "ngheo thi dung roi", "vua dung can cu", "co mot noi khong ban nguoi qua dem", "mot cai ten nho", "giu mot noi vua moi co ten"]):
        return "base-founding"
    if has_any(plain, ["may loc", "loc nuoc", "nghen", "thay loi", "cat lot vao van", "nghe tieng may", "than loc", "noi chao loang", "nuoc chua vo", "ho ra nuoc", "ren len nhu nguoi sot"]):
        return "machine-maintenance"
    if has_any(plain, ["vong bi", "mieng ton", "ton tu thao", "xe nho", "keo tren tam vai dau", "buoc day ngang nguc"]):
        return "repair-logistics"
    if has_any(plain, ["dung nhip", "vang xanh tat", "tung nguoi", "tam be tong noi", "ho nuoc den", "duong trai", "duong phai", "o bo cu"]):
        return "hazard-crossing"
    if has_any(plain, ["buoc xuong duong ham", "di vao duong ham", "vao ham trong im lang", "cui lung di qua", "len duong ham", "qua doan tran sap"]):
        return "hazard-crossing"
    if has_any(plain, ["nho so buoc", "nho cho tran thap", "nho vet gio", "am thanh moi duong ong", "nho duong ong", "nho cua thoat nuoc", "nho mui reu"]):
        return "memory-navigation"
    if has_any(plain, ["ban do", "duong ham so 4", "loi chinh", "loi bao tri", "loi thoat nuoc", "vao ham truoc binh minh", "cat duong", "diem hoi", "duong nao"]):
        return "route-planning"
    if has_any(plain, ["ga xam", "tram doi do", "bang gia", "mot gao nuoc", "mot lieu thuoc", "bach nhi", "cac vi can gi", "noi chuyen gia", "tin ve", "tra gia"]):
        return "market-bargain"
    if has_any(plain, ["gieng cu", "mieng gieng", "lon sat treo bang day", "co nguoi dang o duoi", "mui dong"]):
        return "threshold-negotiation"
    if has_any(plain, ["bat nuoc dang soi", "nuoc sach co mui mau", "mui mau trong nuoc", "nhin bat nuoc", "nuoc dang soi"]):
        return "water-inspection"
    if has_any(plain, ["nua ngum", "them nua ngum", "chia nuoc", "phan cua minh", "uong thuoc", "phan thuoc", "bat minh", "it hon ta", "chao loang", "bot mi con it", "chia phan"]):
        return "ration-pressure"
    if has_any(plain, ["moi nguoi mot phan thuoc", "chia thuoc", "thuoc cua tan da", "thuoc cua tieu ngo"]):
        return "medicine-allocation"
    if has_any(plain, ["luat cua", "mot:", "hai:", "ba:", "tam thep treo", "chu sau", "khac len tam thep", "vet mau cu", "khong ai lau", "tieng go la dung"]):
        return "law-recital"
    if has_any(plain, ["chi con mot tay", "nhac bua len", "ca kho deu yen", "mot tay van cam bua"]):
        return "authority-introduction"
    if has_any(plain, ["con bo", "bo giap than", "vung nuoc dien", "xac bo", "tui loc tinh"]):
        return "insect-combat"
    if has_any(plain, ["duong ray", "doi chim xam", "doan nguoi", "di ve phia nam", "xe lan"]) and not has_any(plain, ["ga xam", "bang gia"]):
        return "journey-column"
    if has_any(plain, ["dau giay", "hoa van tam giac", "vet quan vai", "vet chan", "vet in trong bui do"]):
        return "track-discovery"
    if has_any(plain, ["mui am", "mui bun", "reu chet", "gio am", "hoi nuoc"]):
        return "water-scent"
    if has_any(plain, ["tinh thach sach", "thuoc gen", "hat giong nay mam", "hat giong mo mam", "nguon nuoc ngot", "loi loc moi", "phat hien vat tu"]):
        return "resource-discovery"
    if has_any(plain, ["nem vien tinh thach", "mang dien ho", "tia sang xanh no tung", "chap mach", "no xanh", "cat vao mach dien"]):
        return "control-sabotage"
    if has_any(plain, ["mau xuong roi xuong", "loc coc", "luong gio tanh", "keo su chu y"]):
        return "danger-distraction"
    if has_any(plain, ["mua dan thu duong", "gia tang gap doi", "tu di dang ky", "bang mua dan thu duong", "bang mua dan", "thu duong"]):
        return "human-valuation"
    return ""


def piece_profile(piece):
    plain = normalize_vi(piece)
    word_count = len(re.findall(r"\S+", piece))
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
        "word_count": word_count,
        "focus_tag": infer_fragment_focus(plain),
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
        "question": "?" in piece or has_any(plain, ["co phai", "vi sao", "lam gi", "the nao", "duong nao", "ten?"]),
        "command_like": has_any(plain, ["dung", "di", "im", "nghe", "nhin", "lay", "mang", "cho", "tra", "cat dien"]),
        "named_object": has_any(
            plain,
            [
                "bang viet", "bang dieu khien", "may loc", "gieng", "lon sat", "hat giong", "so no",
                "bang gia", "vien tinh thach", "rang cho hai ham", "bua", "xe lan", "bat nuoc", "tam thep"
            ],
        ),
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
    if profile["named_object"]:
        weight += 1
    return weight


def scene_completeness(profile, words):
    score = 0
    if profile["subjects"]:
        score += 1
    if profile["action_beat"]:
        score += 1
    if profile["object_focus"] or profile["named_object"]:
        score += 1
    if profile["location_shift"]:
        score += 1
    if profile["dialogue"] and words >= 8:
        score += 1
    if profile["emotional_beat"] and words >= 10:
        score += 1
    return score



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
    hard_limit_words = max(56, int(words_per_image * 2.8))

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
            pending_heading = None

        if current:
            current_text = " ".join(current)
            current_profile = piece_profile(current_text)
            current_weight = beat_weight(current_profile)
            next_weight = beat_weight(profile)
            current_complete = scene_completeness(current_profile, current_words)
            next_complete = scene_completeness(profile, words)
            current_has_real_beat = current_complete >= 2 or current_weight >= 4 or current_words >= 14 or len(current) >= 2
            focus_shift = bool(profile["focus_tag"]) and bool(current_profile["focus_tag"]) and profile["focus_tag"] != current_profile["focus_tag"]
            subject_shift = bool(profile["subjects"]) and bool(current_profile["subjects"]) and profile["subjects"] != current_profile["subjects"]
            dialogue_switch = (
                profile["dialogue"]
                and current_has_real_beat
                and not current_profile["dialogue"]
                and current_words >= 14
                and words >= 8
            )
            location_switch = profile["location_shift"] and current_has_real_beat and current_words >= 14
            object_switch = (profile["object_focus"] or profile["named_object"]) and current_has_real_beat and (
                current_profile["action_beat"] or current_profile["dialogue"] or current_profile["emotional_beat"]
            ) and words >= 10 and next_complete >= 2
            reaction_switch = profile["emotional_beat"] and current_has_real_beat and not current_profile["emotional_beat"] and current_words >= 14
            action_switch = profile["action_beat"] and current_has_real_beat and (
                current_profile["action_beat"] or current_profile["dialogue"] or current_profile["object_focus"]
            ) and current_words >= 14 and words >= 10 and next_complete >= 2
            transition_switch = profile["transition"] and current_has_real_beat and current_words >= 16
            beat_density_split = current_has_real_beat and next_weight >= 5 and current_weight >= 5 and current_words >= 18 and next_complete >= 2
            independent_dialogue_turn = (
                profile["dialogue"]
                and current_profile["dialogue"]
                and current_has_real_beat
                and current_words >= 12
                and words >= 5
                and (
                    profile["question"]
                    or current_profile["question"]
                    or profile["command_like"] != current_profile["command_like"]
                    or (
                        bool(profile["subjects"])
                        and bool(current_profile["subjects"])
                        and profile["subjects"] != current_profile["subjects"]
                    )
                    or (
                        bool(profile["focus_tag"])
                        and bool(current_profile["focus_tag"])
                        and profile["focus_tag"] != current_profile["focus_tag"]
                    )
                )
            )
            support_to_action_break = (
                current_profile["dialogue"]
                and profile["action_beat"]
                and current_has_real_beat
                and current_words >= 12
                and words >= 6
            )
            focused_object_break = (
                profile["named_object"]
                and current_has_real_beat
                and current_words >= 12
                and (
                    not current_profile["named_object"]
                    or profile["focus_tag"] != current_profile["focus_tag"]
                )
            )
            same_subject_continuation = bool(profile["subjects"]) and profile["subjects"] == current_profile["subjects"]
            same_focus_continuation = (
                profile["object_focus"] == current_profile["object_focus"]
                and profile["dialogue"] == current_profile["dialogue"]
                and profile["location_shift"] == current_profile["location_shift"]
            )
            fragmentary_next = (
                words <= 10
                and (
                    profile["dialogue"]
                    or profile["question"]
                    or profile["command_like"]
                    or profile["emotional_beat"]
                    or (profile["action_beat"] and next_complete <= 1)
                    or (
                        profile["focus_tag"] in {"interaction", "object-detail", "decision-reaction"}
                        and next_complete <= 1
                    )
                )
                and not profile["named_object"]
                and not profile["location_shift"]
                and not profile["subjects"]
            )
            too_long = (
                (current_words + words > hard_limit_words and not (same_subject_continuation and same_focus_continuation))
                or len(current) >= 5
            )

            if (
                (too_long and not fragmentary_next)
                or (focus_shift and current_has_real_beat and next_complete >= 2)
                or subject_shift
                or dialogue_switch
                or location_switch
                or object_switch
                or reaction_switch
                or action_switch
                or transition_switch
                or beat_density_split
                or independent_dialogue_turn
                or support_to_action_break
                or focused_object_break
            ):
                groups.append(current_text)
                current = [piece]
                current_words = words
                continue

        current.append(piece)
        current_words += words

    if current:
        groups.append(" ".join(current))

    smoothed = []
    index = 0
    while index < len(groups):
        current = groups[index]
        profile = piece_profile(current)
        words = len(re.findall(r"\S+", current))
        weak_scene = (
            (scene_completeness(profile, words) == 0 and words <= 6)
            or (words <= 4 and not profile["named_object"] and not profile["subjects"])
            or (
                words <= 10
                and scene_completeness(profile, words) <= 1
                and profile["focus_tag"] in {"interaction", "object-detail", "decision-reaction"}
                and not profile["named_object"]
                and not profile["subjects"]
            )
        )
        if index + 1 < len(groups) and weak_scene and not profile["heading"]:
            nxt = groups[index + 1]
            next_profile = piece_profile(nxt)
            same_focus = (
                not profile["focus_tag"]
                or not next_profile["focus_tag"]
                or profile["focus_tag"] == next_profile["focus_tag"]
            )
            combined_words = words + len(re.findall(r"\S+", nxt))
            if (
                not next_profile["heading"]
                and same_focus
                and not next_profile["location_shift"]
                and not next_profile["question"]
                and combined_words <= 26
            ):
                smoothed.append(f"{current} {nxt}".strip())
                index += 2
                continue
        smoothed.append(current)
        index += 1
    groups = smoothed

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
                left_words = len(re.findall(r"\S+", groups[index]))
                right_words = len(re.findall(r"\S+", groups[index + 1]))
                left_complete = scene_completeness(left_profile, left_words)
                right_complete = scene_completeness(right_profile, right_words)
                left_tiny_fragment = left_words <= 10 and left_complete <= 1
                right_tiny_fragment = right_words <= 10 and right_complete <= 1
                if beat_weight(left_profile) >= 5 and beat_weight(right_profile) >= 5 and (left_profile["location_shift"] or right_profile["location_shift"] or left_profile["subjects"] != right_profile["subjects"]):
                    continue
                if left_profile["focus_tag"] and right_profile["focus_tag"] and left_profile["focus_tag"] != right_profile["focus_tag"] and left_complete >= 2 and right_complete >= 2 and not (left_tiny_fragment or right_tiny_fragment):
                    continue
                size = left_words + right_words
                if size > max(42, int(words_per_image * 2.1)):
                    continue
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
    plain = normalize_vi(text)
    return any(mark in text for mark in ['"', "“", "”", "‘", "’"]) or has_any(
        plain,
        ["hoi", "dap", "quat", "thot", "gioi thieu", "len tieng", "noi nho", "noi khe", "noi voi", "tra loi"],
    )


def infer_dialogue_subbeat(plain):
    if has_any(plain, ["anh mat han luot qua", "luot qua xe lan", "dung lai o radio", "dung tren ban tay bang mau", "nhin doi minh", "nguoi bi thuong. tre con. no moi. nuoc moi. ke thu moi"]):
        return "appraisal-glance"
    if has_any(plain, ["dem nguoi chet lam gi", "dem nuoc con lai quan trong hon", "hieu biet, hop tac", "quyet dinh khong tham qua sau con", "lang phi tai nguyen", "tra ten lai cho ho", "mua mot dem binh yen"]):
        return "survival-values"
    if has_any(plain, ["chay!", "chui khoi toa", "om loi loc chay sat mep ray", "ua ra ngoai", "lao ra", "thoat ra ngoai"]):
        return "escape-burst"
    if has_any(plain, ["muon o lai phai theo luat", "khong ban nguoi", "do chung phai bao", "nuoc chia theo viec va benh", "ai giau dao hai doi", "khong ban nguoi qua dem"]):
        return "camp-rules-recital"
    if has_any(plain, ["se co nguoi phan", "van nhan", "giu nguoi", "co tay con vet xich", "vua thoat khoi vong so"]):
        return "acceptance-risk"
    if re.fullmatch(r'\s*["“”]?ten\??["“”]?\s*', plain):
        return "identity-probe"
    if has_any(plain, ["bang viet", "viet xau", "doc cham", "khong noi duoc", "khong noi", "tam bang"]):
        return "board-exchange"
    if has_any(plain, ["bang dieu khien", "bang khoa", "cat dien", "hai cua co the ket", "he thong khoa cu", "den xanh do tren tran", "phong dem", "khoa cu", "nem vien tinh thach", "mang dien ho", "tia sang xanh no tung", "chap mach", "no xanh", "cat vao mach dien"]):
        return "control-sabotage"
    if has_any(plain, ["sup gen", "loi trong co the", "de qua lau se hong", "hong co the cuu", "gen do sap", "khong phau thuat kip", "giam hieu suat sinh hoc"]):
        return "diagnostic-pressure"
    if has_any(plain, ["tra tien", "tra gia", "noi chuyen gia", "mot gao nuoc", "mot lieu thuoc", "nuoc mac hon", "cac vi can gi", "tin ve"]):
        return "trade-probe"
    if has_any(plain, ["giong nguoi lam an", "dang ghet cho nao", "doi giam gia", "ngua nhien nua", "thich", "vong vo"]):
        return "verbal-sparring"
    if has_any(plain, ["co phai hac nha khong", "la ai", "co phai", "nhin ra", "nhan ra nguoi", "nguoi tren xe lan kia"]):
        return "identity-probe"
    if has_any(plain, ["luat cua", "mot:", "hai:", "ba:", "tam thep treo", "chu sau", "khac len tam thep", "vet mau cu", "khong ai lau"]):
        return "law-recital"
    if has_any(plain, ["no bao nhieu", "tinh lai", "hop dong viec", "ghi ten", "chuyen sang chim xam", "muoi hai gao nuoc", "ta tra bon", "lai tinh theo ngay", "no tra bang duong", "ganh no", "lai tinh bang tin", "no cua a muc", "viet hai chu chim xam len so", "ghi vao so no"]):
        return "debt-ledger"
    if has_any(plain, ["ho so ghi ma so", "ho so khong biet dau", "kho ban", "chua gap dung gia", "dung nguoi re hon", "khong con gia tri", "giam hieu suat", "de dieu khien", "thu hoi it dau", "nguoi bi ban", "gia tri truy tim", "giong nguoi khong", "giong nguoi", "nguoi hay ho so", "khong biet dau"]):
        return "human-valuation"
    if has_any(plain, ["khai ten", "viec biet lam", "co no voi ai", "xep hang", "ghi ten viec", "hang tiep nhan"]):
        return "intake-registration"
    if has_any(plain, ["sup gen", "loi trong co the", "de qua lau se hong", "hong co the cuu", "gen do sap", "khong phau thuat kip"]):
        return "diagnostic-pressure"
    if has_any(plain, ["nua ngum", "them nua ngum", "chia nuoc", "phan cua minh", "uong thuoc", "phan thuoc", "bat minh", "it hon ta", "chao loang", "bot mi con it", "chia?", "chia phan"]):
        if has_any(plain, ["im", "khong can", "khong uong", "cho uong", "them nua ngum"]):
            return "command-pressure"
        return "ration-negotiation"
    if has_any(plain, ["hom nay can mat cua nguoi", "hom nay can mat cua ngươi", "can mat cua nguoi", "nguoi doc gio", "noi voi moc sanh", "giao cho", "ngươi lam", "nguoi lam"]) and not has_any(plain, ["nua ngum", "them nua ngum", "chia nuoc", "uong thuoc", "phan thuoc", "phan cua minh", "khat"]):
        return "role-assignment"
    if has_any(plain, ["dung can cu", "can ten", "ten noi nay", "kho den vang", "kho nay khong thanh trai cuu te", "nghe ngheo qua", "ngheo thi dung roi", "vua dung can cu"]):
        return "base-founding"
    if has_any(plain, ["hat giong", "nuoc dung cho hat", "it nuoc cho nguoi", "bat chao", "ho ngung suong", "nuoc dau vao", "mang nuoc dau vao"]):
        return "base-resource-balance"
    if has_any(plain, ["may loc", "loc nuoc", "nghen", "thay loi", "cat lot vao van", "nghe tieng may", "than loc", "noi chao loang", "nuoc chua vo"]):
        return "machine-maintenance"
    if has_any(plain, ["vong bi", "mieng ton", "truc thang", "ton tu thao", "xe nho", "sua", "keo tren tam vai dau", "buoc day ngang nguc"]):
        return "repair-logistics"
    if has_any(plain, ["dung nhip", "vang xanh tat", "tung nguoi", "buoc day", "co the qua", "qua duoc bo ben kia", "tam be tong noi", "ho nuoc den", "co hai duong", "duong trai", "duong phai", "o bo cu", "duong nao"]):
        return "hazard-crossing"
    if has_any(plain, ["buoc xuong duong ham", "di vao duong ham", "vao ham trong im lang", "cui lung di qua", "len duong ham", "qua doan tran sap"]):
        return "hazard-crossing"
    if has_any(plain, ["nho so buoc", "nho cho tran thap", "nho vet gio", "am thanh moi duong ong", "nho duong ong", "nho cua thoat nuoc", "nho mui reu"]):
        return "memory-navigation"
    if has_any(plain, ["mua dan thu duong", "gia tang gap doi", "tu di dang ky", "bang mua dan thu duong", "bang mua dan", "thu duong"]):
        return "human-valuation"
    if has_any(plain, ["nho so buoc", "nho cho tran thap", "nho vet gio", "am thanh moi duong ong", "nho duong ong", "nho cua thoat nuoc", "nho mui reu"]):
        return "memory-navigation"
    if has_any(plain, ["nho so buoc", "nho cho tran thap", "nho vet gio", "am thanh moi duong ong", "nho duong ong", "nho cua thoat nuoc", "nho mui reu"]):
        return "memory-navigation"
    if has_any(plain, ["ban do", "chi ban do", "duong ham so 4", "loi chinh", "loi bao tri", "loi thoat nuoc", "vao ham truoc binh minh", "co may loi", "cat duong", "diem hoi", "duong trai", "duong phai", "o bo cu"]):
        return "route-planning"
    if has_any(plain, ["bao truoc", "can than", "khong duoc", "anh hung", "de sau", "khong quay lai", "coi", "nguoi im", "ta khong uong", "khong can", "da bao", "chay la chet", "dung day cho chet", "dung chay", "dung lai", "dung ngay"]):
        return "warning-rebuke"
    if has_any(plain, ["nghe thay", "co nguoi dang o duoi", "o mot minh", "la gi cua nguoi", "co mui nguoi", "ba dau chan", "khong la gi"]):
        return "trust-test"
    if has_any(plain, ["ty ty", "doc cham", "viet xau", "nhin no", "mat no sang", "bang viet"]):
        return "child-observation"
    if has_any(plain, ["ta ngoi", "cac nguoi day", "di duoc", "khong di duoc", "mot minh di", "dung keo"]):
        return "movement-decision"
    return ""


def classify_primary_scene_beat(narration):
    plain = normalize_vi(narration)
    dialogue_subbeat = infer_dialogue_subbeat(plain) if has_dialogue_signals(narration) else ""
    trade_context = has_any(plain, ["bang gia", "mot gao nuoc", "mot lieu thuoc", "noi chuyen gia", "tra tien", "tra gia", "tin ve", "cac vi can gi", "doi nuoc", "doi thuoc", "doi cho tre con", "tra doi"])
    non_medical_context = has_any(plain, [
        "gieng cu", "mieng gieng", "lon sat treo bang day", "gio am", "mui am", "hoi nuoc",
        "duong ray", "doan nguoi", "xe lan", "cot dien gay nghieng", "dat len ban", "vien tinh thach",
        "rang cho hai ham", "ga xam", "bang gia", "tra gia", "doi nuoc", "doi thuoc", "nuoc dang soi",
        "vong so", "mot ngay thu duong", "kho bao tri", "duong ham so 4", "ban do duong ray"
    ])
    if has_any(plain, ["anh mat han luot qua", "luot qua xe lan", "dung lai o radio", "dung tren ban tay bang mau", "nhin doi minh", "nguoi bi thuong. tre con. no moi. nuoc moi. ke thu moi"]):
        return "appraisal-glance"
    if has_any(plain, ["dem nguoi chet lam gi", "dem nuoc con lai quan trong hon", "hieu biet, hop tac", "quyet dinh khong tham qua sau con", "lang phi tai nguyen", "tra ten lai cho ho", "mua mot dem binh yen"]):
        return "survival-values"
    if has_any(plain, ["chay!", "chui khoi toa", "om loi loc chay sat mep ray", "ua ra ngoai", "lao ra", "thoat ra ngoai"]):
        return "escape-burst"
    if has_any(plain, ["muon o lai phai theo luat", "khong ban nguoi", "do chung phai bao", "nuoc chia theo viec va benh", "ai giau dao hai doi", "khong ban nguoi qua dem"]):
        return "camp-rules-recital"
    if has_any(plain, ["se co nguoi phan", "van nhan", "giu nguoi", "co tay con vet xich", "vua thoat khoi vong so"]):
        return "acceptance-risk"
    if has_any(plain, ["moi lan gap nga re", "keo mot nguoi ra", "ra lenh di vao", "nen sap", "khong ai keo kip", "keo day sang nhanh c 1", "nhanh c 1"]) and not has_any(plain, ["ban do", "loi chinh", "loi bao tri", "loi thoat nuoc"]):
        return "forced-route-test"
    if has_any(plain, ["dua vao goc kin", "ong thuoc gen qua han", "hai ong thuoc gen", "dat truoc mat han", "thuoc gen qua han"]):
        return "treatment-setup"
    if has_any(plain, ["hat giong", "nuoc dung cho hat", "it nuoc cho nguoi", "bat chao", "ho ngung suong", "nuoc dau vao", "mang nuoc dau vao"]):
        return "base-resource-balance"
    if has_any(plain, ["them nguoi, them nuoc", "them ban do", "them no", "them ke thu", "giu mot noi vua moi co ten", "khong con chay khoi nha chay"]):
        return "gain-cost-summary"
    if has_any(plain, ["rang no nghien sat", "tieng ken ket", "a that tai mat", "nghien sat"]) and has_any(plain, ["duong ham", "ham", "bo", "giap than", "tunnel 4"]):
        return "creature-threat"
    if has_any(plain, ["anh den xe trang loa", "nga tu mua", "tieng phanh", "dien thoai tren mat duong"]):
        return "memory-flashback"
    if has_any(plain, ["mom cho thoi rua cach mat", "ham duoi cua no tach lam hai", "dam thang vao mat no", "lan vao duoi gam xe"]):
        return "predator-threat"
    if has_any(plain, ["chi con mot tay", "nhac bua len", "ca kho deu yen", "danh tieng", "khong cui dau", "mot tay van cam bua"]):
        return "authority-introduction"
    if has_any(plain, ["bang dieu khien", "bang khoa", "cat dien", "hai cua co the ket", "he thong khoa cu", "den xanh do tren tran", "phong dem", "khoa cu", "nem vien tinh thach", "mang dien ho", "tia sang xanh no tung", "chap mach", "no xanh", "cat vao mach dien"]):
        return "control-sabotage"
    if has_any(plain, ["sup gen", "loi trong co the", "de qua lau se hong", "hong co the cuu", "gen do sap", "khong phau thuat kip", "giam hieu suat sinh hoc"]):
        return "diagnostic-pressure"
    if has_any(plain, ["ho so ghi ma so", "ho so khong biet dau", "kho ban", "chua gap dung gia", "dung nguoi re hon", "khong con gia tri", "giam hieu suat", "de dieu khien", "thu hoi it dau", "nguoi bi ban", "gia tri truy tim", "giong nguoi khong", "giong nguoi", "nguoi hay ho so", "khong biet dau"]):
        return "human-valuation"
    if has_any(plain, ["khai ten", "viec biet lam", "co no voi ai", "xep hang", "ghi ten viec", "hang tiep nhan"]):
        return "intake-registration"
    if has_any(plain, ["dung can cu", "can ten", "ten noi nay", "kho den vang", "kho nay khong thanh trai cuu te", "nghe ngheo qua", "ngheo thi dung roi", "vua dung can cu", "cai ten duoc viet len cua"]):
        return "base-founding"
    if has_any(plain, ["may loc", "loc nuoc", "nghen", "thay loi", "cat lot vao van", "nghe tieng may", "than loc", "noi chao loang", "nuoc chua vo", "ho ra nuoc", "ren len nhu nguoi sot"]):
        return "machine-maintenance"
    if has_any(plain, ["vong bi", "mieng ton", "truc thang", "ton tu thao", "xe nho", "sua", "keo tren tam vai dau", "buoc day ngang nguc"]):
        return "repair-logistics"
    if has_any(plain, ["dung nhip", "vang xanh tat", "tung nguoi", "buoc day", "co the qua", "qua duoc bo ben kia", "tam be tong noi", "ho nuoc den", "co hai duong", "duong trai", "duong phai", "o bo cu", "duong nao"]):
        return "hazard-crossing"
    if has_any(plain, ["nho so buoc", "nho cho tran thap", "nho vet gio", "am thanh moi duong ong", "nho duong ong", "nho cua thoat nuoc", "nho mui reu"]):
        return "memory-navigation"
    if has_any(plain, ["buoc xuong duong ham", "di vao duong ham", "vao ham trong im lang", "cui lung di qua", "len duong ham", "qua doan tran sap"]):
        return "hazard-crossing"
    if dialogue_subbeat == "board-exchange":
        return "board-exchange"
    if dialogue_subbeat == "appraisal-glance":
        return "appraisal-glance"
    if dialogue_subbeat == "survival-values":
        return "survival-values"
    if dialogue_subbeat == "escape-burst":
        return "escape-burst"
    if dialogue_subbeat == "camp-rules-recital":
        return "camp-rules-recital"
    if dialogue_subbeat == "acceptance-risk":
        return "acceptance-risk"
    if dialogue_subbeat == "control-sabotage":
        return "control-sabotage"
    if dialogue_subbeat == "law-recital":
        return "law-recital"
    if dialogue_subbeat == "debt-ledger":
        return "debt-ledger"
    if dialogue_subbeat == "human-valuation":
        return "human-valuation"
    if dialogue_subbeat == "intake-registration":
        return "intake-registration"
    if dialogue_subbeat == "diagnostic-pressure":
        return "diagnostic-pressure"
    if dialogue_subbeat == "role-assignment":
        return "role-assignment"
    if dialogue_subbeat == "base-founding":
        return "base-founding"
    if dialogue_subbeat == "machine-maintenance":
        return "machine-maintenance"
    if dialogue_subbeat == "repair-logistics":
        return "repair-logistics"
    if dialogue_subbeat == "base-resource-balance":
        return "base-resource-balance"
    if dialogue_subbeat == "hazard-crossing":
        return "hazard-crossing"
    if dialogue_subbeat == "memory-navigation":
        return "memory-navigation"
    if has_any(plain, ["luat cua", "mot:", "hai:", "ba:", "tam thep treo", "chu sau", "khac len tam thep", "khong ai lau"]) and not has_any(plain, ["bang vet thuong", "bang gac"]):
        return "law-recital"
    if has_any(plain, ["con bo", "nhung con bo", "bo nho", "bo giap than", "vung nuoc dien", "khop chan", "vo no", "xac bo", "bung sang", "mau bo", "tui loc tinh", "sap bi can", "giu bo", "bo rut", "day ben trai", "cui dau"]) and not has_any(plain, ["rang cho hai ham", "con cho", "cho hai ham", "xac bi bay cho gam"]):
        return "insect-combat"
    if has_any(plain, ["bat nuoc dang soi", "nuoc sach co mui mau", "mui mau trong nuoc", "nhin bat nuoc", "dong chu kia", "nuoc dang soi"]) and not has_any(plain, ["nap hop", "than loc", "nuoc vang nhat", "mui ri sat trong nap"]):
        return "water-inspection"
    if (
        not trade_context
        and has_any(plain, ["duong ham so 4", "co may loi", "loi chinh", "loi bao tri", "loi thoat nuoc", "di loi dong", "ban do duong ray", "chi ban do", "vao ham truoc binh minh", "co bo giap than", "may loi", "cat duong", "diem hoi", "duong trai", "duong phai", "o bo cu"])
        and has_any(plain, ["loi chinh", "loi bao tri", "loi thoat nuoc", "ban do", "vao ham", "may loi", "cat duong", "diem hoi", "duong trai", "duong phai", "o bo cu", "co hai duong", "duong nao", "loi nao"])
    ):
        return "route-planning"
    if has_any(plain, ["moi nguoi mot phan thuoc", "nua phan", "chia thuoc", "uong thuoc", "phan thuoc", "thuoc cua tan da", "thuoc cua tieu ngo"]):
        return "medicine-allocation"
    if has_any(plain, ["con khat", "ngam moi", "nhin phan cua minh", "nuot nuoc bot", "giau con khat", "phan cua minh", "khat den dau", "bat minh", "it hon ta", "chao loang", "bot mi con it", "chia phan", "chia?"]):
        return "ration-pressure"
    if has_any(plain, ["mau xuong roi xuong", "lan tren mai ton", "loc coc", "qua mu lao sang", "luong gio tanh", "danh lac huong", "keo su chu y"]):
        return "danger-distraction"
    if has_any(plain, ["mua dan thu duong", "gia tang gap doi", "tu di dang ky", "bang mua dan thu duong", "bang mua dan", "thu duong", "vong so", "tra cho nguoi nha", "mot ngay thu duong"]):
        return "human-valuation"
    if has_any(plain, ["ga xam", "tram doi do", "bang gia", "mot gao nuoc", "mot lieu thuoc", "tin mot cau", "cac vi can gi", "noi chuyen gia", "tin ve", "doi nuoc", "doi thuoc", "doi cho tre con", "tra doi"]) or (has_any(plain, ["bach nhi"]) and (trade_context or has_any(plain, ["doi nuoc", "doi thuoc", "doi cho tre con", "tra doi"]))):
        return "market-bargain"
    if has_any(plain, ["tin hieu gen", "mo radio", "radio song", "gio radio", "tu radio", "tin hieu radio", "radio re", "radio bao", "radio noi"]):
        return "radio-warning"
    if has_any(plain, ["nuoc chi con mot vach", "khong chia nuoc", "moi nguoi mot ngum", "binh nuoc", "tan da uong thuoc"]):
        return "ration-stop"
    if has_any(plain, ["gieng cu", "mieng gieng", "lon sat treo bang day", "cua kho", "ngoai vach", "vach trang", "bo dao xuong", "tre con vao truoc", "tra gia", "thang nhai duoi gieng"]):
        return "threshold-negotiation"
    if has_any(plain, ["tinh thach", "mau banh", "thit hop", "thuoc", "radio song lai", "moc sat"]):
        return "resource-discovery"
    if has_any(plain, ["mui am", "mui bun", "reu chet", "gio am", "hoi nuoc", "hoi am"]):
        return "water-scent"
    if has_any(plain, ["dau giay", "hoa van tam giac", "manh quan vai", "vet quan vai", "vet chan", "vet in trong bui do"]):
        return "track-discovery"
    if has_any(plain, ["sot", "mo hoi lanh", "bang gac", "bang vet thuong", "vet mau", "chay mau", "bi can", "dau den mat toi"]) and not non_medical_context:
        return "medical-strain"
    if has_any(plain, ["vet thuong", "uong thuoc", "thuoc gen", "gen sup do", "vet mau tham"]) and has_any(plain, ["sot", "mo hoi lanh", "dau", "nhuc", "yeu", "run", "mat toi", "bang", "thuoc"]) and not non_medical_context:
        return "medical-strain"
    if has_any(plain, ["duong ray", "duong ray cu", "doi chim xam", "ca doan", "doan nguoi", "di ve phia nam"]) or (has_any(plain, ["xe lan", "truc xe", "vong banh", "cot ket"]) and has_any(plain, ["doc duong", "di ve phia nam", "ca doan", "doan nguoi", "duong ray"])):
        return "journey-column"
    if dialogue_subbeat == "trade-probe":
        return "market-bargain"
    if dialogue_subbeat == "verbal-sparring":
        return "group-dialogue"
    if dialogue_subbeat == "identity-probe":
        return "identity-probe"
    if dialogue_subbeat == "route-planning":
        return "route-planning"
    if dialogue_subbeat == "child-observation":
        return "board-exchange"
    if dialogue_subbeat == "trust-test":
        return "group-dialogue"
    if dialogue_subbeat == "movement-decision":
        return "group-dialogue"
    if dialogue_subbeat == "command-pressure":
        return "ration-pressure" if has_any(plain, ["nua ngum", "them nua ngum", "chia nuoc", "uong thuoc", "phan thuoc", "phan cua minh", "khat", "it hon ta", "chao loang"]) else "group-dialogue"
    if dialogue_subbeat == "ration-negotiation":
        return "ration-pressure"
    if dialogue_subbeat == "warning-rebuke":
        return "group-dialogue"
    if has_any(plain, ["tranh duong nuoc", "tang gia nuoc phia bac", "gia re hon", "doi nuoc cho tre con", "doi thuoc cho hai nguoi bi thuong"]):
        return "market-bargain"
    if has_dialogue_signals(narration):
        if has_any(plain, ["khong", "ta", "nguoi", "vi sao", "neu", "bo dao", "vao truoc", "tra gia"]):
            return "group-dialogue"
    if has_any(plain, ["nhan ra", "hieu ra", "bat dau hieu", "lan dau tien thay", "moi hieu", "quyet dinh", "ngan nguoi", "khu'ng", "khung", "nho lai", "bat an", "lanh gay", "hai chuyen khac nhau", "nghen lai"]):
        return "decision-reaction"
    if has_any(plain, ["nap hop", "ban tay", "dao", "cai coi", "binh kim loai", "lop nuoc mong"]):
        return "object-detail"
    return "story-beat"


def infer_narration_location(narration, continuity=None):
    continuity = continuity or {}
    plain = normalize_vi(narration)
    trade_context = has_any(plain, ["bang gia", "mot gao nuoc", "mot lieu thuoc", "noi chuyen gia", "tra tien", "tra gia", "tin ve", "cac vi can gi", "doi nuoc", "doi thuoc", "doi cho tre con", "tra doi", "vong so", "mot ngay thu duong", "tra cho nguoi nha"])
    gray_station_cues = ["ga xam", "tram doi do", "bang gia", "toa tau bo hoang", "nhanh ray cu", "cac vi can gi", "noi chuyen gia", "mot gao nuoc", "mot lieu thuoc", "tin mot cau", "tra tien", "vong vo", "doi nuoc", "doi thuoc", "tra doi", "vong so", "mot ngay thu duong", "tra cho nguoi nha", "tang gia nuoc", "tranh duong nuoc", "quay hang", "gian hang", "sap hang", "toa thu nhat", "toa thu hai", "toa thu ba", "toa thu tu"]
    base_cues = ["kho den vang", "dung can cu", "can ten", "ten noi nay", "kho nay khong thanh trai cuu te", "may loc", "khu bep", "khu ngu", "canh thuoc", "trai cuu te", "can cu tam", "ho ngung suong", "hat giong", "hop hat giong", "bat chao", "noi chao", "nuoc dau vao", "mang nuoc dau vao"]
    warehouse_yard_cues = ["kho bao tri", "san sau kho", "giua hai toa tau hong", "ve ban do bang than", "ca kho deu yen", "nhac bua len"]
    railway_cues = ["duong ray", "duong ray cu", "ray gi", "doi chim xam", "ca doan", "doan nguoi", "di ve phia nam", "xe lan", "truc xe", "vong banh", "cot ket"]
    tunnel_cues = ["duong ham so 4", "duong ham", "duoi ray", "ho dien", "bo giap than", "dien bun", "nuoc duoi ray", "ham thap"]
    if has_any(plain, gray_station_cues) or (has_any(plain, ["bach nhi"]) and trade_context):
        return "Gray Station, a harsh rail-junction trading post built from abandoned train cars, scrap walls, and guarded stalls"
    if has_any(plain, base_cues):
        return "the maintenance warehouse turned survival base, with the water filter, cooking corner, sleeping zones, and rough systems being built into a real camp"
    if has_any(plain, tunnel_cues):
        return "Tunnel 4, a low underground rail tunnel with damp concrete, electric water, service pipes, and armored insect danger"
    if has_any(plain, ["khe nhan dang", "the nhan dang", "phong dem", "tu kim loai", "hop den", "hac nha", "quan phuc hac nha", "phong dieu khien"]):
        return "a hidden underground service chamber inside Tunnel 4, with metal lockers, a control desk, identity lock hardware, and remnants of the Hac Nha unit"
    if has_any(plain, warehouse_yard_cues):
        return "the maintenance warehouse yard or warehouse interior described by the narration, with broken train cars and repair-space details"
    if (not trade_context) and has_any(plain, ["duong ham so 4", "ban do duong ray", "loi chinh", "loi bao tri", "loi thoat nuoc", "vao ham truoc binh minh", "may loi"]):
        return "the maintenance-yard briefing area behind the warehouse, with a charcoal route map laid out between broken train cars"
    if has_any(plain, ["bai rac", "dong xe phe lieu", "nhat rac", "gam xe", "xe tai lat", "tu lanh gay cua"]):
        return "a filthy radioactive junkyard with scrap heaps, overturned vehicles, and black contaminated dirt"
    if has_any(plain, ["tin hieu gen", "mo radio", "radio song", "gio radio", "tu radio", "tin hieu radio", "radio re", "radio bao", "radio noi"]) and continuity.get("location"):
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
    if has_any(plain, ["cua ben trong", "xich keo", "cay khoa", "dung cu cay khoa", "khoa ben trong", "cua sat ben trong"]):
        if continuity.get("location"):
            return continuity.get("location")
        return "an inner industrial access door or sealed service passage inside the current facility"
    if has_any(plain, ["thuoc", "chia thuoc", "uong thuoc", "moi nguoi mot phan thuoc", "nua phan"]):
        if continuity.get("location"):
            return continuity.get("location")
        return "the current shelter, rail camp, or warehouse corner where the group is dividing medicine under pressure"
    if has_any(plain, railway_cues) or (has_any(plain, ["xe lan", "truc xe", "vong banh", "cot ket"]) and has_any(plain, ["doc duong", "di ve phia nam", "ca doan", "doan nguoi", "duong ray"])):
        return "an old railway line cutting south through ash, red dust, and rusted wasteland debris"
    if has_any(plain, ["toa nha", "nha cao tang", "cao oc", "chung cu", "biet thu", "hanh lang", "dai sanh", "tien sanh", "vao sanh", "thang may"]):
        return "the building interior or exterior exactly described by the current narration"
    if has_any(plain, ["duong pho", "ngo hem", "hem", "con pho"]):
        return "the ruined street or alley exactly described by the current narration"
    if continuity.get("location"):
        continuity_location = continuity.get("location", "")
        continuity_plain = normalize_vi(continuity_location)
        if "gray station" in continuity_location and (trade_context or has_any(plain, ["bach nhi", "vong so", "tra gia", "doi nuoc", "doi thuoc"])):
            return continuity_location
        if "maintenance warehouse turned survival base" in continuity_location and has_any(plain, base_cues + ["chia phan", "nuoc chia", "phan thuoc", "may loc", "bat chao", "hat giong"]):
            return continuity_location
        if "maintenance warehouse yard" in continuity_location and has_any(plain, warehouse_yard_cues + ["ban do bang than", "nhac bua", "ve than", "chi duong"]):
            return continuity_location
        if "old railway line" in continuity_plain and has_any(plain, railway_cues + ["ninh", "tieu mai", "a that", "gio am", "mui dong", "gieng cu"]):
            return continuity_location
        if "tunnel 4" in continuity_plain and has_any(plain, tunnel_cues + ["dien", "bo giap", "ham", "duoi ray", "vung nuoc", "vuot qua", "qua tung nguoi"]):
            return continuity_location
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
        (["vao sanh", "dai sanh", "tien sanh"], "an interior lobby or main hall that matches the building described by the story"),
        (["thang may", "cho thang may"], "an elevator area or elevator doors in the building interior"),
        (["hanh lang", "di qua hanh lang"], "a corridor leading deeper into the building"),
        (["vao phong", "mo cua phong", "cua phong"], "a specific interior room that matches the story beat"),
        (["nha kho", "kho chua"], "a warehouse-like interior with storage clutter and industrial decay"),
        (["ho ngung suong", "hat giong", "hop hat giong", "bat chao", "noi chao"], "a rough survival-base interior where water, seeds, and thin food are being rationed into a future"),
        (["san thuong", "mai nha"], "a rooftop or upper-level open area connected to the current building"),
        (["duong pho", "ngo hem", "hem", "con pho"], "a ruined street or alley matching the current movement path"),
        (["ga xam", "tram doi do", "bang gia", "nhanh ray cu", "toa tau bo hoang"], "Gray Station, a brutal trading post assembled from abandoned train cars and scrap walls at a rail junction"),
        (["toa thu nhat", "toa thu hai", "toa thu ba", "toa thu tu", "rem den"], "a cramped station interior where each train car functions as a separate stall, clinic, or hidden room"),
        (["duong ray", "duong ray cu", "doc duong ray"], "an old railway line cutting south through ash, red dust, and rusted wasteland debris"),
        (["xe lan", "truc xe", "vong banh", "cot ket"], "a damaged wheelchair or improvised stretcher carrying an injured survivor"),
        (["doi chim xam", "ca doan", "doan nguoi"], "a wounded survivor column moving together on foot through the wasteland"),
        (["radio", "tin hieu gen", "mo radio", "radio song", "gio radio", "tu radio", "tin hieu radio"], "a battered survival radio carrying fragmented distant transmissions"),
        (["duong ham so 4", "duong ham", "bo giap than", "vung nuoc dien", "ho dien", "dien bun"], "Tunnel 4 with low concrete, service pipes, electric water, and armored insect danger"),
        (["khe nhan dang", "the nhan dang", "phong dem", "tu kim loai", "hop den", "quan phuc hac nha"], "a hidden underground service chamber with lockers, black-box remains, and Hac Nha traces"),
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
    focus = scene_state.get("focus", "")

    junkyard_specific_rules = [
        (["tinh lai", "liem mau tren tay", "liem tay minh"], "Lam Tich lies weak in the junkyard and wakes as a two-jawed mutated dog licks the blood on her hand"),
        (["luot qua ke ngon tay", "cay nhe lop mau da kho", "vet nut sau trong long ban tay"], "the two-jawed dog slowly licks between Lam Tich's fingers and worries at the dried blood in her cracked palm"),
        (["mom cho thoi rua cach mat"], "Lam Tich opens her eyes to a rotten dog snout hanging terrifyingly close above her face under the rust-red sky"),
        (["ham duoi cua no tach lam hai", "hai hang rang", "luoi cua bi be cong"], "the frame studies the mutant dog's split lower jaw and saw-like crooked teeth at close range"),
        (["thu bien di cap gi", "thich an xac moi chet"], "Lam Tich's fractured memory identifies the creature as a rust-grade two-jawed mutant that feeds on the freshly dead"),
        (["khong sua", "thu xem nang da chet han chua", "lam tich cung khong dong"], "Lam Tich lies perfectly still, pretending to be dead while the mutated dog tests whether she is still alive"),
        (["con cho lai liem tay", "nin tho den muc nguc gan nhu no tung"], "Lam Tich holds her breath while the two-jawed dog returns to lick her hand again"),
        (["gam gu voi hai con khac", "can xe mot cai xac", "quay dau ve phia cai xac", "hai con cho khac"], "the mutated dog turns away from Lam Tich and snarls at two other dogs tearing at a corpse behind the scrap vehicles"),
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
    shared_specific_rules = [
        (["con bo", "nhung con bo", "bo nho", "bo giap than", "vung nuoc dien", "khop chan", "vo no"], "the group fights armored tunnel insects in cramped electric water, using improvised tools and timing to protect the weakest people"),
        (["xac bo", "bung sang", "mau bo", "tui loc tinh", "vien tinh thach"], "the survivors cut open armored insect bodies and search for the first clean crystal while weighing greed against exhaustion"),
    ]
    specific_rules = list(shared_specific_rules)
    if focus in {"survival-introduction", "memory-flashback", "rebirth-junkyard", "dog-awakening", "dog-pack", "dog-attack", "corpse-loot"}:
        specific_rules = junkyard_specific_rules + specific_rules
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

    if focus == "appraisal-glance":
        actions = ["a calculating trader or survivor scans the wheelchair, radio, bandaged hand, and visible weakness of the whole group before naming a price"]
    elif focus == "treatment-setup":
        actions = ["the injured survivor is pulled into a hidden corner and the expired gene medicine is laid out as an ugly survival gamble"]
    elif focus == "human-valuation" and has_any(plain, ["vong so", "mot ngay thu duong", "tra cho nguoi nha"]):
        actions = ["a tagged trial-runner is displayed with a chest board and a water price owed to the family, turning a person into a listed asset"]
    elif focus == "market-bargain" and has_any(plain, ["doi nuoc cho tre con", "doi thuoc cho hai nguoi bi thuong", "tranh duong nuoc", "tang gia nuoc", "gia re hon"]):
        actions = ["the trade is stated in practical terms while water pressure and route control are used to squeeze the price higher"]
    elif focus == "ration-pressure" and has_any(plain, ["doc gio", "can mat cua nguoi", "them nua ngum", "nua ngum"]):
        actions = ["an extra sip is offered, refused, then forced back into the logic of survival because the group still needs that person's eyes and judgment"]
    elif focus == "survival-values":
        actions = ["someone says out loud that water, cooperation, and hard choices matter more than counting the dead, and the others have to live with that truth"]
    elif focus == "escape-burst":
        actions = ["the group breaks from cover with the one salvage piece they cannot leave behind and runs along the rail edge before the threat turns back"]

    if not actions:
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
                actions = [summarize_visible_action(literal, focus)]
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
    elif has_any(plain, ["gam gu voi hai con khac", "can xe mot cai xac", "dong xe phe lieu", "hai con cho khac", "quay dau ve phia cai xac"]):
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
    if state["focus"] == "interaction" and primary_beat == "insect-combat":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "insect-combat"
        state["threat"] = "high"
    elif state["focus"] == "interaction" and primary_beat == "appraisal-glance":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "appraisal-glance"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "market-bargain":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "market-bargain"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "authority-introduction":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "authority-introduction"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "ration-pressure":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "ration-pressure"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "danger-distraction":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "danger-distraction"
        state["threat"] = "high"
    elif state["focus"] == "interaction" and primary_beat == "route-planning":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "route-planning"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "board-exchange":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "board-exchange"
        state["threat"] = continuity.get("threat", "medium")
    elif state["focus"] == "interaction" and primary_beat == "camp-rules-recital":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "camp-rules-recital"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "acceptance-risk":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "acceptance-risk"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "control-sabotage":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "control-sabotage"
        state["threat"] = "high"
    elif state["focus"] == "interaction" and primary_beat == "debt-ledger":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "debt-ledger"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "forced-route-test":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "forced-route-test"
        state["threat"] = "high"
    elif state["focus"] == "interaction" and primary_beat == "treatment-setup":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "treatment-setup"
        state["threat"] = "high"
    elif state["focus"] == "interaction" and primary_beat == "base-resource-balance":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "base-resource-balance"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "gain-cost-summary":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "gain-cost-summary"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "survival-values":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "survival-values"
        state["threat"] = continuity.get("threat", "medium")
    elif state["focus"] == "interaction" and primary_beat == "creature-threat":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "creature-threat"
        state["threat"] = "high"
    elif state["focus"] == "interaction" and primary_beat == "escape-burst":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "escape-burst"
        state["threat"] = "high"
    elif state["focus"] == "interaction" and primary_beat == "water-inspection":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "water-inspection"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "medicine-allocation":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "medicine-allocation"
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
    elif state["focus"] == "interaction" and primary_beat == "human-valuation":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "human-valuation"
        state["threat"] = "high"
    elif state["focus"] == "interaction" and primary_beat == "identity-probe":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "identity-probe"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "base-founding":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "base-founding"
        state["threat"] = continuity.get("threat", "medium")
    elif state["focus"] == "interaction" and primary_beat == "machine-maintenance":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "machine-maintenance"
        state["threat"] = continuity.get("threat", "medium")
    elif state["focus"] == "interaction" and primary_beat == "intake-registration":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "intake-registration"
        state["threat"] = "medium"
    elif state["focus"] == "interaction" and primary_beat == "diagnostic-pressure":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "diagnostic-pressure"
        state["threat"] = "high"
    elif state["focus"] == "interaction" and primary_beat == "memory-navigation":
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "memory-navigation"
        state["threat"] = "medium"
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
    elif state["focus"] == "interaction" and has_any(plain, ["dat len ban", "vien tinh thach", "tui nho rang cho", "rang cho hai ham", "ra gia", "tra gia"]):
        state["location"] = infer_narration_location(narration, continuity)
        state["focus"] = "market-bargain"
        state["threat"] = "medium"
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
    if focus == "authority-introduction":
        return "show why this person or object commands silence and authority in the current place"
    if focus == "appraisal-glance":
        return "show the calculating scan that sizes up the group, their injuries, and their leverage before any price is spoken out loud"
    if focus == "route-planning":
        return "show the route map, options, and the tactical choice the group is making before moving"
    if focus == "board-exchange":
        return "show the writing board, the child exchange around it, and the exact response the message causes"
    if focus == "camp-rules-recital":
        return "show the base rules being spoken in a way everyone must absorb, including what staying with the group now costs and protects"
    if focus == "acceptance-risk":
        return "show the argument over accepting unstable or dangerous survivors and the moral risk everyone feels in that decision"
    if focus == "control-sabotage":
        return "show the control panel, old lock system, or power-cut idea that could change the escape or trap"
    if focus == "forced-route-test":
        return "show the brutal moment someone is forced ahead into danger so others can learn which path kills first"
    if focus == "treatment-setup":
        return "show the hidden treatment corner, the expired medicine, and the fact that survival now depends on an ugly medical gamble"
    if focus == "law-recital":
        return "show the harsh survival rules being spoken or displayed, and how the listeners react to what those rules really mean"
    if focus == "debt-ledger":
        return "show the debt terms, ledger pressure, and exactly who is being bound, traded, or released by the deal"
    if focus == "role-assignment":
        return "show who is being assigned which survival role, and how the group reacts to that responsibility landing on them"
    if focus == "human-valuation":
        return "show the dehumanizing price logic, retrieval language, or cold efficiency that treats people as assets instead of lives"
    if focus == "base-founding":
        return "show the moment this shelter stops being temporary and begins to feel like a named base with rules and purpose"
    if focus == "base-resource-balance":
        return "show the painful tradeoff between water, food, seeds, or future survival so one object carries the cost of the next decision"
    if focus == "gain-cost-summary":
        return "show how the group's gains and new burdens arrive together in the same beat: more people, more water, more debt, more enemies"
    if focus == "survival-values":
        return "show the brutal value system being spoken aloud so the audience can see exactly what this world counts and what it refuses to count"
    if focus == "machine-maintenance":
        return "show the failing filter machine, the improvised maintenance, and the people learning to keep it alive"
    if focus == "repair-logistics":
        return "show the parts, tools, and practical repair problem the group is solving before they can move on"
    if focus == "hazard-crossing":
        return "show the timed crossing plan, the hazard underfoot, and how each person must move to survive it"
    if focus == "insect-combat":
        return "show the cramped tunnel fight against armored insects, the improvised survival tactics, and what the group is risking in the same beat"
    if focus == "creature-threat":
        return "show the armored creature threat before impact, so the audience understands exactly what sound, jaws, or movement freezes the group in place"
    if focus == "escape-burst":
        return "show the exact escape burst as the group breaks cover, grabs what matters, and runs in the narrow window before the threat closes again"
    if focus == "identity-probe":
        return "show the challenge over who someone really is, with the suspected identity and the group's reaction visible in the same beat"
    if focus == "water-inspection":
        return "show the suspicious clean water and the reaction to what seems wrong about it"
    if focus == "group-dialogue" and has_any(plain, ["nua ngum", "them nua ngum", "chia nuoc", "cho uong"]):
        return "show the spoken negotiation over the next sip, dose, or ration choice"
    if focus == "group-dialogue" and has_any(plain, ["co phai hac nha khong", "co phai", "la ai", "nguoi tren xe lan kia"]):
        return "show the probing question of who this person really is and the immediate tension it triggers around the group"
    if focus == "group-dialogue" and has_any(plain, ["giong nguoi lam an", "dang ghet cho nao", "doi giam gia", "vong vo", "thich"]):
        return "show the verbal sparring where each side tests wit, leverage, and emotional control"
    if focus == "group-dialogue" and has_any(plain, ["bao truoc", "can than", "anh hung", "khong quay lai"]):
        return "show the spoken warning, rebuke, or order that changes how the group moves next"
    if focus == "group-dialogue" and has_any(plain, ["nguoi im", "ta khong uong", "khong can", "khong uong"]):
        return "show the moment one person resists, another person forces compliance, and the group's power balance hardens around that order"
    if focus == "group-dialogue" and has_any(plain, ["co nguoi dang o duoi", "o mot minh", "la gi cua nguoi", "co mui nguoi"]):
        return "show the spoken trust test as one side probes who the other really is and whether they can be believed"
    if focus == "group-dialogue" and has_any(plain, ["ta ngoi", "cac nguoi day", "di duoc", "khong di duoc", "mot minh di", "dung keo"]):
        return "show the decision about who moves, who carries, and how the group physically continues from here"
    if focus == "board-exchange" and has_any(plain, ["mat no sang", "nhin no", "ty ty", "doc cham", "viet xau"]):
        return "show the child-centered exchange and the small human reactions around the writing board"
    if focus == "medicine-allocation":
        return "show exactly how medicine or survival supplies are being divided and who is receiving them"
    if focus == "ration-pressure":
        return "show the emotional strain of dividing scarce survival supplies while someone is visibly hiding thirst or need"
    if focus == "danger-distraction":
        return "show the noise, bait, or sudden movement that pulls danger away or sideways for one critical beat"
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
    if focus in {"tan-da-condition", "aftermath"} or "tan da" in plain:
        if "lam tich" in plain:
            return "Lam Tich and Tan Da"
        return "Tan Da"
    if focus in {"dog-awakening", "dog-pack", "dog-attack"}:
        return "Lam Tich and the mutated dogs"
    if focus == "corpse-loot":
        return "Lam Tich and the corpse loot"
    if focus == "memory-flashback":
        return "Lam Tich in the death memory"
    if focus == "authority-introduction":
        return "the person, weapon, or symbol of authority dominating the current beat"
    if focus == "appraisal-glance":
        return "the person scanning the group and the vulnerable survivors or gear being silently evaluated"
    if focus in {"well-discovery", "resource-discovery", "track-discovery", "object-detail", "water-detail"}:
        return "the key object or trace described in the narration"
    if focus == "route-planning":
        return "the people studying the route options and deciding the next way forward"
    if focus == "board-exchange":
        return "the people focused on the writing board and the child exchange around it"
    if focus == "camp-rules-recital":
        return "the person laying down the rules for staying and the people who now have to live under them"
    if focus == "acceptance-risk":
        return "the person defending acceptance, the doubters, and the newly arrived survivors whose risk is being debated"
    if focus == "control-sabotage":
        return "the person reading the control system and whoever is close enough to act on the sabotage plan"
    if focus == "forced-route-test":
        return "the person being forced into danger first, the enforcers behind them, and the witnesses who know what the test means"
    if focus == "treatment-setup":
        return "the injured person, the hidden treatment corner, and whoever must decide whether the medicine gamble is worth it"
    if focus == "human-valuation":
        return "the speaker pricing or retrieving human lives and the people forced to absorb that logic"
    if focus == "base-founding":
        return "the people defining this place as a real base and the person driving that decision"
    if focus == "base-resource-balance":
        return "the person handling the precious resource and the people forced to weigh present survival against tomorrow"
    if focus == "gain-cost-summary":
        return "the whole group as new gains and new burdens settle onto them at the same time"
    if focus == "survival-values":
        return "the speaker naming the wasteland's real values and the listeners forced to accept what matters more than the dead"
    if focus == "machine-maintenance":
        return "the people keeping the filter machine alive and the failing system everyone depends on"
    if focus == "creature-threat":
        return "the person nearest the threat and the creature whose sound or movement freezes the group"
    if focus == "escape-burst":
        return "the people breaking cover with the one object or person they cannot leave behind"
    if focus == "identity-probe":
        return "the challenger, the questioned person, and the group waiting for the identity answer to land"
    if focus == "water-inspection":
        return "the person inspecting the water and whoever is reacting to the danger in it"
    if focus == "group-dialogue" and has_any(plain, ["nua ngum", "them nua ngum", "chia nuoc", "cho uong"]):
        return "the people arguing over the next ration choice and the person most affected by it"
    if focus == "group-dialogue" and has_any(plain, ["co phai hac nha khong", "co phai", "la ai", "nguoi tren xe lan kia"]):
        return "the people probing identity or recognition while the whole group reacts to what the answer might mean"
    if focus == "group-dialogue" and has_any(plain, ["giong nguoi lam an", "dang ghet cho nao", "doi giam gia", "vong vo", "thich"]):
        return "the people verbally sparring over leverage, attitude, and who has the upper hand"
    if focus == "group-dialogue" and has_any(plain, ["bao truoc", "can than", "anh hung", "khong quay lai"]):
        return "the person giving the warning and the person absorbing or resisting it"
    if focus == "group-dialogue" and has_any(plain, ["nguoi im", "ta khong uong", "khong can", "khong uong"]):
        return "the person issuing the hard order and the person resisting or being forced to comply"
    if focus == "group-dialogue" and has_any(plain, ["co nguoi dang o duoi", "o mot minh", "la gi cua nguoi", "co mui nguoi"]):
        return "the people testing trust, identity, or intent through the conversation"
    if focus == "group-dialogue" and has_any(plain, ["ta ngoi", "cac nguoi day", "di duoc", "khong di duoc", "mot minh di", "dung keo"]):
        return "the people deciding movement roles, transport burden, or who can continue under strain"
    if focus == "medicine-allocation":
        return "the people directly involved in dividing the medicine or ration"
    if focus == "ration-pressure":
        return "the people under pressure as scarce water or medicine is weighed and withheld"
    if focus == "danger-distraction":
        return "the moving bait, startled threat, or people using the distraction to survive the next second"
    if focus in {"journey-column", "radio-warning", "ration-stop", "threshold-negotiation", "market-bargain", "group-dialogue"}:
        return "the people actively driving the current beat"
    if focus in {"location-transition", "mass-chaos", "survival-introduction"}:
        return "the current place and whoever the narration is following through it"
    return "the current narrated subject"


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


def is_location_anchor(item):
    plain = normalize_vi(item)
    return any(token in plain for token in LOCATION_ANCHOR_TOKENS)


def keep_continuity_anchor(item):
    plain = normalize_vi(item)
    if not plain:
        return False
    if any(token in plain for token in [
        "lam tich", "tan da", "ninh", "tieu mai", "tieu ngo", "tieu bao", "a that", "a muc",
        "di man", "bach nhi", "thiet oa", "moc sanh", "la kieu", "hau seo", "child survivor",
        "young male scavenger", "older wasteland woman", "adult male trader", "survivor group",
    ]):
        return True
    if is_location_anchor(item):
        return False
    return False


def prune_characters_for_scene(characters, scene_center, scene_state, narration):
    plain = normalize_vi(narration)
    center_subject = normalize_vi(scene_center.get("subject", ""))
    kind = scene_center.get("kind", "subject-center")
    focus = scene_state.get("focus", "")
    filtered = []

    if focus == "board-exchange" or (kind in {"exchange-center", "object-center"} and has_any(plain, ["viet xau", "doc cham", "khong noi duoc", "khong noi", "bang viet", "tam bang"])):
        preferred = ["ninh", "tieu mai"]
        for item in characters:
            item_plain = normalize_vi(item)
            if any(token in item_plain for token in preferred):
                add_unique(filtered, item)
        return filtered or characters

    if kind == "object-center" and has_any(plain, ["gieng cu", "mieng gieng", "lon sat treo bang day", "mui dong", "co nguoi o duoi"]):
        preferred = ["lam tich", "ninh", "tan da", "di man", "tieu mai"]
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

    if kind == "action-center" and center_subject and focus not in {"journey-column", "hazard-crossing", "insect-combat"}:
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
    text = text.replace("`", "").replace('"', "").replace("“", "").replace("”", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def summarize_visible_action(literal, focus=""):
    text = clean_story_fragment(literal, limit=220)
    text = re.sub(r"\s*[–—-]\s*", " ", text)
    plain = normalize_vi(text)
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if sentences:
        text = sentences[0]
    clauses = [part.strip(" ,;:.\"“”") for part in re.split(r"\s*(?:,|;| rồi | rồi, | và | nhưng )\s*", text) if part.strip(" ,;:.\"“”")]
    if clauses:
        text = next((clause for clause in clauses if len(clause.split()) >= 4), clauses[0])
    if len(text.split()) <= 2 and len(sentences) > 1:
        fallback = next((part.strip(" ,;:.\"“”") for part in sentences[1:] if len(part.strip(" ,;:.\"“”").split()) >= 4), "")
        if fallback:
            text = fallback
    if focus == "authority-introduction":
        text = "the feared veteran raises the worn hammer and the whole space falls silent around that authority"
    elif focus == "camp-rules-recital":
        text = "the speaker lays out the rules for staying, and everyone present measures what those rules will demand of them"
    elif focus == "appraisal-glance":
        text = "a calculating survivor scans the wheelchair, radio, wounds, and posture of the whole group to judge weakness, value, and leverage"
    elif focus == "acceptance-risk":
        text = "the group weighs whether to keep dangerous new survivors despite the risk of betrayal or instability they may bring"
    elif focus == "forced-route-test":
        text = "someone is shoved or ordered into the dangerous branch first so the others can read the trap through that person's risk"
    elif focus == "treatment-setup":
        text = "the injured person is hidden away and confronted with expired gene medicine that may be the only ugly chance left"
    elif focus == "base-resource-balance":
        text = "the scene weighs one precious resource against another, making water, food, or seeds carry the cost of the next decision"
    elif focus == "gain-cost-summary":
        text = "the group gains people, water, maps, and hope at the same time that debt, enemies, and responsibility close in around them"
    elif focus == "survival-values":
        text = "someone states the brutal survival logic of this world, and everyone nearby feels what now matters more than comfort, fairness, or the dead"
    elif focus == "creature-threat":
        text = "the armored creature grinds metal or shifts in the dark, and the nearest survivor visibly understands how close death is"
    elif focus == "escape-burst":
        text = "the group bursts from cover with the salvaged core or needed gear and runs in the instant the threat turns the wrong way"
    elif focus == "identity-probe":
        text = "someone openly questions who a vulnerable person really is, and everyone nearby waits for the answer with immediate alarm"
    if focus == "route-planning" and has_any(plain, ["loi chinh", "loi bao tri", "loi thoat nuoc", "duong ham", "ban do"]):
        text = "the group lays out the tunnel-entry options and chooses which route to take"
    elif focus == "medicine-allocation" and has_any(plain, ["moi nguoi mot phan thuoc", "nua phan", "chia thuoc", "phan thuoc"]):
        text = "the medicine is split between the named people under pressure and without enough for everyone"
    elif focus == "ration-pressure" and has_any(plain, ["con khat", "ngam moi", "nhin phan cua minh", "nuot nuoc bot", "giau con khat", "phan cua minh", "khat den dau"]):
        text = "someone studies the tiny ration share while another person tries to hide thirst under the group's gaze"
    elif focus == "danger-distraction":
        text = "a thrown object or sudden noise pulls the nearby danger sideways for one urgent moment"
    elif focus == "law-recital":
        text = "the harsh survival rules are spoken or shown in full view, and everyone measures what those rules will cost"
    elif focus == "debt-ledger":
        text = "the debt, interest, or name in the ledger is being argued over while everyone measures who will be bound by the deal"
    elif focus == "role-assignment":
        text = "someone is assigned a necessary survival role, and the group feels the weight of that responsibility settling into place"
    elif focus == "human-valuation":
        text = "someone coldly prices, retrieves, or describes people like assets, and the others react to that dehumanizing logic"
    elif focus == "base-founding":
        text = "the group names, defines, or reorganizes this place so it becomes a real base instead of a temporary stop"
    elif focus == "machine-maintenance":
        text = "the group listens to, repairs, feeds, or keeps the filter machine running because water depends on it"
    elif focus == "repair-logistics":
        text = "the group lays out the needed parts, tools, and repair steps for moving the injured or reaching the next route"
    elif focus == "hazard-crossing":
        text = "the group studies the deadly crossing rhythm and prepares how each person will get over alive"
    elif focus == "ration-stop" and has_any(plain, ["vach binh", "mot phan", "nua phan", "moi nguoi mot ngum", "chia nuoc"]):
        text = "the group measures out the last water and medicine portions while everyone watches what each person will get"
    elif focus == "group-dialogue" and has_any(plain, ["bo", "duong ham", "loi", "bo giap than", "vao ham"]):
        text = "one speaker questions the route danger while the others listen and weigh the tunnel options"
    elif focus == "group-dialogue" and has_any(plain, ["ta chi muon lam nguoi tu di", "tu di", "nghen lai"]):
        text = "the speaker insists on staying able to walk alone, and the emotional strain lands on everyone listening"
    elif focus == "group-dialogue" and has_any(plain, ["doi truong", "chia nuoc", "them nua ngum"]):
        text = "the speaker pushes for a ration choice while the others watch who will gain or lose the next sip"
    elif focus == "group-dialogue" and has_any(plain, ["nua ngum", "lac dau", "them nua ngum"]):
        text = "someone offers an extra sip, the child refuses, and the adults absorb what that choice means"
    elif focus == "group-dialogue" and has_any(plain, ["co phai hac nha khong", "co phai", "la ai", "nguoi tren xe lan kia"]):
        text = "someone challenges the identity of a vulnerable person, and everyone nearby tightens in anticipation of the answer"
    elif focus == "group-dialogue" and has_any(plain, ["giong nguoi lam an", "dang ghet cho nao", "doi giam gia", "vong vo", "thich"]):
        text = "the speakers trade sharp lines to test who is calmer, smarter, and more in control of the bargain"
    elif focus == "group-dialogue" and has_any(plain, ["tra tien", "tra gia", "noi chuyen gia", "nuoc mac hon", "cac vi can gi", "tin ve"]):
        text = "the trader and the visitors verbally test price, leverage, and how much the next answer or good will cost"
    elif focus == "group-dialogue" and has_any(plain, ["bao truoc", "can than", "anh hung", "khong quay lai"]):
        text = "someone throws out a blunt warning or rebuke, and the next move of the group shifts around it"
    elif focus == "group-dialogue" and has_any(plain, ["nguoi im", "ta khong uong", "khong can", "khong uong"]):
        text = "one person resists, another shuts them down, and the whole group feels the hard edge of that forced decision"
    elif focus == "group-dialogue" and has_any(plain, ["co nguoi dang o duoi", "o mot minh", "la gi cua nguoi", "co mui nguoi"]):
        text = "one side tests the other with cautious questions while everyone listens for the truth underneath the answers"
    elif focus == "group-dialogue" and has_any(plain, ["ta ngoi", "cac nguoi day", "di duoc", "khong di duoc", "mot minh di", "dung keo"]):
        text = "the group settles who can still move, who must be carried, and what burden each person takes next"
    elif focus == "board-exchange":
        text = "the child writes or reacts through the board while the others read, answer, or tease in the same beat"
    elif focus == "control-sabotage":
        text = "someone studies the old controls, lights, or lock system and realizes how cutting power could jam the doors or change the trap"
    elif focus == "water-inspection":
        text = "someone studies the boiling water and realizes the clean surface still carries the smell or threat hidden inside it"
    elif focus == "group-dialogue" and len(text.split()) > 18:
        text = "show the current speaker, listener, and the emotional exchange driving this beat"
    elif focus == "decision-reaction" and has_any(plain, ["doi truong", "moi hieu", "hai chuyen khac nhau", "khung"]):
        text = "the character freezes for a beat and realizes leadership means carrying other people's hunger and survival"
    elif focus == "interaction" and has_any(plain, ["khan giong", "khàn giọng", "anh hung", "bao truoc"]):
        text = "the injured speaker throws out a hoarse warning or rebuke, and the emotional sting lands in the pause after it"
    elif focus == "route-planning" and len(text.split()) > 18:
        text = "show the route options, the speaker indicating them, and the group's tactical choice"
    elif focus == "medicine-allocation" and len(text.split()) > 18:
        text = "show how the medicine or ration is being divided between the named people"
    elif focus == "market-bargain" and has_any(plain, ["tin la thu duy nhat", "nuoc mac hon", "tra tien", "vong vo", "cac vi can gi", "tin ve"]):
        text = "the trader and the visitors probe each other over price, value, and how much the goods or information are worth"
    elif focus == "market-bargain" and has_any(plain, ["doi nuoc cho tre con", "doi thuoc cho hai nguoi bi thuong", "doi nuoc", "doi thuoc"]):
        text = "the trade goods are placed on the table and the exact exchange is stated: water for the children and medicine for the wounded"
    elif focus == "market-bargain" and len(text.split()) > 18:
        text = "show the trade presentation or bargaining move exactly happening in this beat"
    elif focus in {"well-discovery", "resource-discovery"} and len(text.split()) > 18:
        text = "show the discovery action and the object's importance exactly as described"
    elif focus == "journey-column" and len(text.split()) > 18:
        text = "show the group's current movement beat and the survival strain shaping it"
    elif focus == "human-valuation" and len(text.split()) <= 8:
        text = "the speaker reduces a person to a file, price, or disposable asset while the others absorb the cruelty of it"
    elif focus == "human-valuation" and has_any(plain, ["vong so", "mot ngay thu duong", "tra cho nguoi nha"]):
        text = "a tagged trial-runner is displayed with a water price owed to their family, and the group recoils at a human life being listed like cargo"
    elif focus == "base-founding" and len(text.split()) <= 8:
        text = "the group lands on a name or shared rule that turns this rough shelter into a real base"
    elif focus == "machine-maintenance" and len(text.split()) <= 8:
        text = "someone diagnoses or nurses the filter machine because the whole camp depends on it staying alive"
    elif focus == "control-sabotage" and len(text.split()) <= 8:
        text = "someone spots the old control weakness and realizes the locks or doors can be jammed by cutting power"
    if len(text.split()) <= 3:
        if focus == "group-dialogue":
            text = "show the current speaker, listener, and the emotional pressure inside the exchange"
        elif focus == "board-exchange":
            text = "show the writing board, the child who uses it, and the reaction it triggers in the others"
        elif focus == "water-inspection":
            text = "show the suspicious water and the moment someone realizes it is not truly safe"
        elif focus == "ration-pressure":
            text = "show the ration share, the thirsty reaction, and the pressure around not having enough"
        elif focus == "danger-distraction":
            text = "show the decoy movement or sound and the nearby danger shifting toward it"
        elif focus == "ration-stop":
            text = "show the last ration being measured out while the whole group watches the decision"
        elif focus == "authority-introduction":
            text = "show the authority figure, the raised weapon or symbol, and everyone else's involuntary reaction"
        elif focus == "decision-reaction":
            text = "show the character stopping short as the meaning of the situation lands visibly on them"
    if focus == "decision-reaction" and len(text.split()) <= 8:
        text = "the character stops short as the survival meaning of the moment sinks in and changes the next choice"
    if not text:
        text = "show the current visible beat exactly as the narration describes it"
    return text[:180]


def infer_scene_center(narration, scene_state, actions, props, shot_type):
    plain = normalize_vi(narration)
    focus = scene_state.get("focus", "interaction")
    subject = infer_primary_subject(narration, scene_state)
    location = scene_state.get("location", "story-defined location matching the narration")
    action = clean_story_fragment(actions[0] if actions else infer_beat_goal(narration, scene_state, actions, props))
    obj = infer_primary_object(props, narration)
    kind = "subject-center"

    if focus in {"well-discovery", "well-probe", "written-water-warning", "hidden-survivor-probe", "poisoned-water-discovery", "resource-discovery", "track-discovery", "object-detail", "water-detail", "water-inspection", "danger-distraction", "base-resource-balance"}:
        kind = "object-center"
    elif focus in {"market-bargain", "threshold-negotiation", "group-dialogue", "route-planning", "medicine-allocation", "control-sabotage", "debt-ledger", "repair-logistics", "role-assignment", "human-valuation", "base-founding", "machine-maintenance", "camp-rules-recital", "acceptance-risk", "forced-route-test", "treatment-setup", "gain-cost-summary", "survival-values", "identity-probe"}:
        kind = "exchange-center"
    elif focus == "law-recital":
        kind = "object-center"
    elif focus in {"authority-introduction", "ration-pressure", "appraisal-glance", "child-observation"}:
        kind = "reaction-center"
    elif focus == "board-exchange":
        kind = "object-center"
    elif focus in {"journey-column", "radio-warning", "ration-stop", "doorway-threat", "ash-bluff", "dog-attack", "dog-pack", "medical-strain", "insect-combat", "hazard-crossing", "escape-burst"}:
        kind = "action-center"
    elif focus in {"decision-reaction", "tan-da-condition", "aftermath", "memory-flashback", "bitter-realization"}:
        kind = "reaction-center"
    elif "wide" in shot_type or "establishing" in shot_type or focus in {"survival-introduction", "location-transition", "mass-chaos"}:
        kind = "location-center"

    if has_any(plain, ["gieng cu", "mieng gieng", "lon sat treo bang day", "mui dong"]):
        obj = "the old well mouth, hanging tin can, or hidden water source described in the narration"
        kind = "object-center"
        if has_any(plain, ["buoc vai vao day", "buoc mieng vai", "tha xuong gieng", "nghe tieng kim loai cham vao", "day rung nhe"]):
            obj = "the old well mouth, cloth tied to the rope, and the metal contact deep below"
        elif has_any(plain, ["tam thep nho", "dong chu mo", "nuoc co nguoi giu", "tre con vao truoc", "nguoi lon tra gia sau"]):
            obj = "the old well mouth, hanging can, and the warning plate saying children enter first and adults pay later"
        elif has_any(plain, ["co mui nguoi", "co nguoi dang o duoi", "o mot minh", "thang nhai duoi gieng"]):
            obj = "the old well mouth, hanging can, and the hidden survivor or watcher below the water source"
        elif has_any(plain, ["xac nguoi troi duoi day", "loc bang xac", "mui mau trong nuoc sach", "nuoc sach co mui mau", "mui xac thoi hoi len"]):
            obj = "the old well mouth, tainted clean-looking water, and the corpse-filter truth hidden below"
    elif has_any(plain, ["bang viet", "tam bang", "viet len bang"]):
        obj = "Ninh's small writing board with the exact message or gesture described in the narration"
        kind = "object-center"
        if has_any(plain, ["ninh", "tieu mai"]):
            subject = "Ninh and Tieu Mai"
    elif has_any(plain, ["luat cua", "mot:", "hai:", "ba:", "tam thep treo", "chu sau", "khac len tam thep", "vet mau cu"]):
        obj = "the posted rules, metal plaque, or spoken survival code that everyone is measuring themselves against"
        kind = "object-center"
    elif kind == "exchange-center" and has_any(plain, ["viet xau", "doc cham", "khong noi duoc", "khong noi"]):
        obj = "Ninh's writing board as the object the others are reacting to"
    elif kind == "exchange-center" and has_any(plain, ["bang gia", "tra gia", "mot gao nuoc", "mot lieu thuoc"]):
        obj = "the trade board, ration terms, or goods being negotiated in the scene"
    elif kind == "exchange-center" and has_any(plain, ["no bao nhieu", "tinh lai", "hop dong viec", "ghi ten", "so no", "lai tinh theo ngay"]):
        obj = "the debt ledger, interest terms, or written obligation deciding who owes what"
    elif kind == "exchange-center" and has_any(plain, ["hom nay can mat cua nguoi", "can mat cua nguoi", "giao cho", "nguoi doc gio", "ta biet"]):
        obj = "the assigned role, task, or responsibility being placed on a specific person"
    elif kind == "exchange-center" and has_any(plain, ["ho so ghi ma so", "kho ban", "chua gap dung gia", "dung nguoi re hon", "khong con gia tri", "de dieu khien"]):
        obj = "the record, value logic, or retrieval claim reducing people to assets in the current exchange"
    elif kind == "exchange-center" and has_any(plain, ["vong so", "mot ngay thu duong", "tra cho nguoi nha"]):
        obj = "the numbered wrist ring, chest board, and water-price terms proving that a human life is being valued like cargo"
    elif kind == "exchange-center" and has_any(plain, ["muon o lai phai theo luat", "khong ban nguoi", "do chung phai bao", "nuoc chia theo viec va benh", "ai giau dao hai doi"]):
        obj = "the camp rules and shared terms of belonging that now define what staying with the group really means"
    elif kind == "exchange-center" and has_any(plain, ["se co nguoi phan", "van nhan", "co tay con vet xich", "vua thoat khoi vong so"]):
        obj = "the risk of betrayal or instability hanging over the choice to accept the newly freed survivors"
    elif kind == "exchange-center" and has_any(plain, ["kho den vang", "can ten", "ten noi nay", "trai cuu te", "dung can cu"]):
        obj = "the name, posted idea, or shared agreement turning this warehouse into a real base"
    elif kind == "exchange-center" and has_any(plain, ["dua vao goc kin", "ong thuoc gen qua han", "hai ong thuoc gen", "thuoc gen qua han"]):
        obj = "the expired gene-medicine tubes and the hidden treatment setup that survival now depends on"
    elif kind == "exchange-center" and has_any(plain, ["may loc", "loc nuoc", "than loc", "cat lot vao van", "nghe tieng may"]):
        obj = "the filter machine, valve, charcoal, or failing part everyone must understand to keep water flowing"
    elif kind == "exchange-center" and has_any(plain, ["vong bi", "mieng ton", "truc thang", "ton tu thao", "xe nho", "sua"]):
        obj = "the needed repair parts, tools, or improvised transport problem being worked through"
    elif kind == "exchange-center" and has_any(plain, ["moi lan gap nga re", "keo mot nguoi ra", "ra lenh di vao", "nen sap", "khong ai keo kip", "keo day sang nhanh c 1"]):
        obj = "the deadly branch, the trip line or false path, and the human body being used to test which route collapses first"
    elif kind == "exchange-center" and has_any(plain, ["cac vi can gi", "tin ve", "tra tien", "vong vo", "nuoc mac hon"]):
        obj = "the requested goods, information, or price terms being tested between trader and visitors"
    elif kind == "exchange-center" and has_any(plain, ["tranh duong nuoc", "tang gia nuoc", "gia re hon"]):
        obj = "the local water route leverage and the raised price pressure being used to trap the other side in a worse bargain"
    elif kind == "exchange-center" and has_any(plain, ["anh mat han luot qua", "luot qua xe lan", "dung lai o radio", "dung tren ban tay bang mau"]):
        obj = "the wheelchair, radio, wounds, and visible weakness being silently assessed for leverage"
    elif kind == "exchange-center" and has_any(plain, ["dua nuoc", "gao nuoc", "nuoc trong", "thay day"]):
        obj = "the clean water or ladle being offered, withheld, or inspected in the current exchange"
    elif kind == "exchange-center" and has_any(plain, ["bang viet", "viet xau", "doc cham", "khong noi duoc", "tam bang"]):
        obj = "the writing board carrying the exact child message or response that everyone is reacting to"
    elif kind == "exchange-center" and has_any(plain, ["toa thu nhat", "ban nuoc loc", "qua may cu", "bach nhi dua ho vao trong"]):
        obj = "the first Gray Station stall or train-car counter being shown to the newcomers"
    elif kind == "exchange-center" and has_any(plain, ["duong ham so 4", "loi chinh", "loi bao tri", "loi thoat nuoc", "ban do duong ray", "co may loi"]):
        obj = "the route map on the ground and the exact tunnel-entry options being discussed"
    elif kind == "exchange-center" and has_any(plain, ["moi nguoi mot phan thuoc", "nua phan", "chia thuoc", "uong thuoc", "phan thuoc"]):
        obj = "the medicine portions or survival doses being split between the named people"
    elif kind == "reaction-center" and has_any(plain, ["con khat", "ngam moi", "nhin phan cua minh", "giau con khat", "nuot nuoc bot"]):
        obj = "the ration share or withheld water/medicine creating the visible emotional pressure"
    elif kind == "reaction-center" and has_any(plain, ["chi con mot tay", "nhac bua len", "ca kho deu yen", "danh tieng"]):
        obj = "the one-handed hammer and the authority it carries in the current scene"
    elif kind == "object-center" and has_any(plain, ["hat giong", "nuoc dung cho hat", "it nuoc cho nguoi", "bat chao", "ho ngung suong", "nuoc dau vao"]):
        obj = "the water, seed box, or thin bowl of food carrying the visible tradeoff between surviving tonight and surviving later"
    elif has_any(plain, ["vien tinh thach", "rang cho hai ham", "dat len ban", "tui nho rang cho"]):
        obj = "the crystals, cracked stones, or bag of mutant teeth being placed on the table for trade"
        kind = "object-center"
    elif has_any(plain, ["radio", "tin hieu gen", "mo radio", "radio song", "gio radio", "tu radio", "tin hieu radio"]):
        obj = "the battered survival radio carrying the exact warning or message from the narration"
    elif has_any(plain, ["xe lan", "truc xe", "vong banh", "cot ket"]):
        obj = "the damaged wheelchair or improvised transport carrying the injured person"
        if has_any(plain, ["tan da", "tieu mai", "tieu bao", "tieu ngo"]):
            kind = "action-center"
    elif has_any(plain, ["dau giay", "vet chan", "hoa van tam giac", "manh quan vai", "vet quan vai"]):
        obj = "the exact footprints, cloth mark, or track clue the narration describes"
        kind = "object-center"
    elif has_any(plain, ["mui am", "vung nuoc doc", "mot vach nuoc", "bo qua bat cu mui am nao"]):
        obj = "the faint damp-air clue or possible poisoned water source the group is deciding whether to trust"
        kind = "object-center"
    elif has_any(plain, ["bat nuoc dang soi", "nuoc sach co mui mau", "mui mau trong nuoc", "nuoc dang soi"]):
        obj = "the bowl or vessel of clean-looking water that still carries a dangerous smell or contamination clue"
        kind = "object-center"
    elif has_any(plain, ["mau xuong roi xuong", "lan tren mai ton", "loc coc", "qua mu lao sang", "luong gio tanh"]):
        obj = "the thrown bait, clattering impact point, or creatures turning toward the distraction"
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


def prune_setting_for_focus(setting, scene_state, narration):
    plain = normalize_vi(narration)
    focus = scene_state.get("focus", "")
    location_plain = normalize_vi(scene_state.get("location", ""))
    if not setting:
        return setting
    pruned = list(setting)
    if "old railway line" in location_plain:
        pruned = [
            item for item in pruned
            if not any(token in normalize_vi(item) for token in [
                "shelter interior", "gray station", "warehouse-like interior", "train car functions as a separate stall"
            ])
        ] or pruned
    if "old well area" in location_plain:
        pruned = [
            item for item in pruned
            if not any(token in normalize_vi(item) for token in [
                "shelter interior", "gray station", "warehouse-like interior"
            ])
        ] or pruned
        if not any("old well area" in normalize_vi(item) or "hanging tin can" in normalize_vi(item) for item in pruned):
            pruned.insert(0, "the old well area with broken concrete, hanging tin can, and signs someone is already below")
    if "gray station" in location_plain:
        pruned = [
            item for item in pruned
            if not any(token in normalize_vi(item) for token in [
                "shelter interior", "old well area", "water-filter station", "burning lanes of district 17"
            ])
        ] or pruned
    if "burning lanes of district 17" in location_plain:
        pruned = [
            item for item in pruned
            if not any(token in normalize_vi(item) for token in [
                "shelter interior", "gray station", "old well area", "warehouse-like interior"
            ])
        ] or pruned
    if "tunnel 4" in location_plain:
        pruned = [
            item for item in pruned
            if not any(token in normalize_vi(item) for token in [
                "shelter interior", "gray station", "old railway line", "old well area"
            ])
        ] or pruned
    if focus in {"market-bargain", "human-valuation", "intake-registration", "debt-ledger", "appraisal-glance"}:
        pruned = [
            item for item in pruned
            if not any(token in normalize_vi(item) for token in [
                "tunnel 4", "inside the shelter around the last dirty water", "maintenance warehouse turned survival base"
            ])
        ] or pruned
    if focus in {"base-resource-balance", "machine-maintenance", "camp-rules-recital", "acceptance-risk", "gain-cost-summary", "survival-values"}:
        pruned = [
            item for item in pruned
            if not any(token in normalize_vi(item) for token in [
                "gray station", "rail-junction trading post"
            ])
        ] or pruned
    if focus in {"insect-combat", "hazard-crossing", "route-planning", "memory-navigation", "treatment-setup", "control-sabotage", "creature-threat"}:
        pruned = [
            item for item in pruned
            if not any(token in normalize_vi(item) for token in [
                "gray station", "rail-junction trading post"
            ])
        ] or pruned
    if focus == "escape-burst" and has_any(plain, ["toa", "mep ray", "ga xam"]):
        gray_station = [item for item in pruned if "gray station" in normalize_vi(item)]
        if gray_station:
            pruned = gray_station + [item for item in pruned if item not in gray_station]
    return pruned


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
    if focus in {"mass-chaos", "dog-attack", "dog-pack", "insect-combat"} or "action" in shot_type or "threat" in shot_type:
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
    if has_any(plain, ["gam gu voi hai con khac", "can xe mot cai xac", "dong xe phe lieu", "hai con cho khac", "quay dau ve phia cai xac"]):
        return "medium threat shot showing Lam Tich's cover position, the dogs, and the corpse behind the scrap vehicles"
    if has_any(plain, ["dam thang vao mat no", "mong vuot cao xuong", "lan vao duoi gam xe", "choc thang vao cai mom tach doi"]):
        return "violent survival action shot with body positions, weapon, and predator attack clearly readable"
    if has_any(plain, ["thit hop", "cai xac bi bay cho gam", "tui ao trong phong len"]):
        return "medium survival discovery shot showing the corpse, pocket target, and surrounding danger"
    if has_any(plain, ["khu 17 chay", "lua boc", "khoi den", "gao thet", "dan bo chay", "nguoi bo chay", "mai leu chay", "chay ruc", "can leu rach"]):
        return "wide or medium survival action shot with burning shelters, fleeing survivors, and attack direction readable"
    if primary_beat == "insect-combat":
        return "cramped tunnel-combat shot with armored insects, improvised tools, electric water danger, and the group's body positions clearly readable"
    if primary_beat == "market-bargain":
        return "market exchange shot with seller, visitors, trade goods, and power balance clearly readable"
    if primary_beat == "appraisal-glance":
        return "appraisal-glance shot with the calculating observer, the scanned survivors or gear, and the silent power read clearly visible at a glance"
    if primary_beat == "authority-introduction":
        return "authority-introduction shot with the person, weapon, and everyone else's reaction to their presence clearly readable"
    if primary_beat == "camp-rules-recital":
        return "camp-rules-recital shot with the speaker laying out survival rules, the listeners absorbing them, and the social cost of belonging clearly readable"
    if primary_beat == "acceptance-risk":
        return "acceptance-risk shot with the defender, the doubters, and the newly arrived survivors whose danger is being debated clearly readable"
    if primary_beat == "danger-distraction":
        return "danger-distraction shot with the decoy object or noise, the nearby threat shifting toward it, and the survivors reacting in the same frame"
    if primary_beat == "board-exchange":
        return "board-exchange shot with the writing board, the child using it, and the exact response from the others clearly readable"
    if primary_beat == "control-sabotage":
        return "control-sabotage shot with the panel, lock lights or old controls, and the person realizing how to jam, cut, or exploit the system clearly readable"
    if primary_beat == "forced-route-test":
        return "forced-route-test shot with the dangerous branch, the person pushed ahead first, and the people behind them reading the trap through that risk clearly readable"
    if primary_beat == "treatment-setup":
        return "treatment-setup shot with the hidden corner, the injured survivor, and the expired medicine that may still have to be used clearly readable"
    if primary_beat == "law-recital":
        return "law-recital shot with the posted rules or spoken code, the listeners, and the brutal meaning clearly readable"
    if primary_beat == "debt-ledger":
        return "debt-ledger shot with the ledger, the named debtor, and the social pressure of the terms clearly readable"
    if primary_beat == "human-valuation":
        return "human-valuation shot with the speaker treating people like priced assets, the target of that logic, and the surrounding reaction clearly readable"
    if primary_beat == "intake-registration":
        return "intake-registration shot with the queue, the person collecting names and skills, and the survival screening details clearly readable"
    if primary_beat == "base-founding":
        return "base-founding shot with the warehouse space, the speaker naming or defining it, and the group's response to making it a real base clearly readable"
    if primary_beat == "base-resource-balance":
        return "base-resource-balance shot with the precious water, seeds, or thin food, and the people forced to decide what tomorrow is worth clearly readable"
    if primary_beat == "gain-cost-summary":
        return "gain-cost-summary shot with the expanded group, the newly won supplies, and the heavier burden settling in at the same moment"
    if primary_beat == "survival-values":
        return "survival-values shot with the speaker stating the wasteland's brutal logic and the listeners absorbing exactly what now matters more than comfort or the dead"
    if primary_beat == "machine-maintenance":
        return "machine-maintenance shot with the failing filter machine, the person working on it, and the survival stakes of keeping it running clearly readable"
    if primary_beat == "diagnostic-pressure":
        return "diagnostic-pressure shot with the speaker naming the body's collapse, the threatened person, and the danger of delay clearly readable"
    if primary_beat == "role-assignment":
        return "role-assignment shot with the assigned person, the speaker, and the responsibility being handed over clearly readable"
    if primary_beat == "repair-logistics":
        return "repair-logistics shot with the needed parts, the person solving it, and the movement problem being fixed clearly readable"
    if primary_beat == "hazard-crossing":
        return "hazard-crossing shot with the dangerous path, the timing cue, and the next person preparing to move clearly readable"
    if primary_beat == "memory-navigation":
        return "memory-navigation shot with the remembered tunnel markers, the person guiding from memory, and the route clues clearly readable"
    if primary_beat == "route-planning":
        return "route-planning shot with the map, the speakers, and the tunnel-entry options clearly readable"
    if primary_beat == "water-inspection":
        return "water-inspection shot with the bowl or vessel, the suspicious clean water, and the reaction to the hidden contamination clearly readable"
    if primary_beat == "well-probe":
        return "well-probe shot with the rope, tied cloth or can, the old well mouth, and the listener reacting to the metal contact below clearly readable"
    if primary_beat == "written-water-warning":
        return "written-water-warning shot with the warning plate, the old well mouth, and the reader realizing children enter first while adults pay later"
    if primary_beat == "hidden-survivor-probe":
        return "hidden-survivor-probe shot with the old well mouth, the watcher or voice below, and the survivors testing whether they can trust what is hidden there"
    if primary_beat == "poisoned-water-discovery":
        return "poisoned-water-discovery shot with the old well mouth, the tainted clean-looking water, and the corpse-based truth hidden below clearly readable"
    if primary_beat == "medicine-allocation":
        return "medicine-allocation shot with the portions, recipients, and survival stakes clearly readable"
    if primary_beat == "ration-pressure":
        return "ration-pressure reaction shot with the scarce portion, the thirsty reaction, and the social pressure clearly readable"
    if primary_beat == "creature-threat":
        return "creature-threat shot with the grinding jaws or armored body, the nearest survivor's fear, and the immediate danger clearly readable"
    if primary_beat == "escape-burst":
        return "escape-burst action shot with the group breaking cover, the carried salvage or core, and the pursuing threat window clearly readable"
    if primary_beat == "identity-probe":
        return "identity-probe shot with the questioned person, the challenger, and the group's immediate alarm clearly readable"
    if has_any(plain, ["dat len ban", "vien tinh thach", "tui nho rang cho", "rang cho hai ham"]):
        return "trade presentation shot with the presenter, table surface, and exact goods clearly readable at first glance"
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
        if has_any(plain, ["co phai hac nha khong", "co phai", "la ai", "nguoi tren xe lan kia"]):
            return "identity-probe shot with the questioned person, the challenger, and the group's immediate alarm clearly readable"
        if has_any(plain, ["giong nguoi lam an", "dang ghet cho nao", "doi giam gia", "vong vo", "thich"]):
            return "verbal-sparring shot with both speakers, their posture, and the contest for social control clearly readable"
        if has_any(plain, ["bao truoc", "can than", "anh hung", "khong quay lai", "da bao", "chay la chet", "dung day cho chet", "dung chay"]):
            return "warning-rebuke shot with the speaker, the target, and the tense pause after the warning clearly readable"
        if has_any(plain, ["nguoi im", "ta khong uong", "khong can", "khong uong"]):
            return "command-pressure shot with the resisting person, the enforcer, and the forced compliance clearly readable"
        if has_any(plain, ["co nguoi dang o duoi", "o mot minh", "la gi cua nguoi", "co mui nguoi"]):
            return "trust-test dialogue shot with both sides probing each other and the hidden risk still hanging in the frame"
        if has_any(plain, ["nua ngum", "them nua ngum", "chia nuoc", "cho uong"]):
            return "ration-command dialogue shot with the speaker, recipient, and the contested sip or dose clearly readable"
        if has_any(plain, ["ta ngoi", "cac nguoi day", "di duoc", "khong di duoc", "mot minh di", "dung keo"]):
            return "movement-decision dialogue shot with the group deciding who moves, who carries, and how the next step physically happens"
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
        return "medical strain shot focused on the injured person, wound risk, and whoever is reacting nearby"
    if has_any(plain, ["dua nap hop", "dua binh nuoc", "ben moi", "anh uong di", "nhuong nuoc", "dua lai bang hai tay"]):
        return "ration exchange shot focused on the exact people, water container, and emotional pressure described in the narration"
    if has_any(plain, ["ngoai cua leu", "qua khe ton", "bong nguoi", "hau seo", "tieng buoc chan", "mo cua"]):
        return "threshold danger shot with the current barrier, threatened side, and outside pressure clearly readable"
    if has_any(plain, ["keo thung", "dap nghieng", "tro xam", "nam do"]):
        return "action shot at the shelter entrance as ash spills outward and everyone reacts"
    if has_any(plain, ["di xa", "quay dau", "ngoi xuong canh han", "dem nay ta co the sot lan hai"]):
        return "quiet aftermath shot showing who remains, what changed, and how danger still lingers after the interruption"
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
    return "story-accurate cinematic shot focused on the exact narrated subject, action, object, and setting of this beat"


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
    if not characters and scene_state["focus"] not in {"object-detail", "water-detail", "water-inspection", "well-discovery", "resource-discovery", "track-discovery"}:
        add_unique(characters, "the exact survivor or person described in the narration, shown from side or back view")
    if scene_state["focus"] in {"board-exchange", "ration-pressure", "appraisal-glance", "market-bargain", "human-valuation"}:
        filtered_characters = []
        for item in characters:
            item_plain = normalize_vi(item)
            if "the exact survivor or person described in the narration" in item_plain:
                continue
            add_unique(filtered_characters, item)
        if filtered_characters:
            characters = filtered_characters

    add_unique(setting, scene_state["location"])
    if not setting:
        add_unique(setting, "District 17 wasteland survival setting")
    for detail in story_setting_details(narration, continuity):
        add_unique(setting, detail)
    setting = prune_setting_for_focus(setting, scene_state, narration)

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
    elif focus == "authority-introduction":
        mood = ["hard-earned authority, silence under pressure, and respect built from brutal survival history"]
    elif focus == "insect-combat":
        mood = ["cramped tunnel danger, armored insect violence, and improvised teamwork under electric-water risk"]
    elif focus == "route-planning":
        mood = ["tense tactical planning, limited options, and everyone measuring risk before the next move"]
    elif focus == "board-exchange":
        mood = ["small human warmth, vulnerability, and social tension carried through the writing board exchange"]
    elif focus == "control-sabotage":
        mood = ["tight containment, fragile opportunity, and the dangerous intelligence of reading an old control system under pressure"]
    elif focus == "law-recital":
        mood = ["hard survival law, social judgment, and the cold cost of belonging to this group"]
    elif focus == "debt-ledger":
        mood = ["cold debt pressure, written obligation, and the social violence hidden inside bookkeeping"]
    elif focus == "human-valuation":
        mood = ["dehumanizing market logic, cold efficiency, and the moral sickness of pricing a human life like inventory"]
    elif focus == "base-founding":
        mood = ["hard-won shelter, rough collective purpose, and the fragile hope of turning survival into a real base"]
    elif focus == "machine-maintenance":
        mood = ["practical strain, improvised engineering, and constant anxiety because water or survival depends on the machine holding together"]
    elif focus == "role-assignment":
        mood = ["quiet authority, practical necessity, and the emotional weight of being trusted or burdened with a task"]
    elif focus == "repair-logistics":
        mood = ["practical urgency, scrap ingenuity, and tense cooperation around making something barely work"]
    elif focus == "hazard-crossing":
        mood = ["timed danger, controlled fear, and full-body concentration as each step could kill someone"]
    elif focus == "water-inspection":
        mood = ["suspicion, unease, and the sickening realization that something is wrong with seemingly clean water"]
    elif focus == "danger-distraction":
        mood = ["split-second survival cunning as attention is pulled sideways by noise, bait, or movement"]
    elif focus == "medicine-allocation":
        mood = ["scarcity, triage pressure, and the quiet cruelty of deciding who gets the medicine"]
    elif focus == "ration-pressure":
        mood = ["thirst, restraint, and the shame or pain of not having enough for everyone"]
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
        f"{STORY_FIRST_VISUAL_RULE} "
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
            "aliases": ["Lam Tich", "lâm tịch"],
            "traits": ["honest", "afraid", "cold"],
            "voice_note": "fragile but stubborn, soft inner voice, sharper under survival pressure",
        }
    if "tan da" in plain:
        characters["Tần Dã"] = {
            "gender": "male",
            "voice": "vi-male",
            "aliases": ["Tan Da", "tần dã"],
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


