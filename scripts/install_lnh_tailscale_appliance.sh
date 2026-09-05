#!/usr/bin/env bash
# One-time appliance installation; never part of daily Mission Control use.
set -euo pipefail
: "${TAILSCALE_AUTHKEY:?Required only during installation}"
NODE_NAME="${LNH_QWEN_NODE:-lnh-mgc-qwen}"
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up --auth-key="$TAILSCALE_AUTHKEY" --hostname="$NODE_NAME" --ssh=false
command -v ollama >/dev/null 2>&1 || curl -fsSL https://ollama.com/install.sh | sh
cat >/etc/systemd/system/lnh-ollama.service <<'EOF'
[Unit]
After=network-online.target tailscaled.service
[Service]
Environment=OLLAMA_HOST=0.0.0.0:11434
ExecStart=/usr/local/bin/ollama serve
Restart=always
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now lnh-ollama
until curl --fail --silent http://127.0.0.1:11434/api/tags >/dev/null; do sleep 2; done
ollama pull qwen3:14b
