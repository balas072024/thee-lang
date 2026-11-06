# -*- coding: utf-8 -*-
"""Render the THEE demo video from demo.json (real captured answers) with Tamil narration.

Each scene = one still frame + its narration (macOS `say -v Vani`, the Tamil voice), encoded as
its own clip with identical settings, then joined with ffmpeg's concat demuxer.

  python3 llm/demo/make_video.py                  # → llm/demo/out/thee-demo.mp4
  python3 llm/demo/make_video.py --frames-only    # just the PNG frames, to check the layout
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
W, H, FPS = 1280, 720, 30

BG, PANEL, FG, MUTED = (22, 21, 19), (34, 32, 29), (236, 232, 225), (163, 157, 147)
ACCENT, OK, WARN, ERR = (251, 146, 60), (74, 222, 128), (250, 204, 21), (248, 113, 113)
KEYWORD = (125, 211, 252)

FONT_DIRS = ["/System/Library/Fonts/Supplemental", "/System/Library/Fonts", "/usr/share/fonts/truetype/noto",
             os.path.join(HERE, "fonts")]


def _font(names, size):
    for d in FONT_DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return ImageFont.truetype(p, size, layout_engine=ImageFont.Layout.RAQM)
    raise SystemExit(f"font not found: {names}")


TAMIL_FONTS = ["Tamil Sangam MN.ttc", "Tamil MN.ttc", "NotoSansTamil-Regular.ttf"]
SANS_FONTS = ["SFNS.ttf", "NotoSans-Regular.ttf", "DejaVuSans.ttf"]
MONO_FONTS = ["Menlo.ttc", "SFNSMono.ttf", "DejaVuSansMono.ttf"]
_cache = {}


def F(kind, size):
    key = (kind, size)
    if key not in _cache:
        _cache[key] = _font({"ta": TAMIL_FONTS, "sans": SANS_FONTS, "mono": MONO_FONTS}[kind], size)
    return _cache[key]


_TA = re.compile(r"[஀-௿]+(?:[ ‌‍]*[஀-௿]+)*")
KEYWORDS = {"thee", "kanal", "endral", "allathu", "illai", "ozhugu", "ul", "na", "moochhu", "varai",
            "unmai", "poi", "தீ", "கனல்", "என்றால்", "அல்லது", "இல்லை", "ஓழுகு", "உள்", "நா", "மூச்சு",
            "வரை", "உண்மை", "பொய்", "assert_eq"}


def runs(text):
    """Split text into (segment, is_tamil) runs so each gets a font that has its glyphs."""
    out, i = [], 0
    for m in _TA.finditer(text):
        if m.start() > i:
            out.append((text[i:m.start()], False))
        out.append((m.group(0), True))
        i = m.end()
    if i < len(text):
        out.append((text[i:], False))
    return out


def text_width(text, size, base="sans"):
    return sum(F("ta" if ta else base, size).getlength(seg) for seg, ta in runs(text))


def draw_line(d, xy, text, size, fill, base="sans", color_keywords=False):
    x, y = xy
    for seg, ta in runs(text):
        font = F("ta" if ta else base, size)
        if color_keywords:
            for tok in re.split(r"(\s+|[(){}\[\],=+\-*/<>%])", seg):
                if not tok:
                    continue
                d.text((x, y), tok, font=font, fill=KEYWORD if tok in KEYWORDS else fill)
                x += font.getlength(tok)
        else:
            d.text((x, y), seg, font=font, fill=fill)
            x += font.getlength(seg)
    return x


def wrap(text, size, max_w, base="sans"):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            trial = (cur + " " + word).strip()
            if text_width(trial, size, base) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def canvas():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def header(d, step=""):
    draw_line(d, (48, 28), "தீ THEE", 26, ACCENT)
    draw_line(d, (175, 33), "Tamil coding tutor · runs offline", 20, MUTED)
    if step:
        tw = text_width(step, 18)
        draw_line(d, (W - 48 - tw, 34), step, 18, MUTED)


def panel(d, box, title=None, title_color=MUTED):
    d.rounded_rectangle(box, radius=16, fill=PANEL)
    if title:
        draw_line(d, (box[0] + 22, box[1] + 14), title, 18, title_color)


def clip_line(text, size, max_w, base="mono"):
    if text_width(text, size, base) <= max_w:
        return text
    while text and text_width(text + " …", size, base) > max_w:
        text = text[:-1]
    return text + " …"


def code_block(d, x, y, code, size=22, max_lines=14, max_w=None):
    lh = int(size * 1.45)
    lines = [ln for ln in code.replace("```thee", "").replace("```", "").strip("\n").splitlines()][:max_lines]
    for i, ln in enumerate(lines):
        ln = ln.replace("\t", "    ")
        if max_w:
            ln = clip_line(ln, size, max_w)
        draw_line(d, (x, y + i * lh), ln, size, FG, base="mono", color_keywords=True)
    return y + len(lines) * lh


# ── scenes ───────────────────────────────────────────────────────────────

def scene_title(stats):
    img, d = canvas()
    draw_line(d, (W // 2 - text_width("தீ", 130, "sans") // 2, 150), "தீ", 130, ACCENT)
    t = "THEE — தமிழ்ல programming கத்துக்க ஒரு AI tutor"
    draw_line(d, ((W - text_width(t, 38)) // 2, 340), t, 38, FG)
    for i, s in enumerate(stats):
        draw_line(d, ((W - text_width(s, 24)) // 2, 420 + i * 40), s, 24, MUTED)
    return img


def scene_demo(n, total, demo, stage):
    """stage 1: question; 2: + code; 3: + run result; 4: + explanation"""
    img, d = canvas()
    header(d, f"Demo {n}/{total}")
    panel(d, (48, 78, W - 48, 166), "கேள்வி (question)")
    q = re.sub(r"\s*Function பேரு `[^`]+`\.?", "", demo["question"]).strip()
    for i, ln in enumerate(wrap(q, 26, W - 140)[:1]):
        draw_line(d, (70, 116 + i * 32), ln, 26, FG)
    if stage >= 2:
        panel(d, (48, 182, 760, 650), "THEE code (model-ஓட பதில்)")
        code_block(d, 70, 216, demo["code"], size=20, max_lines=13, max_w=760 - 70 - 22)
    if stage >= 3:
        v = demo["verdict"]
        color, label = {"verified": (OK, "✅ ஓடி சரிபார்த்தது"), "ran": (WARN, "🟡 ஓடுது, சரிபார்க்கல"),
                        "failed": (ERR, "⚠️ ஓடல (error)"), "correct": (OK, "✅ சரியான பதில்"),
                        "wrong": (ERR, "❌ தப்பான பதில்")}[v]
        panel(d, (780, 182, W - 48, 400), "THEE interpreter-ல ஓட்டினது", MUTED)
        draw_line(d, (802, 216), label.replace("✅ ", "").replace("🟡 ", "").replace("⚠️ ", ""), 24, color)
        d.ellipse((W - 92, 220, W - 72, 240), fill=color)
        if demo.get("probe"):
            draw_line(d, (802, 252), demo["probe"], 18, MUTED, base="mono")
            draw_line(d, (802, 282), "எதிர்பார்த்தது: " + demo["expected"], 18, MUTED)
            y = 316
        else:
            draw_line(d, (802, 248), f"attempt {demo['attempts']}", 18, MUTED)
            y = 282
        body = demo["output"] if v != "failed" else (demo["error"].splitlines() or [""])[-1].replace("தீ பிழை: ", "")
        if demo.get("probe") and v != "failed":
            body = "வந்தது: " + (body.splitlines()[-1] if body else "(no output)")
        for ln in (body or "(no output)").splitlines()[:4]:
            for wl in wrap(ln, 20, W - 48 - 830, "mono")[:2]:
                draw_line(d, (802, y), wl, 20, color if v in ("correct", "wrong", "failed") else FG, base="mono")
                y += 28
    if stage >= 4 and demo.get("explanation"):
        panel(d, (780, 416, W - 48, 650), "விளக்கம் (explanation)")
        y = 450
        for ln in wrap(demo["explanation"], 19, W - 48 - 830 - 10)[:6]:
            draw_line(d, (802, y), ln, 19, FG)
            y += 30
    return img


def scene_convert(conv):
    img, d = canvas()
    header(d, "Feature")
    t = "ஒரே code, ரெண்டு மாதிரி எழுதலாம்"
    draw_line(d, (48, 92), t, 34, FG)
    panel(d, (48, 160, 620, 520), "Romanized keywords")
    code_block(d, 72, 200, conv["roman"], size=26)
    panel(d, (660, 160, W - 48, 520), "தமிழ் keywords")
    code_block(d, 684, 200, conv["tamil"], size=26)
    draw_line(d, (48, 560), "ரெண்டும் ஒரே output: " + conv["output"], 26, OK)
    return img


def scene_sandbox(sb):
    img, d = canvas()
    header(d, "Feature")
    draw_line(d, (48, 92), "Sandbox: model எழுதின code உங்க computer-ஐ தொடாது", 32, FG)
    panel(d, (48, 160, W - 48, 300), "Code")
    code_block(d, 72, 200, sb["code"], size=26)
    panel(d, (48, 320, W - 48, 470), "THEE --sandbox")
    err = (sb["error"].splitlines() or [""])[-1]
    for i, ln in enumerate(wrap(err, 22, W - 160, "mono")[:3]):
        draw_line(d, (72, 360 + i * 32), ln, 22, ERR, base="mono")
    draw_line(d, (48, 510), "Files, network, shell, GPIO — எல்லாம் block. 10 விநாடி, 512 MB limit.", 24, MUTED)
    return img


def scene_score(scores):
    img, d = canvas()
    header(d, "Benchmark")
    draw_line(d, (48, 92), "109 தமிழ் tasks — hidden tests-ல pass ஆனது", 32, FG)
    x0, y0, bw, gap, hmax = 160, 610, 220, 110, 380
    top = max(v for _, v, _ in scores) or 1
    for i, (name, v, color) in enumerate(scores):
        x = x0 + i * (bw + gap)
        h = max(4, int(hmax * v / max(top, 30)))
        d.rounded_rectangle((x, y0 - h, x + bw, y0), radius=10, fill=color)
        lab = f"{v:.1f}%"
        draw_line(d, (x + (bw - text_width(lab, 30)) // 2, y0 - h - 44), lab, 30, FG)
        draw_line(d, (x + (bw - text_width(name, 22)) // 2, y0 + 16), name, 22, MUTED)
    return img


def scene_end():
    img, d = canvas()
    draw_line(d, ((W - text_width("தீ", 90)) // 2, 150), "தீ", 90, ACCENT)
    lines = [("ollama run thee", 40, FG, "mono"), ("github.com/balas072024/thee-lang", 26, MUTED, "sans"),
             ("அடுத்து: 3,000+ KodCode tasks-ல v3 training", 26, MUTED, "sans")]
    y = 330
    for t, s, c, b in lines:
        draw_line(d, ((W - text_width(t, s, b)) // 2, y), t, s, c, base=b)
        y += s + 34
    return img


# ── narration + encoding ─────────────────────────────────────────────────

def tts(text, path):
    if not text:
        return 0.0
    aiff = path + ".aiff"
    subprocess.run(["say", "-v", "Vani", "-r", "165", "-o", aiff, text], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", aiff, "-ar", "48000", "-ac", "2", path], check=True)
    os.remove(aiff)
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def encode(png, wav, seconds, out):
    tmp = out[:-4] + ".tmp.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", png]
    if wav:
        cmd += ["-i", wav]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    fade_out = max(0, seconds - 0.25)
    cmd += ["-vf", f"format=yuv420p,loop=-1:1,trim=duration={seconds:.2f},fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out:.2f}:d=0.25",
            "-af", f"apad,atrim=0:{seconds:.2f}", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast",
            "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
            "-shortest", tmp]
    subprocess.run(cmd, check=True)
    os.replace(tmp, out)


def build_scenes(data):
    demos = data["demos"]
    passed = sum(x["verdict"] in ("verified", "correct") for x in demos)
    v2 = data.get("score_v2")
    stats = ["Qwen2.5-Coder 1.5B · தமிழ் data-ல fine-tune · Ollama-ல 986 MB",
             "இங்க வர்ற எல்லா பதிலும் model-ஓட உண்மையான பதில், உண்மையா ஓட்டினது"]
    scenes = [(scene_title(stats),
               "வணக்கம்! இது தீ. தமிழ்ல programming கத்துக்க ஒரு சின்ன AI tutor. இது உங்க computer-லயே, internet இல்லாம ஓடும்.", 2.5)]
    say_q = "கேள்வி தமிழ்ல கேக்கலாம்."
    for i, demo in enumerate(demos, 1):
        v = demo["verdict"]
        say_v = {"verified": "Code-ஐ ஓட்டி பார்த்தோம். எல்லா check-உம் pass ஆச்சு.",
                 "ran": "Code ஓடுது, ஆனா check இல்லாததால logic சரிபார்க்கல.",
                 "failed": "இந்த தடவை code-ல error. அத மறைக்காம காட்டுறோம்.",
                 "correct": "THEE-ல ஓட்டி பார்த்தோம். பதில் சரி.",
                 "wrong": "ஓடுது, ஆனா பதில் தப்பு. இன்னும் training வேணும்."}[v]
        scenes += [(scene_demo(i, len(demos), demo, 1), say_q if i == 1 else "", 2.5),
                   (scene_demo(i, len(demos), demo, 2), "Model THEE code எழுதுது." if i == 1 else "", 3.0),
                   (scene_demo(i, len(demos), demo, 3), say_v, 2.5),
                   (scene_demo(i, len(demos), demo, 4), "அப்புறம் தமிழ்ல விளக்கம் சொல்லுது." if i == 1 else "", 4.0)]
    scenes.append((scene_convert(data["convert"]),
                   "Keywords-ஐ தமிழ்லயும் எழுதலாம், romanized-ஆவும் எழுதலாம். ரெண்டும் ஒரே மாதிரி ஓடும்.", 3.0))
    scenes.append((scene_sandbox(data["sandbox"]),
                   "Model எழுதின code sandbox-ல தான் ஓடும். Files, network எதையும் தொட முடியாது.", 3.0))
    scores = [("Base model", 6.4, (120, 113, 108)), ("v1", 16.5, (191, 120, 60))]
    if v2 is not None:
        scores.append(("v2", v2, ACCENT))
    scenes.append((scene_score(scores),
                   "Benchmark-ல base model ஆறு சதவீதம், எங்க model பதினாறு சதவீதம். இன்னும் நிறைய data-ஓட அடுத்த version வருது.", 3.0))
    scenes.append((scene_end(), "Ollama-ல, ollama run thee. நன்றி!", 2.5))
    return scenes, passed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "demo.json"))
    ap.add_argument("--frames-only", action="store_true")
    a = ap.parse_args()
    data = json.load(open(a.data, encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    scenes, passed = build_scenes(data)
    clips = []
    for i, (img, narration, min_s) in enumerate(scenes):
        png = os.path.join(OUT, f"s{i:02d}.png")
        img.save(png)
        if a.frames_only:
            continue
        wav = os.path.join(OUT, f"s{i:02d}.wav") if narration else None
        dur = tts(narration, wav) if wav else 0.0
        clip = os.path.join(OUT, f"s{i:02d}.mp4")
        encode(png, wav, max(min_s, dur + 0.6), clip)
        clips.append(clip)
        print(f"scene {i:02d}: {max(min_s, dur + 0.6):.1f}s", file=sys.stderr)
    if a.frames_only:
        print(f"frames in {OUT}", file=sys.stderr)
        return
    lst = os.path.join(OUT, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.basename(c)}'\n" for c in clips)
    final = os.path.join(OUT, "thee-demo.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c", "copy", "-movflags", "+faststart", final + ".tmp.mp4"], check=True, cwd=OUT)
    os.replace(final + ".tmp.mp4", final)
    print(f"✓ {final}  ({passed}/{len(data['demos'])} demos verified)", file=sys.stderr)


if __name__ == "__main__":
    main()
