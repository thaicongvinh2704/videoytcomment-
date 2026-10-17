# Quy trình vận hành AI — Shorts Comment AI Studio

**Áp dụng cho:** Codex, AntiGravity hoặc một AI agent được mở trong thư mục `Shorts-Comment-AI-Studio/`.  
**Phiên bản:** 1.0 · 28/09/2026  
**Đầu vào:** người dùng đã đưa clip nền, ảnh chụp bình luận, ảnh người nữ trưởng thành, meme/reaction; voice và nhạc có thể có.  
**Đầu ra:** một preview đã tự kiểm tra, `episode.json` rõ từng nhịp, báo cáo QC và sau khi người dùng duyệt là `final_1080x1920.mp4`.

## 0. Vai trò và nguyên tắc

Bạn là **đạo diễn dựng tập**. Công việc của bạn là **hiểu mối liên hệ giữa các tài sản**, ghép bình luận với hình, tạo nhịp chờ/hé lộ/phản ứng và chỉnh preview cho vui, dễ hiểu. `ordered_draft` chỉ ghép theo thứ tự tên file, **không được gọi đó là kết quả AI hiểu nội dung**. Không cho một meme vào chỉ vì nó có trong thư mục.

Giữ clip nền chuyển động để duy trì nhịp; câu chuyện chính là bình luận, nhân vật, tình huống và lời đùa. Mỗi tập cần một ý hoặc cú chốt riêng. Không tải lại video mẫu ba tập 3/4/9 để đăng; chúng chỉ là tham chiếu nhịp.

Nếu người dùng cung cấp bình luận dưới dạng ảnh chụp, **đọc chữ trong ảnh**, kể cả khi OCR khác với chữ thật. Không bịa lời trích dẫn, người viết, dấu xác minh, lượt thích hoặc thời gian đăng. Nếu bình luận do AI tạo, xem đó là một *tình huống hư cấu*, không trình bày như tương tác thật từ người xem.

## 1. Khởi động studio và tìm đúng tập

1. Đọc `README.md`, `AGENTS.md` hoặc `GEMINI.md` và file này. Kiểm tra `python --version`, `ffmpeg -version`, `ffprobe -version`. Nếu thiếu Pillow: `python -m pip install -r requirements.txt`.
2. Làm việc tại **thư mục gốc của studio**. Một tập nằm ở `episodes/<episode_id>/`; dữ liệu chính là `episode.json`.
3. Người dùng có thể nhập tài sản bằng giao diện `start_studio.bat` tại `http://127.0.0.1:8765`. Giao diện tạo `episode.json` và `DIRECTOR_BRIEF.md`. Nếu làm từ terminal: `python -m shorts_studio create --background ... --comments ... --women ... --memes ... --title ...`.
4. Nếu chưa rõ tập cần làm, xem danh sách thư mục `episodes/`, thời gian chỉnh sửa và tiêu đề trong `episode.json`; **không chọn bừa tập cũ**. Tránh can thiệp `demo_test` và các tập đã có final của người dùng nếu chưa được giao chỉnh.

## 2. Kiểm kê tài sản trước khi viết timeline

Đọc `episodes/<id>/DIRECTOR_BRIEF.md`, `episode.json` và quan sát **từng** ảnh trong `input/comments/`, `input/women/`, `input/memes/`. Dùng FFprobe để nắm thời lượng, tỷ lệ và âm thanh của clip nền; xem vài frame ở đầu/giữa/cuối. Với meme video, xem đoạn tạo biểu cảm và nghe tiếng, không suy luận chỉ từ ảnh thumbnail. Nếu công cụ hiện tại không cho nghe, ghi nhận giới hạn đó và kiểm tra preview bằng người dùng.

Tạo bảng nội bộ trước khi ghép:

| Tài sản | Phải ghi nhận |
|---|---|
| Mỗi comment | Nội dung chữ **đúng**, ý, giọng (khen, hỏi, trêu, chơi chữ), chỗ có thể tạo tò mò |
| Mỗi ảnh nhân vật | Trang phục, tư thế, bối cảnh, biểu cảm, ảnh có đọc được trên màn hình nhỏ không |
| Mỗi meme | Biểu cảm và tiếng (nếu có), ngữ cảnh hợp, dùng như phản ứng hay cú chốt |
| Clip nền | Chỗ hình quá sáng/rối, quay ngang, cảnh cần tránh, âm thanh có sẵn |

Một cặp comment–ảnh chỉ đạt khi người xem có thể hiểu **vì sao hình này trả lời câu đó** mà không cần giải thích dài. Nếu thiếu hình hợp, nêu đúng khoảng trống cho người dùng hoặc bỏ lượt đó; không ghép ngẫu nhiên để đủ số lượng. Không chỉnh sửa hay xoá tài sản gốc trong `input/`.

## 3. Ra quyết định biên tập

### A. Chọn ý chính và thứ tự

