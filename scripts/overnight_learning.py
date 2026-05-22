#!/usr/bin/env python3
"""
Cloud-friendly overnight learning logger.

This script is designed for GitHub Actions. It does not render media and does
not need the user's local E: drive. It searches lightweight web result pages,
summarizes practical lessons for the video pipeline, and appends a readable
Vietnamese checkpoint to references/learning_sprint_log.md.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import textwrap
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


DEFAULT_QUERIES = [
    "Vietnamese audiobook narration emotional pacing YouTube",
    "truyen audio ke chuyen dem khuya giong doc truyen cam",
    "AI narrated story video visual continuity storyboard",
    "cinematic storyboarding continuity character action progression",
    "character consistent AI images story video continuity",
    "post apocalyptic story video AI narration visuals",
]

@dataclass
class SearchResult:
    query: str
    title: str
    url: str
    snippet: str


FALLBACK_RESULTS = [
    SearchResult(
        "audiobook narration pacing",
        "Microsoft Speech SSML voice and prosody documentation",
        "https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-voice",
        "Official reference for rate, pitch, pauses, and speech synthesis markup.",
    ),
    SearchResult(
        "audiobook narration character consistency",
        "Voices: audiobook narration and finding a narrator voice",
        "https://www.voices.com/blog/audiobook-narrators-find-voice/",
        "Practical narration guidance about choosing and sustaining a story voice.",
    ),
    SearchResult(
        "storyboard visual continuity",
        "StudioBinder storyboard and visual storytelling guides",
        "https://www.studiobinder.com/blog/what-is-a-storyboard/",
        "Storyboard basics for planning shots, action, and visual continuity.",
    ),
    SearchResult(
        "visual continuity editing",
        "Wikipedia: continuity editing",
        "https://en.wikipedia.org/wiki/Continuity_editing",
        "Explains continuity between shots so viewers understand space, time, and action.",
    ),
]


def fetch_url(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; auto-video-generator-learning/1.0; "
                "+https://github.com/)"
            )
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def ddg_lite_search(query: str, limit: int = 4) -> list[SearchResult]:
    url = "https://lite.duckduckgo.com/lite/?" + urllib.parse.urlencode({"q": query})
    try:
        raw = fetch_url(url)
    except Exception as exc:
        return [SearchResult(query, "SEARCH_FAILED", url, str(exc))]

    rows = re.findall(
        r'<a rel="nofollow" href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?'
        r'<td class="result-snippet">(?P<snippet>.*?)</td>',
        raw,
        flags=re.S,
    )
    results: list[SearchResult] = []
    for result_url, title, snippet in rows[:limit]:
        clean_title = re.sub(r"\s+", " ", html.unescape(re.sub("<.*?>", "", title))).strip()
        clean_snippet = re.sub(r"\s+", " ", html.unescape(re.sub("<.*?>", "", snippet))).strip()
        clean_url = html.unescape(result_url)
        if clean_url.startswith("//duckduckgo.com/l/?uddg="):
            parsed = urllib.parse.urlparse("https:" + clean_url)
            query_params = urllib.parse.parse_qs(parsed.query)
            clean_url = urllib.parse.unquote(query_params.get("uddg", [clean_url])[0])
        results.append(SearchResult(query, clean_title, clean_url, clean_snippet))
    return results


def youtube_api_search(query: str, limit: int = 4) -> list[SearchResult]:
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        return []
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": str(limit),
        "key": key,
    }
    url = "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode(params)
    try:
        data = json.loads(fetch_url(url))
    except Exception as exc:
        return [SearchResult(query, "YOUTUBE_API_FAILED", url, str(exc))]
    results = []
    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId", "")
        snippet = item.get("snippet", {})
        results.append(
            SearchResult(
                query=query,
                title=snippet.get("title", ""),
                url=f"https://www.youtube.com/watch?v={video_id}" if video_id else url,
                snippet=snippet.get("description", ""),
            )
        )
    return results


def infer_lessons(results: list[SearchResult]) -> tuple[list[str], list[str], list[str]]:
    joined = " ".join((r.title + " " + r.snippet).lower() for r in results)
    voice = [
        "Giữ một giọng kể nền ổn định trong cả tập; cảm xúc chỉ nên dao động nhẹ theo cảnh.",
        "Đừng đọc nhanh để chạy chữ. Với truyện dài, sự dễ nghe quan trọng hơn tốc độ.",
        "Thoại nhân vật cần khác lời dẫn, nhưng khác bằng nhịp/pause/độ chắc, không giả giọng quá lố.",
    ]
    visual = [
        "Ảnh phải bám hành động trong audio trước, sau đó mới tối ưu cinematic.",
        "Mỗi scene cần continuity anchors: nhân vật, địa điểm, đạo cụ, trạng thái vết thương/quần áo.",
        "Storyboard phải có handoff rõ: scene sau tiếp nối hành động của scene trước.",
    ]
    pipeline = [
        "Trước khi gen full phần 2, tạo storyboard + visual bible + audit rồi mới gen sample.",
        "Contact sheet cần hiển thị MUST SHOW để so ảnh với narration nhanh.",
        "Voice-plan và visual-plan nên được giữ lại để review từng scene thay vì sửa mò.",
    ]

    if "character" in joined or "voice" in joined:
        voice.append("Cần character bible để giữ tính cách giọng nhân vật qua nhiều chương.")
    if "storyboard" in joined or "continuity" in joined:
        visual.append("Cần shot type theo beat: establishing, medium action, close prop, hiding POV.")
    if "ai" in joined and "video" in joined:
        pipeline.append("Nên thêm bước sample 3-5 ảnh trước khi tiêu tài nguyên cho cả chương.")
    return voice, visual, pipeline


def format_result(result: SearchResult) -> str:
    title = result.title or "(no title)"
    url = result.url or ""
    snippet = result.snippet or ""
    if len(snippet) > 220:
        snippet = snippet[:217].rstrip() + "..."
    return f"- {title}\n  URL: {url}\n  Ghi chú: {snippet}"


def append_log(log_path: Path, results: list[SearchResult], dry_run: bool = False) -> str:
    now = datetime.now(timezone.utc).astimezone()
    voice, visual, pipeline = infer_lessons(results)
    source_lines = "\n".join(format_result(result) for result in results[:18])
    entry = f"""

