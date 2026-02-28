---
layout: single
title: "[Node.js] 기초 웹 서버 구축 (http 모듈 vs Express 프레임워크)"
categories: nodejs
tag: [nodejs, express, web-server, backend]
toc: true
author_profile: false
sidebar:
  nav: "docs"
---

# Node.js 기초 웹 서버 구축 비교

![http_vs_express](/assets/images/http_vs_express_1772270080061.png)

Node.js를 사용하여 웹 서버를 구축하는 두 가지 기본적인 방법인 내장 `http` 모듈을 사용하는 방법과 `express` 프레임워크를 사용하는 방법을 정리함.

## 1. 내장 `http` 모듈을 사용한 웹 서버 구축

Node.js의 기본 내장 모듈인 `http`를 사용하면 추가적인 프레임워크 설치 없이 원시적인 형태의 웹 서버를 구축할 수 있음.

### 코드 예시 (1_server.js)

```javascript
const http = require('http');
const url = require('url');

// localhost로 호출 설정
const host = 'localhost'
const port = 3000;

// req: 요청 (request), res: 응답 (response)
const server = http.createServer((req, res) => {
    // 요청된 URL에서 경로(.pathname) 추출
    const path = url.parse(req.url).pathname;

    // 라우팅 처리
    if (path === '/') {
        res.writeHead(200, { 'content-type': 'text/html' });
        res.end('<h1>page</h1>');
    }
    else if (path === '/post') {
        res.writeHead(200, { 'content-type': 'text/html' });
        res.end('<h1>postpage</h1>');
    }
    else if (path === '/user') {
        res.writeHead(200, { 'content-type': 'text/html' });
        res.end('<h1>userpage</h1>');
    }
    else {
        res.writeHead(404, { 'content-type': 'text/html' });
        res.end('<h1>page not found</h1>');
    }
});

// 서버 실행
server.listen(port, host, () => {
    console.log(`Server running at http://localhost:3000`);
});
```

### 특징
- 라우팅(URL 경로 분기) 처리를 위해 `if-else` 문과 같은 조건문을 직접 작성해야 함.
- 응답 헤더(`res.writeHead`)와 응답 본문(`res.end`)을 세밀하게 제어할 수 있지만, 코드가 길어지고 가독성이 떨어질 수 있음.

---

## 2. Express 프레임워크를 사용한 웹 서버 구축

`Express`는 Node.js 환경에서 가장 널리 사용되는 웹 프레임워크임. `http` 모듈의 복잡한 부분을 추상화하여 훨씬 간결하고 직관적인 코드로 웹 서버를 만들 수 있게 해줌.

### 패키지 설치
Express는 내장 모듈이 아니므로, `yarn` 또는 `npm`을 이용해 프로젝트에 설치해야 함.
```bash
yarn add express
```

### 코드 예시 (2_server.js)

```javascript
const express = require('express');

// app 객체 생성
const app = express();

// 라우팅 설정
app.get('/', (req, res) => {
    res.send('Hello World!');
});

app.get('/post', (req, res) => {
    res.send('post page');
});

app.get('/user', (req, res) => {
    res.send('user page');
});

// 등록되지 않은 경로(404)에 대한 예외 처리 미들웨어
app.use((req, res) => {
    res.status(404).send('404 Error');
});

// 서버 실행
app.listen(3000, () => {
    console.log('Server running at http://localhost:3000');
});
```

### 특징
- `app.get()`, `app.post()` 등의 메서드를 활용하여 라우팅을 매우 직관적으로 구현할 수 있음.
- 응답 시 `res.send()`를 사용하면 알맞은 Content-Type을 자동으로 설정하여 데이터를 전송함.
- `app.use()`를 활용한 미들웨어 구조를 가져, 404 에러 처리 등 공통 로직을 쉽게 관리할 수 있음.

---

## 요약

| 특징 | `http` 모듈 (기본) | `Express` 프레임워크 |
|------|--------------------|-----------------------|
| **모듈 필요 여부** | 내장 모듈 (별도 설치 불필요) | 외부 패키지 (`yarn add express` 필요) |
| **라우팅 구현** | `if`, `switch` 문 등을 사용해 직접 분기 | `app.get()`, `app.post()` 등 메서드 지원 |
| **코드 가독성** | 상대적으로 코드가 길어지고 복잡해짐 | 코드가 매우 간결하고 구조적임 |
| **가장 큰 장점** | 원시적인 제어가 가능하고 가벼움 | 직관적인 API, 풍부한 미들웨어 생태계 제공 |

처음 웹 작동 원리를 이해할 때는 내장 `http` 모듈을 써보는 것이 좋으나, 실제 실무나 복잡한 프로젝트에서는 라우팅과 미들웨어가 강력한 **Express**를 사용하는 것이 효율적임.
