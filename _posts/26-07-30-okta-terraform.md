---
layout: single
title: "Okta 랩 5 — Terraform import로 기존 org 코드화하기, 그리고 코드화의 한계"
excerpt: "앞선 네 편이 콘솔과 API로 만든 구성의 프로토콜 검증이었다면, 이번엔 그렇게 만든 리소스를 Terraform으로 가져온다. 신규 생성이 아니라 운영 중인 org를 import 블록과 -generate-config-out으로 코드화하는 방향이다. 자격증명 검증이 plan이 아니라 apply에서 일어나는 지점, Sign On 탭의 EL 표현식 클레임 네 개가 okta_app_saml 스키마에 아예 대응되지 않아 IaC 재현 시 누락된다는 사실, 자동 생성 코드에 preconfigured_app이 자기 앱 이름으로 박혀 다른 org에서 생성이 거부되는 함정, 콘솔 Priority와 API priority가 다른 값이라는 점, 그리고 AD-sourced 그룹이 관리는 불가하지만 data source 참조는 되는 경계까지 명령 출력으로 확인한 기록이다."
date: 2026-07-30
categories: [IAM]
tags: [Okta, Terraform, IaC, terraform-import, Access-Policy, Active-Directory, 실측]
---

[전편]({% post_url 26-07-29-okta-ad-agent %})까지 네 편은 Okta의 프로토콜 동작과 AD 연동을 콘솔과 API로 확인한 기록이다. 이번에는 그렇게 만든 리소스를 Terraform으로 가져와 코드로 관리하는 과정을 다룬다. 신규 생성이 아니라 이미 운영 중인 org를 코드화하는 방향이며, 실제 IaC 도입 시나리오에 해당한다.

결론부터 적으면, 콘솔에서 설정한 것 중 Terraform으로 표현되지 않는 영역이 있었다. 그 경계를 확인하는 것이 이번 작업의 핵심이 됐다.

## 1. 환경

| 항목 | 값 |
|---|---|
| Terraform | v1.15.8 (windows_amd64) |
| provider | okta/okta v6.13.0 |
| org | Integrator Free Plan |
| 대상 리소스 | SAML 앱 1개, App sign-in 정책 1개와 그 규칙 1개 |

provider source는 `okta/okta`다. 구버전 문서에 나오는 `oktadeveloper/okta`는 더 이상 유효하지 않다.[^1]

```hcl
# versions.tf
terraform {
  required_version = ">= 1.5"

  required_providers {
    okta = {
      source  = "okta/okta"
      version = "~> 6.13"
    }
  }
}
```

```hcl
# providers.tf
provider "okta" {
  org_name = "{org}"
  base_url = "okta.com"
  # api_token is injected via OKTA_API_TOKEN env var
}
```

`org_name`에는 서브도메인만 넣는다. `base_url`이 `okta.com`이므로 둘을 합쳐 org URL이 구성된다.

인증은 API Token(SSWS)으로 시작했다. provider는 `OKTA_ORG_NAME`, `OKTA_BASE_URL`, `OKTA_API_TOKEN` 환경변수를 자동으로 인식한다.

## 2. 자격증명 검증은 plan이 아니라 apply에서 일어난다

토큰을 설정하지 않은 상태에서 신규 리소스만 있는 구성으로 `plan`을 실행했다.

```powershell
terraform plan
```

```
  # okta_group.tf_test will be created
  + resource "okta_group" "tf_test" { ... }

Plan: 1 to add, 0 to change, 0 to destroy.
```

통과한다. 신규 생성만 있는 계획은 기존 상태를 조회할 필요가 없어 API 호출이 발생하지 않는다.

같은 상태에서 `apply`를 실행하면 provider 구성 단계에서 즉시 실패한다.

```
Error: [ERROR] no Okta credentials provided. Please set one of the following:
'api_token' (or OKTA_API_TOKEN env var), 'access_token' (or OKTA_ACCESS_TOKEN
env var), or 'private_key' + 'client_id' (or OKTA_API_PRIVATE_KEY +
OKTA_API_CLIENT_ID env vars).
```

