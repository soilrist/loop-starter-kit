#!/bin/bash
# ─────────────────────────────────────────────
# 루프 설정 — 여기만 고치면 다음 바퀴부터 적용 (재시작 필요 없음)
# 사람이 직접 고칠 필요 없음: 감독에게 "30분마다로 바꿔줘" 라고 말하면 됨
# ─────────────────────────────────────────────

# 이 프로젝트 이름 (launchd 라벨·알림에 씀, 영어 소문자·하이픈)
LOOP_SLUG="${LOOP_SLUG:-mygame}"
LOOP_LABEL="com.${LOOP_SLUG}.loop"

# 바퀴가 "끝난 뒤" 쉬는 시간(초). 평시 180 / 아낄 때 900 / 한도 빠듯하면 1800
LOOP_SLEEP_SEC=1800

# 한 바퀴 최대 시간(초). 넘으면 끊고 다음 바퀴
LOOP_LAP_TIMEOUT_SEC=2400

# 모델: 소넷 우선, 과부하 시 오퍼스 (claude --fallback-model)
LOOP_MODEL="sonnet"
LOOP_FALLBACK_MODEL="opus"

# 한 바퀴 비용 상한(달러, 비우면 제한 없음) — claude --max-budget-usd
LOOP_MAX_BUDGET_USD=""

# 계정 순서: 한도에 걸리면 다음 계정. "default" = 기본 로그인(개인 Max)
# 팀 계정 폴더가 없으면 자동으로 건너뜀
LOOP_ACCOUNTS="$HOME/.claude-loop-nc default"

# 헛바퀴(커밋 0) 연속 몇 번이면 경고 / 그 두 배면 스스로 멈춤
LOOP_MAX_IDLE=3
LOOP_IDLE_SLEEP_SEC=3600

# 모든 계정이 한도일 때 쉬는 시간(초)
LOOP_LIMIT_SLEEP_SEC=3600

# 헤드리스 권한 — 위험 명령은 .claude/settings.json 의 deny 로 막혀 있음
LOOP_PERMISSION_FLAGS="--dangerously-skip-permissions"

# claude 실행 파일 (launchd 는 PATH 가 짧아서 직접 찾아 줌)
export PATH="$HOME/.local/bin:$HOME/.claude/local:/opt/homebrew/bin:/usr/local/bin:$HOME/.npm-global/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
LOOP_CLAUDE_BIN="$(command -v claude || echo claude)"

# 시험용: 1 이면 claude 를 부르지 않고 흉내만 / 최대 바퀴 수(비우면 무한)
LOOP_DRY_RUN="${LOOP_DRY_RUN:-0}"
LOOP_MAX_LOOPS="${LOOP_MAX_LOOPS:-}"

# 한글 로그가 안 깨지게
export LANG="${LANG:-en_US.UTF-8}"
export LC_ALL="${LC_ALL:-en_US.UTF-8}"
