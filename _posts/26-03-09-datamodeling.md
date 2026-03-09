---
layout: single
title: "[TIL] 도서관리시스템으로 배우는 ERD 설계 — 개념·논리·물리 모델링 완전 정리"
excerpt: "도서관리시스템 예제를 통해 데이터베이스 설계의 핵심인 ERD의 개념적, 논리적, 물리적 모델링 3단계를 실습하고 핵심 설계 원칙을 정리함."
categories: [Database, ERD]
tags: [ERD, Database, Modeling, 데이터베이스설계, TIL]

---

## 📌 오늘의 학습 목표 (TIL)

> 데이터베이스 설계의 핵심인 **ERD(Entity-Relationship Diagram)**를 도서관리시스템을 예제로 삼아
> 개념적 → 논리적 → 물리적 모델링 3단계를 순서대로 실습하고 정리한다.

---

## 1. ERD란 무엇인가?

**ERD(Entity-Relationship Diagram)** 는 데이터베이스의 구조를 시각적으로 표현하는 다이어그램이다.  
시스템에 어떤 **개체(Entity)** 가 존재하고, 개체들 사이에 어떤 **관계(Relationship)** 가 있으며,  
각 개체가 어떤 **속성(Attribute)** 을 가지는지를 한눈에 파악할 수 있다.

### ERD 설계의 3단계

| 단계 | 이름 | 목적 | 산출물 |
|------|------|------|--------|
| 1단계 | **개념적 모델링** | 비즈니스 관점에서 핵심 개체와 관계 정의 | 개념 ERD |
| 2단계 | **논리적 모델링** | 특정 DBMS 독립적으로 테이블·속성·키 정의 | 논리 ERD |
| 3단계 | **물리적 모델링** | 실제 DBMS에 맞는 DDL 작성 | SQL 스크립트 |

---

## 2. 도서관리시스템 요구사항 분석

설계를 시작하기 전에 **업무 요구사항**을 먼저 파악한다.

```
✅ 도서관은 다수의 도서(Book)를 보유한다.
✅ 각 도서는 하나 이상의 저자(Author)가 있다.
✅ 도서는 하나의 카테고리(Category)에 분류된다.
✅ 도서는 하나의 출판사(Publisher)에서 출판된다.
✅ 회원(Member)은 도서를 대출(Loan)할 수 있다.
✅ 하나의 대출에는 하나의 도서만 포함된다.
✅ 반납 기한은 대출일로부터 14일이다.
✅ 연체 시 연체료(fine)가 발생한다.
```

---

## 3. 개념적 모델링 (Conceptual Modeling)

### 개념적 모델링이란?

> **"무엇을 저장할 것인가?"**  
> 기술적 세부사항 없이, 현실 세계의 개체와 관계를 **추상적**으로 표현하는 단계.  
> DB 전문가가 아닌 **업무 담당자도 이해**할 수 있어야 한다.

### 핵심 개체(Entity) 도출

요구사항에서 **명사**를 추출하여 개체를 도출한다.

| 개체 | 설명 |
|------|------|
| **도서 (Book)** | 도서관이 보유한 책 |
| **저자 (Author)** | 도서를 집필한 사람 |
| **카테고리 (Category)** | 도서의 분류 체계 |
| **출판사 (Publisher)** | 도서를 출판한 회사 |
| **회원 (Member)** | 도서를 대출하는 사람 |
| **대출 (Loan)** | 도서와 회원 간의 대출 행위 |

### 관계(Relationship) 도출

요구사항에서 **동사**를 추출하여 관계를 도출한다.

```
도서 ──[집필]── 저자        (N:M - 도서는 여러 저자, 저자는 여러 도서)
도서 ──[분류]── 카테고리    (N:1 - 여러 도서가 하나의 카테고리에 속함)
도서 ──[출판]── 출판사      (N:1 - 여러 도서가 하나의 출판사에서 출판됨)
회원 ──[대출]── 도서        (N:M - 회원은 여러 도서, 도서는 여러 회원에게)
```

### 개념적 ERD (텍스트 표현)

```
┌──────────┐       ┌──────────┐       ┌──────────┐
│  Author  │──────<│   Book   │>──────│Publisher │
└──────────┘  N:M  └────┬─────┘  N:1  └──────────┘
                         │
                     N:1 │
                    ┌────┴─────┐
                    │ Category │
                    └──────────┘

┌──────────┐       ┌──────────┐       ┌──────────┐
│  Member  │──────<│   Loan   │>──────│   Book   │
└──────────┘  1:N  └──────────┘  N:1  └──────────┘
```

