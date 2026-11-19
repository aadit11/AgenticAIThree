#!/bin/sh
set -eu
# Public port is the grader chat. Hermes stays on loopback.
export PORT="${PORT:-8080}"
export HERMES_PORT="${HERMES_PORT:-8081}"
export API_SERVER_ENABLED=true
export API_SERVER_PORT="$HERMES_PORT"
export API_SERVER_HOST=127.0.0.1
/usr/local/bin/isolation-report.sh
python /opt/lumen/write_runtime_env.py
mkdir -p "$HERMES_HOME"
if [ ! -f "$HERMES_HOME/SOUL.md" ]; then
  cp /opt/lumen/seed/SOUL.md "$HERMES_HOME/SOUL.md"
  cp /opt/lumen/seed/USER.md "$HERMES_HOME/USER.md"
fi
if [ ! -f "$HERMES_HOME/config.yaml" ]; then
  cat > "$HERMES_HOME/config.yaml" <<'EOF'
timezone: America/Los_Angeles
model:
  default: gpt-6.1-sol
  provider: openai-api
  base_url: http://127.0.0.1:8642/v1/
EOF
fi
fact="$HERMES_HOME/restart-fact.txt"
if [ ! -f "$fact" ]; then
  printf '%s\n' "Maya's fictional study group meets in Leavey 2." > "$fact"
  echo "isolation: wrote restart fact"
else
  echo "isolation: restart fact survived"
fi
if [ -n "${TAILSCALE_AUTHKEY:-}" ]; then
  mkdir -p /tmp/tailscale
  tailscaled --tun=userspace-networking --statedir=/tmp/tailscale --socket=/tmp/tailscale/tailscaled.sock --socks5-server=localhost:1055 >/tmp/tailscale/tailscaled.log 2>&1 &
  i=0
  while [ ! -S /tmp/tailscale/tailscaled.sock ] && [ "$i" -lt 30 ]; do
    i=$((i + 1))
    sleep 1
  done
  if tailscale --socket=/tmp/tailscale/tailscaled.sock up --auth-key="$TAILSCALE_AUTHKEY" --hostname=lumen-cloud --accept-dns=false --timeout=60s >/tmp/tailscale/up.log 2>&1; then
    echo "isolation: tailscale up"
  else
    echo "isolation: tailscale failed"
  fi
  if [ -n "${OLLAMA_UPSTREAM:-}" ]; then
    python /opt/lumen/ollama_forward.py &
    sleep 1
    if python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=20).read()"; then
      echo "isolation: ollama tags ok"
    else
      echo "isolation: ollama tags failed"
    fi
  fi
fi
python /opt/lumen/install_cloud_jobs.py
python /opt/lumen/openai_proxy.py &
python /opt/lumen/install_cloud_jobs.py briefing >>"$HERMES_HOME/briefing-once.log" 2>&1 &
python /opt/lumen/install_cloud_jobs.py health &
python /opt/lumen/install_cloud_jobs.py alerts &
python /opt/lumen/continuity.py >>"$HERMES_HOME/continuity.log" 2>&1 &
(sleep 90; hermes cron tick; echo "isolation: cron tick done") &
mkdir -p "$HERMES_HOME/plugins/web-approval"
cp /opt/lumen/plugins/web-approval/plugin.yaml "$HERMES_HOME/plugins/web-approval/plugin.yaml"
cp /opt/lumen/plugins/web-approval/__init__.py "$HERMES_HOME/plugins/web-approval/__init__.py"
python /opt/lumen/enable_web_plugin.py
python /opt/lumen/web_ui.py &
WEB_PID=$!
echo "web_ui started (pid $WEB_PID) on 0.0.0.0:$PORT -> agent on 127.0.0.1:$HERMES_PORT"
hermes gateway run &
AGENT_PID=$!
shutdown() {
  kill -TERM "$AGENT_PID" 2>/dev/null || true
  wait "$AGENT_PID" 2>/dev/null || true
  kill -TERM "$WEB_PID" 2>/dev/null || true
  wait "$WEB_PID" 2>/dev/null || true
}
trap 'shutdown; exit 0' TERM INT
while kill -0 "$AGENT_PID" 2>/dev/null && kill -0 "$WEB_PID" 2>/dev/null; do
  sleep 2
done
shutdown
exit 1
