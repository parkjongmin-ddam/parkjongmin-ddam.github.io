---
layout: single
title: "Okta OIDC 연동 실측 — 에이전트 빌더에 '로그인 성공 ≠ 인가' 붙이기"
excerpt: "지금까지의 Okta 실습은 프로토콜을 관찰하는 쪽이었다. 이번에는 직접 만드는 앱(자연어로 AI 에이전트를 만들고 실행·평가하는 Streamlit 앱)에 Okta를 IdP로 붙였다. 앱에는 역할(RBAC)과 권한 경계가 먼저 있었고, OIDC는 '주체를 무엇으로 믿을 것인가'만 바꾼다. Okta 쪽에서 걸린 지점 — scope에 groups를 넣으면 invalid_scope 400, Access Policy가 없으면 MFA까지 통과하고도 no_matching_policy로 토큰 발급 거부, 그룹 이름 불일치는 로그인 후 deny-by-default 거부, 앱 미할당 그룹은 access_denied — 를 순서대로 기록했다. 로그인 성공이 곧 인가가 아니라는 것이 이 글의 전부다."
date: 2026-09-29
categories: [IAM]
tags: [Okta, OIDC, RBAC, Streamlit, 실측]
---

## 1. 배경

지금까지의 Okta 실습(SAML, OIDC, SCIM, AD Agent)은 Okta가 무엇을 보내는지 **관찰**하는 쪽이었다. 이번에는 방향을 바꿔, 직접 만들고 있는 앱에 Okta를 IdP로 붙였다.

대상 앱은 파이널 프로젝트로 만드는 **deep_builder_agent** — 자연어로 AI 에이전트 명세를 생성하고, 화이트리스트에 없는 도구는 프롬프트로 요청해도 붙지 않게 강제하는 빌더다. CLI와 Streamlit UI가 있다.

앱이 어떻게 동작하는지는 터미널 데모로 대신한다. 자연어로 에이전트를 만들고("동사가 셋이면 도구도 셋"), 셸 실행 에이전트를 요청하면 도구가 붙지 않고, 팀 에이전트가 계산·검산을 분담하는 흐름이다:

<video controls preload="metadata" style="width:100%; max-width:100%;">
  <source src="/assets/images/26-09-29/okta-agent/demo-terminal-edit.mp4" type="video/mp4">
  브라우저가 video 태그를 지원하지 않습니다.
</video>

이 앱에는 이미 두 층의 통제가 있었다.

1. **행위 통제 (RBAC)** — 주체의 역할이 허용하는 행위(create_agent / revise_agent / run_agent / view)만 실행된다
2. **권한 경계 (permissions boundary)** — 에이전트를 생성·수정할 때, 스펙이 요청한 도구는 **생성자의 역할이 허용한 도구를 초과할 수 없다** (AWS IAM permissions boundary 개념 이식). 위임이 권한 상승 경로가 되면 안 된다

여기에 OIDC를 붙이는 목적은 하나다. 지금까지 "사이드바에서 고른 이름"이었던 주체를 **IdP가 검증한 신원(이메일 + 그룹 클레임)**으로 바꾸는 것. 역할은 화면에서 고르는 게 아니라 Okta 그룹에서 온다.

## 2. 구성

| 항목 | 값 |
|---|---|
| Okta org | Integrator Free Plan |
| 앱 | Streamlit — `st.login` (네이티브 OIDC, Authorization Code) |
| redirect URI | `http://localhost:8501/oauth2callback` |
| 인가 서버 | Okta default 커스텀 인가 서버 (`/oauth2/default`) |
| 역할 정책 | `iam.json` — roles / principals / groups (deny-by-default) |
| 감사 로그 | `logs/audit.jsonl` — 허용·거부 모두 JSONL 기록 |

마스킹 표기: org 서브도메인·이메일은 이미지에서 검은 박스, 본문에서 `{org}` / `<username>`. 테스트 계정명 동일.

## 3. 앱 쪽 정책이 먼저 있었다

OIDC를 붙이기 전에 `iam.json`의 역할 정의가 먼저다. 실측에 쓴 역할 둘:

```json
{
  "roles": {
    "builder": {
      "actions": ["create_agent", "revise_agent", "run_agent", "view"],
      "tools": ["web_search", "calculate", "file_read", "file_write", "file_list"]
    },
    "viewer": {
      "actions": ["view"],
      "tools": []
    }
  },
  "groups": {
    "agent-builder": "builder",
    "agent-viewer": "viewer"
  }
}
```

