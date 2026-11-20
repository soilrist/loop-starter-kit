#!/usr/bin/env python3
"""바퀴 기록 감사 — loop.sh 가 바퀴마다 부른다. 표준 라이브러리만.

  render <lap.jsonl>            일꾼의 최종 답 + 실행한 명령 목록을 사람이 읽을 글로 출력
  check  <lap.jsonl> <pre-sha> [루트 바퀴]  이번 바퀴가 STATUS 에 적은 "통과(`인용`)" 이 실제 실행 출력에 있고
                                일꾼이 직접 쓴 글(echo·파일 쓰기)이 아닌지, "3층 통과" 가 적은 그림을 실제로 열었는지 대조.
                                아니면 사유를 출력하고 종료코드 1. 루트를 주면 INBOX 맨 위에 `결함` 도 올린다
  usage  <lap.jsonl>            이번 바퀴의 `턴,새입력토큰,출력토큰,캐시읽기토큰,추정비용` 한 줄 (loop.sh 가 usage.csv 에 붙임).
                                기록이 없으면 빈 칸 `,,,,` — 항상 종료코드 0
  report [usage.csv] [바퀴수]   최근 바퀴(기본 20)의 "일한 바퀴 하나당" 턴·토큰·추정비용, 헛바퀴가 쓴 몫,
                                모델·노력 단계별 비교를 사람이 읽을 글로 출력 (`loop/ctl.sh cost`)
  context <lap.jsonl>           이번 바퀴에서 모델이 호출마다 받은 컨텍스트 한 줄: `첫호출,최대,호출수,입력합,출력합`
                                (loop.sh 가 logs/context.csv 에 붙임 — 가벼운 바퀴가 실제로 줄였는지 재는 숫자)
  ctxreport [context.csv] [바퀴수]  최근 바퀴의 시작·최대 컨텍스트 평균 한 줄 (`loop/ctl.sh cost` 끝에 붙음)
  size   [루트]                 매 바퀴 다시 읽히는 문서가 불었는지: STATUS "지금 상태" 줄 수 · STATUS 전체 줄 수 ·
                                INBOX 글자 수와 종류별 개수. 한도를 넘으면 사유를 출력하고 종료코드 1
  tidy   [루트] [--dry]         STATUS 의 오래된 바퀴 기록과 "지금 상태"에서 넘친 항목을 docs/archive/ 로 옮김
                                (글자 하나도 버리지 않음 · 커밋은 감독이 — `loop/ctl.sh tidy`)
  statelines                    표준입력으로 받은 STATUS 의 "지금 상태" 줄 수 (커밋 훅이 씀)
  selftest                      내장 자료로 render/check/usage/context/report/size/tidy 동작 확인 (SELFTEST_OK)

왜: `--output-format text` 로는 최종 답만 남아 "정말 명령을 돌렸나"를 아무도 대조할 수 없었다.
stream-json 을 남기면 도구 호출·결과가 전부 있으니 인용을 기계로 대조한다 (Verification.md 1).
같은 기록의 마지막 `result` 줄에 턴 수·토큰·추정비용이 있다 — 설정을 바꾼 게 나아졌는지 감이 아니라 숫자로 본다.
추정비용은 API 값으로 환산한 것이라 구독 계정의 실제 청구액이 아니다. 전후 비교용으로만 쓴다.
"""
import contextlib
import csv
import datetime
import io
import json
import os
import re
import shutil
import shlex
import subprocess
import sys

PASS_RE = re.compile(r"통과\s*\(`([^`]+)`[^)\n]*\)")   # 인용 뒤 `, jev SUPPORTED 0.79` 같은 덧말 허용
# 1·2층 통과인데 인용이 없음 — `통과(jev 미확인)`·`1층: 통과`·`L1 합격`·`1층 pass` 같은 변형 포함
BARE_RE = re.compile(r"(?:[12]\s*층|\bL[12]|(?<!3층 )(?<!3층)검사)[^`\n(]{0,8}?(?:통과|합격|성공|정상|완료|이상\s*없음|pass(?:ed)?\b|ok\b|✔|✓)(?!\s*\(`)", re.I)
TRAILER_RE = re.compile(r"^Checks: L1 (\S+), L2 (\S+), L3 (\S+)", re.M)
# 일꾼이 고치면 안 되는 키트 파일 — 고치면 판별·감사·훅을 스스로 끌 수 있다 (tools/ 의 다른 스크립트는 일꾼 몫)
GUARD_RE = re.compile(r"^(loop/(?!(STOP|WRAPUP|HOLD)$)|\.githooks/|docs/conventions/|tools/(check_conventions\.py|jev\.py|skills\.sh)$|CLAUDE\.md$|\.claude/(settings|agents/|skills/))")
# 훅·판별을 피하는 명령 — 훅은 일꾼 손 안에서 돌아서 끌 수 있으니, 끈 흔적을 바퀴 뒤에 기록에서 찾는다
# 따옴표 속 글(grep 'git push' 같은 찾기)은 지우고 본다 · 조회(git config core.hooksPath 값 없이)는 허용
BYPASS_RE = re.compile(
    r"env\s+(-\S+\s+)*-u\s*LOOP_LAP|unset\s+LOOP_LAP|(^|[;&|(]\s*|export\s+|env\s+(-\S+\s+)*)LOOP_LAP=|--no-verif"
    r"|\bgit\b[^;&|\n]*\bcommit\b[^;&|\n]*\s-[a-zA-Z]*n|core\.hookspath\s*=|--unset\S*\s+core\.hookspath"
    r"|config\s+(set\s+)?(--(global|local|system)\s+)?core\.hookspath\s+\S|GIT_CONFIG_\w*=|-u\s*GIT_CONFIG|protocol\.allow"
    r"|write-tree|commit-tree|update-ref|hook\.log|LOOP_HOOK_RECEIPT|\bgh\s+(api|pr|repo|release|issue|gist)\b|skills\.sh\b[^;&|\n]*(paid|\$|\b(on|off)\b)|\bln\s[^;&|\n]*\.claude/skills|\bgit\s+(-\S+\s+(\S+\s+)?)*push\b", re.I | re.M)
# 따옴표를 지우면 안 되는 꼴 — 셸에 다시 넘기는 글(bash -c '…'·eval) · 따옴표로 감싼 --no-verify
RAW_BYPASS_RE = re.compile(r"\bgit\b[^;&|\n]*\bcommit\b[^\n]*['\"]--no-verif", re.I)
SHELL_AGAIN_RE = re.compile(r"\b(ba|z)?sh\s+-\w*c\b|\beval\b|\bxargs\b")
# 파일에 쓰는 heredoc 본문(cat <<EOF > x)은 글이지 명령이 아니다 — 셸·파이썬에 넘기는 heredoc 은 그대로 본다
HEREDOC_RE = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?^\s*\1\s*$", re.S | re.M)
QUOTED_RE = re.compile(r"'[^']*'|\"(?:[^\"\\]|\\.)*\"")
# 이 명령의 출력은 인용 근거가 못 된다 — 일꾼이 찍은 글(echo·printf·heredoc), 판정기 jev(입력을 되풀이), 옛 기록 읽기
NOT_EVIDENCE_RE = re.compile(r"^\s*(echo|printf|cat\s*<<)|tools/jev\.py|STATUS\.md|docs/(archive|feedback)/"
                             r"|\b(python[0-9.]*\s+(-\w+\s+)*-c|node\s+(-\w+\s+)*-[ep]|perl\s+(-\w+\s+)*-\w*e|ruby\s+-\w*e)\b"
                             r"|\b(cat|grep|rg|head|tail|less|sed|awk)\b[^|;&\n]*\blogs/(lap-|loop|alerts|tidy|usage)"
                             r"|\bgit\s+(log|show|diff)\b|\b(grep|rg|cat|head|tail|sed|awk|less)\b[^|;&\n]*\bdocs/")
# 일꾼 환경에서 지울 비밀 변수 이름 — 목록이 아니라 꼴 (FAL_KEY·GITHUB_PAT·AWS_ACCESS_KEY_ID 처럼 API_ 가 없는 것까지)
# 남기는 것: 구독 로그인(CLAUDE_CODE_OAUTH_TOKEN) · 판정기 jev 의 키(TYPESAFE_API_KEY — 지우면 jev 가 늘 UNAVAILABLE)
SECRET_RE = re.compile(r"(^|_)(KEY|TOKEN|SECRET|PAT|PASSWORD|PASSWD|APIKEY|CREDENTIALS?)(_|$)", re.I)
SECRET_KEEP = ("CLAUDE_CODE_OAUTH_TOKEN", "TYPESAFE_API_KEY")


def secret_names(names):
    return [n for n in names if re.fullmatch(r"[A-Za-z_]\w*", n) and SECRET_RE.search(n) and n not in SECRET_KEEP]


MIN_QUOTE = 8          # 압축 후 글자 수 — `통과(\`0\`)` 같은 아무 데나 있는 조각을 막는다
EYE_PASS_RE = re.compile(r"3층\s*통과")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
USAGE_COLS = ("turns", "in_tok", "out_tok", "cache_read", "cost_usd")

# 매 바퀴 다시 읽히는 문서의 한도 — 넘으면 size 가 경고, 커밋 훅은 NOW_HARD 에서 거절
NOW_KEEP = 15          # "지금 상태" 권장 줄 수 (tidy 가 이만큼만 남김)
NOW_WARN = 20          # 넘으면 경고
NOW_HARD = 25          # 루프 커밋 훅이 거절하는 줄 수
STATUS_MAX_LINES = 1200
LAPS_KEEP = 30         # tidy 가 STATUS 에 남기는 최근 바퀴 수
INBOX_MAX_CHARS = 12000
HUMAN_KINDS = ("확인", "질문", "승인")   # 루프가 처리하지 않는 종류 — 쌓이면 읽는 값만 든다
LAP_HEAD_RE = re.compile(r"^## #", re.M)   # `## #0412 …` 일꾼 바퀴, `## #감독 …` 감독이 직접 한 일
NOW_HEAD = "## 지금 상태"


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


OUT_SEP = "\n\0\n"


def _blocks(events):
    """기록 속 도구 블록 → (assistant|user, 블록) — message 가 글자이거나 content 가 목록이 아니면 건너뛴다"""
    for ev in events:
        m = ev.get("message")
        for b in (m.get("content") if isinstance(m, dict) and isinstance(m.get("content"), list) else []):
            if isinstance(b, dict):
                yield ev.get("type"), b


def parse(path):
    """→ (최종 답, [명령 문자열], 인용 근거가 되는 출력 — 일꾼이 돌린 Bash 명령의 결과만)
    Read·Grep 결과는 뺀다: 옛 STATUS 를 읽어 그 안의 옛 인용을 다시 쓰는 것을 막는다."""
    events = list(_events(path))
    final = next((str(ev.get("result") or "") for ev in reversed(events) if ev.get("type") == "result"), "")
    cmds, outputs, bash = [], [], set()
    for t, b in _blocks(events):
        if t == "assistant" and b.get("type") == "tool_use":
            inp = b.get("input") or {}
            cmds.append(inp.get("command") or inp.get("file_path") or inp.get("pattern") or b.get("name", "?"))
            if b.get("name") == "Bash" and not NOT_EVIDENCE_RE.search(str(inp.get("command") or "")):
                bash.add(b.get("id"))
        # 실패한 명령(is_error)의 출력은 통과 근거가 못 된다
        elif t == "user" and b.get("type") == "tool_result" and b.get("tool_use_id") in bash and not b.get("is_error"):
            outputs.append(_content_text(b.get("content")))
    return final, cmds, OUT_SEP.join(outputs)   # 명령마다 칸을 나눠 둔다 — 여러 줄 실패(`Passed: 3`/`Failed: 2`)를 칸 단위로 본다


