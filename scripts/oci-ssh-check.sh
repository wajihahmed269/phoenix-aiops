#!/usr/bin/env bash
set -euo pipefail

ssh_key="${OCI_SSH_KEY:-${HOME}/.ssh/id_ed25519}"
ssh_user="${OCI_SSH_USER:-ubuntu}"

nodes=(
  "phoenix-node-control-plane 79.72.10.194 10.0.1.79 control-plane"
  "phoenix-node-app 81.208.190.96 10.0.1.120 app"
  "phoenix-node-observatory 130.110.126.37 10.0.1.233 observability"
  "phoenix-node-ai-ops 130.110.108.152 10.0.1.245 ai-ops"
  "phoenix-node-ollama 193.122.74.169 10.0.1.184 ollama"
)

if [ ! -r "${ssh_key}" ]; then
  echo "SSH key not readable: ${ssh_key}" >&2
  exit 1
fi

for node in "${nodes[@]}"; do
  read -r name public_ip private_ip role <<<"${node}"
  echo "== ${name} (${role}) =="
  ssh \
    -i "${ssh_key}" \
    -o BatchMode=yes \
    -o StrictHostKeyChecking=accept-new \
    -o ConnectTimeout=10 \
    "${ssh_user}@${public_ip}" \
    "test \$(hostname -I | tr ' ' '\\n' | grep -c '^${private_ip}$') -eq 1 && printf 'private_ip=%s cloud_init=' '${private_ip}' && cloud-init status --wait"
done

