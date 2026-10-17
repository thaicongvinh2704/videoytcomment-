from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .core import episode_dir, new_episode, run
from .director import ordered_draft
from .renderer import _font


def create_demo() -> Path:
    """Generates neutral test art; none of the user's reference videos are reused."""
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        background = root / "moving_background.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
             "testsrc2=size=540x960:rate=30", "-t", "9", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(background)])
        imgs = {}
        content = {"comment_1": ("Mình hỏi đi dạo thôi...", "sao bạn mặc như dự tiệc?"),
                   "comment_2": ("Nếu gặp người yêu cũ", "thì phải thật chỉnh chu chứ!"),
                   "woman_1": ("NHÂN VẬT AI", "Tạo ảnh của bạn tại đây"),
                   "woman_2": ("ẢNH NHÂN VẬT 2", "Demo không dùng ảnh ai"),
                   "meme": ("PLOT TWIST", "Biểu cảm hài ở đây")}
        for name, lines in content.items():
            w, h = (850, 220) if name.startswith("comment") else (700, 800)
            color = "#faf7fb" if name.startswith("comment") else ("#534687" if name != "meme" else "#e0747d")
            im = Image.new("RGB", (w, h), color); d = ImageDraw.Draw(im)
            for n, line in enumerate(lines):
                d.text((38, 50+n*75), line, fill="#202443" if name.startswith("comment") else "white",
                       font=_font(34))
            imgs[name] = root / f"{name}.png"; im.save(imgs[name])
        doc = new_episode(background, [imgs["comment_1"], imgs["comment_2"]],
                          [imgs["woman_1"], imgs["woman_2"]], [imgs["meme"]],
                          title="DEMO kỹ thuật — không đăng", episode_id="demo_test")
        ep = episode_dir(doc["id"])
        ordered_draft(ep)
        return ep
