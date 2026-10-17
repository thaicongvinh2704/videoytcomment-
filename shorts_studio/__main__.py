from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import episode_dir, new_episode
from .director import ai_direct, ordered_draft, write_brief
from .renderer import render
from .web import serve


def main():
    p = argparse.ArgumentParser(description="Shorts Comment AI Studio")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("create", help="Tạo tập từ tài sản đã có trên máy")
    c.add_argument("--background", type=Path, required=True)
    c.add_argument("--comments", nargs="+", type=Path, required=True)
    c.add_argument("--women", nargs="+", type=Path, required=True)
    c.add_argument("--memes", nargs="*", type=Path, default=[])
    c.add_argument("--title", default="Tập mới")
    c.add_argument("--voice", type=Path)
    c.add_argument("--music", type=Path)
    r = sub.add_parser("render", help="Render preview hoặc final")
    r.add_argument("id")
    r.add_argument("--quality", choices=["preview", "final"], default="preview")
    a = sub.add_parser("ai", help="AI xem ảnh và đạo diễn; cần OPENAI_API_KEY")
    a.add_argument("id")
    b = sub.add_parser("brief", help="Tạo nhiệm vụ đọc asset cho AntiGravity")
    b.add_argument("id")
    s = sub.add_parser("serve", help="Mở web studio")
    s.add_argument("--port", type=int, default=8765)
    sub.add_parser("demo", help="Tạo tài sản giả lập và render thử")
    args = p.parse_args()
    if args.command == "serve":
        serve(port=args.port)
    elif args.command == "create":
        doc = new_episode(args.background, args.comments, args.women, args.memes, args.title,
                          voice=args.voice, music=args.music)
        doc = ordered_draft(episode_dir(doc["id"]))
        print(json.dumps({"id": doc["id"], "path": str(episode_dir(doc["id"]))}, ensure_ascii=False))
    elif args.command == "render":
        print(json.dumps(render(episode_dir(args.id), args.quality, progress=print), ensure_ascii=False, indent=2))
    elif args.command == "ai":
        doc = ai_direct(episode_dir(args.id))
        print(json.dumps({"id": doc["id"], "beats": doc["beats"], "note": doc["note"]}, ensure_ascii=False, indent=2))
    elif args.command == "brief":
        print(write_brief(episode_dir(args.id)))
    elif args.command == "demo":
        from .demo import create_demo
        ep = create_demo()
        print(json.dumps(render(ep, "preview", progress=print), ensure_ascii=False, indent=2))
        print("Demo:", ep / "preview.mp4")


if __name__ == "__main__":
    main()
