---
name: new-content
description: 몬스터·아이템·스킬·퀘스트·대사 같은 게임 콘텐츠를 추가해 달라는 요청("고블린 추가해줘", "포션 아이템 만들어줘")을 받았을 때 사용. 코드가 아니라 데이터 에셋으로 추가한다.
---

1. `docs/conventions/DataDriven.md`, `docs/conventions/AssetNaming.md` 를 읽는다.
2. `docs/DESIGN.md` 에서 해당 콘텐츠 항목을 grep 으로 찾는다 (통째로 읽지 않음).
3. 이미 있는 데이터 틀을 쓴다 (엔진별 코드 위치·형식은 `docs/engines/<엔진>.md`). 틀이 없을 때만 new-script 절차로 틀을 만든다.
4. 데이터 에셋을 엔진별 이름·폴더 규칙대로 만든다 (에디터/엔진 MCP 로, 구체 규칙·예시는 `docs/engines/<엔진>.md`).
5. DESIGN 에 있는 숫자만 채운다. 없는 숫자는 `-1` 로 두고 INBOX 에 `질문` 을 한 줄로 모아 남긴다 (형식은 `InboxFormat.md`).
6. ID 는 `분류.대상` 소문자 (`enemy.goblin`) — 에셋 이름에서 기계적으로 만든다. 기존 ID 와 겹치지 않는지 확인.
7. `python3 tools/check_conventions.py --changed` 로 이름·자리표시 경고를 확인하고 보고한다.

이 파일과 규칙 문서 내용이 다르면 규칙 문서를 따른다.
