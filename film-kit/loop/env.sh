#!/bin/bash
# ─────────────────────────────────────────────
# 루프 설정 — 여기만 고치면 다음 바퀴부터 적용 (재시작 필요 없음)
# 사람이 직접 고칠 필요 없음: 감독에게 "30분마다로 바꿔줘" 라고 말하면 됨
# ─────────────────────────────────────────────

# 이 프로젝트 이름 (launchd 라벨·알림에 씀, 영어 소문자·하이픈)
LOOP_SLUG="${LOOP_SLUG:-blacksmith-film}"
LOOP_LABEL="com.${LOOP_SLUG}.loop"

# 바퀴가 "끝난 뒤" 쉬는 시간(초). 평시 180 / 아낄 때 900 / 한도 빠듯하면 1800
LOOP_SLEEP_SEC=600   # 영상 렌더는 오래 걸리니 바퀴 사이는 짧게, 바퀴 안에서 렌더를 기다린다

# 한 바퀴 최대 시간(초). 넘으면 끊고 다음 바퀴
LOOP_LAP_TIMEOUT_SEC=5400   # 렌더 포함 90분. 이 안에 못 끝나는 조각은 더 잘게 쪼갠다

# 모델: 소넷 우선, 과부하 시 오퍼스 (claude --fallback-model)
LOOP_MODEL="sonnet"
LOOP_FALLBACK_MODEL="opus"

# 노력 단계 (claude --effort): low / medium / high / xhigh / max. 비우면 claude 기본값
# 평소엔 medium, 직전 바퀴가 일한 커밋 없이 끝났을 때만 RETRY 값으로 올린다 (비우면 안 올림)
# 왜: 단계가 높을수록 토큰을 더 쓴다. 높은 단계는 "재시도 한 번을 줄여 줄 때"만 본전이다
LOOP_EFFORT="medium"
LOOP_EFFORT_RETRY="high"

# 가벼운 바퀴: 1(기본)이면 사람 전역 설정(개인 훅·전역 스킬·플러그인·전역 MCP)을 바퀴에 싣지 않는다
# 프로젝트 .claude/(스킬·설정)·CLAUDE.md 는 그대로, MCP 는 loop/mcp.json 에 적은 것만. 끄려면 0
# 왜: 루프가 안 쓰는 전역 설정이 바퀴의 모든 호출마다 다시 실린다. 줄었는지는 logs/context.csv · `loop/ctl.sh cost` 로 본다
# 주의: 일꾼이 써야 하는 스킬은 전역이 아니라 프로젝트 .claude/skills/ 에 둔다 (전역 것은 일꾼 눈에 안 보인다)
LOOP_LEAN=1
# 가벼운 바퀴에서 일꾼이 쓰는 기본 도구 (비우면 loop.sh 기본 12개). 엔진 MCP 도구는 여기 말고 loop/mcp.json
LOOP_TOOLS=""

# 바퀴 전 점검 명령 (비우면 건너뜀). 종료코드 0 이 아니면 그 바퀴는 claude 를 부르지 않고 쉰다
# 엔진 에디터·MCP 가 살아 있는지처럼 "이게 죽어 있으면 바퀴가 통째로 헛도는 것" 하나를 싸게 확인하는 명령을 감독이 넣는다
# 예) Unity 상주 에디터: 'pgrep -f "Unity.*-projectPath" >/dev/null'   예) 로컬 서버: 'curl -fsS localhost:8080/health >/dev/null'
LOOP_PREFLIGHT_CMD='curl -fsS --max-time 5 http://127.0.0.1:8188/system_stats >/dev/null'   # ComfyUI 응답 확인 〔포트 확인〕. GPU 잠금은 일꾼이 조각 단위로 처리
LOOP_PREFLIGHT_SLEEP_SEC=600

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
