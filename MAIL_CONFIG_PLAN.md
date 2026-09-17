# 메일 처리 방식 확인 및 Helm 설정 계획

2026-09-17 · 사용자: 원본 방식 파악 → 계획 보고 → 구현·검증·실행 요청.
R02/R03/R08/R09/R12, W03/W05/W07. 대상은 새 소스 저장소와 F이며 기존 운영 서버는 변경하지 않는다.

## 확인한 원본 동작

근거: `forShare/forShare/sources/fedops-gateway-runtime`의 Java 소스·application.yml (읽기 전용).

1. Web Backend가 Gateway `/members/emails/verification-requests`에 요청한다.
2. Gateway가 6자리 코드를 만들고 Spring JavaMailSender로 SMTP 전송한다.
3. 전송 후 Redis에 코드를 1,800,000ms(30분) 저장한다.
4. 검증 API가 Redis 값과 입력 코드를 비교한다.

원본 SMTP는 smtp.gmail.com:587, 인증 및 STARTTLS 활성이다. 로그인 정보는 복사하지 않는다.
MailService는 From을 지정하지 않았다. 현재 정제본의 MailService/MemberService/EmailConfig는 원본과 동일하다.
F는 테스트용 Mailpit:1025로 전송 중이다. 2026-09-17 05:26 UTC 메일 수신을 메타데이터에서 확인했다.
현재 브라우저 URL에는 이전 Gateway Pod 이름을 검색하는 조건이 남아 있다. 로컬 8025 도달 여부는 추가 확인한다.

## 변경 계획

- 코드 생성·Redis 저장·검증 및 Web→Gateway 구조 유지.
- 기존 `smtp.host/port/auth/starttls/starttlsRequired`에 `ssl`, `fromAddress`, `fromName` 추가.
- `fromAddress`가 비어 있으면 기존 SMTP Secret의 username을 사용. username도 비어 있거나 주소가 잘못되면 시작 시 오류. OS 사용자/Pod 이름을 발신자로 쓰지 않음.
- From 주소와 SMTP 로그인 계정을 구분. 표시명은 UTF-8 인코딩. 발신자 값의 줄바꿈과 복수 주소 거부.
- 인증 정보는 `secrets.smtp`의 기존 `SPRING_MAIL_USERNAME/PASSWORD`로만 전달.
- 587 STARTTLS, 465 implicit TLS, Mailpit/내부 relay 평문 설정을 지원. SSL과 STARTTLS 중복 및 required-without-enabled 조합은 거부.
- 발송 실패 로그에 인증코드/메일 본문을 남기지 않음.
- 원본 Gmail SMTP 예제와 F 테스트 발신자 overlay 제공. 실제 외부 수신은 사용할 SMTP 계정 결정 후 전환하며 새 자격은 채팅에 받지 않음.

## 검증·배포

- Java 단위 검사: From/UTF-8 표시명, 설정 오류·메일 전송 실패, TLS 설정.
- 일회용 로컬 Gateway·Redis·Mailpit: 발송→수신→코드 검증, 발신자 설정 변경을 같은 이미지로 반복 확인.
- Chart lint/template/schema와 SMTP 모드별 값 검사.
- Gateway 이미지만 재빌드·검증·게시, digest 고정 및 GitHub 문서 갱신.
- F에서 사용자 선택한 SMTP 모드로 Chart upgrade, 기존 데이터/Secrets 보존. Mailpit 테스트 발송·코드 검증 시 코드/본문은 기록하지 않음.

## 상태

- [x] 원본 확인·계획 보고
- [x] 구현 및 로컬 검증
- [ ] 소스·이미지·차트 게시
- [ ] F 적용 및 메일 검증
- [ ] 실제 외부 메일함 수신 (외부 SMTP 선택 시 별도 확인)

기술 근거: [Spring 메일](https://docs.spring.io/spring-framework/reference/integration/email.html),
[SMTP 옵션](https://eclipse-ee4j.github.io/angus-mail/docs/api/org.eclipse.angus.mail/org/eclipse/angus/mail/smtp/package-summary.html),
[Mailpit API](https://mailpit.axllent.org/docs/api-v1/).

## 로컬 완료 증빙

Java 단위 검사 4개와 발신자 3개 프로필(명시 주소/한국어 이름/로그인 계정 fallback)의 Gateway·Redis·Mailpit 수신·코드 검증 통과. Chart 검사 635개 통과. `docs/helm/evidence/gateway-mail.json` 및 `chart-verification.json`에 기록. Gateway `964ede9`와 Docker Hub digest `sha256:42b21b3c35760d40c402095d5fd6e38daba3d3cf03c7fdb6bffe94eaa636f92e` 게시·재다운로드 대조 완료. 외부 SMTP 미선택이므로 F는 Mailpit 유지.
