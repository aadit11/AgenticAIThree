#!/bin/sh
set -eu
/usr/local/bin/isolation-report.sh
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
  base_url: https://api.openai.com/v1
EOF
fi
fact="$HERMES_HOME/restart-fact.txt"
if [ ! -f "$fact" ]; then
  printf '%s\n' "Maya's fictional study group meets in Leavey 2." > "$fact"
  echo "isolation: wrote restart fact"
else
  echo "isolation: restart fact survived"
fi
exec hermes gateway run
