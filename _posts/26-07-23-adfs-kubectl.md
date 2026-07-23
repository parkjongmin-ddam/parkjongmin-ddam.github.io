---
layout: single
title: "홈랩 ADFS를 Kubernetes OIDC Provider로 연동하기 — kubeadm 클러스터 구축부터 group 클레임 트러블슈팅까지"
excerpt: "홈랩 ADFS 팜을 Kubernetes API 서버의 OIDC Provider로 붙여 AD 그룹 기반 kubectl 인가를 검증한 기록. kubeadm 싱글노드 클러스터 구축과 Application Group 등록까지는 순조로웠지만, 발급된 ID Token에 group 클레임이 계속 빠지는 문제에 부딪혔다. response_mode 등 여러 가설을 좁혀가다 ADFS Trace 로그로 resource 파라미터 누락이 근본 원인임을 확인하고, RBAC까지 붙여 마무리한다."
date: 2026-07-23
categories: [IAM, Kubernetes]
tags: [adfs, oidc, kubernetes, kubeadm, rbac, kubelogin, group-claim, 트러블슈팅]
---

## 배경

기존 홈랩(azlab.istn.co.kr)에는 2노드 ADFS 팜과 2-Tier PKI가 이미 구축되어 있었다. 이 ADFS를 Kubernetes 클러스터의 OIDC Provider로 붙여서, AD 그룹 기반으로 kubectl 접근을 통제할 수 있는지 검증했다. IAM 엔지니어 입장에서 흥미로웠던 지점은, 인증(Authentication) 자체는 비교적 빠르게 됐는데 인가(Authorization)에 필요한 `group` 클레임을 ID Token에 실리게 하는 과정에서 ADFS 특유의 동작 방식 때문에 단계별로 원인을 하나씩 좁혀가며 검증해야 했다는 점이다. 이 글은 그 검증 과정을 순서대로 기록한다.

## 환경

- Hyper-V VM: Ubuntu 24.04 LTS, kubeadm 기반 싱글노드 클러스터
- ADFS: 기존 azlab 홈랩의 2노드 팜 (`sts.azlab.istn.co.kr`, PKI는 자체 ISCA01 발급)
- 클라이언트: Windows PowerShell + kubectl + krew + kubelogin(`oidc-login` 플러그인)

## 1. kubeadm 클러스터 구축

Ubuntu Server 설치 후 기본적인 순서로 진행했다.

![Hyper-V 펌웨어 — 부팅 순서를 DVD 드라이브 우선으로 변경](/assets/images/26-07-23-adfs-kubectl/01-hyperv-boot-order-dvd-first.png)

![Hyper-V 보안 — 보안 부팅 사용, 템플릿은 Microsoft UEFI 인증 기관](/assets/images/26-07-23-adfs-kubectl/02-hyperv-secureboot-ms-uefi-ca.png)

![설치 언어 선택 — English](/assets/images/26-07-23-adfs-kubectl/03-installer-language-english.png)

![설치 기반 선택 — Ubuntu Server](/assets/images/26-07-23-adfs-kubectl/04-choose-ubuntu-server.png)

![키보드 레이아웃 — English (US)](/assets/images/26-07-23-adfs-kubectl/05-keyboard-layout-en-us.png)

![네트워크 설정 — eth0 DHCPv4](/assets/images/26-07-23-adfs-kubectl/06-network-dhcpv4.png)

![Ubuntu archive mirror 테스트 통과](/assets/images/26-07-23-adfs-kubectl/07-archive-mirror-test-passed.png)

![스토리지 설정 — 디스크 전체 사용 + LVM](/assets/images/26-07-23-adfs-kubectl/08-storage-use-entire-disk.png)

![스토리지 설정 — 파일시스템 요약(/, /boot, /boot/efi)](/assets/images/26-07-23-adfs-kubectl/09-storage-filesystem-summary.png)

![프로필 설정 — 사용자명/호스트명/비밀번호](/assets/images/26-07-23-adfs-kubectl/10-profile-configuration.png)

![SSH 설정 — OpenSSH server 설치](/assets/images/26-07-23-adfs-kubectl/11-ssh-install-openssh-server.png)

![설치 완료 후 Reboot](/assets/images/26-07-23-adfs-kubectl/12-installation-complete-reboot.png)

```bash
# containerd 설치 및 cgroup 드라이버를 systemd로 설정
sudo apt install -y containerd
containerd config default | sudo tee /etc/containerd/config.toml
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl restart containerd

# 커널 모듈 및 네트워크 설정
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF
sudo modprobe overlay
sudo modprobe br_netfilter

cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF
sudo sysctl --system

# kubeadm/kubelet/kubectl 설치
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.31/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.31/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt install -y kubelet kubeadm kubectl
```

```bash
sudo kubeadm init --pod-network-cidr=10.244.0.0/16
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
kubectl taint nodes --all node-role.kubernetes.io/control-plane-
kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml
```

![kubeadm init 성공 — join 토큰 발급](/assets/images/26-07-23-adfs-kubectl/13-kubeadm-init-success.png)

