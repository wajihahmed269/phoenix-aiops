#!/usr/bin/env bash
set -euo pipefail

COMPARTMENT_OCID="${COMPARTMENT_OCID:-ocid1.compartment.oc1..aaaaaaaauzww5eknxu6fecvdm632udxfj5uug26yih3mb6uzsxfdchefoh7q}"
PROJECT_TAG="${PROJECT_TAG:-phoenix-ops}"

oci compute instance list \
  --compartment-id "${COMPARTMENT_OCID}" \
  --all \
  --query "data[?\"freeform-tags\".Project=='${PROJECT_TAG}'].{\"Name\":\"display-name\",\"State\":\"lifecycle-state\",\"Shape\":shape,\"OCPUs\":\"shape-config\".ocpus,\"MemoryGB\":\"shape-config\".\"memory-in-gbs\",\"InstanceId\":id}" \
  --output table

