#!/usr/bin/env bash
# Provision local PostgreSQL + Redis for the production modular monolith.
# Run as root on the application host before deploy.sh. It never prints secrets.
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/jd-resume-ai}"
ENV_FILE="$APP_DIR/.env"
DB_NAME="${DB_NAME:-jdresume}"
DB_USER="${DB_USER:-jdresume}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root" >&2
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq postgresql redis-server openssl
systemctl enable --now postgresql redis-server

DB_PASSWORD="$(openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c 40)"
if ! su - postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname = '$DB_USER'\"" | grep -q 1; then
  su - postgres -c "psql -c \"CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASSWORD'\""
else
  su - postgres -c "psql -c \"ALTER ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASSWORD'\""
fi
if ! su - postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'\"" | grep -q 1; then
  su - postgres -c "createdb -O $DB_USER $DB_NAME"
fi

cp "$ENV_FILE" "$ENV_FILE.pre-persistence-$(date +%Y%m%d%H%M%S)"
set_env() {
  local key="$1" value="$2"
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
  else
    printf '\n%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

set_env DATABASE_URL "postgresql://${DB_USER}:${DB_PASSWORD}@127.0.0.1:5432/${DB_NAME}"
set_env REDIS_URL "redis://127.0.0.1:6379/0"
set_env TASK_QUEUE_ENABLED "true"
set_env TASK_QUEUE_NAME "resume-ai"
chmod 600 "$ENV_FILE"

echo "PostgreSQL and Redis are ready; credentials were written only to $ENV_FILE."
