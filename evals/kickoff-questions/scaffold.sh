#!/bin/bash
# 평가용 작업 폴더에 키트를 깔아 준다 — 에이전트가 규칙 원문을 읽을 수 있게.
# 케이스마다 같은 사본이 있어야 한다 (eval 이 case 폴더 밖 스크립트를 거부함). 원본은 evals/scaffold.sh, 바꾸면 `for d in evals/*/; do cp evals/scaffold.sh "$d"; done`.
set -e
SRC="${KIT_SRC:-$(cd "$(dirname "$0")/../.." && pwd)}"
[ -f "$SRC/CLAUDE.md" ] || { echo "키트 루트를 못 찾음: $SRC (KIT_SRC 로 지정)"; exit 1; }
for p in CLAUDE.md docs loop tools .claude .editorconfig .gitignore; do cp -R "$SRC/$p" "$PWD/"; done
git init -q && git checkout -q -b develop && git add -A >/dev/null && git -c user.name=eval -c user.email=eval@local commit -q -m "chore: eval scaffold"
echo "scaffold ok in $PWD ($(git branch --show-current))"
