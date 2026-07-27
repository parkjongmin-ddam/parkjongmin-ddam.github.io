---
title: "홈랩 ADFS + Kubernetes 연동 — OIDC 인증부터 cert-manager PKI 자동화, Namespace RBAC까지"
categories: [IAM, Kubernetes]
tags: [ADFS, OIDC, Kubernetes, kubeadm, RBAC, kubelogin, cert-manager, PKI]
---

## 배경

기존 홈랩(azlab.istn.co.kr)에는 2노드 ADFS 팜과 2-Tier PKI가 이미 구축되어 있었다. 이 ADFS를 Kubernetes 클러스터의 OIDC Provider로 붙여서, AD 그룹 기반으로 kubectl 접근을 통제할 수 있는지 검증했다. IAM 엔지니어 입장에서 흥미로웠던 지점은, 인증(Authentication) 자체는 비교적 빠르게 됐는데 인가(Authorization)에 필요한 `group` 클레임을 ID Token에 실리게 하는 과정에서 ADFS 특유의 동작 방식 때문에 단계별로 원인을 하나씩 좁혀가며 검증해야 했다는 점이다. OIDC 연동 이후에는 클러스터를 멀티노드로 확장하고, azlab PKI 하위에 K8s 전용 발급 CA를 구성해 Ingress TLS를 자동화했으며, Namespace 단위로 RBAC을 세분화하는 것까지 이어갔다. 이 글은 그 검증 과정을 순서대로 기록한다.

## 환경

- Hyper-V VM: Ubuntu 24.04 LTS, kubeadm 기반 싱글노드 클러스터
- ADFS: 기존 azlab 홈랩의 2노드 팜 (`sts.azlab.istn.co.kr`, PKI는 자체 ISCA01 발급)
- 클라이언트: Windows PowerShell + kubectl + krew + kubelogin(`oidc-login` 플러그인)

## 1. kubeadm 클러스터 구축

Ubuntu Server 설치 후 기본적인 순서로 진행했다.

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

## 6. RBAC 적용 및 최종 확인

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

## 7. 멀티노드 확장과 Ingress

싱글노드 클러스터에 워커 노드(`k8s-node02`)를 `kubeadm join`으로 추가해 2노드 구성으로 확장했다. 두 노드 모두 DHCP 대신 고정 IP로 전환했는데, 이는 뒤에서 겪은 문제 때문에 뒤늦게 되짚어 적용한 조치다 — DHCP 임대가 갱신되면서 control-plane 노드의 IP가 바뀌자, etcd/kube-apiserver가 매니페스트에 하드코딩된 옛 IP(`--listen-peer-urls` 등)로 바인딩을 계속 시도하다 실패하는 문제가 발생했다.

```
listen tcp 192.168.219.117:2380: bind: cannot assign requested address
```

IP를 원래 값으로 고정하고 kubelet을 재시작하자 정상화됐다. 이후 두 노드 모두 netplan에 고정 IP를 명시해 재발을 막았다.

