# Learning Sprint Log

## 2026-05-21 - Voice + Visual Storytelling Sprint

### Scope

- Improve narrated story videos for Vietnamese wasteland/apocalypse webnovels.
- Focus on two failure points found in part 1:
  - images looked cinematic but did not always match the narration;
  - voice needed stronger long-form narrator consistency and character memory.

### Sources Reviewed

- Vietnamese `truyện audio`, `kể chuyện đêm khuya`, and `tiểu thuyết radio` YouTube/Music results.
- AI cinematic storytelling channels with generated visuals and narration.
- Audio narration craft references about pacing, character voices, scene breaks, and audiobook consistency.
- Visual storytelling/storyboard references about scene continuity and story-beat handoff.

### Learned: Voice

- A good narrator voice stays stable across the whole episode; emotion should be a controlled wave on top of that base, not a different style every sentence.
- Vietnamese night-story channels often keep a calm, even delivery, then use pauses and sentence endings to create emotion instead of constant dramatic pitch changes.
- Long videos need listener comfort more than theatrical performance; exaggerated character acting becomes tiring.
- Character differentiation should be subtle:
  - villain: lower, slower, more controlled pause;
  - hypocrite: polite, smooth, too neat, not openly evil too soon;
  - righteous: steady, firm, grounded;
  - honest: plain, open, slightly slower;
  - flattering: brighter, quicker, shorter pauses;
  - spoiled: softer, slightly higher, lightly stretched;
  - afraid: faster, higher, less pause;
  - cold: slower, lower, distant.
- A character voice bible is required for long stories; keyword detection alone is not enough.
- Feedback should be targetable by character and trait, not only global narrator speed.
- A `voice-plan.json` is useful because it exposes how the generator classified each unit before the user reviews audio.

### Learned: Visuals

- The image must match the audio before it tries to be beautiful.
- Story videos fail when each image is generated as a standalone wallpaper.
- Each image needs a clear story beat:
  - who is present;
  - where they are;
  - what action is happening;
  - what important props are visible;
  - what changed from the previous scene.
- Adjacent images need continuity anchors:
  - same character appearance;
  - same location unless narration changes it;
  - same critical props;
  - wounds/costume state;
  - threat position;
  - previous action handoff.
- Contact sheets should show the required visual contract, not just the generated images.
- Audit should flag prompts that lack action, `MUST SHOW`, shot type, or continuity anchors.

### Implemented So Far

- Added `wasteland-dark` and `story-emotional` voice styles.
- Added dynamic voice detection for danger, soft emotion, inner monologue, reveal, list, dialogue, cliffhanger.
- Added narrator-flow smoothing to avoid rate/pitch jumps.
- Added character archetypes and subtle voice lanes.
- Added `character_voice_bible.example.json`.
- Added character/trait-specific feedback in `record_voice_feedback.py`.
- Added `voice_director_notes.md`.
- Added story-beat visual prompt generation with `MUST SHOW`.
- Added visual continuity anchors and shot types.
- Added `audit_visual_alignment.py`.
- Added `visual_director_notes.md`.

### Next Improvements To Consider

- Generate a real `character_voice_bible.json` per story by reading the first chapter or synopsis.
- Add a `build_character_bible.py` script to extract characters, aliases, traits, and visual appearance from source text.
- Add `visual_style_bible.json` for character appearance and location continuity.
- Add image review scoring fields to contact sheet: `matches narration`, `character consistency`, `prop visibility`, `action clarity`.
- Add a pre-generation storyboard review step for part 2: create storyboard and audit, then generate only 3-5 sample images before full batch.
- Later, add actual audio review tooling that reads `voice-plan.json` and records feedback by scene.

---

## 2026-05-21 - Learning Checkpoint 02: Make The Log Human-Readable

### Tao Đã Học Ở Đâu

- Search YouTube/web về: AI story video, narrated apocalypse story, truyện mạt thế/phế thổ có hình, truyện audio giọng thật.
- Xem thêm các tool/storyboard AI đang quảng bá cách giữ continuity: Vibit, StoryIntoVideo, CinemaDrop, các bài/paper mới về continuity-aware storyboarding.
- Đọc thêm khái niệm dựng phim/storyboard: continuity editing, storyboard, visual narrative structure.

### Điều Tao Rút Ra Bằng Tiếng Người

1. Ảnh đẹp không đủ.
   Nếu audio nói "Lâm Tịch trốn dưới gầm xe" mà hình lại là một cô gái đứng giữa phố hoang thì người xem thấy sai ngay.

2. Mỗi ảnh phải trả lời 5 câu:
   - Ai đang ở trong cảnh?
   - Họ đang ở đâu?
   - Họ đang làm gì?
   - Vật quan trọng nào phải thấy?
   - Cảnh này nối từ cảnh trước như thế nào?