---

## 4. 논리적 모델링 (Logical Modeling)

### 논리적 모델링이란?

> **"어떻게 구조화할 것인가?"**  
> 개념적 모델을 구체적인 **테이블, 컬럼, 기본키(PK), 외래키(FK)** 로 변환하는 단계.  
> 특정 DBMS에 종속되지 않고, **정규화(Normalization)** 를 적용한다.

### N:M 관계 해소 — 중간 테이블 생성

`도서 ↔ 저자`의 N:M 관계는 **book_author** 연결 테이블로 해소한다.

### 논리적 테이블 정의

#### 📚 book (도서)

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| book_id | INTEGER | PK | 도서 식별자 |
| isbn | VARCHAR(13) | UNIQUE, NOT NULL | 국제표준도서번호 |
| title | VARCHAR(200) | NOT NULL | 도서 제목 |
| category_id | INTEGER | FK → category | 카테고리 |
| publisher_id | INTEGER | FK → publisher | 출판사 |
| published_date | DATE | | 출판일 |
| total_copies | INTEGER | NOT NULL, DEFAULT 1 | 총 보유 수량 |
| available_copies | INTEGER | NOT NULL | 대출 가능 수량 |

#### ✍️ author (저자)

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| author_id | INTEGER | PK | 저자 식별자 |
| name | VARCHAR(100) | NOT NULL | 저자명 |
| nationality | VARCHAR(50) | | 국적 |
| bio | TEXT | | 약력 |

#### 🔗 book_author (도서-저자 연결)

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| book_id | INTEGER | PK, FK → book | 도서 |
| author_id | INTEGER | PK, FK → author | 저자 |
| role | VARCHAR(50) | | 역할 (저자/역자 등) |

#### 🗂️ category (카테고리)

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| category_id | INTEGER | PK | 카테고리 식별자 |
| name | VARCHAR(100) | NOT NULL | 카테고리명 |
| parent_id | INTEGER | FK → category | 상위 카테고리 (자기 참조) |

#### 🏢 publisher (출판사)

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| publisher_id | INTEGER | PK | 출판사 식별자 |
| name | VARCHAR(200) | NOT NULL | 출판사명 |
| phone | VARCHAR(20) | | 전화번호 |
| address | VARCHAR(300) | | 주소 |

#### 👤 member (회원)

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| member_id | INTEGER | PK | 회원 식별자 |
| name | VARCHAR(100) | NOT NULL | 회원명 |
| email | VARCHAR(200) | UNIQUE, NOT NULL | 이메일 |
| phone | VARCHAR(20) | | 전화번호 |
| joined_date | DATE | NOT NULL | 가입일 |
| status | VARCHAR(20) | NOT NULL | 상태 (ACTIVE/SUSPENDED) |

#### 📋 loan (대출)

| 컬럼명 | 타입 | 제약조건 | 설명 |
|--------|------|----------|------|
| loan_id | INTEGER | PK | 대출 식별자 |
| member_id | INTEGER | FK → member | 대출 회원 |
| book_id | INTEGER | FK → book | 대출 도서 |
| loan_date | DATE | NOT NULL | 대출일 |
| due_date | DATE | NOT NULL | 반납 기한일 |
| return_date | DATE | | 실제 반납일 |
| fine | DECIMAL(10,2) | DEFAULT 0 | 연체료 |
| status | VARCHAR(20) | NOT NULL | 상태 (ACTIVE/RETURNED/OVERDUE) |

### 논리적 ERD 관계 정의

```
category  1 ─── N  book
publisher 1 ─── N  book
book      N ─── M  author  (via book_author)
member    1 ─── N  loan
book      1 ─── N  loan
category  1 ─── N  category (자기 참조: 대분류 → 소분류)
```

---

## 5. 물리적 모델링 (Physical Modeling)

### 물리적 모델링이란?

> **"실제 DB에 어떻게 생성할 것인가?"**  
> 논리 모델을 선택한 **DBMS(MySQL, PostgreSQL, Oracle 등)** 에 맞는 구체적인  
> DDL(Data Definition Language)로 변환하는 단계.  
> 데이터 타입, 인덱스, 파티셔닝, 스토리지 엔진 등 **성능과 운영 관점**을 고려한다.

> 이하 예시는 **MySQL 8.0** 기준으로 작성한다.

### DDL 스크립트

