from __future__ import annotations

import base64
import io
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

from .core import assets, load_doc, run, safe_asset, save_doc

EMOTIONS = ["curious", "warm", "surprise", "awkward", "punchline"]


def ordered_draft(ep: Path) -> dict:
    doc = load_doc(ep)
    comments, women, memes = (assets(ep, x) for x in ("comments", "women", "memes"))
    if not comments or not women:
        raise ValueError("Chưa có ảnh bình luận hoặc nhân vật")
    count = min(len(comments), 8)
    result = []
    for i, comment in enumerate(comments[:count]):
        meme = ""
        if memes and (i == count - 1 or (len(memes) > 1 and i == count // 2)):
            meme = memes[0 if i != count - 1 else min(len(memes) - 1, 1)]
        result.append({"comment": comment, "woman": women[i % len(women)], "meme": meme,
                       "emotion": "punchline" if i == count - 1 else ("surprise" if meme else "curious"),
                       "caption": "", "hold": 1.8 if i else 2.1, "reveal": 4.4,
                       "reaction": 1.3 if meme else 0})
    doc.update(beats=result, mode="draft_ordered", approved=False,
               note="Bản nháp chỉ ghép theo tên file. Chạy AI Director hoặc sửa trong Studio để khớp nghĩa và tạo điểm hài.")
    save_doc(ep, doc)
    write_brief(ep)
    return doc


def _jpeg_data(path: Path, max_size: tuple[int, int] = (700, 950)) -> str:
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail(max_size)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=79)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _video_frame(video: Path, out: Path) -> Path:
    run(["ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", str(video),
         "-frames:v", "1", "-vf", "scale=480:-2", str(out)])
    return out


def _ocr(path: Path) -> str:
    from shutil import which
    if not which("tesseract"):
        return ""
    p = subprocess.run(["tesseract", str(path), "stdout", "-l", "vie+eng"],
                       text=True, encoding="utf-8", errors="replace", capture_output=True)
    if p.returncode:  # Some Windows installs have only eng.
        p = subprocess.run(["tesseract", str(path), "stdout", "-l", "eng"],
                           text=True, encoding="utf-8", errors="replace", capture_output=True)
    return p.stdout.strip()[:450]


def write_brief(ep: Path) -> Path:
    doc = load_doc(ep)
    comments, women, memes = (assets(ep, x) for x in ("comments", "women", "memes"))
    lines = ["# NHIỆM VỤ ĐẠO DIỄN TẬP SHORT", "", f"Tập: {doc['id']} — {doc['title']}",
             "", "Hãy xem THẬT các asset trong các thư mục dưới, đọc chữ bình luận và hiểu meme.",
             "Ghép ảnh người với bình luận theo nghĩa; chọn meme để tạo bất ngờ hay đối đáp hài.",
             "Chỉnh beats trong episode.json, không đổi đường dẫn asset; sau đó chạy preview và xem lại.",
             "Không gán sự kiện/đời tư có thật cho người trong ảnh. Nếu không đọc được comment, báo để nhập text.",
             "", "## Ảnh bình luận"]
    lines += [f"- {p}  | OCR tham khảo: {_ocr(safe_asset(ep, p)) or '(chưa có)'}" for p in comments]
    lines += ["", "## Ảnh nhân vật"] + [f"- {p}" for p in women]
    lines += ["", "## Meme / reaction"] + [f"- {p}" for p in memes]
    lines += ["", "## Nhịp", "Mỗi beat: hold 1–3 s để đọc, reveal 2–6 s, reaction 0.6–2 s nếu có meme.",
              "Caption ngắn, giàu cảm xúc; câu chốt khác biệt ở cuối. Chỉ tạo FINAL sau preview và QC."]
    p = ep / "DIRECTOR_BRIEF.md"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _schema() -> dict:
    beat = {"type": "object", "additionalProperties": False,
            "properties": {"comment": {"type": "string"}, "woman": {"type": "string"},
                           "meme": {"type": "string"}, "emotion": {"type": "string", "enum": EMOTIONS},
                           "caption": {"type": "string"}, "hold": {"type": "number"},
                           "reveal": {"type": "number"}, "reaction": {"type": "number"}},
            "required": ["comment", "woman", "meme", "emotion", "caption", "hold", "reveal", "reaction"]}
    return {"type": "object", "additionalProperties": False,
            "properties": {"beats": {"type": "array", "items": beat}, "director_note": {"type": "string"}},
            "required": ["beats", "director_note"]}


def ai_direct(ep: Path, model: str | None = None) -> dict:
    """Calls the official Responses API with the user's asset thumbnails, never a video URL."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Chưa có OPENAI_API_KEY. Bản nháp theo thứ tự vẫn dùng được; xem README mục AI Director.")
    model = model or os.getenv("STUDIO_AI_MODEL", "gpt-4.1")
    doc = load_doc(ep)
    comments, women, memes = (assets(ep, x) for x in ("comments", "women", "memes"))
    if not comments or not women:
        raise ValueError("Cần ảnh bình luận và nhân vật trước khi dùng AI Director")
    if len(comments) > 10 or len(women) > 12 or len(memes) > 8:
        raise ValueError("AI Director hiện nhận tối đa 10 comment, 12 ảnh nhân vật, 8 meme/tập")
    content: list[dict] = [{"type": "input_text", "text":
        "Hãy đạo diễn một Short hài tiếng Việt 30–60 giây. XEM ẢNH và ĐỌC CHỮ trong từng ảnh bình luận. "
        "Ghép ảnh nhân vật với bình luận có nghĩa phù hợp, dùng meme đúng lúc để tạo phản ứng hài. "
        "Sắp 3–7 lượt theo thứ tự tăng tò mò → đảo kỳ vọng → punchline cuối. "
        "Chỉ sử dụng đúng path được cung cấp, không bịa chữ có trong screenshot. "
        "Caption <= 80 ký tự; tự viết lời đùa tình huống, không phán đoán đời tư người trong ảnh. "
        "Mỗi comment dùng tối đa một lần. Ảnh nhân vật có thể lặp nếu hợp lý. Meme có thể không dùng nếu không khớp. "
        "Thời lượng: hold 1.3–3.2, reveal 2.5–6, reaction 0.6–2 nếu dùng meme, bằng 0 nếu không. "
        f"Tên tập: {doc['title']}. Trả về JSON schema, không thêm giải thích."}]
    for category, paths in (("COMMENT", comments), ("WOMAN", women), ("MEME", memes)):
        for p in paths:
            media = safe_asset(ep, p)
            if media.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm", ".gif"}:
                media = _video_frame(media, ep / f"_ai_thumb_{len(content)}.jpg")
            ocr = _ocr(media) if category == "COMMENT" else ""
            content.append({"type": "input_text", "text": f"{category} PATH = {p}" + (f"; OCR tham khảo: {ocr}" if ocr else "")})
            content.append({"type": "input_image", "image_url": _jpeg_data(media), "detail": "high" if category == "COMMENT" else "low"})
    bg = _video_frame(safe_asset(ep, doc["background"]), ep / "_ai_background.jpg")
    content += [{"type": "input_text", "text": "BACKGROUND (chỉ để nhận diện nhịp hình; không buộc ảnh nhân vật khớp cảnh game)"},
                {"type": "input_image", "image_url": _jpeg_data(bg), "detail": "low"}]
    body = {"model": model, "store": False,
            "input": [{"role": "user", "content": content}],
            "text": {"format": {"type": "json_schema", "name": "shorts_edit_plan", "strict": True,
                                "schema": _schema()}}}
    req = urllib.request.Request("https://api.openai.com/v1/responses", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            response = json.load(r)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"AI API HTTP {exc.code}: {exc.read(1500).decode(errors='replace')}") from exc
    if response.get("status") not in ("completed", None):
        raise RuntimeError("AI chưa hoàn tất: " + str(response.get("status")))
    texts = [c.get("text", "") for item in response.get("output", []) if item.get("type") == "message"
             for c in item.get("content", []) if c.get("type") == "output_text"]
    if not texts:
        raise RuntimeError("AI không trả về bản dựng")
    plan = json.loads("".join(texts))
    proposal = dict(doc, beats=plan["beats"], mode="ai_directed", approved=False,
                    note=plan["director_note"][:500])
    from .core import validate_doc
    validate_doc(ep, proposal)
    save_doc(ep, proposal)
    write_brief(ep)
    return proposal