def _squash(s):
    return re.sub(r"\s+", " ", s).strip()


def render(path):
    final, cmds, _ = parse(path)
    print("## 최종 답")
    print(final or "(없음)")
    print(f"\n## 실행한 도구 호출 ({len(cmds)}개)")
    for c in cmds:
        print("$ " + _squash(str(c))[:200])


def _git(*args, cwd=None):
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=cwd).stdout


def _added(pre_sha, path, cwd=None):
    """pre_sha..HEAD 동안 path 에 새로 들어간 줄"""
    return [l[1:] for l in _git("diff", f"{pre_sha}..HEAD", "--", path, cwd=cwd).splitlines()
            if l.startswith("+") and not l.startswith("+++")]


def authored_text(events):
    """이번 바퀴에 일꾼이 직접 쓴 글 — Bash 명령(커밋 제외)·Write/Edit 내용(STATUS 제외).
    인용이 여기 있으면 실행 결과가 아니라 일꾼이 만든 글이다 (`echo "Passed: 3"` · 파일에 써 두고 cat)."""
    parts = []
    for t, b in _blocks(events):
        inp = b.get("input") or {}
        if t != "assistant" or b.get("type") != "tool_use" or str(inp.get("file_path") or "").endswith("STATUS.md"):
            continue
        cmd = str(inp.get("command") or "")
        if cmd and not re.search(r"\bgit\s+commit\b|tools/jev\.py", cmd):
            parts.append(cmd)
        parts += [str(inp[k]) for k in ("content", "new_string") if inp.get(k)]
    return "\n".join(parts)


# 인용이 든 출력 줄에 실패 수가 있으면 그 줄은 통과 근거가 못 된다 — `1 failed, 3 passed` 에서 `3 passed` 만 떼어 쓰기
FAIL_LINE_RE = re.compile(r"\b[1-9]\d*\s*(failed|failures?|errors?)\b|\b(failed|failures?|errors?)\s*[:=]?\s*[1-9]|✖|(?-i:\bFAIL(ED)?\b)"
                          r"|(실패|오류|에러)\s*[:=]?\s*[1-9]|\bnot ok\b|\b[1-9]\d*\s*failing\b|^\s*fail\s+[1-9]|\berrored\b"
                          r"|no tests ran|collected 0 items|\b0 (passed|tests?)\b|\b(build|compilation) failed\b|^Traceback \(most recent", re.I | re.M)


def _plain_jev(cmd):
    """jev 를 혼자 한 번 부른 명령인가 — `jev … >/dev/null; echo '{"choice":"SUPPORTED"}'` · `KEY=bad python3 tools/jev.py` ·
    `$(…)` 처럼 판정 출력을 지어내거나 jev 를 일부러 UNAVAILABLE 로 만드는 꼴은 jev 호출로 치지 않는다"""
    if re.search(r"\$\(|`", cmd) or "\n" in QUOTED_RE.sub("''", cmd):
        return None
    try:
        lx = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lx.whitespace_split = True
        t = list(lx)
    except ValueError:
        return None
    # 해석기는 맨 python3 또는 loop.sh 가 준 LOOP_PY 만 (가짜 python 경로·다른 jev 로 cd 막기) · 인자는 주장·인용(+pass) 정확히
    py = ("python3", os.environ.get("LOOP_PY") or "python3")
    if (len(t) in (5, 6) and t[0] in py and t[1] in ("tools/jev.py", "./tools/jev.py") and t[2] == "evidence"
            and (len(t) == 5 or t[5] == "pass") and "cd" not in t and not any(x and set(x) <= set(";&|<>()") for x in t)):
        return t[3], t[4]
    return None


def _jev_choice(out):
    """jev 출력의 판정 — 마지막 JSON 줄의 choice 만 (주장·인용 글에 든 SUPPORTED 낱말에 속지 않게)"""
    for l in reversed(out.strip().splitlines()):
        try:
            d = json.loads(l)
        except ValueError:
            continue
        return str(d.get("choice", "")) if isinstance(d, dict) else ""
    return ""


def jev_calls(events):
    """이번 바퀴의 `tools/jev.py evidence` 호출 → [(명령 글, 출력)] — STATUS 의 jev 판정을 실제 실행과 대조한다"""
    cmds, out = {}, []
    for _, b in _blocks(events):
        if b.get("type") == "tool_use" and b.get("name") == "Bash":
            if j := _plain_jev(str((b.get("input") or {}).get("command") or "")):
                cmds[b.get("id")] = j[1]   # jev 에 넘긴 인용
        elif b.get("type") == "tool_result" and b.get("tool_use_id") in cmds:
            out.append((_squash(cmds[b.get("tool_use_id")]), _jev_choice(_content_text(b.get("content")))))
    return out


def check_quotes(lines, tool_output, authored="", jev=None):
    """STATUS 에 새로 적힌 통과 인용 중 도구 출력에 없거나, 일꾼이 직접 타이핑한 것, 실패 줄에서 떼어 온 것,
    jev 를 돌리지 않았거나 jev 가 SUPPORTED 라 하지 않은 것 → 목록. jev=None 이면 jev 대조는 건너뛴다 (손으로 부를 때)"""
    hay, typed = _squash(tool_output), _squash(authored)
    # jev 에 넘긴 인용도 실제 출력 안에 있어야 한다 — 지어낸 글로 SUPPORTED 를 받아 오지 못하게
    jev = None if jev is None else [(c, o) for c, o in jev if len(c) >= MIN_QUOTE and c in hay]
    blocks = [[_squash(x) for x in blk.splitlines()] for blk in tool_output.split("\0")]
    missing = []
    for l in lines:
        for m in PASS_RE.finditer(l):
            q = m.group(1)
            sq = _squash(q)
            if len(sq) < MIN_QUOTE or sq not in hay or (typed and sq in typed):
                missing.append(q)
                continue
            # 인용이 든 명령 출력 칸마다 실패 줄이 하나라도 있으면 그 칸은 근거가 못 된다 (`Ran 5 tests` … `FAILED (failures=2)`)
            src = [blk for blk in blocks if sq in " ".join(blk)]
            if src and all(any(FAIL_LINE_RE.search(x) for x in blk) for blk in src):
                missing.append(q + " (실패가 든 출력에서 떼어 옴)")
                continue
            if jev is not None:
                want = ("UNAVAILABLE",) if "미확인" in m.group(0) else ("SUPPORTED",)
                if not any(sq in c and o in want for c, o in jev):
                    missing.append(q + (" (jev UNAVAILABLE 기록 없음)" if "미확인" in m.group(0) else " (jev SUPPORTED 기록 없음)"))
    return missing


IMG_NAME_RE = re.compile(r"[\w./-]+\.(?:png|jpe?g|webp|gif|bmp)\b", re.I)


def image_evidence(events):
    """이번 바퀴에 실제로 열어 본 그림의 흔적 — Read 한 그림 경로, 그림을 돌려준 도구 호출의 입력 글"""
    calls, seen = {}, []
    for t, b in _blocks(events):
        if t == "assistant" and b.get("type") == "tool_use":
            inp = b.get("input") or {}
            calls[b.get("id")] = json.dumps(inp, ensure_ascii=False)
            fp = str(inp.get("file_path") or "")
            if b.get("name") == "Read" and fp.lower().endswith(IMAGE_EXT):
                seen.append(fp)
        elif t == "user" and b.get("type") == "tool_result":
            inner = b.get("content")
            if isinstance(inner, list) and any(isinstance(x, dict) and x.get("type") == "image" for x in inner):
                seen.append(calls.get(b.get("tool_use_id"), "(그림)"))
    return seen


def eye_problem(lines, evidence):
    """"3층 통과" 줄마다: 어느 그림인지 적었나, 그 그림을 이번 바퀴에 실제로 열었나. 문제가 없으면 빈칸"""
    for l in lines:
        if not EYE_PASS_RE.search(l):
            continue
        named = [n.rsplit("/", 1)[-1].lower() for n in IMG_NAME_RE.findall(l)]
        if not named:
            return "STATUS 에 '3층 통과' 라 적었는데 어느 그림을 봤는지(captures/<파일>.png) 안 적음"
        if not any("captures/" in n for n in IMG_NAME_RE.findall(l)):
            return "STATUS 의 '3층 통과' 그림이 captures/ 밖에 있음 — 게임 카메라 캡처만 3층 근거가 된다"
        if not any(n in e.lower() for n in named for e in evidence):
            return f"STATUS 의 '3층 통과' 가 적은 그림({', '.join(named)})을 이번 바퀴에 열어 보지 않음"
    return ""


def bare_problem(lines):
    """1·2층 '통과' 를 인용 없이 적은 줄 — 인용이 없으면 감사가 대조할 것이 없다"""
    for l in lines:
        if BARE_RE.search(re.sub(r"`[^`]*`", "``", l)):   # 인용 속 글(`… 검사 통과 …`)은 출력이지 주장이 아니다
            return f"STATUS 에 인용 없는 통과: {l.strip()[:80]} — 통과(`실제 출력 한 줄`) 로 적거나 '못 함(이유)'"
    return ""


def trailer_problem(msgs, lines):
    """커밋 Checks: 에 pass 라 적었는데 STATUS 에 그 층의 근거가 없음 (1·2층 = 인용, 3층 = 본 캡처)"""
    for m in msgs:
        for l1, l2, l3 in TRAILER_RE.findall(m):
            for n, v in (("1", l1), ("2", l2)):
                if v.rstrip(",") == "pass" and not any(re.search(n + r"\s*층[^`\n]{0,12}통과\s*\(`", l) for l in lines):
                    return f"커밋에 'Checks: L{n} pass' 인데 STATUS 에 {n}층 통과(`인용`) 이 없음"
            if l3.rstrip(",") == "pass" and not any(EYE_PASS_RE.search(l) for l in lines):
                return "커밋에 'Checks: L3 pass' 인데 STATUS 에 '3층 통과 (captures/<파일>)' 줄이 없음"
    return ""


GUARD_PATH_RE = r"(\./)?(loop/(?!(STOP|WRAPUP|HOLD)\b)\S|\.githooks/|docs/conventions/|tools/(check_conventions\.py|jev\.py|skills\.sh)\b|\.claude/(settings|agents/))"
# 고쳤다가 바퀴 끝 전에 되돌리면 지문은 같다 — 키트 파일에 쓰는 명령 자체를 잡는다 (읽기 cat·grep 은 괜찮음)
GUARD_WRITE_RE = re.compile(
    r"(\bsed\s+(-\S+\s+)*-\w*i|\b(chmod|chflags|chown|truncate|rm|unlink|touch|patch)\b|\bgit\s+(checkout|restore|apply|mv|rm)\b)[^;&|\n]*?\s" + GUARD_PATH_RE
    + r"|\b(cp|mv|ln|install|rsync)\b[^;&|\n]*\s" + GUARD_PATH_RE + r"\S*\s*($|[;&|\n])"
    + r"|(>>?|\btee\b(\s+-\w+)*)\s*" + GUARD_PATH_RE, re.M)


