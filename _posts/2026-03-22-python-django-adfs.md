---
layout: single
title: "[Python Django] ADFS OAuth 2.0 연동 가이드 (feat. 순수 OAuth 2.0)"
date: 2026-03-22
categories: [Python, Django]
excerpt: "ADFS OAuth 2.0 인증 흐름, ADFS Application Group 등록, OAuth 2.0 핵심 로직 구현, Access Token Claims 확인 방법, HTTPS 설정, 트러블슈팅까지 한 번에 정리한 실전 가이드"
tags: [Python, Django, ADFS, OAuth2, OpenIDConnect, SSO, 인증]
---


# Python Django + ADFS OAuth 2.0 연동 가이드

> **환경**: Windows 10/11 | Python 3.11 | Django 4.2.13 | HTTPS (포트 44367)  
> **인증 방식**: 순수 OAuth 2.0 Authorization Code Flow (openid scope 미사용)  
> **ADFS 등록 방식**: Native Application (Client Secret 없음)

---

## 목차

1. [OAuth 2.0 vs OIDC 개념 정리](#1-oauth-20-vs-oidc-개념-정리)
2. [프로젝트 구조](#2-프로젝트-구조)
3. [환경 설정](#3-환경-설정)
4. [ADFS Application Group 등록](#4-adfs-application-group-등록)
5. [.env 파일 설정](#5-env-파일-설정)
6. [settings.py 설정](#6-settingspy-설정)
7. [OAuth 2.0 핵심 로직 구현](#7-oauth-20-핵심-로직-구현)
8. [URL / 뷰 / 템플릿 설정](#8-url--뷰--템플릿-설정)
9. [Access Token Claims 확인 방법](#9-access-token-claims-확인-방법)
10. [HTTPS 설정](#10-https-설정)
11. [트러블슈팅](#11-트러블슈팅)

---

## 1. OAuth 2.0 vs OIDC 개념 정리

### OAuth 2.0 과 OIDC 의 관계

먼저 두 개념부터 짚고 넘어가는 게 좋음.

```
OAuth 2.0
    └── OIDC (OpenID Connect)
         = OAuth 2.0 을 기반으로 확장한 인증 레이어
```

OIDC 는 OAuth 2.0 을 대체하는 게 아니라 **그 위에 얹은 것**임.  
쉽게 말하면 OIDC 는 OAuth 2.0 의 일종이라고 보면 됨.

### scope=openid 의 의미

`scope=openid` 하나 차이로 동작 방식이 완전히 달라짐.

| 구분 | scope | 발급 토큰 | 용도 |
|---|---|---|---|
| 순수 OAuth 2.0 | openid 없음 | Access Token | 권한 부여 |
| OIDC | openid 포함 | Access Token + **ID Token** | 권한 부여 + 신원 확인 |

비유하자면 이런 느낌임.

```
OAuth 2.0  =  출입증 발급
              (이 사람이 건물에 들어갈 수 있는가?)

OIDC       =  출입증 + 신분증 발급
              (이 사람이 누구인가? + 건물에 들어갈 수 있는가?)
```

> 이 가이드는 **순수 OAuth 2.0 방식**을 사용함.  
> ADFS Application Permissions 에서 **openid 체크 해제** 필수!

### OAuth 2.0 인증 흐름

전체 흐름은 아래와 같음.

```
① 로그인 버튼 클릭          → /oauth2/login/
② ADFS 로그인 페이지        → 사내 AD 계정 입력
③ Authorization Code 발급  → /oauth2/callback/
④ Code → Access Token 교환
⑤ Access Token (JWT) 디코딩 → Claims 추출
⑥ Django User 생성/업데이트 → 로그인
⑦ /profile/ 이동
```

---

## 2. 프로젝트 구조

샘플코드 압축 해제 후 아래 구조로 구성됨.

```
D:\Project\django_adfs_oauth2\
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── Oauth_sample\
│   ├── settings.py      ← ADFS_CONFIG 설정
│   ├── urls.py          ← oauth2/ URL 포함
│   └── wsgi.py
└── accounts\
    ├── oauth_views.py   ← OAuth 2.0 핵심 로직
    ├── oauth_urls.py    ← OAuth 2.0 URL 설정
    ├── views.py         ← 페이지 뷰
    ├── urls.py          ← 페이지 URL
    └── templates\accounts\
        ├── base.html
        ├── home.html
        ├── profile.html
        └── error.html   ← 인증 오류 페이지
```

기존 OIDC 방식과 달리 `django-auth-adfs` 라이브러리를 사용하지 않고 `oauth_views.py` 에서 직접 구현했음.

---

## 3. 환경 설정

### Python 버전 주의사항

Python 버전에 따라 HTTPS 설정 방법이 달라짐.

| Python 버전 | django-sslserver | 비고 |
|---|---|---|
| **3.11 (권장)** | ✅ 정상 동작 | 이 가이드 기준 |
| 3.12 이상 | ❌ ssl.wrap_socket 오류 | mkcert 방식 사용 필요 |

Python 3.12 이상에서는 `ssl.wrap_socket` 이 제거됐기 때문에 django-sslserver 가 동작하지 않음.  
이 경우 mkcert 를 사용해야 함.

### Python 3.12 이상 사용 시 — mkcert 자체검증

```bash
# https://github.com/FiloSottile/mkcert/releases 에서 다운로드
# mkcert-v1.x.x-windows-amd64.exe → mkcert.exe 로 이름 변경 후 프로젝트 폴더에 복사

# 로컬 CA 설치 (최초 1회만)
mkcert -install

# 인증서 생성
mkcert localhost 127.0.0.1

# 서버 실행
python manage.py runserver_plus --cert-file localhost+1.pem --key-file localhost+1-key.pem 44367
```

### 가상환경 생성

Python 3.11 기준으로 가상환경을 생성함.  
다른 버전과 충돌 방지를 위해 반드시 버전 지정해서 생성하는 게 좋음.

```bash
# Python 3.11 로 가상환경 생성
py -3.11 -m venv venv

# 활성화
venv\Scripts\activate

# 버전 확인 (3.11.x 가 출력되어야 정상)
python --version
```

### requirements.txt

OIDC 방식과 달리 `django-auth-adfs` 대신 `requests`, `PyJWT` 를 사용함.

```
Django==4.2.13
requests==2.32.3
PyJWT==2.8.0
cryptography==42.0.5
python-dotenv==1.0.1
django-sslserver==0.22
```

```bash
pip install -r requirements.txt
```

### SECRET_KEY 생성

ZIP 파일을 사용하는 경우 settings.py 가 자동 생성되지 않기 때문에 SECRET_KEY 를 직접 생성해야 함.

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

생성된 값을 .env 파일의 `SECRET_KEY` 에 붙여넣으면 됨.

> ⚠️ 생성된 값에 `#` 이 포함된 경우 .env 에서 따옴표로 감싸야 함.  
> `SECRET_KEY="django-insecure-abc#def..."`  
> `#` 이후가 주석으로 인식돼서 잘리기 때문임.

---

## 4. ADFS Application Group 등록

ADFS 서버에서 진행하는 단계임. 직접 권한이 없으면 IT 인프라팀에 요청하면 됨.

### 4-1. Application Group 생성

```
AD FS Management
→ Application Groups
→ "Add Application Group..." 클릭
→ 이름: Django_ADFS_OAuth2
→ "Native application accessing a web API" 선택
→ Next
```

### 4-2. Native Application 설정

| 항목 | 설정값 |
|---|---|
| Client Identifier | 자동 생성 GUID → 반드시 복사 보관 (.env 의 ADFS_CLIENT_ID) |
| Redirect URI | `https://localhost:44367/oauth2/callback/` |

Native Application 은 **Client Secret 이 발급되지 않음**.  
Secret 을 별도로 요청하거나 생성할 필요 없음.

### 4-3. Web API 설정

| 항목 | 설정값 |
|---|---|
| Relying Party Identifiers | `https://localhost:44367` |
| Access Control Policy | Permit everyone (테스트용) |
| Application Permissions | profile, email (**openid 반드시 체크 해제**) |

여기서 **openid 체크 해제가 핵심**임.  
openid 가 체크되어 있으면 OIDC 방식으로 동작해서 이 가이드의 OAuth 2.0 구현과 충돌하게 됨.

### 4-4. ADFS 등록 항목 → .env 매핑표

헷갈리기 쉬운 부분이라 정리해둠.

| ADFS 등록 화면 | 입력란 | .env 항목 |
|---|---|---|
| Native Application | Client Identifier (자동 발급) | ADFS_CLIENT_ID |
| Native Application | Redirect URI (직접 입력) | ADFS_REDIRECT_URI |
| Web API | Relying Party Identifiers (직접 입력) | ADFS_RESOURCE |

`ADFS_RESOURCE` 와 `ADFS_REDIRECT_URI` 는 역할이 다름.

```
ADFS_RESOURCE     → OAuth 2.0 인증 요청 시 resource 파라미터로 전송
                    "이 토큰은 어떤 서비스용인지" ADFS 에 알려주는 역할

ADFS_REDIRECT_URI → 인증 완료 후 ADFS 가 code 를 전달하는 주소
                    "인증 끝나면 여기로 돌아와라" 는 역할
```

두 값이 다를 수 있고 각각 ADFS 에 등록한 값과 정확히 일치해야 함.  
슬래시(/) 하나 차이로도 인증 실패하니 주의할 것.

---

## 5. .env 파일 설정

민감한 정보를 코드에 하드코딩하지 않고 .env 파일에 분리 관리하는 방식을 사용함.  
`python-dotenv` 가 서버 시작 시 자동으로 읽어들임.

```bash
# .env.example 을 .env 로 복사
copy .env.example .env
```

```bash
# .env 파일 내용
# ================================================================
# .env — Git 에 절대 올리지 마세요
# ================================================================

# Django 기본 설정
# 위에서 생성한 SECRET_KEY 값 붙여넣기
# # 포함 시 따옴표로 감싸기
SECRET_KEY="django-insecure-xxxxxxxxxx"
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# ADFS 서버 도메인 (https:// 제외)
# ADFS 담당자에게 문의
ADFS_SERVER=adfs.company.com

# Application Group 등록 시 자동 발급되는 GUID
ADFS_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Native Application Redirect URI 에 직접 입력한 값
ADFS_REDIRECT_URI=https://localhost:44367/oauth2/callback/

# Web API Relying Party Identifiers 에 직접 입력한 값
# OAuth 2.0 인증 요청 시 resource 파라미터로 전송됨
ADFS_RESOURCE=https://localhost:44367

# Django User.username 에 매핑할 AD 클레임
# winaccountname = sAMAccountName (사번/영문ID)
ADFS_USERNAME_CLAIM=winaccountname

# SSL 검증 (테스트: False / 운영: /path/to/ca-bundle.crt)
ADFS_CA_BUNDLE=False

# ※ Native Application → Client Secret 없음
```

### .env 항목별 값 출처

| .env 항목 | 값 출처 |
|---|---|
| SECRET_KEY | python 명령으로 직접 생성한 값 |
| ADFS_SERVER | ADFS 담당자에게 문의 |
| ADFS_CLIENT_ID | Application Group 등록 시 자동 발급 GUID |
| ADFS_REDIRECT_URI | Native Application Redirect URI 에 직접 입력한 값 |
| ADFS_RESOURCE | Web API Relying Party Identifiers 에 직접 입력한 값 |

---

## 6. settings.py 설정

기존 OIDC 방식의 `AUTH_ADFS` 대신 `ADFS_CONFIG` 를 사용함.  
`django-auth-adfs` 라이브러리를 쓰지 않기 때문에 직접 설정 딕셔너리를 정의한 것임.

```python
"""
Oauth_sample/settings.py
순수 OAuth 2.0 방식 (openid scope 미사용)
"""
import os
from pathlib import Path

# python-dotenv 로 .env 파일 자동 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass   # dotenv 없어도 환경변수가 직접 설정되어 있으면 동작

BASE_DIR = Path(__file__).resolve().parent.parent

# ── 보안 설정 ─────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ── 앱 목록 ───────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',       # 우리가 만든 앱
    'sslserver',      # HTTPS 로컬 개발 서버
    # django_auth_adfs 없음 — 순수 OAuth 2.0 직접 구현
]

# ── 로그인/로그아웃 URL ───────────────────────────────────
LOGIN_URL = '/oauth2/login/'         # 로그인 필요 시 이동할 URL
LOGIN_REDIRECT_URL = '/profile/'     # 로그인 성공 후 이동할 URL
LOGOUT_REDIRECT_URL = '/'            # 로그아웃 후 이동할 URL

# ── ADFS OAuth 2.0 설정 ───────────────────────────────────
# .env 의 'False' 문자열을 Python False 로 변환
ca_raw    = os.environ.get('ADFS_CA_BUNDLE', 'False')
ca_bundle = False if ca_raw.lower() == 'false' else ca_raw

ADFS_CONFIG = {
    # ADFS 서버 도메인 (https:// 제외)
    # 출처: ADFS 담당자에게 문의
    'SERVER': os.environ.get('ADFS_SERVER'),

    # Application Group 등록 시 자동 발급 GUID
    # 출처: .env → ADFS_CLIENT_ID
    'CLIENT_ID': os.environ.get('ADFS_CLIENT_ID'),

    # ※ Native Application → Client Secret 없음

    # Native Application Redirect URI 에 직접 입력한 값
    # 출처: .env → ADFS_REDIRECT_URI
    'REDIRECT_URI': os.environ.get('ADFS_REDIRECT_URI'),

    # Web API Relying Party Identifiers 에 직접 입력한 값
    # OAuth 2.0 인증 요청 시 resource 파라미터로 전송됨
    # 출처: .env → ADFS_RESOURCE
    'RESOURCE': os.environ.get('ADFS_RESOURCE'),

    # Django User.username 에 매핑할 AD 클레임
    # winaccountname = sAMAccountName (사번/영문ID)
    # 출처: .env → ADFS_USERNAME_CLAIM
    'USERNAME_CLAIM': os.environ.get('ADFS_USERNAME_CLAIM', 'winaccountname'),

    # Access Token Claims → Django User 필드 매핑
    # 왼쪽: Django User 모델 필드명 (고정)
    # 오른쪽: ADFS 에서 발급되는 Claim 이름
    'CLAIM_MAPPING': {
        'first_name': 'given_name',    # AD 이름  → User.first_name
        'last_name':  'family_name',   # AD 성    → User.last_name
        'email':      'email',         # AD 이메일 → User.email
    },

    # SSL 인증서 검증
    # False: 검증 안 함 (사내 사설 인증서 환경, 테스트용)
    # 출처: .env → ADFS_CA_BUNDLE
    'CA_BUNDLE': ca_bundle,
}

# HTTPS 사용 시 CSRF 신뢰 도메인 등록 필수
CSRF_TRUSTED_ORIGINS = ['https://localhost:44367']
```

---

## 7. OAuth 2.0 핵심 로직 구현

이 가이드의 핵심 부분임.  
`django-auth-adfs` 없이 OAuth 2.0 흐름을 직접 구현했음.

### accounts/oauth_urls.py

```python
from django.urls import path
from . import oauth_views

urlpatterns = [
    path('login/',    oauth_views.oauth_login,    name='oauth_login'),
    path('callback/', oauth_views.oauth_callback, name='oauth_callback'),
    path('logout/',   oauth_views.oauth_logout,   name='oauth_logout'),
]
```

### accounts/oauth_views.py

```python
"""
순수 OAuth 2.0 Authorization Code Flow 구현
openid scope 미사용 — Access Token 기반으로 사용자 정보 파싱
"""
import secrets
import logging
import requests
import jwt

from urllib.parse import urlencode
from django.shortcuts import redirect, render
from django.contrib.auth import login, logout, get_user_model
from django.conf import settings

logger = logging.getLogger(__name__)
ADFS = settings.ADFS_CONFIG


def get_adfs_urls():
    """ADFS 엔드포인트 URL 반환"""
    server = ADFS['SERVER']
    return {
        'authorize': f"https://{server}/adfs/oauth2/authorize",
        'token':     f"https://{server}/adfs/oauth2/token",
    }


def oauth_login(request):
    """
    ADFS 로그인 시작
    - state 생성 후 세션 저장 (CSRF 방지용)
    - resource 파라미터로 ADFS_RESOURCE 전송 (OAuth 2.0 핵심)
    """
    # CSRF 방지용 랜덤 state 생성
    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state

    # 로그인 전 접근했던 URL 저장 (로그인 후 복귀용)
    next_url = request.GET.get('next', settings.LOGIN_REDIRECT_URL)
    request.session['oauth_next'] = next_url

    # Authorization URL 파라미터 구성
    params = {
        'response_type': 'code',
        'client_id':     ADFS['CLIENT_ID'],
        'redirect_uri':  ADFS['REDIRECT_URI'],
        'resource':      ADFS['RESOURCE'],   # OAuth 2.0 핵심 파라미터
        'state':         state,
    }

    urls = get_adfs_urls()
    auth_url = f"{urls['authorize']}?{urlencode(params)}"
    return redirect(auth_url)


def oauth_callback(request):
    """
    ADFS 인증 콜백 처리
    - state 검증 → code 추출 → Access Token 교환
    - Access Token (JWT) 디코딩 → Claims 추출
    - Django User 생성/업데이트 → 로그인
    """
    # 오류 응답 처리
    error = request.GET.get('error')
    if error:
        error_desc = request.GET.get('error_description', '알 수 없는 오류')
        return render(request, 'accounts/error.html', {
            'error': error,
            'error_description': error_desc,
        })

    # state 검증 (CSRF 방지)
    received_state = request.GET.get('state')
    saved_state    = request.session.pop('oauth_state', None)
    if not received_state or received_state != saved_state:
        return render(request, 'accounts/error.html', {
            'error': 'state_mismatch',
            'error_description': '보안 검증에 실패했습니다. 다시 로그인해 주세요.',
        })

    # Authorization Code 추출
    code = request.GET.get('code')
    if not code:
        return render(request, 'accounts/error.html', {
            'error': 'no_code',
            'error_description': 'Authorization Code 가 없습니다.',
        })

    # Code → Access Token 교환
    urls = get_adfs_urls()
    token_data = {
        'grant_type':   'authorization_code',
        'code':         code,
        'redirect_uri': ADFS['REDIRECT_URI'],
        'client_id':    ADFS['CLIENT_ID'],
        'resource':     ADFS['RESOURCE'],
    }

    try:
        token_response = requests.post(
            urls['token'],
            data=token_data,
            verify=ADFS['CA_BUNDLE'],
            timeout=10,
        )
        token_response.raise_for_status()
        token_json = token_response.json()
    except requests.exceptions.RequestException as e:
        return render(request, 'accounts/error.html', {
            'error': 'token_request_failed',
            'error_description': f"ADFS 서버와 통신 중 오류: {str(e)}",
        })

    access_token = token_json.get('access_token')
    if not access_token:
        return render(request, 'accounts/error.html', {
            'error': 'no_access_token',
            'error_description': 'Access Token 을 받지 못했습니다.',
        })

    # Access Token (JWT) 디코딩 → Claims 추출
    try:
        claims = jwt.decode(
            access_token,
            options={"verify_signature": False},
            algorithms=["RS256"],
        )
        # 세션에 Claims 저장 (프로필 페이지에서 확인용)
        # 운영 배포 전 제거 필요
        request.session['access_token_claims'] = claims
    except jwt.DecodeError as e:
        return render(request, 'accounts/error.html', {
            'error': 'token_decode_failed',
            'error_description': 'Access Token 파싱에 실패했습니다.',
        })

    # Django User 생성 또는 업데이트
    username_claim = ADFS['USERNAME_CLAIM']
    username = claims.get(username_claim) or claims.get('sub')
    if not username:
        return render(request, 'accounts/error.html', {
            'error': 'no_username',
            'error_description': f"'{username_claim}' 클레임이 없습니다.",
        })

    User = get_user_model()
    user, created = User.objects.get_or_create(username=username)

    # CLAIM_MAPPING 에 따라 User 필드 업데이트
    for field, claim_name in ADFS.get('CLAIM_MAPPING', {}).items():
        setattr(user, field, claims.get(claim_name, ''))
    user.save()

    # 로그인 처리
    # login() 먼저 호출 후 세션 저장해야 함 (순서 중요!)
    # login() 내부에서 세션을 새로 생성하기 때문에
    # 먼저 저장하면 Claims 데이터가 사라짐
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    # login() 호출 후 세션 저장
    request.session['access_token_claims'] = claims
    request.session.modified = True

    next_url = request.session.pop('oauth_next', settings.LOGIN_REDIRECT_URL)
    return redirect(next_url)


def oauth_logout(request):
    """로그아웃 — 세션 삭제 후 홈으로 이동"""
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)
```

---

## 8. URL / 뷰 / 템플릿 설정

### Oauth_sample/urls.py

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # OAuth 2.0 인증 URL
    # /oauth2/login/     → ADFS 로그인 시작
    # /oauth2/callback/  → 인증 완료 콜백
    # /oauth2/logout/    → 로그아웃
    path('oauth2/', include('accounts.oauth_urls')),
    path('', include('accounts.urls')),
]
```

### accounts/urls.py

```python
from django.urls import path
from . import views

urlpatterns = [
    path('',         views.home,    name='home'),
    path('profile/', views.profile, name='profile'),
]
```

### accounts/views.py

```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


def home(request):
    """홈 페이지 — 누구나 접근 가능"""
    return render(request, 'accounts/home.html')


@login_required
# @login_required 데코레이터 하나로
# 미로그인 시 LOGIN_URL(/oauth2/login/) 로 자동 리다이렉트됨
def profile(request):
    """프로필 페이지 — 로그인 사용자만 접근 가능"""
    user = request.user
    user_groups = list(user.groups.values_list('name', flat=True))

    # 세션에서 Access Token Claims 꺼내기
    # ADFS 마이그레이션 Claim 확인용 (운영 배포 전 제거)
    access_token_claims = request.session.get('access_token_claims', {})

    context = {
        'user': user,
        'user_groups': user_groups,
        'access_token_claims': access_token_claims,
    }
    return render(request, 'accounts/profile.html', context)
```

---

## 9. Access Token Claims 확인 방법

ADFS 에서 어떤 Claim 이 발급되는지 확인하는 게 중요함.  
특히 사내에서 AD 속성을 마이그레이션해서 쓰는 경우 Claim 이름을 정확히 알아야 `CLAIM_MAPPING` 에 반영할 수 있음.

### profile.html — Claims 표시

{% raw %}

```html
<div class="card">
    <h2>ADFS Claim 정보</h2>
    <table>
        {% for key, value in access_token_claims.items %}
        <tr>
            <th>{{ key }}</th>
            <td>{{ value }}</td>
        </tr>
        {% empty %}
        <tr>
            <td colspan="2">Claims 정보가 없습니다.</td>
        </tr>
        {% endfor %}
    </table>
</div>
```

{% endraw %}

로그인 후 프로필 페이지에서 아래처럼 확인할 수 있음.

```
ADFS Claim 정보
─────────────────────────────────
CUSTOM_CLAIM1   │ value1
CUSTOM_CLAIM2   │ value2
given_name      │ 길동
family_name     │ 홍
email           │ hong@company.com
winaccountname  │ honggildong
```

### CLAIM_MAPPING 에 반영

마이그레이션된 Claim 은 Django User 필드에 매핑하는 게 아니라 세션에서 직접 꺼내서 사용하면 됨.  
`CLAIM_MAPPING` 왼쪽은 Django 기본 User 모델 필드만 사용 가능하기 때문임.

```python
# settings.py → ADFS_CONFIG
'CLAIM_MAPPING': {
    'first_name': 'given_name',    # ✅ Django User 필드
    'last_name':  'family_name',   # ✅ Django User 필드
    'email':      'email',         # ✅ Django User 필드
    # 커스텀 Claim 은 User 모델 필드가 아니므로 직접 매핑 불가
}

# 마이그레이션된 Claim 은 세션에서 직접 꺼내 사용
claims = request.session.get('access_token_claims', {})
custom_claim = claims.get('커스텀_CLAIM_이름', '')
```

> ⚠️ **운영 배포 전 반드시 제거할 것**  
> Claims 에는 민감한 사용자 정보가 포함됨.  
> Claim 목록 확인 완료 후 아래 코드 삭제:
> - `oauth_views.py`: `request.session['access_token_claims'] = claims`
> - `views.py`: `access_token_claims` 관련 코드
> - `profile.html`: Claims 카드 블록 전체

---

## 10. HTTPS 설정

### 서버 실행

```bash
python manage.py runsslserver 0.0.0.0:44367
```

### "안전하지 않음" 경고 해결 방법

django-sslserver 가 자체 서명 인증서를 사용하기 때문에 브라우저에서 경고가 뜸.  
사내 배포용이라면 사용자 문의가 들어올 수 있어서 해결하는 게 좋음.

#### 방법 ① 사내 CA 인증서 사용 (권장)

사내에 이미 루트 CA 인증서(`BW-ROOTCA` 등)가 배포되어 있다면 해당 CA 로 서명된 인증서를 발급받으면 됨.  
`certmgr.msc` → **신뢰할 수 있는 루트 인증 기관** → 인증서 에서 사내 CA 인증서가 있는지 확인.

```
IT 인프라팀에 요청:
BW-ROOTCA 로 서명된 localhost 인증서 발급

필요한 파일:
- 인증서: bw-localhost.pem
- 개인키: bw-localhost-key.pem
```

```bash
# 발급받은 인증서로 서버 실행
python manage.py runsslserver --certificate bw-localhost.pem --key bw-localhost-key.pem 0.0.0.0:44367
```

사내 CA 인증서는 이미 사내 PC 에 신뢰된 상태라서 별도 설치 없이 경고 없이 접속됨.

#### 방법 ② mkcert 사용

```bash
# mkcert 다운로드 후 프로젝트 폴더에 복사
mkcert -install        # 로컬 CA 설치 (최초 1회)
mkcert localhost 127.0.0.1   # 인증서 생성

# 서버 실행
python manage.py runsslserver --certificate localhost+1.pem --key localhost+1-key.pem 0.0.0.0:44367
```

사내 전체 배포 시 IT 인프라팀에 GPO 로 rootCA 를 전체 PC 에 일괄 배포 요청하면 됨.

---

## 11. 트러블슈팅

개발 과정에서 겪었던 오류들을 정리함.

---

### ① ssl.wrap_socket 오류

```
AttributeError: module 'ssl' has no attribute 'wrap_socket'
```

Python 3.12 이상에서 `ssl.wrap_socket` 이 제거됐기 때문에 발생함.  
Python 3.11 로 다운그레이드해서 해결됨.

```bash
rmdir /s /q venv
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

### ② SECRET_KEY is empty

```
ImproperlyConfigured: The SECRET_KEY setting must not be empty.
```

.env 파일의 SECRET_KEY 가 비어있거나 .env 파일 위치가 잘못된 경우임.

```bash
# SECRET_KEY 새로 생성
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# .env 파일 위치 확인 (manage.py 와 같은 폴더에 있어야 함)
D:\Project\django_adfs_oauth2\
├── manage.py
└── .env   ← 여기!
```

---

### ③ SECRET_KEY 의 # 이 주석으로 인식됨

.env 파일에서 `#` 은 주석으로 처리됨.  
SECRET_KEY 에 `#` 이 포함된 경우 그 이후 값이 잘려서 문제가 생김.

```bash
# 잘못된 경우
SECRET_KEY=django-insecure-abc#def...
# → #def... 부분이 주석으로 인식돼서 잘림

# 올바른 방법
SECRET_KEY="django-insecure-abc#def..."
```

---

### ④ invalid_resource (MSIS9602)

```
error=invalid_resource&error_description=MSIS9602...
```

`ADFS_RESOURCE` 값과 ADFS Web API Relying Party Identifiers 가 불일치할 때 발생함.

```
# ADFS Web API Identifiers 에 등록한 값
https://localhost:44367

# .env 의 ADFS_RESOURCE 값
https://localhost:44367/oauth2/callback/   ← 다름!
```

Web API Identifiers 에 등록한 값을 그대로 `ADFS_RESOURCE` 에 넣으면 해결됨.

---

### ⑤ redirect_uri_mismatch

```
MSIS9615: The parameter redirect_uri does not match...
```

`ADFS_REDIRECT_URI` 와 ADFS Native Application Redirect URI 가 불일치할 때 발생함.  
슬래시(/) 하나, http/https 차이도 원인이 될 수 있음.

---

### ⑥ manage.py already exists

```
CommandError: manage.py already exists.
```

ZIP 파일에 이미 완성된 프로젝트가 들어있는데 `django-admin startproject` 를 재실행한 경우임.  
ZIP 사용 시 프로젝트 생성 명령은 실행하지 않아도 됨.

---

### ⑦ accounts conflicts with existing module

```
CommandError: 'accounts' conflicts with the name of an existing Python module
```

`manage.py` 가 없는 폴더에서 앱 생성 명령을 실행한 경우임.

```bash
# manage.py 가 있는 폴더에서 실행해야 함
cd D:\Project\django_adfs_oauth2
python manage.py startapp accounts
```

---

### ⑧ CSRF verification failed

```
CSRF verification failed. Request aborted.
```

`settings.py` 에 `CSRF_TRUSTED_ORIGINS` 가 없을 때 발생함.

```python
CSRF_TRUSTED_ORIGINS = ['https://localhost:44367']
```

---

### ⑨ Access Token Claims 가 프로필에 안 뜸

Claims 화면에 "Claims 정보가 없습니다" 가 표시되는 경우임.

**원인**: `login()` 호출 전에 세션 저장을 했기 때문임.  
Django 의 `login()` 함수는 내부적으로 세션을 새로 생성함 (Session Fixation 공격 방지).  
그래서 `login()` 전에 저장한 데이터가 사라지게 됨.

```python
# ❌ 잘못된 순서
request.session['access_token_claims'] = claims   # 먼저 저장
login(request, user, backend='...')               # 세션 초기화됨!

# ✅ 올바른 순서
login(request, user, backend='...')               # 먼저 호출
request.session['access_token_claims'] = claims   # 그 다음 저장
request.session.modified = True
```

---

### ⑩ Import "dotenv" could not be resolved (노란줄)

VS Code 가 가상환경을 인식하지 못해서 발생하는 경고임.  
실제 서버 실행에는 영향 없음.

```
Ctrl + Shift + P
→ "Python: Select Interpreter"
→ venv\Scripts\python.exe 선택
```

---

### ⑪ ca_bundle is not defined

변수명 오타가 원인임.

```python
# 올바른 변수명 확인
ca_raw    = os.environ.get('ADFS_CA_BUNDLE', 'False')
ca_bundle = False if ca_raw.lower() == 'false' else ca_raw

ADFS_CONFIG = {
    ...
    'CA_BUNDLE': ca_bundle,   # 변수명 오타 없는지 확인
}
```

---

### ⑫ CLAIM_MAPPING 에 마이그레이션된 Claim 추가 불가

`CLAIM_MAPPING` 왼쪽은 Django 기본 User 모델 필드만 사용 가능함.  
커스텀 Claim 은 직접 매핑이 안 됨.

```python
# ❌ 안 됨
'CLAIM_MAPPING': {
    'custom_field': 'CUSTOM_CLAIM',   # User 모델에 없는 필드
}

# ✅ 세션에서 직접 꺼내 사용
claims = request.session.get('access_token_claims', {})
custom_value = claims.get('CUSTOM_CLAIM', '')
```

---

## URL 전체 구조

| URL | 설명 | 접근 |
|---|---|---|
| `https://localhost:44367/` | 홈 | 누구나 |
| `https://localhost:44367/profile/` | 프로필 | 로그인 필요 |
| `https://localhost:44367/oauth2/login/` | ADFS 로그인 시작 | 자동 처리 |
| `https://localhost:44367/oauth2/callback/` | ADFS 인증 콜백 | 자동 처리 |
| `https://localhost:44367/oauth2/logout/` | 로그아웃 | 자동 처리 |

---

## 참고 자료

- [Microsoft AD FS OpenID Connect/OAuth 흐름 및 시나리오](https://learn.microsoft.com/ko-kr/windows-server/identity/ad-fs/overview/ad-fs-openid-connect-oauth-flows-scenarios)
- [PyJWT 공식 문서](https://pyjwt.readthedocs.io/)