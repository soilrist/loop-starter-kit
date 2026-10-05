#!/usr/bin/env python3
"""바퀴 기록 감사 — loop.sh 가 바퀴마다 부른다. 표준 라이브러리만.

  render <lap.jsonl>            일꾼의 최종 답 + 실행한 명령 목록을 사람이 읽을 글로 출력
  check  <lap.jsonl> <pre-sha>  이번 바퀴가 STATUS 에 적은 "통과(`인용`)" 이 실제 도구 출력에 있는지 대조.
                                없으면 사유를 출력하고 종료코드 1 (loop.sh 가 alerts.log 에 올림)
  usage  <lap.jsonl>            이번 바퀴의 `턴,새입력토큰,출력토큰,캐시읽기토큰,추정비용` 한 줄 (loop.sh 가 usage.csv 에 붙임).
                                기록이 없으면 빈 칸 `,,,,` — 항상 종료코드 0
  report [usage.csv] [바퀴수]   최근 바퀴(기본 20)의 "일한 바퀴 하나당" 턴·토큰·추정비용, 헛바퀴가 쓴 몫,
                                모델·노력 단계별 비교를 사람이 읽을 글로 출력 (`loop/ctl.sh cost`)
  selftest                      내장 자료로 render/check/usage/report 동작 확인 (SELFTEST_OK)

왜: `--output-format text` 로는 최종 답만 남아 "정말 명령을 돌렸나"를 아무도 대조할 수 없었다.
stream-json 을 남기면 도구 호출·결과가 전부 있으니 인용을 기계로 대조한다 (Verification.md 1).
같은 기록의 마지막 `result` 줄에 턴 수·토큰·추정비용이 있다 — 설정을 바꾼 게 나아졌는지 감이 아니라 숫자로 본다.
추정비용은 API 값으로 환산한 것이라 구독 계정의 실제 청구액이 아니다. 전후 비교용으로만 쓴다.
"""
import csv
import json
import re
import subprocess
import sys

PASS_RE = re.compile(r"통과\(`([^`]+)`\)")
USAGE_COLS = ("turns", "in_tok", "out_tok", "cache_read", "cost_usd")