def bypass_problem(events, root="."):
    """이번 바퀴 도구 호출에서 훅·판별을 피한 흔적 — 명령, 또는 키트 보호 파일 직접 편집"""
    written = {}
    for _, b in _blocks(events):
        if b.get("type") == "tool_use":
            inp = b.get("input") or {}
            cmd = str(inp.get("command") or "")
            look = cmd if SHELL_AGAIN_RE.search(cmd) else QUOTED_RE.sub("''", HEREDOC_RE.sub("", cmd) if
                                                                      not re.search(r"\b(ba|z)?sh\b[^\n]*<<|python3?\b[^\n]*<<", cmd) else cmd)
            if BYPASS_RE.search(look) or RAW_BYPASS_RE.search(cmd):
                return f"훅·판별을 피하는 명령: {cmd.strip()[:80]}"
            if GUARD_WRITE_RE.search(cmd):
                return f"키트 보호 파일에 쓰는 명령: {cmd.strip()[:80]} (되돌려도 기록에 남는다 — 규칙을 바꾸려면 INBOX 에 질문)"
            # 일꾼이 써 둔 스크립트를 돌렸으면 그 본문도 같은 눈으로 본다 (명령을 파일에 숨기기)
            for wp, body in written.items():
                if cmd and os.path.basename(wp) in cmd and (BYPASS_RE.search(body) or GUARD_WRITE_RE.search(body)):
                    return f"훅·판별을 피하거나 키트 파일에 쓰는 스크립트를 돌림: {wp}"
            fp = str(inp.get("file_path") or inp.get("notebook_path") or "")
            if b.get("name") in ("Write", "Edit") and fp:
                written[fp] = written.get(fp, "") + "\n" + str(inp.get("content") or inp.get("new_string") or "")
            if b.get("name") in ("Edit", "Write", "NotebookEdit", "MultiEdit") and fp:
                rel = os.path.relpath(fp, root) if os.path.isabs(fp) else fp
                if GUARD_RE.match(rel.replace(os.sep, "/")):
                    return f"키트 보호 파일을 직접 고침: {rel} (규칙을 바꾸려면 INBOX 에 질문)"
    return ""


def commits_problem(pre_sha, lap):
    """바퀴 동안 생긴 커밋 — 꼬리말 없이 INBOX 밖을 고친 것(훅을 거치지 않음) · 키트 보호 파일을 고친 것"""
    rp = os.environ.get("LOOP_HOOK_RECEIPT", "")
    receipt = set(_read(rp).split()) if rp else None   # loop.sh 가 줄 때만 본다 (손으로 돌린 check 는 영수증 없음)
    for h in _git("rev-list", f"{pre_sha}..HEAD").split():
        msg = _git("log", "-1", "--format=%B", h)
        files = _git("show", "--name-only", "--format=", h).split()
        bad = [f for f in files if GUARD_RE.match(f)]
        if bad:
            return f"커밋 {h[:7]} 이 키트 보호 파일을 고침: {', '.join(bad[:3])}"
        if not re.search(rf"^Loop: {re.escape(str(lap))}$", msg, re.M) and any(f != "docs/feedback/INBOX.md" for f in files):
            return f"커밋 {h[:7]} 에 'Loop: {lap}' 꼬리말이 없음 — 훅을 거치지 않은 커밋 (감독 커밋이면 이 결함을 지우면 된다)"
        if receipt is not None and re.search(rf"^Loop: {re.escape(str(lap))}$", msg, re.M):
            if _git("rev-parse", f"{h}^{{tree}}").strip() not in receipt:
                return f"커밋 {h[:7]} 의 트리가 훅 영수증에 없음 — 훅을 거치지 않고 커밋함 (hooksPath·권한·스크립트 우회)"
    return ""


def api_today(csv_path, day, missing_cost):
    """오늘 API 폴백 바퀴의 추정비용 합. 비용 칸이 빈 바퀴(결과 줄 없이 끊김)는 바퀴 상한(missing_cost)으로 센다 — 0 으로 세면 상한이 샌다"""
    total = 0.0
    for row in csv.DictReader(open(csv_path, encoding="utf-8")) if os.path.exists(csv_path) else []:
        if row.get("account") == "api" and str(row.get("time", "")).startswith(day):
            try:
                total += float(row.get("cost_usd") or missing_cost)
            except ValueError:
                total += missing_cost
    return total


def done_problem(pre_sha, lines):
    """이번 바퀴가 ROADMAP 에 [x] 를 쳤는데 STATUS 에 통과 인용도 `못 함` 도 없다 — skip·chore 로 검사 없이 끝낸 조각"""
    if not any("[x]" in l for l in _added(pre_sha, "docs/ROADMAP.md")):
        return ""
    if any(re.search(r"[12]\s*층", l) and (PASS_RE.search(l) or "못 함" in l) for l in lines):
        return ""
    return "ROADMAP 에 [x] 를 쳤는데 STATUS 에 통과 인용도 「못 함」도 없음 — 검사를 돌려 인용하거나 못 한 이유를 적을 것"


def commit_msgs(pre_sha):
    return [m for m in _git("log", "--format=%B%x00", f"{pre_sha}..HEAD").split("\0") if m.strip()]


def reopen_roadmap(root, pre_sha):
    """감사 실패 바퀴가 새로 [x] 한 ROADMAP 줄을 [ ] 로 되돌린다 — 거짓 통과로 조각이 끝난 셈이 되지 않게"""
    p = os.path.join(root, "docs/ROADMAP.md")
    done = {l for l in _added(pre_sha, "docs/ROADMAP.md", root) if "[x]" in l}
    text = _read(p)
    if not done or not text:
        return 0
    lines = text.split("\n")
    n = 0
    for i, l in enumerate(lines):
        if l in done:
            lines[i] = l.replace("[x]", "[ ]", 1)
            n += 1
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return n


def add_defect(root, lap, reason):
    """감사가 잡은 거짓 통과를 INBOX 맨 위 `결함` 으로 — 경고만 남기면 아무도 다시 안 본다"""
    p = os.path.join(root, "docs/feedback/INBOX.md")
    text = _read(p)
    mark = "<!-- 여기 아래에 적는다 -->"
    if not text or mark not in text:
        return False
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    item = (f"- [ ] 결함(감사, {now}) **#{lap} 검사 기록이 실제 결과와 다름.** {reason[:200]} "
            f"검사를 실제로 돌려 STATUS 의 그 줄을 고칠 것. 검증: `python3 loop/lap_audit.py check` 통과 / 삭제: 고친 커밋 후")
    with open(p, "w", encoding="utf-8") as f:
        f.write(text.replace(mark, mark + "\n" + item, 1))
    return True


def check(path, pre_sha, inbox_root=None, lap="?"):
    _, cmds, out = parse(path)
    events = list(_events(path))
    lines = _added(pre_sha, "docs/STATUS.md")
    quotes = sum(len(PASS_RE.findall(l)) for l in lines)
    missing = check_quotes(lines, out, authored_text(events), jev_calls(events))
    # LOOP_TAMPER: loop.sh 가 바퀴 전후 키트 파일 지문을 비교해 다르면 넣는다 (이 감사기 자체를 고친 경우까지)
    problem = (os.environ.get("LOOP_TAMPER", "") or bypass_problem(events, os.getcwd()) or commits_problem(pre_sha, lap)
               or (quotes and not cmds and f"통과 인용 {quotes}개인데 도구 호출 기록이 0개 (jsonl 비었음?)")
               or (missing and "STATUS 의 통과 인용이 실제 실행 출력에 없거나 일꾼이 직접 쓴 글임: " + " | ".join(m[:60] for m in missing))
               or bare_problem(lines) or eye_problem(lines, image_evidence(events))
               or trailer_problem(commit_msgs(pre_sha), lines) or done_problem(pre_sha, lines))
    if problem:
        print(problem)
        if inbox_root and add_defect(inbox_root, lap, problem):
            print("→ INBOX 맨 위에 결함으로 올림")
        if inbox_root and reopen_roadmap(inbox_root, pre_sha):
            print("→ 이번 바퀴가 [x] 한 ROADMAP 조각을 [ ] 로 되돌림")
        return 1
    print(f"인용 {quotes}개 전부 실행 출력과 일치")
    return 0


# ── 문서 살림: 매 바퀴 다시 읽히는 STATUS·INBOX 가 불지 않게 ─────────────────────────

def split_status(text):
    """STATUS → (머리말, 지금 상태 본문 줄들, [바퀴 덩어리]). 지금 상태 절이 없으면 본문은 빈 목록."""
    m = LAP_HEAD_RE.search(text)
    top, laps_text = (text[:m.start()], text[m.start():]) if m else (text, "")
    laps = [b for b in re.split(r"(?m)^(?=## #)", laps_text) if b.strip()]
    i = top.find(NOW_HEAD)
    if i < 0:
        return top, [], laps
    head_end = top.find("\n", i) + 1 or len(top)
    return top[:head_end], top[head_end:].splitlines(), laps


def now_line_count(now_lines):
    return sum(1 for l in now_lines if l.strip() and l.strip() != "---")


def split_now(now_lines, keep=NOW_KEEP):
    """지금 상태 본문을 최상위 항목(`- `) 단위로 잘라 앞쪽 keep 줄만 남긴다 → (남길 줄, 넘친 줄). 항목을 중간에서 자르지 않는다."""
    items, cur = [], []
    for l in now_lines:
        if l.startswith("- ") and cur:
            items.append(cur)
            cur = []
        cur.append(l)
    if cur:
        items.append(cur)
    kept, over, used = [], [], 0
    for idx, it in enumerate(items):
        n = now_line_count(it)
        if not over and (idx == 0 or used + n <= keep):
            kept.extend(it)
            used += n
        else:
            over.extend(l for l in it if l.strip() != "---")
    return kept, over


def inbox_stats(text):
    kinds = {}
    for l in text.splitlines():
        m = re.match(r"- \[.\] ([^(（\s]+)", l)
        if m:
            kinds[m.group(1)] = kinds.get(m.group(1), 0) + 1
    human = sum(n for k, n in kinds.items() if k in HUMAN_KINDS)
    standing = sum(1 for l in text.splitlines() if l.startswith("- [") and "상시" in l)
    return kinds, human, standing


