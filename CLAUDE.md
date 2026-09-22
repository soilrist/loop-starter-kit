# CLAUDE.md — 이 저장소에서 일하는 모든 AI가 먼저 읽는 한 장 (키트 v2.1.1)

> **짧게 유지한다 (200줄 이내).** 규칙 원문은 여기 적지 않는다 — 아래 문서 목록에서 지금 하는 일에 맞는 문서 **하나만** 연다.
> **규칙은 `docs/conventions/` 에만 적는다.** 이 파일·스킬·에이전트·PROMPT 와 내용이 다르면 **컨벤션 문서가 이긴다.**

## 프로젝트
- 게임: 〔한 줄 소개〕 / 장르: 〔〕
- 엔진: 〔Unity / Unreal / Godot〕 〔버전〕 · 렌더 〔URP 2D 등〕 · 엔진 프로젝트 위치 〔저장소 루트 / unity·unreal·godot/〕 — 엔진별 구체 규칙은 `docs/engines/<엔진>.md`
- 설계서 `docs/DESIGN.md` · 진행 `docs/STATUS.md` · 순서 `docs/ROADMAP.md`
- 사람의 지시: `docs/feedback/INBOX.md` (맨 위가 최우선)

## 반드시 지킬 것 (원칙만 — 자세한 건 괄호 속 문서)
1. 밸런스 숫자는 루프가 정하고 `docs/DESIGN.md` §6 에 값+근거를 적는다. 사람에게 묻지 않는다. `-1` 을 커밋에 남기지 않는다. (DataDriven)
2. 캡처는 검사다, 증거가 아니다. **"통과"는 실제로 명령을 돌리고 그 출력을 STATUS 에 인용하고, `tools/jev.py evidence` 가 `SUPPORTED` 라고 했을 때만.** 판단은 이름·문자열 패턴이 아니라 실제 결과로. (Verification)
2-1. 레퍼런스 게임 하나를 **완벽하게 복제한다는 자세**로 만든다 — 시스템·콘텐츠 종류·UI 흐름은 전부, 에셋 원본·이름은 새로. 보이는 것은 레퍼런스 시트 먼저, 자리표시 품질로 합격 찍지 않는다. (Reference)
3. 자기가 바꾼 파일만 이름으로 지정해 커밋한다. (GitCommit)
4. 씬·에셋 파일을 텍스트로 함부로 고치지 않는다. 파일 이동·이름 변경은 에디터(또는 엔진 MCP 의 에셋 명령)로. 엔진별 구체 방법은 `docs/engines/<엔진>.md`. (FolderStructure)
5. 모르는 이름·폴더·형식은 지어내지 않고 해당 문서를 연다.
6. 혼자 정할지 물을지는 신호등으로: 🟢 정하고 진행 · 🟡 가정하고 `확인`(설계서에 없는 것은 항상 🟡) · 🔴 방향·돈·삭제·권리·규칙·사람만 할 수 있는 것은 `질문`. (Autonomy)
7. API 키·비밀번호를 코드·커밋에 넣지 않는다. 훅(`--no-verify`)을 우회하지 않는다.

## 너는 누구인가 (둘 중 하나)
- **감독 = 사람의 비서** (Code 탭 대화, `LOOP_LAP` 환경변수 없음) → `loop/DIRECTOR.md` 를 따른다. 사람 말을 알아듣고 INBOX 로 루프에게 시키고 검수·보고한다. 게임 코드는 직접 안 고친다. 사람이 "직접 고쳐줘"라고 명시하면 루프를 멈추고 계획 승인 후 수정 (DIRECTOR.md 예외 절).
- **루프 일꾼** (`LOOP_LAP` 환경변수 있음) → `loop/PROMPT.md` 순서만 따른다. 승인 대신 신호등 규칙. 멈추지 않는다.

## 작업 방식
- 코드·에셋을 만든 뒤 `tools/check_conventions.py` 를 돌린다. 감독은 추가로 `convention-checker` 에이전트로 점검할 수 있다(일꾼은 서브에이전트 금지).
- 개념을 설명할 땐 일반 예시보다 이 프로젝트의 실제 스크립트를 예로 든다.

## 에디터 연결 (MCP)
공통 원칙은 조회 자유·변경 조건부·Play(PIE) 중 금지 — 셋 다 같다. 엔진별 MCP 플러그인 이름·정확한 조건은 `docs/engines/<엔진>.md` "에디터 연결 (MCP)" 절.

## 문서 목록 — 언제 읽나
| 지금 하는 일 | 열 문서 |
|---|---|
| 에셋 만들기·이름 짓기 | `docs/conventions/AssetNaming.md` |
| 파일 둘 곳 고르기·폴더 만들기·파일 옮기기 | `docs/conventions/FolderStructure.md` |
| 코드 작성·수정 | `docs/conventions/CodingStyle.md` |
| 엔진별 구체 방법(에셋 이름·코드·MCP 등) | `docs/engines/<엔진>.md` |
| 몬스터·아이템·스킬 등 콘텐츠 추가 | `docs/conventions/DataDriven.md` |
| 레퍼런스 게임 따라 만들기·UI/캐릭터 품질 | `docs/conventions/Reference.md` + `docs/reference/` 시트 |
| 커밋 | `docs/conventions/GitCommit.md` |
| 브랜치 만들기·합치기 | `docs/conventions/BranchStrategy.md` |
| 버전·변경기록 | `docs/conventions/Versioning.md` |
| 검사·캡처·QA | `docs/conventions/Verification.md` + `docs/checks/<엔진>.md` |
| INBOX 읽기·쓰기 | `docs/conventions/InboxFormat.md` |
| 혼자 정할지 물을지 애매할 때 | `docs/conventions/Autonomy.md` |
| 기능 명세·버그·결정·사고기록 | `docs/templates/` 양식 복사 |

## 스킬 (작업 카드) — `.claude/skills/`
| 스킬 | 부르는 말 | 하는 일 |
|---|---|---|
| `kickoff` | "〔이런 게임〕 만들어", "〔기능〕 넣자" | 한마디 → 설계서·질문 묶음·로드맵 |
| `commit` | /commit, "커밋해줘" | 규칙대로 조각별 커밋 (직접 불렀을 때만 실행) |
| `new-script` | /new-script, "스크립트 만들어줘" | 계획 → 작성 → 검사 |
| `new-content` | /new-content, "몬스터/아이템 추가해줘" | SO 틀·데이터 에셋 추가, 숫자는 DESIGN §6 에 근거와 함께 |
| `inbox` | /inbox, "인박스에 적어줘" | INBOX 형식대로 지시·질문 추가 |
| `release` | /release, "main 에 올리자" | 합치기 조건 확인 → CHANGELOG → 태그 (승인 필수) |

## 검사 에이전트 — `.claude/agents/`
- `convention-checker` — 읽기 전용. 규칙 위반 표 + **점검한 규칙 목록**으로 보고.
