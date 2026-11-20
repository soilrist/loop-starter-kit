# 엔진 모듈: 웹 (three.js · 캔버스 · 브라우저 게임)

> 공통 원칙은 `docs/conventions/AssetNaming.md` · `CodingStyle.md` · `FolderStructure.md` · `DataDriven.md`.
> 여기엔 **웹에서 실제로 어떻게** 만 적는다. 검사 방법은 `docs/checks/web.md`.
> 도구: `threejs-game-director` (입구) + 지금 일에 맞는 `threejs-*` 하나 — 감독이 바퀴 사이에 `tools/skills.sh on` 으로 켠다 (일꾼은 못 켠다, 필요하면 INBOX `질문`). 표는 `docs/tools/CATALOG.md` 4절.

## 폴더
| 무엇 | 어디 |
|---|---|
| 게임 코드 | `src/` (진입 `src/main.ts`) |
| 데이터(밸런스 숫자·몬스터·아이템) | `src/data/*.json` — 코드에 숫자를 박지 않는다 (DataDriven) |
| 모델·텍스처·소리 | `public/assets/<종류>/` (`models/`·`textures/`·`audio/`) |
| 시험 | `tests/` (Playwright `*.spec.ts`), 캡처는 `captures/` |

## 에셋 이름
- 파일·폴더는 kebab-case: `goblin-warrior.glb`, `rock-diffuse.webp`, `ui-button-hover.png`.
- 모델은 `.glb` 하나로 (텍스처 포함). 블렌더에서 내보낼 때 `blender-export-pipelines` 규칙.
- 텍스처는 `.webp`/`.ktx2`. 접미어는 Unity 표와 같은 뜻(`-d` 색 · `-n` 노멀 · `-orm`).

## 코드 이름 (TypeScript 관례)
| 대상 | 규칙 | 예 |
|---|---|---|
| 클래스·타입 | PascalCase | `EnemySpawner`, `ItemData` |
| 함수·변수 | camelCase | `spawnWave()`, `hitPoints` |
| 상수 | UPPER_SNAKE | `MAX_ENEMIES` (값은 data JSON 에서 읽는다) |
| 파일 | kebab-case, 클래스 하나면 그 이름 | `enemy-spawner.ts` |

## 함정
- `requestAnimationFrame` 시간에 기대는 이동은 탭이 뒤로 가면 멈춘다 → `clock.getDelta()` 를 상한(예: 0.1초)으로 자른다.
- 셰이더·텍스처를 매 프레임 새로 만들면 메모리가 샌다 → 만든 것은 `dispose()`. `threejs-debug-profiler` 로 확인.
- `npm run dev` 서버를 띄운 채 끝내지 않는다 — 시험은 Playwright 의 `webServer` 설정으로 띄우고 끈다.
