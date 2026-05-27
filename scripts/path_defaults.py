#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path


def _dedupe(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def _env_path(*names: str) -> Path | None:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return Path(value).expanduser()
    return None


def _repo_based_work_root(repo_root: Path) -> Path:
    parts = list(repo_root.resolve().parts)
    lowered = [part.lower() for part in parts]
    if "thanhmv" in lowered:
        index = lowered.index("thanhmv")
        return Path(*parts[: index + 1])
    return repo_root.parent


def candidate_work_roots(repo_root: Path) -> list[Path]:
    candidates: list[Path] = []
    env_root = _env_path("AUTO_VIDEO_WORK_ROOT")
    if env_root:
        candidates.append(env_root)
    candidates.append(_repo_based_work_root(repo_root))
    candidates.append(Path(r"D:\ThanhMV"))
    candidates.append(Path(r"E:\ThanhMV"))
    return _dedupe(candidates)


def default_work_root(repo_root: Path) -> Path:
    for candidate in candidate_work_roots(repo_root):
        if candidate.exists():
            return candidate
    return candidate_work_roots(repo_root)[0]


def default_projects_root(repo_root: Path) -> Path:
    override = _env_path("VIDEO_PROJECTS_ROOT")
    if override:
        return override
    return default_work_root(repo_root) / "video-projects"


def default_temp_root(repo_root: Path) -> Path:
    override = _env_path("AUTO_VIDEO_TEMP_ROOT")
    if override:
        return override
    return default_work_root(repo_root) / "temp"


def candidate_comfy_roots(repo_root: Path) -> list[Path]:
    candidates: list[Path] = []
    env_root = _env_path("COMFY_ROOT", "AUTO_VIDEO_COMFY_ROOT")
    if env_root:
        candidates.append(env_root)
    for work_root in candidate_work_roots(repo_root):
        candidates.append(work_root / "tools" / "ComfyUI_windows_portable_nvidia" / "ComfyUI_windows_portable")
        candidates.append(work_root / "ComfyUI_windows_portable_nvidia" / "ComfyUI_windows_portable")
        candidates.append(work_root / "tools" / "ComfyUI")
        candidates.append(work_root / "ComfyUI")
    return _dedupe(candidates)


def default_comfy_root(repo_root: Path) -> Path:
    for candidate in candidate_comfy_roots(repo_root):
        if (candidate / "ComfyUI" / "main.py").exists():
            return candidate
    return candidate_comfy_roots(repo_root)[0]


def default_comfy_input_dir(repo_root: Path) -> Path:
    return default_comfy_root(repo_root) / "ComfyUI" / "input"


def default_comfy_output_dir(repo_root: Path) -> Path:
    return default_comfy_root(repo_root) / "ComfyUI" / "output"
