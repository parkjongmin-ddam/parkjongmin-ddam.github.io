---
layout: single
title: "Terraform VPC, Subnet, Gateway 및 Route Table 설정"
categories: terraform
tags: [AWS, terraform, vpc, subnet, gateway, route-table]
toc: true
author_profile: false
sidebar:
  nav: "docs"
---

# Terraform VPC, Subnet, Gateway 및 Route Table 설정

이 가이드는 **Terraform**을 사용하여 AWS에서 VPC, 서브넷, 인터넷 게이트웨이, NAT 게이트웨이, 그리고 라우팅 테이블을 설정하는 방법을 설명합니다. 이 구성은 **ap-northeast-2** 리전에서 하나의 퍼블릭 서브넷과 하나의 프라이빗 서브넷을 포함하는 VPC를 생성합니다.

---

## 1️⃣ 제공자 구성

AWS 제공자는 **ap-northeast-2** 리전을 사용하도록 설정됩니다.

```hcl
provider "aws" {
  region = "ap-northeast-2"
}
```

## 2️⃣ VPC 구성

CIDR 블록 `10.0.0.0/16`을 가진 VPC가 생성되며, 식별을 위해 태그가 지정됩니다.

```hcl
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "terraform-test-vpc"
  }
}
```

## 3️⃣ 서브넷 구성

### 퍼블릭 서브넷

`ap-northeast-2a` 가용 영역에 CIDR 블록 `10.0.0.0/24`을 가진 퍼블릭 서브넷이 생성됩니다.

```hcl
resource "aws_subnet" "public_subnet" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.0.0/24"
  availability_zone = "ap-northeast-2a"

  tags = {
    Name = "terraform-test-vpc-public-subnet"
  }
}
```

### 프라이빗 서브넷

`ap-northeast-2b` 가용 영역에 CIDR 블록 `10.0.10.0/24`을 가진 프라이빗 서브넷이 생성됩니다.

```hcl
resource "aws_subnet" "private_subnet" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "ap-northeast-2b"

  tags = {
    Name = "terraform-test-vpc-private-subnet"
  }
}
```

## 4️⃣ 인터넷 게이트웨이 구성

VPC에 연결된 인터넷 게이트웨이가 생성됩니다.

```hcl
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "terraform-test-vpc-igw"
  }
}
```

## 5️⃣ NAT 게이트웨이 구성

퍼블릭 서브넷에 연결된 NAT 게이트웨이가 생성됩니다.

```hcl
resource "aws_eip" "nat_eip" {
  domain = "vpc"

  lifecycle {
    create_before_destroy = ture
  }
}



resource "aws_nat_gateway" "nat_gw" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.public_subnet.id

  tags = {
    Name = "terraform-test-vpc-nat-gw"
  }
}
```

## 6️⃣ 라우팅 테이블 구성

### 퍼블릭 라우팅 테이블

퍼블릭 서브넷과 연결된 라우팅 테이블이 생성됩니다.

```hcl
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "terraform-test-vpc-rt-public"
  }
}

resource "aws_route_table_association" "route_table_association_public" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public.id
}
```

### 프라이빗 라우팅 테이블

프라이빗 서브넷과 연결된 라우팅 테이블이 생성됩니다.

```hcl
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "terraform-test-vpc-private-rt"
  }
}

resource "aws_route_table_association" "route_table_association_private" {
  subnet_id      = aws_subnet.private_subnet.id
  route_table_id = aws_route_table.private.id
}
```

## 7️⃣ 전체 구성 파일 예시

아래는 위의 모든 내용을 포함한 Terraform 구성 파일(main.tf)의 전체 예시입니다.

```hcl
provider "aws" {
  region = "ap-northeast-2"
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "terraform-test-vpc"
  }
}

resource "aws_subnet" "public_subnet" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.0.0/24"
  availability_zone = "ap-northeast-2a"

  tags = {
    Name = "terraform-test-vpc-public-subnet"
  }
}

resource "aws_subnet" "private_subnet" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "ap-northeast-2b"

  tags = {
    Name = "terraform-test-vpc-private-subnet"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "terraform-test-vpc-igw"
  }
}

resource "aws_eip" "nat_eip" {
  vpc = true
}

resource "aws_nat_gateway" "nat_gw" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.public_subnet.id

  tags = {
    Name = "terraform-test-vpc-NATGW"
  }
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "terraform-test-vpc-rt-public"
  }
}

resource "aws_route_table_association" "route_table_association_public" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "terraform-test-vpc-rt-private"
  }
}

resource "aws_route_table_association" "route_table_association_private" {
  subnet_id      = aws_subnet.private_subnet.id
  route_table_id = aws_route_table.private.id
}
```

```
참고 자료
Terraform 공식 문서(https://developer.hashicorp.com/terraform)
AWS VPC 소개(https://aws.amazon.com/ko/vpc/)
AWS Subnet 구성 가이드(https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Subnets.html)
```