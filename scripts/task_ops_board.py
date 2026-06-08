#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
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
        data["_status_file"] = str(path)
        enrich_with_scheduler(data)
        tasks.append(data)
    return tasks


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
        "status": "requested",
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
            "After QA is requested, Codex reviews the images visually against the criteria.",
            "Only confirmed fail scenes are moved to reject folders.",
            "Only confirmed fail scenes receive local prompt overrides or rescue notes for regeneration.",
            "Pass images remain untouched in assets.",
        ],
    }
    request_path = qa_request_path_for_task(task_name)
    write_json(request_path, request)

    if status:
        nodes = status.setdefault("nodes", {})
        nodes["qa"] = {
            "status": "requested",
            "detail": f"Codex QA requested, pass >= {QA_PASS_THRESHOLD}%, waiting for visual review.",
        }
        status["qa_summary"] = f"Requested at {now}; pass >= {QA_PASS_THRESHOLD}%; request: {request_path}"
        status["qa_request"] = str(request_path)
        status["message"] = "Codex QA requested from OpsBoard. Images/audio stay untouched until Codex visual review confirms fail scenes."
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
