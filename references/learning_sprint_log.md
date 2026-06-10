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

---

## 2026-05-25 02:07 UTC - Overnight Learning Checkpoint

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

## 2026-05-25 02:20 UTC - Overnight Learning Checkpoint

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

## 2026-05-25 03:14 UTC - Auto Learning Checkpoint

### Tao Đã Search/Học Từ Đâu

- Search query prepared for next cloud run
  URL: https://duckduckgo.com/?q=YouTube+truy%E1%BB%87n+m%E1%BA%A1t+th%E1%BA%BF+viral+gi%E1%BB%8Dng+%C4%91%E1%BB%8Dc+truy%E1%BB%81n+c%E1%BA%A3m
  Ghi chú: Fallback query URL because the current run could not parse live search results.
- Search query prepared for next cloud run
  URL: https://duckduckgo.com/?q=YouTube+truy%E1%BB%87n+ph%E1%BA%BF+th%E1%BB%95+audio+viral+h%C3%ACnh+%E1%BA%A3nh+AI
  Ghi chú: Fallback query URL because the current run could not parse live search results.
- Search query prepared for next cloud run
  URL: https://duckduckgo.com/?q=truy%E1%BB%87n+audio+Vi%E1%BB%87t+Nam+gi%E1%BB%8Dng+%C4%91%E1%BB%8Dc+nh%C3%A2n+v%E1%BA%ADt+kh%C3%A1c+nhau
  Ghi chú: Fallback query URL because the current run could not parse live search results.
- Search query prepared for next cloud run
  URL: https://duckduckgo.com/?q=audiobook+narration+character+voices+consistency+pacing+emotion
  Ghi chú: Fallback query URL because the current run could not parse live search results.

### Tao Học Được Gì Về Voice

- Giọng kể chuyện phải ổn định, rõ chữ, có cảm xúc nền nhưng không kéo pause quá dài. Người nghe truyện dài cần cảm giác trôi, không bị ngắt vụn.
- Mỗi nhân vật cần một lane giọng riêng khác narrator: tốc độ, pitch, độ lạnh/ấm, độ căng, kiểu ngắt câu. Lane đó phải giữ nhất quán từ đầu đến cuối.
- Nhân vật không nên chỉ khác bằng giả giọng. Khác biệt nên đến từ tính cách: kẻ lạnh nói ít và chắc; người thật thà mềm hơn; phản diện nén giọng thấp; kẻ nịnh nọt có nhịp nhanh và mềm.
- Voice plan cần ghi lý do vì sao scene dùng nhịp đó: narration, nội tâm, nguy hiểm gần, đối thoại, reveal, hoặc cao trào.

### Tao Học Được Gì Về Hình/Storyboard

- Ảnh phải bám câu đang đọc trước, đẹp sau. Nếu audio nói nhân vật đang bò dưới gầm xe thì hình phải có gầm xe, tư thế bò, mối nguy gần đó.
- Vibe viral không chỉ là màu cinematic. Nó là khung hình dễ hiểu trong 1 giây: nhân vật rõ, nguy hiểm rõ, đạo cụ rõ, không gian đúng truyện.
- Nhân vật phải có visual bible: tuổi, vóc dáng, tóc, quần áo, vết thương, đạo cụ đang cầm, trạng thái cảm xúc. Prompt sau không được tự đổi nhân vật.
- Cảnh sau phải kế thừa cảnh trước: cùng bối cảnh, cùng hướng hành động, cùng đạo cụ, cùng mức thương tích. Tránh slideshow mỗi ảnh một thế giới.
- Chuyển động nên hợp logic truyện: mưa/gió/bụi/khói/ánh đèn/cây/camera push nhẹ; nhân vật có hành động nhỏ đúng scene, không đứng tạo dáng vô nghĩa.

### Ảnh Hưởng Tới Pipeline Của Mình

- Auto learning chỉ ghi log và action items. Không render, không gen thử, không overwrite part 1 assets.
- Mỗi checkpoint phải ưu tiên link mới, không lặp lại YouTube/web URL đã học ở các lần trước.
- Tạo `character_voice_bible.json` cho mỗi truyện: narrator + từng nhân vật + trait + pitch/rate/pause mục tiêu.
- Tạo `visual_bible.json` và `scene_state.json` để giữ nhân vật, bối cảnh, đạo cụ và trạng thái xuyên suốt.
- Thêm audit storyboard trước khi gen: mỗi scene phải có `must_show`, `current_action`, `location_anchor`, `previous_state`, `next_handoff`.

### Action Items Nên Cân Nhắc

