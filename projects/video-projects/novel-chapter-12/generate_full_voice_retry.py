import asyncio
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

EXTRA = Path(r'E:\ThanhMV\python-packages')
if EXTRA.exists():
    sys.path.insert(0, str(EXTRA))
import edge_tts

PROJECT = Path(r'E:\ThanhMV\video-projects\novel-chapter-12')
STORYBOARD = PROJECT / 'storyboard-full.json'
ASSETS = PROJECT / 'assets'
TEMP_ROOT = Path(r'E:\ThanhMV\temp\tts-chunks')
TEMP_ROOT.mkdir(parents=True, exist_ok=True)
VOICE = 'vi-VN-HoaiMyNeural'
RATE = '-5%'
PITCH = '+0Hz'


def split_text(text, limit=420):
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks, current = [], ''
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(current) + len(part) + 1 <= limit:
            current = (current + ' ' + part).strip()
        else:
            if current:
                chunks.append(current)
            if len(part) > limit:
                words = part.split()
                current = ''
                for word in words:
                    if len(current) + len(word) + 1 <= limit:
                        current = (current + ' ' + word).strip()
                    else:
                        chunks.append(current)
                        current = word
            else:
                current = part
    if current:
        chunks.append(current)
    return chunks


async def synth(text, output):
    last_error = None
    for attempt in range(1, 5):
        try:
            if output.exists():
                output.unlink()
            communicate = edge_tts.Communicate(text=text, voice=VOICE, rate=RATE, pitch=PITCH)
            await communicate.save(str(output))
            if output.exists() and output.stat().st_size > 1024:
                return
            last_error = RuntimeError('empty audio')
        except Exception as exc:
            last_error = exc
        await asyncio.sleep(2 * attempt)
    raise RuntimeError(f'TTS failed after retries: {last_error}')


def concat_mp3(chunks, output):
    if len(chunks) == 1:
        shutil.copyfile(chunks[0], output)
        return
    list_file = output.with_suffix('.concat.txt')
    list_file.write_text(''.join(f"file '{p.as_posix()}'\n" for p in chunks), encoding='utf-8')
    subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(list_file), '-c:a', 'libmp3lame', '-b:a', '64k', str(output)], check=True)


async def main():
    data = json.loads(STORYBOARD.read_text(encoding='utf-8-sig'))
    for index, scene in enumerate(data['scenes'], 1):
        output = ASSETS / f'full-scene-{index:02d}.mp3'
        scene['audio'] = f'assets/full-scene-{index:02d}.mp3'
        scene.setdefault('subtitle', scene.get('text', ''))
        if output.exists() and output.stat().st_size > 1024:
            print(f'Scene {index:02d}: exists {output.stat().st_size} bytes')
            continue
        chunks = split_text(scene['narration'])
        chunk_dir = TEMP_ROOT / f'scene-{index:02d}'
        chunk_dir.mkdir(parents=True, exist_ok=True)
        chunk_paths = []
        print(f'Scene {index:02d}: {len(chunks)} chunk(s)')
        for chunk_index, chunk in enumerate(chunks, 1):
            chunk_path = chunk_dir / f'chunk-{chunk_index:02d}.mp3'
            await synth(chunk, chunk_path)
            chunk_paths.append(chunk_path)
        concat_mp3(chunk_paths, output)
        print(f'  wrote {output} {output.stat().st_size} bytes')
    STORYBOARD.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

asyncio.run(main())
