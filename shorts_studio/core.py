from __future__ import annotations

import json
import re
import shutil
import subprocess
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EPISODES = ROOT / "episodes"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm"}
MEME_EXT = IMAGE_EXT | VIDEO_EXT | {".gif"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}
EMOTIONS = {"curious", "warm", "surprise", "awkward", "punchline"}


def run(args: list[str], *, cwd: Path | None = None) -> str:
    p = subprocess.run(args, cwd=cwd, text=True, encoding="utf-8", errors="replace",
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(f"Command failed: {args[0]}\n{p.stderr[-2500:]}")
    return p.stdout


def check_deps() -> None:
    for binary in ("ffmpeg", "ffprobe"):
        if not shutil.which(binary):
            raise RuntimeError(f"Thiếu {binary}. Cài FFmpeg rồi thêm thư mục bin vào PATH.")
    try:
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("Thiếu Pillow. Chạy: python -m pip install -r requirements.txt") from exc


def probe(path: Path) -> dict:
    raw = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)])
    data = json.loads(raw)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if not video:
        raise ValueError(f"Không thấy video trong {path.name}")
    return {"width": int(video["width"]), "height": int(video["height"]),
            "duration": float(data.get("format", {}).get("duration") or video.get("duration") or 0),
            "has_audio": any(s.get("codec_type") == "audio" for s in data.get("streams", []))}


def episode_dir(episode_id: str) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,60}", episode_id):
        raise ValueError("Mã tập không hợp lệ")
    return EPISODES / episode_id


def safe_asset(ep: Path, relative: str) -> Path:
    if not relative or not isinstance(relative, str):
        raise ValueError("Thiếu đường dẫn asset")
    p = (ep / relative).resolve()
    if not p.is_relative_to(ep.resolve()) or not p.is_file():
        raise ValueError(f"Asset không tồn tại hoặc nằm ngoài tập: {relative}")
    return p


def assets(ep: Path, category: str) -> list[str]:
    allowed = {"comments": IMAGE_EXT, "women": IMAGE_EXT, "memes": MEME_EXT}.get(category)
    if allowed is None:
        raise ValueError(f"Danh mục lạ: {category}")
    folder = ep / "input" / category
    return [f"input/{category}/{p.name}" for p in sorted(folder.iterdir(), key=lambda q: q.name.lower())
            if p.is_file() and p.suffix.lower() in allowed] if folder.exists() else []


def new_episode(background: Path, comments: list[Path], women: list[Path], memes: list[Path],
                title: str = "Tập mới", episode_id: str | None = None,
                voice: Path | None = None, music: Path | None = None) -> dict:
    check_deps()
    episode_id = episode_id or "ep_" + uuid.uuid4().hex[:8]
    ep = episode_dir(episode_id)
    if ep.exists():
        raise ValueError("Tập đã tồn tại")
    if not background.is_file() or background.suffix.lower() not in VIDEO_EXT:
        raise ValueError("Clip nền phải là video mp4/mkv/mov/webm")
    if not comments or not women:
        raise ValueError("Cần ít nhất 1 ảnh bình luận và 1 ảnh nhân vật")
    if any(x.suffix.lower() not in IMAGE_EXT for x in comments + women):
        raise ValueError("Bình luận và nhân vật phải là PNG/JPG/WebP/BMP")
    if any(x.suffix.lower() not in MEME_EXT for x in memes):
        raise ValueError("Meme cần là ảnh, GIF hoặc video")
    ep.mkdir(parents=True)
    (ep / "input").mkdir()
    shutil.copy2(background, ep / "input" / ("background" + background.suffix.lower()))
    for category, paths in (("comments", comments), ("women", women), ("memes", memes)):
        folder = ep / "input" / category
        folder.mkdir()
        for i, src in enumerate(paths, 1):
            shutil.copy2(src, folder / f"{i:02d}_{re.sub(r'[^a-zA-Z0-9_.-]', '_', src.stem)[:45]}{src.suffix.lower()}")
    extra_audio = {}
    for field, source in (("voice", voice), ("music", music)):
        if source:
            if source.suffix.lower() not in AUDIO_EXT or not source.is_file():
                raise ValueError(f"{field} cần là MP3/WAV/M4A/OGG/FLAC/AAC")
            target = ep / "input" / f"{field}{source.suffix.lower()}"
            shutil.copy2(source, target)
            extra_audio[field] = f"input/{target.name}"
    bg = next((ep / "input").glob("background.*"))
    info = probe(bg)
    if info["duration"] < 1:
        raise ValueError("Clip nền quá ngắn")
    doc = {"version": 1, "id": episode_id, "title": title[:100], "background": f"input/{bg.name}",
           "background_info": info, "mode": "draft_ordered", "approved": False,
           "rights_confirmed": False, "ai_disclosure_reviewed": False,
           "beats": [], "music": extra_audio.get("music", ""), "voice": extra_audio.get("voice", ""),
           "note": "AI chưa được cấu hình: thứ tự ghép là bản nháp."}
    save_doc(ep, doc)
    return doc


def validate_doc(ep: Path, doc: dict) -> dict:
    if doc.get("id") != ep.name:
        raise ValueError("Mã tập không khớp")
    safe_asset(ep, doc.get("background", ""))
    beats = doc.get("beats")
    if not isinstance(beats, list) or not 1 <= len(beats) <= 12:
        raise ValueError("Cần 1–12 lượt nội dung")
    if len(doc.get("title", "")) > 100:
        raise ValueError("Tiêu đề quá dài")
    total = sum(b.get("hold", 0) + b.get("reveal", 0) +
                (b.get("reaction", 0) if b.get("meme") else 0) for b in beats if isinstance(b, dict))
    if total > 59.5:
        raise ValueError(f"Tập {total:.1f} giây; hãy rút còn dưới 60 giây")
    for i, b in enumerate(beats):
        if not isinstance(b, dict) or b.get("emotion") not in EMOTIONS:
            raise ValueError(f"Cảm xúc không hợp lệ ở lượt {i+1}")
        for field, cat in (("comment", "comments"), ("woman", "women")):
            if b.get(field) not in assets(ep, cat):
                raise ValueError(f"Ảnh {field} không nằm trong thư mục {cat} ở lượt {i+1}")
        if b.get("meme") and b["meme"] not in assets(ep, "memes"):
            raise ValueError(f"Meme không hợp lệ ở lượt {i+1}")
        for field in ("hold", "reveal", "reaction"):
            value = b.get(field, 0)
            if not isinstance(value, (float, int)) or not 0 <= value <= 8:
                raise ValueError(f"Thời lượng {field} không hợp lệ ở lượt {i+1}")
        if b["hold"] < 0.8 or b["reveal"] < 1.5 or (b.get("meme") and b["reaction"] < 0.5):
            raise ValueError(f"Nhịp đọc hoặc hé lộ quá ngắn ở lượt {i+1}")
        if len(b.get("caption", "")) > 120:
            raise ValueError(f"Caption quá dài ở lượt {i+1}")
    for key in ("voice", "music"):
        if doc.get(key):
            safe_asset(ep, doc[key])
    return doc


def save_doc(ep: Path, doc: dict) -> None:
    ep.mkdir(parents=True, exist_ok=True)
    if doc.get("beats"):
        validate_doc(ep, doc)
    tmp = ep / "episode.json.tmp"
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(ep / "episode.json")


def load_doc(ep: Path) -> dict:
    return json.loads((ep / "episode.json").read_text(encoding="utf-8"))
