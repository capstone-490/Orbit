# Deployment Procedure

**RUN COMMANDS INSIDE THE VM**

## Create VM and Firewall

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker

sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## Create Let's Encrypt Cert

```bash
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/bin/certbot
sudo mkdir -p /etc/letsencrypt/renewal-hooks/deploy

# create hook to copy certs for non-root nginx and reload
sudo vim /etc/letsencrypt/renewal-hooks/deploy/orbit-nginx.sh

#!/bin/sh
set -e
cp -L "$RENEWED_LINEAGE/fullchain.pem" /opt/orbit/certs/fullchain.pem
cp -L "$RENEWED_LINEAGE/privkey.pem" /opt/orbit/certs/privkey.pem
chown 101:101 /opt/orbit/certs/fullchain.pem /opt/orbit/certs/privkey.pem
chmod 600 /opt/orbit/certs/privkey.pem
docker compose -f /opt/orbit/compose.yml exec -T frontend nginx -s reload
EOF
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/orbit-nginx.sh


# request cert
VM_IP=$(curl -s https://ifconfig.me)
sudo certbot certonly \
  --preferred-profile shortlived \
  --webroot -w /opt/orbit/certbot_www \
  --ip-address "$VM_IP" \
  --non-interactive --agree-tos --register-unsafely-without-email

# deploy once to load new cert
sudo RENEWED_LINEAGE="/etc/letsencrypt/live/${VM_IP}" /etc/letsencrypt/renewal-hooks/deploy/orbit-nginx.sh

# check auto-renew
sudo systemctl status snap.certbot.renew.timer
sudo certbot renew --dry-run
```

## Clone Project

```bash
sudo mkdir -p /opt/orbit && sudo chown $USER:$USER /opt/orbit
git clone git@github.com:capstone-490/Orbit.git /opt/orbit
cd /opt/orbit

cp .env.example .env
chmod 600 .env

VM_IP=$(curl -s --max-time 5 https://ifconfig.me || echo "127.0.0.1")

sed -i \
  -e "s|^ENVIRONMENT=.*|ENVIRONMENT=production|" \
  -e "s|^DEBUG=.*|DEBUG=false|" \
  -e "s|^COOKIE_SECURE=.*|COOKIE_SECURE=true|" \
  -e "s|^VITE_API_URL=.*|VITE_API_URL=/api/v1|" \
  -e "s|^CORS_ORIGINS=.*|CORS_ORIGINS=[\"http://localhost:5173\",\"http://127.0.0.1:5173\",\"https://${VM_IP}\"]|" \
  -e "s|^SECRET_KEY=.*|SECRET_KEY=$(openssl rand -hex 32)|" \
  -e "s|^ORBIT_AUTH_SECRET=.*|ORBIT_AUTH_SECRET=$(openssl rand -hex 32)|" \
  -e "s|^ORBIT_ANONYMIZATION_SECRET=.*|ORBIT_ANONYMIZATION_SECRET=$(openssl rand -hex 32)|" \
  -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -hex 24)|" \
  -e "s|^DB_PASSWORD=.*|DB_PASSWORD=$(openssl rand -hex 24)|" \
  .env
```

## Build and Launch

```bash
docker compose -f compose.yaml -f compose.monitoring.yaml build --pull
docker compose -f compose.yaml -f compose.monitoring.yaml up -d --remove-orphans
```

## Verify Health

```bash
docker compose -f compose.yaml -f compose.monitoring.yaml ps -a
curl -I http://127.0.0.1/
curl -i http://127.0.0.1/api/v1/health
```

## Optional

```bash
#db backup
mkdir -p /opt/orbit/backups

DB_NAME_VAL=$(grep -E '^DB_NAME=' .env | cut -d '=' -f2- | tr -d '"' | tr -d "'")
PG_USER_VAL=$(grep -E '^POSTGRES_USER=' .env | cut -d '=' -f2- | tr -d '"' | tr -d "'")

# add to crontab -e
0 2 * * * docker exec orbit-db-1 pg_dump -U ${PG_USER_VAL} ${DB_NAME_VAL} | gzip > /opt/orbit/backups/db_\$(date +\%F).sql.gz && find $/opt/orbit/backups -type f -mtime +14 -delete
```

## View Prometheus Metrics

```bash
ssh -L 9090:127.0.0.1:9090 ubuntu@<VM_PUBLIC_IP>
```
