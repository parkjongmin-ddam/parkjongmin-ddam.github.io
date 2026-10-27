---
layout: single
title: "ADFS 업무 관련 자동화 스크립트 설정"
categories: ["IAM", "ADFS"]
permalink: "/terraform/ADFS_Script/"
tags: [ADFS, PowerShell, 자동화, RelyingPartyTrust, ApplicationGroup]
toc: true
author_profile: false
sidebar:
  nav: "docs"
---


# ADFS 관리 자동화 PowerShell 스크립트 모음집

## 📋 개요

ADFS(Active Directory Federation Services) 관리 작업을 자동화하기 위한 PowerShell 스크립트 모음집입니다. 
기존 설정을 안전하게 보존하면서 새로운 설정을 추가할 수 있도록 설계되었습니다.

### 🎯 주요 특징
- **기존 정보 완전 보존**: 모든 기존 설정이 유지됩니다
- **중복 방지**: "이미 사용중입니다" 메시지로 중복 등록 차단
- **단일/다수 처리**: 하나씩 또는 여러 개를 한번에 추가 가능
- **안전한 처리**: 오류 발생 시 적절한 롤백 및 메시지 제공
- **사용자 친화적**: 작업 전후 상태를 명확히 표시

---

## 🛠️ 스크립트 목록

### 1. Relying Party Trust Identifier 추가
### 2. SAML Assertion Consumer Endpoints 추가  
### 3. Application Groups Web API Identifier 추가
### 4. Application Groups Native App Redirect URI 추가

---

## 📝 1. Relying Party Trust Identifier 추가

기존 Relying Party Trust의 Identifier를 유지하면서 새로운 Identifier를 추가합니다.

### 사용법

```powershell
# 단일 추가
.\Add-RPIdentifier.ps1 -RelyingPartyName "MyApp" -NewIdentifier "https://newapp.example.com"

# 다수 추가
.\Add-RPIdentifier.ps1 -RelyingPartyName "MyApp" -NewIdentifiers @("https://app1.com", "https://app2.com", "https://app3.com")
```

### 스크립트 코드