def size_problems(status_text, inbox_text):
    _, now, laps = split_status(status_text)
    probs = []
    n = now_line_count(now)
    if n > NOW_WARN:
        probs.append(f'STATUS "지금 상태" {n}줄 (권장 {NOW_KEEP}줄 이내) — 일꾼이 매 바퀴 읽는다')
    total = status_text.count("\n")
    if total > STATUS_MAX_LINES:
        probs.append(f"STATUS {total}줄 · 바퀴 기록 {len(laps)}개 (한도 {STATUS_MAX_LINES}줄)")
    kinds, human, standing = inbox_stats(inbox_text)
    if len(inbox_text) > INBOX_MAX_CHARS:
        detail = " · ".join(f"{k} {v}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]))
        probs.append(f"INBOX {len(inbox_text):,}글자 (한도 {INBOX_MAX_CHARS:,}) — {detail}")
    if human > 10:
        probs.append(f"INBOX 에 사람·감독이 닫아야 할 확인·질문·승인 {human}개가 쌓임")
    if standing:
        probs.append(f"INBOX 에 '상시' 규칙 {standing}줄 — INBOX 는 끝나면 지우는 우편함, 상시 규칙은 CLAUDE.md 로")
    return probs


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def size(root="."):
    probs = size_problems(_read(os.path.join(root, "docs/STATUS.md")), _read(os.path.join(root, "docs/feedback/INBOX.md")))
    if probs:
        print(" / ".join(probs) + " → 감독이 정리 (DIRECTOR.md 문서 살림)")
        return 1
    print("문서 크기 정상")
    return 0


def tidy_plan(status_text, keep_laps=LAPS_KEEP, keep_now=NOW_KEEP):
    """→ (새 STATUS, 보관 파일에 덧붙일 글, 옮긴 바퀴 수, 옮긴 지금-상태 줄 수)"""
    head, now, laps = split_status(status_text)
    kept_now, over_now = split_now(now, keep_now) if now_line_count(now) > keep_now else (now, [])
    old_laps = laps[keep_laps:]
    body = "\n".join(l for l in kept_now if l.strip() != "---").rstrip("\n")
    new_status = head + (body + "\n" if body else "")
    if laps:
        new_status = new_status.rstrip("\n") + "\n\n---\n\n" + "".join(laps[:keep_laps])
    today = datetime.date.today().isoformat()
    archive = ""
    if over_now:
        archive += f"## 지금 상태에서 넘친 것 ({today} 정리)\n" + "\n".join(over_now).rstrip("\n") + "\n\n"
    archive += "".join(old_laps)
    return new_status, archive, len(old_laps), now_line_count(over_now)


def inbox_items(text):
    """INBOX 를 덩어리로 나눈다 → [(항목인가, [줄…])]. 항목 = `- [` 줄 + 바로 이어지는 줄(빈 줄·다음 항목·제목·인용·주석 전까지)."""
    chunks = []
    for l in text.splitlines():
        if l.startswith("- ["):
            chunks.append((True, [l]))
        elif chunks and chunks[-1][0] and l.strip() and not l.startswith(("#", ">", "<!--")):
            chunks[-1][1].append(l)
        else:
            chunks.append((False, [l]))
    return chunks


def inbox_tidy_plan(text, max_chars=INBOX_MAX_CHARS):
    """→ (새 INBOX, 보관 글, 옮긴 끝난 항목 수, 옮긴 확인 수).
    줄 번호가 아니라 항목 단위로 옮긴다. 끝난 `[x]` 항목은 언제나, 그래도 한도를 넘으면 오래된 `확인` 부터.
    `질문`·`승인`(사람 답 대기)과 루프 몫(결함·지시·답·보정·철회·보류·막힘)은 건드리지 않는다. 왜: 줄 번호로 잘라 보관했다가 살아 있는 항목이 사라진 것처럼 보인 일이 있었다."""
    chunks = inbox_items(text)
    move = {i for i, (is_item, ls) in enumerate(chunks) if is_item and re.match(r"- \[[xX]\]", ls[0])}
    n_done = len(move)
    size = len(text) - sum(len("\n".join(chunks[i][1])) + 1 for i in move)
    n_confirm = 0
    if size > max_chars:
        def when(i):
            m = re.search(r"\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?", chunks[i][1][0])
            return m.group(0) if m else "9999"
        confirms = sorted((i for i, (is_item, ls) in enumerate(chunks)
                           if is_item and i not in move and re.match(r"- \[ \] 확인[(（]", ls[0])), key=when)
        for i in confirms:
            if size <= max_chars:
                break
            move.add(i)
            n_confirm += 1
            size -= len("\n".join(chunks[i][1])) + 1
    if not move:
        return text, "", 0, 0
    new_text = "\n".join(l for i, (_, ls) in enumerate(chunks) if i not in move for l in ls) + "\n"
    archive = "\n".join(l for i in sorted(move) for l in chunks[i][1]) + "\n"
    return new_text, archive, n_done, n_confirm


def tidy_inbox(root=".", dry=False):
    ip = os.path.join(root, "docs/feedback/INBOX.md")
    text = _read(ip)
    new_text, archive, n_done, n_confirm = inbox_tidy_plan(text)
    if not archive:
        if len(text) > INBOX_MAX_CHARS:
            print(f"INBOX {len(text):,}글자 — 자동으로 옮길 것 없음 (질문·승인·루프 몫만 남음) → 감독이 닫는다")
        return 0
    after = set(new_text.splitlines()) | set(archive.splitlines())
    lost = [l for l in text.splitlines() if l.strip() and l not in after]
    if lost:
        print(f"중단: INBOX 를 정리하면 {len(lost)}줄이 사라짐 (첫 줄: {lost[0][:60]}) — INBOX 는 바꾸지 않음")
        return 1
    today = datetime.date.today().isoformat()
    ap = os.path.join(root, "docs/archive", f"INBOX-{today}.md")
    print(f"INBOX 끝난 항목 {n_done}개 · 오래된 확인 {n_confirm}개 → {os.path.relpath(ap, root)} "
          f"(INBOX {len(text):,}글자 → {len(new_text):,}글자)")
    if len(new_text) > INBOX_MAX_CHARS:
        print(f"INBOX 가 아직 한도({INBOX_MAX_CHARS:,}자)를 넘음 — 남은 건 질문·승인·루프 몫 → 감독이 닫는다")
    if dry:
        return 0
    os.makedirs(os.path.dirname(ap), exist_ok=True)
    with open(ap, "a", encoding="utf-8") as f:
        f.write(f"## INBOX 에서 옮긴 것 ({today} 정리 — 확인은 감독이 검수 때 본다)\n" + archive + "\n")
    with open(ip, "w", encoding="utf-8") as f:
        f.write(new_text)
    return 0


def tidy(root=".", dry=False):
    sp = os.path.join(root, "docs/STATUS.md")
    text = _read(sp)
    if not text:
        print("docs/STATUS.md 를 못 읽음")
        return 1
    rc_inbox = tidy_inbox(root, dry)
    new_status, archive, n_laps, n_now = tidy_plan(text)
    if not archive.strip():
        print("STATUS 옮길 것 없음 (바퀴 기록·지금 상태 모두 한도 안)")
        return rc_inbox
    ap = os.path.join(root, "docs/archive", f"STATUS-{datetime.date.today().isoformat()}.md")
    # 한 글자도 버리지 않았는지: 옮긴 줄이 전부 새 STATUS 나 보관 글에 있어야 한다
    after = set(new_status.splitlines()) | set(archive.splitlines())
    lost = [l for l in text.splitlines() if l.strip() and l.strip() != "---" and l not in after]
    if lost:
        print(f"중단: 정리하면 {len(lost)}줄이 사라짐 (첫 줄: {lost[0][:60]}) — 아무것도 바꾸지 않음")
        return 1
    print(f"바퀴 기록 {n_laps}개 · 지금 상태 {n_now}줄 → {os.path.relpath(ap, root)} "
          f"(STATUS {text.count(chr(10))}줄 → {new_status.count(chr(10))}줄)")
    if dry:
        print("(--dry: 파일은 바꾸지 않음)")
        return 0
    os.makedirs(os.path.dirname(ap), exist_ok=True)
    with open(ap, "a", encoding="utf-8") as f:
        f.write(archive if archive.endswith("\n") else archive + "\n")
    with open(sp, "w", encoding="utf-8") as f:
        f.write(new_status)
    print(f"다음: git add docs/STATUS.md docs/feedback/INBOX.md docs/archive → 커밋 `docs(status): 오래된 기록 보관`")
    return rc_inbox


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


def context_fields(events):
    """호출마다 모델이 받은 컨텍스트(입력+캐시) — 같은 message.id 는 한 번만 센다 (한 호출이 여러 줄로 나뉘어 기록된다)"""
    seen, sizes, out = set(), [], 0
    for ev in events:
        m = ev.get("message")
        if not isinstance(m, dict):
            continue
        u, mid = m.get("usage"), m.get("id")
        if ev.get("type") != "assistant" or not u or mid in seen:
            continue
        seen.add(mid)
        sizes.append(u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0))
        out += u.get("output_tokens", 0)
    if not sizes:
        return "0,0,0,0,0"
    return f"{sizes[0]},{max(sizes)},{len(sizes)},{sum(sizes)},{out}"


def context(path):
    try:
        print(context_fields(_events(path)))
    except OSError:
        print("0,0,0,0,0")


def ctxreport_line(rows, last_n=20):
    """context.csv 줄들 → 최근 바퀴의 시작·최대 컨텍스트 평균 한 줄. 잰 바퀴가 없으면 빈 문자열."""
    vals = []
    for r in rows[-last_n:]:
        try:
            first, peak, calls = int(r.get("first") or 0), int(r.get("peak") or 0), int(r.get("calls") or 0)
        except ValueError:
            continue
        if calls > 0:
            vals.append((first, peak, calls))
    if not vals:
        return ""
    n = len(vals)
    return (f"컨텍스트 (최근 {n}바퀴 평균): 바퀴 시작 {sum(v[0] for v in vals) / n / 1000:.1f}K · "
            f"최대 {sum(v[1] for v in vals) / n / 1000:.1f}K · 호출 {sum(v[2] for v in vals) / n:.0f}번")


