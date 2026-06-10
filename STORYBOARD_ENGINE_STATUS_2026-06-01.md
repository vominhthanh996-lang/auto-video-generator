## Storyboard engine status - 2026-06-01

### Goal
Make the shared storyboard/image logic follow the story accurately across future parts, not just one chapter:
- characters must match the narration
- backgrounds and locations must match the plot
- no repeated default shelter/two-shot composition
- actions must be readable from the image
- fewer deformed / fused / wrong-age characters

### Files changed
- `E:\ThanhMV\auto-video-generator\scripts\run_story_pipeline.py`
- `E:\ThanhMV\auto-video-generator\scripts\generate_images_comfy_local.py`

### Big engine changes already in
1. `run_story_pipeline.py`
   - smarter scene grouping, not pure word-count splitting
   - soft `max-scenes` cap works again
   - generalized beat classifier added
   - generalized location inference added
   - chapter-boundary continuity reset added
   - supporting cast descriptors added:
     - Ninh
     - Tieu Mai
     - Tieu Bao
     - A That
     - Di Man
     - Bach Nhi
     - etc.
   - continuity anchors now filtered:
     - keep character/world identity
     - stop carrying old scene locations like shelter/rail/station into unrelated new scenes
   - primary subject prompt now uses visual descriptors, not only plain names
   - well scenes now prefer a dedicated `well discovery shot` instead of being mistaken for threshold-negotiation

2. `generate_images_comfy_local.py`
   - default image flow is now landscape-friendly for story scenes
   - scene prompt now uses a more structured prompt path:
     - subject
     - setting
     - action
     - props
     - shot
   - cast notes added for:
     - Ninh as a child
     - Tieu Mai as a child
     - Tieu Bao as a very young child
     - A That as a young male scavenger
     - Di Man as an older woman
     - Bach Nhi as a trader
   - extra guardrails:
     - show every named child/companion if named
     - keep well visible when the scene is about the water source
     - keep Bach Nhi as trader/host in market scenes
   - removed more noisy story-excerpt text from the image-generation prompt so the model gets a shorter, more concrete instruction

### Cross-part rebuilds already done
- `tap-02 part-01` rebuilt repeatedly, current working version at:
  - `E:\ThanhMV\auto-video-generator\projects\storyboards\tap-02-storyboards\phan-01-duong-ray-khong-dan-ve-nha\storyboard.json`
- `tap-02 part-02` rebuilt repeatedly, current working version at:
  - `E:\ThanhMV\auto-video-generator\projects\storyboards\tap-02-storyboards\phan-02-ga-xam\storyboard.json`

Both currently validate at text stage with:
- `160 scenes`
- no validation errors

### Sample test packs
Workspace sample storyboards:
- `C:\Users\thanh\.codex\worktrees\b99d\New project\storyboard_samples\tap02_part01_samples\storyboard.json`
- `C:\Users\thanh\.codex\worktrees\b99d\New project\storyboard_samples\tap02_part02_samples\storyboard.json`

Current chosen scenes:
- part 1:
  - `scene-014`
  - `scene-034`
  - `scene-069`
- part 2:
  - `scene-017`
  - `scene-022`
  - `scene-029`

### What improved
- no more obvious collapse back into the old shelter/two-shot default
- Gray Station visuals are more station-like than before
- some multi-character scenes now keep 3 figures instead of collapsing to 1
- anatomy is generally stable in tested renders

### What is still not good enough
1. child casting still drifts
   - Ninh/Tieu Mai scenes can still become older teens/adults
2. some well scenes still drift
   - even after the well-shot fix, sample output can still miss the actual well
3. market scenes still drift in role clarity
   - Bach Nhi not always reading like a trader
   - buyer/seller balance can still collapse into generic standing figures

### Most recent visual read
Latest rerender still shows:
- `part01 scene-014`: better than before, now often 3 figures, but age/cast is still not fully reliable
- `part01 scene-034`: still weak, the water-source/well is not consistently visible
- `part02 scene-017/022/029`: station environment is closer, but cast-role clarity is still not fully stable

