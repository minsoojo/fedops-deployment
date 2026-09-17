# FedOps 인증메일 설정

2026-09-17 F 적용 완료: Chart 0.1.2/revision 4 deployed. Web 발송→Mailpit 수신→Gateway 코드 검증 성공. 현재 SMTP 모드는 Mailpit이며 실제 외부 메일함 전송은 미설정이다.

## 원본 방식과 변경점

원본은 `Web → Java Gateway → Gmail SMTP(587/STARTTLS) → 수신 메일함`이었다.
Gateway가 6자리 코드를 생성하고 SMTP 발송 성공 후 Redis에 30분 동안 저장한다.
코드 생성·발송·검증 경로는 유지했다. 발신자를 지정하지 않던 부분을 명시적으로 설정하도록 바꿨다.

SMTP 서버와 표시되는 발신자는 별개다. SMTP 제공자가 허용하는 계정·발신 주소를 사용해야 한다.
F 테스트는 `Web → Gateway → Mailpit`으로 받는다. Mailpit은 외부 메일함으로 전달하지 않는다.

## Helm 설정

```yaml
smtp:
  host: smtp.gmail.com
  port: 587
  auth: true
  starttls: true
  starttlsRequired: true
  ssl: false
  fromAddress: ""  # 빈 값이면 SMTP Secret의 username 사용
  fromName: FedOps
secrets:
  smtp: fedops-smtp
```

| 설정 | 의미 |
|---|---|
| `smtp.host`, `port` | 메일을 전달할 SMTP 서버·포트 |
| `smtp.auth` | SMTP 로그인 여부 |
| `smtp.starttls`, `starttlsRequired` | 접속 후 TLS로 전환, TLS 실패 시 전송 거부 |
| `smtp.ssl` | 접속부터 TLS 사용(주로 465). STARTTLS 두 옵션은 false로 설정 |
| `smtp.fromAddress` | 수신자가 보는 발신 주소. 빈 값이면 Secret의 로그인 계정 사용 |
| `smtp.fromName` | 발신자 표시명. 한국어 가능, 빈 값도 가능 |
| `secrets.smtp` | 같은 namespace에 있는 SMTP Secret 이름 |

Secret 키는 `SPRING_MAIL_USERNAME`, `SPRING_MAIL_PASSWORD`다. 로그인 계정·비밀번호를 values나 Git에 넣지 않는다.
SMTP 인증을 사용하지 않는 relay라도 발신 주소는 설정한다. 주소가 잘못되면 Gateway 시작 시 오류로 알려준다.
연결/읽기/쓰기 제한은 기존처럼 5초, 코드 유효 시간은 30분이다.

## SMTP 모드

| 용도 | 포트 예 | auth | starttls / required | ssl |
|---|---:|---|---|---|
| 기존 Gmail SMTP | 587 | true | true / true | false |
| implicit TLS SMTP | 465 | true | false / false | true |
| F Mailpit | 1025 | false | false / false | false |

메일 수신은 SMTP 제공자의 정책과 자격에 따른다. Gmail의 앱 비밀번호 사용 가능 여부는 계정 보안 설정/관리자 정책에 따라 확인한다.
기존 운영 서버의 Gmail 비밀번호나 Secret을 가져오지 않았다.

## F 테스트 적용 파일

`charts/fedops/examples/f-test-mail.yaml`은 `FedOps Test <noreply@fedops.test>`로 Mailpit에 보낸다.
기존 F values·이미지·IP overlay 뒤에 이 파일을 추가한다. 외부 SMTP로 전환할 때는 마지막 파일을 자체 SMTP 값 또는 `smtp-gmail.yaml`로 대체하고 해당 Secret을 준비한다.

```bash
export KUBECONFIG="$HOME/.kube/fedops-f.conf"
helm upgrade fedops ~/fedops-deployment/charts/fedops \
  --namespace fedops --kube-context fedops-f \
  -f ~/fedops-f-values.yaml \
  -f ~/fedops-deployment/charts/fedops/examples/images-minsoojo.yaml \
  -f ~/fedops-deployment/charts/fedops/examples/f-ip-access.yaml \
  -f ~/fedops-deployment/charts/fedops/examples/f-test-mail.yaml \
  --wait --timeout 5m
```

SMTP Secret 값만 변경한 경우에는 `kubectl --context=fedops-f -n fedops rollout restart deployment/fedops-gateway`로 다시 읽게 한다.
현재 Chart는 ConfigMap 변경 시 모든 기본 Deployment의 checksum이 바뀌므로 Helm 설정 변경 시 잠깐 접속이 중단될 수 있다.

## 인증메일이 안 보일 때

현재 테스트 메일함은 **http://127.0.0.1:8025/** 다. Web IP 접속과 별개의 테스트 도구다.
`/search?q=root@옛Pod이름` 같은 기존 검색 조건을 지우고 전체 메일함을 확인한다.
Pod가 교체돼도 새 메일의 발신자는 설정한 From 주소로 일정하게 유지된다.

현재 PC의 SSH 터널이 끊겼다면, F에서 Mailpit port-forward가 실행 중인 상태에서 다음을 유지한다.

```bash
ssh -N -L 127.0.0.1:8025:127.0.0.1:8025 ccl-f-server@192.9.203.184
```

F의 port-forward도 종료됐다면 F에서 먼저 실행한다.

```bash
KUBECONFIG=~/.kube/fedops-f.conf kubectl --context=fedops-f -n fedops \
  port-forward --address=127.0.0.1 svc/fedops-test-mail 8025:8025
```

실제 외부 메일함 전환은 위 Mailpit 테스트와 별개이며, 실제 수신 전까지 완료로 표시하지 않는다.

근거: [Spring의 From 설정](https://docs.spring.io/spring-framework/reference/integration/email.html),
[SMTP TLS 옵션](https://eclipse-ee4j.github.io/angus-mail/docs/api/org.eclipse.angus.mail/org/eclipse/angus/mail/smtp/package-summary.html).
