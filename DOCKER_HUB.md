# 개인 Docker Hub 이미지 게시

계정: **minsoojo**. 현재 PC에서 만든 앱 이미지 6종을 전달한다. GitHub 저장소와 Docker Hub 저장소는 별개다.

**2026-09-16 완료:** 사용자 로그인·비공개 저장소 생성 후 앱 6종 tag/push, 원격 digest 조회, digest로 재다운로드·로컬 검증 이미지 ID 일치 확인을 마쳤다. 익명 manifest 요청은 401로 거부됨을 확인했다. [게시 증빙](verification/published-images.json) · [접근 확인](verification/registry-access-check.json).

[게시 이미지 Helm 설정](charts/fedops/examples/images-minsoojo.yaml)에 6종 digest와 `imagePullSecrets: [{name: fedops-registry-pull}]` 참조를 넣었다. 실제 F 값 파일을 먼저, 이 이미지 파일을 나중에 적용하는 순서다. 해당 Secret은 F namespace에 별도 생성해야 하며 이번에 F에서 생성하지 않았다. [정적 검사](verification/published-chart-check.json): lint/template 성공, 42개 자원·6종 이미지·9개 Deployment의 pull Secret 참조 확인.

## 완료한 사용자 준비 절차 — 재현 참고

### 1. 현재 PC에서 로그인

Docker Desktop을 실행한 상태로 PowerShell에서 실행한다.

```powershell
docker login
```

안내되는 브라우저 인증을 완료한다. 브라우저에서 **minsoojo 계정**인지 확인하고, 터미널에 `Login Succeeded`가 나오는지 확인한다. 이미 저장된 인증으로 성공하면 다시 로그인할 필요가 없다. 비밀번호·토큰·일회용 인증 코드를 채팅에 전달하지 않는다.

[Docker 공식 로그인 안내](https://docs.docker.com/reference/cli/docker/login/)

### 2. 이미지 저장소 하나 생성

[Docker Hub](https://hub.docker.com/) 로그인 → **My Hub → Repositories → Create repository**.

| 입력 | 값 |
|---|---|
| Namespace | `minsoojo` |
| Repository name | `fedops-onprem` |
| Visibility | `Private` |

임시 사용이므로 한 저장소 안에서 앱별 태그로 구분한다. 소스 저장소 8개에 맞춰 Docker 저장소 8개를 만들 필요는 없다. 공개로 배포하려면 별도 결정한다.

[Docker 공식 저장소 생성 안내](https://docs.docker.com/docker-hub/repos/create/)

### 3. 완료 여부 전달

“Docker 로그인 완료, minsoojo/fedops-onprem 비공개 저장소 생성 완료”라고 알려주면 된다. 실제 비밀번호·토큰 대신 성공 여부만 전달한다.

## 게시한 앱 이미지

| 로컬 이미지 | 게시한 이미지 태그 |
|---|---|
| `fedops-local/frontend:onprem-20260916` | `minsoojo/fedops-onprem:frontend-onprem-20260916` |
| `fedops-local/backend:onprem-20260916` | `minsoojo/fedops-onprem:backend-onprem-20260916` |
| `fedops-local/manager:onprem-20260916` | `minsoojo/fedops-onprem:manager-onprem-20260916` |
| `fedops-local/performance:onprem-20260916` | `minsoojo/fedops-onprem:performance-onprem-20260916` |
| `fedops-local/gateway:onprem-20260916` | `minsoojo/fedops-onprem:gateway-onprem-20260916` |
| `fedops-local/registry:onprem-20260916` | `minsoojo/fedops-onprem:registry-onprem-20260916` |

위 6종은 게시·재다운로드 확인을 완료했다. core wheel 생성용 이미지는 앱 배포 이미지가 아니므로 이 6종에 포함하지 않는다. MongoDB·MinIO·Redis·기존 CPU Task base는 확인한 기존 저장소의 digest를 사용한다.

아래는 이번에 사용한 Backend 업로드·조회 절차의 명령 형식이다. 전체 정확한 push 명령과 결과는 게시 증빙에 기록했다.

```powershell
docker tag fedops-local/backend:onprem-20260916 minsoojo/fedops-onprem:backend-onprem-20260916
docker push minsoojo/fedops-onprem:backend-onprem-20260916
docker buildx imagetools inspect minsoojo/fedops-onprem:backend-onprem-20260916
```

이미지 설정에는 태그 대신 레지스트리가 확인한 `docker.io/minsoojo/fedops-onprem@sha256:...`를 넣었다. 비공개 이미지를 받는 F의 pull 자격은 F 설치 안내에서 별도로 연결한다. GitHub 인증 토큰을 Docker Hub 자격으로 사용하지 않는다. 새 Git 저장소의 Task Runtime 연결과 F 배포는 아직 남아 있다.
