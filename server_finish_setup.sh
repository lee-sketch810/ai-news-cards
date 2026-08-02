#!/usr/bin/env bash
# ============================================================
# ai-news-cards : 서버 쪽 마무리 설정 (1회 실행)
# iwinv 서버(root)에 SSH로 접속한 상태에서 이 스크립트를 붙여넣어 실행하세요.
#
#   ssh root@49.247.137.87
#   nano finish.sh   (이 내용을 붙여넣고 저장) 후:
#   bash finish.sh
#
# 이미 DNS(ai-news.wiselab.kr)와 certbot 인증서 발급은 끝난 상태를
# 전제로 한다. nginx가 아직 설치 안 됐으면 먼저 설치한다.
# ============================================================
set -e

DOMAIN="ai-news.wiselab.kr"
WEBROOT="/var/www/ai-news-cards"
DEPLOY_PUBKEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOobzpdy8tZyz0MYkCWvHK2Gq3FVT2T/pNQjs8ZAMEOx ai-news-cards-deploy"

echo "== 0) 무인 배포용 SSH 공개키 등록 =="
mkdir -p ~/.ssh && chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
if ! grep -qF "ai-news-cards-deploy" ~/.ssh/authorized_keys; then
  echo "$DEPLOY_PUBKEY" >> ~/.ssh/authorized_keys
  echo "  deploy 공개키 추가함"
else
  echo "  이미 등록되어 있음 (스킵)"
fi
chmod 600 ~/.ssh/authorized_keys

echo "== 0.5) OS 방화벽에서 80/443 허용 (ufw/firewalld가 있는 경우) =="
if command -v ufw >/dev/null 2>&1; then
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
fi
if command -v firewall-cmd >/dev/null 2>&1; then
  firewall-cmd --permanent --add-service=http || true
  firewall-cmd --permanent --add-service=https || true
  firewall-cmd --reload || true
fi

echo "== 1) nginx 설치 확인 =="
if ! command -v nginx >/dev/null 2>&1; then
  apt update && apt install -y nginx
fi
systemctl enable --now nginx

echo "== 2) 웹 루트 생성 =="
mkdir -p "$WEBROOT"
chown -R root:root "$WEBROOT"

echo "== 3) 임시 플레이스홀더 페이지 (배포 전 확인용) =="
if [ ! -f "$WEBROOT/index.html" ]; then
  cat > "$WEBROOT/index.html" <<'EOF'
<!doctype html><html><head><meta charset="utf-8"><title>ai-news-cards</title></head>
<body style="font-family:sans-serif;padding:40px"><h1>ai-news-cards</h1>
<p>서버 설정 완료. 첫 배포를 기다리는 중입니다.</p></body></html>
EOF
fi

echo "== 4) nginx 사이트 설정 =="
CERT_DIR="/etc/letsencrypt/live/$DOMAIN"
if [ -f "$CERT_DIR/fullchain.pem" ]; then
  echo "  certbot 인증서 발견 -> HTTPS 설정 포함"
  cat > /etc/nginx/sites-available/ai-news-cards <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate     $CERT_DIR/fullchain.pem;
    ssl_certificate_key $CERT_DIR/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    root $WEBROOT;
    index index.html;

    location / {
        try_files \$uri \$uri/ =404;
    }

    location /data/ {
        add_header Cache-Control "no-cache";
    }
}
EOF
else
  echo "  인증서 미발견 -> 우선 HTTP만 설정 (나중에 certbot --nginx -d $DOMAIN 재실행)"
  cat > /etc/nginx/sites-available/ai-news-cards <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    root $WEBROOT;
    index index.html;

    location / {
        try_files \$uri \$uri/ =404;
    }

    location /data/ {
        add_header Cache-Control "no-cache";
    }
}
EOF
fi

ln -sf /etc/nginx/sites-available/ai-news-cards /etc/nginx/sites-enabled/ai-news-cards
rm -f /etc/nginx/sites-enabled/default

echo "== 5) nginx 설정 검사 + 재적용 =="
nginx -t
systemctl reload nginx

echo ""
echo "완료. 확인:"
echo "  http://<서버_공인_IP>  (IP로 즉시 접속 가능해야 함)"
echo "  http://$DOMAIN         (DNS가 살아있어야 함 - 지금은 SERVFAIL 상태일 수 있음)"
echo ""
echo "DNS(wiselab.kr)가 아직 SERVFAIL이면 도메인 등록업체 콘솔에서 네임서버부터 복구하세요."
echo "DNS 복구 후 인증서 발급: certbot --nginx -d $DOMAIN"
