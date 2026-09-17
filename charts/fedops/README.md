# FedOps 온프레미스 Chart 구성·설정 안내

2026-09-16 · Chart 0.1.1 · 기존 FedOps를 F 단일 노드에 새 데이터로 설치하기 위한 최소 구성.

**현재 완료: Chart 정적 검증, 앱 6종 빌드·기동·Docker Hub 게시/digest 대조, Web SDK의 로컬 MinIO 왕복.** [이미지 기록](../../README.md). Task Runtime 연결·F 설치/FL 검증은 남아 있다. `values.yaml`의 앱 이미지·F 입력은 의도적으로 비어 있다. 실제 F 값 파일 뒤에 [게시 이미지 설정](examples/images-minsoojo.yaml)을 덧씌워 사용하며 `fedops-registry-pull` Secret은 해당 namespace에 준비해야 한다. `tests/static-values.yaml`은 존재하지 않는 주소를 사용하는 정적 검사 전용 파일이다.

[전체 계획](../../README.md) · [실행·이미지 명세](../../README.md) · [검증 기록](../../README.md)

## 1. 포함 자원과 담당 범위

| Chart가 만드는 자원 | 내용 |
|---|---|
| Deployment 9개 | Frontend, Backend, Manager, Performance, Java Gateway(+Redis 컨테이너), MongoDB 2개, Registry, MinIO |
| Service 9개 | 기존 이름·포트를 유지한 ClusterIP. 운영 clusterIP/nodePort/LB IP는 복사하지 않음 |
| ConfigMap 7개 | 앱 6종의 일반 env, 브라우저 공개 runtime-config.js |
| local PV/PVC 각 3개 | Web Mongo·Registry Mongo·MinIO. 기존 PVC 연결 시 해당 PV/PVC 생성 생략 |
| ServiceAccount/Role/RoleBinding | Manager의 namespace API 호출 |
| ClusterRole/ClusterRoleBinding | Manager의 전역 PV API 호출만 허용 |
| Istio Gateway 1개 | HTTP 또는 HTTPS, 기본 FL TCP 40026~40039 listener |
| HTTP VirtualService | 기본 도메인 모드 5개, 단일 주소 모드 1개 |

기본 모드 42개, `access.singleOrigin=true` 모드 38개 자원. Task·legacy Job·Task PVC·Task VirtualService는 Manager 소유다. 기존 운영 Task 7개, 테스트 Web, 오래된 sharded Mongo 리소스는 기본 Chart에 복제하지 않는다.

