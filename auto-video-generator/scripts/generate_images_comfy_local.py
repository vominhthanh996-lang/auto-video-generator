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
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


DEFAULT_POSITIVE_SUFFIX = (
    "cinematic composition, realistic lighting, warm and cool color contrast, volumetric fog, "
    "soft bloom, atmospheric perspective, realistic shadows, subtle film grain, detailed environment, "
    "35mm cinema lens, premium travel film still, emotional, immersive, natural colors"
)

DEFAULT_NEGATIVE = (
    "low quality, blurry, jpeg artifacts, cartoon, anime, illustration, plastic skin, oversaturated, "
    "bad anatomy, deformed hands, distorted face, extra limbs, duplicate body, ugly face, text, "
    "watermark, logo, messy composition, flat lighting, bad perspective, AI artifacts, random dots, "
    "white speckles, noisy, over-sharpened, waxy skin"
)

RATIO_TO_SIZE = {
    "9:16": (512, 768),
    "3:4": (576, 768),
    "2:3": (512, 768),
    "1:1": (640, 640),
    "16:9": (768, 512),
}


def request_json(base_url: str, path: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    request = urllib.request.Request(f"{base_url.rstrip('/')}{path}", data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
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
    if DEFAULT_POSITIVE_SUFFIX.lower() not in prompt.lower():
        prompt = f"{prompt}, {DEFAULT_POSITIVE_SUFFIX}"
    return prompt


def size_for_ratio(ratio: str) -> tuple[int, int]:
    return RATIO_TO_SIZE.get(ratio, RATIO_TO_SIZE["9:16"])


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
            },
        }
    else:
        workflow[str(node_id)] = {
            "class_type": "VAEEncode",
            "inputs": {"pixels": image_ref, "vae": vae_ref},
        }
    return [str(node_id), 0], node_id + 1


def build_sd15_workflow(args: argparse.Namespace, prompt: str, seed: int, width: int, height: int) -> dict[str, Any]:
    workflow: dict[str, Any] = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": args.checkpoint},
        },
        "2": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": args.vae},
        },
    }
    model_ref: list[Any] = ["1", 0]
    clip_ref: list[Any] = ["1", 1]
    vae_ref: list[Any] = ["2", 0] if args.vae else ["1", 2]
    model_ref, clip_ref, next_id = add_loras(workflow, model_ref, clip_ref, parse_loras(args.lora))

    pos_id = str(next_id)
    neg_id = str(next_id + 1)
    latent_id = str(next_id + 2)
    sampler_id = str(next_id + 3)
    next_id += 4
    workflow[pos_id] = {"class_type": "CLIPTextEncode", "inputs": {"clip": clip_ref, "text": prompt}}
    workflow[neg_id] = {"class_type": "CLIPTextEncode", "inputs": {"clip": clip_ref, "text": args.negative_prompt}}
    workflow[latent_id] = {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}}
    workflow[sampler_id] = {
        "class_type": "KSampler",
        "inputs": {
            "model": model_ref,
            "positive": [pos_id, 0],
            "negative": [neg_id, 0],
            "latent_image": [latent_id, 0],
            "seed": seed,
            "steps": args.steps,
            "cfg": args.cfg,
            "sampler_name": args.sampler,
            "scheduler": args.scheduler,
            "denoise": 1.0,
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
    workflow = build_sd15_workflow(args, prompt, seed, width, height)
    history = submit_and_wait(args.comfy_url, workflow, args.timeout, args.poll_seconds)
    save_comfy_image(args.comfy_url, extract_first_image(history), output)
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
    }
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate storyboard images locally with a low-VRAM cinematic ComfyUI workflow.")
    parser.add_argument("--storyboard", required=True, type=Path)
    parser.add_argument("--comfy-url", default=os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188"))
    parser.add_argument("--checkpoint", default=os.environ.get("SD15_CHECKPOINT", "realisticVisionV60B1_v51VAE.safetensors"))
    parser.add_argument("--vae", default=os.environ.get("SD15_VAE", "vae-ft-mse-840000-ema-pruned.safetensors"))
    parser.add_argument("--lora", action="append", default=[], help="Optional LoRA name or name:model_strength:clip_strength.")
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
    parser.add_argument("--upscale-model", default=os.environ.get("SD_UPSCALE_MODEL", ""))
    parser.add_argument("--final-width", type=int, default=1080)
    parser.add_argument("--final-height", type=int, default=1920)
    parser.add_argument("--negative-prompt", default=DEFAULT_NEGATIVE)
    parser.add_argument("--output-format", default="png")
    parser.add_argument("--prefix", default="auto-video-local")
    parser.add_argument("--seed", type=int, default=23052026)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    storyboard = args.storyboard.resolve()
    storyboard_dir = storyboard.parent
    assets_dir = storyboard_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    config = json.loads(storyboard.read_text(encoding="utf-8-sig"))
    scenes = config.get("scenes") or []
    if not scenes:
        raise SystemExit("Storyboard has no scenes.")
    request_json(args.comfy_url, "/system_stats", timeout=10)
    generated = []
    for index, scene in enumerate(scenes):
        path = generate_scene(args, scene, index, storyboard_dir, assets_dir)
        generated.append(str(path))
        print(f"Generated local SD image: {path}")
    storyboard.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"provider": "comfy-local", "mode": "sd15-low-vram", "storyboard": str(storyboard), "images": generated}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