- Đổi voice generator sang character-lane: narrator riêng, từng nhân vật riêng, giữ consistency bằng `character_voice_bible.json`.
- Giảm pause quá dài trong voice style mặc định, ưu tiên nhịp kể tự nhiên và chỉ pause mạnh ở reveal/cao trào.
- Dùng log hiện có để chặn trùng URL giữa các checkpoint; nếu đã học link rồi thì bỏ qua.
- Thêm `learning_action_items.md` để gom việc nên code sau này, tách khỏi log học dài.
- Thêm scoring cho storyboard: khớp audio, đúng nhân vật, đúng đạo cụ, đúng không gian, continuity với scene trước.

---

## 2026-05-25 12:00 Asia/Bangkok - Auto Learning Checkpoint 05

### Nguồn đã kiểm tra

- M Studio - AI Character Consistency in Storyboards 2026
  URL: https://mstudio.ai/blog/storyboarding/ai-character-consistency-storyboards
  Ghi chú: Character consistency nghĩa là frame 1 và frame 40 vẫn là cùng một người: cùng mặt, dáng, trang phục và visual identity.
- AI Magicx - Long-form AI video with character consistency
  URL: https://www.aimagicx.com/blog/long-form-ai-video-character-consistency-guide-2026
  Ghi chú: Long-form cần character reference sheets, batch generation, consistency review, editing và color grading; sound design phải được đầu tư tương xứng với hình.
- Seedance - Character Consistency Guide 2026
  URL: https://www.seedance.tv/blog/seedance-character-consistency-guide-2026
  Ghi chú: Image-to-video/reference workflow mạnh hơn text-to-video khi cần giữ cùng nhân vật qua nhiều cảnh.
- Genra - AI Video Character Consistency Guide
  URL: https://genra.ai/blog/ai-video-character-consistency-guide
  Ghi chú: Storyboard mode/multi-shot planning phù hợp hơn cho long-form character series.
- CANVAS - Continuity-Aware Narratives via Visual Agentic Storyboarding
  URL: https://arxiv.org/abs/2604.13452
  Ghi chú: Cần character continuity, persistent background anchors, location-aware planning.
- Lights, Camera, Consistency - Multistage Pipeline for Character-Stable AI Video Stories
  URL: https://arxiv.org/abs/2512.16954
  Ghi chú: Visual anchoring rất quan trọng; bỏ anchoring làm character consistency rớt mạnh.
- StoryBlender - Inter-Shot Consistent and Editable 3D Storyboard
  URL: https://arxiv.org/abs/2604.03315
  Ghi chú: Tách global assets khỏi shot-specific variables bằng continuity memory graph.
- YouTube retention / storytelling pacing notes
  Ghi chú: Video truyện dài không cần cắt nhanh kiểu shorts, nhưng 10 giây đầu phải rõ câu hỏi/hook và nhịp đọc không được ì.

### Tao học được gì về voice

- Lỗi thực tế vừa gặp: voice `wasteland-dark` đang đọc chậm và pause quá lâu. Cảm xúc nặng không đồng nghĩa với kéo giãn mọi câu.
- Voice viral cho truyện dài cần `flow`: câu phải trôi, pause chỉ dùng ở điểm có ý nghĩa. Nếu pause nhiều, người nghe cảm giác máy đọc hoặc câu chuyện bị tụt lực.
- Nên tách hai tham số: `emotion_weight` và `pause_weight`. Có thể giọng vẫn lạnh/nặng nhưng pause thấp hơn.
- Narrator nên có tốc độ nền gần tự nhiên hơn; chỉ hạ tốc ở nội tâm, nguy hiểm gần, hoặc reveal.
- Nhân vật cần voice lane riêng, nhưng lane không nên làm tổng audio chậm thêm. Thoại nhân vật khác narrator bằng tone/rhythm, không phải bằng pause dài.
- Trước khi render full video, cần có bước `voice audit`: tính tổng duration, words per minute, average pause, scene quá dài bất thường.

### Tao học được gì về hình/storyboard