베어메탈(온프레미스) 환경이라 클라우드 LoadBalancer가 없으므로, `nginx-ingress-controller`를 NodePort 방식으로 배포했다.

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.11.3/deploy/static/provider/baremetal/deploy.yaml
```

테스트용 Deployment/Service/Ingress를 배포해 도메인 기반 라우팅(`hello.azlab.istn.co.kr` → NodePort → Ingress → Service → Pod)이 정상 동작하는 것까지 확인했다.

![NodePort 경유 Ingress 라우팅으로 hello-world 서비스 접근 확인](/assets/images/26-07-27-adfs-kubernates-oidc/ingress-test-success.png)

## 8. cert-manager로 PKI 자동화

Ingress에 자동으로 TLS를 붙이기 위해 cert-manager를 도입했다. azlab의 CA(ISCA01)는 Windows AD CS 기반인데, 먼저 ACME 지원 여부를 확인했다.

```powershell
Get-WindowsFeature | Where-Object {$_.Name -like "ADCS*"}
```

![ADCS 역할 설치 상태 확인 — Certification Authority만 Installed](/assets/images/26-07-27-adfs-kubernates-oidc/adcs-role-check.png)

![ADCS-ACME 서비스 별도 확인](/assets/images/26-07-27-adfs-kubernates-oidc/acme-service-check.png)

`ADCS-ACME` 역할 서비스가 설치되어 있지 않아 ACME는 미지원으로 확인됐다. 대신 azlab ISCA01 하위에 K8s 클러스터 전용 하위 CA(`k8s-issuing-ca`)를 별도로 발급하고, 그 CA의 인증서와 개인키를 cert-manager의 `ClusterIssuer(type: ca)`에 등록하는 방식으로 진행했다. 루트/상위 CA의 키를 직접 K8s에 넣는 대신 전용 하위 CA를 분리한 것은, 키 유출 시 영향 범위를 제한하기 위해서다.

![CA 서버 내 SubCA 템플릿 존재 여부 확인 (certutil -CATemplates)](/assets/images/26-07-27-adfs-kubernates-oidc/ca-templates-check.png)

```powershell
# ISCA01에서 SubCA 템플릿으로 CSR 생성 및 제출
certreq -new request.inf request.req
certreq -submit -attrib "CertificateTemplate:SubCA" request.req cert.cer
certreq -accept cert.cer
```

![request.inf 작성 및 certreq -new로 CSR 생성](/assets/images/26-07-27-adfs-kubernates-oidc/csr-request-create.png)

![certreq -submit으로 ISCA01에 SubCA 발급 요청 제출](/assets/images/26-07-27-adfs-kubernates-oidc/ca-submit-subca.png)

![SubCA 인증서 발급 성공 (Certificate retrieved(Issued))](/assets/images/26-07-27-adfs-kubernates-oidc/cert-issue-success.png)

![certreq -accept로 발급받은 인증서 설치](/assets/images/26-07-27-adfs-kubernates-oidc/cert-install-accept.png)

![로컬 인증서 저장소에 설치된 k8s-issuing-ca Thumbprint 확인](/assets/images/26-07-27-adfs-kubernates-oidc/cert-thumbprint-check.png)

발급받은 인증서를 PFX로 export한 뒤 K8s로 옮겨 PEM으로 분리하고, Secret으로 등록했다.

![Export-PfxCertificate로 k8s-issuing-ca 인증서 반출](/assets/images/26-07-27-adfs-kubernates-oidc/cert-export-pfx.png)

```bash
openssl pkcs12 -in k8s-issuing-ca.pfx -clcerts -nokeys -out ca.crt -passin pass:xxx
openssl pkcs12 -in k8s-issuing-ca.pfx -nocerts -nodes -out ca.key -passin pass:xxx
kubectl create secret tls k8s-issuing-ca-secret --cert=ca.crt --key=ca.key -n cert-manager
```

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: azlab-ca-issuer
spec:
  ca:
    secretName: k8s-issuing-ca-secret
```

Ingress에 `cert-manager.io/cluster-issuer` annotation과 `tls` 섹션을 추가하자, cert-manager가 자동으로 `Certificate` 리소스를 만들고 몇 초 안에 서명까지 완료했다. 여기까지는 순조로웠는데, 브라우저로 접속하면 계속 `NET::ERR_CERT_AUTHORITY_INVALID`가 떴다.

![k8s 노드의 Ingress에 인증서 설치 후 https 접속 시 브라우저 인증서 경고 발생](/assets/images/26-07-27-adfs-kubernates-oidc/https-cert-warning.png)

### 신뢰 체인 디버깅

인증서 자체(SAN, 체인 구성)는 여러 차례 확인해도 문제가 없었다. `openssl s_client`로 서버가 실제로 보내는 체인을 직접 받아서 Windows `certutil -verify`로 검증한 결과, 처음에는 인증서 1개(leaf)만 확인됐다.

