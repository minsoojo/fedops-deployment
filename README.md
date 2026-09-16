# FedOps 온프레미스 배포

Chart 및 별도 소스 저장소의 고정 commit을 관리합니다. 기존 upstream의 전체 Git 이력이 아닌 정제 전달본에서 시작한 새 저장소입니다.

## 현재 상태

- Chart 0.1.0 정적 검사 540개, 기본 자원 42개.
- 앱 6종 로컬 이미지 빌드·기동, Mongo 인증·Web SDK/MinIO 왕복 포함 12개 검사 통과.
- core wheel 생성·45개 Python 파일 대조 완료. 실제 Task Runtime 연결·F/FL 검증은 남아 있습니다.
- Docker Hub 계정: minsoojo. [로그인·비공개 저장소 준비 방법](DOCKER_HUB.md). 이미지 업로드·Docker Hub 저장소 생성은 아직 하지 않았습니다.
- 위 결과는 `verification/`의 기존 로컬 증빙입니다. 새 GitHub clone 기반 재빌드나 F 배포 성공을 뜻하지 않습니다.

## 소스와 버전

| 저장소 | 기준 commit |
|---|---|
| [fedops-core-onprem](https://github.com/minsoojo/fedops-core-onprem) | `ff5f44ddea2705c8d901a54a0272f517822da8f4` |
| [fedops-web-onprem](https://github.com/minsoojo/fedops-web-onprem) | `d51644b1659e7b438bcc59a746cbafa22e5a058a` |
| [fedops-server-onprem](https://github.com/minsoojo/fedops-server-onprem) | `677be801c33e8d5d53e1aedd27c3f152f1d606f3` |
| [fedops-gateway-onprem](https://github.com/minsoojo/fedops-gateway-onprem) | `e64d3bee896264ce9e0ce9de71a15fc76b4e2088` |
| [fedops-registry-onprem](https://github.com/minsoojo/fedops-registry-onprem) | `548c5fbb4e0af0883d5b76fbefc2b5caecd9c63f` |
| [fedops-agent-studio-onprem](https://github.com/minsoojo/fedops-agent-studio-onprem) | `3a66538f33b720641d80f742a8dfe672db2c0c2a` |
| [fedops-silo-baseline-onprem](https://github.com/minsoojo/fedops-silo-baseline-onprem) | `c9c8939e9fe26dc13b8d030b1924e917a2d6635c` |

`sources.json`의 URL과 commit으로 아래처럼 형제 디렉터리에 가져옵니다. 비공개 저장소를 읽을 수 있는 Git 인증이 필요합니다.

```powershell
$repos = Get-Content sources.json -Raw | ConvertFrom-Json
foreach ($repo in $repos) {
    git clone ($repo.url + '.git') ('../' + $repo.name)
    git -C ('../' + $repo.name) checkout --detach $repo.commit
}
```

## 이미지 빌드

이 저장소 루트에서 Docker Desktop Linux/amd64로 실행합니다. 소스마다 Dockerfile/.dockerignore 및 필요한 Python lock을 포함합니다.

```powershell
docker build --platform linux/amd64 -t fedops-local/frontend:onprem-20260916 ../fedops-web-onprem/client
docker build --platform linux/amd64 -t fedops-local/backend:onprem-20260916 ../fedops-web-onprem/server
docker build --platform linux/amd64 -t fedops-local/manager:onprem-20260916 ../fedops-server-onprem/server_manager
docker build --platform linux/amd64 -t fedops-local/performance:onprem-20260916 ../fedops-server-onprem/fl_performance
docker build --platform linux/amd64 -t fedops-local/gateway:onprem-20260916 ../fedops-gateway-onprem
docker build --platform linux/amd64 -t fedops-local/registry:onprem-20260916 ../fedops-registry-onprem
docker build --platform linux/amd64 -t fedops-local/core:onprem-20260916 ../fedops-core-onprem/src/python
```

core 이미지는 wheel 생성용이며 현재 Task 배포 이미지가 아닙니다. 기존 Task profile/Release의 Git revision·패키지 pin은 아직 이전 출처를 사용합니다. 새 저장소가 생성됐다는 이유만으로 그 연결이 바뀌지 않습니다.

## Chart

[구성·Secret·F 입력 안내](charts/fedops/README.md), [입력 예시](charts/fedops/examples/f-values.yaml).
`tests/static-values.yaml`은 가짜 주소/이미지를 쓰는 정적 검사 전용이며 배포하지 않습니다.

```powershell
helm lint charts/fedops -f charts/fedops/tests/static-values.yaml --strict --kube-version 1.36.0
helm template fedops charts/fedops -n fedops -f charts/fedops/tests/static-values.yaml --kube-version 1.36.0
```

전체 Python 검사에는 Helm 4.3.0, PyYAML/jsonschema/referencing, `work/helm-tools` 아래 공식 [K8s 1.36 OpenAPI](https://raw.githubusercontent.com/kubernetes/kubernetes/v1.36.0/api/openapi-spec/swagger.json)를 `kubernetes-v1.36.0-swagger.json`으로, [Istio 1.30.4 CRD](https://raw.githubusercontent.com/istio/istio/1.30.4/manifests/charts/base/files/crd-all.gen.yaml)를 `istio-1.30.4-crds.yaml`로 준비합니다. 실행: `python -B charts/fedops/tests/verify_chart.py --helm <helm실행파일경로>`.

F 적용·신규 Secret·버킷·저장 디렉터리는 사용자 직접 설치 단계입니다. 실제 비밀번호·kubeconfig·토큰을 저장소에 넣지 않습니다.