운영 관점의 함의가 있다. CI 파이프라인에서 `plan` 단계만 돌려 변경 내역을 검토하는 구성이라면, 자격증명 문제가 `apply` 단계까지 숨는다. 신규 리소스만 추가하는 PR에서는 `plan`이 정상 통과하므로 리뷰에서도 걸리지 않는다.

환경변수는 프로세스 범위이므로 터미널을 새로 열면 사라진다. VS Code 통합 터미널은 VS Code 실행 시점의 환경 블록을 상속하므로, 사용자 환경변수를 등록해도 VS Code를 재시작하지 않으면 반영되지 않는다.

## 3. import 블록과 설정 자동 생성

Terraform 1.5 이후에는 CLI `terraform import` 대신 설정 파일에 `import` 블록을 선언하는 방식을 쓸 수 있다. 여기에 `-generate-config-out`을 붙이면 provider가 읽은 상태로부터 HCL을 생성한다.

```hcl
# imports.tf
import {
  to = okta_app_saml.saml_sp
  id = "{saml_app_id}"
}
```

```powershell
terraform plan "-generate-config-out=generated_saml.tf"
```

PowerShell에서는 인수 전체를 따옴표로 감싸야 한다. 감싸지 않으면 `=` 뒤가 별도 인수로 분리되어 `Too many command line arguments`가 발생한다.

앱 ID는 SSO URL에 들어가는 `exk...` 키가 아니라 API용 `0oa...` 값이다. 두 값이 다르며, 혼동하면 존재하지 않는 객체로 처리된다.

실행 결과는 다음과 같다.

```
Plan: 1 to import, 0 to add, 0 to change, 0 to destroy.

Warning: Config generation is experimental
```

`0 to change`가 나온 것은 생성된 설정이 실제 상태와 완전히 일치한다는 뜻이다. provider의 읽기 충실도는 이 리소스 유형에서 문제가 없었다.

읽기 전용 속성은 생성 코드에서 제외된다. `certificate`, `keys`, `metadata`, `entity_key`, `entity_url`, `http_post_binding`, `http_redirect_binding`, `embed_url`, `metadata_url`, `name`이 여기 해당한다. plan 미리보기에는 값이 표시되지만 코드에는 들어가지 않는다.

## 4. 코드화되지 않는 설정이 있다

생성된 `okta_app_saml` 코드에서 `attribute_statements` 블록은 하나뿐이었다.

```hcl
attribute_statements {
  filter_type  = "REGEX"
  filter_value = ".*"
  name         = "groups"
  namespace    = "urn:oasis:names:tc:SAML:2.0:attrname-format:unspecified"
  type         = "GROUP"
  values       = []
}
```

앞선 편에서 Sign On 탭의 EL 표현식으로 설정한 `email`, `firstName`, `lastName`, `amr` 네 개 클레임이 전혀 포함되지 않았다. legacy Group Attribute Statements로 만든 `groups` 항목만 남았다.

이 결과는 앞서 API로 앱 객체를 조회했을 때 `settings.signOn.attributeStatements`에 legacy 항목만 있던 것과 일치한다. 신규 expression 방식 클레임은 별도 객체로 저장되며 `okta_app_saml` 스키마에 대응 인수가 없다.

실무 관점에서 문제가 되는 지점이다.

- 이 앱을 IaC로 재현하면 클레임 네 개가 빠진 상태로 만들어진다
- 누락된 클레임은 콘솔 수작업으로 채워야 하고, 그 부분은 코드 리뷰·변경 이력·환경 간 복제에서 제외된다
- 특히 `session.amr`은 앞선 편에서 확인한 대로 SAML assertion에서 실제 인증 수단을 알 수 있는 유일한 근거다. 그것이 코드 관리 밖에 있다

