# AGENTS.md

Guidance for Codex and other coding agents working in this repository.

Phoenix-Ops is a self-healing DevOps/AIOps lab platform using Terraform, Ansible, K3s, Argo CD, Prometheus, Grafana, Loki, Ollama, AI remediation, and chaos/security testing. Keep changes small, explicit, and aligned with the existing structure.

## Core Rules

1. Always inspect existing files before editing.
2. Do not invent AWS regions, IP addresses, SSH key names, AMI IDs, credentials, tokens, or account-specific values.
3. Never modify Terraform files unless the task explicitly says Terraform.
4. Never run `terraform apply`, `terraform destroy`, or destructive AWS commands without asking first.
5. Never commit secrets, `.pem` files, `terraform.tfvars`, Terraform state files, kubeconfigs with credentials, or generated credentials.
6. Prefer small focused changes over broad rewrites.
7. Always show the diff after edits.
8. Run syntax or validation checks when safe and relevant:
   - `terraform fmt`
   - `terraform validate`
   - `ansible-playbook --syntax-check`
   - `kubectl --dry-run=client` or `kubectl --dry-run=server` when relevant
9. Keep architecture simple, production-style, and understandable.
10. Do not add new tools, frameworks, services, or dependencies unless requested.
11. Use private IPs for internal node-to-node communication.
12. Use public IPs only for SSH from the user's laptop or explicitly exposed lab access.
13. For Kubernetes, prefer manifests, Helm, and GitOps workflows over manual live `kubectl` edits.
14. For scripts, make them safe, readable, repeatable, and idempotent.

## Repository Workflow

- Read nearby files before changing behavior.
- Preserve the current layout unless the task asks for a structural change.
- Avoid unrelated formatting churn.
- Do not rename files, directories, variables, hosts, or resources unless required.
- Treat existing inventory, variables, and examples as the source of truth.
- If required values are missing, ask the user instead of guessing.
- After editing, show `git diff -- AGENTS.md` or a narrower relevant diff.

## Terraform Agent Rules

- Only edit files under `terraform/` when the user explicitly asks for Terraform work.
- Never run `terraform apply`, `terraform destroy`, `terraform import`, or state-changing commands without explicit approval.
- Never modify or commit:
  - `terraform/terraform.tfvars`
  - `*.tfstate`
  - `*.tfstate.backup`
  - `.terraform/`
  - plan files containing sensitive data
- Do not invent AWS regions, AMI IDs, instance types, VPC CIDRs, subnet CIDRs, key names, security group rules, or IAM policy details.
- Prefer variables and outputs over hard-coded environment-specific values.
- Keep Terraform resources minimal and clearly named.
- Run `terraform fmt` after Terraform edits.
- Run `terraform validate` only when provider initialization is already available or can be performed safely without changing infrastructure.
- For AWS commands, avoid destructive actions. Ask before stopping, terminating, deleting, detaching, modifying, or replacing resources.

## Ansible Agent Rules

- Inspect inventories, roles, handlers, and existing playbooks before editing.
- Keep playbooks idempotent.
- Prefer role tasks and variables over one-off shell commands.
- Avoid hard-coded public IPs for cluster-internal communication.
- Use private IPs for K3s server, worker, and node-to-node paths.
- Do not embed secrets, private keys, tokens, or generated kubeconfig credentials.
- Use `become` only where required.
- Prefer Ansible modules over raw `shell` or `command` tasks when a suitable module exists.
- When `shell` or `command` is necessary, make changed status explicit with `changed_when` or `creates` where practical.
- Run `ansible-playbook --syntax-check` when the inventory and variables needed for the playbook are available.

## Kubernetes/GitOps Agent Rules

- Prefer declarative manifests, Helm values, and Argo CD application definitions over manual cluster edits.
- Do not use `kubectl edit` or make live-only changes unless the task explicitly requests it.
- Do not assume the current Kubernetes context is safe.
- Ask before applying manifests to a real cluster unless the task clearly authorizes it.
- Use dry-run validation where relevant.
- Keep namespaces, labels, selectors, ports, and service names consistent with existing manifests.
- Prefer private service discovery and cluster networking for internal traffic.
- Do not commit kubeconfigs or service account tokens.
- Keep K3s-specific assumptions explicit and minimal.

## Observability Agent Rules

- Keep Prometheus, Grafana, Loki, and alerting changes declarative.
- Do not add dashboards, alerts, scrape targets, or log pipelines unrelated to the requested task.
- Avoid noisy alerts; prefer actionable alerts with clear labels and severity.
- Keep dashboard JSON or provisioning files readable and scoped.
- Do not hard-code credentials, admin passwords, or external endpoints.
- Preserve existing metric names, labels, and scrape conventions where present.

## AI/Ollama Agent Rules

- Treat AI remediation as high-risk automation.
- Do not add autonomous destructive remediation actions unless explicitly requested.
- Prefer human-review or dry-run remediation flows.
- Keep prompts, model settings, and remediation policies explicit and auditable.
- Do not hard-code model names, API endpoints, or credentials unless they already exist as documented variables.
- Avoid sending secrets, private keys, Terraform state, kubeconfigs, or sensitive logs to model prompts.
- Keep Ollama integration local/private unless the task explicitly requests external access.

## Security/Chaos Agent Rules

- Ask before running disruptive chaos tests, port scans, exploit tools, credential checks, or destructive security commands.
- Keep security and chaos experiments scoped, reversible, and documented.
- Prefer lab-safe tests with clear blast radius.
- Do not weaken SSH, firewall, IAM, Kubernetes RBAC, or security group settings unless explicitly requested.
- Do not commit credentials, generated keys, scan output containing secrets, or sensitive evidence files.
- For chaos automation, include guardrails, timeouts, and clear recovery behavior.
- For security fixes, prefer least privilege and explicit allowlists over broad access.