- Long-form nên ưu tiên reference/anchor trước motion. Nếu nhân vật và bối cảnh chưa khóa được, tăng motion chỉ làm lỗi rõ hơn.
- Storyboard nên giữ `global assets`: nhân vật, bối cảnh, đạo cụ, mood màu. Mỗi shot chỉ đổi biến cục bộ: góc máy, hành động, khoảng cách camera, ánh sáng.
- Với mode hybrid manual ChatGPT, prompt tổng phải cho ChatGPT đọc toàn bộ scene manual trước, lập character/setting sheet, rồi mới tạo từng ảnh.
- Prompt từng scene cần có filename bắt buộc, must-show, current action, continuity from previous scene. Như vậy mày copy sang ChatGPT app sẽ ít bị lạc nhân vật hơn.
- ComfyUI local nên nhận các scene đơn giản/nền/chuyển tiếp; ChatGPT manual nên nhận key scene khó: nhiều cảm xúc, nhiều nhân vật, cảnh mở, cảnh reveal, cảnh hành động khó.

### Ảnh hưởng tới pipeline/code

- Cần sửa voice preset `wasteland-dark`: tăng rate, giảm comma/sentence/paragraph pause, giữ tone lạnh bằng pitch/style thay vì kéo dài im lặng.
- Thêm `voice_quality_report.json`: tổng số từ, tổng duration, WPM, scene longest, pause profile, cảnh nào quá chậm.
- Thêm `--voice-speed-profile`: `natural`, `dramatic`, `fast-retention`, để chọn nhịp đọc theo mục tiêu.
- Với hybrid manual, thêm prompt tổng ở đầu `chatgpt_image_prompts.md` để ChatGPT hiểu toàn bộ character/setting consistency trước khi làm từng scene.
- Pipeline nên cho phép `--prepare-only` hoặc `--hybrid-prompts-only` để tạo prompt ChatGPT mà không tự chạy ComfyUI/voice nếu người dùng chỉ muốn chuẩn bị ảnh manual.
- Không render tiếp khi voice audit fail hoặc khi người dùng đã nói voice không ổn.

### Action items nên cân nhắc

- Sửa ngay `wasteland-dark` cho nhanh hơn và ít pause hơn trước khi render lại chương 2.
- Thêm `validate_voice_timing.py` để bắt cảnh đọc quá chậm.
- Thêm prompt tổng cho `chatgpt_image_prompts.md`.
- Thêm `hybrid-prompts-only` mode để chỉ tạo storyboard + prompt manual, chưa chạy asset nặng.
- Thêm phân loại scene cho hybrid: `manual_priority_score` thay vì chia 50% đơn giản.

---

## 2026-05-25 14:05 Asia/Bangkok - Auto Learning Checkpoint 06

### Nguồn đã kiểm tra

- M Studio - AI Character Consistency in Storyboards 2026
  URL: https://mstudio.ai/blog/storyboarding/ai-character-consistency-storyboards
  Ghi chú: Nhấn mạnh storyboard dài phải giữ cùng khuôn mặt, trang phục, dáng người và visual identity qua nhiều frame.
- Genra - AI Video Character Consistency Guide
  URL: https://genra.ai/blog/ai-video-character-consistency-guide
  Ghi chú: Multi-shot/storyboard mode và reference workflow giúp giảm lỗi nhân vật đổi mặt giữa các cảnh.
- Vertical Motion - How to Keep AI Characters Consistent Across Scenes 2026
  URL: https://motion.verticalstudio.ai/blog/ai-character-consistency-guide
  Ghi chú: Frame chaining/keyframe stitching dùng frame trước làm neo cho frame sau để giữ continuity.
- AI Magicx - AI Multi-Shot Video Character Consistency 2026
  URL: https://www.aimagicx.com/blog/ai-multi-shot-video-character-consistency-2026
  Ghi chú: Nếu không có multi-shot planning, người xem dễ bị rối vì đứt không gian, đứt đạo cụ, đứt nhân vật.
- CANVAS: Continuity-Aware Narratives via Visual Agentic Storyboarding
  URL: https://arxiv.org/abs/2604.13452
  Ghi chú: Cần character continuity, persistent background anchors và location-aware planning; nghiên cứu báo cải thiện continuity đạo cụ/nhân vật/bối cảnh.
- StoryBlender: Inter-Shot Consistent and Editable 3D Storyboard
  URL: https://arxiv.org/abs/2604.03315
  Ghi chú: Ý tưởng đáng học là tách global assets khỏi biến cục bộ từng shot bằng continuity memory graph.
- CineAGI: Character-Consistent Movie Creation
  URL: https://arxiv.org/abs/2604.23579
  Ghi chú: Multi-scene video cần cinematic blueprint, character-centric tracking và audio-visual synchronization.

### Tao học được gì về voice

