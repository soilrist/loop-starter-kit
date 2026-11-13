# 프로필: game

**언제** — 결과물이 사람이 플레이하는 게임일 때.

**결과물** — 실행되는 빌드. 조각 하나 = 플레이어가 화면에서 알아챌 변화 하나.

**검사 3층**
| 층 | 여기서 뜻하는 것 |
|---|---|
| 1 기계 | 컴파일 0 에러 + `tools/check_conventions.py` 통과 |
| 2 동작 | 엔진 테스트·플레이 모드로 실제 입력 → 상태 변화 확인 (`docs/checks/<엔진>.md`) |
| 3 눈 | 캡처를 직접 보고 `conventions/PlayerEye.md` 다섯 칸 + 레퍼런스 시트 대조 |

**쓰는 사람 눈 다섯 칸** — `conventions/PlayerEye.md` 그대로 (플레이어).

**이 종류의 🔴** — 스토어 제출·결제 상품 등록·세이브 형식을 호환 안 되게 바꾸기·핵심 재미(DESIGN §2) 바꾸기.

**여는 문서·스킬**
- 엔진: `docs/engines/<엔진>.md`, `docs/checks/<엔진>.md`
- 규칙: `conventions/Reference.md`, `AssetNaming.md`, `DataDriven.md`, `FolderStructure.md`
- 스킬: `new-script` · `new-content` · `new-visual` · `reference-sheet`
- 설계서: `docs/DESIGN.md` 는 GDD 로 쓴다 (§6 밸런스 숫자 포함)

**안 쓰는 것** — 없음 (키트의 게임 문서를 전부 쓴다).

**이 종류의 함정**
- 손맛·재미는 사람만 판정한다 → 마일스톤 끝마다 `[!] 사람: 🎮 해 보기`.