```sql
-- ============================================================
-- 도서관리시스템 물리적 모델 DDL (MySQL 8.0)
-- ============================================================

CREATE DATABASE IF NOT EXISTS library_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE library_db;

-- ──────────────────────────────────────────
-- 1. category (카테고리)
-- ──────────────────────────────────────────
CREATE TABLE category (
    category_id   INT           NOT NULL AUTO_INCREMENT,
    name          VARCHAR(100)  NOT NULL,
    parent_id     INT           NULL COMMENT '상위 카테고리 (자기 참조)',
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_category      PRIMARY KEY (category_id),
    CONSTRAINT fk_cat_parent    FOREIGN KEY (parent_id)
                                REFERENCES category(category_id)
                                ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='도서 카테고리';

-- ──────────────────────────────────────────
-- 2. publisher (출판사)
-- ──────────────────────────────────────────
CREATE TABLE publisher (
    publisher_id  INT           NOT NULL AUTO_INCREMENT,
    name          VARCHAR(200)  NOT NULL,
    phone         VARCHAR(20)   NULL,
    address       VARCHAR(300)  NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_publisher     PRIMARY KEY (publisher_id)
) ENGINE=InnoDB COMMENT='출판사';

-- ──────────────────────────────────────────
-- 3. author (저자)
-- ──────────────────────────────────────────
CREATE TABLE author (
    author_id     INT           NOT NULL AUTO_INCREMENT,
    name          VARCHAR(100)  NOT NULL,
    nationality   VARCHAR(50)   NULL,
    bio           TEXT          NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_author        PRIMARY KEY (author_id)
) ENGINE=InnoDB COMMENT='저자';

-- ──────────────────────────────────────────
-- 4. book (도서)
-- ──────────────────────────────────────────
CREATE TABLE book (
    book_id           INT           NOT NULL AUTO_INCREMENT,
    isbn              VARCHAR(13)   NOT NULL,
    title             VARCHAR(200)  NOT NULL,
    category_id       INT           NOT NULL,
    publisher_id      INT           NOT NULL,
    published_date    DATE          NULL,
    total_copies      INT           NOT NULL DEFAULT 1,
    available_copies  INT           NOT NULL DEFAULT 1,
    created_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT pk_book            PRIMARY KEY (book_id),
    CONSTRAINT uq_book_isbn       UNIQUE (isbn),
    CONSTRAINT fk_book_category   FOREIGN KEY (category_id)
                                  REFERENCES category(category_id),
    CONSTRAINT fk_book_publisher  FOREIGN KEY (publisher_id)
                                  REFERENCES publisher(publisher_id),
    CONSTRAINT chk_copies         CHECK (available_copies >= 0
                                    AND available_copies <= total_copies)
) ENGINE=InnoDB COMMENT='도서';

-- 검색 성능을 위한 인덱스
CREATE INDEX idx_book_title       ON book (title);
CREATE INDEX idx_book_category    ON book (category_id);
CREATE INDEX idx_book_publisher   ON book (publisher_id);

-- ──────────────────────────────────────────
-- 5. book_author (도서-저자 연결 테이블)
-- ──────────────────────────────────────────
CREATE TABLE book_author (
    book_id    INT          NOT NULL,
    author_id  INT          NOT NULL,
    role       VARCHAR(50)  NULL COMMENT '저자 역할 (저자/역자/편저 등)',
    CONSTRAINT pk_book_author    PRIMARY KEY (book_id, author_id),
    CONSTRAINT fk_ba_book        FOREIGN KEY (book_id)
                                 REFERENCES book(book_id)  ON DELETE CASCADE,
    CONSTRAINT fk_ba_author      FOREIGN KEY (author_id)
                                 REFERENCES author(author_id)
) ENGINE=InnoDB COMMENT='도서-저자 연결';

-- ──────────────────────────────────────────
-- 6. member (회원)
-- ──────────────────────────────────────────
CREATE TABLE member (
    member_id    INT           NOT NULL AUTO_INCREMENT,
    name         VARCHAR(100)  NOT NULL,
    email        VARCHAR(200)  NOT NULL,
    phone        VARCHAR(20)   NULL,
    joined_date  DATE          NOT NULL,
    status       VARCHAR(20)   NOT NULL DEFAULT 'ACTIVE'
                               COMMENT 'ACTIVE | SUSPENDED | WITHDRAWN',
    created_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                               ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT pk_member        PRIMARY KEY (member_id),
    CONSTRAINT uq_member_email  UNIQUE (email),
    CONSTRAINT chk_mem_status   CHECK (status IN ('ACTIVE','SUSPENDED','WITHDRAWN'))
) ENGINE=InnoDB COMMENT='회원';

-- ──────────────────────────────────────────
-- 7. loan (대출)
-- ──────────────────────────────────────────
CREATE TABLE loan (
    loan_id      INT             NOT NULL AUTO_INCREMENT,
    member_id    INT             NOT NULL,
    book_id      INT             NOT NULL,
    loan_date    DATE            NOT NULL,
    due_date     DATE            NOT NULL,
    return_date  DATE            NULL     COMMENT '실제 반납일 (NULL = 미반납)',
    fine         DECIMAL(10,2)   NOT NULL DEFAULT 0.00 COMMENT '연체료',
    status       VARCHAR(20)     NOT NULL DEFAULT 'ACTIVE'
                                 COMMENT 'ACTIVE | RETURNED | OVERDUE',
    created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                 ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT pk_loan           PRIMARY KEY (loan_id),
    CONSTRAINT fk_loan_member    FOREIGN KEY (member_id)
                                 REFERENCES member(member_id),
    CONSTRAINT fk_loan_book      FOREIGN KEY (book_id)
                                 REFERENCES book(book_id),
    CONSTRAINT chk_loan_status   CHECK (status IN ('ACTIVE','RETURNED','OVERDUE')),
    CONSTRAINT chk_loan_fine     CHECK (fine >= 0)
) ENGINE=InnoDB COMMENT='대출 내역';

CREATE INDEX idx_loan_member  ON loan (member_id);
CREATE INDEX idx_loan_book    ON loan (book_id);
CREATE INDEX idx_loan_status  ON loan (status);
```