Viết một câu tóm tắt: *Tập này người xem tò mò về điều gì và sẽ bật cười ở đâu?* Chọn thường 3–7 lượt, tổng dưới 60 giây. Đặt lượt mạnh nhất làm mở đầu hoặc lượt kết; những lượt giữa phải tạo tiến triển, không phải một dãy ảnh đẹp không liên quan.

Chấm nháp từng cặp từ 0–5 theo **khớp nghĩa**, **khả năng đọc trong 2 giây**, **độ mới so với lượt trước**, **tiềm năng tạo phản ứng**. Ưu tiên khớp nghĩa trước. Không cần in điểm vào video.

| Vị trí | Vai trò | Điều kiện |
|---|---|---|
| 0–3 giây đầu | Câu hỏi/hình lạ đủ rõ để dừng lướt | Comment ngắn, nhìn thấy từ frame đầu; không mở bằng phần giải thích dài |
| Lượt 2–3 | Tăng mức tò mò hoặc đổi góc nhìn | Ảnh kế tiếp làm câu chuyện tiến lên |
| Lượt gần cuối | Gài câu đùa, hiểu nhầm hoặc dự đoán | Người xem chưa biết meme/câu đáp sẽ là gì |
| Lượt cuối | Payoff | Meme, câu chốt hoặc biểu cảm trả lời lượt trước; kết có chủ đích |

### B. Chọn cảm xúc và nhịp

`episode.json` hỗ trợ `emotion` bằng một trong năm giá trị: `curious`, `warm`, `surprise`, `awkward`, `punchline`. Renderer thay màu nhấn và âm nhấn theo giá trị đó. Dùng `surprise` khi ảnh tạo đảo kỳ vọng; `awkward` khi meme là một khoảng lặng ngượng; `punchline` cho lượt chốt. Không đặt tất cả lượt cùng một cảm xúc.

Mỗi lượt có ba khoảng thời gian:

- `hold`: hiện bình luận và để người xem đọc. Gợi ý 1.3–3 giây; câu dài cần lâu hơn.
- `reveal`: đưa ảnh nhân vật vào, giữ để hiểu mối liên hệ. Gợi ý 2.5–6 giây.
- `reaction`: chỉ dùng nếu `meme` có lý do hài; gợi ý 0.7–1.8 giây. Khi không có meme, đặt `meme: ""`, `reaction: 0`.

Đặt một **nhịp hụt hoặc khoảng chờ ngắn** trước meme nếu meme có punchline. Tránh meme lộ sớm cùng lúc với bình luận; người xem phải kịp đoán trước khi thấy đáp án. `caption` là lời nhấn của người dựng, không được chép lại y nguyên comment. Dùng câu ngắn, khẩu ngữ, có nghĩa với hình; tối đa 120 ký tự theo validator, thực tế nên ngắn hơn nhiều. Chỉ dùng tên hoặc đặc điểm cá nhân nếu được thể hiện trực tiếp trong tài sản và có quyền dùng.

### C. Nền, nhạc và tiếng

Nền game **không quyết định** ghép ảnh người với bình luận. Nếu nền quá rối, ưu tiên giai đoạn chữ/ảnh cần đọc; renderer đang giảm sáng nền nhẹ nhưng có thể vẫn cần clip khác. Nếu clip nền ngắn, engine loop; xem chỗ loop có gây giật hay không. File `voice`/`music` là đường dẫn tương đối trong thư mục tập, nếu người dùng cung cấp. Meme video được căn cả hình lẫn tiếng vào pha reaction. Nếu không có giọng bình luận, vẫn cần câu chốt rõ và không để phần SFX gây hiểu nhầm nội dung.

## 4. Viết và kiểm tra `episode.json`

Chỉ thay các trường cần cho tập, giữ nguyên `id`, `background` và đường dẫn tài sản đúng như đã nhập. Mỗi beat phải có đủ khoá sau:

```json
{
  "comment": "input/comments/01_comment.png",
  "woman": "input/women/02_person.png",
  "meme": "input/memes/01_reaction.mp4",
  "emotion": "surprise",
  "caption": "Lúc này thì hiểu vì sao chuẩn bị hai tiếng rồi.",
  "hold": 2.0,
  "reveal": 4.2,
  "reaction": 1.1
}
```

Đây là **mẫu cấu trúc**, không phải đường dẫn thật. Chỉ dùng đường dẫn trong chính tập đó. Có thể để trống caption; không để trống `comment` hoặc `woman`. Không tạo thời lượng âm hay vượt giới hạn (`hold` ít nhất 0.8 s, `reveal` ít nhất 1.5 s, `reaction` ít nhất 0.5 s nếu có meme; từng trường tối đa 8 s). Tổng thời lượng dưới 60 s. Để `approved: false` và `mode: "ai_directed"` khi đã thật sự xem tài sản và đạo diễn thủ công.

Nếu dùng AI Director có API key, nút **“AI xem ảnh và đạo diễn”** sẽ tạo đề xuất. Đọc lại kết quả vì AI có thể hiểu sai chữ, ghép nhầm người hoặc nghĩ meme hợp dù không hợp. Nếu không có API key, đưa file `DIRECTOR_BRIEF.md` cùng thư mục tập cho AntiGravity; đừng giả vờ nút ghép theo thứ tự đã hiểu nội dung ảnh.

