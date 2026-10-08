#!/usr/bin/env python3
"""영상 루프 기계 검사 (1층) — 종료코드로 말한다. 0=통과, 1=실패.

  python3 tools/film.py check [--staged] [--quiet]   # data/ 대본·샷리스트 JSON 검사 (커밋 훅이 부름)
  python3 tools/film.py clip <파일.mp4> [--spec shorts|reels|youtube]   # 완성 영상 규격·블랙·정지·음량
  python3 tools/film.py sheet <파일.mp4> [--out captures/tmp] [--n 12]  # 눈 검사용 컨택트시트(프레임 모음) 만들기
  python3 tools/film.py selftest                      # 이 검사기가 거짓 통과를 안 내는지 스스로 시험

판단은 이름이 아니라 실제 측정값으로 한다 (ffprobe/ffmpeg 출력).
"""
import json, re, subprocess, sys, shutil, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPECS = {  # 세로 숏폼 기본. 길이는 초.
    "shorts":  dict(w=1080, h=1920, min_s=5,  max_s=60,  fps=(24, 60)),
    "reels":   dict(w=1080, h=1920, min_s=5,  max_s=90,  fps=(24, 60)),
    "youtube": dict(w=1920, h=1080, min_s=30, max_s=1200, fps=(24, 60)),
}
PLACEHOLDER = re.compile(r"TBD|Lorem|\bTODO\b|자리표시|〔.*?〕|^-1$")

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr

# ───────── data 검사 ─────────
def check_data(staged=False, quiet=False):
    errs = []
    banned = []
    bp = ROOT / "data/banned_words.json"
    if bp.exists():
        try: banned = json.loads(bp.read_text("utf-8"))
        except Exception as e: errs.append(f"banned_words.json 읽기 실패: {e}")
    files = sorted((ROOT / "data/episodes").glob("*.json"))
    if staged:
        _, out, _ = run(["git", "diff", "--cached", "--name-only"])
        keep = {ROOT / l for l in out.split() if l.startswith("data/")}
        files = [f for f in files if f in keep]
    for f in files:
        try: ep = json.loads(f.read_text("utf-8"))
        except Exception as e:
            errs.append(f"{f.name}: JSON 이 깨짐 ({e})"); continue
        for k in ("id", "title", "platform", "hook", "shots"):
            if k not in ep: errs.append(f"{f.name}: '{k}' 없음")
        if ep.get("platform") not in SPECS: errs.append(f"{f.name}: platform 은 {list(SPECS)} 중 하나")
        shots = ep.get("shots", [])
        if not shots: errs.append(f"{f.name}: shots 가 비어 있음")
        total = 0.0
        for i, s in enumerate(shots, 1):
            for k in ("id", "sec", "visual", "audio"):
                if k not in s: errs.append(f"{f.name} 샷{i}: '{k}' 없음")
            sec = s.get("sec", 0)
            if not isinstance(sec, (int, float)) or sec <= 0: errs.append(f"{f.name} 샷{i}: sec 가 양수가 아님")
            else: total += sec
            blob = json.dumps(s, ensure_ascii=False)
            if PLACEHOLDER.search(blob): errs.append(f"{f.name} 샷{i}: 자리표시 글자 남아 있음")
            for w in banned:
                if w in blob: errs.append(f"{f.name} 샷{i}: 금지어 '{w}'")
        sp = SPECS.get(ep.get("platform"))
        if sp and shots and not (sp["min_s"] <= total <= sp["max_s"]):
            errs.append(f"{f.name}: 총 {total:g}초 — {ep['platform']} 은 {sp['min_s']}~{sp['max_s']}초")
        if shots and shots[0].get("sec", 99) > 4 and "hook" in ep and not ep["hook"].strip():
            errs.append(f"{f.name}: 첫 샷이 4초 넘는데 hook 문장이 없음")
    for mp in sorted((ROOT / "publish").glob("*/meta.json")):
        try: m = json.loads(mp.read_text("utf-8"))
        except Exception as e:
            errs.append(f"{mp.parent.name}/meta.json 깨짐 ({e})"); continue
        for k in ("title", "description", "hashtags", "ai_generated", "music_source"):
            if k not in m: errs.append(f"{mp.parent.name}/meta.json: '{k}' 없음")
        if m.get("ai_generated") is not True: errs.append(f"{mp.parent.name}/meta.json: ai_generated 는 true 여야 함 (AI 표기)")
        if PLACEHOLDER.search(json.dumps(m, ensure_ascii=False)): errs.append(f"{mp.parent.name}/meta.json: 자리표시 남아 있음")
    if errs:
        for e in errs: print("✖", e)
        print(f"✖ 영상 데이터 검사 실패 ({len(errs)}건)"); return 1
    if not quiet: print(f"✔ 영상 데이터 검사 통과 (에피소드 {len(files)}개 / 오류 0)")
    return 0

