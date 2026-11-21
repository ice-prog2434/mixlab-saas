import subprocess, pytest
from app import audio

def tone(path, f, d=3):
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency={f}:duration={d}", path], check=True, capture_output=True)

def loudness(path):
    r = subprocess.run(["ffmpeg", "-i", path, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
    return float([l for l in r.stderr.splitlines() if "mean_volume" in l][0].split(":")[1].split()[0])

@pytest.mark.parametrize("style", list(audio.STYLES))
def test_each_style_renders(tmp_path, style):
    v, i, o = str(tmp_path / "v.wav"), str(tmp_path / "i.wav"), str(tmp_path / "o.mp3")
    tone(v, 440); tone(i, 110)
    audio.render(v, i, o, style, {})
    assert audio.probe(o)["duration"] > 2

def test_styles_differ():
    f = {s: audio.build_filter(s, {}) for s in audio.STYLES}
    assert len(set(f.values())) == len(f)

def test_balance_changes_output(tmp_path):
    v, i = str(tmp_path / "v.wav"), str(tmp_path / "i.wav")
    tone(v, 440); tone(i, 110)
    a, b = str(tmp_path / "a.mp3"), str(tmp_path / "b.mp3")
    audio.render(v, i, a, "rap_fr", {"voice_balance_db": -10})
    audio.render(v, i, b, "rap_fr", {"voice_balance_db": 8})
    assert a != b and audio.probe(a)["duration"] > 2
