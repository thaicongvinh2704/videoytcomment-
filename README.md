# Shorts Comment AI Studio v1

Studio local trên Windows để ghép clip nền + ảnh bình luận + ảnh nhân vật + meme thành YouTube Short dọc, có bản nháp, AI Director, preview, chỉnh từng lượt và xuất final. Toàn bộ tài sản nằm trong `episodes/` trên máy của bạn.

**Cho AI vận hành studio:** mở `AI_OPERATIONS_PLAYBOOK.md`; file này có quy trình đọc asset, ghép nghĩa, dựng nhịp hài, render, QC và một prompt một lệnh cho AntiGravity/Codex.

## Cài và chạy

1. Cài **Python 3.10–3.12** và **FFmpeg/FFprobe**, thêm hai chương trình vào PATH. Kiểm tra: `python --version`, `ffmpeg -version`.
2. Giải nén toàn bộ thư mục. Nhấp đúp `start_studio.bat`. Cửa sổ dòng lệnh phải mở khi sử dụng.
3. Trình duyệt mở `http://127.0.0.1:8765`. Chọn clip nền; chọn nhiều ảnh bình luận, ảnh nhân vật và meme. Có thể thêm file voice và nhạc nền. Ảnh bình luận phải là screenshot rõ chữ.
4. Bản nháp mặc định ghép theo thứ tự tên file. Xem/sửa thứ tự, cặp ghép, thời lượng, caption và cảm xúc. Nhấn `Render preview`.
5. Xem hết preview, rà quyền sử dụng nguồn, khai báo AI và duyệt. Sau đó xuất final 1080×1920. File ở `episodes/<id>/final_1080x1920.mp4`.

Lệnh thử máy không cần tài sản: `python -m shorts_studio demo`. Kết quả là ảnh demo dạng thẻ chữ, không chứa video mẫu hay hình người thật. Nếu `demo_test` đã tồn tại, xoá thư mục `episodes/demo_test` rồi chạy lại.

## Cho AI thực sự xem ảnh và đạo diễn

Studio **không tự suy ra nội dung ảnh khi thiếu AI**. Chế độ ghép mặc định chỉ là bản nháp có thứ tự; caption tự để trống để tránh bịa nghĩa. Có hai cách dùng AI:

**OpenAI API:** tạo API key riêng (ChatGPT Plus không thay thế API key), đặt biến môi trường `OPENAI_API_KEY` trên Windows rồi mở lại `start_studio.bat`. Chọn tập > `AI xem ảnh và đạo diễn`. Model mặc định `gpt-4.1`; có thể đặt `STUDIO_AI_MODEL` thành model hỗ trợ ảnh và JSON Schema trong tài khoản của bạn. Mỗi lần dùng AI sẽ gửi thumbnail tài sản của tập (ảnh bình luận, ảnh nhân vật, meme, một khung hình nền) tới API và có phí theo tài khoản API. AI chọn thứ tự, cặp ghép, nhịp đọc/hé lộ/meme, caption và cảm xúc; **bạn duyệt và chỉnh** trước khi render. Khóa chỉ đọc từ biến môi trường, không lưu trong tập.

**AntiGravity:** mở `episodes/<id>/DIRECTOR_BRIEF.md` trong dự án và đưa prompt đó cho AntiGravity. Anti xem ảnh trong các thư mục, chỉnh `episode.json`, sau đó bạn mở lại tập/preview. Tệp brief có thể ghi OCR tham khảo khi Tesseract được cài nhưng AI cần tự đọc ảnh.

Nếu muốn dùng CLI thay cho trình duyệt:

```powershell
python -m shorts_studio create --background "C:\\clips\\game.mp4" --comments "C:\\comments\\1.png" "C:\\comments\\2.png" --women "C:\\women\\1.png" "C:\\women\\2.png" --memes "C:\\memes\\laugh.mp4" --title "Tập 01"
python -m shorts_studio ai ep_XXXXXXXX
python -m shorts_studio render ep_XXXXXXXX --quality preview
```

## Cấu trúc và giới hạn hiện tại

`episode.json` là timeline có thể sửa; một lượt gồm `comment`, `woman`, `meme`, `emotion`, `caption`, `hold`, `reveal`, `reaction`. Một tập có 1–12 lượt. Studio cắt và loop nền, canh clip/ảnh tương ứng với từng pha, tự làm âm nhấn nhẹ ở hé lộ và meme; tiếng clip nền được mix ở mức thấp cả trong preview để bạn nghe trước. Xác nhận quyền nguồn là điều kiện xuất final. Voice/nhạc có thể chọn khi tạo tập hoặc điền đường dẫn tương đối vào `voice`/`music` trong `episode.json`. Meme video có hình chuyển động và tiếng của nó được căn vào đoạn reaction.

Preview là 540×960 để duyệt nhanh; final là 1080×1920, H.264/AAC, 30 fps. Render final cần có preview và ba xác nhận trên giao diện. QC kỹ thuật ở `qc_preview.json`/`qc_final.json`; việc ảnh có hài, đúng người, đúng ý bình luận phải do người xem kiểm tra. Studio chỉ phục vụ trên `127.0.0.1` của máy, không xuất bản YouTube.

**Phạm vi kiểm thử:** lệnh demo kiểm tra toàn tuyến upload/timeline/render; AI API chưa thể kiểm thử khi thiếu API key và asset thật của bạn. Với asset thật, render thử 1 tập để tinh chỉnh điểm nhấn, font chữ, nhạc và mức cảm xúc.

YouTube yêu cầu nội dung tạo bằng AI trông như thực được khai báo khi thuộc trường hợp cần công bố; nội dung lặp hàng loạt có thể không đủ điều kiện kiếm tiền. Mỗi tập nên có tình huống và góc hài thật sự mới. Xem: https://support.google.com/youtube/answer/14328491 và https://support.google.com/youtube/answer/1311392.
