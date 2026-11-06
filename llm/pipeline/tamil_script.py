# -*- coding: utf-8 -*-
"""Convert THEE keywords between romanized (moochhu, kanal) and Tamil script (மூச்சு, கனல்).

Tamil script is the main form for learners; romanized stays as an alias.
Only keywords are changed: strings, comments, identifiers and .member names are left alone.

  python3 llm/pipeline/tamil_script.py --to tamil  file.thee
  python3 llm/pipeline/tamil_script.py --to roman  file.thee
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))
from thee_lang.lexer import KEYWORDS  # noqa: E402

_TAMIL = re.compile(r"[஀-௿]")
_WORD = re.compile(r"[A-Za-z_஀-௿][A-Za-z0-9_஀-௿]*")


def _build_maps():
    by_type = {}
    for word, tt in KEYWORDS.items():
        by_type.setdefault(tt, []).append(word)
    to_tamil, to_roman = {}, {}
    for tt, words in by_type.items():
        tamil = [w for w in words if _TAMIL.search(w)]
        latin = [w for w in words if not _TAMIL.search(w)]
        if not tamil or not latin:
            continue
        canon_tamil, canon_roman = tamil[0], latin[0]  # first entry in lexer order
        for w in latin:
            to_tamil[w] = canon_tamil
        for w in tamil:
            to_roman[w] = canon_roman
    return to_tamil, to_roman


TO_TAMIL, TO_ROMAN = _build_maps()


def convert(source, to="tamil"):
    table = TO_TAMIL if to == "tamil" else TO_ROMAN
    out, i, n = [], 0, len(source)
    last_sig = ""  # last non-space character emitted, to skip .member names
    while i < n:
        ch = source[i]
        # comments
        if source.startswith("//", i):
            j = source.find("\n", i)
            j = n if j == -1 else j
            out.append(source[i:j]); i = j; continue
        if source.startswith("/*", i):
            j = source.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out.append(source[i:j]); i = j; continue
        # strings
        if ch in "\"'`":
            j = i + 1
            while j < n and source[j] != ch:
                j += 2 if source[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(source[i:j]); i = j; last_sig = ch; continue
        m = _WORD.match(source, i)
        if m:
            w = m.group(0)
            out.append(w if last_sig == "." else table.get(w, w))
            i = m.end(); last_sig = w[-1]; continue
        out.append(ch)
        if not ch.isspace():
            last_sig = ch
        i += 1
    return "".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--to", choices=["tamil", "roman"], default="tamil")
    ap.add_argument("file", nargs="?", help="THEE file (default: stdin)")
    a = ap.parse_args()
    src = open(a.file, encoding="utf-8").read() if a.file else sys.stdin.read()
    sys.stdout.write(convert(src, a.to))


if __name__ == "__main__":
    main()