def _events(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


def _content_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


def parse(path):
    """→ (최종 답, [명령 문자열], 도구 출력 전체 문자열)"""
    final, cmds, outputs = "", [], []
    for ev in _events(path):
        t = ev.get("type")
        if t == "assistant":
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "tool_use":
                    inp = b.get("input") or {}
                    cmds.append(inp.get("command") or inp.get("file_path") or inp.get("pattern") or b.get("name", "?"))
        elif t == "user":
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "tool_result":
                    outputs.append(_content_text(b.get("content")))
        elif t == "result":
            final = str(ev.get("result") or "")
    return final, cmds, "\n".join(outputs)


def _squash(s):
    return re.sub(r"\s+", " ", s).strip()


def render(path):
    final, cmds, _ = parse(path)
    print("## 최종 답")
    print(final or "(없음)")
    print(f"\n## 실행한 도구 호출 ({len(cmds)}개)")
    for c in cmds:
        print("$ " + _squash(str(c))[:200])


def status_added_lines(pre_sha):
    diff = subprocess.run(
        ["git", "diff", f"{pre_sha}..HEAD", "--", "docs/STATUS.md"],
        capture_output=True, text=True,
    ).stdout
    return [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]


def check_quotes(lines, tool_output):
    """STATUS 에 새로 적힌 통과 인용 중 도구 출력에 없는 것 → 목록"""
    hay = _squash(tool_output)
    missing = []
    for l in lines:
        for q in PASS_RE.findall(l):
            if _squash(q) not in hay:
                missing.append(q)
    return missing


def check(path, pre_sha):
    _, cmds, out = parse(path)
    lines = status_added_lines(pre_sha)
    quotes = sum(len(PASS_RE.findall(l)) for l in lines)
    if quotes and not cmds:
        print(f"통과 인용 {quotes}개인데 도구 호출 기록이 0개 (jsonl 비었음?)")
        return 1
    missing = check_quotes(lines, out)
    if missing:
        print("STATUS 의 통과 인용이 실제 도구 출력에 없음: " + " | ".join(m[:60] for m in missing))
        return 1
    print(f"인용 {quotes}개 전부 도구 출력과 일치")
    return 0


def usage_fields(events):
    """마지막 result 줄 → (턴, 새 입력 토큰, 출력 토큰, 캐시 읽기 토큰, 추정비용). 없으면 전부 빈 문자열."""
    last = None
    for ev in events:
        if ev.get("type") == "result":
            last = ev
    if last is None:
        return ("", "", "", "", "")
    u = last.get("usage") or {}

    def num(v):
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0

    fresh = num(u.get("input_tokens")) + num(u.get("cache_creation_input_tokens"))
    cost = last.get("total_cost_usd")
    return (
        str(num(last.get("num_turns"))),
        str(fresh),
        str(num(u.get("output_tokens"))),
        str(num(u.get("cache_read_input_tokens"))),
        f"{cost:.4f}" if isinstance(cost, (int, float)) and not isinstance(cost, bool) else "",
    )


def usage(path):
    try:
        fields = usage_fields(_events(path))
    except OSError:
        fields = ("", "", "", "", "")
    print(",".join(fields))


def _f(row, key):
    try:
        return float(row.get(key) or "")
    except (TypeError, ValueError):
        return None


def _work(row):
    """commits 칸은 `전체/일한` — 일한 커밋 수"""
    try:
        return int(str(row.get("commits") or "0/0").split("/")[-1])
    except ValueError:
        return 0


def _avg(rows, key):
    vals = [v for v in (_f(r, key) for r in rows) if v is not None]
    return sum(vals) / len(vals) if vals else None


def _fmt(v, unit="", digits=0):
    return "?" if v is None else f"{v:,.{digits}f}{unit}"


def report_lines(rows, last_n=20):
    rows = [r for r in rows if (r.get("account") or "") != "dry"][-last_n:]
    if not rows:
        return ["기록된 바퀴가 없음"]
    measured = [r for r in rows if _f(r, "turns") is not None]
    worked = [r for r in measured if _work(r) > 0]
    idle = [r for r in measured if _work(r) == 0]
    out = [f"최근 {len(rows)}바퀴 (측정값 있는 바퀴 {len(measured)}개 · 일한 바퀴 {len(worked)}개 · 헛바퀴 {len(idle)}개)"]
    if not measured:
        out.append("턴·토큰 측정값이 아직 없음 — 키트 v2.3 이후 바퀴부터 쌓인다")
        return out
    out.append(
        "일한 바퀴 하나당: 턴 " + _fmt(_avg(worked, "turns"), "", 1)
        + " · 출력 " + _fmt(_avg(worked, "out_tok"), " 토큰")
        + " · 새 입력 " + _fmt(_avg(worked, "in_tok"), " 토큰")
        + " · 추정 $" + _fmt(_avg(worked, "cost_usd"), "", 2)
    )
    total = sum(v for v in (_f(r, "cost_usd") for r in measured) if v is not None)
    wasted = sum(v for v in (_f(r, "cost_usd") for r in idle) if v is not None)
    if total > 0:
        out.append(f"헛바퀴가 쓴 몫: 추정 ${wasted:,.2f} / ${total:,.2f} ({wasted / total * 100:.0f}%)")
    groups = {}
    for r in worked:
        groups.setdefault(((r.get("model") or "?"), (r.get("effort") or "기본")), []).append(r)
    if len(groups) > 1:
        out.append("설정별 (일한 바퀴만 — 바퀴 수가 5개 미만이면 믿지 말 것):")
        for (model, effort), rs in sorted(groups.items()):
            out.append(
                f"  {model} / 노력 {effort}: {len(rs)}바퀴 · 턴 " + _fmt(_avg(rs, "turns"), "", 1)
                + " · 추정 $" + _fmt(_avg(rs, "cost_usd"), "", 2)
            )
    out.append("추정비용은 API 값 환산 — 구독 계정의 청구액이 아니라 전후 비교용")
    return out


def report(path="logs/usage.csv", last_n=20):
    try:
        with open(path, encoding="utf-8", errors="replace", newline="") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        print(f"{path} 를 못 읽음 — 루프가 한 바퀴도 안 돌았거나 경로가 다름")
        return 1
    print("\n".join(report_lines(rows, last_n)))
    return 0


def selftest():
    res = {"type": "result", "num_turns": 12, "total_cost_usd": 0.51234,
           "usage": {"input_tokens": 100, "cache_creation_input_tokens": 900,
                     "cache_read_input_tokens": 50000, "output_tokens": 4000}}
    assert usage_fields([{"type": "assistant"}, res]) == ("12", "1000", "4000", "50000", "0.5123"), "usage 칸 계산이 틀림"
    assert usage_fields([{"type": "assistant"}]) == ("", "", "", "", ""), "result 없는 기록에 값을 지어냄"
    assert usage_fields([{"type": "result"}]) == ("0", "0", "0", "0", ""), "빈 result 처리"
    rows = [
        {"account": "dry", "commits": "0/0"},
        {"account": "nc", "model": "sonnet", "commits": "2/1", "effort": "medium", "turns": "20", "in_tok": "1000", "out_tok": "5000", "cost_usd": "1.00"},
        {"account": "nc", "model": "sonnet", "commits": "1/0", "effort": "high", "turns": "30", "in_tok": "1000", "out_tok": "9000", "cost_usd": "3.00"},
        {"account": "nc", "model": "sonnet", "commits": "1/1"},
    ]
    rep = "\n".join(report_lines(rows))
    assert "최근 3바퀴 (측정값 있는 바퀴 2개 · 일한 바퀴 1개 · 헛바퀴 1개)" in rep, rep
    assert "턴 20.0" in rep and "$1.00" in rep, rep
    assert "$3.00 / $4.00 (75%)" in rep, rep
    assert report_lines([{"account": "dry"}]) == ["기록된 바퀴가 없음"]
    out = "✔ 규칙 검사 통과 (경고 0 / 미정 숫자 0)\nPassed: 3, Failed: 0"
    ok = ["검사: 1층 통과(`✔ 규칙 검사 통과 (경고 0 / 미정 숫자 0)`) / 2층 통과(`Passed: 3, Failed: 0`)"]
    bad = ["검사: 1층 통과(`✔ 규칙 검사 통과 (경고 1)`)"]
    assert check_quotes(ok, out) == [], "일치하는 인용을 놓침"
    assert check_quotes(bad, out) == ["✔ 규칙 검사 통과 (경고 1)"], "없는 인용을 통과시킴"
    assert check_quotes(["검사: 3층 못 함(에디터 꺼짐)"], "") == [], "인용 없는 줄을 지적함"
    assert _content_text([{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]) == "a\nb"
    print("SELFTEST_OK")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["render"] and len(a) == 2:
        render(a[1])
    elif a[:1] == ["check"] and len(a) == 3:
        sys.exit(check(a[1], a[2]))
    elif a[:1] == ["usage"] and len(a) == 2:
        usage(a[1])
    elif a[:1] == ["report"] and len(a) <= 3:
        sys.exit(report(a[1] if len(a) > 1 else "logs/usage.csv", int(a[2]) if len(a) > 2 and a[2].isdigit() else 20))
    elif a[:1] == ["selftest"]:
        selftest()
    else:
        print(__doc__)
        sys.exit(2)
