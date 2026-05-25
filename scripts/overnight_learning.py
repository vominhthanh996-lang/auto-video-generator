#!/usr/bin/env python3
"""
Cloud-friendly auto learning logger.

This script is designed for GitHub Actions. It never renders media and never
touches local project assets. Each run searches for fresh sources, skips links
already written to the learning logs, and appends human-readable Vietnamese
notes about voice, visuals, and pipeline improvements.
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
    "YouTube truyện mạt thế viral giọng đọc truyền cảm",
    "YouTube truyện phế thổ audio viral hình ảnh AI",
    "truyện audio Việt Nam giọng đọc nhân vật khác nhau",
    "audiobook narration character voices consistency pacing emotion",
    "viral AI narrated story videos visual continuity character consistency",
    "post apocalyptic wasteland story video YouTube cinematic AI images",
    "storyboard continuity character consistent AI images long story video",
    "AI video story narration match visuals to audio",
]

VIRAL_HINTS = [
    "viral",
    "youtube",
    "truyện",
    "truyen",
    "mạt thế",
    "mat the",
    "phế thổ",
    "phe tho",
    "audiobook",
    "narration",
    "story",
    "storyboard",
    "continuity",
    "character",
    "ai video",
]

ACTION_ITEMS_PATH = Path("references/learning_action_items.md")


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
                "Mozilla/5.0 (compatible; auto-video-generator-learning/2.0; "
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


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    if "youtube.com" in parsed.netloc and "v" in query:
        return f"https://www.youtube.com/watch?v={query['v'][0]}"
    if "youtu.be" in parsed.netloc:
        video_id = parsed.path.strip("/")
        return f"https://www.youtube.com/watch?v={video_id}" if video_id else url
    clean_query = urllib.parse.urlencode(
        {
            key: value[0]
            for key, value in sorted(query.items())
            if not key.lower().startswith("utm_")
        }
    )
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), "", clean_query, "")
    )


def load_used_urls(paths: list[Path]) -> set[str]:
    used: set[str] = set()
    url_pattern = re.compile(r"https?://[^\s)>\"]+")
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for url in url_pattern.findall(text):
            used.add(normalize_url(url.rstrip(".,;]")))
    return used


def score_result(result: SearchResult) -> int:
    haystack = f"{result.query} {result.title} {result.snippet} {result.url}".lower()
    score = 0
    for hint in VIRAL_HINTS:
        if hint in haystack:
            score += 2
    if "youtube.com/watch" in result.url or "youtu.be/" in result.url:
        score += 6
    if any(word in haystack for word in ["official", "guide", "paper", "research"]):
        score += 1
    if result.title.endswith("_FAILED"):
        score -= 20
    return score


def infer_lessons(results: list[SearchResult]) -> tuple[list[str], list[str], list[str], list[str]]:
    joined = " ".join((r.title + " " + r.snippet).lower() for r in results)
    voice = [
        "Giọng kể chuyện phải ổn định, rõ chữ, có cảm xúc nền nhưng không kéo pause quá dài. Người nghe truyện dài cần cảm giác trôi, không bị ngắt vụn.",
        "Mỗi nhân vật cần một lane giọng riêng khác narrator: tốc độ, pitch, độ lạnh/ấm, độ căng, kiểu ngắt câu. Lane đó phải giữ nhất quán từ đầu đến cuối.",
        "Nhân vật không nên chỉ khác bằng giả giọng. Khác biệt nên đến từ tính cách: kẻ lạnh nói ít và chắc; người thật thà mềm hơn; phản diện nén giọng thấp; kẻ nịnh nọt có nhịp nhanh và mềm.",
        "Voice plan cần ghi lý do vì sao scene dùng nhịp đó: narration, nội tâm, nguy hiểm gần, đối thoại, reveal, hoặc cao trào.",
    ]
    visual = [
        "Ảnh phải bám câu đang đọc trước, đẹp sau. Nếu audio nói nhân vật đang bò dưới gầm xe thì hình phải có gầm xe, tư thế bò, mối nguy gần đó.",
        "Vibe viral không chỉ là màu cinematic. Nó là khung hình dễ hiểu trong 1 giây: nhân vật rõ, nguy hiểm rõ, đạo cụ rõ, không gian đúng truyện.",
        "Nhân vật phải có visual bible: tuổi, vóc dáng, tóc, quần áo, vết thương, đạo cụ đang cầm, trạng thái cảm xúc. Prompt sau không được tự đổi nhân vật.",
        "Cảnh sau phải kế thừa cảnh trước: cùng bối cảnh, cùng hướng hành động, cùng đạo cụ, cùng mức thương tích. Tránh slideshow mỗi ảnh một thế giới.",
        "Chuyển động nên hợp logic truyện: mưa/gió/bụi/khói/ánh đèn/cây/camera push nhẹ; nhân vật có hành động nhỏ đúng scene, không đứng tạo dáng vô nghĩa.",
    ]
    pipeline = [
        "Auto learning chỉ ghi log và action items. Không render, không gen thử, không overwrite part 1 assets.",
        "Mỗi checkpoint phải ưu tiên link mới, không lặp lại YouTube/web URL đã học ở các lần trước.",
        "Tạo `character_voice_bible.json` cho mỗi truyện: narrator + từng nhân vật + trait + pitch/rate/pause mục tiêu.",
        "Tạo `visual_bible.json` và `scene_state.json` để giữ nhân vật, bối cảnh, đạo cụ và trạng thái xuyên suốt.",
        "Thêm audit storyboard trước khi gen: mỗi scene phải có `must_show`, `current_action`, `location_anchor`, `previous_state`, `next_handoff`.",
    ]
    actions = [
        "Đổi voice generator sang character-lane: narrator riêng, từng nhân vật riêng, giữ consistency bằng `character_voice_bible.json`.",
        "Giảm pause quá dài trong voice style mặc định, ưu tiên nhịp kể tự nhiên và chỉ pause mạnh ở reveal/cao trào.",
        "Dùng log hiện có để chặn trùng URL giữa các checkpoint; nếu đã học link rồi thì bỏ qua.",
        "Thêm `learning_action_items.md` để gom việc nên code sau này, tách khỏi log học dài.",
        "Thêm scoring cho storyboard: khớp audio, đúng nhân vật, đúng đạo cụ, đúng không gian, continuity với scene trước.",
    ]

    if "character" in joined or "voice" in joined:
        voice.append("Khi nguồn nhắc character voice, áp dụng thành rule: một nhân vật đã có lane thì các chương sau phải reuse lane đó, không auto đổi voice.")
    if "storyboard" in joined or "continuity" in joined:
        visual.append("Khi nguồn nhắc continuity/storyboard, áp dụng thành rule: shot sau phải có `previous_state` và `next_handoff`.")
    if "ai" in joined and "video" in joined:
        pipeline.append("AI image/video chỉ nên chạy sau khi storyboard pass audit; learning runner không gọi bất kỳ script gen asset nào.")
    return voice, visual, pipeline, actions


def format_result(result: SearchResult) -> str:
    title = result.title or "(no title)"
    url = result.url or ""
    snippet = result.snippet or ""
    if len(snippet) > 220:
        snippet = snippet[:217].rstrip() + "..."
    return f"- {title}\n  URL: {url}\n  Ghi chú: {snippet}"


def append_log(log_path: Path, action_path: Path, results: list[SearchResult], dry_run: bool = False) -> str:
    now = datetime.now(timezone.utc).astimezone()
    voice, visual, pipeline, actions = infer_lessons(results)
    source_lines = "\n".join(format_result(result) for result in results[:18])
    entry = f"""

