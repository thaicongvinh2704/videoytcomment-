from __future__ import annotations

import json
import math
import wave
import struct
import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from .core import check_deps, load_doc, probe, run, safe_asset, validate_doc


def _plan_hash(doc: dict) -> str:
    relevant = {k: doc.get(k) for k in ("beats", "background", "music", "voice")}
    return hashlib.sha256(json.dumps(relevant, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _font(size: int) -> ImageFont.FreeTypeFont:
    for p in ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/seguisb.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _wrap(text: str, font, width: int, draw) -> list[str]:
    result: list[str] = []
    line = ""
    for word in text.split():
        proposal = (line + " " + word).strip()
        if line and draw.textbbox((0, 0), proposal, font=font)[2] > width:
            result.append(line)
            line = word
        else:
            line = proposal
    if line:
        result.append(line)
    return result


def _fit_image(path: Path, width: int, height: int, *, cover: bool) -> Image.Image:
    if path.suffix.lower() in {".mp4", ".mkv", ".mov", ".webm"}:
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as temp:
            target = Path(temp) / "frame.png"
            run(["ffmpeg", "-v", "error", "-y", "-ss", "0.3", "-i", str(path),
                 "-frames:v", "1", str(target)])
            with Image.open(target) as im:
                raw = ImageOps.exif_transpose(im).convert("RGB")
    else:
        with Image.open(path) as im:
            raw = ImageOps.exif_transpose(im)
            if raw.mode == "RGBA":
                bg = Image.new("RGBA", raw.size, (255, 255, 255, 255))
                bg.alpha_composite(raw)
                raw = bg.convert("RGB")
            else:
                raw = raw.convert("RGB")
    if cover:
        return ImageOps.fit(raw, (width, height), method=Image.Resampling.LANCZOS, centering=(.5, .34))
    return ImageOps.contain(raw, (width, height), Image.Resampling.LANCZOS)


def _rounded_photo(canvas: Image.Image, photo: Image.Image, box: tuple[int, int, int, int], radius: int):
    x, y, w, h = box
    mask = Image.new("L", (w, h))
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius=radius, fill=255)
    shadow = Image.new("RGBA", canvas.size)
    ImageDraw.Draw(shadow).rounded_rectangle((x+4, y+8, x+w+4, y+h+8), radius=radius,
                                              fill=(0, 0, 0, 110))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(16)))
    full = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    full.paste(photo.resize((w, h)), (0, 0), mask)
    canvas.alpha_composite(full, (x, y))


def _canvas(ep: Path, beat: dict, phase: str, size: tuple[int, int], index: int, count: int) -> Image.Image:
    w, h = size
    s = w / 1080
    v = lambda a: int(a*s)
    im = Image.new("RGBA", size)

    # 1. Thẻ bình luận: Căn giữa, né mép trên (Y ~ 180px)
    cw = v(940)
    x = (w - cw) // 2
    y = v(180)
    comment = _fit_image(safe_asset(ep, beat["comment"]), cw, v(300), cover=False)
    ch = comment.height
    _rounded_photo(im, comment, (x, y, cw, ch), v(24))

    # 2. Ảnh nhân vật ở pha Reveal và Meme
    if phase != "comment":
        pw = v(940)
        px = (w - pw) // 2
        py = y + ch + v(32)
        ph = min(v(1120), h - py - v(120))
        person = _fit_image(safe_asset(ep, beat["woman"]), pw, ph, cover=True)
        _rounded_photo(im, person, (px, py, pw, ph), v(28))

        # 3. Nếu meme là ảnh tĩnh (nếu meme là video thì _segment sẽ overlay)
        if phase == "meme" and beat.get("meme"):
            meme_path = safe_asset(ep, beat["meme"])
            if meme_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}:
                mw, mh = v(400), v(400)
                mx = w - mw - v(70)
                my = py + ph - mh - v(40)
                meme = _fit_image(meme_path, mw, mh, cover=True)
                _rounded_photo(im, meme, (mx, my, mw, mh), v(24))

    return im


