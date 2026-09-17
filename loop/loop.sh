#!/bin/bash
# ─────────────────────────────────────────────
# 루프 일꾼 실행기 — 매 바퀴 새 claude 헤드리스 세션을 띄운다
# launchd 가 이 파일을 계속 켜 둔다 (loop/ctl.sh on)
# macOS 기본 bash 3.2 에서 돌도록 작성
# ─────────────────────────────────────────────
set -u

LOOP_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$LOOP_DIR/.." && pwd)"
cd "$ROOT" || exit 1
mkdir -p logs

LOCK="$LOOP_DIR/.lock"
if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "이미 돌고 있음 (pid $(cat "$LOCK"))"
  exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

log()   { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a logs/loop.log; }
alert() {
  # 사람·감독이 봐야 할 일 — 깃에 안 들어가는 logs/alerts.log 에 쌓고 맥 알림
  echo "- [ ] 막힘(loop.sh, $(date '+%Y-%m-%d %H:%M')) **$1**" >> logs/alerts.log
  log "⚠ $1"
  if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"$1\" with title \"루프 ${LOOP_SLUG:-}\"" >/dev/null 2>&1 || true
  fi
}

[ -f logs/usage.csv ] || echo "time,lap,account,model,exit,commits,seconds,note" > logs/usage.csv
LAP_FILE="logs/lap"
[ "${LOOP_DRY_RUN:-0}" = "1" ] && LAP_FILE="logs/lap.dry"   # 시험 바퀴는 번호를 따로 셈
[ -f "$LAP_FILE" ] || echo 0 > "$LAP_FILE"

# 시간 제한 실행 (macOS 에는 timeout 명령이 없음)
# 감시자는 5초마다 살아 있는지만 보다가 claude 가 끝나면 스스로 끝남 (sleep 이 새지 않음)
run_with_timeout() {
  local secs="$1"; shift
  "$@" &
  local pid=$!
  (
    waited=0
    while kill -0 "$pid" 2>/dev/null; do
      sleep 5; waited=$((waited + 5))
      if [ "$waited" -ge "$secs" ]; then
        pkill -TERM -P "$pid" 2>/dev/null; kill -TERM "$pid" 2>/dev/null
        sleep 15
        pkill -KILL -P "$pid" 2>/dev/null; kill -KILL "$pid" 2>/dev/null
        break
      fi
    done
  ) >/dev/null 2>&1 &
  local watcher=$!
  wait "$pid"
  local rc=$?
  wait "$watcher" 2>/dev/null
  return $rc
}

# 쉬는 동안에도 STOP/WRAPUP 을 30초마다 확인
nap() {
  local left="$1"
  while [ "$left" -gt 0 ]; do
    if [ -f "$LOOP_DIR/STOP" ] || [ -f "$LOOP_DIR/WRAPUP" ]; then return 0; fi
    if [ "$left" -gt 30 ]; then sleep 30; left=$((left - 30)); else sleep "$left"; left=0; fi
  done
}

LIMIT_RE='usage limit|rate limit|limit reached|quota|credit balance|too many requests|429'

idle=0
count=0

