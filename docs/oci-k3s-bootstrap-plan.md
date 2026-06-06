# OCI K3s Bootstrap Plan

This plan prepares the OCI K3s installation path for Phoenix-Ops. It does not install K3s, deploy Argo CD, deploy BankApp, or expose Kubernetes services publicly.

## Nodes

| Node | Role | Public IP for SSH | Private IP for K3s | Shape |
| --- | --- | --- | --- | --- |
| `phoenix-node-control-plane` | control-plane | `79.72.10.194` | `10.0.1.79` | `VM.Standard.E3.Flex` |
| `phoenix-node-app` | app worker | `81.208.190.96` | `10.0.1.120` | `VM.Standard.E3.Flex` |
| `phoenix-node-observatory` | observability worker | `130.110.126.37` | `10.0.1.233` | `VM.Standard.E3.Flex` |
| `phoenix-node-ai-ops` | ai-ops worker | `130.110.108.152` | `10.0.1.245` | `VM.Standard.E3.Flex` |
| `phoenix-node-ollama` | ollama worker | `193.122.74.169` | `10.0.1.184` | `VM.Standard.E3.Flex` |

All nodes are `1` OCPU and `6` GB memory.

## SSH Model

- Ansible connects over public IPs because OCI SSH ingress is restricted to the operator `/32`.
- User: `ubuntu`
- Key: `~/.ssh/id_ed25519`
- Public IPs are management-only entry points.
- K3s node-to-node traffic must use private IPs.

## Private Networking Model

- VCN CIDR: `10.0.0.0/16`
- Node subnet: `10.0.1.0/24`
- Control-plane private endpoint for workers: `https://10.0.1.79:6443`
- Public `6443` remains closed.
- Workloads, dashboards, Argo CD, observability, and Ollama remain private.

## K3s Server Install Plan

Use the OCI inventory:

```bash
ansible/inventory/oci/hosts.ini
```

The control-plane host defines:

```text
k3s_server_private_ip=10.0.1.79
k3s_server_extra_args="--node-ip 10.0.1.79 --advertise-address 10.0.1.79 --tls-san 127.0.0.1 --tls-san 10.0.1.79"
```

The server role should install K3s only on `phoenix-node-control-plane`, publish the node token as an Ansible fact, and expose the join URL through the private control-plane IP.

## Worker Join Plan

Workers join as K3s agents:

| Node | Agent args |
| --- | --- |
| `phoenix-node-app` | `--node-ip 10.0.1.120` |
| `phoenix-node-observatory` | `--node-ip 10.0.1.233` |
| `phoenix-node-ai-ops` | `--node-ip 10.0.1.245` |
| `phoenix-node-ollama` | `--node-ip 10.0.1.184` |

The agent role resolves the server URL from the control-plane private IP and should join workers to:

```text
https://10.0.1.79:6443
```

## Kubeconfig Tunnel Plan

Kubeconfig should not point at the public control-plane IP. After K3s is installed, use a local tunnel:

```bash
./scripts/oci-k3s-tunnel.sh
```

Equivalent command:

```bash
ssh -i ~/.ssh/id_ed25519 -L 6443:127.0.0.1:6443 ubuntu@79.72.10.194
```

Future kubeconfig recovery should rewrite the cluster server to:

```text
https://127.0.0.1:6443
```

## Validation Checklist

Before installation:

```bash
ansible-inventory -i ansible/inventory/oci/hosts.ini --list
ansible -i ansible/inventory/oci/hosts.ini all_nodes -m ping
ansible-playbook -i ansible/inventory/oci/hosts.ini ansible/oci-k3s-bootstrap.yml --syntax-check
./scripts/oci-ssh-check.sh
```

After a future approved K3s installation:

```bash
ssh -i ~/.ssh/id_ed25519 ubuntu@79.72.10.194 'sudo k3s kubectl get nodes -o wide'
./scripts/oci-k3s-tunnel.sh
kubectl get nodes -o wide
```

Do not run `kubectl apply` during the infrastructure bootstrap phase.

## Rollback and Uninstall Plan

Only after explicit approval:

1. Stop workload deployment first if any future workloads exist.
2. Remove K3s agents from workers with `/usr/local/bin/k3s-agent-uninstall.sh`.
3. Remove K3s server from the control plane with `/usr/local/bin/k3s-uninstall.sh`.
4. Verify no `k3s` or `k3s-agent` systemd units remain.
5. Keep OCI instances, VCN, subnet, NSG, and Terraform state intact unless a separate Terraform teardown is explicitly approved.

Do not destroy OCI infrastructure as part of K3s rollback.

## Risks and Blockers

- Existing `ansible/inventory.ini` is AWS-specific and should not be used for OCI.
- Existing K3s roles install from `https://get.k3s.io`, so the next execution phase requires outbound internet access from nodes.
- `common` installs and upgrades packages and Docker; this is mutating and should run only after explicit approval.
- Kubeconfig must be handled carefully because it contains credentials and must not be committed.
- 1 OCPU / 6 GB nodes are cost-aware but may be tight for Ollama and observability workloads.

## Exact Next Execution Prompt

```text
Use AGENTS.md and agents/ansible-agent.md. Read docs/oci-k3s-bootstrap-plan.md and ansible/inventory/oci/hosts.ini. Run ansible-inventory and ansible ping checks, then execute ansible/oci-k3s-bootstrap.yml against the OCI inventory to install K3s only. Do not deploy Argo CD, BankApp, observability, or any workloads. Keep Kubernetes API private and use SSH tunnel access only.
```