### Best next step
Continue from here:
1. rerender the latest sample packs again after the newest prompt-shortening patch
2. if well scene still misses the well:
   - strengthen scene prompt to require the well mouth or hanging tin can in foreground
3. if child scenes still drift:
   - add stronger explicit age/height contrast in prompt
   - possibly use `child` wording twice in subject and composition instructions
4. if market scenes still drift:
   - force `seller behind table + buyer in front` role blocking when `market-bargain` is active

### Useful commands
Start ComfyUI:
```powershell
& 'E:\ThanhMV\auto-video-generator\scripts\start_comfyui_service.ps1'
```

Rebuild part 1:
```powershell
& 'C:\Users\thanh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'E:\ThanhMV\auto-video-generator\scripts\run_story_pipeline.py' --source 'E:\ThanhMV\auto-video-generator\projects\storyboards\tap-02-storyboards\phan-01-duong-ray-khong-dan-ve-nha\source.txt' --project 'E:\ThanhMV\auto-video-generator\projects\storyboards\tap-02-storyboards\phan-01-duong-ray-khong-dan-ve-nha' --title 'phan-01-duong-ray-khong-dan-ve-nha' --words-per-image 24 --min-scenes 0 --max-scenes 160 --skip-images --skip-voice --skip-sfx --skip-render
```

Rebuild part 2:
```powershell
& 'C:\Users\thanh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'E:\ThanhMV\auto-video-generator\scripts\run_story_pipeline.py' --source 'E:\ThanhMV\auto-video-generator\projects\storyboards\tap-02-storyboards\phan-02-ga-xam\source.txt' --project 'E:\ThanhMV\auto-video-generator\projects\storyboards\tap-02-storyboards\phan-02-ga-xam' --title 'phan-02-ga-xam' --words-per-image 24 --min-scenes 0 --max-scenes 160 --skip-images --skip-voice --skip-sfx --skip-render
```

Rerender sample pack:
```powershell
& 'C:\Users\thanh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' 'E:\ThanhMV\auto-video-generator\scripts\generate_images_comfy_local.py' --storyboard 'C:\Users\thanh\.codex\worktrees\b99d\New project\storyboard_samples\tap02_part01_samples\storyboard.json' --preset safe --overwrite
```


## 2026-06-01 late update
- Added generalized scene-center fields into storyboard output.
- Reduced false well-trigger caused by generic "co nuoc" mentions.
- Added generalized exchange/object center rules for:
  - Ninh writing-board scenes
  - Gray Station first-stall introduction
  - trade goods placed on a table
  - damp-water clue scenes
- Added generalized character pruning so non-central characters do not automatically flood the frame.
- Stopped treating `rang cho hai ham` as a live monster character in trade scenes.
- Updated Lam Tich / Tan Da default style:
  - Lam Tich: beautiful, feminine, wasteland summer clothing, arms/legs/upper chest may show, still YouTube-safe
  - Tan Da: tall, muscular, handsome, upright heroic presence
- Added stronger child identity rules:
  - Ninh = preteen mute boy
  - Tieu Mai = preteen girl
- Sample rerender status:
  - p1_s014 still wrong: model still drifts to adult/male figures despite child-scene rules
  - p2_s022 partly better: table and goods are readable, but still duplicates the presenter
- Next best fixes:
  1. remove raw dialogue lines from must_show priority in dialogue scenes
  2. make child scenes use a dedicated child-scene composition string with boy/girl count baked in
  3. make single-presenter trade scenes suppress any second standing figure unless named in narration
  4. rerender p1_s014, p2_s022, then test p1_s034 and p2_s029

- Further tightened generalized subject-count rules:
  - Ninh writing-board scenes now prune to Ninh + Tieu Mai only in central framing
  - single-presenter object-center scenes now explicitly ask for exactly one presenter
  - child exchange scenes now explicitly ask for exactly two children in frame
