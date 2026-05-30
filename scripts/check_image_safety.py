#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from pathlib import Path
from typing import Any

from PIL import Image
from transformers import pipeline
from transformers.utils import logging as transformers_logging


def build_classifier(model_name: str):
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    warnings.filterwarnings("ignore", message="`huggingface_hub` cache-system uses symlinks by default.*")
    transformers_logging.set_verbosity_error()
    return pipeline("image-classification", model=model_name, device=-1)


def classify_image(classifier, image_path: Path, threshold: float) -> dict[str, Any]:
    image = Image.open(image_path).convert("RGB")
    raw = classifier(image)
    scores = {str(item["label"]).lower(): float(item["score"]) for item in raw}
    nsfw_score = scores.get("nsfw", 0.0)
    normal_score = scores.get("normal", 0.0)
    return {
        "image": str(image_path.resolve()),
        "scores": {
            "nsfw": round(nsfw_score, 6),
            "normal": round(normal_score, 6),
        },
        "threshold": threshold,
        "reject": nsfw_score >= threshold,
        "top_label": "nsfw" if nsfw_score >= normal_score else "normal",
    }


def serve(model_name: str) -> int:
    classifier = build_classifier(model_name)
    for line in sys.stdin:
        payload = json.loads(line)
        image = Path(payload["image"]).resolve()
        threshold = float(payload.get("threshold", 0.18))
        result = classify_image(classifier, image, threshold)
        sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="NSFW image safety classifier helper.")
    parser.add_argument("--image", type=Path)
    parser.add_argument("--threshold", type=float, default=0.18)
    parser.add_argument("--model", default="Falconsai/nsfw_image_detection")
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()

    if args.serve:
        return serve(args.model)
    if not args.image:
        parser.error("--image is required unless --serve is used.")

    classifier = build_classifier(args.model)
    result = classify_image(classifier, args.image.resolve(), args.threshold)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
