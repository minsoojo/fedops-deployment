# Web·Manager의 온프레미스 Task 연결

2026-09-16 · R05/R09/R12 → W03/T03.9, W06 로컬 호환 준비.

## 완료한 변경

- Web의 새 Task 기본 Baseline은 `0.19.1`이다. Baseline 저장소 commit `eb54b25473e387c50b343c9382bdad74e297c3a6`의 Release를 Backend에 포함했다.
- Web·Manager는 FedOps `1.1.30.19+onprem.20260916`과 core commit `ff5f44ddea2705c8d901a54a0272f517822da8f4` 조합을 명시적으로 허용한다.
- 새 버전명의 `+onprem.20260916` 때문에 서버 평가 설정이 비활성화되지 않도록 검사에 반영했다.
- 기존 profile의 기본값·고정 commit과 Baseline 0.19.0 이하 파일은 유지한다. 기존 Task를 자동 업그레이드하지 않는다.

소스: [Web 커밋](https://github.com/minsoojo/fedops-web-onprem/commit/c371ac2c4d894fc902022287fa984a162e7052f5), [Manager 커밋](https://github.com/minsoojo/fedops-server-onprem/commit/c39aa34c460d46055035d055766d002504eb7818).

## 실제 검증

로컬 Docker Desktop `desktop-linux`, Linux/amd64에서 외부 네트워크를 차단한 테스트 컨테이너로 수행했다.

| 검사 | 결과 |
|---|---|
| Backend `node --test test/*.test.js` | 104개 통과 |
| Manager profile/bootstrap | 11개 통과 |
| 모의 Kubernetes Deployment 생성 | 6개 통과. 기존/신규 profile의 버전·commit 환경변수 전달 확인 |
| 새 Baseline 파일 | Git에 저장된 26개 파일의 manifest hash 일치, 기존 Release 파일 변경 없음 |
| Backend·Manager 이미지 | 새 Git 작업본으로 빌드, push, 원격 digest pull 후 로컬 이미지 ID 일치 |
| Helm 이미지 설정 | lint/template 통과, 42개 자원·6종 이미지·9개 pull Secret 참조 확인 |

최초 Backend 전체 검색은 필수 Manager 주소 누락 및 helper fixture 자동 실행 때문에 실패했다. 테스트 전용 `FL_SERVER_MANAGER_URL=http://manager.invalid:8000`과 `test/*.test.js` 범위를 적용한 최종 검사에서 104개가 통과했다. 기존 SDK/Python 지원 경고는 이번 버전 연결 변경 범위에서 유지했다.

[명령·종료 코드·이미지 ID·digest](verification/task-runtime/verification.json), [테스트 로그](verification/task-runtime/backend-final-tests.log), [Helm 검증](verification/published-chart-check.json). 초기 6종 게시 기록은 `verification/task-runtime/previous-published-images.json`으로 보존했다.

## 배포 입력과 남은 작업

새 태그는 `minsoojo/fedops-onprem:backend-task-onprem-20260916` 및 `manager-task-onprem-20260916`이다. 실제 배포 설정은 [이미지 overlay](charts/fedops/examples/images-minsoojo.yaml)의 digest를 사용한다. 나머지 4개 앱 이미지는 이전 digest를 유지한다.

F에는 아직 적용하지 않았다. 다음은 F의 이미지 pull 인증과 기반 네트워크 준비, 사용자 직접 설치 및 실제 Task 생성·FL 통신·모델 저장/복원 검증이다. 이번 검사는 실제 Kubernetes·FL 통합 성공을 뜻하지 않는다. Git 토큰이나 Secret을 이미지·values에 포함하지 않았다.

## Core 공개 전환

2026-09-16 후속: 사용자의 명시 요청으로 `minsoojo/fedops-core-onprem`만 Public으로 전환했다. 고정 commit과 이미지 digest는 유지하며, 인증을 끈 Git 조회가 성공했다. Task/참여 클라이언트의 core 설치에는 GitHub 토큰·SSH 키가 필요 없다. 다른 저장소와 Docker Hub는 비공개를 유지한다. [확인 기록](verification/core-public.json).
