# CLAUDE.md — 이 저장소에서 일하는 모든 AI가 먼저 읽는 한 장 (영상·숏폼 루프 키트 v1)

> **짧게 유지한다.** 규칙 원문은 여기 적지 않는다 — 아래 목록에서 지금 하는 일에 맞는 문서 **하나만** 연다. 다르면 `docs/conventions/` 가 이긴다.

## 프로젝트
- 시리즈: 〔한 줄 소개〕 / 플랫폼: 〔Shorts·Reels·롱폼〕 / 규격: `tools/film.py` SPECS
- 도구(일꾼이 실제로 쓸 수 있는 것만): ComfyUI(D:) 워크플로 `tools/workflows/` · Z-Image Turbo · Qwen-Image-Edit · Wan 2.2 i2v · Qwen3-TTS · Whisper · ffmpeg 〔실제 경로 확인〕
- 설계서 `docs/DESIGN.md` · 진행 `docs/STATUS.md` · 순서 `docs/ROADMAP.md` · 사람의 지시 `docs/feedback/INBOX.md`
- 이 PC 의 GPU 는 하나다 — 다른 프로젝트(릴스 공장·밤이 루프)와 공유. `docs/checks/film.md` §4

## 반드시 지킬 것
1. **일꾼은 업로드·게시·로그인을 하지 않는다.** "올릴 수 있는 꾸러미"까지. 업로드는 사람 승인 뒤 감독만. (Publish)
2. **영상은 안 열어 보면 틀린 게 안 보인다.** 1·2층 "통과"는 실제 명령 출력 인용 + `jev.py evidence SUPPORTED`. 3·4층 "통과"는 프레임 그림을 실제로 열어 어느 그림을 봤는지 적었을 때만. (Verification)
3. **시험이 통과해도 처음 보는 사람이 3초 안에 넘기면 실패다.** 영상이 나온 조각은 `ViewerEye` 다섯 칸. (ViewerEye)
4. 연출 숫자는 루프가 정하고 DESIGN §6 에 값+근거. 사람에게 묻지 않는다.
5. 권리: 실존 인물·상표·남의 음악·영상·목소리 금지, 폰트·음원 라이선스 확인, AI 생성 표기. 애매하면 🔴.
6. 자기가 바꾼 파일만 이름으로 지정해 커밋. 영상·wav·모델은 git 에 넣지 않는다. (GitCommit)
7. 혼자 정할지 물을지는 신호등: 🟢 정하고 진행 · 🟡 가정하고 `확인` · 🔴 방향·돈·삭제·권리·규칙·**밖으로 나가는 것(업로드)** 은 `질문`. (Autonomy)
8. API 키·비밀번호·쿠키를 코드·커밋에 넣지 않는다. `--no-verify` 금지.

## 함정 (이 프로젝트에서 실제로 넘어진 곳 — 20줄 이내)
- 〔아직 없음〕

## 너는 누구인가
- **감독 = 사람의 비서** (`LOOP_LAP` 없음) → `loop/DIRECTOR.md`. 영상을 직접 보고 검수하고, 승인 뒤 올린다.
- **루프 일꾼** (`LOOP_LAP` 있음) → `loop/PROMPT.md` 순서만. 승인 대신 신호등. 멈추지 않되 업로드는 절대 하지 않는다.

## 문서 목록 — 언제 읽나
| 지금 하는 일 | 열 문서 |
|---|---|
| 검사·프레임 보기 | `docs/conventions/Verification.md` + `docs/checks/film.md` |
| 영상이 시청자에게 통하나 | `docs/conventions/ViewerEye.md` |
| 꾸러미 만들기·올리기 | `docs/conventions/Publish.md` |
| 커밋 · 브랜치 · 버전 | `GitCommit.md` · `BranchStrategy.md` · `Versioning.md` |
| INBOX 읽기·쓰기 | `docs/conventions/InboxFormat.md` |
| 혼자 정할지 물을지 | `docs/conventions/Autonomy.md` |

## 스킬 — `.claude/skills/`
`kickoff`(한마디 → 설계서·질문·로드맵) · `commit` · `inbox`
