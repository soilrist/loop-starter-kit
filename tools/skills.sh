#!/usr/bin/env bash
# 도구 서랍의 스킬을 이 프로젝트에서 켜고 끈다.
#   서랍 = ~/.claude/skill-library/<owner>_<repo>/ (클로드가 안 읽는 곳 — 깔려 있어도 꺼진 상태)
#   켜기 = .claude/skills/<이름> 에 심볼릭 링크 → 감독·루프 일꾼 둘 다 보게 됨
#   끄기 = 그 링크만 지움. 키트 자체 스킬(진짜 폴더)은 절대 안 건드린다.
# 쓰는 법: tools/skills.sh list [낱말] | on <이름|저장소/이름>... | off <이름>... | status
# 무엇을 켤지는 docs/tools/CATALOG.md. 켠 스킬 설명은 매 호출에 실리니 조금만 켠다.
set -euo pipefail
LIB="${SKILL_LIBRARY:-$HOME/.claude/skill-library}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
DEST="$ROOT/.claude/skills"

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
  on)
    [ $# -gt 0 ] || { echo "on 뒤에 이름" >&2; exit 2; }
    mkdir -p "$DEST"
    for q in "$@"; do
      link="$DEST/${q#*/}"
      if [ -e "$link" ] && [ ! -L "$link" ]; then echo "거부: $link 는 키트·프로젝트 자체 스킬" >&2; exit 1; fi
      src=$(resolve "$q") || exit 1
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
