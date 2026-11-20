#!/usr/bin/env bash
# 도구 서랍의 스킬을 이 프로젝트에서 켜고 끈다.
#   서랍 = ~/.claude/skill-library/<owner>_<repo>/ (클로드가 안 읽는 곳 — 깔려 있어도 꺼진 상태)
#   켜기 = .claude/skills/<이름> 에 심볼릭 링크 → 감독·루프 일꾼 둘 다 보게 됨
#   끄기 = 그 링크만 지움. 키트 자체 스킬(진짜 폴더)은 절대 안 건드린다.
# 쓰는 법: tools/skills.sh list [낱말] | on [--paid] <이름|저장소/이름>... | off <이름>... | status
# 무료만: 유료 API 키(OpenAI·fal·Tripo…)를 쓰는 스킬은 거부한다. --paid 는 사람이 돈 쓰기를 허락했을 때만 (🔴).
# 무엇을 켤지는 docs/tools/CATALOG.md. 켠 스킬 설명은 매 호출에 실리니 조금만 켠다.
set -euo pipefail
LIB="${SKILL_LIBRARY:-$HOME/.claude/skill-library}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
DEST="$ROOT/.claude/skills"
# 이름 목록이 아니라 꼴로 잡는다 — 목록에 없는 새 키(OPENROUTER_API_KEY 등)도 걸리게
PAID_KEYS='\b[A-Z][A-Z0-9_]*_(API_KEY|API_TOKEN)\b|\b(OPENAI|ANTHROPIC|GEMINI|XAI|GROQ|MISTRAL|ELEVENLABS|TRIPO|MESHY|FAL|RUNWAY|LUMA|SUNO|HF|HUGGINGFACE|REPLICATE|STABILITY|LEONARDO|KLING|SCENARIO|DEEPGRAM|COHERE|PERPLEXITY)_(KEY|TOKEN|SECRET)\b|\bAWS_SECRET_ACCESS_KEY\b|\bGOOGLE_APPLICATION_CREDENTIALS\b|\bREPLICATE_API|\bSTABILITY_API|\bSCENARIO_API'
FREE_KEYS='^(ROBLOX[A-Z_]*|AUTH_SOURCE_API_KEY|SOME_API_KEY)$'  # 무료 서비스·예시 문자열
FREE_OK=" majidmanzarpour_threejs-game-skills/threejs-game-director "  # 저장소/이름 — 키가 있는지 확인만 하고 부르지 않음

PAID_REPOS=" scenario-labs_skills "  # 키 이름 없이 유료 MCP 크레딧으로 도는 저장소

paid_use() { # 유료 근거 한 줄 (없으면 빈칸)
  r=${1#"$LIB/"}; case $FREE_OK in *" ${r%%/*}/$2 "*) return 0 ;; esac
  case $PAID_REPOS in *" ${r%%/*} "*) echo "$LIB/${r%%/*} (유료 MCP 크레딧)"; return 0 ;; esac
  grep -roE "$PAID_KEYS" "$1" --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=.git 2>/dev/null |
    awk -F: -v free="$FREE_KEYS" '$NF !~ free { print $1 " (" $NF ")"; exit }' || true
}

