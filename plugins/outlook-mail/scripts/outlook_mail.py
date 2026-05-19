#!/usr/bin/env python3
"""Read Outlook mail through Microsoft Graph without third-party packages."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


GRAPH = "https://graph.microsoft.com/v1.0"
AUTHORITY = "https://login.microsoftonline.com/common/oauth2/v2.0"
SCOPES = "offline_access User.Read Mail.Read"
ROOT = pathlib.Path(__file__).resolve().parents[1]
SECRETS = ROOT / ".secrets"
TOKEN_PATH = SECRETS / "token.json"


class OutlookError(RuntimeError):
    pass


def http_json(method: str, url: str, *, token: str | None = None, data: dict | None = None) -> dict:
    headers = {"Accept": "application/json"}
    body = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise OutlookError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise OutlookError(f"Network error calling {url}: {exc.reason}") from exc


def client_id() -> str:
    value = os.environ.get("OUTLOOK_CLIENT_ID", "").strip()
    if not value:
        raise OutlookError(
            "Missing OUTLOOK_CLIENT_ID. Create a Microsoft Entra app registration, "
            "enable public client flows, add delegated Mail.Read, then run: "
            'setx OUTLOOK_CLIENT_ID "your-client-id"'
        )
    return value


def save_token(token: dict) -> None:
    SECRETS.mkdir(parents=True, exist_ok=True)
    token = dict(token)
    token["obtained_at"] = int(time.time())
    TOKEN_PATH.write_text(json.dumps(token, indent=2), encoding="utf-8")


def load_token() -> dict:
    if not TOKEN_PATH.exists():
        raise OutlookError("Not signed in yet. Run: python plugins\\outlook-mail\\scripts\\outlook_mail.py login")
    return json.loads(TOKEN_PATH.read_text(encoding="utf-8"))


def login() -> dict:
    cid = client_id()
    device = http_json(
        "POST",
        f"{AUTHORITY}/devicecode",
        data={"client_id": cid, "scope": SCOPES},
    )
    print(device.get("message", "Open the verification URL and enter the device code."))
    interval = int(device.get("interval", 5))
    payload = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_id": cid,
        "device_code": device["device_code"],
    }

    while True:
        time.sleep(interval)
        try:
            token = http_json("POST", f"{AUTHORITY}/token", data=payload)
            save_token(token)
            print("Signed in. Token saved locally.")
            return token
        except OutlookError as exc:
            text = str(exc)
            if "authorization_pending" in text:
                continue
            if "slow_down" in text:
                interval += 5
                continue
            raise


def access_token() -> str:
    token = load_token()
    expires_at = int(token.get("obtained_at", 0)) + int(token.get("expires_in", 0)) - 120
    if time.time() < expires_at:
        return token["access_token"]

    refresh = token.get("refresh_token")
    if not refresh:
        print("Token expired and no refresh token is available. Starting login again.", file=sys.stderr)
        return login()["access_token"]

    refreshed = http_json(
        "POST",
        f"{AUTHORITY}/token",
        data={
            "client_id": client_id(),
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "scope": SCOPES,
        },
    )
    save_token(refreshed)
    return refreshed["access_token"]


def graph_get(path: str, params: dict[str, str] | None = None) -> dict:
    query = urllib.parse.urlencode(params or {}, safe="(),:$'")
    url = f"{GRAPH}{path}"
    if query:
        url = f"{url}?{query}"
    return http_json("GET", url, token=access_token())


def iso_utc(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today_bounds(tz_name: str) -> tuple[str, str]:
    zone = timezone(tz_name)
    now = dt.datetime.now(zone)
    start = dt.datetime(now.year, now.month, now.day, tzinfo=zone)
    end = start + dt.timedelta(days=1)
    return iso_utc(start), iso_utc(end)


def timezone(tz_name: str) -> dt.tzinfo:
    if tz_name in {"Asia/Bangkok", "ICT", "+07:00", "+0700"}:
        return dt.timezone(dt.timedelta(hours=7), name="Asia/Bangkok")
    if tz_name.upper() in {"UTC", "Z", "+00:00", "+0000"}:
        return dt.timezone.utc
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as exc:
        raise OutlookError(f"Unknown timezone '{tz_name}'. Try '+07:00' or 'UTC'.") from exc


def list_today(limit: int, tz_name: str) -> list[dict]:
    start, end = today_bounds(tz_name)
    params = {
        "$top": str(limit),
        "$select": "subject,from,receivedDateTime,bodyPreview,webLink,hasAttachments,importance",
        "$filter": f"receivedDateTime ge {start} and receivedDateTime lt {end}",
        "$orderby": "receivedDateTime desc",
    }
    return graph_get("/me/mailFolders/inbox/messages", params).get("value", [])


def search_messages(query: str, limit: int) -> list[dict]:
    params = {
        "$top": str(limit),
        "$select": "subject,from,receivedDateTime,bodyPreview,webLink,hasAttachments,importance",
        "$search": f'"{query}"',
    }
    return graph_get("/me/messages", params).get("value", [])


def normalize(message: dict) -> dict:
    sender = (message.get("from") or {}).get("emailAddress") or {}
    return {
        "receivedDateTime": message.get("receivedDateTime"),
        "from": sender.get("address") or sender.get("name"),
        "fromName": sender.get("name"),
        "subject": message.get("subject"),
        "importance": message.get("importance"),
        "hasAttachments": message.get("hasAttachments"),
        "bodyPreview": message.get("bodyPreview"),
        "webLink": message.get("webLink"),
    }


def render(messages: list[dict]) -> None:
    print(json.dumps({"count": len(messages), "messages": [normalize(m) for m in messages]}, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read Outlook mail through Microsoft Graph.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("login", help="Sign in with Microsoft device code flow.")
    today = sub.add_parser("today", help="List inbox messages received today.")
    today.add_argument("--limit", type=int, default=20)
    today.add_argument("--timezone", default=os.environ.get("TZ", "Asia/Bangkok"))
    search = sub.add_parser("search", help="Search messages.")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    args = parser.parse_args(argv)

    try:
        if args.command == "login":
            login()
        elif args.command == "today":
            render(list_today(args.limit, args.timezone))
        elif args.command == "search":
            render(search_messages(args.query, args.limit))
        return 0
    except OutlookError as exc:
        print(f"outlook-mail: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
