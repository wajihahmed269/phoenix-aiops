# Phoenix-Ops OCI Terraform

This directory prepares OCI infrastructure-as-code for the Phoenix-Ops 5-node K3s lab. It is separate from the preserved AWS Terraform root in `terraform/`.

Do not run `terraform apply` until the plan, shape sizing, SSH CIDR, image lookup, and expected monthly cost are reviewed.

## Target

- Region: `me-jeddah-1`
- VCN: `10.0.0.0/16`
- Public subnet: `10.0.1.0/24`
- Nodes:
  - `phoenix-node-control-plane`
  - `phoenix-node-app`
  - `phoenix-node-observatory`
  - `phoenix-node-ai-ops`
  - `phoenix-node-ollama`
- Current verified shape: `VM.Standard.E3.Flex`, `1` OCPU and `6` GB memory per node.

## OCI CLI Setup

The OCI CLI must be configured before Terraform provider operations:

```bash
oci setup config
oci iam compartment list --all --output table
```

Use the `phoenix-ops` compartment OCID in `terraform.tfvars`.

## Terraform Review Workflow

```bash
cd terraform/oci
cp terraform.tfvars.example terraform.tfvars
```

Edit only local `terraform.tfvars` with:

- `compartment_ocid`
- `ssh_ingress_cidr`
- `ssh_public_key`
- reviewed shape settings
- optional reviewed `instance_image_ocid` if image lookup is not suitable

Then run safe review commands:

```bash
terraform init
terraform fmt
terraform validate
terraform plan
```

Do not save plan files containing sensitive values, and do not run `terraform apply` without explicit approval.

## Security Defaults

- Public ingress allows only SSH from `ssh_ingress_cidr`.
- Kubernetes API port `6443` is not publicly open.
- BankApp, Argo CD, Grafana, Prometheus, Loki, Ollama, and HTTP demo ports are not publicly open.
- Node-to-node traffic is allowed inside the VCN CIDR.
- Public IPs are for SSH only.

Use SSH tunnels or Kubernetes port-forwarding for all early demos.

## Cost Controls

- Keep OCI Database out of the first pass.
- Do not add load balancers, NAT gateways, or reserved public IPs until explicitly needed.
- Stop compute instances daily:

```bash
../../scripts/oci-stop-lab.sh
```

- Check status before and after lifecycle actions:

```bash
../../scripts/oci-status-lab.sh
```

## Next Recovery Order

1. Provision OCI infrastructure in a separate approved pass.
2. Generate Ansible inventory from Terraform outputs.
3. Install K3s with private IPs.
4. Recover Argo CD with manual sync.
5. Recover BankApp from GHCR with temporary in-cluster MySQL.
6. Continue observability work.