index() { # 저장소<TAB>이름<TAB>폴더
  [ -d "$LIB" ] || { echo "도구 서랍이 없음: $LIB (docs/tools/CATALOG.md '서랍 채우기' 참고)" >&2; exit 1; }
  find "$LIB" -name SKILL.md -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/.git/*' |
  while IFS= read -r f; do
    n=$(awk 'NR==1&&/^---/{f=1;next} f&&/^---/{exit} f&&/^name:/{sub(/^name:[ \t]*/,"");gsub(/["\047]/,"");print;exit}' "$f")
    d=$(dirname "$f"); [ -n "$n" ] || n=$(basename "$d")
    r=${f#"$LIB/"}; printf '%s\t%s\t%s\n' "${r%%/*}" "$n" "$d"
  done | sort
}

resolve() { # 이름 또는 저장소/이름 → 폴더 하나
  local q=$1 repo="" name=$1 hits
  case $q in */*) repo=${q%%/*}; name=${q#*/} ;; esac
  hits=$(index | awk -F'\t' -v r="$repo" -v n="$name" '$2==n && (r=="" || $1==r)')
  [ -n "$hits" ] || { echo "없음: $q  (tools/skills.sh list $name)" >&2; return 1; }
  if [ "$(printf '%s\n' "$hits" | wc -l)" -gt 1 ]; then
    echo "이름 겹침: $q — 저장소/이름 으로 골라라:" >&2
    printf '%s\n' "$hits" | awk -F'\t' '{print "  " $1 "/" $2}' >&2; return 1
  fi
  printf '%s\n' "$hits" | cut -f3
}

cmd=${1:-status}; shift || true
case $cmd in
  list)
    index | awk -F'\t' -v w="${1:-}" -v dest="$DEST" 'tolower($0) ~ tolower(w) {
      on = (system("test -L \"" dest "/" $2 "\"") == 0) ? "켜짐 " : "     "
      print on $1 "/" $2 }' ;;
  on|off)
    # 켜고 끄기는 감독이 바퀴 사이에 한다 (DIRECTOR.md) — 바퀴 도중 바뀐 링크는 바퀴 끝 지문 검사가 되돌린다. --paid(돈)는 🔴
    if [ -n "${LOOP_LAP:-}" ]; then echo "거부: 루프 일꾼은 도구를 켜고 끄지 못한다 — 필요한 도구를 INBOX 에 질문으로 (감독이 바퀴 사이에 켬)" >&2; exit 1; fi ;;
esac
case $cmd in
  on)
    paid=0; [ "${1:-}" = --paid ] && { paid=1; shift; }
    [ $# -gt 0 ] || { echo "on 뒤에 이름" >&2; exit 2; }
    mkdir -p "$DEST"
    for q in "$@"; do
      link="$DEST/${q#*/}"
      if [ -e "$link" ] && [ ! -L "$link" ]; then echo "거부: $link 는 키트·프로젝트 자체 스킬" >&2; exit 1; fi
      src=$(resolve "$q") || exit 1
      f=$(paid_use "$src" "${q#*/}")  # resolve 가 이름을 맞췄으니 q 의 이름 = 스킬 이름
      if [ -n "$f" ] && [ $paid = 0 ]; then
        echo "거부(유료): $q 는 유료 API 를 부른다 — ${f#"$LIB/"}. 무료 대안을 CATALOG 에서 찾거나, 사람이 허락하면 on --paid" >&2; exit 1
      fi
      ln -sfn "$src" "$link"; echo "켬: ${link#"$ROOT/"} → ${src#"$LIB/"}"
    done ;;
  off)
    [ $# -gt 0 ] || { echo "off 뒤에 이름" >&2; exit 2; }
    for q in "$@"; do
      link="$DEST/${q#*/}"
      if [ -L "$link" ]; then rm "$link"; echo "끔: ${link#"$ROOT/"}"
      elif [ -e "$link" ]; then echo "거부: $link 는 키트·프로젝트 자체 스킬" >&2; exit 1
      else echo "원래 꺼져 있음: $q"; fi
    done ;;
  status)
    echo "도구 서랍: $LIB"; found=0
    for l in "$DEST"/*; do
      [ -L "$l" ] || continue; found=1
      t=$(readlink "$l"); [ -e "$l" ] && s="" || s="  ← 깨짐(서랍에 없음)"
      echo "  켜짐 $(basename "$l") → ${t#"$LIB/"}$s"
    done
    [ $found = 1 ] || echo "  켠 도구 없음 (키트 스킬만)" ;;
  *) sed -n '2,8p' "$0"; exit 2 ;;
esac
