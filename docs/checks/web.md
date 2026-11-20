# 검사 모듈: 웹 (three.js · 캔버스 · 브라우저 게임)

> 공통 원칙은 `docs/conventions/Verification.md`. 여기엔 **브라우저 게임에서 실제로 어떻게** 만 적는다.
> 도구: `tools/skills.sh on test-playable-web-games` (Playwright 로 실제 브라우저에서 끝까지 시험). Playwright 브라우저가 없으면 `npx playwright install chromium`.

## 1층 — 기계 검사 (커밋 전 필수)
| 검사 | 명령 | 인용할 줄 |
|---|---|---|
| 타입·빌드 에러 0 | `npx tsc --noEmit && npm run build` | 빌드 마지막 줄 (`built in …`) |
| 이름·폴더·자리표시 | `python3 tools/check_conventions.py --changed` | `✔ 규칙 검사 통과 …` |
| 데이터 무결성 (ID 중복·빈 참조) | `src/data/*.json` 을 읽는 단위 시험 (`npx vitest run`) | `Tests  N passed` |

## 2층 — 동작 검사 (실제 입력)
- Playwright 로 **실제 키·마우스 입력**을 넣는다: `page.keyboard.press('Space')`, `page.mouse.click(x, y)`. 게임 함수를 `page.evaluate()` 로 직접 부르는 것은 통과 근거가 아니다 (Verification.md 2).
- 결과는 화면 밖 상태로 확인: 게임이 `window.__game = { score, hp, scene }` 같은 **읽기 전용** 상태를 내놓게 하고 `expect(await page.evaluate(() => window.__game.score)).toBeGreaterThan(0)`.
- 콘솔 에러 0: `page.on('pageerror')`·`console` 의 `error` 를 모아 시험 끝에 0 인지 단정.
- 명령: `npx playwright test` → 인용은 `N passed (…s)` 줄.

## 3층 — 눈 검사 (캡처)
- 캡처: `await page.screenshot({ path: 'captures/<조각>-<상황>.png' })` — 쓰는 사람이 밟는 길(시작 화면 → 클릭 → 플레이)로 그 장면에 닿은 뒤 찍는다.
- 뷰포트 고정: 데스크톱 `1280x720`, 모바일 대상이면 `devices['iPhone 13']` 도 한 장.
- 찍은 그림을 **Read 로 열어** 체크리스트와 플레이어 눈 다섯 칸을 본 뒤 `3층 통과(…, captures/<파일>.png)` 로 적는다. 연 그림 이름이 STATUS 에 없거나 안 열었으면 `lap_audit.py` 가 INBOX `결함` 으로 올린다.
- **코드로 잡을 것:** 캔버스가 다 검정/흰색인지(픽셀 표본), WebGL 컨텍스트 손실(`webglcontextlost`), 화면에 `undefined`·`NaN`·`TBD` 글자.

## 알려진 함정
- 헤드리스 Chromium 은 GPU 없이 SwiftShader 로 그린다 — 느리고 일부 셰이더가 다르게 나온다. 비주얼 판정이 중요하면 `--headed` 또는 `launchOptions: { args: ['--use-angle=metal'] }`. 그래도 안 되면 "못 함(헤드리스 렌더 제한)".
- 첫 프레임 전에 찍으면 빈 캔버스 → `await page.waitForFunction(() => window.__game?.ready)` 뒤에 찍는다.