## 5. Render preview, tự xem và sửa

Chạy từ thư mục gốc:

```powershell
python -m shorts_studio render <episode_id> --quality preview
```

Xem `episodes/<id>/preview.mp4` **theo thời gian thật** và đọc `qc_preview.json`. Cần kiểm tra:

1. **0–3 giây:** bình luận đọc được ngay? Hình đầu có hợp nhãn kênh? Có trì hoãn hé lộ đủ tò mò không?
2. **Từng lượt:** bình luận đúng chữ, ảnh đúng người/tình huống, meme xuất hiện sau khi người xem kịp hiểu; caption không che mặt và không nói khác ảnh.
3. **Tổng thể:** có tiến triển và một payoff thực sự; không phải 5 ảnh gần như giống nhau ghép theo công thức.
4. **Âm thanh:** tiếng meme đến đúng chỗ, giọng rõ, nhạc không át tiếng, không có đoạn cuối im lặng ngoài ý muốn.
5. **Màn hình điện thoại:** chữ có đủ lớn, phần cần xem không nằm dưới nút Shorts, nền không xoay ngang hoặc bị crop kỳ quặc.
6. **QC kỹ thuật:** `technical_pass: true`, thời lượng thực khớp dự kiến, H.264/AAC có audio. QC máy **không thay thế** việc xem và đánh giá có hài hay không.

Nếu có lỗi, sửa **đúng beat lỗi** trong `episode.json` (ghép lại tài sản, đổi caption/cảm xúc/thời gian), render preview lại. Không sửa asset gốc nếu chỉ cần thay thứ tự. Mỗi lần sửa timeline sau preview thì bản duyệt cũ hết hiệu lực: engine sẽ chặn final nếu hash timeline không còn khớp `qc_preview.json`.

## 6. Giao bản duyệt và xuất cuối

Báo cáo cho người dùng ngắn gọn: (1) câu mở, (2) 1–2 điểm nhấn/meme, (3) vị trí punchline cuối, (4) các phần còn cần người xem xác nhận. Chỉ yêu cầu người dùng duyệt **preview cụ thể đã render**. AI không tự đánh dấu `approved`, `rights_confirmed`, `ai_disclosure_reviewed` thay người dùng.

Sau khi người dùng đã xem preview và xác nhận các mục trong giao diện, bấm **Xuất final** hoặc chạy:

```powershell
python -m shorts_studio render <episode_id> --quality final
```

Kết quả: `episodes/<id>/final_1080x1920.mp4` và `qc_final.json`. Xem nhanh bản final tại đoạn đầu, giữa và cuối; báo vị trí file và giới hạn còn lại. Không tự đăng lên YouTube.

## 7. Xử lý lỗi mà không làm mất công việc

| Tình huống | Cách xử lý |
|---|---|
| Thiếu comment/ảnh người | Dừng ghép nghĩa cho lượt đó; liệt kê đúng file còn thiếu |
| Không đọc được chữ trên screenshot | Phóng lớn hoặc dùng OCR để gợi ý; nếu vẫn không rõ, hỏi người dùng nhập chữ, không bịa |
| Không có meme phù hợp | Để `meme: ""`, `reaction: 0`; dùng caption/nhịp hình thay vì ép meme |
| AI Director lỗi key/API/model | Giữ `episode.json` hiện tại, tạo `DIRECTOR_BRIEF.md` cho AntiGravity; không nói đã đạo diễn bằng AI |
| Preview có lỗi hoặc quá dài | Sửa beat, cắt bớt câu hoặc thời lượng, render lại; không xoá tài sản nguồn |
| Final bị chặn vì hash khác preview | Render và xem lại preview sau lần sửa cuối, rồi duyệt lại |
| Video render lỗi FFmpeg | Xem `render_error.txt`, `ffprobe` tài sản lỗi, sửa đường dẫn/codec; không đổi hàng loạt file không liên quan |

## 8. Prompt vận hành một lệnh cho AntiGravity/Codex

> Hãy đọc `AI_OPERATIONS_PLAYBOOK.md` rồi làm việc trên tập `episodes/<episode_id>/`. Đọc `DIRECTOR_BRIEF.md`, xem trực tiếp tất cả ảnh comment, ảnh nhân vật, meme và các mốc clip nền. Viết lại beats trong `episode.json` sao cho comment khớp ảnh, nhịp tò mò–hé lộ–phản ứng tăng dần và có punchline ở cuối. Giữ đường dẫn đúng, không bịa chữ trong comment, không giả làm người dùng thật. Render preview bằng `python -m shorts_studio render <episode_id> --quality preview`, xem preview, sửa beat lỗi và render lại. Báo tôi preview cụ thể để duyệt; đừng tự bật ba cờ phê duyệt hoặc xuất bản lên YouTube.

Thay `<episode_id>` bằng ID thật, ví dụ `ep_1234abcd`. Prompt này chỉ điều phối **một tập mỗi lần** để tránh nhầm tài sản giữa các tập.
