# 콘텐츠는 데이터로

## 한 줄 요약
**몬스터·아이템·스킬·퀘스트·대사는 코드가 아니라 데이터 파일(ScriptableObject)로 만든다.**
코드는 "고블린이 뭔지" 몰라야 하고, "적이 어떻게 움직이는지"만 안다.

비유: 코드는 **게임기**, 데이터는 **게임 카트리지**. 새 몬스터 = 새 카트리지 꽂기. 게임기를 뜯지 않는다.

## 규칙
1. **새 몬스터·아이템 추가에 C# 파일이 늘어나면 잘못된 것.** 새 `SO_` 에셋 하나 + 필요하면 프리팹 하나.
2. **데이터 클래스(틀)** 는 `Scripts/Runtime/Data/` 에, **데이터 에셋(값)** 은 `Assets/_Project/Data/종류/` 에.
3. **숫자 칸은 사람이 채운다.**
   - 설계서(DESIGN.md)에 숫자가 있으면 그대로 옮긴다.
   - 없으면 값에 **자리표시 `-1`** (또는 문자열 `"TBD"`)을 넣고, INBOX 에 `질문:` 을 남긴다.
   - `tools/check_conventions.py` 가 `Data/` 안의 `-1`/`TBD` 를 **경고로 센다** → 사람이 한눈에 "아직 안 정한 숫자" 목록을 본다.
   - 왜: AI가 "적당히" 넣은 숫자는 아무도 모르게 굳는다.
   - 테스트는 테스트 전용 값을 따로 만든다 (Verification.md 6), 런타임은 `-1` 을 만나면 에러 로그 (Verification.md 7).
4. **ID 는 문자열 고정값**, 에셋 이름과 맞춘다: `SO_Enemy_Goblin` → `id = "enemy.goblin"`. 한번 정한 ID 는 바꾸지 않는다(세이브 파일이 깨짐).
5. **다른 데이터 참조는 에셋 참조로**, 이름 문자열로 찾지 않는다. (드롭 테이블 → `SO_Item` 직접 연결)
6. 표로 관리하는 게 편한 대량 데이터(아이템 200개 등)는 `_Source/tables/*.csv` 를 원본으로 두고, 에디터 스크립트로 `SO_` 를 생성한다. **이때는 CSV 가 진짜, SO 는 결과물** — SO 를 손으로 고치지 않는다. 어느 방식을 쓰는지 decisions/ 에 기록.

## 틀 예시
데이터 클래스·데이터 에셋의 실제 코드 예시는 엔진마다 다르다 (Unity `ScriptableObject`, Unreal `DataAsset`/`DataTable`, Godot `Resource`) → **`docs/engines/<엔진>.md`** 의 "코드 — 예시" 절 참고 (예: Godot `HealthConfig`/`res_player_hero_health.tres`, Unreal `UHealthConfig`/`DA_Player_Hero_Health`).

## 검사
- 에디터 시작·빌드 전: 모든 데이터 에셋의 `id` 중복 없음, 참조 비어 있지 않음 — 구체 방법은 `docs/checks/<엔진>.md`.
