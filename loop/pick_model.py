#!/usr/bin/env python3
"""이번 바퀴에 쓸 모델을 고른다 (loop.sh 가 LOOP_MODEL="auto" 일 때 부른다). 출력: haiku / sonnet / opus / fable 한 단어.

고르는 순서 (loop/PROMPT.md ④ 와 같은 순서로 "이번 바퀴 할 일"을 추측한다):
  1. INBOX 에 루프가 처리할 항목(결함·지시·답·보정·철회)이 있으면 그 줄
  2. 없으면 ROADMAP 의 첫 `- [ ]` 조각 (〔진행 중〕 표시는 건너뜀)
  3. 그 줄에 〔모델: haiku|sonnet|opus|fable〕 가 있으면 그대로, 없으면 아래 낱말 표로
  4. 직전 바퀴들이 일한 커밋 없이 끝났으면(헛바퀴 수 = 인자 1) 2번부터 한 단계 올린다

등급: 평소 = 기본 모델(sonnet) · 제일 어려운 일(돈·권한·설계) = fable · opus 는 과부하 때 대체 + 막혔을 때 중간 단계.
왜: 단순 조각까지 같은 모델로 돌리면 비싸고, 위험한 조각을 싼 모델로 돌리면 다시 하느라 더 든다.
프로젝트 낱말: loop/model_words.txt 가 있으면 더한다 (한 줄에 `fable: 낱말, 낱말` · `opus: 낱말` · `haiku: 낱말`, # 은 주석).
쓰는 법: python3 loop/pick_model.py <헛바퀴 수> [기본 모델]   ·   --selftest   ·   --has-work (루프가 할 줄이 있으면 1, 없으면 0)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIERS = ["haiku", "sonnet", "opus", "fable"]

# 돈·권한·데이터 구조처럼 틀리면 되돌리기 어려운 일, 방향을 정하는 일 → 제일 좋은 모델
HARD_WORDS = ["결제", "정산", "환불", "권한", "보안", "암호화", "인증", "마이그레이션", "스키마",
              "설계", "아키텍처", "멱등", "동시성", "세이브 형식", "계획 바퀴", "원인 모름"]
# 손이 정해진 단순 작업 → 싼 모델
HAIKU_WORDS = [".gitignore", "주석", "README", "CHANGELOG", "오타", "이름 바꾸기", "문구 수정", "문서 정리"]

TAG_RE = re.compile(r"〔모델:\s*(haiku|sonnet|opus|fable)\s*〕")
INBOX_RE = re.compile(r"^- \[ \] (결함|지시|답|보정|철회)\(")


def load_words(text: str):
    """model_words.txt 내용을 (opus 낱말, haiku 낱말, fable 낱말) 로."""
    extra = {"opus": [], "haiku": [], "fable": []}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        tier, words = line.split(":", 1)
        tier = tier.strip().lower()
        if tier in extra:
            extra[tier] += [w.strip() for w in words.split(",") if w.strip()]
    return extra["opus"], extra["haiku"], extra["fable"]


def next_task(inbox: str, roadmap: str) -> str:
    for line in inbox.splitlines():
        if INBOX_RE.match(line):
            return line
    for line in roadmap.splitlines():
        if line.startswith("- [ ]") and "진행 중" not in line:
            return line
    return "계획 바퀴"  # ROADMAP 이 비면 계획 바퀴


def pick(task: str, idle: int, default: str = "sonnet", opus_extra=(), haiku_extra=(), fable_extra=()) -> str:
    m = TAG_RE.search(task)
    if m:
        base = m.group(1)
    elif any(w in task for w in list(HARD_WORDS) + list(fable_extra)):
        base = "fable"
    elif any(w in task for w in opus_extra):
        base = "opus"
    elif any(w in task for w in list(HAIKU_WORDS) + list(haiku_extra)):
        base = "haiku"
    else:
        base = default
    if idle >= 2:  # 같은 일 2번 막힘 → 한 단계 위로 (노력 단계 올리기는 loop.sh 가 1번째부터)
        base = TIERS[min(TIERS.index(base) + 1, len(TIERS) - 1)]
    return base


def read(rel: str) -> str:
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def selftest() -> int:
    o, h, f = load_words("# 프로젝트 낱말\nopus: 토스, RLS\nhaiku: 셀렉터 수정\nfable: 밸런스 공식\n엉뚱한 줄\n")
    cases = [
        (pick("- [ ] M0-09 `.gitignore` 에 logs/ 추가", 0), "haiku"),
        (pick("- [ ] M4-02 결제 승인", 0), "fable"),
        (pick("- [ ] M1-05 목록 화면 입력", 0), "sonnet"),
        (pick("- [ ] M1-05 입력 〔모델: opus〕", 0), "opus"),
        (pick("- [ ] M4-02 결제 〔모델: haiku〕", 0), "haiku"),
        (pick("- [ ] M0-09 `.gitignore`", 2), "sonnet"),
        (pick("- [ ] M4-02 결제", 3), "fable"),
        (pick("- [ ] M1-05 입력", 2), "opus"),
        (pick("- [ ] M1-05 입력 〔모델: fable〕", 0), "fable"),
        (pick("- [ ] M3-01 밸런스 공식", 0, "sonnet", o, h, f), "fable"),
        (pick("- [ ] M1-05 입력", 0, "haiku"), "haiku"),
        (pick("- [ ] M4-03 토스 승인", 0), "sonnet"),
        (pick("- [ ] M4-03 토스 승인", 0, "sonnet", o, h), "opus"),
        (pick("- [ ] M2-01 셀렉터 수정", 0, "sonnet", o, h), "haiku"),
        ((o, h, f), (["토스", "RLS"], ["셀렉터 수정"], ["밸런스 공식"])),
        (next_task("- [ ] 보류(감독, 2026) x\n- [ ] 지시(감독, 2026) **y**", "- [ ] M0-01"), "- [ ] 지시(감독, 2026) **y**"),
        (next_task("", "- [ ] M0-04 a 〔진행 중: 다른 작업자〕\n- [ ] M0-05 b"), "- [ ] M0-05 b"),
        (next_task("", "- [x] M0-01"), "계획 바퀴"),
    ]
    bad = [(got, want) for got, want in cases if got != want]
    for got, want in bad:
        print(f"실패: {got!r} != {want!r}")
    print(f"selftest {len(cases) - len(bad)}/{len(cases)} 통과")
    return 1 if bad else 0


def main() -> int:
    if sys.argv[1:2] == ["--selftest"]:
        return selftest()
    if sys.argv[1:2] == ["--has-work"]:
        print(0 if next_task(read("docs/feedback/INBOX.md"), read("docs/ROADMAP.md")) == "계획 바퀴" else 1)
        return 0
    try:
        idle = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    except ValueError:
        idle = 0
    default = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] in TIERS else "sonnet"
    o, h, f = load_words(read("loop/model_words.txt"))
    task = next_task(read("docs/feedback/INBOX.md"), read("docs/ROADMAP.md"))
    print(pick(task, idle, default, o, h, f))
    return 0


if __name__ == "__main__":
    sys.exit(main())