```
Missing Issuer: CN=k8s-issuing-ca, ...
인증서 체인을 신뢰된 최상위 인증 기관에 만들 수 없습니다.
```

nginx-ingress-controller를 재시작하자 Secret이 다시 읽히면서 leaf + 중간 CA 2개가 정상적으로 전송되기 시작했다(단순 캐싱 지연이었다). 그런데도 브라우저 경고는 그대로였다. 다음으로 확인한 것은 클라이언트(도메인 조인된 테스트 VM)의 로컬 인증서 저장소였는데, `Cert:\LocalMachine\CA`에는 `k8s-issuing-ca`와 `azlab-ISCA01-CA`가 이미 존재했다. 그런데도 실패했다.

결정적 단서는 GPO 저장소를 별도로 확인하면서 나왔다.

```powershell
certutil -verifystore -GroupPolicy CA
certutil -verifystore -GroupPolicy Root
```

`GroupPolicy Root` 저장소가 완전히 비어 있었다. 로컬 저장소에 보이던 `azlab-ISCA01-CA`, `azlab-ROOTCA-CA`는 GPO가 아니라 다른 경로(도메인 조인 시 초기 배포 등)로 들어가 있던 것이었고, 실제 TLS 체인 검증에 쓰이는 GPO 관리 저장소 기준으로는 `k8s-issuing-ca`보다 상위 체인이 전혀 등록되어 있지 않았다. 즉 GPO가 재적용될 때마다 "GPO가 관리하지 않는" 상위 인증서가 함께 정리되는 것으로 보였다.

해결은 ROOTCA, ISCA01, k8s-issuing-ca 세 인증서 전부를 하나의 GPO에 명시적으로 등록하는 것이었다.

![Group Policy Management 콘솔에서 신뢰 인증서 등록 진행](/assets/images/26-07-27-adfs-kubernates-oidc/gpo-management-console.png)

![도메인에 새 GPO 생성 및 링크](/assets/images/26-07-27-adfs-kubernates-oidc/gpo-create.png)

![생성한 GPO Edit 진입](/assets/images/26-07-27-adfs-kubernates-oidc/gpo-edit.png)

![GPO의 Intermediate Certification Authorities에 k8s-issuing-ca 인증서 import 완료](/assets/images/26-07-27-adfs-kubernates-oidc/gpo-cert-import.png)

```
Computer Configuration → Policies → Windows Settings → Security Settings → Public Key Policies
  → Trusted Root Certification Authorities : azlab-ROOTCA-CA
  → Intermediate Certification Authorities : azlab-ISCA01-CA, k8s-issuing-ca
```

`gpupdate /force` 후 재확인하자 `GroupPolicy Root`/`GroupPolicy CA` 양쪽에 전체 체인이 나타났고, 브라우저에서도 경고 없이 정상 접속됐다.

## 9. Namespace 단위 RBAC 세분화

기존에는 `k8s-admins` 그룹에 `cluster-admin` ClusterRole을 매핑해 전체 권한을 부여하는 구조였다. 이를 Namespace 단위로 나눠, 특정 그룹은 특정 Namespace에서 제한된 동작만 하도록 세분화했다.

![AD에서 새 보안 그룹 생성 메뉴 진입](/assets/images/26-07-27-adfs-kubernates-oidc/ad-group-new-menu.png)

![k8s-dev 보안 그룹 생성 (Global/Security)](/assets/images/26-07-27-adfs-kubernates-oidc/ad-group-k8s-dev-create.png)

```bash
kubectl create namespace dev
kubectl create namespace prod
```

![kubectl create namespace로 dev/prod 네임스페이스 생성](/assets/images/26-07-27-adfs-kubernates-oidc/namespace-create.png)