`groups`가 이번 글의 연결 고리다 — **IdP의 그룹 클레임 → 앱의 역할** 매핑. 여러 그룹에 속하면 정책 파일 선언 순서로 첫 매칭이 이긴다.

## 4. Okta 쪽 설정 — 걸린 지점 순서대로

### 4.1 OIDC 앱 생성

Applications → Create App Integration → **OIDC - OpenID Connect + Web Application**. 토큰 교환을 서버(Streamlit)가 하므로 SPA가 아니라 Web Application이다.

![Create app integration — OIDC, Web Application 선택](/assets/images/26-09-29/okta-agent/01-create-oidc-app.png)

Sign-in redirect URI에 `http://localhost:8501/oauth2callback`을 등록한다. Streamlit `st.login`의 콜백 경로는 고정이다.

### 4.2 그룹 생성 — 이름이 정책 파일과 정확히 일치해야 한다

Directory → Groups에서 역할별 그룹을 만든다. `agent-builder`, 그리고 테스트 계정을 넣을 `agent-viewer`.

![Add group — agent-builder](/assets/images/26-09-29/okta-agent/02-add-group-agent-builder.png)

![Add group — agent-viewer (테스트 계정용)](/assets/images/26-09-29/okta-agent/03-add-group-agent-viewer.png)

여기서 만든 그룹 이름은 `iam.json`의 `groups` 키에 **그대로 복사**한다. deny-by-default라서 오타·불일치는 에러가 아니라 **로그인 성공 후 매핑 없음 → 거부**로 나타난다. 조용히 기본 역할로 받아주는 순간 RBAC은 장식이 된다.

### 4.3 groups 클레임 — scope에 넣으면 invalid_scope 400

ID 토큰에 그룹을 담는 것이 이 연동의 핵심인데, 여기가 가장 헷갈렸다.

- 클라이언트 scope에 `groups`를 추가하면 **`invalid_scope` 400**이 났다 — default 인가 서버에 `groups`라는 커스텀 스코프가 없기 때문이다
- Security → API → default 서버의 Scopes 탭에서 커스텀 스코프를 직접 추가하는 경로가 있다 (아래 캡처)
- 하지만 스코프를 만들지 않아도 된다 — **Claims 탭에서 groups 클레임을 ID Token / Always(Any scope)로 추가**하면 `openid profile email` 3개 스코프만으로 ID 토큰에 groups가 담긴다. 필터는 정규식 `agent-.*`로 걸어 이 앱과 무관한 그룹은 토큰에 싣지 않았다

![default 인가 서버에 커스텀 스코프를 추가하는 화면 — 결과적으로 이 경로 대신 Always 클레임을 썼다](/assets/images/26-09-29/okta-agent/04-add-scope-group.png)

메타데이터 URL도 주의할 것 — org 도메인 뒤에 커스텀 인가 서버 경로가 붙어야 groups 클레임이 나온다:

```toml
server_metadata_url = "https://{org}.okta.com/oauth2/default/.well-known/openid-configuration"
```

`-admin`이 붙은 관리자 콘솔 도메인이 아니라 org 도메인이다.

### 4.4 Access Policy + Rule — 없으면 no_matching_policy

커스텀 인가 서버(default 포함)는 **Access Policy와 Rule이 최소 1개** 있어야 토큰을 발급한다. 없으면 Okta 로그인과 MFA까지 전부 통과하고도 마지막에 `no_matching_policy`로 토큰 발급이 거부됐다 (실측).

정책은 이 앱(클라이언트)에만 할당했다:

![Add Policy — deep-builder-agent 클라이언트에만 할당](/assets/images/26-09-29/okta-agent/05-add-access-policy.png)

규칙은 Authorization Code 그랜트, 앱에 할당된 사용자, 토큰 수명 기본값으로 만들었다:

![Add Rule — 그랜트 타입·대상 사용자·토큰 수명](/assets/images/26-09-29/okta-agent/06-add-policy-rule.png)

### 4.5 Assignments — 미할당은 로그인 자체가 access_denied

앱 Assignments에 그룹을 할당한다. 할당되지 않은 그룹의 계정은 Okta 로그인 단계에서 `access_denied`로 차단된다. 완전 차단이 목적이면 이것이 1차 방어선이고, 앱 쪽 `iam.json` 매핑은 그 다음 층이다.

## 5. 앱 쪽 연동 — 로그인 성공 ≠ 인가

