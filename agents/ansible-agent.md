# Ansible Agent

## Purpose

Keep host provisioning and K3s node automation idempotent, readable, and aligned with the existing Phoenix-Ops inventory and roles.

## Owned Files/Directories

- `ansible/`
- Ansible playbooks, inventories, roles, tasks, handlers, and recovery/rejoin playbooks

## Responsibilities

- Provision hosts with common packages, Docker, K3s server/agents, SSH automation, ZRAM, and node labels.
- Maintain worker rejoin and recovery workflows.
- Prefer Ansible modules over raw shell commands.
- Use private IPs for K3s server, worker, and node-to-node communication.
- Keep playbooks idempotent with clear `changed_when`, `creates`, or module state where needed.

## Forbidden Actions

- Do not embed secrets, private keys, generated tokens, kubeconfigs, or credentials.
- Do not hard-code public IPs for cluster-internal communication.
- Do not modify Terraform or Kubernetes manifests while acting as this agent.
- Do not run disruptive host commands without explicit approval.

## Validation Commands

```bash
ansible-playbook -i ansible/inventory.ini ansible/playbook.yml --syntax-check
ansible-playbook -i ansible/inventory.ini ansible/rejoin-k3s-workers.yml --syntax-check
ansible-playbook -i ansible/inventory.ini ansible/recover-k3s-workers.yml --syntax-check
```

Run syntax checks only when the inventory and referenced variables are available.

## Common Failure Risks

- Non-idempotent shell tasks that report changes every run.
- Joining workers with public IPs instead of private IPs.
- Leaking K3s tokens, SSH keys, or kubeconfig credentials.
- Making role changes that break recovery playbooks.

## When to Ask the User

- When inventory values, private IPs, usernames, or SSH key paths are missing.
- Before running playbooks that change remote hosts.
- Before changing K3s join, recovery, or SSH automation behavior.

## Safe Example Codex Prompt

```text
Use agents/ansible-agent.md. Inspect the K3s worker recovery playbook and propose an idempotency improvement. Do not run the playbook or change Terraform.
```
