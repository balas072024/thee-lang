# -*- coding: utf-8 -*-
"""Build a single-file playground (THEE source embedded) that works from anywhere:
GitHub Pages, any static host, or opened straight from disk.

  python3 playground/build_playground.py      # → playground/dist/thee-playground.html
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FILES = ["__init__.py", "lexer.py", "parser.py", "interpreter.py", "sandbox.py"]


def main():
    files = [{"name": f, "text": open(os.path.join(ROOT, "src", "thee_lang", f), encoding="utf-8").read()}
             for f in FILES]
    conv = open(os.path.join(ROOT, "llm", "pipeline", "tamil_script.py"), encoding="utf-8").read()
    blob = json.dumps({"files": files, "converter": conv}, ensure_ascii=False).replace("</", "<\\/")
    html = open(os.path.join(HERE, "index.html"), encoding="utf-8").read()
    html = html.replace("<script>\n", f"<script>window.THEE_SOURCES = {blob};</script>\n<script>\n", 1)
    os.makedirs(os.path.join(HERE, "dist"), exist_ok=True)
    out = os.path.join(HERE, "dist", "thee-playground.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"wrote {out} ({os.path.getsize(out) // 1024} KB)")


if __name__ == "__main__":
    main()