Streamlit 쪽은 `.streamlit/secrets.toml`의 `[auth]`가 전부다:

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "{masked}"
client_id = "{masked}"
client_secret = "{masked}"
server_metadata_url = "https://{org}.okta.com/oauth2/default/.well-known/openid-configuration"
client_kwargs = { scope = "openid profile email" }   # groups를 넣지 않는다 — 4.3 참고
```

이 파일이 없으면 앱은 데모 모드(사이드바에서 주체 선택)로 뜨고, 있으면 로그인 없이는 아무 화면도 그리지 않는다.

로그인 후가 중요하다. ID 토큰의 이메일·그룹을 주체로 해석하는 우선순위:

1. `principals`의 **이메일 직접 매핑** (개인 예외 — 그룹보다 구체적이므로 우선)
2. `groups` 매핑 — 정책 파일 선언 순서로 첫 매칭
3. 매핑 없음 → **거부**. IdP가 신원을 보증해도 이 시스템에서의 역할은 정책이 명시해야 한다

주체 이름은 이메일이다. 감사 로그가 "선택한 이름"이 아니라 **검증된 신원**을 가리키게 된다. 실제 기록 한 줄 (마스킹):

```json
{"timestamp": "2026-09-28T04:56:51+00:00", "principal": "<username>@{masked}",
 "role": "builder", "action": "run_agent", "decision": "allow",
 "resource": "data_analysis_team"}
```

거부도 같은 파일에 남는다 — 매핑 없는 계정의 `resolve_identity` deny에는 그 계정이 가진 그룹 목록과 정책에 선언된 그룹 목록이 함께 기록되어, "왜 거부됐는지"를 로그만으로 추적할 수 있다.

## 6. 화면 실측

builder 그룹 계정으로 로그인하면 사이드바에 역할·허용 행위·도구 경계가 뜬다. 전부 IdP 그룹에서 온 것이고 화면에서 바꿀 수 없다:

![builder 계정 로그인 후 — 사이드바에 역할·행위·도구 경계 표시](/assets/images/26-09-29/okta-agent/07-builder-ui-oidc.gif)

`agent-viewer` 그룹의 테스트 계정으로 로그인하면 생성이 잠기고 이유가 표시된다. 버튼을 숨기는 게 아니라 **왜 안 되는지**를 보여준다:

![viewer 계정 — 에이전트 생성이 역할 사유와 함께 잠김](/assets/images/26-09-29/okta-agent/08-viewer-locked.jpg)

builder 계정은 평가 탭(빌더 회귀 검사 27케이스)까지 접근된다:

![builder 계정 — 평가 탭 접근 가능](/assets/images/26-09-29/okta-agent/09-eval-tab-27cases.jpg)

## 7. 걸린 지점 정리

| 증상 | 원인 | 해결 |
|---|---|---|
| `invalid_scope` 400 | scope에 `groups` 요청 — default 서버에 해당 커스텀 스코프 없음 | scope는 `openid profile email`만, groups는 클레임을 Always로 |
| `no_matching_policy` (MFA 통과 후) | 커스텀 인가 서버에 Access Policy/Rule 없음 | 정책+규칙 최소 1개 생성, 이 클라이언트에 할당 |
| 로그인 성공 후 IAM 거부 | Okta 그룹 이름 ≠ `iam.json` groups 키 | 그룹 이름을 정책 파일에 그대로 복사 (deny-by-default) |
| 로그인 자체가 `access_denied` | 계정의 그룹이 앱 Assignments에 미할당 | 그룹을 앱에 할당 — 이것이 1차 방어선 |
| groups 클레임이 토큰에 없음 | org 도메인 루트 메타데이터 사용 | `server_metadata_url`에 `/oauth2/default` 경로 포함 |

## 8. 정리

- 인증과 인가는 붙어 있지 않다. Okta가 4단계(Assignments → 로그인 → 정책 → 토큰)를 전부 통과시켜도, 앱의 정책 파일에 매핑이 없으면 그 계정은 아무것도 못 한다 — 그리고 그 거부가 감사 로그에 남는다
- 지금까지 SCIM 실습에서 "Okta가 앱의 계정 저장소를 관리"하는 층을 봤다면, 이번 것은 "Okta가 보증한 신원을 앱이 어디까지 믿을 것인가"의 층이다. 그룹 클레임은 편리하지만, 역할 결정권을 IdP에 전부 넘기는 순간 앱 쪽 최소 권한 설계가 사라진다 — 매핑을 앱 정책 파일에 남겨둔 이유다
- 권한 경계는 OIDC와 독립적으로 작동한다. builder가 로그인해서 에이전트를 만들어도, 스펙이 builder의 도구 화이트리스트를 초과하면 생성 자체가 거부된다
