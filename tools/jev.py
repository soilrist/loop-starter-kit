#!/usr/bin/env python3
"""Jev(TypeSafe System One) 제3 판정기 — 일꾼·감독이 자기 결과를 자기가 채점하지 않게.

사용:
  python3 tools/jev.py evidence "<주장>" "<인용한 명령 출력>" [pass|fail]  → SUPPORTED | NOT_SUPPORTED
      pass(기본) = "검사가 통과했다"는 주장 · fail = "일부러 깨서 검사가 잡았다"(역검증)는 주장
  python3 tools/jev.py noise    "<엔진>" "<Error: 로그 줄>"       → KNOWN_NOISE | NEEDS_REVIEW
  python3 tools/jev.py verdict  "<결함 설명 + 근거>"              → CONFIRMED | PLAUSIBLE | NOT_REAL
  (evidence 만) Jev 를 못 쓰면 하이쿠 5.5 가 대타로 판정 → SUPPORTED_LITE (JEV_LITE=0 으로 끔)
  python3 tools/jev.py selftest                                   → 알려진 6개 사례로 자기 검사

출력: JSON 한 줄 {"choice": ..., "p": ..., "model": ...}
종료 코드: 0 = 긍정(SUPPORTED/KNOWN_NOISE/CONFIRMED) · 1 = 그 밖 · 2 = UNAVAILABLE(키·SDK·네트워크 없음)
키: 환경변수 TYPESAFE_API_KEY, 없으면 macOS Keychain(service=typesafe-api-key). 평문 저장 안 함.
"""
import inspect
import json
import os
import pathlib
import subprocess
import sys

VENV_PY = pathlib.Path.home() / ".claude/scripts/.venv/bin/python3"
try:
    from typesafe_sdk import Choice, Noul, TypeSafeClient
except ImportError:
    if VENV_PY.exists() and pathlib.Path(sys.executable) != VENV_PY:
        os.execv(str(VENV_PY), [str(VENV_PY), *sys.argv])  # ponytail: SDK 는 ~/.claude 의 venv 하나에만
    # SDK 가 없어도 죽지 않는다 — evidence 는 아래 하이쿠 대타가 받는다. 나머지는 _ask 가 UNAVAILABLE 로 알린다
    Choice = Noul = TypeSafeClient = None

POSITIVE = {"SUPPORTED", "SUPPORTED_LITE", "KNOWN_NOISE", "CONFIRMED"}
EVIDENCE_P = 0.7  # Noul 은 0.5 근처가 '모름' — 0.7 이상만 통과로 친다