def ctxreport(path="logs/context.csv", last_n=20):
    try:
        with open(path, encoding="utf-8", errors="replace", newline="") as f:
            line = ctxreport_line(list(csv.DictReader(f)), last_n)
    except OSError:
        return 0
    if line:
        print(line)
    return 0


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
    # 눈 검사: 어느 그림인지 적고, 그 그림을 실제로 열었을 때만 "3층 통과"
    read_img = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "r1", "name": "Read", "input": {"file_path": "captures/0007_ui_inventory.PNG"}}]}}]
    tool_img = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "s1", "name": "shot", "input": {"out": "captures/0008_hud.png"}}]}},
                {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "s1", "content": [{"type": "image", "source": {}}]}]}}]
    read_txt = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "r2", "name": "Read", "input": {"file_path": "docs/STATUS.md"}}]}}]
    assert image_evidence(read_img) and image_evidence(tool_img) and not image_evidence(read_txt), "그림을 열었는지 판정이 틀림"
    assert not image_evidence([{"type": "user", "message": "글자뿐인 메시지"}]), "message 가 글자일 때 죽으면 안 됨"
    eye = "검사: 1층 통과 / 3층 통과(레퍼런스 대조: docs/reference/inv.md, captures/0007_ui_inventory.png)"
    assert eye_problem([eye], image_evidence(read_img)) == "", "연 그림을 적었는데 지적함"
    assert "열어 보지 않음" in eye_problem([eye], image_evidence(tool_img)), "다른 그림을 열고 적은 그림은 안 열었는데 통과시킴"
    assert eye_problem([eye.replace("0007_ui_inventory", "0008_hud")], image_evidence(tool_img)) == "", "캡처 도구가 돌려준 그림을 인정 안 함"
    assert "안 적음" in eye_problem(["3층 통과(레퍼런스 대조: docs/reference/inv.md)"], image_evidence(read_img)), "그림 이름 없는 3층 통과를 통과시킴"
    assert eye_problem(["검사: 1층 통과 / 3층 못 함(에디터 꺼짐)"], []) == "", "못 함을 지적함"
    # 문서 살림: 넘친 것만 옮기고 한 줄도 버리지 않는다
    st = "# STATUS\n> 머리말\n\n## 지금 상태 (루프가 매 바퀴 갱신)\n" + "".join(f"- 항목 {i}\n  덧붙인 줄 {i}\n" for i in range(1, 21)) \
        + "\n---\n\n" + "".join(f"## #{n:04d} · 조각 M0-{n}\n- 한 것: {n}\n\n" for n in range(40, 0, -1))
    head, now, laps = split_status(st)
    assert now_line_count(now) == 40 and len(laps) == 40, (now_line_count(now), len(laps))
    new, arch, n_laps, n_now = tidy_plan(st)
    h2, now2, laps2 = split_status(new)
    assert n_laps == 10 and len(laps2) == 30 and laps2[0].startswith("## #0040"), (n_laps, len(laps2))
    assert now_line_count(now2) == 14 and n_now == 26, (now_line_count(now2), n_now)
    assert "- 항목 7\n" in new and "- 항목 8\n" in arch and "## #0010" in arch and "## #0011" in new
    both = set(new.splitlines()) | set(arch.splitlines())
    assert all(l in both for l in st.splitlines() if l.strip() and l.strip() != "---"), "정리하다 줄을 잃음"
    assert tidy_plan(new)[1].strip() == "", "한도 안인데 또 옮기려 함"
    one = "## 지금 상태\n- " + "\n  ".join(f"긴 항목의 줄 {i}" for i in range(30)) + "\n- 둘째\n"
    kept, over = split_now(split_status(one)[1])
    assert len(kept) == 30 and over == ["- 둘째"], "첫 항목은 길어도 통째로 남겨야 함"
    inbox = "# INBOX\n" + "".join(f"- [ ] 확인(루프#{i}, 2026-09-18 10:00) **가정 {i}.** 본문\n" for i in range(12)) \
        + "- [ ] 지시(감독←형 상시 규칙, 2026-09-21 00:00) **검증 확실히.** 삭제: 하지 않음\n"
    probs = " / ".join(size_problems(st, inbox))
    assert "지금 상태" in probs and "40줄" in probs and "확인·질문·승인 12개" in probs and "상시" in probs, probs
    assert size_problems(new, "# INBOX\n- [ ] 지시(감독, 2026-09-21 00:00) **고블린 속도 3.5.**\n") == [], size_problems(new, "")
    box = ("# INBOX\n\n> 머리말\n\n<!-- 여기 아래에 적는다 -->\n"
           "- [x] 지시(감독, 2026-09-01 10:00) **끝난 것.**\n  이어지는 줄\n"
           "- [ ] 질문(루프#1, 2026-09-01 11:00) **사람 답 대기.**\n"
           "- [ ] 확인(루프#3, 2026-09-03 10:00) **새 가정.** " + "가" * 300 + "\n"
           "- [ ] 확인(루프#2, 2026-09-02 10:00) **옛 가정.** " + "나" * 300 + "\n"
           "- [ ] 지시(감독, 2026-09-04 10:00) **할 일.**\n")
    nb, arc, nd, nc = inbox_tidy_plan(box, max_chars=500)
    assert (nd, nc) == (1, 1), (nd, nc)
    assert "끝난 것" in arc and "이어지는 줄" in arc and "옛 가정" in arc, "끝난 항목·오래된 확인을 항목째 옮겨야 함"
    assert all(s in nb for s in ("사람 답 대기", "새 가정", "할 일", "> 머리말", "<!-- 여기")), "질문·루프 몫·머리말은 남겨야 함"
    assert all(l in set(nb.splitlines()) | set(arc.splitlines()) for l in box.splitlines() if l.strip()), "INBOX 정리하다 줄을 잃음"
    assert inbox_tidy_plan(nb, max_chars=5000)[1] == "", "한도 안이고 끝난 것도 없는데 또 옮기려 함"
    out = "✔ 규칙 검사 통과 (경고 0 / 미정 숫자 0)\nPassed: 3, Failed: 0"
    ok = ["검사: 1층 통과(`✔ 규칙 검사 통과 (경고 0 / 미정 숫자 0)`) / 2층 통과(`Passed: 3, Failed: 0`)"]
    bad = ["검사: 1층 통과(`✔ 규칙 검사 통과 (경고 1)`)"]
    assert check_quotes(ok, out) == [], "일치하는 인용을 놓침"
    assert check_quotes(bad, out) == ["✔ 규칙 검사 통과 (경고 1)"], "없는 인용을 통과시킴"
    fake = [{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": 'echo "Passed: 3, Failed: 0"'}}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit", "input": {"file_path": "docs/STATUS.md", "new_string": ok[0]}}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "git commit -m 'Checks: Passed: 3, Failed: 0'"}}]}}]
    assert check_quotes(ok, out, authored_text(fake)) == ["Passed: 3, Failed: 0"], "echo 로 만든 인용을 통과시킴"
    assert check_quotes(ok, out, authored_text(fake[1:])) == [], "STATUS 편집·커밋 메시지 속 인용을 지어낸 것으로 봄"
    assert "Passed: 3" in authored_text([{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit", "input": {"file_path": "t.sh", "new_string": "echo Passed: 3"}}]}}]), "Edit 로 써 둔 가짜 출력을 놓침"
    for l in ("no tests ran in 0.01s", "=== 0 passed ===", "Build failed with 2 errors", "Traceback (most recent call last):"):
        assert FAIL_LINE_RE.search(l), "실패 줄을 놓침: " + l
    for l in ("검사: 1층 정상", "2층 검사 완료", "1층 이상 없음"):
        assert BARE_RE.search(l), "인용 없는 통과 변형을 놓침: " + l
    ev = lambda i, c: {"type": "assistant", "message": {"id": i, "usage": {"input_tokens": 1, "cache_read_input_tokens": c, "output_tokens": 5}}}
    assert context_fields([ev("a", 99), ev("a", 99), ev("b", 199)]) == "100,200,2,300,10", "같은 id 두 줄은 한 번만 세야 함"
    assert context_fields([{"type": "result"}]) == "0,0,0,0,0", "호출 없는 기록"
    ctx = ctxreport_line([{"first": "20000", "peak": "90000", "calls": "30"}, {"first": "0", "peak": "0", "calls": "0"}, {"first": "30000", "peak": "110000", "calls": "50"}])
    assert "바퀴 시작 25.0K" in ctx and "최대 100.0K" in ctx and "최근 2바퀴" in ctx, ctx
    assert ctxreport_line([{"first": "0", "peak": "0", "calls": "0"}]) == "", "잰 바퀴가 없는데 줄을 냄"
    assert check_quotes(["검사: 3층 못 함(에디터 꺼짐)"], "") == [], "인용 없는 줄을 지적함"
    jev = ["1층 통과(`✔ 규칙 검사 통과 (경고 0 / 미정 숫자 0)`, jev SUPPORTED 0.79)"]
    assert PASS_RE.findall(jev[0]) and check_quotes(jev, out) == [], "STATUS 예시 꼴(인용 뒤 jev)을 못 읽음"
    assert check_quotes(["1층 통과(`0`)"], out) == ["0"], "너무 짧은 인용을 통과시킴"
    assert bare_problem(["검사: 1층 통과(jev 미확인)"]) and bare_problem(["2층 통과"]), "인용 없는 통과를 놓침"
    assert bare_problem(jev + ["3층 통과(captures/a.png)", "2층 못 함(에디터 꺼짐)"]) == "", "정상 줄을 지적함"
    assert "captures/" in eye_problem(["3층 통과(tmp/0007_ui_inventory.png)"], ["tmp/0007_ui_inventory.png"]), "captures 밖 그림을 인정함"
    tr = "feat: x\n\nChecks: L1 pass, L2 pass, L3 skip(에디터)\n"
    assert "L2 pass" in trailer_problem([tr], jev), "STATUS 에 없는 L2 pass 를 놓침"
    assert trailer_problem([tr], jev + ["2층 통과(`Passed: 3, Failed: 0`)"]) == "", "맞는 Checks 를 지적함"
    assert trailer_problem([tr.replace("L2 pass", "L2 skip(없음)")], jev) == "", "skip 을 지적함"
    tu = lambda name, inp: [{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}]
    for c in ("env -u LOOP_LAP git commit -m x", "git commit --no-verify -m x", "git -c core.hooksPath=/dev/null commit",
              "bash tools/skills.sh on --paid sprite-gen", "git push origin develop", "unset LOOP_LAP; git commit"):
        assert bypass_problem(tu("Bash", {"command": c})), "우회 명령을 놓침: " + c
    assert "보호 파일" in bypass_problem(tu("Edit", {"file_path": "/p/loop/PROMPT.md"}), "/p"), "PROMPT.md 편집을 놓침"
    assert bypass_problem(tu("Write", {"file_path": "/p/tools/blender/make.py"}), "/p") == "", "일꾼 도구 스크립트를 막음"
    assert bypass_problem(tu("Bash", {"command": "echo $LOOP_LAP; bash tools/skills.sh list blender"})) == "", "정상 명령을 막음"
    for c in ("git -c core.hookspath=/x commit -m y", "git commit -n -m x", "git commit -qn -m x", "git commit --no-verif -m x",
              "P=--paid; tools/skills.sh on $P x", "bash tools/skills.sh on blender-core", "tools/skills.sh off x", "ln -s ~/.claude/skill-library/a .claude/skills/a",
              "git config --unset core.hooksPath", "git config core.hooksPath /dev/null", "export LOOP_LAP=; git commit",
              "bash -c 'git push'", "git commit-tree HEAD^{tree} -m x", "git update-ref HEAD abc", "cat x >> /tmp/r/hook.log", 'git commit "--no-verify" -m x', "git -C . push", "env LOOP_LAP= git commit -m x",
              "git config set core.hooksPath x", "sh -c \"git commit --no-verify\"", "echo '--no-verify' | xargs git commit -m x"):
        assert bypass_problem(tu("Bash", {"command": c})), "우회 명령을 놓침: " + c
    for c in ("git config core.hooksPath", "grep -rn 'git push' docs/", 'echo "LOOP_LAP=$LOOP_LAP"',
              "git commit -q -m 'feat: x' -m 'Loop: 3'", "git commit --amend --no-edit", "tools/skills.sh status",
              "cat > docs/specs/a.md <<'EOF'\n배포는 git push 로 한다\nEOF", "git log --grep push", "touch loop/STOP"):
        assert bypass_problem(tu("Bash", {"command": c})) == "", "정상 명령을 막음: " + c
    for l in ("1층: 통과", "L1 통과", "1층 합격", "2층 pass"):
        assert bare_problem([l]), "변형 표기 통과를 놓침: " + l
    assert not bare_problem(["1층 통과 (`✔ 규칙 검사 통과`)"]), "띄어 쓴 인용을 인용 없음으로 봄"
    assert bypass_problem(tu("Bash", {"command": "git -c protocol.allow=always fetch x"})), "protocol.allow 우회를 놓침"
    for f in (".claude/settings.json", ".claude/settings.local.json", ".claude/agents/a.md", "tools/skills.sh", "tools/jev.py", ".githooks/pre-commit", "docs/conventions/Verification.md"):
        assert GUARD_RE.match(f), "키트 보호 파일을 놓침: " + f
    for c in ("git log -1", "git show HEAD", "git diff HEAD~1", "echo Passed: 3", "  printf 'ok'"):
        assert NOT_EVIDENCE_RE.search(c), "근거가 못 되는 명령을 근거로 봄: " + c
    for c in ("npm test", "dotnet test | tail -5", "python3 tools/check_conventions.py; echo done"):
        assert not NOT_EVIDENCE_RE.search(c), "검사 명령을 근거에서 뺌: " + c
    hide = "FAL_KEY OPENAI_KEY HF_TOKEN AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY GITHUB_PAT ANTHROPIC_API_KEY DB_PASSWORD GH_TOKEN".split()
    keep = "CLAUDE_CODE_OAUTH_TOKEN TYPESAFE_API_KEY LD_LIBRARY_PATH PATH MONKEY HOME KEYBOARD LOOP_LAP".split()
    assert secret_names(hide + keep) == hide, secret_names(hide + keep)
    for l in ("1층 검사 통과", "1층은 통과", "1층 — 통과", "**1층** 통과"):
        assert bare_problem([l]), "변형 표기 통과를 놓침: " + l
    for l in ("1층 통과 (`✔ 규칙 검사 통과`)", "1층: 통과(`✔ 규칙 검사 통과`)", "**1층** 통과(`✔ 규칙 검사 통과`)"):
        assert trailer_problem(["feat: x\n\nChecks: L1 pass, L2 skip(없음), L3 skip(없음)\n"], [l]) == "", "띄어 쓴 근거를 못 읽음: " + l
    tr3 = "feat: x\n\nChecks: L1 skip(없음), L2 skip(없음), L3 pass\n"
    assert "L3" in trailer_problem([tr3], jev), "STATUS 에 없는 L3 pass 를 놓침"
    assert trailer_problem([tr3], ["3층 통과(captures/a.png)"]) == "", "맞는 L3 pass 를 지적함"
    # 인용 근거 = Bash 결과만. jev 명령에 넣은 인용·jev 출력·Read 한 옛 STATUS 는 근거가 아니고, 지어낸 글도 아니다
    import tempfile
    q = "Passed: 3, Failed: 0"
    lap_ev = [tu("Bash", {"command": "npm test"})[0], None, tu("Bash", {"command": f'python3 tools/jev.py evidence "2층" "{q}"'})[0], None,
              tu("Read", {"file_path": "docs/STATUS.md"})[0], None]
    for i in (0, 2, 4):
        lap_ev[i]["message"]["content"][0]["id"] = f"t{i}"
        lap_ev[i + 1] = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": q if i else "ok\n" + q}]}}
    def quotes_ok(evs):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
            f.write("\n".join(json.dumps(e) for e in evs))
        ok = check_quotes([f"2층 통과(`{q}`)"], parse(f.name)[2], authored_text(evs)) == []
        os.unlink(f.name)
        return ok
    assert quotes_ok(lap_ev), "jev 를 돌린 정직한 바퀴를 거짓으로 봄"
    assert not quotes_ok(lap_ev[2:]), "jev 출력·Read 한 옛 STATUS 를 인용 근거로 인정함"
    err_ev = [lap_ev[0], {**lap_ev[1], "message": {"content": [{**lap_ev[1]["message"]["content"][0], "is_error": True}]}}]
    assert not quotes_ok(err_ev), "실패한 명령의 출력을 인용 근거로 인정함"
    # 실패 줄에서 성공 조각만 떼어 쓰기 · jev 를 안 돌렸거나 NOT_SUPPORTED 인데 통과라 적기
    assert check_quotes(["2층 통과(`3 passed in 0.2s`)"], "1 failed, 3 passed in 0.2s") != [], "실패 줄에서 떼어 온 인용을 통과시킴"
    assert check_quotes(["2층 통과(`3 passed in 0.2s`)"], "3 passed in 0.2s") == [], "실패 없는 줄을 지적함"
    # 여러 줄 실패 — 성공 줄과 실패 줄이 따로 찍히는 도구 (같은 명령 출력 칸 안이면 근거 아님, 다른 명령 칸이면 근거)
    for out in ("Passed: 3\nFailed: 2", "Ran 5 tests in 0.1s\n\nFAILED (failures=2)", "Tests: 3 passed\nErrors: 1"):
        good = out.splitlines()[0]
        assert check_quotes([f"2층 통과(`{good}`)"], out), f"여러 줄 실패를 놓침: {out!r}"
        assert check_quotes([f"2층 통과(`{good}`)"], out.split("\n")[-1] + OUT_SEP + good) == [], "다른 명령의 실패로 지적함"
    j_ok = [(_squash(q), "SUPPORTED")]   # (jev 에 넘긴 인용, 판정)
    j_no = [(j_ok[0][0], "NOT_SUPPORTED")]
    j_un = [(j_ok[0][0], "UNAVAILABLE")]
    assert check_quotes([f"2층 통과(`{q}`)"], q, "", j_ok) == [], "jev SUPPORTED 인 인용을 지적함"
    for j in ([], j_no, j_un):
        assert check_quotes([f"2층 통과(`{q}`)"], q, "", j), "jev SUPPORTED 기록 없는 통과를 놓침"
    assert check_quotes([f"2층 통과(`{q}`, jev 미확인)"], q, "", j_un) == [], "jev UNAVAILABLE 인 미확인을 지적함"
    assert check_quotes([f"2층 통과(`{q}`, jev 미확인)"], q, "", []), "jev 를 안 돌린 '미확인' 을 놓침"
    jl = [tu("Bash", {"command": f'python3 tools/jev.py evidence "2층" "{q}"'})[0]]
    jl[0]["message"]["content"][0]["id"] = "j1"
    jl.append({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "j1", "content": '{"choice": "SUPPORTED"}'}]}})
    assert jev_calls(jl) == j_ok, jev_calls(jl)
    # jev 판정 지어내기 — 출력 뒤에 echo · 키 바꿔치기 · 명령 치환 · 줄바꿈으로 두 명령 · 주장 글 속 SUPPORTED 낱말
    jc = f'python3 tools/jev.py evidence "2층" "{q}"'
    for bad in (jc + " >/dev/null; echo '{\"choice\":\"SUPPORTED\"}'", jc + " | tail -1", "TYPESAFE_API_KEY=bad " + jc,
                "env " + jc, jc + ' "$(echo x)"', jc + "\necho done", jc + " && true", "cd . && " + jc,
                jc + " fail", jc + " pass x", jc.replace("python3", "/tmp/x/python3"), jc.replace("python3", "python3.9")):
        assert not _plain_jev(bad), f"jev 위조 꼴을 jev 호출로 침: {bad[:70]}"
    for ok in (jc, "python3 ./tools/jev.py evidence 'a; b' 'x | y > z'", "python3 tools/jev.py evidence a b pass"):
        assert _plain_jev(ok), f"정상 jev 호출을 버림: {ok}"
    assert _jev_choice('{"choice": "UNAVAILABLE", "reason": "SUPPORTED 라고 적힌 주장"}') == "UNAVAILABLE"
    assert _jev_choice("SUPPORTED\n") == "", "JSON 이 아닌 낱말을 판정으로 침"
    # 하루 API 상한: 오늘 api 줄만, 비용 빈 줄은 바퀴 상한으로
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        f.write("time,lap,account,cost_usd\n2026-01-02 01:00,1,api,12.5\n2026-01-02 02:00,2,api,\n2026-01-01 01:00,3,api,99\n2026-01-02 03:00,4,nc,50\n")
    assert api_today(f.name, "2026-01-02", 10) == 22.5, api_today(f.name, "2026-01-02", 10)
    assert api_today("/없는/파일.csv", "2026-01-02", 10) == 0
    os.unlink(f.name)
    # 커밋 기록 감사 · ROADMAP 되돌림 · 훅의 키트 파일 거절 — 임시 git 저장소에서 실제로
    kit, here = os.path.dirname(os.path.dirname(os.path.abspath(__file__))), os.getcwd()
    d = tempfile.mkdtemp()
    g = lambda *c, **kw: subprocess.run(["git", *c], cwd=d, capture_output=True, text=True, **kw)
    try:
        g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
        os.makedirs(f"{d}/docs/feedback"); os.makedirs(f"{d}/loop")
        open(f"{d}/docs/ROADMAP.md", "w").write("- [ ] 조각 A\n- [ ] 조각 B\n")
        open(f"{d}/docs/feedback/INBOX.md", "w").write("# INBOX\n<!-- 여기 아래에 적는다 -->\n")
        g("add", "docs/ROADMAP.md", "docs/feedback/INBOX.md"); g("commit", "-qm", "init")
        pre = g("rev-parse", "HEAD").stdout.strip()
        open(f"{d}/docs/ROADMAP.md", "w").write("- [x] 조각 A\n- [ ] 조각 B\n")
        g("add", "docs/ROADMAP.md"); g("commit", "-qm", "feat: A\n\nLoop: 7")
        os.chdir(d)
        assert commits_problem(pre, 7) == "", "꼬리말 있는 커밋을 지적함"
        assert "꼬리말" in commits_problem(pre, 8), "꼬리말 없는 커밋을 놓침"
        # 훅 영수증: 'Loop:' 커밋의 트리가 영수증에 없으면 훅을 안 거친 것 (명령 글이 아니라 결과로)
        a_sha = g("rev-parse", "HEAD").stdout.strip()
        rc = os.path.join(d, ".git", "receipt")
        open(rc, "w").write(g("rev-parse", f"{a_sha}^{{tree}}").stdout)
        os.environ["LOOP_HOOK_RECEIPT"] = rc
        assert commits_problem(pre, 7) == "", "영수증에 있는 커밋을 지적함"
        open(f"{d}/docs/feedback/INBOX.md", "a").write("- [ ] 지시(감독): x\n")
        g("add", "docs/feedback/INBOX.md"); g("commit", "-qm", "docs(inbox): 감독 지시", "--no-verify")
        assert commits_problem(pre, 7) == "", "꼬리말 없는 감독 INBOX 커밋을 영수증으로 지적함"
        open(rc, "w").write("")
        assert "영수증" in commits_problem(pre, 7), "훅을 안 거친 커밋(영수증 없음)을 놓침"
        del os.environ["LOOP_HOOK_RECEIPT"]
        assert reopen_roadmap(d, pre) == 1 and "- [ ] 조각 A" in open(f"{d}/docs/ROADMAP.md").read(), "[x] 를 안 되돌림"
        assert add_defect(d, 7, "시험") and "결함(감사" in open(f"{d}/docs/feedback/INBOX.md").read()
        open(f"{d}/loop/x.sh", "w").write("x")
        g("add", "loop/x.sh")
        r = g("-c", f"core.hooksPath={kit}/.githooks", "commit", "-qm", "feat: x", env={**os.environ, "LOOP_LAP": "7"})
        assert r.returncode != 0 and "키트 파일" in r.stdout + r.stderr, "훅이 일꾼의 키트 파일 커밋을 안 막음: " + r.stdout + r.stderr
        g("commit", "-qm", "chore: 감독\n\nLoop: 7", "--no-verify")
        assert "보호 파일" in commits_problem(pre, 7), "커밋된 키트 파일을 놓침"
        # 훅이 실제로 영수증을 남기나 — 키트 검사기를 옮겨 놓고 진짜 훅으로 커밋
        os.makedirs(f"{d}/tools"); shutil.copy(f"{kit}/tools/check_conventions.py", f"{d}/tools/")
        open(f"{d}/docs/note.md", "w").write("메모\n"); g("add", "docs/note.md")
        r = g("-c", f"core.hooksPath={kit}/.githooks", "commit", "-qm", "docs: 메모\n\nLoop: 7",
              env={**os.environ, "LOOP_LAP": "7", "LOOP_HOOK_RECEIPT": rc})
        assert r.returncode == 0 and g("rev-parse", "HEAD^{tree}").stdout.strip() in open(rc).read().split(), "훅이 영수증을 안 남김: " + r.stdout + r.stderr
        # 바퀴 사이 자동 정리 커밋 — LOOP_LAP 이 남아 있으면 훅이 Loop: 꼬리말을 요구해 거절한다 (loop.sh 는 env -u LOOP_LAP)
        open(f"{d}/docs/note.md", "a").write("정리\n"); g("add", "docs/note.md")
        tidy_msg = re.search(r'env -u LOOP_LAP git commit -q -m "([^"]+)"', open(f"{kit}/loop/loop.sh", encoding="utf-8").read()).group(1)
        hk = lambda e: g("-c", f"core.hooksPath={kit}/.githooks", "commit", "-qm", tidy_msg, env=e)
        assert hk({**os.environ, "LOOP_LAP": "3"}).returncode != 0, "훅이 꼬리말 없는 루프 커밋을 받음"
        r = hk({k: v for k, v in os.environ.items() if k != "LOOP_LAP"})
        assert r.returncode == 0, "자동 정리 커밋을 훅이 거절함: " + r.stdout + r.stderr
        # [x] 인데 인용도 못 함도 없음
        assert "못 함" in done_problem(pre, ["검사: 1층 skip"]) and done_problem(pre, ["3층 못 함(에디터)"]) and done_problem(pre, ["1층 못 함(검사기 없음)"]) == "" \
        and done_problem(pre, ["메모: 못 함"]), "검사 없는 [x] 판정이 틀림 (1·2층 줄만 근거)"
        # loop.sh 의 지문·되돌림·deny — 함수만 떼어 이 임시 저장소에서 실제로 돌린다
        sh = open(f"{kit}/loop/loop.sh", encoding="utf-8").read()
        fn = lambda name, end: sh[sh.index(name):sh.index(end, sh.index(name))]
        script = (fn("GUARD_PATHS=", "\nLOCK=") + fn("lean_settings() {", "\n}\n") + "\n}\n" +
                  'a=$(guard_sum); guard_snap; echo x >> loop/x.sh; ln -s /tmp .claude/skills/new; echo y > loop/new.sh; '
                  'b=$(guard_sum); guard_restore; touch loop/HOLD loop/STOP; '
                  'c=$(guard_sum); echo "$a $b $c"; test -L .claude/skills/new && echo LINK_LEFT; test -e loop/new.sh && echo NEW_LEFT; '
                  'out=o.txt raw=r.jsonl; echo "API Error: rate limit" > o.txt; echo \'{"type":"user","x":"quota 429"}\' > r.jsonl; '
                  'lim "rate limit" && lim "quota" && echo LIM_BAD; lim "rate limit" || echo LIM_MISS; '
                  'pre=$(git rev-parse HEAD); refs_pre=$(git for-each-ref refs/remotes | shasum); : > r.jsonl; '
                  'test -z "$(raw_problem)" || echo EMPTY_TAMPER; git update-ref refs/remotes/o/x HEAD; test -n "$(raw_problem)" || echo REF_MISS; '
                  'refs_pre=$(git for-each-ref refs/remotes | shasum); git commit -q --allow-empty --no-verify -m e; '
                  'test -n "$(raw_problem)" || echo WIPED_MISS; echo \'{"type":"user"}\' > r.jsonl; test -n "$(raw_problem)" || echo INIT_MISS; '
                  'echo \'{"type":"system","subtype":"init"}\' > r.jsonl; test -z "$(raw_problem)" || echo INIT_BAD; '
                  'rm -r "$RECEIPT_DIR"; LOOP_LEAN=0 lean_settings /없음 | python3 -c "import json,sys; print(len(json.load(sys.stdin)[\'permissions\'][\'deny\']))"; '
                  'LOOP_LEAN=1 lean_settings u | python3 -c "import json,sys; print(\',\'.join(sorted(json.load(sys.stdin)[\'env\'])))"; '
                  'LOOP_LEAN=0 lean_settings u | python3 -c "import json,sys; e=json.load(sys.stdin)[\'env\']; print(\',\'.join(sorted(k for k in e if e[k]==\'\')))"')
        os.makedirs(f"{d}/.claude/skills"); os.makedirs(f"{d}/logs"); os.makedirs(f"{d}/u")
        json.dump({"env": {"FAL_KEY": "x", "GITHUB_PAT": "x", "TYPESAFE_API_KEY": "x", "MAX_THINKING": "1"}}, open(f"{d}/u/settings.json", "w"))
        out = subprocess.run(["bash", "-c", script], cwd=d, capture_output=True, text=True,
                             env={**os.environ, "GUARD_DIR": f"{d}/.git", "LOOP_DIR": f"{kit}/loop"}).stdout.split()
        assert out[4:] == ["MAX_THINKING,TYPESAFE_API_KEY", "FAL_KEY,GITHUB_PAT"], "lean_settings 가 사람 설정 env 의 비밀 키를 일꾼에게 넘김 (LOOP_LEAN=1·0): " + str(out)
        out = out[:4]
        assert len(out) == 4 and out[0] == out[2] != out[1] and int(out[3]) >= 10, "loop.sh 지문·되돌림·lim·빈 기록·원격 ref·deny 가 틀림: " + str(out)
    finally:
        os.chdir(here)
        shutil.rmtree(d, ignore_errors=True)
    # check() 전체 — 임시 저장소 + 가짜 stream-json 기록으로, 통과 하나와 걸려야 할 갈래들
    def e2e(status, calls, tamper="", msg="docs(status): #1 A", roadmap=False, receipt=None):
        d2 = tempfile.mkdtemp()
        g2 = lambda *c: subprocess.run(["git", *c], cwd=d2, capture_output=True, text=True)
        try:
            g2("init", "-q"); g2("config", "user.email", "t@t"); g2("config", "user.name", "t")
            os.makedirs(f"{d2}/docs")
            open(f"{d2}/docs/STATUS.md", "w").write("# STATUS\n"); open(f"{d2}/docs/ROADMAP.md", "w").write("- [ ] A\n")
            g2("add", "docs"); g2("commit", "-qm", "init")
            pre2 = g2("rev-parse", "HEAD").stdout.strip()
            open(f"{d2}/docs/STATUS.md", "a").write(status + "\n")
            if roadmap:
                open(f"{d2}/docs/ROADMAP.md", "w").write("- [x] A\n")
            g2("add", "docs"); g2("commit", "-qm", msg + "\n\nLoop: 1")
            evs = []
            for i, (c, o) in enumerate(calls):
                if c == "@write":   # (경로, 본문) — 일꾼이 Write 로 파일을 씀
                    evs.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"w{i}", "name": "Write",
                                                                                "input": {"file_path": o[0], "content": o[1]}}]}})
                    continue
                evs += [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"t{i}", "name": "Bash", "input": {"command": c}}]}},
                        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": o}]}}]
            jp = f"{d2}/r.jsonl"
            open(jp, "w").write("".join(json.dumps(e) + "\n" for e in evs))
            os.chdir(d2); os.environ["LOOP_TAMPER"] = tamper
            if receipt is not None:
                open(f"{d2}/receipt", "w").write(receipt); os.environ["LOOP_HOOK_RECEIPT"] = f"{d2}/receipt"
            with contextlib.redirect_stdout(io.StringIO()):
                return check(jp, pre2, None, 1)
        finally:
            os.chdir(here); os.environ.pop("LOOP_TAMPER", None); os.environ.pop("LOOP_HOOK_RECEIPT", None); shutil.rmtree(d2, ignore_errors=True)
    run_ok = ("npm test", "Ran 12 tests OK")
    jev_ok = ('python3 tools/jev.py evidence "npm test 통과" "Ran 12 tests OK"', '{"choice": "SUPPORTED"}')
    good = "1층 통과(`Ran 12 tests OK`)"
    assert e2e(good, [run_ok, jev_ok]) == 0, "check: 정직한 바퀴를 막음"
    jev_na = (jev_ok[0], '{"choice": "UNAVAILABLE"}')
    assert e2e("1층 통과(`Ran 12 tests OK`, jev 미확인)", [run_ok, jev_na]) == 0, "check: jev 못 쓴 정직한 바퀴를 막음"
    assert e2e(good, [run_ok, jev_ok], msg="feat: A\n\nChecks: L1 pass, L2 skip, L3 skip", roadmap=True) == 0, "check: 꼬리말·[x] 정직한 바퀴를 막음"
    jq = lambda pre, post="": (pre + ' "npm test 통과" "Ran 12 tests OK"' + post, '{"choice": "SUPPORTED"}')
    for why, st, calls, tp in (("jev 안 돌림", good, [run_ok], ""), ("지어낸 인용", good, [jev_ok], ""),
                               ("인용 없는 통과", "1층 통과", [run_ok, jev_ok], ""),
                               ("실패가 든 출력", good, [("npm test", "Ran 12 tests OK\n2 failed"), jev_ok], ""),
                               ("훅 우회", good, [run_ok, jev_ok, ("git commit --no-verify -m x", "")], ""),
                               ("jev 판정 지어냄", good, [run_ok, ("python3 tools/jev.py evidence a 'Ran 12 tests OK'; echo '{\"choice\":\"SUPPORTED\"}'", '{"choice": "SUPPORTED"}')], ""),
                               ("키트 지문 바뀜", good, [run_ok, jev_ok], "LOOP_TAMPER 시험"),
                               ("미확인인데 jev 는 SUPPORTED", "1층 통과(`Ran 12 tests OK`, jev 미확인)", [run_ok, jev_ok], ""),
                               ("jev 를 일부러 잘못 부름", good, [run_ok, jq("python3 tools/jev.py evidence", " pass bogus")], ""),
                               ("jev fail 모드", good, [run_ok, jq("python3 tools/jev.py evidence", " fail")], ""),
                               ("가짜 python 경로", good, [run_ok, jq("/tmp/x/python3 tools/jev.py evidence")], ""),
                               ("다른 jev 로 cd", good, [run_ok, jq("cd /tmp/x && python3 tools/jev.py evidence")], ""),
                               ("jev 인용이 실제 출력 밖", good, [run_ok, ('python3 tools/jev.py evidence "npm test" "Ran 12 tests OK, 0 skipped"', '{"choice": "SUPPORTED"}')], ""),
                               ("TAP 실패", good, [("npm test", "Ran 12 tests OK\nnot ok 3 - x"), jev_ok], ""),
                               ("키트 파일 고쳤다 되돌림", good, [run_ok, jev_ok, ("sed -i '' s/a/b/ .githooks/pre-commit", "")], ""),
                               ("스크립트에 숨긴 우회", good, [run_ok, jev_ok, ("@write", ("/r/x.sh", "git commit --no-verify -m a")), ("bash x.sh", "")], "")):
        assert e2e(st, calls, tp) == 1, "check 가 놓침: " + why
    assert e2e("3층 통과 (captures/a.png)", [run_ok, jev_ok]) == 1, "check 가 놓침: 열지 않은 캡처로 3층 통과"
    assert e2e(good, [run_ok, jev_ok], msg="feat: A\n\nChecks: L1 pass, L2 pass, L3 skip") == 1, "check 가 놓침: 근거 없는 L2 pass 꼬리말"
    assert e2e("작업함", [run_ok], roadmap=True) == 1, "check 가 놓침: 검사 없이 ROADMAP [x]"
    assert e2e(good, [run_ok, jev_ok], receipt="") == 1, "check 가 놓침: 훅 영수증에 없는 커밋"
    # loop.sh 의 일꾼 막기 목록을 못 박는다 — 누가 한 줄 지워도 여기서 깨진다
    sh = open(f"{kit}/loop/loop.sh", encoding="utf-8").read()
    deny = set(re.findall(r'"((?:Bash|Edit)\([^"]+\))"', sh[sh.index('s["permissions"]'):sh.index("if shutil.which")]))
    want = {"Bash(git push:*)", "Bash(git -c core.hooksPath:*)", "Bash(git config core.hooksPath:*)", "Bash(env -u LOOP_LAP:*)", "Bash(gh:*)",
            "Bash(unset LOOP_LAP:*)", "Bash(bash tools/skills.sh on --paid:*)", "Bash(tools/skills.sh on --paid:*)", "Edit(./loop/**)",
            "Edit(./.githooks/**)", "Edit(./.claude/settings.json)", "Edit(./.claude/settings.local.json)", "Edit(./.claude/agents/**)",
            "Edit(./tools/check_conventions.py)", "Edit(./tools/jev.py)", "Edit(./tools/skills.sh)", "Edit(./docs/conventions/**)",
            "Bash(bash tools/skills.sh on:*)", "Bash(tools/skills.sh on:*)", "Bash(bash tools/skills.sh off:*)", "Bash(tools/skills.sh off:*)"}
    assert want <= deny, "loop.sh deny 에서 빠짐: " + str(want - deny)
    gp = re.search(r"^GUARD_PATHS=\((.*)\)", sh, re.M).group(1).split()
    assert {"loop", ".githooks", "docs/conventions", "tools/check_conventions.py", "tools/jev.py", "tools/skills.sh",
            ".claude/settings.json", ".claude/agents"} <= set(gp), "GUARD_PATHS 에서 빠짐: " + str(gp)
    for pin, why in (('"${SECRET_UNSET[@]}" "${WORKER_ENV[@]}"', "일꾼 실행 3곳에 비밀 변수 지우기·push 막기"),
                     ("SECRET_UNSET=(-u FALLBACK_ANTHROPIC_API_KEY -u LOOP_API_KEY_FILE)", "폴백 키·키 파일 경로를 일꾼에게서 지우기"),
                     ('(subpath \\"$r/$g\\")', "가두기에 보호 경로 넣기"), ('"$GUARD_DIR" "${pd[@]}"', "가두기에 되돌림 사본·PATH 넣기"),
                     ("secret_unset || {", "비밀 목록 실패 시 멈춤"), ("GIT_CONFIG_VALUE_0=never", "WORKER_ENV 의 push 막기"),
                     ('git config core.hooksPath .githooks', "훅 재무장"), ('budget=(--max-budget-usd "$cap")', "API 바퀴 상한 늘 전달"),
                     ("d - a < c", "하루 상한의 남은 돈으로 바퀴 상한 줄이기"), ("a>=m", "하루 상한 넘으면 API 안 씀"),
                     ('LOOP_TAMPER="$tamper" LOOP_HOOK_RECEIPT="$RECEIPT" "$LOOP_PY" -I "$LOOP_DIR/lap_audit.py" check', "감사기에 변조·영수증 넘기기, -I 로"),
                     ('[ "$(guard_sum)" != "$guard_post" ]', "바퀴 사이 키트 변경 되돌리기"), ('"Read(/" + sys.argv[4] + ")"', "API 키 파일 읽기 막기"),
                     ('${lean[@]+"${lean[@]}"}', "가벼운 설정(--settings) 일꾼에 넘기기")):
        assert pin in sh, "loop.sh 에서 빠짐: " + why
    # 일꾼은 skills.sh on·off 를 못 쓴다 (도구 서랍이 없어도 거부가 먼저 나와야 함)
    for c in ("on", "off"):
        r = subprocess.run(["bash", f"{kit}/tools/skills.sh", c, "x"], capture_output=True, text=True,
                           env={**os.environ, "LOOP_LAP": "1", "SKILL_LIBRARY": "/없음"})
        assert r.returncode == 1 and "거부" in r.stderr, "skills.sh 가 일꾼의 " + c + " 를 안 막음"
    assert '"-I", *sys.argv' in open(f"{kit}/tools/jev.py", encoding="utf-8").read(), "jev.py 가 -I 로 다시 뜨지 않음"
    # 유료 키를 쓰는 스킬은 사람 셸에서도 on 이 거부한다 (가짜 서랍으로)
    lib = tempfile.mkdtemp(); proj = tempfile.mkdtemp()
    try:
        for n, body in (("paid", "export OPENAI_API_KEY=..."), ("free", "그냥 규칙")):
            os.makedirs(f"{lib}/o_r/{n}"); open(f"{lib}/o_r/{n}/SKILL.md", "w").write(f"---\nname: {n}\n---\n{body}\n")
        env = {k: v for k, v in os.environ.items() if k != "LOOP_LAP"} | {"SKILL_LIBRARY": lib}
        sk = lambda n: subprocess.run(["bash", f"{kit}/tools/skills.sh", "on", n], capture_output=True, text=True, cwd=proj, env=env)
        r = sk("paid"); assert r.returncode == 1 and "거부(유료)" in r.stderr, "skills.sh 가 유료 스킬을 켬"
        assert sk("free").returncode == 0 and os.path.islink(f"{proj}/.claude/skills/free"), "skills.sh 가 무료 스킬을 못 켬"
    finally:
        shutil.rmtree(lib, ignore_errors=True); shutil.rmtree(proj, ignore_errors=True)
    assert sh.count('${lean[@]+"${lean[@]}"}') == 3, "일꾼을 부르는 곳 중 가벼운 설정을 안 넘기는 곳이 있음"
    assert sh.count('"${SECRET_UNSET[@]}" "${WORKER_ENV[@]}"') == 3, "일꾼을 부르는 곳 중 비밀 변수를 안 지우는 곳이 있음"
    assert sh.count('${SANDBOX[@]+"${SANDBOX[@]}"} env') == 3, "일꾼을 부르는 곳 중 가두기(sandbox-exec)를 안 쓰는 곳이 있음"
    if shutil.which("sandbox-exec"):   # 실제 프로필로: 보호 파일·사본은 막히고 STOP·STATUS 는 써진다
        box = tempfile.mkdtemp()
        try:
            fn = re.search(r"^make_sandbox\(\) \{.*?^\}$", sh, re.M | re.S).group(0)
            sb = (f'mkdir -p "{box}/r/loop" "{box}/r/docs" "{box}/g" && cd "{box}/r" && GUARD_DIR="{box}/g" && LOOP_SANDBOX=1 && '
                  'GUARD_PATHS=(loop) && alert() { :; }\n' + fn + '\nmake_sandbox; t() { "${SANDBOX[@]}" sh -c "echo x >> $1" 2>/dev/null && echo "$1:y" || echo "$1:n"; }; '
                  't loop/env.sh; t ../g/guard.tar; t loop/STOP; t docs/STATUS.md')
            got = subprocess.run(["bash", "-c", sb], capture_output=True, text=True).stdout.split()
            assert got == ["loop/env.sh:n", "../g/guard.tar:n", "loop/STOP:y", "docs/STATUS.md:y"], "가두기 프로필이 틀림: " + str(got)
        finally:
            shutil.rmtree(box, ignore_errors=True)
    # 유료 키 꼴 (tools/skills.sh PAID_KEYS) — 표본 글에서 잡을 것·안 잡을 것
    pk = re.search(r"^PAID_KEYS='(.*)'$", open(f"{kit}/tools/skills.sh", encoding="utf-8").read(), re.M).group(1)
    hit = lambda t: subprocess.run(["grep", "-qE", pk], input=t, text=True).returncode == 0
    for t in ("OPENAI_KEY=x", "HF_TOKEN", "process.env.TRIPO_API_KEY", "DEEPGRAM_API_KEY", "AWS_SECRET_ACCESS_KEY"):
        assert hit(t), "유료 키를 놓침: " + t
    for t in ("PRIMARY_KEY", "sort_key", "ROBLOX_UNIVERSE"):
        assert not hit(t), "무료 글을 유료로 봄: " + t
    assert not GUARD_RE.match("docs/STATUS.md") and GUARD_RE.match("loop/loop.sh") and not GUARD_RE.match("loop/STOP") and not GUARD_RE.match("loop/WRAPUP") and not GUARD_RE.match("loop/HOLD"), "멈춤 표시를 키트 변경으로 잡음"
    assert _content_text([{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]) == "a\nb"
    for c in ("GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath git commit -m x", "env -u GIT_CONFIG_COUNT git fetch", "git -c protocol.allow=always push",
              "git write-tree >> /tmp/r", "echo x >> $LOOP_HOOK_RECEIPT", "gh pr create -f", "gh api repos/a/b"):
        assert BYPASS_RE.search(c), "우회를 놓침: " + c
    for c in ("python3 -c \"print('ok')\"", "node -e 'console.log(1)'", "cat logs/lap-00001.log", "tail -n 5 logs/alerts.log"):
        assert NOT_EVIDENCE_RE.search(c), "찍은 글·옛 기록을 근거로 봄: " + c
    for c in ("python3 -m pytest -q | tee logs/test.txt", "npm test", "cat logs/test.txt"):
        assert not NOT_EVIDENCE_RE.search(c), "실제 검사 출력을 근거에서 뺌: " + c
    print("SELFTEST_OK")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["render"] and len(a) == 2:
        render(a[1])
    elif a[:1] == ["check"] and len(a) in (3, 5):
        sys.exit(check(a[1], a[2], *(a[3:5])))
    elif a[:1] == ["usage"] and len(a) == 2:
        usage(a[1])
    elif a[:1] == ["context"] and len(a) == 2:
        context(a[1])
    elif a[:1] == ["ctxreport"] and len(a) <= 3:
        sys.exit(ctxreport(a[1] if len(a) > 1 else "logs/context.csv", int(a[2]) if len(a) > 2 and a[2].isdigit() else 20))
    elif a[:1] == ["report"] and len(a) <= 3:
        sys.exit(report(a[1] if len(a) > 1 else "logs/usage.csv", int(a[2]) if len(a) > 2 and a[2].isdigit() else 20))
    elif a[:1] == ["size"] and len(a) <= 2:
        sys.exit(size(a[1] if len(a) > 1 else "."))
    elif a[:1] == ["tidy"] and len(a) <= 3:
        rest = [x for x in a[1:] if x != "--dry"]
        sys.exit(tidy(rest[0] if rest else ".", dry="--dry" in a))
    elif a[:1] == ["statelines"]:
        print(now_line_count(split_status(sys.stdin.read())[1]))
    elif a[:1] == ["api_today"] and len(a) == 4:  # api_today <usage.csv> <YYYY-MM-DD> <비용 빈 바퀴를 셀 값>
        print(f"{api_today(a[1], a[2], float(a[3] or 0)):.2f}")
    elif a[:1] == ["secrets"]:   # 표준입력의 변수 이름 중 일꾼에게서 지울 것 (loop.sh)
        print("\n".join(secret_names(sys.stdin.read().split())))
    elif a[:1] == ["selftest"]:
        selftest()
    else:
        print(__doc__)
        sys.exit(2)
