# 루프 스타터 키트 v2.0 (확정)

**"이거 만들어!" 한마디면 알아서 만들고, 정말 필요할 때만 물어보는 AI 개발팀**을 게임 프로젝트에 심는 키트예요.

## 비유로 보면
- **감독 = 형의 비서.** 형은 클로드 데스크탑 Code 탭에서 이 비서하고만 대화해요.
- **루프 일꾼 = 밤새 일하는 직원.** 30분마다 새로 출근해서 일 한 조각을 하고 기록을 남겨요.
- **규칙 문서 = 회사 규정집.** 둘 다 같은 규정집을 봐요.
- **검사기와 훅 = 문 앞 검문소.** 규칙을 어긴 커밋은 아예 못 들어가요.
- **신호등 = 비서의 판단 기준.**
  - 🟢 알아서 해요.
  - 🟡 일단 하고 "이렇게 했어요"라고 알려요.
  - 🔴 숫자, 방향, 돈, 삭제, 권리 문제는 꼭 물어봐요.

## 확정된 규칙
| 항목 | 정한 것 | 이유 |
|---|---|---|
| 커밋 | `feat(combat): 3연타 추가` + 꼬리말 `Loop:` `Checks:` `Slice:` | 훅이 형식·바퀴 번호·검사 기록까지 기계로 검증, 조각별 추적 |
| 에셋 이름 | 접두어 방식 (예 Unity `SPR_Player_Hero_Run_01`) — 엔진별 구체 규칙은 `docs/engines/<엔진>.md` | 이름이 ID처럼 검색됨 |
| 코드 이름 | 엔진별 공식 가이드 (Unity `m_`/`k_`/`s_`, Unreal `b`/PascalCase, Godot snake_case) — `docs/engines/<엔진>.md` | 각 엔진 커뮤니티가 이미 읽을 줄 아는 규칙 |

## 들어 있는 것
| 파일 | 하는 일 |
|---|---|
| `CLAUDE.md` | 모든 AI가 제일 먼저 읽는 한 장 |
| `docs/conventions/` | 규칙 원문 (이름·폴더·코드·데이터·커밋·브랜치·버전·검사·INBOX·**자율 판단**) |
| `.claude/skills/` | `kickoff`(한마디→설계·로드맵), `new-script`, `new-content`, `commit`, `inbox`, `release` |
| `.claude/agents/convention-checker.md` | 읽기 전용 규칙 점검 AI |
| `.claude/settings.json` | 위험 명령 차단 (`git add -A`, `push --force`, `rm -rf` …) |
| `.githooks/` | 커밋 메시지 형식·규칙 위반을 **커밋 순간에 막음** |
| `tools/check_conventions.py` | 이름·엔진별 사이드카 파일·코드 접두어·미정 숫자 자동 검사 (점검한 규칙 목록 출력) |
| `loop/` | `PROMPT.md`(일꾼), `DIRECTOR.md`(비서), `loop.sh`·`env.sh`·`ctl.sh`(맥 launchd 실행기) |
| `docs/DESIGN.md` `ROADMAP.md` `STATUS.md` `feedback/INBOX.md` | 기획서·조각 목록·바퀴 기록·우편함 |
| `docs/templates/` | 기능 명세·버그·결정·사고기록 양식 |

---

## 1단계: 설치 (맥 → 클로드 데스크탑 → Code 탭)
압축을 풀어 둔 뒤, **프로젝트 폴더를 연 Code 탭 세션**에 아래를 그대로 붙여넣으세요.

```
루프 스타터 키트 v2 를 이 프로젝트(〔프로젝트 이름〕)에 설치해 줘. 키트 위치: 〔압축 푼 loop-starter-kit 폴더 경로〕
키트의 README.md "설치 규칙"을 먼저 읽고 그대로 따라 줘.
끝나면 결과를 5줄로 보고하고, 내가 정해야 할 것만 모아서 물어봐.
루프는 아직 켜지 마.
```

## 설치 규칙 (설치하는 AI가 읽는 부분)
1. **먼저 살펴보기**
   - 어떤 엔진인지 확인한다 (`Assets/`+`ProjectSettings/`=Unity, `*.uproject`=Unreal, `project.godot`=Godot). 애매하면 물어본다.
   - git 저장소 여부, 엔진 프로젝트 위치(루트 / 하위 폴더), 엔진 버전을 확인한다 — 구체 확인 방법은 `docs/engines/<엔진>.md`.
   - 이미 있는 `CLAUDE.md`·`docs/`·`loop/`·`.gitignore`·기획 문서도 확인한다.
   - 발견한 걸 먼저 보여 준다.
2. **덮어쓰지 않기**
   - 이미 있는 파일은 차이를 보여 주고 합칠 방법을 제안한다. 사람 승인 후에만 합친다.
   - 옛 루프 파일(`loop/`)이 있으면 `loop/_v1_backup/` 으로 옮긴 뒤 새 파일을 넣는다. 지우지 않는다.
3. **복사**
   - 키트 파일을 복사하되 `README.md` 는 `docs/LOOP_KIT_README.md` 로 넣는다.
   - 실행 권한: `chmod +x loop/*.sh .githooks/*`