![dev/prod 네임스페이스 생성 확인](/assets/images/26-07-27-adfs-kubernates-oidc/namespace-verify.png)

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: dev-viewer
  namespace: dev
rules:
- apiGroups: ["", "apps"]
  resources: ["pods", "services", "deployments", "replicasets"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: k8s-dev-binding
  namespace: dev
subjects:
- kind: Group
  name: k8s-dev
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: dev-viewer
  apiGroup: rbac.authorization.k8s.io
```

![kubectl apply로 dev-viewer Role과 k8s-dev-binding RoleBinding 배포 완료](/assets/images/26-07-27-adfs-kubernates-oidc/rbac-apply-result.png)

`ClusterRole`이 아니라 `Role` + `namespace` 필드로 스코프를 특정 Namespace에 한정했다. 검증은 기존 관리자 계정이 아니라 `k8s-dev` 그룹에만 속한 별도 테스트 계정(`test.dev`)으로 진행했는데, 관리자 계정으로 테스트하면 이미 `cluster-admin` 권한이 있어 격리 여부를 제대로 확인할 수 없기 때문이다.

```json
{
  "upn": "test.dev",
  "group": ["Domain Users", "k8s-dev"]
}
```

이 토큰으로:

```
kubectl get pods -n dev   → 성공
kubectl get pods -n prod  → Forbidden
kubectl get pods -A       → Forbidden
```

`dev` Namespace에서만 조회가 허용되고, `prod`나 클러스터 전체 조회는 명시적으로 거부되는 것을 확인했다.



| 문제 | 원인 | 해결 |
|---|---|---|
| TLS 인증서 거부 (API 서버) | 자체 PKI 인증서 미신뢰 | `--oidc-ca-file`로 CA 체인 지정 |
| group 클레임 누락 | `resource` 파라미터 미지정 → 기본 폴백 리소스로 발급 | `--oidc-auth-request-extra-params=resource=<Web API Identifier>` 명시 |
| etcd/apiserver 재시작 실패 | DHCP IP 변경으로 매니페스트의 정적 바인딩 주소와 불일치 | 클러스터 노드 고정 IP로 전환 |
| Ingress TLS 브라우저 경고 | GPO가 관리하지 않는 상위 CA가 gpupdate 시 정리됨 | ROOTCA·중간 CA·발급 CA 전체를 하나의 GPO에 명시적으로 등록 |

가장 시간이 오래 걸린 부분은 두 군데였다. 하나는 `resource` 파라미터 문제로, `response_mode`까지 확인해봐도 안 됐던 이유가 Application Group에서 설정한 건 클라이언트-리소스 권한 관계였을 뿐 실제 인증 요청에 그 리소스를 지목하는 `resource` 파라미터가 빠져 있었기 때문이다. Postman으로 사내 ADFS 연동을 테스트해본 경험상 `resource`는 항상 명시해야 하는 파라미터였는데, 이번 kubelogin 연동에서는 그 파라미터가 기본값으로 빠져 있다는 걸 놓치고 있었다. ADFS Trace 로그로 실제 발급 대상 리소스를 직접 확인하고 나서야 원인이 명확해졌다.

다른 하나는 cert-manager 신뢰 체인 문제로, 로컬 인증서 저장소에 상위 CA가 보이는 것과 GPO가 실제로 관리하는 저장소는 별개라는 점을 놓치고 있었다. `certutil -verifystore -GroupPolicy`로 GPO 관리 저장소를 직접 들여다보고 나서야 상위 체인이 통째로 비어 있다는 걸 확인할 수 있었다.

두 사례 모두 공통적으로, 겉으로 보이는 설정(클레임 매핑 규칙, 로컬 인증서 존재 여부)보다 먼저 **실제로 서버가 무엇을 대상으로 처리하고 있는지, 어느 저장소를 기준으로 검증하는지**부터 확인하는 게 우선이라는 걸 이번에 다시 확인했다.