```powershell
# Relying Party Trust Identifier 추가 스크립트
# 단일 추가 | 다수 추가 두 가지 방식

param(
    [Parameter(Mandatory=$true)]
    [string]$RelyingPartyName,
    
    [Parameter(ParameterSetName="Single", Mandatory=$true)]
    [string]$NewIdentifier,
    
    [Parameter(ParameterSetName="Multiple", Mandatory=$true)]
    [array]$NewIdentifiers
)

# 단일 Identifier 추가 함수
function Add-SingleIdentifier {
    param(
        [string]$RPName,
        [string]$NewIdentifier
    )
    
    try {
        Write-Host "=== 단일 Identifier 추가 ===" -ForegroundColor Green
        Write-Host "대상 RP: $RPName" -ForegroundColor Cyan
        Write-Host "추가할 Identifier: $NewIdentifier" -ForegroundColor Cyan
        
        # 기존 Trust 가져오기
        $trust = Get-AdfsRelyingPartyTrust -Name $RPName -ErrorAction Stop
        $currentIdentifiers = $trust.Identifier
        
        Write-Host "기존 Identifier 개수: $($currentIdentifiers.Count)" -ForegroundColor Yellow
        
        # 중복 확인
        if ($currentIdentifiers -contains $NewIdentifier) {
            Write-Host "❌ 해당 Identifier는 이미 사용중입니다: $NewIdentifier" -ForegroundColor Red
            Write-Host "추가할 수 없습니다." -ForegroundColor Yellow
            return $false
        }
        
        # 기존 + 새 Identifier 합치기
        $updatedIdentifiers = @($currentIdentifiers) + @($NewIdentifier)
        
        # 업데이트 적용
        Set-AdfsRelyingPartyTrust -TargetName $RPName -Identifier $updatedIdentifiers -ErrorAction Stop
        
        Write-Host "✅ 단일 Identifier 추가 완료!" -ForegroundColor Green
        Write-Host "총 Identifier 개수: $($updatedIdentifiers.Count)" -ForegroundColor Green
        
        return $true
        
    }
    catch {
        Write-Error "❌ 단일 Identifier 추가 실패: $($_.Exception.Message)"
        return $false
    }
}

# 다수 Identifier 추가 함수
function Add-MultipleIdentifiers {
    param(
        [string]$RPName,
        [array]$NewIdentifiers
    )
    
    try {
        Write-Host "=== 다수 Identifier 추가 ===" -ForegroundColor Green
        Write-Host "대상 RP: $RPName" -ForegroundColor Cyan
        Write-Host "추가할 개수: $($NewIdentifiers.Count)" -ForegroundColor Cyan
        
        # 기존 Trust 가져오기
        $trust = Get-AdfsRelyingPartyTrust -Name $RPName -ErrorAction Stop
        $currentIdentifiers = $trust.Identifier
        
        Write-Host "기존 Identifier 개수: $($currentIdentifiers.Count)" -ForegroundColor Yellow
        
        # 중복 확인
        $duplicates = @()
        $uniqueIdentifiers = @()
        
        foreach ($newId in $NewIdentifiers) {
            if ($currentIdentifiers -contains $newId) {
                $duplicates += $newId
            } else {
                $uniqueIdentifiers += $newId
            }
        }
        
        if ($duplicates.Count -gt 0) {
            Write-Host "`n❌ 다음 Identifier는 이미 사용중입니다:" -ForegroundColor Red
            foreach ($dup in $duplicates) {
                Write-Host "   - $dup (사용중)" -ForegroundColor Red
            }
        }
        
        if ($uniqueIdentifiers.Count -eq 0) {
            Write-Host "`n모든 Identifier가 이미 사용중입니다. 추가할 항목이 없습니다." -ForegroundColor Yellow
            return $false
        }
        
        # 모든 Identifier 합치기 (기존 + 새로운 것들)
        $allIdentifiers = @($currentIdentifiers) + @($uniqueIdentifiers)
        
        # 업데이트 적용
        Set-AdfsRelyingPartyTrust -TargetName $RPName -Identifier $allIdentifiers -ErrorAction Stop
        
        Write-Host "✅ 다수 Identifier 추가 완료!" -ForegroundColor Green
        Write-Host "총 Identifier 개수: $($allIdentifiers.Count)" -ForegroundColor Green
        Write-Host "새로 추가된 개수: $($uniqueIdentifiers.Count)" -ForegroundColor Green
        
        if ($duplicates.Count -gt 0) {
            Write-Host "이미 사용중으로 건너뛴 개수: $($duplicates.Count)" -ForegroundColor Yellow
        }
        
        return $true
        
    }
    catch {
        Write-Error "❌ 다수 Identifier 추가 실패: $($_.Exception.Message)"
        return $false
    }
}

# 현재 상태 조회 함수
function Show-CurrentIdentifiers {
    param([string]$RPName)
    
    try {
        $trust = Get-AdfsRelyingPartyTrust -Name $RPName -ErrorAction Stop
        
        Write-Host "`n=== 현재 Identifier 목록 ===" -ForegroundColor Yellow
        Write-Host "총 개수: $($trust.Identifier.Count)" -ForegroundColor Cyan
        
        if ($trust.Identifier.Count -gt 0) {
            for ($i = 0; $i -lt $trust.Identifier.Count; $i++) {
                Write-Host "  [$($i+1)] $($trust.Identifier[$i])" -ForegroundColor White
            }
        } else {
            Write-Host "  (등록된 Identifier가 없습니다)" -ForegroundColor Gray
        }
        Write-Host "==============================" -ForegroundColor Yellow
        
    }
    catch {
        Write-Error "❌ Identifier 조회 실패: $($_.Exception.Message)"
    }
}

# 메인 실행 로직
Write-Host "=== Relying Party Identifier 추가 스크립트 ===" -ForegroundColor Magenta
Write-Host "대상 Relying Party: $RelyingPartyName" -ForegroundColor White

# 실행 전 현재 상태 확인
Show-CurrentIdentifiers -RPName $RelyingPartyName