3. Video truyện cần continuity anchors.
   Tức là vài thứ phải lặp lại qua nhiều ảnh để người xem biết đây vẫn là cùng một câu chuyện:
   - Lâm Tịch: áo rách bẩn, dáng gầy yếu, tay nứt nẻ;
   - Tần Dã: áo chiến thuật đen, bị thương;
   - bãi rác Khu 17: trời đỏ, tủ lạnh rỉ, xe tải lật, tường bê tông sập;
   - đạo cụ: thịt hộp, còi, kẹo, tinh thạch.

4. Không nên prompt kiểu "cinematic wasteland".
   Câu này chỉ tạo wallpaper. Phải prompt kiểu:
   "MUST SHOW: Lâm Tịch, gầm xe, móng vuốt chó hai hàm cào ngoài xe, Tần Dã bị thương nằm cạnh nàng."

5. Hình trước và hình sau phải có handoff.
   Ví dụ:
   - Scene A: Lâm Tịch thấy chó hai hàm xé xác cạnh xe tải lật.
   - Scene B: nàng bò tới xác.
   - Scene C: xác người đàn ông nắm cổ tay nàng.
   - Scene D: chó quay lại, nàng kéo hắn xuống gầm xe.
   Nếu mỗi scene tự sinh riêng, AI dễ đổi địa điểm hoặc đổi nhân vật.

6. Shot type cần phục vụ truyện.
   - Mở cảnh: wide establishing shot.
   - Hành động: medium action shot.
   - Đạo cụ quan trọng: close survival-detail shot.
   - Trốn/chạy/sợ: low claustrophobic POV.

7. Voice cũng cần continuity giống hình.
   Giọng kể xuyên suốt là một người kể ổn định, không phải mỗi câu đổi cảm xúc quá mạnh. Cảm xúc chỉ nên đổi nhẹ theo cảnh.

### Tao Đã Sửa Vào Pipeline

- Thêm `visual_must_show`: vật/nhân vật/hành động bắt buộc có trong ảnh.
- Thêm `visual_continuity`: nhớ scene trước có gì.
- Thêm `visual_shot_type`: góc máy phù hợp với hành động.
- Thêm `audit_visual_alignment.py`: kiểm storyboard có thiếu action, shot type, continuity không.
- Thêm `visual_bible.example.json`: mẫu hồ sơ hình ảnh cho nhân vật, bối cảnh, đạo cụ.
- Thêm `visual_director_notes.md`: quy tắc hình ảnh bám truyện.

### Thay Đổi Quan Trọng Cho Phần 2

Trước khi gen full phần 2, tao sẽ không chạy thẳng 90 ảnh nữa.

Quy trình mới:

1. Tạo storyboard.
2. Tạo visual bible cho phần 2.
3. Audit storyboard.
4. Gen thử 3-5 ảnh đại diện.
5. Mày xem contact sheet có `MUST SHOW`.
6. Nếu khớp mới chạy full.

### Việc Tao Còn Muốn Học/Sửa Tiếp

- Học thêm cách các kênh truyện thật giữ hình nhân vật nhất quán.
- Thêm script tự tạo `visual_bible.json` từ chương truyện.
- Thêm chấm điểm ảnh: `khớp narration`, `đúng nhân vật`, `đúng đạo cụ`, `đúng hành động`.
- Sau này nếu có model image-to-image/reference, dùng ảnh trước làm reference cho ảnh sau.

---

## 2026-05-22 02:46 UTC - Overnight Learning Checkpoint

### Tao Đã Search/Học Từ Đâu

- Microsoft Speech SSML voice and prosody documentation
  URL: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-voice
  Ghi chú: Official reference for rate, pitch, pauses, and speech synthesis markup.
- Voices: audiobook narration and finding a narrator voice
  URL: https://www.voices.com/blog/audiobook-narrators-find-voice/
  Ghi chú: Practical narration guidance about choosing and sustaining a story voice.
- StudioBinder storyboard and visual storytelling guides
  URL: https://www.studiobinder.com/blog/what-is-a-storyboard/
  Ghi chú: Storyboard basics for planning shots, action, and visual continuity.
- Wikipedia: continuity editing
  URL: https://en.wikipedia.org/wiki/Continuity_editing
  Ghi chú: Explains continuity between shots so viewers understand space, time, and action.
- Search query prepared for next cloud run
  URL: https://duckduckgo.com/?q=Vietnamese+audiobook+narration+emotional+pacing+YouTube
  Ghi chú: Fallback query URL because the current run could not parse live search results.
- Search query prepared for next cloud run
  URL: https://duckduckgo.com/?q=truyen+audio+ke+chuyen+dem+khuya+giong+doc+truyen+cam
  Ghi chú: Fallback query URL because the current run could not parse live search results.
- Search query prepared for next cloud run
  URL: https://duckduckgo.com/?q=AI+narrated+story+video+visual+continuity+storyboard
  Ghi chú: Fallback query URL because the current run could not parse live search results.
- Search query prepared for next cloud run
  URL: https://duckduckgo.com/?q=cinematic+storyboarding+continuity+character+action+progression
  Ghi chú: Fallback query URL because the current run could not parse live search results.

### Tao Học Được Gì Về Voice