# ───────── 완성 영상 검사 ─────────
def probe(path):
    rc, out, err = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)])
    if rc: raise RuntimeError(err.strip() or "ffprobe 실패")
    return json.loads(out)

def check_clip(path, spec_name="shorts"):
    p = Path(path)
    if not p.is_file(): print(f"✖ 파일 없음: {p}"); return 1
    sp = SPECS[spec_name]; errs = []; notes = []
    try: info = probe(p)
    except Exception as e: print(f"✖ 열 수 없는 영상: {e}"); return 1
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if not v: print("✖ 영상 스트림 없음"); return 1
    w, h = int(v["width"]), int(v["height"])
    if (w, h) != (sp["w"], sp["h"]): errs.append(f"해상도 {w}x{h} (필요 {sp['w']}x{sp['h']})")
    num, den = v["r_frame_rate"].split("/"); fps = float(num) / float(den or 1)
    if not (sp["min_s"] <= float(info["format"]["duration"]) <= sp["max_s"]):
        errs.append(f"길이 {float(info['format']['duration']):.1f}초 (필요 {sp['min_s']}~{sp['max_s']}초)")
    if not (sp["fps"][0] <= fps <= sp["fps"][1]): errs.append(f"fps {fps:.1f} (필요 {sp['fps'][0]}~{sp['fps'][1]})")
    if v.get("codec_name") != "h264": notes.append(f"코덱 {v.get('codec_name')} (h264 권장)")
    if not a: errs.append("오디오 스트림 없음 (무음 영상은 올리지 않는다)")
    # 블랙 프레임 · 정지 장면
    _, _, e1 = run(["ffmpeg", "-nostats", "-i", str(p), "-vf", "blackdetect=d=0.5:pix_th=0.10", "-an", "-f", "null", "-"])
    blacks = re.findall(r"black_duration:([\d.]+)", e1)
    if blacks: errs.append(f"검은 화면 {len(blacks)}곳 (합 {sum(map(float, blacks)):.1f}초)")
    _, _, e2 = run(["ffmpeg", "-nostats", "-i", str(p), "-vf", "freezedetect=n=-60dB:d=2", "-an", "-f", "null", "-"])
    freezes = re.findall(r"freeze_duration: ([\d.]+)", e2)
    if freezes: errs.append(f"2초 넘게 멈춘 장면 {len(freezes)}곳")
    # 음량 (EBU R128 통합 라우드니스)
    if a:
        _, _, e3 = run(["ffmpeg", "-nostats", "-i", str(p), "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"])
        m = re.findall(r"I:\s+(-?[\d.]+) LUFS", e3)
        if m:
            lufs = float(m[-1])
            if not (-20 <= lufs <= -10): errs.append(f"음량 {lufs} LUFS (필요 -20~-10, 권장 -14)")
            else: notes.append(f"음량 {lufs} LUFS")
        _, _, e4 = run(["ffmpeg", "-nostats", "-i", str(p), "-af", "silencedetect=n=-50dB:d=3", "-vn", "-f", "null", "-"])
        sil = re.findall(r"silence_duration: ([\d.]+)", e4)
        if sil: errs.append(f"3초 넘는 무음 {len(sil)}곳")
    for n in notes: print("ℹ", n)
    if errs:
        for e in errs: print("✖", e)
        print(f"✖ 영상 검사 실패 ({len(errs)}건): {p.name}"); return 1
    print(f"✔ 영상 검사 통과 ({p.name} {w}x{h} {fps:.0f}fps {float(info['format']['duration']):.1f}초 / 오류 0)")
    return 0

