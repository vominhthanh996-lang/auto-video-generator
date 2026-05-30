#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import torch
from safetensors.torch import load_file as load_safetensors, save_file as save_safetensors


def load_checkpoint(path: Path) -> dict[str, torch.Tensor]:
    if path.suffix.lower() == ".safetensors":
        return load_safetensors(str(path), device="cpu")
    data = torch.load(str(path), map_location="cpu")
    if isinstance(data, dict) and "state_dict" in data and isinstance(data["state_dict"], dict):
        return data["state_dict"]
    if isinstance(data, dict):
        return data
    raise SystemExit(f"Unsupported checkpoint format: {path}")


def merge_state_dicts(
    primary: dict[str, torch.Tensor],
    secondary: dict[str, torch.Tensor],
    primary_weight: float,
    secondary_weight: float,
) -> tuple[dict[str, torch.Tensor], dict[str, int]]:
    merged: dict[str, torch.Tensor] = {}
    blended = 0
    primary_only = 0
    secondary_only = 0
    for key, tensor_a in primary.items():
        tensor_b = secondary.get(key)
        if (
            tensor_b is not None
            and isinstance(tensor_a, torch.Tensor)
            and isinstance(tensor_b, torch.Tensor)
            and tensor_a.shape == tensor_b.shape
            and tensor_a.dtype.is_floating_point
            and tensor_b.dtype.is_floating_point
        ):
            merged[key] = (tensor_a.float() * primary_weight + tensor_b.float() * secondary_weight).to(tensor_a.dtype)
            blended += 1
        else:
            merged[key] = tensor_a
            primary_only += 1
    for key, tensor_b in secondary.items():
        if key not in merged:
            merged[key] = tensor_b
            secondary_only += 1
    return merged, {
        "blended": blended,
        "primary_only": primary_only,
        "secondary_only": secondary_only,
        "total": len(merged),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge two SD1.5 checkpoints into one safetensors file.")
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--secondary", type=Path, required=True)
    parser.add_argument("--primary-weight", type=float, default=0.70)
    parser.add_argument("--secondary-weight", type=float, default=0.30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    total = args.primary_weight + args.secondary_weight
    if total <= 0:
        raise SystemExit("Weights must sum to a positive value.")
    primary_weight = args.primary_weight / total
    secondary_weight = args.secondary_weight / total

    primary_sd = load_checkpoint(args.primary.resolve())
    secondary_sd = load_checkpoint(args.secondary.resolve())
    merged_sd, stats = merge_state_dicts(primary_sd, secondary_sd, primary_weight, secondary_weight)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "merge_recipe": f"primary={args.primary.name}:{primary_weight:.4f};secondary={args.secondary.name}:{secondary_weight:.4f}",
        "merge_tool": "auto-video-generator-media/scripts/merge_sd15_checkpoints.py",
    }
    save_safetensors(merged_sd, str(args.output.resolve()), metadata=metadata)
    print(
        f"Merged checkpoint saved: {args.output.resolve()}\n"
        f"  primary={args.primary.name} ({primary_weight:.2%})\n"
        f"  secondary={args.secondary.name} ({secondary_weight:.2%})\n"
        f"  blended={stats['blended']}, primary_only={stats['primary_only']}, secondary_only={stats['secondary_only']}, total={stats['total']}"
    )


if __name__ == "__main__":
    main()