---

## {now:%Y-%m-%d %H:%M %Z} - Auto Learning Checkpoint

### Tao Đã Search/Học Từ Đâu

{source_lines if source_lines else "- Không lấy được kết quả search mới trong lần chạy này."}

### Tao Học Được Gì Về Voice

{chr(10).join("- " + item for item in voice)}

### Tao Học Được Gì Về Hình/Storyboard

{chr(10).join("- " + item for item in visual)}

### Ảnh Hưởng Tới Pipeline Của Mình

{chr(10).join("- " + item for item in pipeline)}

### Action Items Nên Cân Nhắc

{chr(10).join("- " + item for item in actions)}
"""
    entry = textwrap.dedent(entry).strip() + "\n"
    if not dry_run:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write("\n" + entry)
        action_path.parent.mkdir(parents=True, exist_ok=True)
        with action_path.open("a", encoding="utf-8") as handle:
            handle.write(
                f"\n\n---\n\n## {now:%Y-%m-%d %H:%M %Z} - Auto Learning Action Items\n\n"
                + "\n".join("- " + item for item in actions)
                + "\n"
            )
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description="Append an auto learning checkpoint log.")
    parser.add_argument("--log", type=Path, default=Path("references/learning_sprint_log.md"))
    parser.add_argument("--action-items", type=Path, default=ACTION_ITEMS_PATH)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit-per-query", type=int, default=3)
    args = parser.parse_args()

    results: list[SearchResult] = []
    for query in DEFAULT_QUERIES:
        results.extend(youtube_api_search(query, args.limit_per_query))
        results.extend(ddg_lite_search(query, args.limit_per_query))

    used_urls = load_used_urls([args.log, args.action_items])
    seen = set()
    unique_results = []
    for result in sorted(results, key=score_result, reverse=True):
        clean_url = normalize_url(result.url)
        if clean_url and clean_url in used_urls:
            continue
        key = (result.title.strip().lower(), clean_url)
        if key in seen:
            continue
        seen.add(key)
        result.url = clean_url or result.url
        unique_results.append(result)

    if not unique_results or all(result.title.endswith("_FAILED") for result in unique_results):
        unique_results = [result for result in FALLBACK_RESULTS if normalize_url(result.url) not in used_urls] + [
            SearchResult(
                query,
                "Search query prepared for next cloud run",
                "https://duckduckgo.com/?" + urllib.parse.urlencode({"q": query}),
                "Fallback query URL because the current run could not parse live search results.",
            )
            for query in DEFAULT_QUERIES[:4]
        ]

    entry = append_log(args.log, args.action_items, unique_results, dry_run=args.dry_run)
    print(entry)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