- Voice không được chỉ là preset tốc độ. Cần có voice director layer: narrator lane ổn định, character lane riêng, scene mood riêng.
- Nhịp đọc truyện dài nên nhanh hơn bản cũ: câu thường trôi tự nhiên, pause ngắn; chỉ giữ pause rõ ở scene break, cliffhanger, reveal quan trọng.
- Giọng nhân vật phải được suy ra từ người nói, không phải chỉ thấy tên ai trong câu là đổi giọng. Ví dụ Lâm Tịch gọi "Tần Dã" thì người nói vẫn là Lâm Tịch.
- Đối thoại nên khác narration bằng voice/rhythm/pitch nhẹ, không diễn quá lố. Tần Dã cần ít hơi, trầm và chắc; Lâm Tịch yếu nhưng lì, không được đọc nhõng nhẽo.
- Cần voice audit trước khi render: duration, WPM, đoạn quá chậm, pause trung bình, số lần đổi voice trong một scene.

### Tao học được gì về hình/storyboard

- Ảnh chưa khớp truyện vì pipeline vẫn nghĩ theo từng ảnh độc lập. Cần global visual bible + scene state trước khi gen bất kỳ ảnh nào.
- Mỗi scene phải có: location_anchor, character_state, prop_state, current_action, previous_handoff, next_handoff. Không có mấy thứ này thì model dễ tạo ảnh đẹp nhưng sai truyện.
- Với truyện phế thổ, vibe tốt không phải chỉ xám/tối. Frame phải đọc được trong 1 giây: ai đang làm gì, đang ở đâu, đạo cụ sống còn là gì, nguy hiểm ở đâu.
- Character consistency nên khóa bằng reference sheet hoặc ít nhất prompt canonical rất ngắn và lặp lại: mặt, tóc, tuổi, áo, vết thương, đạo cụ. Không nên nhồi quá nhiều mô tả mới mỗi scene.
- ComfyUI SD1.5 local nên giao các cảnh đơn giản/nền/đạo cụ; cảnh nhiều nhân vật hoặc cần đúng mặt nên đưa vào hybrid ChatGPT/manual hoặc dùng reference workflow.

### Ảnh hưởng tới pipeline/code

- Bắt buộc tạo `character_voice_bible.json` và `visual_bible.json` trước khi render phần 2 trở đi.
- Thêm `scene_state.json` hoặc nhúng state vào storyboard: nhân vật đang bị thương thế nào, đang cầm gì, đang ở góc lều nào, đạo cụ còn lại bao nhiêu.
- Thêm bước `voice_quality_report.json` sau gen voice sample/full: WPM, duration từng scene, pause profile, voice lane đã dùng.
- Thêm bước visual audit trước image generation: nếu scene thiếu must_show hoặc action quá chung chung thì fail sớm, chưa gen ảnh.
- Với mode hybrid, cần prompt tổng cho ChatGPT tạo/giữ character sheet trước, rồi mới tạo từng ảnh. Key scene khó ưu tiên manual, không chia 50/50 ngẫu nhiên.
- Không render video full nếu sample image chưa đạt đúng nội dung hoặc voice audit báo quá chậm.

### Action items nên cân nhắc

- Sửa speaker detection: thoại lấy người nói từ câu dẫn trước dấu hai chấm, không chỉ dựa vào tên xuất hiện trong lời thoại.
- Tạo `build_visual_bible.py` hoặc stage trong `run_story_pipeline.py` để sinh visual bible từ chương/truyện.
- Tạo `validate_voice_timing.py` để đo WPM/pause và cảnh báo trước render.
- Tạo `audit_storyboard_alignment.py` chấm điểm scene theo đúng nhân vật, đạo cụ, bối cảnh, hành động, handoff.
- Tạo `hybrid_key_scene_selector` để chọn cảnh khó cho ChatGPT/manual: nhiều nhân vật, đối thoại cảm xúc, vết thương, đạo cụ quan trọng, hành động cần khớp.

---

## 2026-05-25 14:36 Asia/Bangkok - Auto Learning Checkpoint 07

### Nguồn đã kiểm tra

- Vois - Dialogue That Breathes: Pacing Techniques for AI Audiobooks
  URL: https://vois.so/blog/audiobook-dialogue-pacing
  Ghi chú: Dialogue cần nhịp thở tự nhiên, nhưng pause nên có chủ đích giữa lượt thoại, không chèn nghỉ máy móc sau từng mệnh đề.
- Narration Box - Scene Breaks in AI Audiobooks
  URL: https://narrationbox.com/blog/scene-break-section-pause-conventions-ai-audiobooks
  Ghi chú: Scene break cần tín hiệu bằng pause/tone, còn trong cùng cảnh thì quá nhiều pause làm mất dòng kể.
