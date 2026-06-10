import base64
import json
from pathlib import Path
import urllib.request
import fal_client

project = Path(r'E:\ThanhMV\video-projects\motion-test-01')
storyboard = project / 'storyboard.json'
config = json.loads(storyboard.read_text(encoding='utf-8-sig'))
scene = config['scenes'][0]
image_path = project / scene['image']
output = project / 'output' / 'fal-kling-motion-test-01.mp4'
output.parent.mkdir(parents=True, exist_ok=True)

encoded = base64.b64encode(image_path.read_bytes()).decode('ascii')
image_url = 'data:image/png;base64,' + encoded
prompt = scene.get('video_prompt') or scene.get('image_prompt')

result = fal_client.subscribe(
    'fal-ai/kling-video/v2.5-turbo/standard/image-to-video',
    arguments={
        'image_url': image_url,
        'prompt': prompt,
        'duration': '5',
        'negative_prompt': 'blur, distort, low quality, watermark, text, logo, deformed scene, warped cabin, flickering artifacts',
        'cfg_scale': 0.5,
    },
    with_logs=True,
)
print(json.dumps(result, ensure_ascii=False, indent=2))
video_url = result.get('video', {}).get('url')
if not video_url:
    raise SystemExit('No video URL returned')
with urllib.request.urlopen(video_url, timeout=600) as response:
    output.write_bytes(response.read())
scene['fal_kling_video'] = str(output.relative_to(project)).replace('\\', '/')
storyboard.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
print('saved=' + str(output))
