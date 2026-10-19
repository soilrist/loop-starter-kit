# 검사 모듈: Unreal  〔DRAFT — 사람 승인 후 DRAFT 표시 삭제〕

> 공통 원칙은 `docs/conventions/Verification.md`. 여기엔 **Unreal 에서 실제로 어떻게** 만 적는다.
> Unreal MCP(`ModelContextProtocol`+`AllToolsets`)가 연결돼 있으면 MCP 명령, 없으면 커맨드릿/배치 모드 명령. 둘 다 안 되면 그 층은 **"못 함"**.

## 1층 — 기계 검사 (커밋 전 필수)
| 검사 | Unreal MCP | MCP 없을 때 |
|---|---|---|
| 컴파일 에러 0 | 로그 조회(Output Log) | `UnrealBuildTool <Target> <Platform> <Config> -Project=<uproject>` |
| 이름·폴더·자리표시 | — | `python3 tools/check_conventions.py --changed --engine unreal` |
| 유닛 테스트 (Automation Spec) | 로그로 결과 확인 | `UnrealEditor-Cmd.exe <uproject> -ExecCmds="Automation RunTests <필터>; Quit" -unattended -nullrhi -log` |
| 데이터 무결성 (ID 중복·빈 참조) | Automation Spec `FAutomationTestBase` 로 만든다 | 동일 |
| 빠진 에셋 참조(Broken Reference) | 커맨드릿(`ResavePackages` 등)로 스캔 | 동일 |

## 2층 — 동작 검사
- **Automation Spec/Functional Test**로 실제 입력을 넣는다: `FAutomationTestBase` 파생 테스트에서 `PlayerController` 로 키·버튼 입력을 흉내내거나, 레벨에 `AFunctionalTest` 액터를 배치.
- **UI 는 함수 직접 호출 금지** → `FSlateApplication::Get().ProcessKeyDown`/포인터 이벤트로 위젯 트리에 실제 이벤트 주입. 위젯이 다른 창에 가려져 있으면 히트테스트가 실패해야 정상.
- 대규모 자동 플레이는 **Gauntlet**(`RunUAT.bat RunUnreal ...`)로 — 여러 맵을 돌며 크래시·에러 로그를 모아 리포트.
- 테스트 이름: `<시스템>.<상황>.<기대>` (Automation Spec 관례, 점 구분: `Combat.ThreeHits.KnocksBack`)

## 3층 — 눈 검사 (캡처)
- 캡처: Automation Spec 안에서 `AutomationCommon::TakeScreenshot` 또는 `FScreenshotRequest::RequestScreenshot`; Gauntlet 은 스텝마다 자동 캡처.
- 해상도 고정: 〔1920x1080 / 픽셀아트면 기준 해상도 × 정수배〕
- 체크리스트: Verification.md "캡처 눈 검사 체크리스트"
- **자동으로 잡을 수 있는 것은 코드로:** 분홍색(#FF00FF 근처, 누락 머티리얼 기본색) 픽셀 비율, 완전 흰/검은 화면, `UMG` 텍스트에 `TBD`·플레이스홀더 문자열 포함 여부 → Automation Spec 으로.

## 알려진 함정
- 에디터가 켜진 상태에서도 `-Cmd` 커맨드렛은 돈다(락 파일 없음 — 맥 5.8 실증). 단 **uproject 는 반드시 절대경로**: 상대경로면 엔진 `Binaries/` 기준으로 찾아 `Unable to find project file` 로 죽는다.
- 커맨드렛 종료코드 1 은 곧 실패가 아니다. `-unattended` 에서 `Error:` 줄이 하나라도 있으면 끝에 `Failure - N error(s)` 를 찍고 1 로 나간다 — 시험 결과는 로그의 `Result={Success}`/`{Fail}` 줄로 판정하고, `Error:` 줄은 Verification 9 대로 하나씩 본다.
- **헤드리스 실행엔 크래시 리포터 대화상자를 막는 플래그를 붙인다**: `"-ini:EditorSettings:[/Script/UnrealEd.CrashReportsPrivacySettings]:bSendUnattendedBugReports=False"`. 없으면 `ensure` 하나에 `CrashReportClient` 가 떠서 사람 화면에 시스템 대화상자가 쌓인다. 에디터는 스크립트 종료나 `kill -9` 로 끈다(`-TERM` 은 크래시 경로를 탄다).
- **루프가 띄우는 게임 실행은 전부 `-RenderOffscreen`, `-windowed` 금지** — 사람 화면에 저절로 움직이는 창이 뜨면 사람이 진짜 플레이로 착각한다. 자동 입력 검사 스위치가 켜진 실행은 화면에 「검사용 자동 입력 중」 같은 띠를 띄운다.
- `-nullrhi` 로 돌리면 렌더링이 없어 3층 캡처는 실패한다 — 캡처가 필요한 테스트는 `-nullrhi` 없이(또는 `-RenderOffscreen`) 돌린다.
- 셰이더 컴파일이 안 끝난 상태에서 첫 실행하면 첫 프레임이 전부 분홍색 — 캡처 전 셰이더 컴파일 완료를 기다린다(로그의 `Shaders Left to compile` 확인).
- `-RenderOffscreen` 첫 실행이 몇 분간 프레임이 안 넘어가는 건 정지가 아니라 콜드 셰이더 캐시 컴파일일 수 있다 — 프로세스가 CPU 를 쓰고 있으면 기다린다. "로그가 안 는다" 만으로 정지라고 적지 않는다.
- **검사 전용 명령줄 스위치**(`-<게임>StandAt=X,Y`·`-<게임>Capture=<파일>` 처럼 자리·화면을 정해 찍는 것)는 3층을 루프가 혼자 찍게 하는 열쇠다 — "PIE·로그인이 필요해 감독 몫" 으로 넘기지 말고 스위치를 만든다. 게임 소스는 명령줄을 **도우미 하나**로만 읽고, 그 도우미는 Shipping 빌드에서 늘 false 를 돌려준다(출시 빌드에서 검사 스위치가 열리면 치트가 된다). 스위치마다 로그 한 줄(`검사용 … (-…)`)을 찍어 걸렸는지 확인한다.
- 자동 시험(`IMPLEMENT_…AUTOMATION_TEST`)은 반드시 `#if WITH_DEV_AUTOMATION_TESTS … #endif` 안에. 파일 끝 `#endif` 뒤에 붙이면 에디터 빌드·시험은 통과하고 Shipping 빌드만 컴파일 오류 — `check_conventions.py` R16 이 잡는다.
- 바이너리 에셋(`.uasset`/`.umap`)은 커맨드릿·MCP 로만 다뤄야 리다이렉터가 안 깨진다 — `docs/engines/unreal.md` "언리얼 파일 다루기" 참고.