while :; do
  # 설정은 매 바퀴 다시 읽는다 (재시작 없이 변경 반영)
  # shellcheck source=/dev/null
  . "$LOOP_DIR/env.sh"
  [ -n "${LOOP_FORCE_SLEEP_SEC:-}" ] && LOOP_SLEEP_SEC="$LOOP_FORCE_SLEEP_SEC"

  if [ -f "$LOOP_DIR/STOP" ]; then
    rm -f "$LOOP_DIR/WRAPUP"
    log "STOP 파일 → 종료"
    exit 0
  fi
  # 매 바퀴가 커밋된 상태로 끝나므로, 바퀴 사이의 WRAPUP 은 곧 STOP
  if [ -f "$LOOP_DIR/WRAPUP" ]; then
    rm -f "$LOOP_DIR/WRAPUP"; touch "$LOOP_DIR/STOP"
    log "WRAPUP → 바퀴 사이라 바로 멈춤"
    exit 0
  fi

  branch="$(git branch --show-current 2>/dev/null)"
  if [ "$branch" != "develop" ]; then
    if [ "$LOOP_DRY_RUN" = "1" ]; then
      log "(시험) 브랜치가 develop 이 아님($branch) — 실제로는 여기서 멈춤"
    else
      alert "브랜치가 develop 이 아님($branch) — 루프 멈춤"
      touch "$LOOP_DIR/STOP"
      exit 0
    fi
  fi

  lap=$(( $(cat "$LAP_FILE") + 1 ))
  echo "$lap" > "$LAP_FILE"
  export LOOP_LAP="$lap"
  pre="$(git rev-parse HEAD)"
  started=$(date +%s)
  out="logs/lap-$(printf '%05d' "$lap").log"

  prompt="너는 루프 일꾼이다. 바퀴 번호는 ${lap} 이다. loop/PROMPT.md 를 읽고 그 순서대로 이번 바퀴 하나만 수행하고 끝내라. 커밋 꼬리말 Loop: ${lap} 을 잊지 마라."

  set -- -p "$prompt" --model "$LOOP_MODEL" --output-format text
  [ -n "${LOOP_FALLBACK_MODEL:-}" ] && set -- "$@" --fallback-model "$LOOP_FALLBACK_MODEL"
  [ -n "${LOOP_MAX_BUDGET_USD:-}" ] && set -- "$@" --max-budget-usd "$LOOP_MAX_BUDGET_USD"
  [ -f "$LOOP_DIR/mcp.json" ] && set -- "$@" --mcp-config "$LOOP_DIR/mcp.json"
  # shellcheck disable=SC2086
  set -- "$@" $LOOP_PERMISSION_FLAGS

  used_account="-"
  rc=0
  note=""
  all_limited=1
  log "바퀴 #$lap 시작 (모델 $LOOP_MODEL)"

  for acct in $LOOP_ACCOUNTS; do
    if [ "$acct" != "default" ] && [ ! -d "$acct" ]; then
      continue
    fi
    used_account="$(basename "$acct")"
    if [ "$LOOP_DRY_RUN" = "1" ]; then
      used_account="dry"
      echo "[DRY] $LOOP_CLAUDE_BIN $*" > "$out"
      rc=0
    elif [ "$acct" = "default" ]; then
      run_with_timeout "$LOOP_LAP_TIMEOUT_SEC" env -u CLAUDE_CONFIG_DIR "$LOOP_CLAUDE_BIN" "$@" > "$out" 2>&1
      rc=$?
    else
      run_with_timeout "$LOOP_LAP_TIMEOUT_SEC" env CLAUDE_CONFIG_DIR="$acct" "$LOOP_CLAUDE_BIN" "$@" > "$out" 2>&1
      rc=$?
    fi

    if [ $rc -ne 0 ] && grep -Eiq "$LIMIT_RE" "$out"; then
      log "계정 $used_account 한도 → 다음 계정"
      note="limit:$used_account"
      continue
    fi
    all_limited=0
    break
  done

  secs=$(( $(date +%s) - started ))
  commits="$(git rev-list --count "$pre..HEAD" 2>/dev/null || echo 0)"
  # 진짜 일한 커밋 = 기록(docs(status)) 말고 다른 커밋
  work="$(git log --format=%s "$pre..HEAD" 2>/dev/null | grep -vc '^docs(status)' || true)"
  work="${work:-0}"
  [ $rc -eq 143 ] || [ $rc -eq 137 ] && note="${note} timeout"
  echo "$(date '+%Y-%m-%d %H:%M:%S'),$lap,$used_account,$LOOP_MODEL,$rc,$commits/$work,$secs,$note" >> logs/usage.csv
  log "바퀴 #$lap 끝 — 종료코드 $rc, 커밋 $commits(일 $work), ${secs}초 ${note}"

  # 작업 트리에 커밋 안 된 루프 흔적이 남았는지
  # (loop/env.sh 는 감독이 설정을 바꾸는 파일이라 제외)
  if [ "$LOOP_DRY_RUN" != "1" ] && [ -n "$(git status --porcelain 2>/dev/null | grep -v ' loop/env.sh$')" ]; then
    alert "바퀴 #$lap 뒤에 커밋 안 된 변경이 남음 — 감독 확인 필요"
  fi

  count=$((count + 1))
  if [ -n "${LOOP_MAX_LOOPS:-}" ] && [ "$count" -ge "$LOOP_MAX_LOOPS" ]; then
    log "최대 바퀴 수($LOOP_MAX_LOOPS) 도달 → 종료"
    exit 0
  fi

  if [ "$LOOP_DRY_RUN" != "1" ] && [ "$all_limited" = "1" ]; then
    alert "모든 계정이 한도 — ${LOOP_LIMIT_SLEEP_SEC}초 쉼"
    nap "$LOOP_LIMIT_SLEEP_SEC"
    continue
  fi

  if [ "$work" = "0" ] && [ "$LOOP_DRY_RUN" != "1" ]; then
    idle=$((idle + 1))
  else
    idle=0
  fi

  if [ "$idle" -ge $((LOOP_MAX_IDLE * 2)) ]; then
    alert "헛바퀴 ${idle}번 연속 — 스스로 멈춤. logs/lap-*.log 확인 필요"
    touch "$LOOP_DIR/STOP"
    exit 0
  elif [ "$idle" -ge "$LOOP_MAX_IDLE" ]; then
    alert "헛바퀴 ${idle}번 연속 — 쉬는 시간을 ${LOOP_IDLE_SLEEP_SEC}초로 늘림"
    nap "$LOOP_IDLE_SLEEP_SEC"
    continue
  fi

  nap "$LOOP_SLEEP_SEC"
done