# 파라미터에 따라 단일/다수 처리 분기
if ($PSCmdlet.ParameterSetName -eq "Single") {
    Write-Host "`n📝 단일 Identifier 추가 모드" -ForegroundColor Magenta
    Write-Host "추가할 Identifier: $NewIdentifier" -ForegroundColor White
    
    $confirmation = Read-Host "`n위 Identifier를 추가하시겠습니까? (y/N)"
    
    if ($confirmation -eq 'y' -or $confirmation -eq 'Y') {
        $result = Add-SingleIdentifier -RPName $RelyingPartyName -NewIdentifier $NewIdentifier
        
        if ($result) {
            Write-Host "`n🎉 단일 Identifier 추가 완료!" -ForegroundColor Green
            Show-CurrentIdentifiers -RPName $RelyingPartyName
        } else {
            Write-Host "`n💥 단일 Identifier 추가 실패!" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "작업이 취소되었습니다." -ForegroundColor Yellow
    }
}
elseif ($PSCmdlet.ParameterSetName -eq "Multiple") {
    Write-Host "`n📝 다수 Identifier 추가 모드" -ForegroundColor Magenta
    Write-Host "추가할 Identifier 개수: $($NewIdentifiers.Count)" -ForegroundColor White
    
    $confirmation = Read-Host "`n위 $($NewIdentifiers.Count)개 Identifier를 추가하시겠습니까? (y/N)"
    
    if ($confirmation -eq 'y' -or $confirmation -eq 'Y') {
        $result = Add-MultipleIdentifiers -RPName $RelyingPartyName -NewIdentifiers $NewIdentifiers
        
        if ($result) {
            Write-Host "`n🎉 다수 Identifier 추가 완료!" -ForegroundColor Green
            Show-CurrentIdentifiers -RPName $RelyingPartyName
        } else {
            Write-Host "`n💥 다수 Identifier 추가 실패!" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "작업이 취소되었습니다." -ForegroundColor Yellow
    }
}

Write-Host "`n작업이 완료되었습니다." -ForegroundColor Green
```

---

## 📝 2. SAML Assertion Consumer Endpoints 추가

기존 SAML Endpoints를 유지하면서 새로운 Assertion Consumer Endpoints를 추가합니다.
- **Index**: 0부터 순차 증가
- **Binding**: POST 고정
- **Default**: No 고정

### 사용법

```powershell
# 단일 추가
.\Add-SamlEndpoints.ps1 -RelyingPartyName "MyApp" -NewEndpointUri "https://example.com/saml/acs"

# 다수 추가
.\Add-SamlEndpoints.ps1 -RelyingPartyName "MyApp" -NewEndpointUris @("https://example.com/saml/acs", "https://example2.com/saml/acs")
```

### 실행 결과 예시

```
=== 현재 SAML Assertion Consumer Endpoints ===
총 개수: 3
  [1] Index: 0, Binding: POST, Default: No
      URI: https://example.com/saml/acs
  [2] Index: 1, Binding: POST, Default: No  
      URI: https://example2.com/saml/acs
  [3] Index: 2, Binding: POST, Default: No
      URI: https://example3.com/saml/acs
```

---

## 📝 3. Application Groups Web API Identifier 추가

ADFS Application Groups의 "Native Application accessing a Web API" 구조에서 Web API Application의 Identifier를 추가합니다.

### 사용법

```powershell
# 단일 추가
.\Add-AppGroup-WebApiIdentifier.ps1 -ApplicationGroupName "MyNativeApp" -NewIdentifier "https://newapi.example.com"

# 다수 추가  
.\Add-AppGroup-WebApiIdentifier.ps1 -ApplicationGroupName "MyNativeApp" -NewIdentifiers @("https://api1.com", "https://api2.com")
```

### 실행 결과 예시

```
=== Application Group 구조 분석: MyNativeApp ===
Application Group ID: 12345-67890-abcdef
Native Client Applications: 1
  - 이름: MyNativeApp - Native application
    ID: b2c3d4e5...
    Redirect URI: https://ToDoListClient
    
Web API Applications: 1  
  - 이름: MyNativeApp - Web API
    Identifiers: https://localhost:44321/, https://newapi.example.com
    Access Control Policy: Permit everyone
```

---

## 📝 4. Application Groups Native App Redirect URI 추가

ADFS Application Groups의 Native Application에서 Redirect URI를 기존 정보를 유지하면서 추가합니다.

### 사용법

```powershell
# 단일 추가
.\Add-Native-RedirectUri.ps1 -ApplicationGroupName "MyNativeApp" -NewRedirectUri "https://newapp.example.com/callback"

# 다수 추가  
.\Add-Native-RedirectUri.ps1 -ApplicationGroupName "MyNativeApp" -NewRedirectUris @("https://app1.com/callback", "https://app2.com/redirect")
```

### 지원하는 Redirect URI 형식

- **HTTPS**: `https://example.com/callback`
- **HTTP (개발용)**: `http://localhost:3000/callback`  
- **Windows Store Apps**: `ms-app://s-1-15-2-...`
- **Custom Schemes**: `myapp://auth/callback`

---

## 🚀 사용 시 주의사항

### 1. 사전 준비

```powershell
# PowerShell을 관리자 권한으로 실행
# ADFS 서비스가 실행 중인지 확인
Get-Service -Name "adfssrv"

# ADFS 모듈 로드
Import-Module ADFS
```

### 2. 실행 권한

- PowerShell을 **관리자로 실행** 필수
- ADFS 서버에서 직접 실행
- 적절한 ADFS 관리 권한 필요

### 3. 백업 권장

중요한 설정 변경 전에는 ADFS 구성을 백업하는 것을 권장합니다:

```powershell
# ADFS 구성 백업
Export-AdfsConfiguration -Path "C:\Backup\ADFS-Config-$(Get-Date -Format 'yyyyMMdd-HHmmss').xml"
```

---

## 🔧 문제 해결

### ADMIN0083 에러 발생 시

```powershell
# 1. 관리자 권한 확인
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "❌ PowerShell을 '관리자로 실행'하세요!"
}

# 2. ADFS 서비스 상태 확인
Get-Service -Name "adfssrv" | Select-Object Name, Status

# 3. ADFS 모듈 확인
Get-Module -Name ADFS -ListAvailable
```

### 일반적인 해결 방법

1. **PowerShell을 "관리자로 실행"**
2. **ADFS 서비스 시작**: `Start-Service adfssrv`
3. **정확한 이름 사용**: 대소문자 구분
4. **URI 형식 확인**: `https://example.com` 형태
5. **ADFS Management Tools 설치 확인**

---

## 📊 스크립트 실행 흐름

모든 스크립트는 다음과 같은 공통된 실행 흐름을 따릅니다:

```
1. 현재 상태 확인 → 기존 설정 목록 표시
2. 중복 검사 → 이미 존재하는 항목 확인
3. 사용자 확인 → 추가 작업 진행 여부 확인
4. 안전한 추가 → 기존 + 새 항목 합쳐서 적용
5. 결과 확인 → 최종 상태 표시
```

---

## 💡 추가 팁

### PowerShell 프로필에 함수 등록

자주 사용하는 함수들을 PowerShell 프로필에 등록하여 편리하게 사용할 수 있습니다:

```powershell
# PowerShell 프로필 파일 경로 확인
$PROFILE

# 프로필에 간단한 별칭 함수 추가
function Add-RPId($RPName, $Identifier) {
    # 간소화된 Identifier 추가 로직
}

Set-Alias -Name "addid" -Value "Add-RPId"
```

### 배치 처리 예시

여러 환경에 동일한 설정을 적용할 때:

```powershell
$environments = @("Dev", "Staging", "Production")
$identifiers = @("https://api-dev.example.com", "https://api-staging.example.com", "https://api-prod.example.com")

for ($i = 0; $i -lt $environments.Count; $i++) {
    $rpName = "MyApp-$($environments[$i])"
    $identifier = $identifiers[$i]
    # 스크립트 실행
}
```

---

## 📋 요약

이 스크립트 모음집을 사용하면:

- ✅ **안전한 ADFS 관리**: 기존 설정 손실 없이 새 설정 추가
- ✅ **효율성 향상**: 수동 작업을 자동화하여 시간 절약  
- ✅ **일관성 보장**: 표준화된 방식으로 설정 관리
- ✅ **오류 방지**: 중복 및 형식 오류 자동 차단
- ✅ **확장성**: 필요에 따라 추가 기능 구현 가능

ADFS 관리 업무의 효율성과 안정성을 크게 향상시킬 수 있는 도구입니다!

---

## 📞 문의 및 피드백

스크립트 사용 중 문제가 발생하거나 개선 사항이 있으시면 언제든지 피드백 부탁드립니다.

Author: Jongminpark
Date: 2025-09-02
Version: v1.0