def _api_key() -> str:
    if os.environ.get("TYPESAFE_API_KEY"):
        return os.environ["TYPESAFE_API_KEY"]
    user = subprocess.run(["whoami"], capture_output=True, text=True, check=True).stdout.strip()
    return subprocess.run(
        ["security", "find-generic-password", "-a", user, "-s", "typesafe-api-key", "-w"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


LITE_MODEL = os.environ.get("LOOP_LIGHT_MODEL", "claude-haiku-5-5")
LITE_BIN = os.environ.get("LOOP_CLAUDE_BIN") or "claude"


def _lite_evidence(claim: str, output: str, expect: str) -> dict:
    """Jev 를 못 쓸 때(키·네트워크 없음)만 부르는 대타: 하이쿠 5.5 가 같은 질문에 yes/no 만 답한다.
    Jev 보다 약한 판정이라 결과 이름이 다르다(SUPPORTED_LITE) — STATUS 에는 '통과(jev 미확인, lite 확인)' 로 적는다.
    도구 없이(--tools "") 글만 판정하고, 변명을 못 쓰게 첫 단어 YES/NO 만 읽는다."""
    prompt = (
        EVIDENCE_INSTRUCTIONS[expect]
        + "\n\nclaim:\n" + claim + "\n\ncited_output:\n" + output
        + "\n\nAnswer with exactly one word on the first line: YES or NO."
    )
    r = subprocess.run(
        [LITE_BIN, "-p", prompt, "--model", LITE_MODEL, "--effort", "low", "--tools", "",
         "--setting-sources", "", "--strict-mcp-config"],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0:
        raise RuntimeError(f"lite rc={r.returncode}: {r.stderr.strip()[:120]}")
    first = (r.stdout.strip().split() or [""])[0].strip(".,:").upper()
    if first not in ("YES", "NO"):
        raise RuntimeError(f"lite 답이 YES/NO 가 아님: {r.stdout.strip()[:60]!r}")
    return {"choice": "SUPPORTED_LITE" if first == "YES" else "NOT_SUPPORTED", "p": None, "model": LITE_MODEL}


def _ask(state, question):
    if TypeSafeClient is None:
        raise ImportError("typesafe_sdk 없음")
    with TypeSafeClient(api_key=_api_key()) as client:
        return client.system_one(state=state, questions={"q": question})


EVIDENCE_INSTRUCTIONS = {
    "pass": (
        "`claim` says a check or test PASSED. `cited_output` is what the author pasted as the last lines "
        "of the actual command output. Does `cited_output` genuinely demonstrate that `claim` is true? "
        "Answer no if the output is empty, is a prose description instead of real program output, "
        "comes from a different command or check than the claim, or shows any failure, error, "
        "skipped/unknown result, or zero tests run."
    ),
    # 역검증(일부러 깨서 검사가 잡는지) — 주장이 "실패했다"인데 pass 문구는 실패가 보이면 무조건 no 라 구조적으로 못 통과했다 (Snarehaven #123~#125)
    "fail": (
        "`claim` says a check or test FAILED AS INTENDED (a negative / mutation test: the author broke something on "
        "purpose to prove the check catches it). `cited_output` is what the author pasted as the last lines of the "
        "actual command output. Does `cited_output` show that the failure really happened, for the reason the claim "
        "states? Answer no if the output is empty, is a prose description instead of real program output, comes from "
        "a different command or check than the claim, or shows success / pass instead of a failure."
    ),
}


def evidence(claim: str, output: str, expect: str = "pass") -> dict:
    if TypeSafeClient is None:
        raise ImportError("typesafe_sdk 없음")
    if expect not in EVIDENCE_INSTRUCTIONS:
        raise ValueError(f"expect 는 pass|fail 중 하나: {expect!r}")
    r = _ask(
        {"claim": claim, "cited_output": output},
        Noul(instructions=EVIDENCE_INSTRUCTIONS[expect]),
    )
    p = r.nouls["q"].noul
    return {"choice": "SUPPORTED" if p >= EVIDENCE_P else "NOT_SUPPORTED", "p": round(p, 3), "model": r.model}


def noise(engine: str, line: str) -> dict:
    if TypeSafeClient is None:
        raise ImportError("typesafe_sdk 없음")
    r = _ask(
        {"engine": engine, "log_line": line},
        Choice(
            instructions=(
                "`log_line` is one Error/Warning line from a headless run of the game engine named in `engine`. "
                "KNOWN_NOISE = boilerplate the engine logs regardless of project code (missing default asset-manager "
                "rules, experimental plugin notices, licensing/telemetry chatter, missing optional tooling). "
                "NEEDS_REVIEW = plausibly caused by project code, assets, or configuration."
            ),
            criteria={"KNOWN_NOISE": None, "NEEDS_REVIEW": None},
        ),
    )
    c = r.choices["q"]
    return {"choice": c.choice, "p": round(c.confidence, 3), "model": r.model}


def verdict(finding: str) -> dict:
    if TypeSafeClient is None:
        raise ImportError("typesafe_sdk 없음")
    r = _ask(
        {"finding": finding},
        Choice(
            instructions=(
                "`finding` is a code-review or QA finding with its evidence. CONFIRMED = a real defect shown by "
                "concrete evidence (reproduction, output, exact code). PLAUSIBLE = could be real but unverified or "
                "evidence is indirect. NOT_REAL = not a defect, or the evidence contradicts it."
            ),
            criteria={"CONFIRMED": None, "PLAUSIBLE": None, "NOT_REAL": None},
        ),
    )
    c = r.choices["q"]
    return {"choice": c.choice, "p": round(c.confidence, 3), "model": r.model}


def selftest() -> dict:
    cases = [
        # 주장엔 '어떤 검사인지' 적는다 — 맨 "1층 통과" 만 쓰면 p≈0.6 으로 떨어져 NOT_SUPPORTED (2026-09-22 측정)
        ("evidence", ("1층 기계 검사(check_conventions.py) 통과", "결과: 통과 (오류 0 / 경고 0 / 미정 숫자 0)"), "SUPPORTED"),
        ("evidence", ("2층 통과", "Passed: 3, Failed: 2, Skipped: 0"), "NOT_SUPPORTED"),
        ("evidence", ("2층 통과", "테스트를 돌려서 전부 잘 됐음"), "NOT_SUPPORTED"),
        # 역검증 — 실패를 정확히 인용하면 SUPPORTED, 성공 출력을 실패 주장에 붙이면 NOT_SUPPORTED
        ("evidence", ("역검증: 뼈 이름을 일부러 바꾸자 소켓 검사가 불일치를 잡았다",
                      "Expected 'Socket_Tool attached to RightHand' to be RightHand, but it was LeftHand.\n"
                      "Result={Fail} Name={SocketBoneCheck}", "fail"), "SUPPORTED"),
        ("evidence", ("역검증: 뼈 이름을 일부러 바꾸자 소켓 검사가 불일치를 잡았다",
                      "Result={Success} Name={SocketBoneCheck}\nPassed: 1, Failed: 0", "fail"), "NOT_SUPPORTED"),
        ("verdict", ("STATUS says '2층 통과' but logs/lap-12.log has no test command; only check_conventions ran. "
                     "Evidence: grep -c 'run_tests\\|runTests' logs/lap-12.log -> 0",), "CONFIRMED"),
    ]
    results = []
    for name, args, want in cases:
        got = globals()[name](*args)["choice"]
        results.append({"case": name, "want": want, "got": got})
        assert got == want, results
    return {"choice": "SELFTEST_OK", "cases": results}


if __name__ == "__main__":
    cmd, args = (sys.argv[1] if len(sys.argv) > 1 else "help"), sys.argv[2:]
    fn = {"evidence": evidence, "noise": noise, "verdict": verdict, "selftest": selftest}.get(cmd)
    if fn is not None:
        params = inspect.signature(fn).parameters.values()
        lo = sum(p.default is inspect.Parameter.empty for p in params)
    if fn is None or not lo <= len(args) <= len(params):
        print(__doc__)
        sys.exit(2)
    try:
        out = fn(*args)
    except AssertionError as e:
        print(json.dumps({"choice": "SELFTEST_FAIL", "cases": e.args[0]}, ensure_ascii=False))
        sys.exit(1)
    except Exception as e:  # 키 없음·네트워크·429 — 루프를 죽이지 않고 '미확인'으로
        if cmd == "evidence" and os.environ.get("JEV_LITE", "1") == "1":  # Jev 대신 하이쿠가 한 번 더 (더 약한 판정)
            try:
                out = _lite_evidence(args[0], args[1], args[2] if len(args) > 2 else "pass")
                print(json.dumps(out, ensure_ascii=False))
                sys.exit(0 if out["choice"] == "SUPPORTED_LITE" else 1)
            except SystemExit:
                raise
            except Exception as e2:
                e = RuntimeError(f"{e} | lite: {e2}")
        print(json.dumps({"choice": "UNAVAILABLE", "reason": f"{type(e).__name__}: {e}"[:200]}, ensure_ascii=False))
        sys.exit(2)
    print(json.dumps(out, ensure_ascii=False))
    sys.exit(0 if out["choice"] in POSITIVE or out["choice"] == "SELFTEST_OK" else 1)
