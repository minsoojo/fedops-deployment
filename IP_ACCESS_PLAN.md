# 기기별 설정 없는 F 접속 계획 및 실행 기록

2026-09-17 · 사용자 승인: 계획 수립 후 구현·검증·게시, 최종 결과 정리.

## 목표와 범위

F 진입 IP에 접근할 수 있는 기기에서 hosts/DNS 수정·Lens/SSH 포워딩 없이 `http://192.9.201.220/fedops/`로 Web을 사용한다. Studio 등록 주소도 `http://192.9.201.220/fedops`다. 실제 인터넷 외부 경로 확보나 새 IP 예약은 이번 범위가 아니다. F 적용은 기존 사용자 직접 실행 방식으로 안내하며 원격 변경을 자동 실행하지 않는다.

R02/R03/R06/R07/R09/R12 → W03/W05/W07. 원본·기존 운영·DB 데이터는 수정하지 않는다.

## 구현 계획

1. Chart에 `access.singleOrigin` 옵션 추가(기존 도메인 모드는 기본 유지). F용 overlay는 webHost=192.9.201.220, singleOrigin=true.
2. IP 모드에서는 하나의 Gateway HTTP host와 하나의 HTTP VirtualService 사용. Web/API/Socket 경로 유지, `/fedops/services/{manager,performance,registry}/`는 해당 내부 Service로 접두사 제거 후 전달.
3. 앱에 제공하는 공개 Manager URL은 IP 경로로 변경. MinIO 서명 endpoint는 같은 IP의 루트 사용. 설정된 5개 bucket의 정확한 경로/하위 경로는 rewrite 없이 MinIO로 전달해 서명을 유지한다. MinIO Console 및 루트 ListBuckets API 노출은 이 Web 진입점의 목표가 아니다.
4. Frontend의 API/Socket same-origin 및 다운로드 프록시 유지. Web과 저장소 origin이 같을 때 일반 API URL을 파일 URL로 오인하지 않도록 서명 URL만 변환한다.
5. Chart 기본/단일 주소 모드 회귀 검사, 고정 Istio 검증 규칙 확인, 실제 Envoy·앱·DB·S3로 IP Host와 경로 라우팅 통합 검증. 가능한 검증 범위와 미검증 F 실제 적용을 구분.
6. 변경 Frontend 이미지·Web 소스·배포 Chart를 기존 개인 저장소에 게시하고 digest 고정. Git pull/Helm upgrade 명령과 F 점검 기준 제공.

## 경로 계약

| IP 기준 경로 | 대상 | 처리 |
|---|---|---|
| /fedops/api, /socket.io | Web Backend | 경로 유지 |
| /fedops/services/manager/ | Manager | 서비스 접두사만 제거 |
| /fedops/services/performance/ | Performance | 서비스 접두사만 제거 |
| /fedops/services/registry/ | Registry | 서비스 접두사만 제거 |
| /각 설정된 bucket 및 /각 bucket/… | MinIO | Host·경로·서명 query 유지 |
| 나머지(Web UI, /fedops/objects) | Frontend | 기존 UI/다운로드 프록시 |

FL TCP 40026~40039, Task 전용 LB 추가 주소 필요 조건은 유지한다. Studio의 Web 연결·등록·파일 전달과 실제 FL 학습 완료는 다른 검증이다.

## 완료 기준과 진행

- [x] 차트·Frontend 수정 및 기존 도메인 모드 회귀 검사
- [x] 로컬 IP 진입 HTTP·로그인 쿠키·Socket·파일 서명·서비스 경로 검증
- [x] 소스·이미지·차트 게시 및 재다운로드 대조
- [x] F 수동 적용 가이드·최종 증빙 정리
- [ ] F 사용자 적용 후 설정 없는 기기의 실제 접속 확인 (사용자 실행 단계)

## 실행 결과

- Chart 0.1.1: 기본 도메인 모드 42개, IP 모드 38개 자원. `python -B charts/fedops/tests/verify_chart.py` 622개 검사 통과. [정적 증빙](verification/chart-verification.json).
- F 테스트 값+게시 이미지+IP overlay: lint/template 통과, 공개 ConfigMap에 `*.fedops.test` 없음. Istio 1.30.4 `validate` 성공. [명령·결과](verification/ip-access-f-values.json).
- `python -B work/verify_frontend_forwarding.py --single-origin`: 실제 Envoy 1.30.4/Frontend/Backend/MongoDB/MinIO로 IP Host 기반 UI 응답·가입 API·로그인/로그아웃·쿠키 인증·Socket.IO polling/WebSocket·서명 파일 다운로드/변조 거부 성공. 임시 컨테이너/네트워크 정리.
- Manager/Performance/Registry는 echo target으로 경로 및 query 전달을 검사했다. 실제 업무 API 전체·이메일 인증코드·Studio 전체 E2E·FL 학습·브라우저 GUI·F 배포는 이 로컬 검사에 포함되지 않는다. [상세 증빙](verification/ip-access-integration.json).
- Frontend 설정 단위 검사 4개 통과. Web commit `1613311e8bb2b094769aaa29494bc2525403e983` GitHub 게시.
- Docker Hub 비공개 `minsoojo/fedops-onprem:frontend-ip-access-20260917`, digest `sha256:2878636eb4263ccd910e67dcf55161cc73eaf002e070b0dcd922d07bae642789`. digest pull 후 로컬 검증 이미지 ID와 일치. 이미지 overlay 갱신.
- 배포 저장소에 Chart·이미지 설정·F 적용 가이드·검증 JSON 게시. [F 실행 명령](F_IP_ACCESS.md).

F 실제 변경은 수행하지 않았다. 기존 사용자 직접 설치 원칙에 따라 위 가이드의 upgrade와 새 기기 확인만 남아 있다.

