# 도구 목록 (CATALOG)

**다 깔려 있고, 다 꺼져 있다.** 이 프로젝트에 필요한 것만 켠다.

> **무료만 쓴다.** 유료 API·크레딧(OpenAI·fal·Tripo·Meshy·Gemini·ElevenLabs·xAI·Scenario…)을 부르는 스킬은 `skills.sh on` 이 거부한다 (스킬 폴더에서 유료 키 이름을 찾아 막음). 풀려면 `on --paid` — 돈이라 🔴, 사람이 "써도 돼"라고 한 그 건만.

- **서랍**: `~/.claude/skill-library/<owner>_<repo>/`. 클로드는 여기를 읽지 않으므로, 깔려 있어도 스킬 목록에 안 실린다.
- **켜기**: `tools/skills.sh on <이름>`. `.claude/skills/<이름>` 에 링크가 생기고, 감독과 루프 일꾼 둘 다 그 스킬을 본다.
- **끄기**: `tools/skills.sh off <이름>`. 링크만 지운다. 키트 자체 스킬(진짜 폴더)은 거부한다.
- **보기**: `tools/skills.sh status` 는 켠 것만, `tools/skills.sh list <낱말>` 은 서랍 전체에서 찾는다. 이름이 겹치면 `저장소/이름` 으로 쓴다.
- **켜는 때**: kickoff 0단계에서 프로필·엔진·아트 방향이 정해진 뒤, 아래 표에서 고른다.
- **얼마나 켜나**: 일꾼에게는 **5개 안팎**. 켠 스킬의 설명은 매 호출에 실려 토큰을 먹는다.
- **기록**: 켠 이유는 `CLAUDE.md` "만드는 도구" 칸에 한 줄 적는다.

**"일꾼" 칸이 뜻하는 것**

| 값 | 뜻 |
|---|---|
| ✅ | 루프 일꾼에 켜도 됨 |
| 감독 | 사람 판단이 필요하다. 감독이 쓸 때만 켜고 다 쓰면 끈다(켜 두면 일꾼도 본다). |
| 💰 막힘 | 유료. `skills.sh` 가 거부한다. 같은 일은 무료 대안으로. |
| 참고 | 켜지 않는다. 읽고 규칙만 가져온다. |

**무료 대안** — 그림·모델·소리를 돈 없이 만드는 길

- 3D·2D 그림: 블렌더 스크립트로 만들고 렌더해서 스프라이트로 뽑는다 (`blender-*`).
- 웹 게임 그림: three.js 절차적 모델·셰이더 (`threejs-aaa-graphics-builder`).
- 생성 AI 가 꼭 필요하면: RTX4090 노드의 로컬 모델(ComfyUI 등, 미설치) — 전기세만. 맥 로컬 추론은 금지.

## 1. 기획

| 스킬 | 서랍 | 키·비용 | 일꾼 | 언제 |
|---|---|---|---|---|
| `game-design` | OpenDCAI_GameFactory-3A | 없음 | 감독 | 요구·대본을 이야기, 챕터 계획, 에셋 목록으로 바꾼다. kickoff 3~4단계를 돕는다. |
| `game-feel` | OpenDCAI_GameFactory-3A | 없음 | ✅ | 타격감·카메라·피드백을 다듬는 조각 |
| `design-action-combat` · `design-game-encounters` · `author-game-levels` · `tune-enemy-ai` | MengTo_Skills | 없음 | ✅ | 액션 전투·전투 구성·레벨·적 AI. 웹 기준이지만 원칙은 엔진과 무관하다. |
| (문서) eremes81_game-design-ai-practice | 서랍 | — | 참고 | AI 와 기획하는 실전 예시 |

## 2. 2D 아트

| 스킬 | 서랍 | 키·비용 | 일꾼 | 언제 |
|---|---|---|---|---|
| `sprite-gen` | aldegad_sprite-gen | OpenAI(있음) 또는 xAI. 장당 과금 | 💰 막힘 | 스프라이트 시트, 걷기·공격 프레임. CLI 는 `sprite-gen`. 돈이 드니 감독이 뽑고, 일꾼은 결과 PNG 만 쓴다. |
| `scenario-*` (179개) | scenario-labs_skills | Scenario 키(없음) | 💰 막힘 | 생성 모델 조합. 키를 받으면 필요한 것 1~2개만 켠다. |
| (도구) handsupmin_mono-pix | 서랍 | 없음 | 참고 | 단색 픽셀 아트 규칙 |

## 3. 3D·모션

