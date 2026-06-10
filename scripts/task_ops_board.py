#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_ROOT = REPO_ROOT.parent
STATUS_DIR = WORK_ROOT / "temp" / "story-task-status"
BOARD_ROOT = REPO_ROOT / "ops_board"
QA_REQUEST_DIR = WORK_ROOT / "temp" / "story-qa-requests"
QA_PASS_THRESHOLD = 40


def slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "story-task"


def read_task_statuses() -> list[dict]:
    tasks = []
    for path in sorted(STATUS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        overall = str(data.get("overall", "")).lower()
        if overall in {"terminated", "success"}:
            try:
                path.unlink()
            except Exception:
                pass
            continue
        refresh_counts_from_assets(data)
        reconcile_live_state(data)
        attach_qa_state(data)
        data["_status_file"] = str(path)
        enrich_with_scheduler(data)
        tasks.append(data)
    return tasks


def attach_qa_state(task: dict) -> None:
    task_name = str(task.get("task") or "").strip()
    if not task_name:
        return
    request_path = qa_request_path_for_task(task_name)
    if not request_path.exists():
        return
    request = read_json(request_path) or {}
    if not request:
        return
    task["qa_request"] = str(request_path)
    task["qa_request_state"] = {
        "status": request.get("status", ""),
        "requested_at": request.get("requested_at", ""),
        "reviewed_at": request.get("reviewed_at", ""),
        "summary": request.get("summary", ""),
        "fail_scene_ranges": request.get("fail_scene_ranges") or [],
        "fail_scenes": request.get("fail_scenes") or [],
        "fail_details": request.get("fail_details") or [],
        "pass_scenes": request.get("pass_scenes") or [],
        "pass_count": request.get("pass_count", ""),
        "fail_count": request.get("fail_count", ""),
        "regen": request.get("regen") or {},
    }
    status = str(request.get("status") or "").lower()
    nodes = task.setdefault("nodes", {})
    qa_node = nodes.setdefault("qa", {"status": "pending", "detail": ""})
    if status in {"checking", "requested"}:
        qa_node["status"] = "running"
        qa_node["detail"] = "Codex automation is expected to review images visually and write pass/fail details."
        task["qa_summary"] = f"Codex visual QA {status}; request: {request_path}"
    elif status in {"failed", "fail"}:
        qa_node["status"] = "failed"
        qa_node["detail"] = str(request.get("summary") or "Codex visual QA failed.")
        task["qa_summary"] = qa_node["detail"]
        render_node = nodes.setdefault("render", {"status": "pending", "detail": ""})
        render_node["status"] = "blocked"
        render_node["detail"] = "Blocked until failed scenes are regenerated and QA passes."
    elif status in {"passed", "pass", "approved", "done"}:
        qa_node["status"] = "done"
        qa_node["detail"] = str(request.get("summary") or "Codex visual QA passed.")
        task["qa_summary"] = qa_node["detail"]
    elif status in {"regenerating", "regen"}:
        qa_node["status"] = "warning"
        qa_node["detail"] = "Failed scenes were moved to reject and queued for regeneration."
        task["qa_summary"] = qa_node["detail"]


def refresh_counts_from_assets(task: dict) -> None:
    storyboard_path = task.get("storyboard")
    if not storyboard_path:
        return
    try:
        storyboard = json.loads(Path(storyboard_path).read_text(encoding="utf-8-sig"))
    except Exception:
        return
    scenes = list(storyboard.get("scenes") or [])
    project_root = Path(task.get("project") or Path(storyboard_path).parent)
    image_count = 0
    audio_count = 0
    for scene in scenes:
        image_value = scene.get("image")
        if image_value:
            image_path = Path(image_value)
            if not image_path.is_absolute():
                image_path = project_root / image_value
            if image_path.exists():
                image_count += 1
        audio_value = scene.get("audio")
        if audio_value:
            audio_path = Path(audio_value)
            if not audio_path.is_absolute():
                audio_path = project_root / audio_value
            if audio_path.exists():
                audio_count += 1
    task["counts"] = {
        "scenes": len(scenes),
        "images": image_count,
        "audio": audio_count,
    }
    nodes = task.setdefault("nodes", {})
    voice_node = nodes.setdefault("voice", {"status": "pending", "detail": ""})
    images_node = nodes.setdefault("images", {"status": "pending", "detail": ""})
    if len(scenes):
        if audio_count >= len(scenes):
            voice_node["status"] = "done"
            voice_node["detail"] = f"Audio ready {audio_count}/{len(scenes)}"
        elif audio_count > 0 and str(voice_node.get("status", "")).lower() == "running":
            voice_node["detail"] = f"Audio {audio_count}/{len(scenes)}"
        if image_count >= len(scenes):
            images_node["status"] = "done"
            images_node["detail"] = f"Images ready {image_count}/{len(scenes)}"
        elif image_count > 0 and str(images_node.get("status", "")).lower() == "running":
            images_node["detail"] = f"Images {image_count}/{len(scenes)}"


def reconcile_live_state(task: dict) -> None:
    task_name = str(task.get("task") or "").strip()
    if not task_name:
        return
    worker_entries = get_worker_entries(task_name)
    supervisor_entries = get_supervisor_entries(task_name)
    if not worker_entries and not supervisor_entries:
        return
    overall = str(task.get("overall", "")).lower()
    current_node = str(task.get("current_node", "")).lower()
    if overall == "failed":
        task["overall"] = "running"
        if current_node in {"", "supervisor", "startup"}:
            voice_status = str(task.get("nodes", {}).get("voice", {}).get("status", "")).lower()
            image_status = str(task.get("nodes", {}).get("images", {}).get("status", "")).lower()
            if voice_status == "running":
                task["current_node"] = "voice"
            elif image_status == "running":
                task["current_node"] = "images"
            else:
                task["current_node"] = "supervisor"
        task["message"] = "Worker restarted and task is continuing."


def enrich_with_scheduler(task: dict) -> None:
    name = task.get("task")
    if not name:
        return
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/TN", name, "/V", "/FO", "LIST"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except Exception:
        return
    if result.returncode != 0:
        return
    parsed: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parsed[key.strip()] = value.strip()
    task["scheduler"] = {
        "status": parsed.get("Status", ""),
        "last_result": parsed.get("Last Result", ""),
        "last_run_time": parsed.get("Last Run Time", ""),
        "next_run_time": parsed.get("Next Run Time", ""),
        "task_to_run": parsed.get("Task To Run", ""),
    }


def get_worker_entries(task_name: str) -> list[dict]:
    slug = slugify(task_name)
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Get-CimInstance Win32_Process | "
                    "Where-Object { $_.Name -eq 'powershell.exe' -and $_.CommandLine -like '*story_task_worker.ps1*' } | "
                    "Select-Object ProcessId,CommandLine | ConvertTo-Json -Depth 4"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except Exception:
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        payload = json.loads(result.stdout)
    except Exception:
        return []
    rows = payload if isinstance(payload, list) else [payload]
    entries: list[dict] = []
    for row in rows:
        command_line = str(row.get("CommandLine") or "")
        if not command_line:
            continue
        config_path = ""
        if '-ConfigPath "' in command_line:
            config_path = command_line.split('-ConfigPath "', 1)[1].split('"', 1)[0]
        elif "-ConfigPath " in command_line:
            config_path = command_line.split("-ConfigPath ", 1)[1].split(" ", 1)[0].strip()
        config_task = ""
        if config_path:
            try:
                config_task = json.loads(Path(config_path).read_text(encoding="utf-8-sig")).get("TaskName", "")
            except Exception:
                config_task = ""
        if config_task == task_name:
            entries.append(
                {
                    "pid": int(row.get("ProcessId")),
                    "config_path": config_path,
                    "command_line": command_line,
                }
            )
    return entries


def get_supervisor_entries(task_name: str) -> list[dict]:
    slug = slugify(task_name)
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Get-CimInstance Win32_Process | "
                    "Where-Object { $_.Name -eq 'powershell.exe' -and $_.CommandLine -like '*resume_story_task_on_logon.ps1*' } | "
                    "Select-Object ProcessId,CommandLine | ConvertTo-Json -Depth 4"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except Exception:
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        payload = json.loads(result.stdout)
    except Exception:
        return []
    rows = payload if isinstance(payload, list) else [payload]
    entries: list[dict] = []
    for row in rows:
        command_line = str(row.get("CommandLine") or "")
        if not command_line:
            continue
        config_path = ""
        if '-ConfigPath "' in command_line:
            config_path = command_line.split('-ConfigPath "', 1)[1].split('"', 1)[0]
        elif "-ConfigPath " in command_line:
            config_path = command_line.split("-ConfigPath ", 1)[1].split(" ", 1)[0].strip()
        config_task = ""
        if config_path:
            try:
                config_task = json.loads(Path(config_path).read_text(encoding="utf-8-sig")).get("TaskName", "")
            except Exception:
                config_task = ""
        command_line_lc = command_line.lower()
        config_path_lc = config_path.lower()
        if config_task == task_name or slug in command_line_lc or slug in config_path_lc:
            entries.append(
                {
                    "pid": int(row.get("ProcessId")),
                    "config_path": config_path,
                    "command_line": command_line,
                }
            )
    return entries


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def status_path_for_task(task_name: str) -> Path:
    return STATUS_DIR / f"{slugify(task_name)}.json"


def config_path_for_task(task_name: str) -> Path:
    return WORK_ROOT / "temp" / f"{slugify(task_name)}.json"


def qa_request_path_for_task(task_name: str) -> Path:
    return QA_REQUEST_DIR / f"{slugify(task_name)}.json"


def collect_asset_counts(storyboard_path: Path, project_root: Path) -> dict:
    storyboard = read_json(storyboard_path) or {}
    scenes = list(storyboard.get("scenes") or [])
    image_count = 0
    audio_count = 0
    missing_images: list[int] = []
    missing_audio: list[int] = []
    for index, scene in enumerate(scenes, 1):
        image_value = scene.get("image")
        if image_value:
            image_path = Path(image_value)
            if not image_path.is_absolute():
                image_path = project_root / image_value
            if image_path.exists():
                image_count += 1
            else:
                missing_images.append(index)
        else:
            missing_images.append(index)

        audio_value = scene.get("audio")
        if audio_value:
            audio_path = Path(audio_value)
            if not audio_path.is_absolute():
                audio_path = project_root / audio_value
            if audio_path.exists():
                audio_count += 1
            else:
                missing_audio.append(index)
        else:
            missing_audio.append(index)
    return {
        "scenes": len(scenes),
        "images": image_count,
        "audio": audio_count,
        "missing_images": missing_images,
        "missing_audio": missing_audio,
    }


def request_qa(task_name: str) -> dict:
    QA_REQUEST_DIR.mkdir(parents=True, exist_ok=True)
    status_path = status_path_for_task(task_name)
    config_path = config_path_for_task(task_name)
    status = read_json(status_path) or {}
    config = read_json(config_path) or {}
    storyboard_value = str(status.get("storyboard") or config.get("StoryboardPath") or "")
    project_value = str(status.get("project") or config.get("ProjectRoot") or "")
    if not storyboard_value:
        return {
            "task": task_name,
            "requested": False,
            "errors": [f"Missing storyboard path for task: {task_name}"],
        }

    storyboard_path = Path(storyboard_value)
    project_root = Path(project_value) if project_value else storyboard_path.parent
    counts = collect_asset_counts(storyboard_path, project_root)
    now = dt.datetime.now().isoformat(timespec="seconds")
    request = {
        "task": task_name,
        "status": "checking",
        "requested_at": now,
        "pass_threshold": QA_PASS_THRESHOLD,
        "storyboard": str(storyboard_path),
        "project": str(project_root),
        "counts": counts,
        "criteria": [
            "pass if image reaches at least 40% of the story/visual criteria",
            "highest priority: closely follows the exact story beat and scene purpose",
            "characters must match role, age, gender, and relationship in the narration",
            "human bodies must not be deformed; faces need intact eyes, nose, mouth, and readable expression",
            "characters must not be fused, nested, or incoherently overlapping",
            "required props/locations/actions from the storyboard must be readable enough to draw the beat",
            "Lam Tich stays attractive/glam but practical for the wasteland context, not bikini-like unless the scene truly supports exposure",
            "Tan Da stays tall, muscular, masculine, righteous, and fully grounded in the survival scene",
        ],
        "workflow": [
            "Generate all image and audio assets first; QA does not run during generation.",
            "After QA is requested, Codex heartbeat automation reviews the images visually against the criteria.",
            "Only confirmed fail scenes are moved to reject folders.",
            "Only confirmed fail scenes receive local prompt overrides or rescue notes for regeneration.",
            "Pass images remain untouched in assets.",
        ],
        "automation": {
            "expected_handler": "Codex heartbeat automation in the active QA thread",
            "result_fields": ["status", "reviewed_at", "summary", "pass_scenes", "fail_scenes", "fail_scene_ranges", "fail_details"],
        },
    }
    request_path = qa_request_path_for_task(task_name)
    write_json(request_path, request)

    if status:
        nodes = status.setdefault("nodes", {})
        nodes["qa"] = {
            "status": "running",
            "detail": f"Codex automation visual QA queued, pass >= {QA_PASS_THRESHOLD}%. Waiting for reviewed pass/fail details.",
        }
        status["qa_summary"] = f"Codex visual QA checking since {now}; pass >= {QA_PASS_THRESHOLD}%; request: {request_path}"
        status["qa_request"] = str(request_path)
        status["message"] = "Codex visual QA requested from OpsBoard. Waiting for Codex automation to review images and mark pass/fail."
        status["updated_at"] = now
        write_json(status_path, status)

    return {
        "task": task_name,
        "requested": True,
        "request_file": str(request_path),
        "pass_threshold": QA_PASS_THRESHOLD,
        "counts": counts,
        "errors": [],
    }


def expand_scene_ranges(values: list) -> list[int]:
    scenes: set[int] = set()
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        for part in re.split(r"[,;]\s*", text):
            part = part.strip()
            if not part:
                continue
            match = re.fullmatch(r"0*(\d+)\s*-\s*0*(\d+)", part)
            if match:
                start = int(match.group(1))
                end = int(match.group(2))
                if start > end:
                    start, end = end, start
                scenes.update(range(start, end + 1))
                continue
            match = re.search(r"0*(\d+)", part)
            if match:
                scenes.add(int(match.group(1)))
    return sorted(scene for scene in scenes if scene > 0)


def scene_image_path(scene: dict, storyboard_dir: Path, project_root: Path, index: int) -> Path:
    value = scene.get("image")
    if value:
        path = Path(str(value))
        if not path.is_absolute():
            path = project_root / path
        return path
    return storyboard_dir / "assets" / f"scene-{index:03d}.png"


def append_unique_note(scene: dict, key: str, note: str) -> None:
    values = scene.get(key)
    if not isinstance(values, list):
        values = []
    if note not in values:
        values.append(note)
    scene[key] = values[-10:]


def fail_detail_map(request: dict) -> dict[int, dict]:
    details: dict[int, dict] = {}
    for item in request.get("fail_details") or []:
        try:
            scene_no = int(item.get("scene") or item.get("scene_number") or item.get("index") or 0)
        except Exception:
            scene_no = 0
        if scene_no:
            details[scene_no] = item
    return details


def classify_fail_reason(reason: str, fix_hint: str) -> str:
    text = f"{reason} {fix_hint}".lower()
    if any(token in text for token in ["pose", "standing", "portrait", "glamour", "bikini", "crop"]):
        return "pose_drift"
    if any(token in text for token in ["missing prop", "object", "radio", "board", "water", "medicine", "trade", "door", "gate"]):
        return "missing_story_object"
    if any(token in text for token in ["male", "man", "belly", "feminine", "masculine"]):
        return "male_identity_clothing"
    if any(token in text for token in ["child", "age", "old", "elder", "young"]):
        return "age_identity"
    if any(token in text for token in ["setting", "wasteland", "location", "background", "environment"]):
        return "location_mismatch"
    return "story_beat_mismatch"


def regen_failed_qa(task_name: str) -> dict:
    request_path = qa_request_path_for_task(task_name)
    request = read_json(request_path) or {}
    if not request:
        return {"task": task_name, "started": False, "errors": [f"Missing QA request: {request_path}"]}
    status = str(request.get("status") or "").lower()
    if status not in {"failed", "fail"}:
        return {"task": task_name, "started": False, "errors": [f"QA status is not failed: {status or 'empty'}"]}

    storyboard_path = Path(str(request.get("storyboard") or ""))
    project_root = Path(str(request.get("project") or storyboard_path.parent))
    if not storyboard_path.exists():
        return {"task": task_name, "started": False, "errors": [f"Missing storyboard: {storyboard_path}"]}
    storyboard = read_json(storyboard_path) or {}
    scenes = list(storyboard.get("scenes") or [])
    failed = expand_scene_ranges(list(request.get("fail_scene_ranges") or []) + list(request.get("fail_scenes") or []))
    failed = [index for index in failed if 1 <= index <= len(scenes)]
    if not failed:
        return {"task": task_name, "started": False, "errors": ["QA failed but no fail scenes were listed."]}
    details_by_scene = fail_detail_map(request)

    now = dt.datetime.now()
    reject_dir = project_root / "reject" / f"qa-{now.strftime('%Y%m%d-%H%M%S')}"
    reject_dir.mkdir(parents=True, exist_ok=True)
    moved: list[str] = []
    missing: list[int] = []
    for index in failed:
        scene = scenes[index - 1]
        image_path = scene_image_path(scene, storyboard_path.parent, project_root, index)
        if image_path.exists():
            target = reject_dir / image_path.name
            if target.exists():
                target = reject_dir / f"scene-{index:03d}-{int(now.timestamp())}{image_path.suffix}"
            shutil.move(str(image_path), str(target))
            moved.append(str(target))
        else:
            missing.append(index)
        scene.pop("image", None)
        scene.pop("local_image", None)
        detail = details_by_scene.get(index) or {}
        reason = str(detail.get("reason") or detail.get("fail_reason") or "")
        fix_hint = str(detail.get("fix_hint") or detail.get("hint") or "")
        scene["qa_rescue_mode"] = True
        scene["qa_retry_limit"] = 5
        scene["qa_failure_type"] = classify_fail_reason(reason, fix_hint)
        scene["qa_last_fail_score"] = detail.get("approximate_score_percent") or detail.get("score_percent") or detail.get("score")
        if reason:
            scene["qa_last_fail_reason"] = reason[:500]
        if fix_hint:
            scene["qa_local_fix_hint"] = fix_hint[:500]
        append_unique_note(scene, "local_prompt_frontload", "QA rescue: story beat is the source of truth; draw the exact narrated action, object, place, danger, exchange, injury, creature, or reaction first.")
        append_unique_note(scene, "local_prompt_frontload", "QA rescue: characters are supporting the beat unless the narration itself is a character-focused beat; no default standing pose or glamour portrait.")
        append_unique_note(scene, "local_rescue_notes", "QA rescue: required props, location, body action, creature/threat, and story pressure must be readable in one frame.")
        append_unique_note(scene, "local_rescue_notes", "QA rescue: male characters use masculine layered wasteland clothing with covered waist; female styling stays feminine, sexy only when the beat calls for it, and never bikini-bottom/two-piece.")
        if reason:
            append_unique_note(scene, "local_rescue_notes", f"Previous Codex QA fail reason: {reason[:260]}")
        if fix_hint:
            append_unique_note(scene, "local_rescue_notes", f"Previous Codex QA fix hint: {fix_hint[:260]}")

    storyboard["scenes"] = scenes
    storyboard_path.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")

    request["status"] = "regenerating"
    request["regen"] = {
        "requested_at": now.isoformat(timespec="seconds"),
        "reject_dir": str(reject_dir),
        "scene_count": len(failed),
        "scenes": failed,
        "moved": moved,
        "missing_existing_images": missing,
        "per_scene_retry_limit": 5,
        "check_engine": "python-lightweight-beat-integrity-v1",
    }
    request["summary"] = f"Moved {len(moved)} failed image(s) to reject and queued {len(failed)} scene(s) for regeneration."
    write_json(request_path, request)

    status_path = status_path_for_task(task_name)
    state = read_json(status_path) or {}
    if state:
        nodes = state.setdefault("nodes", {})
        nodes["qa"] = {"status": "warning", "detail": request["summary"]}
        nodes["images"] = {"status": "running", "detail": f"Regenerating QA failed scenes: {len(failed)} scene(s)"}
        nodes["render"] = {"status": "blocked", "detail": "Render blocked until regenerated scenes pass Codex visual QA"}
        state["overall"] = "queued"
        state["current_node"] = "images"
        state["message"] = request["summary"]
        state["qa_summary"] = request["summary"]
        state["qa_request"] = str(request_path)
        state["updated_at"] = now.isoformat(timespec="seconds")
        write_json(status_path, state)

    config_path = config_path_for_task(task_name)
    started = False
    errors: list[str] = []
    if config_path.exists():
        try:
            started = start_supervisor(config_path)
        except Exception as exc:
            errors.append(str(exc))
    else:
        errors.append(f"Missing config file: {config_path}")

    return {
        "task": task_name,
        "started": started,
        "errors": errors,
        "reject_dir": str(reject_dir),
        "scenes": failed,
        "moved": moved,
        "missing_existing_images": missing,
    }


def parse_current_scene_number(state: dict) -> int | None:
    text = " ".join(
        str(state.get(key, "") or "")
        for key in ("current_node", "message")
    )
    match = re.search(r"scene\s+(\d+)", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def contiguous_ready_index(storyboard: dict, project_root: Path, field: str) -> int:
    scenes = list(storyboard.get("scenes") or [])
    ready = 0
    for scene in scenes:
        value = scene.get(field)
        if not value:
            break
        path = Path(value)
        if not path.is_absolute():
            path = project_root / value
        if not path.exists():
            break
        ready += 1
    return ready


def reset_in_progress_outputs(status_path: Path, config_path: Path) -> list[str]:
    notes: list[str] = []
    status = read_json(status_path) or {}
    config = read_json(config_path) or {}
    storyboard_path_value = str(status.get("storyboard") or config.get("StoryboardPath") or "")
    project_root_value = str(status.get("project") or config.get("ProjectRoot") or "")
    if not storyboard_path_value:
        return notes
    storyboard_path = Path(storyboard_path_value)
    project_root = Path(project_root_value) if project_root_value else storyboard_path.parent
    storyboard = read_json(storyboard_path)
    if not storyboard:
        return notes

    current_node = str(status.get("current_node") or "").lower()
    scene_number = parse_current_scene_number(status)
    scenes = list(storyboard.get("scenes") or [])

    if "image" in current_node and scene_number and 1 <= scene_number <= len(scenes):
        scene = scenes[scene_number - 1]
        image_value = scene.get("image")
        if image_value:
            image_path = Path(image_value)
            if not image_path.is_absolute():
                image_path = project_root / image_value
            if image_path.exists():
                image_path.unlink()
                notes.append(f"reset image output for scene {scene_number}")
        return notes

    if "voice" in current_node:
        try:
            target = int((status.get("counts") or {}).get("audio") or 0) + 1
        except Exception:
            target = 0
        if target <= 0:
            target = contiguous_ready_index(storyboard, project_root, "audio") + 1
        if 1 <= target <= len(scenes):
            audio_value = scenes[target - 1].get("audio")
            if audio_value:
                audio_path = Path(audio_value)
                if not audio_path.is_absolute():
                    audio_path = project_root / audio_value
                if audio_path.exists():
                    audio_path.unlink()
                    notes.append(f"reset audio output for scene {target}")
        return notes

    if "render" in current_node:
        output_dir = project_root / "output"
        if output_dir.exists():
            for path in sorted(output_dir.glob("*.mp4"), key=lambda item: item.stat().st_mtime, reverse=True):
                try:
                    path.unlink()
                    notes.append(f"reset render output {path.name}")
                except Exception:
                    continue
                break
        return notes

    return notes


def update_status_for_pause(status_path: Path, message: str) -> None:
    state = read_json(status_path) or {}
    if not state:
        return
    state["overall"] = "paused"
    state["message"] = message
    state["updated_at"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    write_json(status_path, state)


def update_status_for_resume(status_path: Path, message: str) -> None:
    state = read_json(status_path) or {}
    if not state:
        return
    state["overall"] = "queued"
    state["current_node"] = "startup"
    state["message"] = message
    state["updated_at"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    write_json(status_path, state)


def create_startup_launcher(task_name: str, config_path: Path) -> Path:
    launcher = Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup" / f"{slugify(task_name)}.cmd"
    launcher.write_text(
        '@echo off\n'
        f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{REPO_ROOT / "scripts" / "resume_story_task_on_logon.ps1"}" -ConfigPath "{config_path}"\n',
        encoding="ascii",
    )
    return launcher


def start_supervisor(config_path: Path) -> bool:
    resume_script = REPO_ROOT / "scripts" / "resume_story_task_on_logon.ps1"
    proc = subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(resume_script),
            "-ConfigPath",
            str(config_path),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.pid > 0


def stop_entries(entries: list[dict]) -> tuple[list[int], list[str]]:
    killed: list[int] = []
    errors: list[str] = []
    for entry in entries:
        pid = int(entry["pid"])
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if result.returncode == 0:
            killed.append(pid)
        else:
            detail = (result.stderr or result.stdout or "").strip()
            errors.append(f"PID {pid}: {detail}")
    return killed, errors


def end_task(task_name: str) -> dict:
    slug = slugify(task_name)
    status_path = STATUS_DIR / f"{slugify(task_name)}.json"
    config_path = WORK_ROOT / "temp" / f"{slug}.json"
    startup_launcher = Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup" / f"{slugify(task_name)}.cmd"
    workers = get_worker_entries(task_name)
    supervisors = get_supervisor_entries(task_name)
    killed, errors = stop_entries(workers + supervisors)
    if startup_launcher.exists():
        try:
            startup_launcher.unlink()
        except Exception as exc:
            errors.append(f"startup launcher: {exc}")
    if config_path.exists():
        try:
            config_path.unlink()
        except Exception as exc:
            errors.append(f"config remove: {exc}")
    if status_path.exists():
        try:
            status_path.unlink()
        except Exception as exc:
            errors.append(f"status remove: {exc}")
    return {
        "task": task_name,
        "killed": killed,
        "errors": errors,
        "status_file": str(status_path),
        "config_file": str(config_path),
        "startup_launcher_removed": not startup_launcher.exists(),
        "status_removed": not status_path.exists(),
        "config_removed": not config_path.exists(),
    }


def pause_task(task_name: str) -> dict:
    slug = slugify(task_name)
    status_path = STATUS_DIR / f"{slug}.json"
    config_path = WORK_ROOT / "temp" / f"{slug}.json"
    startup_launcher = Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup" / f"{slug}.cmd"
    workers = get_worker_entries(task_name)
    supervisors = get_supervisor_entries(task_name)
    killed, errors = stop_entries(workers + supervisors)
    if startup_launcher.exists():
        try:
            startup_launcher.unlink()
        except Exception as exc:
            errors.append(f"startup launcher: {exc}")
    if status_path.exists():
        update_status_for_pause(status_path, "Task paused. Resume will restart the in-progress step from the beginning.")
    return {
        "task": task_name,
        "killed": killed,
        "errors": errors,
        "paused": True,
        "status_file": str(status_path),
        "config_file": str(config_path),
    }


def resume_task(task_name: str) -> dict:
    slug = slugify(task_name)
    status_path = STATUS_DIR / f"{slug}.json"
    config_path = WORK_ROOT / "temp" / f"{slug}.json"
    if not config_path.exists():
        return {
            "task": task_name,
            "started": False,
            "errors": [f"Missing config file: {config_path}"],
        }
    reset_notes = reset_in_progress_outputs(status_path, config_path)
    update_status_for_resume(status_path, "Resuming task. The in-progress step has been reset and will run again.")
    create_startup_launcher(task_name, config_path)
    started = start_supervisor(config_path)
    return {
        "task": task_name,
        "started": started,
        "errors": [] if started else ["Failed to start supervisor."],
        "reset": reset_notes,
        "status_file": str(status_path),
        "config_file": str(config_path),
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=str(BOARD_ROOT), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/tasks":
            payload = {"tasks": read_task_statuses()}
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/end"):
            middle = parsed.path[len("/api/tasks/") : -len("/end")].strip("/")
            task_name = unquote(middle)
            payload = end_task(task_name)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/pause"):
            middle = parsed.path[len("/api/tasks/") : -len("/pause")].strip("/")
            task_name = unquote(middle)
            payload = pause_task(task_name)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/resume"):
            middle = parsed.path[len("/api/tasks/") : -len("/resume")].strip("/")
            task_name = unquote(middle)
            payload = resume_task(task_name)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/qa"):
            middle = parsed.path[len("/api/tasks/") : -len("/qa")].strip("/")
            task_name = unquote(middle)
            payload = request_qa(task_name)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200 if payload.get("requested") else 400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path.startswith("/api/tasks/") and parsed.path.endswith("/qa-regen"):
            middle = parsed.path[len("/api/tasks/") : -len("/qa-regen")].strip("/")
            task_name = unquote(middle)
            payload = regen_failed_qa(task_name)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200 if payload.get("started") or not payload.get("errors") else 400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the story task operation board.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    BOARD_ROOT.mkdir(parents=True, exist_ok=True)
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Serving task board at http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
