# 개인 Docker Hub 사용 준비

계정: **minsoojo**. 현재 PC에서 만든 앱 이미지 6종을 전달한다. GitHub 저장소와 Docker Hub 저장소는 별개다.

## 사용자가 할 일

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

## 이후 진행할 작업

| 로컬 이미지 | 게시할 이미지 태그 |
|---|---|
| `fedops-local/frontend:onprem-20260916` | `minsoojo/fedops-onprem:frontend-onprem-20260916` |
| `fedops-local/backend:onprem-20260916` | `minsoojo/fedops-onprem:backend-onprem-20260916` |
| `fedops-local/manager:onprem-20260916` | `minsoojo/fedops-onprem:manager-onprem-20260916` |
| `fedops-local/performance:onprem-20260916` | `minsoojo/fedops-onprem:performance-onprem-20260916` |
| `fedops-local/gateway:onprem-20260916` | `minsoojo/fedops-onprem:gateway-onprem-20260916` |
| `fedops-local/registry:onprem-20260916` | `minsoojo/fedops-onprem:registry-onprem-20260916` |

로그인/저장소 확인 후 위 이미지 tag·push와 게시 digest 확인을 진행한다. 아직 업로드하지 않았다. core wheel 생성용 이미지는 앱 배포 이미지가 아니므로 이 6종에 포함하지 않는다. MongoDB·MinIO·Redis·기존 CPU Task base는 확인한 기존 저장소의 digest를 사용한다.

아래는 Backend에 대한 **업로드 예시이며 아직 실행하지 않은 명령**이다.

```powershell
docker tag fedops-local/backend:onprem-20260916 minsoojo/fedops-onprem:backend-onprem-20260916
docker push minsoojo/fedops-onprem:backend-onprem-20260916
docker buildx imagetools inspect minsoojo/fedops-onprem:backend-onprem-20260916
```

게시 후 Chart에는 태그 대신 레지스트리가 확인한 `minsoojo/fedops-onprem@sha256:...`를 넣는다. 비공개 이미지를 받는 F의 pull 자격은 F 설치 안내에서 별도로 연결한다. GitHub 인증 토큰을 Docker Hub 자격으로 사용하지 않는다.