def sheet(path, out="captures/tmp", n=12):
    p = Path(path); o = ROOT / out; o.mkdir(parents=True, exist_ok=True)
    dur = float(probe(p)["format"]["duration"]); res = []
    for i in range(n):   # 첫 3초 훅은 따로 촘촘히
        t = min(dur - 0.1, (i + 0.5) * dur / n) if i >= 3 else i * 1.0
        f = o / f"{p.stem}_{i:02d}.jpg"
        rc, _, _ = run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(p), "-frames:v", "1", "-vf", "scale=360:-2", str(f)])
        if rc == 0 and f.exists(): res.append(f)
    if res:
        tile = o / f"{p.stem}_sheet.jpg"
        run(["ffmpeg", "-y", "-v", "error", "-pattern_type", "glob", "-i", str(o / f"{p.stem}_[0-9][0-9].jpg"),
             "-vf", f"tile=6x{(len(res)+5)//6}", str(tile)])
        print(f"✔ 눈 검사용 프레임 {len(res)}장 → {tile} (이 그림을 Read 로 열어야 3층 통과)"); return 0
    print("✖ 프레임을 못 뽑음"); return 1

# ───────── 자가 시험 ─────────
def selftest():
    if not shutil.which("ffmpeg"): print("✖ ffmpeg 없음 — 시험 못 함"); return 1
    d = Path(tempfile.mkdtemp()); ok = True
    def mk(name, vf, af, dur=8, size="1080x1920"):
        f = d / name
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"{vf}=s={size}:r=30:d={dur}" if vf != "testsrc2" else f"testsrc2=s={size}:r=30:d={dur}",
             *(["-f", "lavfi", "-i", af] if af else []), "-t", str(dur), "-pix_fmt", "yuv420p", "-c:v", "libx264", *(["-c:a", "aac"] if af else []), str(f)])
        return f
    good = mk("good.mp4", "testsrc2", "sine=f=220:d=8,volume=2.5")
    black = mk("black.mp4", "color=c=black", "sine=f=220:d=8,volume=2.5") if False else None
    noaud = mk("noaudio.mp4", "testsrc2", None)
    small = mk("small.mp4", "testsrc2", "sine=f=220:d=8,volume=2.5", size="640x360")
    cases = [("정상 영상은 통과", good, 0), ("오디오 없으면 실패", noaud, 1), ("해상도 틀리면 실패", small, 1)]
    import io, contextlib
    for name, f, want in cases:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf): rc = check_clip(f)
        good_case = (rc == want); ok &= good_case
        print(("✔" if good_case else "✖"), "역검증:", name, "→", buf.getvalue().strip().splitlines()[-1])
    print("✔ 자가 시험 통과" if ok else "✖ 자가 시험 실패"); return 0 if ok else 1

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(2)
    if a[0] == "check": sys.exit(check_data("--staged" in a, "--quiet" in a))
    if a[0] == "clip":
        spec = a[a.index("--spec") + 1] if "--spec" in a else "shorts"
        sys.exit(check_clip(a[1], spec))
    if a[0] == "sheet":
        n = int(a[a.index("--n") + 1]) if "--n" in a else 12
        out = a[a.index("--out") + 1] if "--out" in a else "captures/tmp"
        sys.exit(sheet(a[1], out, n))
    if a[0] == "selftest": sys.exit(selftest())
    print(__doc__); sys.exit(2)