def _tones(path: Path, seconds: float, cues: list[tuple[float, str]]) -> None:
    rate = 44100
    n_samples = int(seconds * rate)
    left = [0.0] * n_samples
    right = [0.0] * n_samples

    sfx_dir = Path(__file__).resolve().parent.parent / "resources" / "sfx"
    sfx_map = {
        "comment": sfx_dir / "pop_comment.wav",
        "reveal": sfx_dir / "ding_reveal.wav",
        "meme": sfx_dir / "vine_boom.wav",
        "curious": sfx_dir / "pop_comment.wav",
        "warm": sfx_dir / "ding_reveal.wav",
        "surprise": sfx_dir / "ding_reveal.wav",
        "awkward": sfx_dir / "vine_boom.wav",
        "punchline": sfx_dir / "vine_boom.wav",
    }

    has_real_sfx = False
    for start, kind in cues:
        target_f = sfx_map.get(kind)
        if not target_f or not target_f.exists():
            if (sfx_dir / kind).exists():
                target_f = sfx_dir / kind
            elif (sfx_dir / f"{kind}.wav").exists():
                target_f = sfx_dir / f"{kind}.wav"
            elif Path(kind).exists():
                target_f = Path(kind)
        if target_f and target_f.exists():
            has_real_sfx = True
            try:
                with wave.open(str(target_f), "rb") as w:
                    w_ch = w.getnchannels()
                    w_frames = w.getnframes()
                    raw = struct.unpack(f"<{w_frames * w_ch}h", w.readframes(w_frames))
                    start_idx = int(start * rate)
                    vol = 0.95 if (str(kind).startswith("meme") or kind in ("meme", "punchline", "awkward")) else 0.75
                    for i in range(w_frames):
                        idx = start_idx + i
                        if idx >= n_samples:
                            break
                        sl = raw[i * w_ch] / 32768.0 * vol
                        sr = raw[i * w_ch + (1 if w_ch > 1 else 0)] / 32768.0 * vol
                        left[idx] += sl
                        right[idx] += sr
            except Exception:
                pass

    if not has_real_sfx:
        for start, kind in cues:
            freq = {"curious": 600, "warm": 490, "surprise": 850, "awkward": 260,
                    "punchline": 370, "meme": 300}.get(kind, 680)
            length = 0.24 if kind in {"punchline", "meme", "awkward"} else 0.14
            for j in range(int(length * rate)):
                pos = int(start * rate) + j
                if pos >= n_samples: break
                env = math.sin(math.pi * j / max(1, int(length * rate))) ** 2
                val = 0.35 * env * math.sin(2 * math.pi * (freq + 180 * j / (length * rate)) * j / rate)
                left[pos] += val
                right[pos] += val

    with wave.open(str(path), "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(rate)
        frames = []
        for l, r in zip(left, right):
            il = max(-32768, min(32767, int(l * 32767)))
            ir = max(-32768, min(32767, int(r * 32767)))
            frames.append(struct.pack("<hh", il, ir))
        f.writeframes(b"".join(frames))


def _segment(ep: Path, bg: Path, overlay: Path, dest: Path, size: tuple[int, int],
             begin: float, length: float, quality: str, meme_path: Path | None = None) -> None:
    w, h = size
    dur = probe(bg)["duration"]
    offset = begin % dur if dur > .1 else 0
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-stream_loop", "-1",
           "-ss", f"{offset:.3f}", "-i", str(bg), "-loop", "1", "-framerate", "30", "-i", str(overlay)]
    filter_src = (f"[0:v]fps=30,scale={w}:{h}:force_original_aspect_ratio=increase,"
                  f"crop={w}:{h},setsar=1,eq=brightness=-0.055:saturation=0.90[bg];"
                  f"[1:v]format=rgba,fade=t=in:st=0:d=0.14:alpha=1[ov];"
                  f"[bg][ov]overlay=0:0:shortest=1:format=auto[base]")
    if meme_path and meme_path.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}:
        cmd += ["-stream_loop", "-1", "-i", str(meme_path)]
        mx, my, mw, mh = int(600*w/1080), int(1000*h/1920), int(370*w/1080), int(370*h/1920)
        filter_src += (f";[2:v]fps=30,scale={mw}:{mh}:force_original_aspect_ratio=increase,"
                       f"crop={mw}:{mh},format=rgba,fade=t=in:st=0:d=0.1:alpha=1[m];"
                       f"[base][m]overlay={mx}:{my}:shortest=1:format=auto,format=yuv420p[out]")
    else:
        filter_src += ";[base]format=yuv420p[out]"
    cmd += ["-filter_complex", filter_src, "-map", "[out]", "-an", "-t", f"{length:.3f}",
            "-r", "30", "-c:v", "libx264", "-preset", "ultrafast" if quality == "preview" else "veryfast",
            "-crf", "27" if quality == "preview" else "21", "-pix_fmt", "yuv420p",
            "-video_track_timescale", "30000", str(dest)]
    run(cmd)


