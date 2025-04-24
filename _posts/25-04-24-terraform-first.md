---
layout: single
title: "Terraform 기본 가이드 (AWS 환경 설정)"
categories: terraform
tags: [AWS, terraform]
toc: true
author_profile: false
sidebar:
  nav: "docs"
---

# Terraform 기본 가이드 (AWS 환경 설정)

이 가이드는 AWS EC2 인스턴스 생성, IAM 계정 생성 및 Access Key 발급, zsh 및 oh-my-zsh 설치, AWS CLI 설정, 그리고 Terraform 설치를 AWS Linux 환경에서 진행하는 방법을 설명합니다.

---

## 1️⃣ AWS EC2 생성

1. **AWS Management Console**에 로그인합니다.
2. **EC2 서비스**로 이동하여 **"인스턴스 시작"**을 클릭합니다.
3. **Amazon Linux 2 AMI**를 선택합니다.
4. **인스턴스 유형**(예: `t2.micro`)을 선택하고, 키 페어를 생성하거나 기존 키를 선택합니다.
5. **네트워크 설정**에서 SSH 포트(22번)가 열려 있는 보안 그룹을 설정합니다.
6. **인스턴스를 시작**하고, 접속을 위해 `.pem` 키 파일을 안전하게 저장합니다.

---

## 2️⃣ IAM 계정 생성 및 Access Key 발급

1. **AWS Management Console**에서 **IAM 서비스**로 이동합니다.
2. **사용자 메뉴**에서 **"사용자 추가"**를 클릭합니다.
3. 사용자 이름을 입력하고, **프로그래밍 방식 액세스**를 선택합니다.
4. 적절한 권한 정책(예: `AdministratorAccess`)을 연결합니다.
5. 사용자 생성 후 **Access Key ID**와 **Secret Access Key**를 다운로드하거나 기록합니다.

> **⚠️ 주의:** 이 키는 한 번만 표시되므로 안전하게 저장하세요.

---

## 3️⃣ zsh 및 oh-my-zsh 설치 (AWS Linux, MobaXterm 사용)

### 3.1 zsh 설치

1. AWS EC2 인스턴스에 SSH로 접속합니다 (MobaXterm 사용).
   ```bash
   ssh -i <your-key.pem> ec2-user@<EC2-Public-IP>

2. zsh 및 관련 유틸리티 설치
    ```
    sudo yum install -y zsh
    sudo yum install -y util-linux-user.x86_64
    sudo yum install -y git
    ```

3. 기본 쉘을 zsh로 변경
    ```
    chsh -s /bin/zsh
    ```

### 3.2 oh-my-zsh 설치

1. oh-my-zsh 설치 스크립트 실행
    ```
    curl -L https://raw.github.com/robbyrussell/oh-my-zsh/master/tools/install.sh | sh
    ```

2. oh-my-zsh 테마 설정
    ```
    vi ~/.zshrc
    ZSH_THEME="ys"로 변경 후 저장하고 종료 합니다.
    ```

3. 설정 적용
    ```
    source ~/.zshrc
    ```

## 4️⃣ AWS CLI 설치 및 구성

### 4.1 AWS CLI 설치

1. AWS CLI v2 다운로드 및 설치
    ```
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    sudo ./aws/install
    ```

2. 설치 확인
    ```
    aws --version
    ```

### 4.2 AWS Configure 설정

1. AWS CLI 구성
    ```
    aws configure
    ```

2. 다음 정보를 입력
    ```
    AWS Access Key ID [None]: <IAM에서 발급받은 Access Key ID>
    AWS Secret Access Key [None]: <IAM에서 발급받은 Secret Access Key>
    Default region name [None]: ap-northeast-2 #본인이 사용하는 regeion 정보 설정
    Default output format [None]: json
    ```

## 5️⃣ Terraform 설치

1. Terraform 설치 준비
    ```
    sudo yum install -y yum-utils shadow-utils
    sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/AmazonLinux/hashicorp.repo
    ```
2. Terraform 설치
    ```
    sudo yum -y install terraform
    ```

3. 설치 확인
    ```
    terraform --version
    ```

## 6️⃣ Terraform 기본 사용 예시

### 6.1 Terraform 구성 파일 생성

1. 작업 디렉터리 생성
    ```
    mkdir terraform-example
    cd terraform-example
    vi main.tf
    ```

2. 예시 main.tf 파일
    ```
    provider "aws" {
    region = "ap-northeast-2"
}

    resource "aws_instance" "example" {
    ami           = "ami-0c55b159cbfafe1f0" # Amazon Linux 2 AMI
    instance_type = "t2.micro"

    tags = {
    Name = "Terraform-Example"
    } 
}
    ```

### 6.2 Terraform 초기화 및 적용

1. Terraform 초기화
    ```
    terraform init
    ```

2. Terraform 적용
    ```
    terraform apply
    적용 확인 후 yes를 입력합니다.
    ```
3. 리소스 삭제(필요 시)
    ```
    terraform destroy
    ```
### 참고자료
https://developer.hashicorp.com/terraform
https://aws.amazon.com/cli/
