#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_ROOT = REPO_ROOT.parent
STATUS_DIR = WORK_ROOT / "temp" / "story-task-status"
BOARD_ROOT = REPO_ROOT / "ops_board"


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
        if str(data.get("overall", "")).lower() == "terminated":
            try:
                path.unlink()
            except Exception:
                pass
            continue
        data["_status_file"] = str(path)
        enrich_with_scheduler(data)
        tasks.append(data)
    return tasks


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


def end_task(task_name: str) -> dict:
    slug = slugify(task_name)
    status_path = STATUS_DIR / f"{slugify(task_name)}.json"
    config_path = WORK_ROOT / "temp" / f"{slug}.json"
    startup_launcher = Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup" / f"{slugify(task_name)}.cmd"
    workers = get_worker_entries(task_name)
    killed: list[int] = []
    errors: list[str] = []
    for worker in workers:
        pid = int(worker["pid"])
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