def _mux_audio(ep: Path, doc: dict, video: Path, audio: Path, dest: Path, duration: float,
               meme_audio: list[tuple[Path, float, float]]):
    inputs = ["-i", str(video), "-i", str(audio)]
    filters = ["[1:a]volume=0.85[sfx]"]
    tracks = ["[sfx]"]
    bg = safe_asset(ep, doc["background"])
    ambient = doc.get("music")
    if ambient:
        ambient = safe_asset(ep, ambient)
    elif doc.get("background_info", {}).get("has_audio"):
        ambient = bg
    if ambient:
        idx = inputs.count("-i")
        inputs += ["-stream_loop", "-1", "-i", str(ambient)]
        amb_vol = 0.22 if doc.get("voice") else 0.35
        filters.append(f"[{idx}:a]atrim=duration={duration:.3f},asetpts=PTS-STARTPTS,volume={amb_vol}[amb]")
        tracks.append("[amb]")
    if doc.get("voice"):
        idx = inputs.count("-i")
        inputs += ["-i", str(safe_asset(ep, doc["voice"]))]
        filters.append(f"[{idx}:a]atrim=duration={duration:.3f},asetpts=PTS-STARTPTS,volume=1.35[voice]")
        tracks.append("[voice]")
    for path, start, length in meme_audio:
        if not probe(path)["has_audio"]:
            continue
        idx = inputs.count("-i")
        inputs += ["-i", str(path)]
        ms = round(start*1000)
        tag = f"react{idx}"
        filters.append(f"[{idx}:a]atrim=duration={length:.3f},asetpts=PTS-STARTPTS,"
                       f"volume=0.85,adelay={ms}:all=1[{tag}]")
        tracks.append(f"[{tag}]")
    filters.append("".join(tracks) + f"amix=inputs={len(tracks)}:duration=first:dropout_transition=0:normalize=0,aresample=async=1[mix]")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
           "-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[mix]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-t", f"{duration:.3f}",
           "-movflags", "+faststart", str(dest)]
    run(cmd)


def render(ep: Path, quality: str = "preview", progress=None) -> dict:
    check_deps()
    doc = validate_doc(ep, load_doc(ep))
    if quality not in {"preview", "final"}:
        raise ValueError("quality cần là preview hoặc final")
    if quality == "final" and not (doc.get("approved") and doc.get("rights_confirmed") and doc.get("ai_disclosure_reviewed")):
        raise ValueError("Trước khi xuất final: duyệt preview, xác nhận quyền clip/nhạc/ảnh và rà soát khai báo AI")
    if quality == "final":
        review_path = ep / "qc_preview.json"
        review = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else {}
        if review.get("plan_hash") != _plan_hash(doc):
            raise ValueError("Nội dung đã thay đổi sau preview; render và xem lại preview trước khi xuất final")
    size = (540, 960) if quality == "preview" else (1080, 1920)
    work = ep / "render_cache" / quality
    work.mkdir(parents=True, exist_ok=True)
    bg = safe_asset(ep, doc["background"])
    segments: list[Path] = []
    cues: list[tuple[float, str]] = []
    meme_audio: list[tuple[Path, float, float]] = []
    cursor = 0.
    for i, b in enumerate(doc["beats"]):
        phases = [("comment", b["hold"]), ("reveal", b["reveal"])]
        if b.get("meme") and b.get("reaction", 0):
            phases.append(("meme", b["reaction"]))
        for phase, seconds in phases:
            if progress: progress(f"Lượt {i+1}/{len(doc['beats'])}: {phase}")
            canvas = _canvas(ep, b, phase, size, i, len(doc["beats"]))
            overlay = work / f"{i:02d}_{phase}.png"
            canvas.save(overlay)
            segment = work / f"{i:02d}_{phase}.mp4"
            meme = safe_asset(ep, b["meme"]) if phase == "meme" else None
            _segment(ep, bg, overlay, segment, size, cursor, seconds, quality, meme)
            segments.append(segment)
            cues.append((cursor, "comment" if phase == "comment" else ("meme" if phase == "meme" else b.get("sfx", "reveal"))))
            if phase == "meme" and meme and meme.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}:
                meme_audio.append((meme, cursor, seconds))
            cursor += seconds
    if progress: progress("Nối cảnh và trộn âm thanh")
    concat = work / "segments.txt"
    concat.write_text("\n".join("file '" + p.name.replace("'", "'\\''") + "'" for p in segments) + "\n", encoding="utf-8")
    joined = work / "joined.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
         "-c", "copy", str(joined)])
    audio = work / "accent.wav"
    _tones(audio, cursor, cues)
    out = ep / ("preview.mp4" if quality == "preview" else "final_1080x1920.mp4")
    _mux_audio(ep, doc, joined, audio, out, cursor, meme_audio)
    info = probe(out)
    report = {"output": out.name, "quality": quality, "expected_seconds": round(cursor, 3),
              "actual_seconds": round(info["duration"], 3), "plan_hash": _plan_hash(doc), "width": info["width"],
              "height": info["height"], "audio": info["has_audio"], "scenes": len(segments),
              "technical_pass": info["width"] == size[0] and info["height"] == size[1]
              and info["has_audio"] and abs(info["duration"]-cursor) < .30,
              "editorial_review_required": True}
    (ep / f"qc_{quality}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not report["technical_pass"]:
        raise RuntimeError("QC kỹ thuật chưa đạt; xem qc_" + quality + ".json")
    if progress: progress("Hoàn tất " + out.name)
    return report
