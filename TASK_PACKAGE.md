# Task Baseline의 새 FedOps 저장소 연결

2026-09-16 · R05/R09/R12 → W03/T03.8. 사용자 승인한 의존성 변경 단계 완료.

## 변경

- `fedops-silo-baseline-onprem`의 Baseline을 0.19.1로 올렸다. 기존 0.19.0 Release는 유지한다.
- `pyproject.toml`의 FedOps Git 출처를 `minsoojo/fedops-core-onprem`, revision을 `ff5f44ddea2705c8d901a54a0272f517822da8f4`, 하위 경로를 `src/python`으로 고정했다.
- `requirements.txt`의 버전을 실제 core 버전 `1.1.30.19+onprem.20260916`에 맞췄다.
- Task 부트스트랩이 쓰는 uv 0.8.13으로 `uv.lock`을 재생성했다. 나머지 패키지 버전은 유지했고 플랫폼 조건·배포 파일 정보는 도구가 재계산했다.
- Baseline 버전 상수·Release manifest 생성기·기존 테스트의 버전 기대값도 맞췄다.

소스: [GitHub 변경 커밋](https://github.com/minsoojo/fedops-silo-baseline-onprem/commit/eb54b25473e387c50b343c9382bdad74e297c3a6).

## 검증

Windows 11 / Python 3.12.10 / uv 0.8.13, 프로젝트별 `.venv`에서 수행했다.

| 검사 | 결과 |
|---|---|
| uv lock / sync --locked | 잠금 142개, 현재 플랫폼 설치 126개 |
| Task와 같은 sync --frozen --link-mode copy | 성공 |
| uv pip check | 설치된 의존성 호환 |
| 설치된 FedOps direct_url.json | 새 저장소 URL·고정 commit·하위 경로 일치 |
| CPU Torch/TorchVision | 2.8.0+cpu / 0.23.0+cpu, NMS 연산 성공 |
| 기존 unittest | 14개 통과 |

[정확한 명령·결과](verification/task-dependency.json). 설치 시 이 PC의 기존 Git 인증을 사용했다. 토큰은 소스·lock·문서에 넣지 않았다.

## Core 접근 방식 갱신

2026-09-16 후속: 사용자의 명시 요청으로 `minsoojo/fedops-core-onprem`만 Public으로 전환했다. 고정 commit과 이미지 digest는 유지하며, 인증을 끈 Git 조회가 성공했다. Task/참여 클라이언트의 core 설치에는 GitHub 토큰·SSH 키가 필요 없다. 다른 저장소와 Docker Hub는 비공개를 유지한다.

## 당시 다음 작업과 완료 경계

후속으로 [Web·Manager 연결과 이미지 게시](TASK_RUNTIME.md)를 완료했다. 아래는 의존성 변경 단계 당시의 경계다.

Web/Manager가 새 Baseline·FedOps 버전을 허용하고 새 Baseline을 배포하도록 연결하는 작업이 남아 있다. F의 비공개 Git 접근 방법과 실제 Linux Task/FL 실행도 별도다. 이번 결과는 로컬 패키지 설치·Baseline 검사 성공이며 F 배포나 Task 전체 통합 성공은 아니다. 기존 앱 이미지 6종은 이번 변경으로 재빌드하지 않았다.
