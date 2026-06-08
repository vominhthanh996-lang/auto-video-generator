from pathlib import Path
from PIL import Image, ImageDraw
scenes = [1,3,4,9,12,13,14,22,30,34,38,39,40,45,48,57,60,62,65]
base = Path(r'E:\ThanhMV\auto-video-generator\projects\storyboards\tap-02-storyboards\phan-01-duong-ray-khong-dan-ve-nha\assets')
out_dir = Path(r'C:\Users\thanh\.codex\worktrees\b99d\New project\scratch_compare\tap02_part1_current19_scoring')
thumb_w, thumb_h = 320, 180
cols = 2
rows_per_page = 5
page_w = cols * thumb_w + 60
page_h = rows_per_page * (thumb_h + 40) + 40
page_idx = 1
slot = 0
for i, scene in enumerate(scenes):
    if slot == 0:
        page = Image.new('RGB', (page_w, page_h), 'white')
        draw = ImageDraw.Draw(page)
    img = Image.open(base / f'scene-{scene:03d}.png').convert('RGB')
    img.thumbnail((thumb_w, thumb_h))
    row = slot // cols
    col = slot % cols
    x = 20 + col * thumb_w
    y = 20 + row * (thumb_h + 40)
    page.paste(img, (x, y))
    draw.text((x, y + thumb_h + 8), f'scene-{scene:03d}', fill='black')
    slot += 1
    if slot == cols * rows_per_page or i == len(scenes) - 1:
        page.save(out_dir / f'page-{page_idx:02d}.png')
        page_idx += 1
        slot = 0
print(out_dir)
