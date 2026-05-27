#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_ROOT = REPO_ROOT.parent
STATUS_DIR = WORK_ROOT / "temp" / "story-task-status"
BOARD_ROOT = REPO_ROOT / "ops_board"


def read_task_statuses() -> list[dict]:
    tasks = []
    for path in sorted(STATUS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
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
