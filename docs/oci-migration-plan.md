# OCI Migration Plan

## Purpose

Phoenix-Ops is moving from AWS to Oracle Cloud Infrastructure because the AWS account is closed and the previous EC2-backed K3s lab can no longer be used. This plan preserves the working 5-node Phoenix-Ops architecture while rebuilding the infrastructure layer on OCI with a separate Terraform root.

This is planning and infrastructure-as-code preparation only. Do not create OCI resources, run `terraform apply`, deploy Kubernetes, or install K3s during this pass.

## AWS to OCI Mapping

| AWS concept | OCI equivalent | Phoenix-Ops use |
| --- | --- | --- |
| AWS VPC | OCI VCN | Private lab network for all nodes |
| AWS subnet | OCI subnet | Public subnet for SSH-reachable lab nodes |
| AWS security group | OCI NSG/security list | Node firewall rules |
| AWS EC2 | OCI Compute instance | K3s control-plane and workers |
| AWS EBS | OCI boot/block volume | Instance boot disks and future persistent volumes |
| AWS public IP | OCI public IP | SSH access from the operator laptop only |

## Target Architecture

The OCI rebuild keeps the same 5-node K3s shape:

| Node name | Role | Intended workload |
| --- | --- | --- |
| `phoenix-node-control-plane` | K3s server | Kubernetes API, control-plane components |
| `phoenix-node-app` | Worker | BankApp frontend, backend, temporary in-cluster MySQL |
| `phoenix-node-observatory` | Worker | Prometheus, Grafana, Loki, kube-state-metrics |
| `phoenix-node-ai-ops` | Worker | AI remediation controller, dashboards, runbooks |
| `phoenix-node-ollama` | Worker | Ollama and model-serving experiments |

BankApp should recover first with GHCR images and temporary in-cluster MySQL. OCI Database is intentionally out of scope until the cluster and GitOps path are stable again.

## Network Layout

- Region: `me-jeddah-1`
- Compartment: `phoenix-ops`
- VCN CIDR: `10.0.0.0/16`
- Public subnet CIDR: `10.0.1.0/24`
- One internet gateway for SSH access to lab nodes.
- One route table with `0.0.0.0/0` via the internet gateway for the public subnet.
- Public IPs are attached to compute instances for SSH only.
- Private IPs are used for all node-to-node, K3s, BankApp, observability, and Ollama traffic.

The first OCI Terraform root is intentionally simple: one VCN, one public subnet, one network security group, and five compute instances. Additional private subnets, NAT gateways, bastions, OCI Block Volume persistence, and OCI Database can be added later after the baseline lab is working.

## Firewall and Security Rules

Initial ingress should be minimal:

- Allow TCP `22` from the operator's public IP CIDR only.
- Allow all traffic within the VCN CIDR for K3s node-to-node communication.
- Do not expose Kubernetes API port `6443` publicly. Use SSH tunneling to the control-plane node when `kubectl` access is needed.
- Do not expose BankApp, Grafana, Argo CD, Prometheus, Loki, Ollama, or demo HTTP ports publicly during the initial infrastructure pass.
- Keep services as `ClusterIP` in GitOps. Use local port-forwarding or SSH tunnels for demos.

Initial egress:

- Allow outbound internet access so instances can install packages, pull GHCR images, and reach required update repositories.

Later hardening options:

- Split SSH access into a bastion pattern.
- Move workers to a private subnet behind NAT.
- Replace broad internal VCN ingress with explicit K3s, Flannel, kubelet, DNS, and workload ports after the cluster is proven.

## SSH Access Model

- Each instance receives an operator-provided SSH public key through Terraform metadata.
- SSH is allowed only from `ssh_ingress_cidr`, for example `203.0.113.5/32`.
- The public IPs are for SSH from the user's laptop only.
- Internal operations should use private IPs after connecting.
- Kubernetes API access should use an SSH tunnel to `phoenix-node-control-plane`, not public `6443`.

Example future tunnel pattern:

```bash
ssh -L 6443:127.0.0.1:6443 ubuntu@CONTROL_PLANE_PUBLIC_IP
```

## K3s Install Plan

K3s installation happens after OCI provisioning is reviewed and applied in a separate approved pass.

1. Provision the five OCI nodes with Terraform.
2. Generate or update Ansible inventory from Terraform outputs.
3. Install K3s server on `phoenix-node-control-plane`.
4. Join the four worker nodes using private IPs and the K3s token.
5. Label or taint workers by role:
   - `phoenix-role=app`
   - `phoenix-role=observability`
   - `phoenix-role=ai-ops`
   - `phoenix-role=ollama`
6. Validate all nodes are `Ready`.
7. Keep public Kubernetes API access closed and use SSH tunnels for local administration.

## Argo CD Recovery Plan

1. Install Helm locally if needed.
2. Install Argo CD declaratively into the `argocd` namespace after K3s is healthy.
3. Register the Phoenix-Ops Git repository.
4. Keep automated sync, prune, and self-heal disabled at first.
5. Review Argo CD diffs before each manual sync.
6. Recover BankApp first, then observability, then AI/Ollama workflows.

## BankApp Recovery Plan

Initial BankApp recovery should preserve the last known working demo path:

- Use GHCR images first:
  - `ghcr.io/wajihahmed269/ai-banking-backend:<immutable-tag>`
  - `ghcr.io/wajihahmed269/ai-banking-frontend:<immutable-tag>`
- Do not use `latest`.
- Use the temporary in-cluster MySQL deployment first for demo stability.
- Keep BankApp Services as `ClusterIP`.
- Use port-forwarding or SSH tunneling for local demos.
- Verify signup/login, dashboard, deposit, withdraw, transfer/pay bill, transaction history, and AI endpoint behavior.

OCI Database is not part of the first recovery pass.

## Observability Continuation Plan

Observability resumes after the base cluster and BankApp are stable:

1. Deploy or recover Prometheus, Grafana, Loki, and kube-state-metrics declaratively.
2. Keep dashboards and alerts scoped to the Phoenix-Ops lab.
3. Start with actionable alerts only.
4. Keep Grafana private and access it through port-forwarding or SSH tunnels.
5. Preserve existing metric names, labels, and scrape conventions where possible.
6. Add BankApp dashboards and logs after the app is stable on OCI.

## Cost-Control Rules

- Keep the first OCI design to five compute instances and one small public subnet.
- Do not add OCI Database, load balancers, NAT gateways, object storage, or reserved public IPs in the first pass.
- Use shape variables so node sizing can be reviewed before provisioning.
- Stop compute instances daily when not actively using the lab.
- Run `scripts/oci-status-lab.sh` before and after start/stop actions.
- Avoid block volumes beyond boot volumes until persistence requirements are clear.
- Use freeform tags on all resources:
  - `Project=phoenix-ops`
  - `ManagedBy=terraform`
  - `Environment=lab`

## Daily Shutdown, Startup, and Status Workflow

After resources exist in a future approved provisioning pass:

```bash
./scripts/oci-status-lab.sh
./scripts/oci-start-lab.sh
./scripts/oci-status-lab.sh

# When finished for the day:
./scripts/oci-stop-lab.sh
./scripts/oci-status-lab.sh
```

The scripts should select instances by compartment and freeform tag. They should never terminate resources.

## Risks and Blockers

- OCI image lookup must be verified in `me-jeddah-1` before the first plan/apply.
- Compute shape availability and quota must be confirmed before provisioning.
- Five always-on instances may create unnecessary cost if daily stop discipline is missed.
- Public SSH requires the user's current public IP CIDR; do not use `0.0.0.0/0`.
- BankApp images must exist in GHCR with immutable tags before GitOps recovery.
- K3s and workload scheduling may need ARM/AMD64 alignment if OCI shapes differ from prior AWS instances.
- Ollama resource sizing may require a larger shape or separate cost review.
- No Kubernetes, Argo CD, or BankApp deployment should happen until OCI infrastructure is provisioned and validated in a separate approved step.

