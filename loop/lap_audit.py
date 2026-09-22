#!/usr/bin/env python3
"""바퀴 기록 감사 — loop.sh 가 바퀴마다 부른다. 표준 라이브러리만.

  render <lap.jsonl>            일꾼의 최종 답 + 실행한 명령 목록을 사람이 읽을 글로 출력
  check  <lap.jsonl> <pre-sha>  이번 바퀴가 STATUS 에 적은 "통과(`인용`)" 이 실제 도구 출력에 있는지 대조.
                                없으면 사유를 출력하고 종료코드 1 (loop.sh 가 alerts.log 에 올림)
  selftest                      내장 자료로 render/check 동작 확인 (SELFTEST_OK)

왜: `--output-format text` 로는 최종 답만 남아 "정말 명령을 돌렸나"를 아무도 대조할 수 없었다.
stream-json 을 남기면 도구 호출·결과가 전부 있으니 인용을 기계로 대조한다 (Verification.md 1).
"""
import json
import re
import subprocess
import sys

PASS_RE = re.compile(r"통과\(`([^`]+)`\)")


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


def selftest():
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
    elif a[:1] == ["selftest"]:
        selftest()
    else:
        print(__doc__)
        sys.exit(2)
