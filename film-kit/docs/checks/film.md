# 검사 모듈: 로컬 AI 영상 (ComfyUI + ffmpeg)  〔DRAFT — 아래 명령을 실제로 한 번씩 돌려 확인하고 사람 승인 후 DRAFT 삭제〕

> 공통 원칙은 `docs/conventions/Verification.md`. 여기엔 **이 PC(Windows RTX 4090)에서 실제로 어떻게** 만 적는다.
> 〔…〕 는 첫 바퀴가 실제 경로·값으로 채운다. 못 채우면 그 층은 "못 함".

## 0. 파이프라인 단계 (한 바퀴 = 한 단계의 한 조각)
| 단계 | 산출물 | 도구 | 폴더 |
|---|---|---|---|
| S1 대본·샷리스트 | `data/episodes/epNN.json` | 글 | git |
| S2 스틸(첫 프레임) | 컷별 png | ComfyUI: Z-Image Turbo / Qwen-Image-Edit 2509 (인물 일관성) | `work/epNN/still/` |
| S3 컷 영상 | 컷별 4초 mp4 | ComfyUI: Wan 2.2 i2v | `work/epNN/clip/` |
| S4 음성·자막 | wav, srt | Qwen3-TTS, Whisper(자막 시각 뽑기), (립싱크 필요 시 Wan2.1+InfiniteTalk) | `work/epNN/voice/` |
| S5 조립 | `work/epNN/cut.mp4` | ffmpeg (이어 붙이기·자막 입히기·음악 믹스, 음원은 ACE-Step 또는 무료 라이선스) | `work/epNN/` |
| S6 검수 | 컨택트시트·보고 | `film.py clip` · `film.py sheet` · 눈 | `captures/` |
| S7 꾸러미 | `publish/epNN/` | 복사 + meta.json | git (최종본만) |
| S8 업로드 | — | **일꾼 금지.** `Publish.md` | — |

## 1층 — 기계 검사
| 검사 | 명령 | 통과 줄 예 |
|---|---|---|
| 대본·샷리스트·꾸러미 | `python3 tools/film.py check` | `✔ 영상 데이터 검사 통과 (에피소드 3개 / 오류 0)` |
| 완성 영상 | `python3 tools/film.py clip work/ep01/cut.mp4 --spec shorts` | `✔ 영상 검사 통과 (cut.mp4 1080x1920 30fps 42.0초 / 오류 0)` |
| 검사기 자가 시험 (키트 고친 날) | `python3 tools/film.py selftest` | `✔ 자가 시험 통과` |
| ComfyUI 살아 있음 | `curl -fsS http://127.0.0.1:8188/system_stats` 〔포트 확인〕 | 종료코드 0 |

## 2층 — 흐름 검사
- **컷 수·순서**: `ls work/epNN/clip/*.mp4 | wc -l` 이 샷리스트 샷 수와 같다. 파일 이름이 샷 ID 와 같다.
- **길이 대조**: 컷 mp4 길이 합 ± 0.5초 = 샷리스트 `sec` 합. ffprobe 로 재서 숫자를 인용.
- **자막 싱크**: srt 마지막 자막 종료 시각 ≤ 영상 길이, 자막이 겹치지 않음 (짧은 파이썬으로 파싱해 종료코드).
- **음성 길이**: wav 길이가 그 샷 `sec` 보다 길면 실패 (잘림).
- **이음새**: 컷 경계 앞뒤 프레임을 `ffmpeg -ss` 로 뽑아 3층에서 본다.

## 3·4층 — 눈
1. `python3 tools/film.py sheet work/ep01/cut.mp4` → `captures/tmp/cut_sheet.jpg`
2. **Read 로 그 그림을 연다.** 체크리스트는 `Verification.md`, 다섯 칸은 `ViewerEye.md`.
3. 인물 일관성: `data/characters.json` 의 기준 프레임(`ref_still`) 과 나란히 연다.
4. 합격 프레임만 `captures/epNN_<설명>.jpg` 로 복사해 커밋.

## 4. GPU 잠금 (이 PC 의 GPU 는 하나, 릴스 공장·밤이 루프와 공유)
- 렌더(S2·S3·S4 일부) 전에: `test ! -e loop/gpu.lock || exit 0` → 있으면 **그 조각을 하지 않고** 다른 단계(S1·S5·S6)를 한다.
- 렌더 시작 때 `echo "$$ $(date +%s) <조각ID>" > loop/gpu.lock`, 끝나면 `rm loop/gpu.lock`. 30분 넘은 잠금 파일은 죽은 것으로 보고 INBOX `확인` 후 지운다.
- 다른 프로젝트의 잠금(릴스 공장)도 같은 규칙으로 쓰려면 경로를 〔공용 경로〕 로 맞춘다 — 🔴 (다른 프로젝트 건드림) 이니 감독이 사람에게 묻는다.
- 시간대: 밤이 루프 01:00·업로드 19:00 에는 렌더 금지 〔시간 확인〕.

## 알려진 함정
- Wan i2v 는 4초가 한계 — 긴 장면은 컷을 나눠 이어 붙인다 (이음새 3층 필수).
- 인물이 컷마다 달라진다 → S2 에서 항상 같은 기준 이미지(`ref_still`)를 Qwen-Image-Edit 입력으로 쓴다.
- 한글 자막은 ffmpeg `subtitles` 필터에 폰트 경로를 직접 준다 (□ 방지). 폰트는 상업 이용 가능한 것만.
- 렌더 도중 PC 슬립 → 바퀴 헛돈다. 〔전원 설정〕을 LOOP_PREFLIGHT 가 못 잡으면 감독이 사람에게.
- ComfyUI 워크플로 JSON 은 `tools/workflows/` 에 이름 붙여 저장하고, 모델 파일 이름이 바뀌면 깨진다 — 바퀴 시작 전 `system_stats` 로 확인.