- Giữ một giọng kể nền ổn định trong cả tập; cảm xúc chỉ nên dao động nhẹ theo cảnh.
- Đừng đọc nhanh để chạy chữ. Với truyện dài, sự dễ nghe quan trọng hơn tốc độ.
- Thoại nhân vật cần khác lời dẫn, nhưng khác bằng nhịp/pause/độ chắc, không giả giọng quá lố.
- Cần character bible để giữ tính cách giọng nhân vật qua nhiều chương.

### Tao Học Được Gì Về Hình/Storyboard

- Ảnh phải bám hành động trong audio trước, sau đó mới tối ưu cinematic.
- Mỗi scene cần continuity anchors: nhân vật, địa điểm, đạo cụ, trạng thái vết thương/quần áo.
- Storyboard phải có handoff rõ: scene sau tiếp nối hành động của scene trước.
- Cần shot type theo beat: establishing, medium action, close prop, hiding POV.

### Ảnh Hưởng Tới Pipeline Của Mình

- Trước khi gen full phần 2, tạo storyboard + visual bible + audit rồi mới gen sample.
- Contact sheet cần hiển thị MUST SHOW để so ảnh với narration nhanh.
- Voice-plan và visual-plan nên được giữ lại để review từng scene thay vì sửa mò.

### Việc Nên Làm Tiếp

- Với phần 2, tạo `visual_bible.json` và `character_voice_bible.json` riêng trước khi gen full.
- Audit storyboard trước, sau đó gen 3-5 ảnh mẫu để xem có khớp narration không.
- Sau khi mày nghe audio phần 2, ghi feedback theo nhân vật/trait để generator học tiếp.

---

## 2026-05-25 01:41 UTC - Overnight Learning Checkpoint

### Tao Đã Search/Học Từ Đâu

- Microsoft Speech SSML voice and prosody documentation
  URL: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-voice
  Ghi chú: Official reference for rate, pitch, pauses, and speech synthesis markup.
- Voices: audiobook narration and finding a narrator voice
  URL: https://www.voices.com/blog/audiobook-narrators-find-voice/
  Ghi chú: Practical narration guidance about choosing and sustaining a story voice.
- StudioBinder storyboard and visual storytelling guides
  URL: https://www.studiobinder.com/blog/what-is-a-storyboard/
  Ghi chú: Storyboard basics for planning shots, action, and visual continuity.
- Wikipedia: continuity editing
  URL: https://en.wikipedia.org/wiki/Continuity_editing
  Ghi chú: Explains continuity between shots so viewers understand space, time, and action.
- Search query prepared for next cloud run
  URL: https://duckduckgo.com/?q=Vietnamese+audiobook+narration+emotional+pacing+YouTube
  Ghi chú: Fallback query URL because the current run could not parse live search results.
- Search query prepared for next cloud run
  URL: https://duckduckgo.com/?q=truyen+audio+ke+chuyen+dem+khuya+giong+doc+truyen+cam
  Ghi chú: Fallback query URL because the current run could not parse live search results.
- Search query prepared for next cloud run
  URL: https://duckduckgo.com/?q=AI+narrated+story+video+visual+continuity+storyboard
  Ghi chú: Fallback query URL because the current run could not parse live search results.
- Search query prepared for next cloud run
  URL: https://duckduckgo.com/?q=cinematic+storyboarding+continuity+character+action+progression
  Ghi chú: Fallback query URL because the current run could not parse live search results.

### Tao Học Được Gì Về Voice

- Giữ một giọng kể nền ổn định trong cả tập; cảm xúc chỉ nên dao động nhẹ theo cảnh.
- Đừng đọc nhanh để chạy chữ. Với truyện dài, sự dễ nghe quan trọng hơn tốc độ.
- Thoại nhân vật cần khác lời dẫn, nhưng khác bằng nhịp/pause/độ chắc, không giả giọng quá lố.
- Cần character bible để giữ tính cách giọng nhân vật qua nhiều chương.

### Tao Học Được Gì Về Hình/Storyboard

- Ảnh phải bám hành động trong audio trước, sau đó mới tối ưu cinematic.
- Mỗi scene cần continuity anchors: nhân vật, địa điểm, đạo cụ, trạng thái vết thương/quần áo.
- Storyboard phải có handoff rõ: scene sau tiếp nối hành động của scene trước.
- Cần shot type theo beat: establishing, medium action, close prop, hiding POV.

### Ảnh Hưởng Tới Pipeline Của Mình

- Trước khi gen full phần 2, tạo storyboard + visual bible + audit rồi mới gen sample.
- Contact sheet cần hiển thị MUST SHOW để so ảnh với narration nhanh.
- Voice-plan và visual-plan nên được giữ lại để review từng scene thay vì sửa mò.

### Việc Nên Làm Tiếp

- Với phần 2, tạo `visual_bible.json` và `character_voice_bible.json` riêng trước khi gen full.
- Audit storyboard trước, sau đó gen 3-5 ảnh mẫu để xem có khớp narration không.
- Sau khi mày nghe audio phần 2, ghi feedback theo nhân vật/trait để generator học tiếp.