4. **이름 맞추기**
   - `loop/env.sh` 의 `LOOP_SLUG` 를 프로젝트 이름(영어 소문자·하이픈, 예 `joseon-sword`)으로 바꾼다.
   - 문서 속 예시 네임스페이스 `MyGame` 은 프로젝트 이름(PascalCase, 예 `JoseonSword`)으로 바꿔도 된다. 🟢
5. **CLAUDE.md 〔〕 칸 채우기**
   - 알 수 있는 건 채운다.
   - 게임 소개처럼 모르는 건 🔴 질문 목록에 올린다.
6. **git 설정**
   - `git config core.hooksPath .githooks`
   - `develop` 브랜치가 없으면 만들고, **`git checkout develop` 으로 옮겨 둔다** (루프는 develop 에서만 돈다).
   - `git lfs version` 이 실패하면 `.gitattributes` 의 `#LFS-BEGIN`~`#LFS-END` 사이 줄을 주석 처리한다 (Unreal 은 `.uasset`/`.umap` 이 이 블록에 있어 LFS 가 특히 중요 — 안 되면 🔴 질문).
   - **Unity 일 때만**: 설치된 Unity 버전의 `UnityYAMLMerge` 경로를 찾아(맥: `/Applications/Unity/Hub/Editor/<버전>/Unity.app/Contents/Tools/UnityYAMLMerge`)
     `git config merge.unityyamlmerge.name "Unity SmartMerge"` 와
     `git config merge.unityyamlmerge.driver "'<경로>' merge -p %O %B %A %A"` 를 설정한다. 못 찾으면 보고만.
     `Project Settings > Editor > Asset Serialization` 이 Force Text 인지 확인하고, 아니면 🔴 질문에 올린다.
   - Unreal/Godot 은 이 단계 불필요 (씬·에셋이 텍스트/바이너리 다루는 방식이 달라 `.gitattributes` 설정으로 충분 — `docs/engines/<엔진>.md`).
7. **검사**
   - `python3 tools/check_conventions.py` 를 돌린다 (엔진 프로젝트가 하위 폴더면 `--root <폴더>`).
   - 기존 파일의 위반은 **지금 고치지 않는다.** 목록만 보여 주고, ROADMAP 맨 앞에 `M0-00 기존 파일 규칙 맞추기` 조각으로 넣는다. 파일 이동은 루프가 에디터·엔진 MCP 로 한다.
8. **루프 시험**
   - `loop/ctl.sh try` 로 claude 를 부르지 않는 시험 두 바퀴를 돌린다 (번호는 `logs/lap.dry` 에 따로 셈).
   - `logs/usage.csv` 에 `dry` 두 줄이 생겼는지 확인한다.
   - `command -v claude` 와 `~/.claude-loop-nc` 폴더가 있는지 확인해 보고한다.
9. **커밋**
   - `chore(loop): 루프 스타터 키트 v2 설치` 로 커밋한다 (훅 통과 확인).
   - 사람이 확인한 뒤에만 커밋한다.
10. **보고**: 설치된 것 / 합친 파일 / 기존 위반 수 / 사람이 정할 것.

---

## 2단계: 쓰는 법 (전부 Code 탭에서 말로)
| 형이 할 말 | 일어나는 일 |
|---|---|
| **"〔프로젝트 이름〕 이렇게 만들자: 〔한두 줄〕"** | 비서가 설계서 초안을 쓰고 질문 묶음을 보냄. 형이 답하면 로드맵까지 만듦 |
| **"켜"** | 준비 점검 후 루프 시작 (로그인하면 자동으로 다시 켜짐) |
| **"어때?"** | 3줄 보고 |
| **"고블린 더 빠르게"** | 비서가 숫자를 되물은 뒤 루프에게 지시 |
| **"알아서 해"** | 방향은 비서 추천대로. 숫자는 그래도 물어봄 |
| **"꺼"** | 하던 조각 마무리하고 멈춤 |

## 출처
- Unity `.gitignore`: github/gitignore
- C# 이름 규칙: Unity 공식 *Naming and code style tips* / *C# Style Guide (Unity 6)*
- 폴더: Unity 공식 *Organizing your project*
- 에셋 접두어: justinwasilenko/Unity-Style-Guide
- Unreal `.gitignore`/`.gitattributes`: github/gitignore (UnrealEngine.gitignore) + Epic 공식 *Setting Up Unreal Engine Projects With Perforce/Git* 가이드
- C++ 이름 규칙: Epic 공식 *Coding Standard*
- Godot `.gitignore`: godotengine/godot (프로젝트 템플릿) + github/gitignore (Godot.gitignore)
- GDScript 이름 규칙: Godot 공식 *GDScript style guide*
- 커밋: Conventional Commits 1.0
- 버전: SemVer 2.0
- 변경기록: Keep a Changelog 1.1
- 설정 구조(CLAUDE.md·규칙 문서·스킬·검사 에이전트·MCP 경계): "유니티 팀 프로젝트 AI 설정" 교재 (엔진 무관 구조로 일반화)
