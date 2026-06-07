#!/usr/bin/env bash
set -euo pipefail

COMPARTMENT_OCID="${COMPARTMENT_OCID:-ocid1.compartment.oc1..aaaaaaaauzww5eknxu6fecvdm632udxfj5uug26yih3mb6uzsxfdchefoh7q}"
PROJECT_TAG="${PROJECT_TAG:-phoenix-ops}"

mapfile -t instance_ids < <(
  oci compute instance list \
    --compartment-id "${COMPARTMENT_OCID}" \
    --all \
    --query "data[?\"freeform-tags\".Project=='${PROJECT_TAG}' && \"lifecycle-state\"=='STOPPED'].id" \
    --output json | jq -r '.[]'
)

if [ "${#instance_ids[@]}" -eq 0 ]; then
  echo "No stopped Phoenix-Ops OCI instances found for Project=${PROJECT_TAG}."
  exit 0
fi

echo "Starting Phoenix-Ops OCI instances:"
printf '  %s\n' "${instance_ids[@]}"

for instance_id in "${instance_ids[@]}"; do
  oci compute instance action \
    --instance-id "${instance_id}" \
    --action START
done
