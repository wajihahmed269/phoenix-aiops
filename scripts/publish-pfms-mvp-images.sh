#!/usr/bin/env bash
set -euo pipefail

# Publish helper for the PFMS MVP images.
# This script never handles GitHub tokens or stores credentials. Log in to GHCR
# separately before running with PUSH_IMAGES=true.

REGISTRY_NAMESPACE="${REGISTRY_NAMESPACE:-ghcr.io/wajihahmed269}"
IMAGE_TAG="${IMAGE_TAG:-pfms-mvp-v1}"
PUSH_IMAGES="${PUSH_IMAGES:-false}"

IMAGES=(
  "pfms-audit-pfms-ui:latest ${REGISTRY_NAMESPACE}/pfms-ui:${IMAGE_TAG}"
  "pfms-audit-api-gateway:latest ${REGISTRY_NAMESPACE}/pfms-api-gateway:${IMAGE_TAG}"
  "pfms-audit-budget-service:latest ${REGISTRY_NAMESPACE}/pfms-budget-service:${IMAGE_TAG}"
)

for image_pair in "${IMAGES[@]}"; do
  source_image="${image_pair%% *}"
  target_image="${image_pair##* }"

  if ! docker image inspect "${source_image}" >/dev/null 2>&1; then
    echo "Missing local source image: ${source_image}" >&2
    exit 1
  fi

  echo "Tagging ${source_image} -> ${target_image}"
  docker tag "${source_image}" "${target_image}"
done

echo
echo "Docker push commands:"
for image_pair in "${IMAGES[@]}"; do
  target_image="${image_pair##* }"
  echo "docker push ${target_image}"
done

if [[ "${PUSH_IMAGES}" == "true" ]]; then
  echo
  echo "PUSH_IMAGES=true detected. Pushing images..."
  for image_pair in "${IMAGES[@]}"; do
    target_image="${image_pair##* }"
    docker push "${target_image}"
  done
else
  echo
  echo "Set PUSH_IMAGES=true to push images after docker login ghcr.io"
fi