| 스킬 | 서랍 | 키·비용 | 일꾼 | 언제 |
|---|---|---|---|---|
| `blender-*` (28개: core·character-rigging·animation·retopology-uv·export-pipelines·game-optimization·asset-qa …) | EL4CTEO_blender-skills | 없음. Blender 는 `~/Desktop/Blender.app` | ✅ (필요한 것 2~3개) | 블렌더로 모델링·리깅·내보내기를 할 때. 보통 `blender-core` 와 그 일에 맞는 하나를 켠다. |
| `build-rigged-game-assets` · `build-game-monster-system` | MengTo_Skills | 없음 | ✅ | 리깅된 캐릭터·몬스터의 규격(소켓·히트박스) |
| `threejs-3d-generator` | majidmanzarpour_threejs-game-skills | Tripo(없음) | 💰 막힘 | 글이나 그림을 3D 로. 엔진과 무관하게 GLB/FBX 로 받는다. |
| GameFactory `asset_qa/*` | OpenDCAI_GameFactory-3A | 없음 | ✅ | 이미지·3D·모션·오디오 에셋 검수표 |
| (GPU) Motion2MixamoRig · UniMate | 서랍 | GPU 필요 | 참고 | 맥에서 돌리지 않는다. RTX4090 노드에 설치해야 한다(미설치). |

## 4. 웹·three.js 게임

| 스킬 | 서랍 | 키·비용 | 일꾼 | 언제 |
|---|---|---|---|---|
| `threejs-game-director` (입구) + `threejs-gameplay-systems` · `threejs-aaa-graphics-builder` · `threejs-game-ui-designer` · `threejs-debug-profiler` · `threejs-qa-release` | majidmanzarpour_threejs-game-skills | 없음 | ✅ | three.js 게임 전반. director 와 지금 하는 일에 맞는 하나를 켠다. |
| `threejs-image-generator` · `threejs-audio-generator` | 위와 같음 | Gemini · ElevenLabs(없음) | 💰 막힘 | 이미지·소리 생성 |
| `create-game-vfx` · `build-game-camera-controls` · `build-game-audio-feedback` | MengTo_Skills | 없음 | ✅ | 이펙트·카메라·소리 피드백 |
| `video-to-game` | lovisdotio_video-to-game | fal(없음). 영상 생성 과금 | 💰 막힘 | 생성 영상 프레임을 게임 화면 소스로 쓴다. 프로토타입·분위기 잡기용. |
| `3dviz-pro-max` | viettranx_3dviz-pro-max | 없음 | ✅ | 설명용 3D 장면·인터랙티브 모델 |
| (예제) LinearAbiltyCastingThreeJS · mykonos-island-voxels · 3d-vibe-coding-handbook | 서랍 | — | 참고 | 스킬 시전, 복셀 섬, 바이브 코딩 예제 코드 |

## 5. 검증·성능

| 스킬 | 서랍 | 키·비용 | 일꾼 | 언제 |
|---|---|---|---|---|
| `test-playable-web-games` | MengTo_Skills | 없음(playwright 설치됨) | ✅ | 웹 게임을 실제 브라우저로 끝까지 시험한다. 눈 검사의 근거가 된다. |
| `game-dev-combat-skill-polish` · `game-dev-combat-animation` | MengTo_Skills | 없음 | ✅ | 스킬과 전투 애니메이션을 블라인드 채점하고 고친다. |
| `game-perf` | gykim80_andrew_game_perf | 없음 | ✅ | Unity·Unreal 성능 점검 |
| `create-vfx-effects` | OpenDCAI_GameFactory-3A | 없음 | ✅ | Unity·UE5 이펙트 |

## 켜지 않는 것

**dudwns0921_claude-gamedev-kit** (`init` · `board` · `cycle` · `ceo` · `playtest` …)

모든 도구 호출마다 걸리는 훅과 외부 보드 서버로 보내는 기능이 있다. 우리 루프와 역할이 겹치고 충돌하므로 켜지 않는다. `balance-table` · `gdd-sync` 의 생각만 참고한다.

## 서랍 채우기 (새 맥 · 갱신)

**저장소 받기**

```bash
mkdir -p ~/.claude/skill-library && cd ~/.claude/skill-library
git clone --depth 1 --filter=blob:limit=3m https://github.com/<owner>/<repo> <owner>_<repo>
```

받을 저장소 목록은 위 표의 "서랍" 칸에 있다.

**갱신**: 각 폴더에서 `git pull` 을 실행한다.

**추가로 깔 것**

- `sprite-gen`: `uv tool install -e ~/.claude/skill-library/aldegad_sprite-gen`
- threejs-game-skills 폴더: `npm install`
- Playwright 브라우저: `npx playwright install chromium`

**처음 받는 저장소**: 켜기 전에 감독이 훅·외부 전송·설치 스크립트를 훑어본다.