별도 준비: Kubernetes/containerd/Calico, Istio base/istiod/**ingress Deployment와 LoadBalancer Service**, MetalLB와 예약 IP 풀, 도메인 모드의 DNS/hosts, Namespace, 신규 Secrets, F 디렉터리, 버킷/앱 자격. Chart가 이 기반 환경을 자동 설치하지 않는다.

기본 9개 앱 Service는 ClusterIP이며 외부 접근을 Istio로 모은다. 기존 Task Service의 LoadBalancer 동작은 그대로다. 따라서 최소 LB 입력은 Istio ingress 1개 + 동시 Task 수이다.

## 2. 실제 입력

[examples/f-values.yaml](examples/f-values.yaml)을 별도 배포 설정 파일로 복사해 채운다. 파일 안에는 비밀값을 넣지 않는다.

| values | 의미 / 연결 |
|---|---|
| `nodeName` | F의 `kubernetes.io/hostname` label 값. 기본 Pod·local PV nodeAffinity·Manager Task 노드 설정에 공통 전달 |
| `images.*` | 앱/제품/Task 이미지 전체 주소. 명시적 tag 또는 sha256 digest 필수; `latest` 거부 |
| `imagePullSecrets` | 기본 앱 Pod의 이미지 pull Secret 이름 목록. Task에 자동 전파되지 않음 |
| `access.singleOrigin` | 기본 false. true이면 webHost 하나에서 경로로 서비스 구분; 보조 HTTP host 4개는 무시되고 빈 값 가능 |
| `access.scheme` | `http`(80) 또는 `https`(443). HTTPS는 별도 인증서 Secret 필요 |
| `access.webHost` | 브라우저 Web/API/Socket/SSE 접속 host. UI prefix `/fedops` 유지 |
| `access.managerHost`, `performanceHost` | 클러스터 밖 FL Client가 사용하는 각 서비스 host |
| `access.registryHost` | 기존 Registry API의 외부 접속 host |
| `access.objectsHost` | Web/Registry가 생성하는 MinIO 서명 URL의 host. bucket/key 앞에 새 prefix를 붙이지 않음 |
| `access.flHost` | FL TCP 접속 hostname 또는 IPv4, 포트 제외 |
| `access.additionalCorsOrigins` | Studio 등 추가 브라우저 origin 목록. scheme 포함, 경로 제외 |
| `istio.ingressSelector` | 실제 Istio ingress Pod label과 일치시킬 선택자 |
| `istio.tlsSecretName` | HTTPS 인증서 Secret 이름. 실제 ingress workload namespace에 별도 준비 |
| `istio.taskVirtualServiceName` | Manager가 만드는 동적 Task route 이름. 기본 `fedops-virtualservice` |
| `task.*` | Task 데이터 기본 경로·선언 용량·FL TCP 범위. Gateway listener와 Manager env에 함께 반영 |
| `persistence.*` | 역할별 경로·용량 또는 기존 PVC 이름. 새 디렉터리 작성·권한 설정은 설치 전 사용자 수행 |
| `storage.*` | 모델/XAI/Registry 버킷 이름과 region. 신규 MinIO에도 같은 region 전달 |
| `secrets.*` | 아래 키를 가진 신규 Secret 이름 |
| `smtp.*` | SMTP host/port·auth/STARTTLS 설정. 실제 SMTP 전달 가능 여부는 별도 검증 |
| `frontend.runtimeConfigPath` | 앱 이미지가 제공하는 공개 설정 파일 경로. 현재 React 서버 계약은 `/app/client/public/runtime-config.js` |
| `workloads.*` | 해당 이미지의 workingDir/command·resources·Pod/container securityContext. 기본값은 실행 명세의 경로 계약 |
| `redis.*` | 같은 Gateway Pod의 Redis resources/securityContext |

기본 도메인 모드에서는 5개 HTTP host가 서로 달라야 한다. DNS가 없으면 접속하는 브라우저·Client의 hosts 설정으로 같은 F ingress IP를 가리킬 수 있다. `flHost`는 그 ingress의 도달 가능한 host/IP를 사용한다. F 테스트에는 임시 IP 192.9.201.220을 사용한다.

내부 URL은 기존 Service 이름과 release namespace를 사용해 자동 생성한다. 사용자가 동일한 내부 주소를 여러 번 입력하지 않는다. 예: `FL_SERVER_MANAGER_URL=http://server-manager-service.<namespace>.svc.cluster.local:8000`.

## 3. Secret 계약

모두 release namespace에 별도로 만든다. Chart는 Secret 본문을 생성·조회하지 않고 키만 참조한다.

| values 참조 | 필수 키 | 사용하는 앱 |
|---|---|---|
| `secrets.web` | `MONGO_URI`, `JWT_SECRET` | Backend. artifact 서명 키는 기존 JWT_SECRET fallback 사용 |
| `secrets.performance` | `MONGODB_URI` | Performance; Web과 같은 `fedops` DB |
| `secrets.registry` | `MONGODB_URI`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Registry 전용 DB·객체 저장소 앱 자격 |
| `secrets.mongo` | `MONGO_INITDB_ROOT_USERNAME`, `MONGO_INITDB_ROOT_PASSWORD` | Web Mongo 신규 데이터 초기화 |
| `secrets.registryMongo` | 위 두 Mongo root 키 | Registry Mongo 신규 데이터 초기화 |
| `secrets.minio` | `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` | MinIO 관리 자격 |
| `secrets.taskStorage` | `ACCESS_KEY_ID`, `ACCESS_SECRET_KEY`, `BUCKET_NAME` | Backend SDK와 Manager가 생성한 Task. Backend의 버킷 이름은 values에서 주입 |
| `secrets.smtp` | `SPRING_MAIL_USERNAME`, `SPRING_MAIL_PASSWORD` | Java 인증 서비스 |

`taskStorage.BUCKET_NAME`은 `storage.modelBucket`과 같아야 한다. Helm은 Secret 본문을 읽지 않으므로 일치 여부는 설치 준비 단계에서 확인한다. Backend 공유 객체 계정에는 모델·XAI 버킷에 필요한 권한을 준비하고, Registry 계정에는 해당 Registry 버킷 권한을 준비한다. 버킷 생성·정책/사용자 발급을 수행하는 hook은 없다.

DB URI의 host/port: Web와 Performance는 `fedops-mongo-np:5000/fedops`, Registry는 `fedops1-registry-mongo-svc:27017/fedops-registry`. 계정에 맞는 `authSource`를 포함한다. 앱 DB 사용자는 별도 준비하며 Chart가 root 자격을 앱에 복사하거나 DB 사용자를 자동 생성하지 않는다. 기존 PVC를 재사용하면 초기화 env로 기존 DB 비밀번호가 변경되지 않는다.

Secret 내용 변경은 checksum에 포함되지 않는다. 반영 시 필요한 앱을 사용자 절차로 재시작한다. ConfigMap 변경은 Pod template checksum으로 재시작을 유발한다.

## 4. 연결과 라우팅

- Lens에서 Frontend Pod의 3000 또는 Service의 80을 로컬 포트로 연결하면 `http://localhost:<port>/fedops/`로 접속한다. API/Socket은 현재 브라우저 origin을 사용하며 Frontend의 기존 Backend 프록시를 통과한다. hosts 설정은 필요 없다. 개발 서버의 WDS socket port도 0(현재 페이지 포트)으로 지정한다.
- 모델·파일의 서명 다운로드는 `/fedops/objects`를 통해 내부 MinIO로 전달한다. 브라우저에는 서명 대상 origin 식별값만 제공하며, 프록시는 원래 서명 Host/경로/쿼리를 유지한다. 새 Frontend 이미지와 함께 적용해야 한다. 외부 FL 클라이언트 TCP/Manager 접근은 별도다.

- Web host의 `/fedops/api`, `/fedops/api/*`, `/socket.io`, `/socket.io/*`는 Backend로 전달한다. 나머지는 Frontend로 전달한다. HTTP route의 `timeout`은 생략해 요청 시간 제한이 비활성인 [Istio 기본 동작](https://istio.io/latest/docs/tasks/traffic-management/request-timeouts/)을 사용하며 URI를 바꾸지 않는다. Istio 1.30.4 CRD는 명시적인 `timeout: 0s`를 거부하므로 넣지 않는다.
- Manager·Performance·Registry는 각 host에서 기존 경로 그대로 전달한다.
- MinIO는 전용 host에서 bucket/key와 Host를 보존한다. SDK는 내부 Service로 저장/조회하고 외부 endpoint로 처음부터 서명한다. 서명 후 host 치환을 하지 않는다. console 9001은 외부 route에 넣지 않는다.
- HTTP Gateway와 FL TCP listener는 Chart가 만들지만, **실제 Istio ingress Kubernetes Service의 포트도 기반 구성 단계에서 동일하게 열어야 한다.** 현재 기본 HTTP 80(HTTPS 선택 시 443) 및 TCP 40026~40039. values만 바꿔서는 기반 Service·방화벽이 변경되지 않는다.
- Chart Gateway는 앱 namespace에 있다. ingress가 `istio-system`에 있다면 Istio의 namespace 간 Gateway 선택이 허용돼야 한다. `PILOT_SCOPE_GATEWAY_TO_NAMESPACE=true` 환경은 이 배치와 맞지 않으므로 F 기반 설정을 확인한다. [공식 Gateway 설명](https://istio.io/latest/docs/reference/config/networking/gateway/)
- 앱 namespace의 자동 sidecar injection은 사용하지 않는 것을 기반 조건으로 한다. 기본 앱은 annotation으로 injection을 끄지만 Manager가 만드는 Task에는 Chart가 annotation을 덧붙이지 않는다.

### 동적 route의 소유권

Manager의 기존 코드는 VirtualService가 없으면 첫 Task 생성 시 유효한 TCP route와 함께 만든다. 따라서 Chart가 빈 Task VirtualService를 미리 만들거나 `lookup`으로 복사할 필요가 없다. Chart는 별도 이름의 HTTP VirtualService만 소유한다. Helm upgrade/rollback은 Task route를 템플릿으로 덮어쓰지 않는다.

이 방식은 기존 설계의 “빈 Task route를 Chart가 만들고 lookup으로 보존”을 대체한다. `istio.taskVirtualServiceName`과 Chart HTTP route 이름의 충돌은 렌더링에서 거부한다. 활성 Task가 있는 동안 release/namespace/Gateway 참조·FL 포트 범위를 바꾸지 않는다. 실제 업그레이드 중 Task 통신 유지 검증은 W06에 남아 있다.

## 5. 저장소와 실행

- Mongo 2개·MinIO는 정적 local PV/PVC, `Retain`, `helm.sh/resource-policy: keep`, 명시적 PV↔PVC 바인딩을 사용한다. NAS·자동 provisioner는 없다.
- DB/MinIO/Task 경로는 같거나 서로 포함 관계가 될 수 없다. 데이터는 새 전용 경로에 둔다. 용량 선언이 디스크 quota나 공간 예약을 보장하지 않는다.
- 기존 PVC를 연결하려면 해당 `persistence.<role>.existingClaim`을 입력한다. 해당 PV/PVC는 Chart가 생성·변경하지 않는다. PVC namespace/Bound 상태·F 노드 affinity·경로·권한은 설치자가 확인한다. 보존 후 재설치 절차의 실제 성공은 아직 미검증이다.
- 모든 기본 Deployment는 단일 replica와 `Recreate`로 중복 writer/Manager 실행을 피한다. 업데이트 중 중단 시간이 있다. Redis는 이메일 인증 코드용 휘발성 저장소로 같은 Gateway Pod에 있고, Pod 재생성 시 인증 코드가 사라질 수 있다.
- startup/readiness는 열린 TCP 포트를 확인한다. DB 연결·SMTP·학습 성공을 판정하는 E2E 검사가 아니다. Gateway Redis readiness는 `redis-cli ping`이다.
- Manager만 Kubernetes API 토큰을 마운트한다. namespace의 Pod/Service/PVC/Deployment/Job/VirtualService, Pod log·exec와 전역 PV 권한을 제공한다. Secret 조회·wildcard 권한·운영 kubeconfig 마운트는 없다.
- 실행 이미지의 UID/GID 확인 뒤 필요한 `podSecurityContext`/`securityContext`와 디렉터리 권한을 정한다. 임의 chmod·privileged·호스트 전체 마운트는 없다.

## 6. 로컬 검증과 다음 단계

현재 로컬 재현 명령(워크스페이스 루트):

```powershell
work/helm-tools/windows-amd64/helm.exe lint charts/fedops -f charts/fedops/tests/static-values.yaml --strict --kube-version 1.36.0
work/helm-tools/windows-amd64/helm.exe template fedops charts/fedops -n fedops -f charts/fedops/tests/static-values.yaml --kube-version 1.36.0
python -B charts/fedops/tests/verify_chart.py
```

검증 도구·공식 스키마 확보 방법과 결과는 [검증 기록](../../README.md)에 있다. Helm template 결과는 실제 클러스터 admission·설치·통신 검증을 대신하지 않는다.

다음은 Task Runtime 패키지 연결이다. 이후 F 전용 context·신규 Secret·디렉터리·버킷·기반 네트워크를 확인한 설치 가이드를 작성한다. 앱 이미지 게시·원격 digest 대조는 완료했고 F 설치 명령은 실행하지 않았다.

## 기기별 설정 없는 IP 접속

F 값과 이미지 overlay 뒤에 [f-ip-access.yaml](examples/f-ip-access.yaml)을 추가한다.
`http://192.9.201.220/fedops/`로 접속하며 Studio에는 `http://192.9.201.220/fedops`를 등록한다.
접속 기기는 해당 IP로 네트워크 통신이 가능해야 한다. hosts 수정이나 Lens 포워딩은 필요 없다.

- Web/API/Socket은 같은 origin이다.
- `/fedops/services/{manager,performance,registry}`는 내부 서비스 전달 시 접두사를 제거한다.
- 설정된 5개 bucket의 `/bucket` 및 `/bucket/...`는 Host/경로/query 변경 없이 MinIO로 전달한다.
- Web `/fedops/registry` 화면과 `/fedops/objects` 다운로드 프록시는 유지한다.
- MinIO Console/루트 ListBuckets, Mailpit UI, 외부 인터넷 연결은 이 진입점에 포함하지 않는다.
- 단일 주소 모드에서는 기존 보조 도메인 VirtualService를 만들지 않는다. `webHost`가 HTTP 진입 주소다.
- ConfigMap checksum이 모든 기본 Deployment에 연결되어 있어 적용 시 앱/DB Pod들이 교체된다.
  기존 PV/PVC와 Secret은 그대로 사용한다. 실제 배포 후 Ready와 로그인/파일 다운로드를 확인한다.
