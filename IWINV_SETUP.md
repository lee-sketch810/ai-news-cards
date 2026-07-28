# iwinv 서버로 사이트 이전 — 콘솔 설정 가이드

목표: 지금 GitHub Pages가 서빙하는 `public/` 폴더(정적 사이트)를 iwinv 서버에서 직접 서빙하도록 바꾼다.
이 문서는 **iwinv 콘솔/서버에서 직접 하는 작업**만 다룬다. 로컬 PC 쪽 자동 배포 스크립트는 이 설정이 끝난 뒤 별도로 준비한다.

---

## 0. 준비물 확인

iwinv 콘솔(https://console.iwinv.kr) 로그인 후 서버 상세 페이지에서 아래 정보를 확인해 둔다.

- **공인 IP 주소** (예: 123.45.67.89)
- **OS 종류** — Ubuntu/Debian 계열인지 CentOS/Rocky/AlmaLinux 계열인지 (서버 생성 시 선택한 이미지에 표시됨)
- **root 접속 정보** — 서버 생성 시 이메일로 발송되었거나, 콘솔의 "서버 정보 → 루트 비밀번호 확인"에서 조회 가능

OS 종류에 따라 아래 3~4단계 명령어가 다르다. 모르면 콘솔의 "서버 정보"나 "이미지명"을 확인하면 된다(Ubuntu 22.04 / Rocky Linux 9 등으로 표기됨).

---

## 1. 방화벽(ACG/보안그룹) — 80·443 포트 열기

iwinv는 서버 자체 방화벽과 별개로 콘솔에서 **ACG(Access Control Group, 접근제어그룹)** 를 설정해야 외부에서 접속이 가능하다.

1. 콘솔 → 서버 관리 → 해당 서버 선택 → **ACG(방화벽) 설정**
2. 인바운드 규칙에 아래 두 개 추가:
   - TCP 22 (SSH) — 본인 IP만 허용 권장 (전체 허용도 가능하지만 보안상 비권장)
   - TCP 80 (HTTP) — 전체 허용(0.0.0.0/0)
   - TCP 443 (HTTPS) — 전체 허용(0.0.0.0/0), HTTPS 쓸 경우
3. 적용 후 반영까지 1~2분 소요될 수 있음

---

## 2. SSH 접속

Windows 11/10(2019년 이후 빌드)은 OpenSSH 클라이언트가 기본 내장되어 있어 PowerShell에서 바로 접속 가능:

```powershell
ssh root@<서버_공인_IP>
```

처음 접속 시 "authenticity of host... continue connecting?" 물으면 `yes` 입력. 이후 비밀번호를 물으면 iwinv에서 발급받은 root 비밀번호 입력.

---

## 3. 웹서버(nginx) 설치

서버에 SSH로 접속한 상태에서 진행.

**Ubuntu / Debian 계열:**
```bash
apt update && apt install -y nginx
systemctl enable --now nginx
```

**CentOS / Rocky / AlmaLinux 계열:**
```bash
dnf install -y nginx
systemctl enable --now nginx
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload
```

설치 후 브라우저에서 `http://<서버_IP>` 접속 시 nginx 기본 환영 페이지가 뜨면 정상.

---

## 4. 사이트 폴더 만들기

```bash
mkdir -p /var/www/ai-news-cards
chown -R $(whoami):$(whoami) /var/www/ai-news-cards
```

---

## 5. nginx 사이트 설정

**Ubuntu/Debian:**
```bash
cat > /etc/nginx/sites-available/ai-news-cards <<'EOF'
server {
    listen 80;
    server_name _;
    root /var/www/ai-news-cards;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    location /data/ {
        add_header Cache-Control "no-cache";
    }
}
EOF
ln -sf /etc/nginx/sites-available/ai-news-cards /etc/nginx/sites-enabled/ai-news-cards
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

**CentOS/Rocky/AlmaLinux** (sites-available 구조가 없으므로 conf.d 사용):
```bash
cat > /etc/nginx/conf.d/ai-news-cards.conf <<'EOF'
server {
    listen 80;
    server_name _;
    root /var/www/ai-news-cards;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
EOF
nginx -t && systemctl reload nginx
```

---

## 6. (선택) 도메인 연결 + HTTPS

커스텀 도메인이 있다면:

1. 도메인 DNS의 A 레코드를 서버 공인 IP로 설정 (예: `news.내도메인.com → 123.45.67.89`)
2. 위 nginx 설정의 `server_name _;` 를 `server_name news.내도메인.com;` 로 변경 후 `nginx -t && systemctl reload nginx`
3. HTTPS 발급 (Let's Encrypt):

```bash
# Ubuntu/Debian
apt install -y certbot python3-certbot-nginx
certbot --nginx -d news.내도메인.com

# CentOS/Rocky
dnf install -y certbot python3-certbot-nginx
certbot --nginx -d news.내도메인.com
```

도메인이 없으면 이 단계는 건너뛰고 `http://<서버_IP>` 로 접속하면 된다.

---

## 7. 로컬 PC → 서버 자동 업로드용 SSH 키 등록 (무인 배포에 필수)

지금까지는 사람이 비밀번호로 접속했지만, 매일 자동 배포하려면 **비밀번호 없이** 접속되는 SSH 키가 필요하다.

**Windows PC(이 저장소가 있는 PC)에서:**
```powershell
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\iwinv_deploy" -N '""'
```
(암호 없이 키 생성 — 자동화 스크립트가 매번 비밀번호를 못 넣으므로 필수)

생성된 공개키 내용 출력:
```powershell
Get-Content "$env:USERPROFILE\.ssh\iwinv_deploy.pub"
```

**서버(iwinv)에서:**
```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo "<위에서_출력된_공개키_전체를_여기에_붙여넣기>" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

이후 Windows PC에서 아래처럼 비밀번호 없이 접속되면 성공:
```powershell
ssh -i "$env:USERPROFILE\.ssh\iwinv_deploy" root@<서버_IP>
```

---

## 8. 여기까지 끝나면 알려주세요

아래 4가지를 알려주시면 자동 배포 스크립트(`deploy_to_iwinv.bat`)를 완성해서 GitHub push 대신 iwinv로 매일 자동 업로드하도록 바꿔드립니다.

1. 서버 공인 IP
2. SSH 접속 계정 (보통 `root`)
3. 웹 루트 경로 (위 가이드대로면 `/var/www/ai-news-cards`)
4. 도메인을 연결했다면 그 도메인 주소 (없으면 "없음")
