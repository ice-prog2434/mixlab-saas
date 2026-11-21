"""Moteur audio FFmpeg. Chaque style = des paramètres réellement différents."""
import json, subprocess

# eq: (fréquence Hz, largeur Hz, gain dB) ; comp: (seuil dB, ratio)
STYLES = {
    "rap_fr":   {"hp": 90,  "eq": [(250, 200, -2), (3500, 2000, 3)],  "comp": (-20, 4),   "reverb": 0.10, "delay": 0.00},
    "drill":    {"hp": 110, "eq": [(300, 200, -3), (5000, 3000, 4)],  "comp": (-22, 5),   "reverb": 0.05, "delay": 0.08},
    "trap":     {"hp": 100, "eq": [(200, 150, -2), (4500, 3000, 3)],  "comp": (-20, 4),   "reverb": 0.15, "delay": 0.15},
    "rnb":      {"hp": 80,  "eq": [(200, 150, 1), (8000, 4000, 2)],   "comp": (-18, 3),   "reverb": 0.30, "delay": 0.10},
    "afrobeat": {"hp": 85,  "eq": [(400, 300, -1), (3000, 2000, 2)],  "comp": (-18, 3),   "reverb": 0.18, "delay": 0.12},
    "pop":      {"hp": 85,  "eq": [(250, 200, -1), (6000, 3000, 3)],  "comp": (-19, 3.5), "reverb": 0.20, "delay": 0.05},
    "naturel":  {"hp": 70,  "eq": [],                                 "comp": (-16, 2),   "reverb": 0.00, "delay": 0.00},
}

def build_filter(style: str, opts: dict) -> str:
    p = STYLES[style]
    intensity = min(max(float(opts.get("intensity", 0.5)), 0), 1)
    balance_db = min(max(float(opts.get("voice_balance_db", 0)), -12), 12)
    reverb = min(max(float(opts.get("reverb", p["reverb"])), 0), 1)
    delay = min(max(float(opts.get("delay", p["delay"])), 0), 1)
    thr, ratio = p["comp"]
    ratio = 1 + (ratio - 1) * (0.4 + 1.2 * intensity)
    v = [f"highpass=f={p['hp']}"]
    for f, w, g in p["eq"]:
        v.append(f"equalizer=f={f}:width_type=h:width={w}:g={g * (0.5 + intensity):.2f}")
    v.append(f"acompressor=threshold={thr}dB:ratio={ratio:.2f}:attack=10:release=120:makeup=3")
    if reverb > 0:
        v.append(f"aecho=0.8:0.7:60|120:{reverb * 0.5:.3f}|{reverb * 0.3:.3f}")
    if delay > 0:
        v.append(f"aecho=0.8:0.6:350:{delay * 0.6:.3f}")
    v.append(f"volume={balance_db}dB")
    return (
        "[0:a]" + ",".join(v) + "[v];"
        "[1:a]volume=0dB[i];"
        "[v][i]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95,"
        "loudnorm=I=-14:TP=-1:LRA=11[out]"
    )

def build_cmd(voice: str, instru: str, out: str, style: str, opts: dict) -> list[str]:
    codec = ["-c:a", "libmp3lame", "-b:a", "256k"] if out.endswith(".mp3") else []
    return ["ffmpeg", "-y", "-i", voice, "-i", instru, "-filter_complex", build_filter(style, opts), "-map", "[out]", *codec, out]

def probe(path: str) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration,format_name", "-of", "json", path],
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        raise ValueError("Fichier audio illisible")
    f = json.loads(r.stdout)["format"]
    return {"duration": float(f["duration"]), "format": f["format_name"]}

def render(voice, instru, out, style, opts):
    r = subprocess.run(build_cmd(voice, instru, out, style, opts), capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-500:])
