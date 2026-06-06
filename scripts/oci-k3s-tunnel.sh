#!/usr/bin/env bash
set -euo pipefail

ssh_key="${OCI_SSH_KEY:-${HOME}/.ssh/id_ed25519}"
ssh_user="${OCI_SSH_USER:-ubuntu}"
control_plane_public_ip="${OCI_CONTROL_PLANE_PUBLIC_IP:-79.72.10.194}"
local_port="${OCI_K3S_LOCAL_PORT:-6443}"

if [ ! -r "${ssh_key}" ]; then
  echo "SSH key not readable: ${ssh_key}" >&2
  exit 1
fi

echo "Opening local K3s API tunnel on 127.0.0.1:${local_port}."
echo "This does not expose Kubernetes publicly. Stop with Ctrl-C."

exec ssh \
  -i "${ssh_key}" \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -L "${local_port}:127.0.0.1:6443" \
  "${ssh_user}@${control_plane_public_ip}"