"Terraform으로 Okta를 관리한다"는 진술이 어디까지 참인지 구분해서 말해야 한다는 뜻이다.

## 5. 자동 생성 코드의 함정 두 가지

### 5.1 템플릿 구문 충돌

Okta의 속성 템플릿 구문이 Terraform 보간 구문과 겹친다. 생성 코드는 이를 이스케이프한다.

```hcl
idp_issuer               = "http://www.okta.com/$${org.externalKey}"
subject_name_id_template = "$${user.userName}"
user_name_template       = "$${source.login}"
```

손으로 작성할 때 `${`로 쓰면 Terraform이 자기 변수로 해석해 실패한다. `$$`로 시작해야 리터럴 `$`가 된다.

### 5.2 preconfigured_app

커스텀 SAML 앱인데도 생성 코드에 다음 인수가 포함됐다.

```hcl
preconfigured_app = "{org}_samlsp_1"
```

값은 이 앱 자신의 `name`이다. OIN 카탈로그 앱을 지정하는 인수에 자기 이름이 들어간 형태다.

import만 할 때는 문제가 없다. 그러나 이 코드로 새 앱을 만들려 하면 실패한다. 작업 중 import 블록을 apply 전에 삭제한 실수로 이 경로를 실제로 밟았다.

```
Error: failed to create SAML application: the API returned an error:
Api validation failed: mediated.
Causes: errorSummary: Cannot create an existing App Wizard App
```

Okta가 동일 App Wizard App 이름 충돌로 거부했다. 중복 앱은 생성되지 않았고 기존 앱도 영향받지 않았다. 다만 이 코드를 다른 org에 재사용하려면 `preconfigured_app`을 제거해야 한다.

부수적으로 확인된 순서 문제도 기록해 둔다. `import` 블록은 `apply`가 성공한 뒤에 제거해야 한다. 먼저 제거하면 Terraform은 import 대상을 잃고 신규 생성을 시도한다.

정상 순서는 다음과 같다.

```powershell
Move-Item generated_saml.tf saml_sp.tf -Force
terraform apply          # yes → Import complete
Remove-Item imports.tf
terraform plan            # No changes 확인
```

## 6. Access Policy와 규칙

앱의 `authentication_policy` 인수에 정책 ID가 박혀 있으므로 정책도 코드화 대상이 된다.

정책 리소스는 단순하다.

```hcl
resource "okta_app_signon_policy" "any_two_factors" {
  catch_all   = true
  description = "Require two factors to access."
  name        = "Any two factors"
  priority    = 1
}
```

인수가 네 개뿐이다. 주목할 점은 **어떤 앱이 이 정책을 사용하는지가 포함되지 않는다**는 것이다. 연결은 앱 리소스의 `authentication_policy` 인수가 담당한다.

콘솔에서는 정책 상세의 Applications 탭에서 적용 대상 앱 목록을 볼 수 있다. 코드에서는 그 뷰가 없다. 정책 변경의 영향 범위를 알려면 모든 앱 리소스를 훑어야 한다. 정책을 손대기 전에 무엇이 깨질지 파악하는 비용이 콘솔보다 높다.

규칙 리소스의 import ID는 `정책ID/규칙ID` 복합 형식이다.

```hcl
import {
  to = okta_app_signon_policy_rule.ad_password_only
  id = "{policy_id}/{rule_id}"
}
```

규칙 ID는 API로 조회했다.

```powershell
$h = @{ Authorization = "SSWS $env:OKTA_API_TOKEN"; Accept = "application/json" }
$r = Invoke-RestMethod -Uri "https://{org}.okta.com/api/v1/policies/{policy_id}/rules" -Headers $h
$r | ConvertTo-Json -Depth 10
```

