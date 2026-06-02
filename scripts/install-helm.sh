#!/usr/bin/env bash
set -euo pipefail

install_dir="${HELM_INSTALL_DIR:-${HOME}/.local/bin}"
helm_version="${HELM_VERSION:-}"

if command -v helm >/dev/null 2>&1; then
  echo "Helm is already installed: $(helm version --short)"
  exit 0
fi

case "$(uname -s)" in
  Linux) os="linux" ;;
  Darwin) os="darwin" ;;
  *)
    echo "Unsupported operating system: $(uname -s)"
    exit 1
    ;;
esac

case "$(uname -m)" in
  x86_64 | amd64) arch="amd64" ;;
  aarch64 | arm64) arch="arm64" ;;
  *)
    echo "Unsupported architecture: $(uname -m)"
    exit 1
    ;;
esac

if [ -z "${helm_version}" ]; then
  echo "Set HELM_VERSION to the Helm version you want to install, for example: HELM_VERSION=v3.15.4"
  exit 1
fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT

archive="helm-${helm_version}-${os}-${arch}.tar.gz"
url="https://get.helm.sh/${archive}"

mkdir -p "${install_dir}"

echo "Downloading ${url}"
curl -fsSL "${url}" -o "${tmp_dir}/${archive}"
tar -xzf "${tmp_dir}/${archive}" -C "${tmp_dir}"
install -m 0755 "${tmp_dir}/${os}-${arch}/helm" "${install_dir}/helm"

echo "Installed Helm to ${install_dir}/helm"
echo "Ensure ${install_dir} is on PATH before running helm commands."