- CinemaDrop - Scene Continuity Image Generator
  URL: https://www.cinemadrop.com/scene-continuity-image-generator
  Ghi chú: Story-first storyboard phải giữ nhân vật, địa điểm, đạo cụ chung một visual DNA.
- CinemaDrop - Consistent Prop Generator
  URL: https://www.cinemadrop.com/consistent-prop-generator
  Ghi chú: Hero props như dao gãy, nắp hộp nước, than lọc độc cần được giữ nhận diện qua nhiều shot.
- M Studio - Character Consistency Feature
  URL: https://mstudio.ai/features/consistent-characters
  Ghi chú: Character profiles nên hoạt động như lớp khóa identity độc lập với model tạo ảnh.
- Story2Board - Visual Continuity / CANVAS lessons
  URL: https://story2board.com/blog/ai-storyboard-visual-continuity-canvas
  Ghi chú: Cần appearance states: cùng nhân vật nhưng trạng thái áo, thương tích, đạo cụ thay đổi theo thời điểm truyện.
- AxiomStory - AI Video Continuity
  URL: https://axiomstory.com/blog/ai-video-continuity
  Ghi chú: Mỗi shot phải kế thừa visual canon, current story state và production logic của shot trước/sau.

### Tao học được gì về voice

- Lỗi vừa gặp trong sample rất quan trọng: không nên chèn silence nhân tạo giữa mọi unit. TTS đã có ngắt câu tự nhiên; nếu thêm silence nữa sẽ thành cảm giác từng câu bị cắt rời.
- Pause chỉ nên dùng ở scene break, chuyển POV, reveal lớn, hoặc giữa lượt thoại nhân vật. Trong cùng một câu thoại dài của một nhân vật, không được tự đổi speaker giữa chừng.
- Speaker detection phải hiểu cấu trúc: câu dẫn trước dấu hai chấm xác định người nói; nội dung trong ngoặc kép phải giữ speaker đó cho tới khi đóng ngoặc.
- Không được suy speaker chỉ vì tên xuất hiện trong lời thoại. Ví dụ Lâm Tịch gọi "Tần Dã" thì người nói vẫn là Lâm Tịch.
- Voice plan cần log `active_dialogue_speaker`, `pause_inserted`, và cảnh báo nếu một quoted dialogue đổi voice giữa chừng.

### Tao học được gì về hình/storyboard

- Key props cần memory riêng giống nhân vật. Trong truyện phế thổ, đạo cụ nhỏ như nắp hộp nước, dao gãy, than lọc độc chính là "cốt truyện hình ảnh".
- Visual continuity phải có appearance states: Lâm Tịch trước/sau bị thương, Tần Dã sốt cao/không đứng được, lượng nước còn hai ngụm, vết thương đang thấm máu.
- Prompt ảnh không nên chỉ nói cinematic; phải có current action rõ: ai làm gì với đạo cụ nào, ở góc nào của lều, trạng thái từ scene trước là gì.
- Cảnh nhiều nhân vật trong ComfyUI local dễ sai giới tính/mặt. Các key scene có đối thoại cảm xúc hoặc hai nhân vật nên ưu tiên hybrid/manual/reference workflow.

### Ảnh hưởng tới pipeline/code

- `wasteland-dark` nên mặc định không chèn silence giữa units (`max_inserted_pause = 0`) hoặc chỉ chèn ở scene break.
- Cần thêm validator cho voice: nếu trong cùng quoted dialogue có hơn một voice thì fail trước khi render.
- `voice-plan.json` nên ghi rõ speaker được suy ra từ đâu: narrator, character alias, dialogue context, fallback.
- Storyboard nên lưu `prop_state` và `character_appearance_state` để ảnh sau không tự reset đồ vật/trạng thái nhân vật.
- Hybrid selector nên ưu tiên manual cho scene có: hai nhân vật, close interaction, đạo cụ sống còn, thương tích, hoặc continuity dài.

### Action items nên cân nhắc

- Thêm `validate_voice_consistency.py`: kiểm tra pause quá dài, đổi voice giữa ngoặc kép, và WPM bất thường.
- Sửa voice generator để chỉ thêm artificial silence ở scene break, không thêm sau mỗi sentence/clause.
- Thêm `active_dialogue_speaker` vào voice plan cho debug dễ đọc.
- Tạo `prop_bible.json` cho nắp hộp nước, dao gãy, than lọc độc, lon rỉ, thịt hộp.
- Thêm visual audit rule: mỗi scene phải có ít nhất một action + một prop/location cụ thể nếu narration có mô tả.
