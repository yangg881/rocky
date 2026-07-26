#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/jd-resume-ai}"
SERVICE_NAME="${SERVICE_NAME:-jd-resume-ai}"
APP_USER="${APP_USER:-jdresume}"
ENV_FILE="$APP_DIR/.env"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run deploy.sh as root" >&2
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE. Copy .env.example and fill secrets first." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip nginx curl postgresql redis-server

if ! id -u "$APP_USER" >/dev/null 2>&1; then
  useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi

cd "$APP_DIR"
"$PYTHON_BIN" -m venv .venv
.venv/bin/pip install --index-url "$PIP_INDEX_URL" --timeout 120 --retries 8 --progress-bar off --upgrade pip wheel
.venv/bin/pip install --index-url "$PIP_INDEX_URL" --timeout 120 --retries 8 --progress-bar off -r requirements.txt
.venv/bin/python -m playwright install --with-deps chromium

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

.venv/bin/python scripts/bootstrap_tos.py
if [[ -n "${DATABASE_URL:-}" ]]; then
  .venv/bin/python scripts/migrate_metadata_to_postgres.py
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
PREVIOUS_PORT="$(cat "$APP_DIR/.runtime-port" 2>/dev/null || true)"
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
if [[ "$PREVIOUS_PORT" =~ ^[0-9]+$ ]]; then
  export PORT="$PREVIOUS_PORT"
fi
APP_PORT="$(.venv/bin/python scripts/find_port.py)"
echo "$APP_PORT" > "$APP_DIR/.runtime-port"

cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=JD Resume AI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
Environment=PORT=$APP_PORT
Environment=PYTHONUNBUFFERED=1
ExecStart=$APP_DIR/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $APP_PORT --workers 1 --proxy-headers
Restart=on-failure
RestartSec=4
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=full
ReadWritePaths=$APP_DIR

[Install]
WantedBy=multi-user.target
EOF

if [[ "${TASK_QUEUE_ENABLED:-false}" == "true" ]]; then
  cat > "/etc/systemd/system/${SERVICE_NAME}-worker.service" <<EOF
[Unit]
Description=JD Resume AI persistent task worker
After=network-online.target redis-server.service postgresql.service
Wants=network-online.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
Environment=PYTHONUNBUFFERED=1
ExecStart=$APP_DIR/.venv/bin/python -m app.worker_runner
Restart=on-failure
RestartSec=4
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=full
ReadWritePaths=$APP_DIR

[Install]
WantedBy=multi-user.target
EOF
else
  systemctl disable --now "${SERVICE_NAME}-worker.service" 2>/dev/null || true
fi

systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"
if [[ "${TASK_QUEUE_ENABLED:-false}" == "true" ]]; then
  systemctl enable --now "${SERVICE_NAME}-worker.service"
fi

for _ in {1..30}; do
  if curl -fsS "http://127.0.0.1:${APP_PORT}${APP_BASE_PATH:-/resume-ai}/api/health" >/dev/null; then
    echo "Service ready on 127.0.0.1:$APP_PORT"
    exit 0
  fi
  sleep 1
done

journalctl -u "$SERVICE_NAME" -n 80 --no-pager
exit 1