`-Depth` 값을 낮게 주면 오해를 부른다. 깊이 한계를 넘는 배열은 `ToString()`으로 직렬화되어 공백으로 이어붙은 하나의 문자열처럼 보인다. `-Depth 4`로 출력했을 때 `groups.include`가 `"00g... 00g..."`로 나와 API가 공백 구분 문자열을 반환한 것처럼 읽혔으나, 실제 값은 배열이었다. `Select-Object id, name`이 빈 표를 낸 것도 같은 구조 문제이며, 응답이 중첩 객체 배열이라 최상위에 해당 속성이 없었기 때문이다.

## 7. 콘솔의 Priority와 API의 priority가 다르다

규칙 두 개의 값을 비교하면 다음과 같다.

| 규칙 | 콘솔 Priority | API priority | system | 허용 메서드 |
|---|---|---|---|---|
| AD User - password only | 1 | 0 | false | GET PUT DELETE |
| Catch-all Rule | 2 | 99 | true | GET PUT |

콘솔은 표시 순번을 보여주고 API는 실제 정렬 가중치를 반환한다. 코드에 `priority`를 지정할 때 콘솔에서 본 숫자를 그대로 쓰면 의도와 다른 순서가 된다.

Catch-all Rule은 `system: true`이고 `_links`에 DELETE가 없다. 삭제할 수 없는 시스템 규칙이므로 Terraform 관리 대상에서 제외하는 것이 맞다. 정책 객체 자체도 `system: true`였다.

생성된 규칙 코드에서 눈에 띄는 것은 `constraints`다.

```hcl
constraints = ["{\"knowledge\":{\"types\":[\"password\"],\"required\":true}}"]
```

HCL 안에 JSON을 문자열로 담은 리스트다. 콘솔에서 체크박스로 고른 "Password only" 요구가 이렇게 표현된다.

코드화는 가능하지만 실질적인 약점이 있다.

- 문자열이므로 HCL 파서가 내부 구조를 검증하지 않는다
- 오타는 `plan` 단계에서 잡히지 않고 API가 거부할 때까지 드러나지 않는다
- 리뷰어가 이스케이프된 JSON을 읽고 인증 요구 조건을 판단해야 한다

인증 정책은 앱 설정과 달리 자주 변경되는 대상이다. 그 대상의 핵심 조건이 검증되지 않는 문자열로 표현된다는 점은 도입 판단에 반영할 만하다.

## 8. AD-sourced 그룹 — 관리는 불가, 참조는 가능

자동 생성된 규칙 코드는 그룹을 ID로 하드코딩한다.

```hcl
groups_included = ["{group_id_1}", "{group_id_2}"]
```

두 그룹은 AD Agent가 Import한 AD-sourced 그룹이다. 앞선 편에서 확인한 대로 이 그룹은 Okta 콘솔에서도 멤버를 편집할 수 없고, Terraform으로 생성·수정할 수도 없다.

그러나 data source 조회는 동작한다.

```hcl
# data.tf
data "okta_group" "ad_lab_users" {
  name = "okta-lab-users"
}

data "okta_group" "ad_lab_admins" {
  name = "okta-lab-admins"
}
```

```hcl
groups_included = [
  data.okta_group.ad_lab_users.id,
  data.okta_group.ad_lab_admins.id,
]
```

```
data.okta_group.ad_lab_users: Read complete after 1s [id={group_id_1}]
data.okta_group.ad_lab_admins: Read complete after 1s [id={group_id_2}]

No changes. Your infrastructure matches the configuration.
```

같은 방식으로 하드코딩된 정책 ID도 리소스 참조로 교체했다.

```hcl
# policies.tf
policy_id = okta_app_signon_policy.any_two_factors.id

# saml_sp.tf
authentication_policy = okta_app_signon_policy.any_two_factors.id
```

교체 후에도 `No changes`가 유지됐다. 값이 동일하므로 변경이 발생하지 않는 것이 정상이다.

이 패턴이 AD 연동 org의 IaC 관리 경계를 그대로 반영한다.

| 리소스 | 소유 | Terraform |
|---|---|---|
| 사용자, 그룹 | Active Directory | data source 참조만 |
| 앱, 정책, 규칙, 매핑 | Okta | 생성·수정·삭제 |