kubeadm으로 생성한 control-plane 노드에는 기본적으로 `node-role.kubernetes.io/control-plane` taint가 걸려 있어서, 일반 워크로드 Pod가 스케줄링되지 않는다. 보통은 워커 노드를 별도로 붙여서 워크로드를 그쪽으로 분리하는데, 이번 구성은 노드가 1대뿐인 싱글노드 클러스터라 taint를 그대로 두면 Pod를 아예 띄울 수 없다. 그래서 taint를 제거해 control-plane 노드에도 Pod가 스케줄링되도록 허용했고, flannel CNI를 올려서 `kubectl get nodes`가 `Ready`로 뜨는 것까지 확인했다.

## 2. ADFS Application Group 등록

ADFS 관리 콘솔에서 Application Group 마법사로 "Native application accessing a web API" 템플릿을 선택해 등록했다.

- Native Application: Redirect URI `http://localhost:8000` (kubelogin의 기본 콜백 포트)
- Web API: Access control policy는 "Permit everyone"
- Issuance Transform Rule: `Token-Groups - Unqualified Names` → Outgoing Claim Type `group`

## 3. K8s API 서버 OIDC 설정

`/etc/kubernetes/manifests/kube-apiserver.yaml`에 다음을 추가했다.

```yaml
- --oidc-issuer-url=https://sts.azlab.istn.co.kr/adfs
- --oidc-client-id=f7e390fb-a388-4257-893c-7415dd45a72a
- --oidc-username-claim=upn
- --oidc-groups-claim=group
- --oidc-ca-file=/etc/kubernetes/pki/adfs-ca.pem
```

### TLS 인증서 신뢰

```
oidc authenticator: initializing plugin: ... tls: failed to verify certificate: x509: certificate signed by unknown authority
```

ADFS 인증서가 자체 PKI(ISCA01)로 발급된 것이라 API 서버가 기본적으로 신뢰하지 못했다. 서버 체인을 추출해서 `--oidc-ca-file`로 지정해 해결했다.

```bash
echo | openssl s_client -connect sts.azlab.istn.co.kr:443 -showcerts 2>/dev/null | \
  sed -n '/-----BEGIN CERTIFICATE-----/,/-----END CERTIFICATE-----/p' > /etc/kubernetes/pki/adfs-ca.pem
```

## 4. kubelogin(kubectl oidc-login) 설정

Windows에 krew, kubelogin 플러그인을 설치하고 kubeconfig에 OIDC exec credential을 등록했다.

```powershell
kubectl config set-credentials jongmin-oidc `
  --exec-api-version=client.authentication.k8s.io/v1beta1 `
  --exec-command=kubectl `
  --exec-arg=oidc-login `
  --exec-arg=get-token `
  --exec-arg=--oidc-issuer-url=https://sts.azlab.istn.co.kr/adfs `
  --exec-arg=--oidc-client-id=f7e390fb-a388-4257-893c-7415dd45a72a `
  --exec-arg=--oidc-extra-scope=allatclaims `
  --exec-arg="--oidc-auth-request-extra-params=resource=https://localhost:8000" `
  --exec-arg=--insecure-skip-tls-verify
```

여기까지는 비교적 정석적인 흐름이었다. 문제는 여기서부터였다.

## 5. group 클레임이 계속 빠지는 문제

인증 자체는 성공했다. 로그인하면 `Authenticated` 화면이 뜨고, API 서버도 사용자를 정상적으로 식별했다.

```
Error from server (Forbidden): pods is forbidden: User "https://sts.azlab.istn.co.kr/adfs#jongmin.park@azlab.istn.co.kr" cannot list resource "pods"
```

문제는 발급된 ID Token의 payload에 `group` 필드 자체가 없었다는 것이다.

```json
{
  "aud": "f7e390fb-...",
  "iss": "https://sts.azlab.istn.co.kr/adfs",
  "sub": "...",
  "upn": "jongmin.park@azlab.istn.co.kr",
  "unique_name": "AZLAB\\jongmin.park"
}
```

Issuance Transform Rule은 분명히 설정했는데 클레임이 안 실렸다. 이 시점부터 여러 가설을 순서대로 검증했다.

### 시도 1 — response_mode

Microsoft 공식 문서(AD FS OpenID Connect/OAuth concepts)에는 ID Token에 커스텀 클레임을 추가하는 두 가지 옵션이 나온다.

> Option 2: 웹앱이 접근하려는 리소스가 있고 ID Token으로 추가 클레임을 전달해야 하는 경우 사용. `response_mode`가 `form_post`로 설정되어야 하고, `allatclaims` scope가 client-RP 쌍에 할당되어야 한다.

kubelogin은 `response_mode`를 지정하는 옵션이 없어서, `--oidc-auth-request-extra-params=response_mode=form_post`로 강제 주입을 시도했다. 그런데 `form_post`는 브라우저가 GET 리다이렉트가 아니라 HTML 폼을 통한 POST로 콜백을 보내는 방식이라, kubelogin의 로컬 콜백 서버가 POST 요청 자체를 처리하지 못해 `404 page not found`가 떴다. 이 경로는 막다른 길이었다.

### 근본 원인 — resource 파라미터 누락

