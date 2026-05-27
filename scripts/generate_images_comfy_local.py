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
    "cropped face, face out of frame, hidden face, faceless, over-smoothed face, childlike doll face, "
    "solo portrait, single person, close-up portrait, extreme close-up, cropped body, missing second character"
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
    # SD 1.5 CLIP truncates long prompts, so put the essential face/composition
    # control at the very front instead of burying it after story context.
    lower_prompt = prompt.lower()
    two_character_scene = (
        ("woman" in lower_prompt and "man" in lower_prompt)
        or ("lam tich" in lower_prompt and "tan da" in lower_prompt)
        or ("lâm tịch" in lower_prompt and "tần dã" in lower_prompt)
    )
    if two_character_scene:
        face_control = (
            "medium-wide two-character cinematic shot, both full heads visible, both faces readable, "
            "beautiful youthful Asian maiden scavenger woman kneeling on the left, soft delicate natural face under grime, "
            "injured black-clad man lying half-reclined on the right, "
            "warm oil lantern between them, torn tarp shelter, no solo portrait, no close-up crop"
        )
    else:
        face_control = (
            "medium cinematic story shot, full head visible, clear natural Asian human face, "
            "readable eyes nose mouth and jaw, no facial deformity, story-accurate character blocking, "
            "dirty post-apocalyptic survival drama, no close-up crop"
        )
    if face_control.lower() not in prompt.lower():
        prompt = f"{face_control}, {prompt}"
    if DEFAULT_POSITIVE_SUFFIX.lower() not in prompt.lower():
        prompt = f"{prompt}, {DEFAULT_POSITIVE_SUFFIX}"
    return prompt


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
    two_character_scene = (
        ("woman" in lower_prompt and "man" in lower_prompt)
        or ("lam tich" in lower_prompt and "tan da" in lower_prompt)
        or ("lâm tịch" in lower_prompt and "tần dã" in lower_prompt)
    )
    if "close" in shot_type or "detail" in shot_type:
        face_control = (
            "close survival detail shot, story-specific props and hands readable, "
            "do not repeat the same full shelter composition, keep only the character parts needed for this action visible, "
            "no solo glamour portrait"
        )
    elif "wide" in shot_type or "establishing" in shot_type:
        face_control = (
            "wide establishing cinematic shot, environment scale clearly visible, "
            "characters smaller in frame but still identifiable, no repeated medium two-shot framing"
        )
    elif "action" in shot_type or "predator" in shot_type or "threat" in shot_type or "hiding" in action_text:
        face_control = (
            "dynamic cinematic action shot, readable movement and threat direction, "
            "change camera angle from the calm shelter two-shot, maintain identity but not the same pose"
        )
    elif two_character_scene:
        face_control = (
            "medium-wide two-character cinematic shot, both full heads visible, both faces readable, "
            "beautiful youthful Asian maiden scavenger woman kneeling on the left, soft delicate natural face under grime, "
            "injured black-clad man lying half-reclined on the right, warm oil lantern between them, torn tarp shelter, "
            "no solo portrait, no close-up crop"
        )
    else:
        face_control = (
            "medium cinematic story shot, full head visible, clear natural Asian human face, "
            "readable eyes nose mouth and jaw, no facial deformity, story-accurate character blocking, "
            "dirty post-apocalyptic survival drama, no close-up crop"
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
            args.width, args.height = 512, 704
        args.steps = min(args.steps, 20)
        args.hires_scale = min(args.hires_scale, 1.25)
        args.hires_steps = min(args.hires_steps, 8)
        args.vae_tile_size = min(args.vae_tile_size, 320)
    elif args.preset == "quality":
        if not args.width and not args.height:
            args.width, args.height = 576, 832
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


def generate_scene(args: argparse.Namespace, scene: dict[str, Any], index: int, storyboard_dir: Path, assets_dir: Path) -> Path:
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
    parser.add_argument("--comfy-input-dir", type=Path, default=WORK_ROOT / "ComfyUI_windows_portable_nvidia" / "ComfyUI_windows_portable" / "ComfyUI" / "input")
    parser.add_argument("--output-format", default="png")
    parser.add_argument("--prefix", default="auto-video-local")
    parser.add_argument("--comfy-output-dir", type=Path, default=WORK_ROOT / "ComfyUI_windows_portable_nvidia" / "ComfyUI_windows_portable" / "ComfyUI" / "output")
    parser.add_argument("--seed", type=int, default=23052026)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
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
