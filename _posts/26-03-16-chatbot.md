---
layout: single
title: "FastAPI + React 챗봇 Railway & Vercel 배포 완전 가이드 (SmartHee Chatbot)"
date: 2026-03-16
categories: [Dev, Deploy]
tags: [FastAPI, React, TypeScript, Railway, Vercel, Claude API, 배포, 보안]
---

> 아내를 위한 전용 AI 챗봇을 만들었습니다. 네, 세상에서 단 한 명만 쓸 수 있는 챗봇입니다. 그 한 명이 만족하면 그걸로 충분합니다. 배포까지의 트러블슈팅을 공유합니다.

## 📌 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 프로젝트명 | SmartHee Chatbot |
| GitHub | [parkjongmin-ddam/SmartHee_Chatbot](https://github.com/parkjongmin-ddam/SmartHee_Chatbot) |
| 백엔드 | FastAPI + Anthropic Claude API |
| 프론트엔드 | React + TypeScript + Vite |
| 백엔드 배포 | Railway |
| 프론트엔드 배포 | Vercel |
| 접근 제한 | 비밀번호 잠금 화면 + 백엔드 토큰 인증 |

---

## 🗂️ 프로젝트 구조

```
SmartHee_Chatbot/
├── backend/
│   ├── main.py
│   ├── api/
│   │   └── chat.py
│   ├── requirements.txt
│   └── .env.example        ← API 키 형식만, 실제 키는 미포함
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── vite-env.d.ts
│   │   └── components/
│   │       ├── ChatWindow.tsx
│   │       ├── ChatWindow.module.css
│   │       ├── PasswordGate.tsx
│   │       ├── PasswordGate.module.css
│   │       ├── TokenDashboard.tsx
│   │       └── TokenDashboard.module.css
│   ├── vercel.json
│   ├── vite.config.ts
│   └── package.json
└── .gitignore
```

> ⚠️ `.env` 파일은 `.gitignore`에 포함시켜 GitHub에 올리지 않습니다. API 키는 각 플랫폼의 환경변수에서 직접 입력합니다.

---

## 왜 Railway + Vercel 조합인가?

백엔드와 프론트엔드를 굳이 다른 플랫폼에 나눠 배포한 데는 이유가 있습니다.

| 구분 | 플랫폼 | 선택 이유 |
|------|--------|----------|
| 백엔드 (FastAPI) | Railway | Python 서버를 별도 설정 없이 GitHub 연동만으로 배포 가능. 항상 켜져 있어야 하는 서버에 적합 |
| 프론트엔드 (React) | Vercel | React/Vite 프로젝트에 최적화된 빌드 파이프라인 제공. 정적 파일 배포에 특화 |

Vercel에 무료로 정적 파일을 올리고, API 요청만 Railway 백엔드로 프록시하는 구조입니다. 덕분에 프론트엔드 호스팅 비용이 0원이고, 백엔드는 Railway Hobby 플랜($5/월)만으로 운영됩니다.

```
브라우저 → Vercel (프론트엔드, 무료)
              ↓ /api/* 요청
           Railway (백엔드, $5/월)
              ↓
           Claude API
```

> 💡 Vercel의 `rewrites` 설정 덕분에 브라우저 입장에서는 모든 요청이 같은 도메인으로 보입니다. CORS 문제가 없고, 백엔드 URL이 프론트엔드 코드에 직접 노출되지 않습니다.

---

## 1단계: Railway 백엔드 배포

### Railway란?

Railway는 GitHub 레포지토리를 연동해 서버를 자동으로 빌드·배포해주는 클라우드 플랫폼입니다.

| 플랜 | 가격 | 내용 |
|------|------|------|
| Trial | 무료 | $5 크레딧 제공, 소진 시 종료 |
| **Hobby** | **$5/월** | **개인 프로젝트에 적합** |
| Pro | $20/월 | 팀/상업용 |

개인 프로젝트면 **Hobby 플랜**이 충분합니다.

---

### 배포 순서

#### 1. Railway 접속 및 로그인

[railway.app](https://railway.app) → **Login with GitHub**

#### 2. 새 프로젝트 생성

1. **New Project** 클릭
2. **Deploy from GitHub repo** 클릭
3. `SmartHee_Chatbot` 선택

#### 3. Root Directory 설정 (중요!)

모노레포 구조이므로 백엔드 폴더를 루트로 지정해야 합니다.

1. 생성된 서비스 클릭
2. **Settings** 탭 → **Source** 섹션 이동
3. **Add Root Directory** 클릭
4. `/backend` 입력 후 저장

> 💡 Railway UI에서 `Add Root Directory`가 버튼처럼 보이지 않아도, 텍스트 자체가 클릭 가능한 링크입니다.

#### 4. 환경변수 설정

1. **Variables** 탭 클릭
2. **New Variable** 클릭
3. Key: `ANTHROPIC_API_KEY` / Value: 실제 API 키 입력

#### 5. 배포 확인

**Deployments** 탭에서 **Active** 상태 확인 후, **Settings → Networking → Generate Domain** 클릭해 URL 생성.

```
https://YOUR_RAILWAY_URL
```

브라우저에서 `/docs` 경로로 접속해 FastAPI Swagger UI가 뜨면 성공입니다.

```
https://YOUR_RAILWAY_URL/docs
```

---

## 2단계: 프론트엔드 비밀번호 보호 기능 추가

배포 전, 특정 사람만 접근하도록 비밀번호 잠금 화면을 추가합니다.

### PasswordGate 컴포넌트

```tsx
// src/components/PasswordGate.tsx
import { useState, KeyboardEvent } from 'react'
import styles from './PasswordGate.module.css'

const PASSWORD = import.meta.env.VITE_APP_PASSWORD ?? ''

interface Props {
  onUnlock: () => void
}

export default function PasswordGate({ onUnlock }: Props) {
  const [input, setInput] = useState('')
  const [error, setError] = useState(false)

  const handleSubmit = () => {
    if (input === PASSWORD) {
      sessionStorage.setItem('unlocked', 'true')  // 탭 닫으면 자동 초기화
      onUnlock()
    } else {
      setError(true)
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSubmit()
  }

  return (
    <div className={styles.container}>
      <div className={styles.box}>
        <h1 className={styles.title}>🔐 SmartHee</h1>
        <input
          type="password"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          className={styles.input}
          placeholder="비밀번호 입력"
        />
        {error && <p className={styles.error}>비밀번호가 틀렸습니다.</p>}
        <button onClick={handleSubmit} className={styles.button}>입장</button>
      </div>
    </div>
  )
}
```

### App.tsx에 연동

```tsx
// src/App.tsx
import { useState } from 'react'
import ChatWindow from './components/ChatWindow'
import PasswordGate from './components/PasswordGate'

export default function App() {
  const [unlocked, setUnlocked] = useState(
    sessionStorage.getItem('unlocked') === 'true'  // 탭 닫으면 재입력 요구
  )

  if (!unlocked) {
    return <PasswordGate onUnlock={() => setUnlocked(true)} />
  }

  return <ChatWindow />
}
```

> ⚠️ **`localStorage` vs `sessionStorage`**: `localStorage`는 브라우저를 닫아도 유지되지만, `sessionStorage`는 탭/브라우저를 닫으면 자동으로 사라집니다. 보안을 위해 `sessionStorage`를 사용합니다.

> ⚠️ **보안 주의**: 비밀번호를 코드에 하드코딩하면 GitHub에 그대로 노출됩니다.
> `import.meta.env.VITE_APP_PASSWORD`로 환경변수 처리 후 Vercel에서만 값을 입력합니다.

---

## 3단계: TypeScript 타입 선언 추가

CSS Modules와 Vite 환경변수 타입 오류를 방지하기 위해 타입 선언 파일을 추가합니다.

```typescript
// src/vite-env.d.ts
/// <reference types="vite/client" />

declare module '*.module.css' {
  const classes: { [key: string]: string }
  export default classes
}
```

---

## 4단계: Vercel 프록시 설정

Vercel에서 `/api` 요청을 Railway 백엔드로 전달하도록 설정합니다.

```json
// frontend/vercel.json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://YOUR_RAILWAY_URL/api/:path*"
    }
  ]
}
```

---

## 5단계: Vercel 프론트엔드 배포

#### 1. Vercel 접속 및 로그인

[vercel.com](https://vercel.com) → **Continue with GitHub**

#### 2. 프로젝트 Import

**New Project** → `SmartHee_Chatbot` 선택 → **Import** 클릭

#### 3. Root Directory 설정

Root Directory: **frontend** 로 변경 (Edit 버튼 클릭)

#### 4. 환경변수 설정

| Key | Value |
|-----|-------|
| `VITE_APP_PASSWORD` | 사용할 비밀번호 |

#### 5. Deploy 클릭

배포 성공 후 생성된 URL:

```
https://smart-hee-chatbot.vercel.app/
```

---

## 6단계: 빌드 오류 트러블슈팅

### 오류 1: CSS Modules 타입 오류

```
error TS2307: Cannot find module './PasswordGate.module.css'
```

**원인**: TypeScript가 `.module.css` 파일을 인식하지 못함  
**해결**: `src/vite-env.d.ts`에 CSS Modules 타입 선언 추가

```typescript
declare module '*.module.css' {
  const classes: { [key: string]: string }
  export default classes
}
```

---

### 오류 2: import.meta.env 타입 오류

```
error TS2339: Property 'env' does not exist on type 'ImportMeta'
```

**원인**: Vite 환경변수 타입 미선언  
**해결**: `vite-env.d.ts` 상단에 아래 추가

```typescript
/// <reference types="vite/client" />
```

---

### 오류 3: tsc 빌드 실패

`tsc` 타입 체크에서 오류 발생 시 빌드 명령어를 단순화합니다.

```json
// package.json
"scripts": {
  "build": "vite build"  // tsc 제거
}
```

> `tsc`를 완전히 제거하기보다, 타입 오류를 모두 해결하는 것이 이상적이지만, 빠른 배포가 필요한 경우 임시 방편으로 사용 가능합니다.

---

## 7단계: 보안 강화

배포 후 뒤늦게 깨달았습니다. "아, 이거 그냥 두면 누구나 API 직접 호출할 수 있겠구나." 부랴부랴 3가지를 추가했습니다.

### 문제 1: CORS가 전체 허용 상태

```python
# 수정 전 — 전 세계 누구나 API 호출 가능 ❌
allow_origins=["*"]

# 수정 후 — Vercel URL만 허용 ✅
allow_origins=["https://smart-hee-chatbot.vercel.app"]
```

### 문제 2: 토큰 없이 API 직접 호출 가능

프론트엔드 비밀번호는 브라우저에서만 확인합니다. 개발자 도구에서 `sessionStorage.setItem('unlocked', 'true')` 한 줄이면 통과되고, 백엔드 URL을 알면 바로 API를 직접 호출할 수 있습니다.

백엔드에 토큰 검증을 추가해 해결했습니다.

```python
# backend/api/chat.py
@router.post("/chat", response_model=ChatResponse)
@limiter.limit("N/minute")  # 적절한 횟수로 설정
async def chat(
    request: Request,
    body: ChatRequest,
    x_app_token: str = Header(default=None)
):
    expected_token = os.getenv("APP_TOKEN")
    if not expected_token or not secrets.compare_digest(x_app_token or "", expected_token):
        raise HTTPException(status_code=401, detail="Unauthorized")
    ...
```

```typescript
// frontend — 요청 시 토큰 헤더 포함
headers: {
  'Content-Type': 'application/json',
  'X-App-Token': import.meta.env.VITE_APP_TOKEN ?? '',
}
```

Railway에 `APP_TOKEN`, Vercel에 `VITE_APP_TOKEN`을 동일한 값으로 등록합니다. 토큰 값은 아래로 생성합니다.

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 문제 3: Rate Limit 없음

토큰을 탈취당한 최악의 상황에서도 크레딧을 무한 소비당하지 않도록 `slowapi`로 분당 30회 제한을 걸었습니다.

```python
# main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

---

### 보안 테스트 결과

적용 후 직접 테스트했습니다.

**토큰 없이 API 호출 시:**
```bash
curl -X POST https://YOUR_RAILWAY_URL/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "test"}]}'

# 결과
{"detail":"Unauthorized"}  ✅
```

**외부 사이트에서 직접 호출 시:**
```
차단됨: Failed to fetch  ✅
```

| 항목 | 결과 |
|------|------|
| CORS 차단 | ✅ 외부 Origin 차단 확인 |
| 토큰 검증 | ✅ 401 Unauthorized 확인 |
| Rate Limit | ✅ 토큰 없는 요청 401 선차단 확인 |

---

## 8단계: 토큰 사용량 대시보드 추가

채팅 화면 옆 사이드바에 토큰 사용량과 예상 비용을 실시간으로 표시합니다.

### 구성 요소

- **이번 세션**: 입력/출력/총 토큰, 예상 비용
- **최근 7일 사용량**: 일별 막대 그래프 (`localStorage`에 누적 저장)
- **대화별 사용량**: 응답 단위로 토큰 수와 비용 표시

```tsx
// src/components/TokenDashboard.tsx 핵심 로직

// claude-sonnet-4-5 기준 단가
const INPUT_COST_PER_TOKEN = 3 / 1_000_000    // $3 / 1M tokens
const OUTPUT_COST_PER_TOKEN = 15 / 1_000_000  // $15 / 1M tokens

// 일별 사용량 localStorage에 최근 7일 저장
function saveTodayUsage(input: number, output: number) {
  const today = new Date().toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' })
  const history = loadDailyHistory()
  const existing = history.find(d => d.date === today)
  if (existing) {
    existing.input = input
    existing.output = output
  } else {
    history.push({ date: today, input, output })
  }
  localStorage.setItem('tokenHistory', JSON.stringify(history.slice(-7)))
}
```

### ChatWindow에 사이드바 연결

```tsx
// src/components/ChatWindow.tsx
return (
  <div className={styles.layout}>       {/* flex 레이아웃 */}
    <div className={styles.container}>  {/* 채팅 영역 */}
      ...
    </div>
    <TokenDashboard messages={messages} totalTokens={totalTokens} />
  </div>
)
```

```css
/* ChatWindow.module.css */
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.container {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
```

> 💡 **localStorage vs sessionStorage 혼용**: 비밀번호 인증은 `sessionStorage`(탭 닫으면 초기화), 토큰 히스토리는 `localStorage`(브라우저 닫아도 누적 유지)로 각각의 목적에 맞게 구분해서 사용합니다.

---

## ✅ 최종 결과

| 항목 | URL |
|------|-----|
| 백엔드 API | Railway 배포 후 생성된 URL + `/docs` |
| 프론트엔드 | `https://smart-hee-chatbot.vercel.app/` |

- 접속 시 비밀번호 입력 화면 표시
- 브라우저/탭 종료 시 자동으로 비밀번호 재입력 요구 (`sessionStorage`)
- 정확한 비밀번호 입력 시 채팅 화면으로 진입
- 채팅 화면 우측 사이드바에 토큰 사용량 및 예상 비용 실시간 표시

---

## 💡 배운 점

1. **모노레포 배포 시 Root Directory 설정**이 핵심 — Railway와 Vercel 모두 서브폴더 지정이 필요
2. **민감 정보는 절대 코드에 하드코딩 금지** — 환경변수로 관리하고 플랫폼 콘솔에서 입력
3. **Vite 프로젝트 TypeScript 타입 선언** — `vite-env.d.ts` 파일로 CSS Modules 및 `import.meta.env` 타입 해결
4. **Vercel의 rewrites** — 프록시 설정으로 CORS 없이 백엔드 API 호출 가능
5. **프론트엔드 인증은 믿으면 안 된다** — 브라우저 검증은 우회가 쉬우므로 백엔드에서 반드시 재검증
6. **`allow_origins=["*"]` 는 개발용** — 배포 시 반드시 실제 도메인으로 교체
7. **Rate Limit은 보험** — 토큰이 탈취되더라도 피해를 최소화하는 마지막 방어선
8. **`localStorage` vs `sessionStorage` 목적 구분** — 인증 상태는 세션 단위, 누적 데이터는 영구 저장

---

*전체 소스코드: [github.com/parkjongmin-ddam/SmartHee_Chatbot](https://github.com/parkjongmin-ddam/SmartHee_Chatbot)*