원인을 찾기 위해 ADFS Tracing/Debug 로그를 활성화해서 실제 토큰 발급 로그를 직접 확인했다.

```powershell
Set-AdfsProperties -AuditLevel Verbose
wevtutil sl "AD FS Tracing/Debug" /e:true
```

로그에 결정적인 문구가 있었다.

```
An Access Token was successfully issued to client: 'f7e390fb-...' 
with redirectUri: 'http://localhost:8000' for resource 'urn:microsoft:userinfo'.
```

`resource` 파라미터가 요청에 없으면 ADFS는 우리가 만든 Web API가 아니라 **기본 폴백 리소스(`urn:microsoft:userinfo`)로 토큰을 발급한다.** 이 폴백 리소스는 발급 정책(Issuance Transform Rules)을 커스터마이징할 수 없는 별도 경로다. Application Group을 "Native application accessing a web API" 템플릿으로 등록하면 클라이언트가 그 Web API에 대한 토큰을 요청할 수 있는 권한 관계는 설정되지만, 이는 어디까지나 "요청 시 허용되는 대상"을 정의하는 것이지 매 인증 요청에서 실제로 어떤 리소스를 대상으로 할지는 별개다. 클라이언트가 `resource` 파라미터로 명시하지 않으면, 권한 관계와 무관하게 기본 폴백 리소스로 처리된다. 지금까지 Web API 쪽 설정을 아무리 손봐도 반영이 안 됐던 이유가 이거였다 — 권한은 맞게 설정돼 있었지만, kubelogin이 보내는 인증 요청 자체가 그 Web API를 지목하고 있지 않았다.

kubelogin에 `resource` 파라미터를 강제로 추가했다.

```powershell
--exec-arg="--oidc-auth-request-extra-params=resource=https://localhost:8000"
```

(`https://localhost:8000`은 Web API의 Relying Party Identifier 값이다. Native Application 등록 시 자동으로 이 값이 같이 생성되어 있었다.)

이후 발급된 토큰:

```json
{
  "aud": "f7e390fb-...",
  "iss": "https://sts.azlab.istn.co.kr/adfs",
  "upn": "jongmin.park",
  "group": ["Domain Users", "k8s-admins"],
  "appid": "f7e390fb-...",
  "apptype": "Public",
  "scp": "openid allatclaims"
}
```

`group` 클레임이 정상적으로 실렸다.

![디코딩한 ID Token — group 클레임에 Domain Users, k8s-admins 포함](/assets/images/26-07-23-adfs-kubectl/17-id-token-group-claim-decoded.png)

## 6. RBAC 적용 및 최종 확인

토큰에 실린 `k8s-admins`는 AD에 미리 만들어 둔 보안 그룹이다. ADUC에서 사용자를 만들고, 전역 보안 그룹으로 `k8s-admins`를 만든 뒤, 여기에 사용자를 멤버로 추가했다.

![Active Directory 사용자 및 컴퓨터 — 새 사용자 생성](/assets/images/26-07-23-adfs-kubectl/14-aduc-new-user.png)

![새 개체 - 그룹 — k8s-admins, 전역/보안 그룹으로 생성](/assets/images/26-07-23-adfs-kubectl/15-aduc-new-group-k8s-admins.png)

![k8s-admins 속성 — 멤버 탭에 jongmin park 추가](/assets/images/26-07-23-adfs-kubectl/16-k8s-admins-group-members.png)

```bash
kubectl create -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: adfs-group-binding
subjects:
- kind: Group
  name: k8s-admins
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: cluster-admin
  apiGroup: rbac.authorization.k8s.io
EOF
```

```powershell
kubectl get pods -A
```

`k8s-admins` AD 그룹에 속한 사용자로 정상적으로 클러스터 리소스를 조회할 수 있었다.

## 정리

| 문제 | 원인 | 해결 |
|---|---|---|
| TLS 인증서 거부 | 자체 PKI 인증서 미신뢰 | `--oidc-ca-file`로 CA 체인 지정 |
| group 클레임 누락 | `resource` 파라미터 미지정 → 기본 폴백 리소스로 발급 | `--oidc-auth-request-extra-params=resource=<Web API Identifier>` 명시 |

가장 시간이 오래 걸린 부분은 마지막 `resource` 파라미터 문제였다. `response_mode`까지 확인해봐도 안 됐던 이유가, Application Group에서 설정한 건 클라이언트-리소스 권한 관계였을 뿐 실제 인증 요청에 그 리소스를 지목하는 `resource` 파라미터가 빠져 있었기 때문이다. Postman으로 사내 ADFS 연동을 테스트해본 경험상 `resource`는 항상 명시해야 하는 파라미터였는데, 이번 kubelogin 연동에서는 그 파라미터가 기본값으로 빠져 있다는 걸 놓치고 있었다. ADFS Trace 로그로 실제 발급 대상 리소스를 직접 확인하고 나서야 원인이 명확해졌다. OIDC 연동 트러블슈팅에서는 클레임 매핑 규칙보다 먼저, **토큰이 실제로 어느 리소스를 대상으로 발급되고 있는지**부터 확인하는 게 우선이라는 걸 이번에 다시 확인했다.
