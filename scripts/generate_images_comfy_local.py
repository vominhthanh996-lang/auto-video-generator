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
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from PIL import Image
from path_defaults import default_comfy_input_dir, default_comfy_output_dir, default_comfy_root

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
WORK_ROOT = REPO_ROOT.parent


DEFAULT_POSITIVE_SUFFIX = (
    "clear natural human faces, anatomically correct eyes nose mouth and jaw, readable facial expression, "
    "the word woman means a clearly adult female character with feminine facial structure and feminine body language, "
    "the word man means a clearly adult male character with masculine facial structure and masculine body language, "
    "female characters must read clearly female, male characters must read clearly male, no androgynous face, no gender ambiguity, "
    "for Lam Tich scenes: exceptionally beautiful readable female face, clearly visible face, expressive eyes, feminine facial structure, short black hair framing the face without covering it, subtly glamorous and captivating without explicit sexualization, "
    "for Tan Da scenes: exceptionally handsome readable male face, sharp masculine jawline, strong brows, steady heroic eyes, masculine neck and shoulders, rugged protective aura, "
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
    "fused bodies, merged bodies, overlapping bodies, detached head, floating head, extra person fragment, extra arm, extra hand, extra leg, missing arm, missing leg, tangled limbs, broken wrists, broken elbows, broken knees, impossible pose, "
    "cropped face, face out of frame, hidden face, faceless, over-smoothed face, childlike doll face, "
    "solo portrait, single person, close-up portrait, extreme close-up, cropped body, missing second character, "
    "nude, naked, topless, shirtless woman, bare chest, bare torso, exposed torso, exposed breasts, exposed nipples, areola, "
    "underboob, sideboob, cleavage focus, exposed navel, full bare abdomen, lingerie, bikini, underwear, bra, bralette, crop top, deep neckline, off-shoulder, bare shoulders, "
    "see-through clothing, wet revealing clothing, erotic pose, seductive pose, pin-up pose, reclining pin-up pose, spread legs, "
    "sexualized body, sexualized minor, childlike body, teen girl, underage, fetish, voyeuristic framing, "
    "focal point on breasts, focal point on buttocks, focal point on crotch, torso glamour shot, waist fetish framing, "
    "open jacket with bare torso, open jacket, unbuttoned jacket, open shirt, wardrobe malfunction, boudoir, sultry expression, bedroom eyes, glamour pose, visible chest skin, visible torso skin, visible stomach skin, "
    "androgynous face, gender ambiguous face, masculine woman, feminine man, gender swap, woman with male facial structure, man with feminine facial structure, weak jawline on male lead, soft feminine male face, villain glare on male lead"
)

RATIO_TO_SIZE = {
    "9:16": (512, 768),
    "3:4": (576, 768),
    "2:3": (512, 768),
    "1:1": (640, 640),
    "16:9": (1280, 720),
}

