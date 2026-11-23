#!/usr/bin/env python3
"""감독 세션 교대 장치 (키트 v3.1.2).

감독 대화가 길어지면 턴마다 그 긴 대화를 통째로 다시 읽어 토큰이 갈려 나간다.
그래서 일정 크기를 넘으면 docs/HANDOFF.md(인수인계서)에 적고 새 세션으로 넘어가게 한다.

  prompt   UserPromptSubmit 훅. 이 대화의 크기(마지막 응답의 입력 토큰)가 한도를 넘으면 교대 지시를 붙인다.
  start    SessionStart 훅. 인수인계서가 '상태: 넘김' 이면 새 세션에게 먼저 읽으라고 붙인다.
  selftest 자체 시험.

루프 일꾼(LOOP_LAP 있음)에게는 아무것도 하지 않는다. 어떤 오류가 나도 조용히 0 으로 끝난다 (대화를 막지 않음).
한도: 환경변수 DIRECTOR_HANDOFF_TOKENS > loop/env.sh 의 DIRECTOR_HANDOFF_TOKENS > 기본 100000.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDOFF = os.path.join(ROOT, "docs", "HANDOFF.md")
DEFAULT_LIMIT = 100000
TAIL_BYTES = 4 * 1024 * 1024


def limit_tokens(root=ROOT):
    v = os.environ.get("DIRECTOR_HANDOFF_TOKENS", "").strip()
    if not v:
        try:
            with open(os.path.join(root, "loop", "env.sh"), encoding="utf-8") as f:
                m = re.search(r'^\s*(?:export\s+)?DIRECTOR_HANDOFF_TOKENS="?(\d+)', f.read(), re.M)
                v = m.group(1) if m else ""
        except OSError:
            v = ""
    return int(v) if v.isdigit() and int(v) > 0 else DEFAULT_LIMIT


def context_tokens(transcript_path):
    """대화 파일 끝에서부터 마지막 assistant 응답의 usage 를 찾아 지금 대화 크기를 돌려준다."""
    try:
        with open(transcript_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - TAIL_BYTES))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return 0
    for line in reversed(lines):
        if '"usage"' not in line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        msg = rec.get("message") if isinstance(rec, dict) else None
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        u = msg.get("usage") or {}
        total = sum(int(u.get(k) or 0) for k in
                    ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
        if total:
            return total
    return 0


def handoff_state(path=HANDOFF):
    try:
        with open(path, encoding="utf-8") as f:
            head = f.read(2000)
    except OSError:
        return ""
    m = re.search(r"상태:\s*(넘김|받음)", head)
    return m.group(1) if m else ""


PROMPT_MSG = (
    "[감독 교대] 이 감독 대화가 약 {k}k 토큰으로 커졌다 (한도 {lim}k). 턴마다 이 대화 전체를 다시 읽어 비싸다. "
    "지금 질문에 답한 뒤 같은 턴에서 교대한다 (loop/DIRECTOR.md '세션 교대' 절): "
    "① docs/HANDOFF.md 를 덮어써 '상태: 넘김' 과 6칸을 채우고 그 파일만 커밋 "
    "② 새 세션을 여는 도구가 있으면 'docs/HANDOFF.md 를 읽고 감독을 이어가' 로 새 세션을 열고, 없으면 사람에게 "
    "'새 세션을 열고 「HANDOFF 읽고 감독 이어가」 라고 입력해 주세요' 한 줄을 알린다 "
    "③ 이 세션에서는 새 일을 시작하지 않는다."
)
START_MSG = (
    "[감독 인수] docs/HANDOFF.md 가 '상태: 넘김' 이다. 감독 세션이라면 다른 일보다 먼저 그 파일을 읽고, "
    "적힌 '다음에 할 일' 부터 잇는다. 읽은 뒤 첫 줄 상태를 '받음 (날짜)' 로 바꾸고 그 파일만 커밋한다."
)


def emit(event, text):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}},
                     ensure_ascii=False))


def run(mode, stdin_text):
    if os.environ.get("LOOP_LAP"):
        return None
    if mode == "start":
        return ("SessionStart", START_MSG) if handoff_state() == "넘김" else None
    try:
        data = json.loads(stdin_text or "{}")
    except ValueError:
        return None
    tp = data.get("transcript_path") if isinstance(data, dict) else None
    if not tp:
        return None
    used, lim = context_tokens(tp), limit_tokens()
    if used >= lim:
        return ("UserPromptSubmit", PROMPT_MSG.format(k=used // 1000, lim=lim // 1000))
    return None


def selftest():
    import tempfile
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("  ok  " if cond else "  FAIL ") + name)
        ok = ok and cond

    d = tempfile.mkdtemp()
    tp = os.path.join(d, "t.jsonl")
    big = {"type": "assistant", "message": {"role": "assistant", "usage": {
        "input_tokens": 10, "cache_read_input_tokens": 150000, "cache_creation_input_tokens": 500}}}
    small = {"type": "assistant", "message": {"role": "assistant", "usage": {"input_tokens": 3000}}}
    with open(tp, "w", encoding="utf-8") as f:
        f.write(json.dumps(small) + "\n" + "깨진 줄 \"usage\"\n" + json.dumps(big) + "\n"
                + json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}}) + "\n")
    check("마지막 assistant usage 합산", context_tokens(tp) == 150510)
    check("없는 파일은 0", context_tokens(os.path.join(d, "none.jsonl")) == 0)
    stdin = json.dumps({"transcript_path": tp})
    saved = {k: os.environ.pop(k, None) for k in ("LOOP_LAP", "DIRECTOR_HANDOFF_TOKENS")}
    try:
        os.environ["DIRECTOR_HANDOFF_TOKENS"] = "120000"
        r = run("prompt", stdin)
        check("한도 넘으면 교대 지시", bool(r) and r[0] == "UserPromptSubmit" and "HANDOFF" in r[1])
        os.environ["DIRECTOR_HANDOFF_TOKENS"] = "200000"
        check("한도 안이면 조용", run("prompt", stdin) is None)
        del os.environ["DIRECTOR_HANDOFF_TOKENS"]
        os.environ["LOOP_LAP"] = "7"
        check("루프 일꾼에겐 조용", run("prompt", stdin) is None)
        del os.environ["LOOP_LAP"]
        check("깨진 입력도 조용", run("prompt", "not json") is None)
        envd = os.path.join(d, "loop")
        os.makedirs(envd)
        with open(os.path.join(envd, "env.sh"), "w", encoding="utf-8") as f:
            f.write('DIRECTOR_HANDOFF_TOKENS="90000"   # 감독 교대 한도\n')
        check("env.sh 한도 읽기", limit_tokens(d) == 90000)
        check("기본 한도", limit_tokens(os.path.join(d, "x")) == DEFAULT_LIMIT)
        hp = os.path.join(d, "H.md")
        with open(hp, "w", encoding="utf-8") as f:
            f.write("# 인수인계서\n상태: 넘김 (2026-11-21 14:00)\n")
        check("상태 넘김 읽기", handoff_state(hp) == "넘김")
        with open(hp, "w", encoding="utf-8") as f:
            f.write("# 인수인계서\n상태: 받음 (2026-11-21)\n")
        check("상태 받음 읽기", handoff_state(hp) == "받음")
    finally:
        os.environ.pop("DIRECTOR_HANDOFF_TOKENS", None)
        os.environ.pop("LOOP_LAP", None)
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v
    print("SELFTEST_OK" if ok else "SELFTEST_FAIL")
    return 0 if ok else 1


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "prompt"
    if mode == "selftest":
        return selftest()
    try:
        stdin_text = sys.stdin.read() if mode == "prompt" else ""
        r = run(mode, stdin_text)
        if r:
            emit(*r)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
