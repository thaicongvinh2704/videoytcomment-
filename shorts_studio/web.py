from __future__ import annotations

import json
import tempfile
import threading
import traceback
import uuid
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .core import EPISODES, ROOT, assets, episode_dir, load_doc, new_episode, safe_asset, save_doc, validate_doc
from .director import ai_direct, ordered_draft, write_brief
from .renderer import render

JOBS: dict[str, dict] = {}


class Handler(BaseHTTPRequestHandler):
    server_version = "ShortsStudio/1.0"

    def _json(self, data, status=200):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _file(self, path: Path):
        from mimetypes import guess_type
        self.send_response(200)
        self.send_header("Content-Type", guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(path.stat().st_size))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with path.open("rb") as f:
            while block := f.read(1024*1024):
                self.wfile.write(block)

    def do_GET(self):
        try:
            url = urlparse(self.path)
            q = parse_qs(url.query)
            if url.path == "/":
                return self._file(ROOT / "shorts_studio" / "static" / "index.html")
            if url.path == "/api/episodes":
                result = [{"id": p.name, "title": load_doc(p).get("title", "")}
                          for p in sorted(EPISODES.iterdir(), reverse=True) if p.is_dir() and (p / "episode.json").exists()] if EPISODES.exists() else []
                return self._json(result)
            if url.path == "/api/episode":
                ep = episode_dir(q.get("id", [""])[0])
                doc = load_doc(ep)
                return self._json({"doc": doc,
                                   "assets": {cat: assets(ep, cat) for cat in ("comments", "women", "memes")},
                                   "preview": (ep / "preview.mp4").exists(),
                                   "final": (ep / "final_1080x1920.mp4").exists()})
            if url.path == "/api/job":
                return self._json(JOBS.get(q.get("job", [""])[0], {"status": "missing"}))
            if url.path.startswith("/media/"):
                parts = unquote(url.path[len("/media/"):]).split("/", 1)
                if len(parts) != 2: raise ValueError("Đường dẫn thiếu")
                ep = episode_dir(parts[0])
                return self._file(safe_asset(ep, parts[1]))
            self._json({"error": "Không thấy đường dẫn"}, 404)
        except Exception as exc:
            self._json({"error": str(exc)}, 400)

    def _body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > 256*1024*1024:
            raise ValueError("Upload phải dưới 256 MB; clip lớn có thể dùng CLI.")
        return self.rfile.read(length)

    def _parts(self, body):
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            raise ValueError("Cần multipart/form-data")
        message = BytesParser(policy=default).parsebytes(
            b"MIME-Version: 1.0\r\nContent-Type: " + content_type.encode() + b"\r\n\r\n" + body)
        fields, uploaded = {}, {}
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition") or ""
            filename = part.get_filename()
            data = part.get_payload(decode=True)
            if filename:
                uploaded.setdefault(name, []).append((filename, data))
            else:
                fields[name] = data.decode("utf-8", errors="replace")
        return fields, uploaded

    def do_POST(self):
        try:
            if self.path == "/api/create":
                fields, uploaded = self._parts(self._body())
                if len(uploaded.get("background", [])) != 1:
                    raise ValueError("Cần một clip nền")
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    saved = {}
                    for category, data in uploaded.items():
                        saved[category] = []
                        for i, (name, content) in enumerate(data):
                            suffix = Path(name).suffix.lower()
                            path = root / f"{category}_{i:02d}{suffix}"
                            path.write_bytes(content)
                            saved[category].append(path)
                    doc = new_episode(saved["background"][0], saved.get("comments", []),
                                      saved.get("women", []), saved.get("memes", []),
                                      title=fields.get("title", "Tập mới"),
                                      voice=saved.get("voice", [None])[0], music=saved.get("music", [None])[0])
                ordered_draft(episode_dir(doc["id"]))
                return self._json({"id": doc["id"]})
            body = json.loads(self._body())
            ep = episode_dir(body.get("id", ""))
            if self.path == "/api/direct":
                doc = ai_direct(ep) if body.get("mode") == "ai" else ordered_draft(ep)
                return self._json({"doc": doc})
            if self.path == "/api/save":
                doc = body.get("doc", {})
                if doc.get("approved") and not (ep / "preview.mp4").is_file():
                    raise ValueError("Cần render preview trước khi duyệt final")
                validate_doc(ep, doc)
                save_doc(ep, doc)
                return self._json({"ok": True})
            if self.path == "/api/render":
                quality = body.get("quality", "preview")
                job_id = uuid.uuid4().hex[:12]
                JOBS[job_id] = {"status": "running", "message": "Bắt đầu dựng", "quality": quality}
                def task():
                    try:
                        def update(message): JOBS[job_id]["message"] = message
                        report = render(ep, quality, progress=update)
                        JOBS[job_id].update(status="done", report=report)
                    except Exception as err:
                        JOBS[job_id].update(status="error", message=str(err))
                        (ep / "render_error.txt").write_text(traceback.format_exc(), encoding="utf-8")
                threading.Thread(target=task, daemon=True).start()
                return self._json({"job": job_id})
            if self.path == "/api/brief":
                return self._json({"path": str(write_brief(ep))})
            self._json({"error": "Không thấy đường dẫn"}, 404)
        except Exception as exc:
            self._json({"error": str(exc)}, 400)


def serve(host="127.0.0.1", port=8765):
    EPISODES.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Studio: http://{host}:{port}", flush=True)
    server.serve_forever()