---

## {now:%Y-%m-%d %H:%M %Z} - Overnight Learning Checkpoint

### Tao Đã Search/Học Từ Đâu

{source_lines if source_lines else "- Không lấy được kết quả search trong lần chạy này."}

### Tao Học Được Gì Về Voice

{chr(10).join("- " + item for item in voice)}

### Tao Học Được Gì Về Hình/Storyboard

{chr(10).join("- " + item for item in visual)}

### Ảnh Hưởng Tới Pipeline Của Mình

{chr(10).join("- " + item for item in pipeline)}

### Việc Nên Làm Tiếp

- Với phần 2, tạo `visual_bible.json` và `character_voice_bible.json` riêng trước khi gen full.
- Audit storyboard trước, sau đó gen 3-5 ảnh mẫu để xem có khớp narration không.
- Sau khi mày nghe audio phần 2, ghi feedback theo nhân vật/trait để generator học tiếp.
"""
    entry = textwrap.dedent(entry).strip() + "\n"
    if not dry_run:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write("\n" + entry)
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description="Append an overnight learning checkpoint log.")
    parser.add_argument("--log", type=Path, default=Path("references/learning_sprint_log.md"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit-per-query", type=int, default=3)
    args = parser.parse_args()

    results: list[SearchResult] = []
    for query in DEFAULT_QUERIES:
        results.extend(youtube_api_search(query, args.limit_per_query))
        results.extend(ddg_lite_search(query, args.limit_per_query))

    seen = set()
    unique_results = []
    for result in results:
        key = (result.title, result.url)
        if key in seen:
            continue
        seen.add(key)
        unique_results.append(result)
    if not unique_results or all(result.title.endswith("_FAILED") for result in unique_results):
        unique_results = FALLBACK_RESULTS + [
            SearchResult(
                query,
                "Search query prepared for next cloud run",
                "https://duckduckgo.com/?" + urllib.parse.urlencode({"q": query}),
                "Fallback query URL because the current run could not parse live search results.",
            )
            for query in DEFAULT_QUERIES[:4]
        ]

    entry = append_log(args.log, unique_results, dry_run=args.dry_run)
    print(entry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
