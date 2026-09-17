# F: 기기별 설정 없는 IP 접속

2026-09-17 · R02/R03/R06/R07/R09/R12 · W03/W05/W07

## 목표와 현재 상태

F ingress IP에 도달 가능한 기기에서 **http://192.9.201.220/fedops/** 를 연다.
hosts 수정, DNS 서버 변경, Lens/SSH 포트포워딩은 필요 없다.
인터넷 어느 곳에서나 접속하도록 네트워크를 개방하는 변경은 아니다.

로컬 구현·검증·게시 결과는 [계획과 실행 기록](IP_ACCESS_PLAN.md)에 있다.
F 적용은 사용자 직접 실행 단계이며, 실제 F에서 새 기기로 접속한 결과는 아직 확인하지 않았다.

## F에서 실행

이미 설치된 release `fedops`, context `fedops-f`, namespace `fedops`에 적용한다.
기존 데이터/PVC와 Secrets를 사용하므로 저장소 초기화나 Secret 재생성은 하지 않는다.

```bash
git -C ~/fedops-deployment pull --ff-only

helm upgrade --install fedops ~/fedops-deployment/charts/fedops \
  --namespace fedops --kube-context fedops-f \
  -f ~/fedops-f-values.yaml \
  -f ~/fedops-deployment/charts/fedops/examples/images-minsoojo.yaml \
  -f ~/fedops-deployment/charts/fedops/examples/f-ip-access.yaml \
  --wait --timeout 5m

kubectl --context=fedops-f -n fedops get pods
```

오래된 `~/fedops-images.yaml` 대신 저장소의 최신 이미지 설정을 쓴다.
마지막 overlay가 `access.singleOrigin=true`, `access.webHost=192.9.201.220`을 설정한다.
ConfigMap checksum 변경으로 기본 앱/DB Deployment들이 재시작하므로 잠시 접속이 중단될 수 있다.
Helm 오류가 나오면 이어서 진행하지 말고 해당 오류를 확인한다.

## 새 기기에서 확인

1. 브라우저로 **http://192.9.201.220/fedops/** 접속.
2. 기존 테스트 계정으로 로그인하고 새로고침 후에도 로그인 유지 확인.
3. Task 목록/상세 화면, 사용할 수 있는 모델/파일 다운로드 확인.
4. 개발자 도구 Network에서 브라우저가 `*.fedops.test`로 요청하지 않는지 확인.
5. Studio에는 **http://192.9.201.220/fedops** 등록. `/fedops` 경로를 포함한다.

명령으로 첫 응답만 확인하려면, 접속할 기기에서:

```bash
wget --no-proxy -S -O /dev/null -T 10 -t 1 http://192.9.201.220/fedops/
```

예상 결과는 HTTP 200이다. HTTP 200만으로 로그인·파일 전송까지 완료된 것은 아니다.

## 바뀐 경로

| 공개 주소/경로 | 역할 |
|---|---|
| `/fedops/` | Web |
| `/fedops/api/`, `/socket.io/` | Backend API, 실시간 연결 |
| `/fedops/services/manager/` | Manager API |
| `/fedops/services/performance/` | 성능 API |
| `/fedops/services/registry/` | Registry API |
| `/global-model/`, `/global-model-xai/`, `/fedops-llms/`, `/fedops-tasks/`, `/fedops-models/` | 기본 bucket의 MinIO API/서명 파일 |

단일 주소 모드는 기존 5개 도메인 분기를 대체한다. DB와 내부 서비스 주소, FL TCP 포트는 유지한다.
이전에 발급된 `objects.fedops.test` 파일 URL은 새 설정으로 자동 변환되지 않으므로 화면/파일 링크를 다시 요청한다.
MinIO Console/루트 ListBuckets와 Mailpit UI는 여기에 포함하지 않는다. 테스트 메일 확인 방식은 기존과 같다.
메일 발송·인증코드 입력부터 시작하는 전체 가입 과정과 외부 FL 학습 완료는 이번 로컬 검사 범위 밖이다.

## 문제가 있으면

- 연결 실패: 기기에서 192.9.201.220의 80/TCP로 접근 가능한지 먼저 확인한다.
- HTTP 404: 마지막 IP overlay 적용 여부와 `kubectl --context=fedops-f -n fedops get virtualservice fedops-web -o yaml`의 hosts를 확인한다.
- 로그인 실패: `kubectl --context=fedops-f -n fedops get pods` 상태와 Backend DB 연결을 확인한다. 요청 비밀번호/토큰이 포함된 로그는 공유하지 않는다.
- 되돌려야 할 때: `helm history fedops -n fedops --kube-context fedops-f`에서 이전 정상 revision을 확인한 다음 그 revision으로 `helm rollback`한다. 데이터 초기화는 하지 않는다.
