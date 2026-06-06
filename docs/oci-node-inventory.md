# OCI Node Inventory

Phoenix-Ops OCI infrastructure was provisioned in `me-jeddah-1` under the `phoenix-ops` compartment.

K3s is not installed yet. These nodes are infrastructure-only and ready for the next provisioning phase.

## Nodes

| Node | Role | Public IP | Private IP | Shape |
| --- | --- | --- | --- | --- |
| `phoenix-node-control-plane` | control-plane | `79.72.10.194` | `10.0.1.79` | `VM.Standard.E3.Flex` |
| `phoenix-node-app` | app | `81.208.190.96` | `10.0.1.120` | `VM.Standard.E3.Flex` |
| `phoenix-node-observatory` | observability | `130.110.126.37` | `10.0.1.233` | `VM.Standard.E3.Flex` |
| `phoenix-node-ai-ops` | ai-ops | `130.110.108.152` | `10.0.1.245` | `VM.Standard.E3.Flex` |
| `phoenix-node-ollama` | ollama | `193.122.74.169` | `10.0.1.184` | `VM.Standard.E3.Flex` |

All nodes are `1` OCPU and `6` GB memory.

## SSH Commands

```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@79.72.10.194
ssh -i ~/.ssh/id_ed25519 ubuntu@81.208.190.96
ssh -i ~/.ssh/id_ed25519 ubuntu@130.110.126.37
ssh -i ~/.ssh/id_ed25519 ubuntu@130.110.108.152
ssh -i ~/.ssh/id_ed25519 ubuntu@193.122.74.169
```

## Future K3s API Tunnel

Kubernetes API port `6443` is not public. After K3s is installed on the control-plane node, use an SSH tunnel from the workstation:

```bash
ssh -i ~/.ssh/id_ed25519 -L 6443:127.0.0.1:6443 ubuntu@79.72.10.194
```

Then point local `kubectl` at the tunnel only after kubeconfig is generated through the approved K3s installation workflow.

## Parallel SSH Check

```bash
for node in \
  79.72.10.194 \
  81.208.190.96 \
  130.110.126.37 \
  130.110.108.152 \
  193.122.74.169; do
  ssh -i ~/.ssh/id_ed25519 \
    -o BatchMode=yes \
    -o ConnectTimeout=10 \
    ubuntu@"${node}" \
    'hostname; hostname -I; uptime -p; cloud-init status || true' &
done
wait
```

## Quick Node Health

Run these checks before K3s installation:

```bash
./scripts/oci-status-lab.sh

for node in \
  79.72.10.194 \
  81.208.190.96 \
  130.110.126.37 \
  130.110.108.152 \
  193.122.74.169; do
  ssh -i ~/.ssh/id_ed25519 ubuntu@"${node}" \
    'hostname; free -h; df -h /; ip -4 addr show; cloud-init status || true'
done
```

## Security Notes

- Public SSH is allowed only from the operator CIDR configured in `terraform/oci/terraform.tfvars`.
- The NSG allows internal VCN traffic from `10.0.0.0/16`.
- The default security list is managed with no ingress rules to prevent OCI default SSH exposure from `0.0.0.0/0`.
- Kubernetes API `6443` is not publicly open.
- BankApp, Grafana, Argo CD, Prometheus, Loki, and Ollama ports are not publicly open.

