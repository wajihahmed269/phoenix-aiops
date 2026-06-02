#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
terraform_dir="${repo_root}/terraform"

read -r -a instance_ids <<< "$(terraform -chdir="${terraform_dir}" output -raw ec2_instance_id_args)"

if [ "${#instance_ids[@]}" -eq 0 ]; then
  echo "No EC2 instance IDs found in Terraform output."
  exit 1
fi

aws ec2 describe-instances \
  --instance-ids "${instance_ids[@]}" \
  --query 'Reservations[].Instances[].{InstanceId:InstanceId,State:State.Name,Name:Tags[?Key==`Name`]|[0].Value,PrivateIp:PrivateIpAddress,PublicIp:PublicIpAddress}' \
  --output table