CHECKPOINT_PREFERENCES = [
    "ytsafe_mix",
    "dreamsafe",
    "rv6mix",
    "dreamshaper",
    "realisticvision",
    "cyberrealistic",
    "epicrealism",
    "photon",
    "majicmixrealistic",
    "deliberate",
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

SAFETY_RETRY_POSITIVE = (
    "fully clothed, chest and torso fully covered, no cleavage, no bikini, no lingerie, "
    "practical survival outfit with secure top coverage, YouTube-safe framing"
)

SAFETY_RETRY_NEGATIVE = (
    "nudity, nipples, areola, sideboob, underboob, cleavage, exposed breasts, exposed buttocks, thong, bikini, lingerie, "
    "open shirt, open jacket, bra visible, underwear visible, see-through clothing, erotic framing, erotic pose"
)


class SafetyClassifierClient:
    def __init__(self, process: subprocess.Popen[str], model_name: str) -> None:
        self.process = process
        self.model_name = model_name

    def classify(self, image_path: Path, threshold: float) -> dict[str, Any]:
        if not self.process.stdin or not self.process.stdout:
            raise SystemExit("NSFW classifier process is missing stdio pipes.")
        payload = {"image": str(image_path.resolve()), "threshold": threshold}
        self.process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            stderr = ""
            if self.process.stderr:
                try:
                    stderr = self.process.stderr.read()
                except Exception:
                    stderr = ""
            raise SystemExit(f"NSFW classifier process exited unexpectedly. {stderr}".strip())
        result = json.loads(line)
        if "error" in result:
            raise SystemExit(f"NSFW classifier error: {result['error']}")
        return result

    def close(self) -> None:
        try:
            if self.process.stdin:
                self.process.stdin.close()
        except Exception:
            pass
        try:
            self.process.terminate()
            self.process.wait(timeout=5)
        except Exception:
            try:
                self.process.kill()
            except Exception:
                pass


def start_safety_classifier(args: argparse.Namespace) -> SafetyClassifierClient | None:
    if not args.enable_nsfw_classifier:
        return None
    helper = (SCRIPT_DIR / "check_image_safety.py").resolve()
    comfy_python = (default_comfy_root(REPO_ROOT) / "python_embeded" / "python.exe").resolve()
    if not helper.exists():
        raise SystemExit(f"Safety helper script is missing: {helper}")
    if not comfy_python.exists():
        raise SystemExit(f"Comfy embedded Python was not found: {comfy_python}")
    env = os.environ.copy()
    env.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    process = subprocess.Popen(
        [str(comfy_python), str(helper), "--serve", "--model", args.nsfw_classifier_model],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
        env=env,
    )
    return SafetyClassifierClient(process, args.nsfw_classifier_model)


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


def scene_prompt(scene: dict[str, Any]) -> str:
    prompt = (
        scene.get("comfy_prompt")
        or scene.get("image_prompt")
        or scene.get("stability_prompt")
        or scene.get("visual")
        or scene.get("text")
        or scene.get("narration")
        or ""
    )
    prompt = str(prompt).strip()
    if not prompt:
        return ""
    shot_type = str(scene.get("visual_shot_type") or "").strip().lower()
    action_text = ", ".join(str(item).strip() for item in (scene.get("visual_action") or []) if str(item).strip()).lower()
    lower_prompt = prompt.lower()
    must_show_text = " ".join(str(item).strip() for item in (scene.get("visual_must_show") or []) if str(item).strip()).lower()
    combined_text = f"{lower_prompt} {must_show_text} {action_text}"
    two_character_scene = (
        ("lam tich" in combined_text and "tan da" in combined_text)
        or ("two share" in combined_text)
        or ("two measure the next danger together" in combined_text)
    )
    if "close" in shot_type or "detail" in shot_type:
        face_control = (
            "close survival detail shot, story-specific props and hands readable, face optional, "
            "keep only face, hands, sleeves, or props visible for this action, no chest visible, no torso visible, no shoulder visible, no twisted limbs, no overlapping bodies, "
            "do not repeat the same full shelter composition, no solo glamour portrait, "
            "fully clothed with practical layered survival jacket and covered long-sleeved shirt, no nudity, no bare chest, no exposed torso, no exposed shoulders, no cleavage focus, no exposed navel, no sexualized pose"
        )
        if "lam tich" in combined_text:
            face_control = (
                "close or medium-close survival character shot, Lam Tich's face clearly visible and readable, exceptionally beautiful female face, expressive eyes, short black hair framing the face, clearly feminine features, subtly glamorous presence, "
                "hands or props may share frame but her face must remain visible, no chest visible, no torso visible, no shoulder visible, no twisted limbs, "
                "no solo glamour portrait, no fashion beauty pose, fully clothed with practical layered survival jacket and covered long-sleeved shirt, "
                "no nudity, no bare chest, no exposed torso, no exposed shoulders, no cleavage focus, no exposed navel, no sexualized pose"
            )
    elif "wide" in shot_type or "establishing" in shot_type:
        face_control = (
            "wide establishing cinematic shot, environment scale clearly visible, "
            "characters smaller in frame but still identifiable, no repeated medium two-shot framing, "
            "summer wasteland outfit with secure chest and torso coverage, practical short bottoms, and tasteful collarbone, arms, and legs visibility, never a focal point, no nudity, no bare chest, no exposed torso, no navel, no sexualized pose, no chest-or-waist focal framing"
        )
        if "lam tich" in combined_text:
            face_control = (
                "wide or medium-wide establishing shot with Lam Tich still readable in the foreground or midground, her face clearly visible and identifiable, exceptionally beautiful female face, short black hair, clearly feminine features, subtle glamorous presence, "
                "do not make Lam Tich a tiny unreadable silhouette, environment scale visible but face still readable, "
                "summer wasteland outfit with secure chest and torso coverage, practical short bottoms, "
                "allow a modest natural neckline and tasteful collarbone hint plus visible arms and legs, never a focal point, no nudity, no bare chest, no exposed torso, no navel, no sexualized pose, no chest-or-waist focal framing"
            )
    elif "action" in shot_type or "predator" in shot_type or "threat" in shot_type or "hiding" in action_text:
        face_control = (
            "dynamic cinematic action shot, readable movement and threat direction, "
            "change camera angle from the calm shelter two-shot, maintain identity but not the same pose, "
            "summer wasteland outfit with secure chest and torso coverage, practical short bottoms, modest neckline, visible arms and legs, never a focal point, no nudity, no bare chest, no exposed torso, no navel, no sexualized pose, no chest-or-waist focal framing"
        )
    elif two_character_scene:
        face_control = (
            "medium two-character cinematic shot, both full heads visible, both faces readable, two clearly separate bodies, no body overlap, no one lying across the other, no detached head, "
            "beautiful short-haired adult Asian scavenger woman in rugged layered wasteland clothing kneeling on the left, exceptionally beautiful clearly female face, "
            "summer wasteland outfit with a flattering lightweight fitted outer layer over a secure dark inner top that fully covers chest and torso, practical short bottoms, "
            "soft tired natural face under grime, quietly attractive and subtly glamorous without explicit sexualization, Lam Tich face clearly visible and readable, allow a modest natural neckline and tasteful collarbone hint plus visible arms and legs, never a focal point, "
            "injured black-clad man lying half-reclined on the right on his own separate bedding or ground space, clearly male face and masculine structure, exceptionally handsome weathered face, sharp jawline, steady heroic eyes, broad shoulders and strong arms visible through clothing, warm oil lantern between them, torn tarp shelter, "
            "no solo portrait, no close-up crop, YouTube-safe survival drama, no nudity, no bare chest, no exposed torso, no cleavage focus, no navel, no sexualized pose, no chest-or-waist focal framing"
        )
    else:
        face_control = (
            "medium cinematic story shot, half-body preferred over full-body when anatomy is complex, both hands or clear body action visible, full head visible, clear natural beautiful Asian human face, short rough layered hair, clearly female face when the scene is Lam Tich, clearly male face when the scene is Tan Da, "
            "readable eyes nose mouth and jaw, no facial deformity, no androgynous face, story-accurate character blocking, no glamour portrait framing, "
            "dirty post-apocalyptic survival drama, summer wasteland outfit with a flattering lightweight fitted outer layer over a secure dark inner top that fully covers chest and torso, practical short bottoms, allow a modest natural neckline and tasteful collarbone hint, visible arms and legs, no visible chest skin, quietly attractive and subtly glamorous without explicit sexualization, Lam Tich face must stay clearly visible and readable when she is the scene focus, Tan Da must read as exceptionally handsome masculine adult male with sharp jawline, steady heroic eyes, strong shoulders and arms through posture and clothing, no tangled limbs, no impossible pose, "
            "no close-up crop, no fashion pose, "
            "YouTube-safe, no nudity, no bare chest, no exposed torso, no cleavage focus, no navel, no sexualized pose, no chest-or-waist focal framing"
        )
    if face_control.lower() not in prompt.lower():
        prompt = f"{face_control}, {prompt}"
    if DEFAULT_POSITIVE_SUFFIX.lower() not in prompt.lower():
        prompt = f"{prompt}, {DEFAULT_POSITIVE_SUFFIX}"
    return prompt


def scene_reference_policy(scene: dict[str, Any], default_reference: str, default_denoise: float) -> tuple[str, float | None]:
    if not default_reference:
        return "", None
    shot_type = str(scene.get("visual_shot_type") or "").strip().lower()
    action_text = ", ".join(str(item).strip() for item in (scene.get("visual_action") or []) if str(item).strip()).lower()
    beat_type = str(scene.get("beat_type") or "").strip().lower()
    transition = str(scene.get("transition_from_previous") or "").strip().lower()
    beat_goal = str(scene.get("beat_goal") or "").strip().lower()
    scene_id = str(scene.get("id") or "")
    if scene_id.endswith("001"):
        return default_reference, min(max(default_denoise, 0.26), 0.30)
    if "close" in shot_type or "detail" in shot_type:
        return "", None
    if beat_type in {"location-transition", "mass-chaos", "dog-attack", "dog-pack", "dog-awakening"}:
        return "", None
    if any(token in transition for token in ["buoc", "qua cong", "vao sanh", "cho thang may", "vao phong", "mo cua"]):
        return "", None
    if any(token in beat_goal for token in ["movement through the current location sequence", "predator threat", "survival response"]):
        return "", None
    if "wide" in shot_type or "establishing" in shot_type:
        return "", None
    if "action" in shot_type or "predator" in shot_type or "threat" in shot_type or "hiding" in action_text:
        return "", None
    return default_reference, min(default_denoise, 0.24)


def node_choices(object_info: dict[str, Any], class_type: str, input_name: str) -> list[str]:
    node = object_info.get(class_type, {})
    required = node.get("input", {}).get("required", {})
    optional = node.get("input", {}).get("optional", {})
    spec = required.get(input_name) or optional.get(input_name) or []
    if isinstance(spec, list) and spec and isinstance(spec[0], list):
        return [str(item) for item in spec[0]]
    if isinstance(spec, list) and len(spec) >= 2 and spec[0] == "COMBO" and isinstance(spec[1], dict):
        options = spec[1].get("options", [])
        if isinstance(options, list):
            return [str(item) for item in options]
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
            safe_sizes = {
                "16:9": (896, 504),
                "9:16": (432, 768),
                "3:4": (576, 768),
                "2:3": (512, 768),
                "1:1": (576, 576),
            }
            args.width, args.height = safe_sizes.get(args.aspect_ratio, size_for_ratio(args.aspect_ratio))
        args.steps = min(args.steps, 20)
        args.hires_scale = min(args.hires_scale, 1.2)
        args.hires_steps = min(args.hires_steps, 6)
        args.hires_denoise = min(args.hires_denoise, 0.28)
        args.vae_tile_size = min(args.vae_tile_size, 256)
    elif args.preset == "quality":
        if not args.width and not args.height:
            quality_sizes = {
                "16:9": (896, 512),
                "9:16": (576, 1024),
                "3:4": (640, 896),
                "2:3": (640, 960),
                "1:1": (768, 768),
            }
            args.width, args.height = quality_sizes.get(args.aspect_ratio, size_for_ratio(args.aspect_ratio))
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


def skin_component_metrics(path: Path) -> dict[str, float]:
    image = Image.open(path).convert("RGB")
    image.thumbnail((160, 160))
    rgb = image.load()
    ycbcr = image.convert("YCbCr")
    ycbcr_px = ycbcr.load()
    width, height = image.size
    if width == 0 or height == 0:
        return {"overall": 0.0, "upper_center": 0.0, "lower_center": 0.0, "largest_component": 0.0}

    mask = [[False for _ in range(width)] for _ in range(height)]
    total_skin = 0
    upper_center_skin = 0
    lower_center_skin = 0
    upper_center_total = 0
    lower_center_total = 0
    center_x0 = int(width * 0.2)
    center_x1 = int(width * 0.8)
    upper_y1 = int(height * 0.45)
    lower_y0 = int(height * 0.45)

    for y in range(height):
        for x in range(width):
            r, g, b = rgb[x, y]
            yy, cb, cr = ycbcr_px[x, y]
            rgb_skin = r > 95 and g > 40 and b > 20 and (max(r, g, b) - min(r, g, b)) > 15 and abs(r - g) > 15 and r > g and r > b
            ycbcr_skin = yy > 60 and 80 <= cb <= 135 and 125 <= cr <= 180
            is_skin = rgb_skin and ycbcr_skin
            mask[y][x] = is_skin
            if is_skin:
                total_skin += 1
            if center_x0 <= x < center_x1 and y < upper_y1:
                upper_center_total += 1
                if is_skin:
                    upper_center_skin += 1
            if center_x0 <= x < center_x1 and y >= lower_y0:
                lower_center_total += 1
                if is_skin:
                    lower_center_skin += 1

    visited = [[False for _ in range(width)] for _ in range(height)]
    largest_component = 0
    for y in range(height):
        for x in range(width):
            if visited[y][x] or not mask[y][x]:
                continue
            stack = [(x, y)]
            visited[y][x] = True
            size = 0
            while stack:
                cx, cy = stack.pop()
                size += 1
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < width and 0 <= ny < height and not visited[ny][nx] and mask[ny][nx]:
                        visited[ny][nx] = True
                        stack.append((nx, ny))
            if size > largest_component:
                largest_component = size

    total_pixels = width * height
    return {
        "overall": round(total_skin / total_pixels, 4),
        "upper_center": round(upper_center_skin / max(1, upper_center_total), 4),
        "lower_center": round(lower_center_skin / max(1, lower_center_total), 4),
        "largest_component": round(largest_component / total_pixels, 4),
    }


def scene_needs_strict_safety(scene: dict[str, Any]) -> bool:
    combined = " ".join(
        [
            str(scene.get("image_prompt") or ""),
            str(scene.get("narration") or ""),
            " ".join(str(item) for item in (scene.get("visual_must_show") or [])),
            " ".join(str(item) for item in (scene.get("visual_action") or [])),
        ]
    ).lower()
    return any(token in combined for token in ["lam tich", "woman", "female", "nu", "co gai"])


def safety_rejection_reason(
    path: Path,
    scene: dict[str, Any],
    args: argparse.Namespace,
    classifier: SafetyClassifierClient | None,
) -> tuple[list[str], dict[str, Any]]:
    metrics = skin_component_metrics(path)
    reasons: list[str] = []
    strict_scene = scene_needs_strict_safety(scene)
    if metrics["overall"] >= 0.34:
        reasons.append(f"overall skin ratio {metrics['overall']:.2f}")
    if strict_scene and metrics["upper_center"] >= 0.42:
        reasons.append(f"upper-center skin ratio {metrics['upper_center']:.2f}")
    if strict_scene and metrics["lower_center"] >= 0.42:
        reasons.append(f"lower-center skin ratio {metrics['lower_center']:.2f}")
    if strict_scene and metrics["largest_component"] >= 0.16 and metrics["overall"] >= 0.20:
        reasons.append(f"large contiguous skin region {metrics['largest_component']:.2f}")
    classifier_result: dict[str, Any] | None = None
    if classifier:
        threshold = args.nsfw_threshold_strict if strict_scene else args.nsfw_threshold
        classifier_result = classifier.classify(path, threshold)
        nsfw_score = float((classifier_result.get("scores") or {}).get("nsfw", 0.0))
        if classifier_result.get("reject"):
            reasons.append(f"classifier nsfw score {nsfw_score:.2f} >= {threshold:.2f}")
    return reasons, {
        "skin_heuristic": metrics,
        "classifier": classifier_result or {},
    }


def stricter_prompt(prompt: str) -> str:
    if SAFETY_RETRY_POSITIVE.lower() not in prompt.lower():
        return f"{SAFETY_RETRY_POSITIVE}, {prompt}"
    return prompt


def generate_scene(
    args: argparse.Namespace,
    scene: dict[str, Any],
    index: int,
    storyboard_dir: Path,
    assets_dir: Path,
    classifier: SafetyClassifierClient | None,
) -> Path:
    output = resolve(storyboard_dir, scene["image"]) if scene.get("image") else assets_dir / f"scene-{index + 1:02d}.{args.output_format}"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not args.overwrite:
        scene["image"] = relpath(output, storyboard_dir)
        return output
    prompt = scene_prompt(scene)
    if not prompt:
        raise SystemExit(f"Scene {index + 1} has no image prompt.")
    width, height = (args.width, args.height) if args.width and args.height else size_for_ratio(args.aspect_ratio)
    seed = args.seed + index if args.seed >= 0 else int(time.time() * 1000) % 2_147_483_647
    scene_reference_image, scene_reference_denoise = scene_reference_policy(scene, args.reference_image, args.reference_denoise)
    original_reference_image = args.reference_image
    original_reference_denoise = args.reference_denoise
    original_negative_prompt = args.negative_prompt
    accepted = False
    safety_metrics: dict[str, float] | None = None
    for safety_attempt in range(args.max_safety_retries + 1):
        attempt_prompt = prompt if safety_attempt == 0 else stricter_prompt(prompt)
        attempt_seed = seed + (safety_attempt * 7919)
        if safety_attempt > 0 and SAFETY_RETRY_NEGATIVE.lower() not in args.negative_prompt.lower():
            args.negative_prompt = f"{original_negative_prompt}, {SAFETY_RETRY_NEGATIVE}"
        args.reference_image = scene_reference_image
        args.reference_denoise = scene_reference_denoise if scene_reference_denoise is not None else original_reference_denoise
        try:
            workflow = build_sd15_workflow(args, attempt_prompt, attempt_seed, width, height)
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
        reasons, safety_metrics = safety_rejection_reason(output, scene, args, classifier)
        if not reasons:
            accepted = True
            seed = attempt_seed
            break
        print(
            f"Safety reject scene {index + 1} attempt {safety_attempt + 1}/{args.max_safety_retries + 1}: "
            f"{'; '.join(reasons)}"
        )
        try:
            output.unlink()
        except FileNotFoundError:
            pass
    args.negative_prompt = original_negative_prompt
    if not accepted:
        raise SystemExit(
            f"Scene {index + 1} rejected by local safety gate after {args.max_safety_retries + 1} attempts: {safety_metrics}"
        )
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
        "safety_gate": {
            "mode": "hybrid-heuristic-and-nsfw-classifier" if classifier else "local-skin-exposure-heuristic",
            "metrics": safety_metrics or {},
            "max_retries": args.max_safety_retries,
        },
    }
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate storyboard images locally with a low-VRAM cinematic ComfyUI workflow.")
    parser.add_argument("--storyboard", type=Path)
    parser.add_argument("--comfy-url", default=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188"))
    parser.add_argument("--checkpoint", default=os.environ.get("SD15_CHECKPOINT", "auto"))
    parser.add_argument("--vae", default=os.environ.get("SD15_VAE", "auto"))
    parser.add_argument("--lora", action="append", default=[], help="Optional LoRA name or name:model_strength:clip_strength.")
    parser.add_argument("--preset", choices=["safe", "balanced", "quality"], default="balanced")
    parser.add_argument("--aspect-ratio", default="9:16")
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
    parser.add_argument("--final-width", type=int, default=1080)
    parser.add_argument("--final-height", type=int, default=1920)
    parser.add_argument("--negative-prompt", default=DEFAULT_NEGATIVE)
    parser.add_argument("--reference-image", default=os.environ.get("LOCAL_IMAGE_REFERENCE", ""), help="Optional local image used as img2img composition reference.")
    parser.add_argument("--reference-denoise", type=float, default=0.28, help="Img2img denoise for --reference-image. Lower keeps composition, higher changes more.")
    parser.add_argument("--comfy-input-dir", type=Path, default=default_comfy_input_dir(REPO_ROOT))
    parser.add_argument("--output-format", default="png")
    parser.add_argument("--prefix", default="auto-video-local")
    parser.add_argument("--comfy-output-dir", type=Path, default=default_comfy_output_dir(REPO_ROOT))
    parser.add_argument("--seed", type=int, default=23052026)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--max-safety-retries", type=int, default=2)
    parser.add_argument("--enable-nsfw-classifier", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--nsfw-classifier-model", default=os.environ.get("NSFW_CLASSIFIER_MODEL", "Falconsai/nsfw_image_detection"))
    parser.add_argument("--nsfw-threshold", type=float, default=0.28, help="Reject image if classifier NSFW score meets this threshold.")
    parser.add_argument("--nsfw-threshold-strict", type=float, default=0.18, help="Stricter threshold for scenes focused on female lead/body exposure risk.")
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
    classifier = start_safety_classifier(args)
    try:
        for index, scene in enumerate(scenes[start_index:end_index], start=start_index):
            path = generate_scene(args, scene, index, storyboard_dir, assets_dir, classifier)
            generated.append(str(path))
            print(f"Generated local SD image: {path}")
    finally:
        if classifier:
            classifier.close()
    storyboard.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**selected, "storyboard": str(storyboard), "images": generated}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
