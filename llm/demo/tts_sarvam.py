"""Sarvam Bulbul v3 Tamil TTS. Key read from SARVAM_API_KEY or ~/Claude/manbalai/backend/.env (never printed)."""
import base64, json, os, urllib.error, urllib.request

TAMIL_PICKS = ["kavitha", "shruti", "gokul", "vijay", "mani"]  # samples in llm/demo/voices/
URL = "https://api.sarvam.ai/text-to-speech"


def _key():
    k = os.environ.get("SARVAM_API_KEY")
    if k:
        return k
    env = os.path.expanduser("~/Claude/manbalai/backend/.env")
    if os.path.exists(env):
        for line in open(env, encoding="utf-8"):
            line = line.strip().removeprefix("export ")
            if line.startswith("SARVAM_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("SARVAM_API_KEY not set (env or manbalai backend .env)")


def synth(text, out_wav, speaker="kavitha", pace=1.0, model="bulbul:v3"):
    """Write WAV for text. Splits long text at sentence ends (API limit per request)."""
    chunks, cur = [], ""
    for part in text.replace("!", "!|").replace("?", "?|").replace(". ", ".|").split("|"):
        if len(cur) + len(part) > 450 and cur:
            chunks.append(cur); cur = ""
        cur += part
    if cur.strip():
        chunks.append(cur)
    audio = []
    for c in chunks:
        body = {"text": c.strip(), "target_language_code": "ta-IN", "model": model,
                "speaker": speaker, "pace": pace}
        req = urllib.request.Request(URL, json.dumps(body).encode(),
                                     {"api-subscription-key": _key(), "Content-Type": "application/json"})
        for attempt in range(3):
            try:
                d = json.load(urllib.request.urlopen(req, timeout=90)); break
            except urllib.error.HTTPError as e:
                if e.code < 500 and e.code != 429 or attempt == 2:
                    raise SystemExit(f"Sarvam TTS {e.code}: {e.read().decode()[:300]}")
        audio += [base64.b64decode(a) for a in d["audios"]]
    if len(audio) == 1:
        open(out_wav, "wb").write(audio[0]); return
    # concat WAV chunks via ffmpeg
    import subprocess, tempfile
    with tempfile.TemporaryDirectory() as td:
        lst = os.path.join(td, "l.txt")
        with open(lst, "w") as f:
            for i, a in enumerate(audio):
                p = os.path.join(td, f"{i}.wav"); open(p, "wb").write(a); f.write(f"file '{p}'\n")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, out_wav], check=True)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("text"); ap.add_argument("out")
    ap.add_argument("--speaker", default="kavitha"); a = ap.parse_args()
    synth(a.text, a.out, a.speaker)