---

## 6. 3단계 모델링 비교 정리

| 항목 | 개념적 모델링 | 논리적 모델링 | 물리적 모델링 |
|------|--------------|--------------|--------------|
| **관점** | 비즈니스 | 데이터 구조 | 구현/운영 |
| **대상** | 업무 담당자 | DB 설계자 | DBA / 개발자 |
| **표현** | 개체·관계 다이어그램 | 테이블·속성·키 | DDL (SQL) |
| **DBMS 종속** | ❌ 독립 | ❌ 독립 | ✅ 종속 |
| **N:M 관계** | 그대로 표현 | 중간 테이블로 해소 | 실제 테이블 생성 |
| **데이터 타입** | 없음 | 논리 타입 | DBMS 전용 타입 |
| **인덱스** | 없음 | 없음 | 성능 고려 추가 |

---

## 7. 핵심 설계 원칙 정리

### ① 정규화(Normalization)

- **1NF**: 모든 컬럼이 원자값을 가져야 한다 → 저자를 별도 테이블로 분리
- **2NF**: 부분 함수 종속 제거 → `book_author`에서 book 정보를 중복 저장하지 않음
- **3NF**: 이행 종속 제거 → 출판사 정보를 `publisher` 테이블로 분리

### ② 참조 무결성(Referential Integrity)

- FK 제약조건으로 고아(orphan) 데이터 방지
- `ON DELETE CASCADE`: 도서 삭제 시 `book_author` 자동 삭제
- `ON DELETE SET NULL`: 상위 카테고리 삭제 시 하위 카테고리의 parent_id → NULL

### ③ 감사(Audit) 컬럼

- `created_at`, `updated_at` 컬럼을 핵심 테이블에 추가하여 데이터 변경 이력 추적

---

## 8. 오늘의 회고 (Retrospective)

✅ **잘 된 점**
- 요구사항에서 개체·관계를 체계적으로 도출하는 흐름을 잡았다.
- N:M 관계를 중간 테이블로 해소하는 개념을 확실히 이해했다.
- 자기 참조(Self-Reference)를 `category.parent_id`로 표현했다.

🔄 **개선할 점**
- 실제 Workbench나 ERDCloud 같은 도구로 시각적인 ERD 다이어그램도 그려보기
- 대출 이력의 연체료 자동 계산 로직 (트리거 또는 애플리케이션 레이어)을 추가 설계해보기
- 인덱스 전략을 더 깊이 고민해보기 (카디널리티, 복합 인덱스 등)

---

> 📚 **Reference**
> - [MySQL 8.0 Reference Manual](https://dev.mysql.com/doc/refman/8.0/en/)
> - 데이터베이스 개론 — 김연희 저 (한빛아카데미)