사용자와 그룹의 원천은 AD이고 Terraform은 앱과 정책을 담당한다. 접근 권한의 실질적 통제는 "어떤 그룹이 어떤 앱을 쓰는가"(Terraform)와 "누가 그 그룹에 속하는가"(AD)로 분리된다.

data source 참조에는 부수 효과도 있다. AD 측에서 그룹 이름이 바뀌면 `plan`이 조회 실패로 멈춘다. ID 하드코딩이었다면 유령 ID를 가리키는 상태로 조용히 유지된다.

## 9. 최종 구성

```
okta-terraform-lab/
├── .gitignore
├── versions.tf      # provider 버전 제약
├── providers.tf     # org 설정 (토큰은 환경변수)
├── data.tf          # AD-sourced 그룹 조회
├── saml_sp.tf       # SAML 앱
└── policies.tf      # App sign-in 정책과 규칙
```

`.gitignore`는 코드보다 먼저 만들었다.

```
.terraform/
*.tfstate
*.tfstate.*
*.tfvars
!*.tfvars.example
crash.log
```

`.terraform.lock.hcl`은 커밋한다. provider 버전을 고정하는 파일이다.

state 파일은 리소스 ID를 담고 있으며 잃으면 import로 다시 붙여야 한다. 로컬 state로 진행했고 원격 백엔드 전환은 하지 않았다.

## 10. 미측정 항목

- **private key JWT 인증** — 현재는 API Token(SSWS) 방식이며 발급자 권한을 그대로 상속한다. 스코프 제한이 불가능하다. OAuth 2.0 + private key JWT로 전환하면 리소스별 필요 스코프를 실측할 수 있다
- **네트워크 존 제한** — API Token 생성 시 출발지 IP를 제한하는 옵션이 있다. 스코프 제한 대 네트워크 제한이라는 두 통제 축의 비교는 하지 않았다
- **OIDC 앱 import** — `okta_app_oauth` 스키마에서 PKCE·grant·redirect가 어떻게 표현되는지
- **신규 expression 클레임의 API 경로** — `okta_app_saml`로 표현되지 않는 것은 확인했으나, 별도 API 엔드포인트가 있어 provider의 다른 리소스나 `restapi` provider로 우회 가능한지는 확인하지 않았다
- **원격 state 백엔드** — 팀 작업과 CI 전제
- **`terraform destroy` 동작** — 시스템 정책과 규칙이 state에 있을 때 어떻게 처리되는지

## 정리

이번 작업에서 문서만으로는 예측되지 않았던 지점은 다음과 같다.

1. 자격증명 검증이 `plan`이 아니라 `apply`에서 일어난다. 신규 생성만 있는 계획은 토큰 없이 통과한다
2. Sign On 탭의 EL 표현식 클레임은 `okta_app_saml`로 코드화되지 않는다. IaC 재현 시 누락된다
3. 자동 생성 코드에 `preconfigured_app`이 자기 앱 이름으로 들어가며, 다른 org에서 재사용하면 생성이 거부된다
4. 콘솔의 Priority 표시와 API의 priority 값이 다르다
5. 인증 요구 조건이 이스케이프된 JSON 문자열로 표현되어 HCL 수준의 검증을 받지 못한다
6. AD-sourced 리소스는 관리는 불가하지만 data source 참조는 가능하다

2번과 5번은 도입 판단에 직접 영향을 준다. "Okta를 코드로 관리한다"는 목표를 세울 때, 어느 설정이 코드 밖에 남는지 먼저 확인해야 한다.

---

[^1]: okta/okta Terraform Provider 문서 — <https://registry.terraform.io/providers/okta/okta/latest/docs>
[^2]: Terraform 플러그인 서명 정책 (init 출력에 안내되는 문서) — <https://developer.hashicorp.com/terraform/cli/plugins/signing>
