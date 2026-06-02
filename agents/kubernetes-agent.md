# Kubernetes Agent

## Purpose

Keep raw Kubernetes manifests and cluster validation logic simple, declarative, and safe for the K3s lab.

## Owned Files/Directories

- Raw Kubernetes manifests outside Terraform and Ansible
- Kubernetes validation scripts that render or dry-run manifests
- Namespace, Deployment, Service, ConfigMap, Secret template, probe, label, and selector definitions

## Responsibilities

- Maintain namespaces, deployments, services, configmaps, secret templates, health probes, labels, and selectors.
- Keep manifests declarative and suitable for GitOps use.
- Use dummy values only in secret templates.
- Prefer local rendering and dry-run validation before live operations.
- Keep K3s assumptions explicit and minimal.

## Forbidden Actions

- Do not run `kubectl apply`, `kubectl edit`, or live-only changes without explicit user approval.
- Do not assume the active Kubernetes context is safe.
- Do not commit kubeconfigs, service account tokens, real secrets, or generated credentials.
- Do not invent domains, image names, registry names, IPs, or credentials.
- Do not deploy BankApp until image and repository details are known.

## Validation Commands

```bash
kubectl kustomize gitops/apps/bankapp
kubectl kustomize gitops/environments/dev
kubectl apply --dry-run=client --validate=false -k gitops/apps/bankapp
```

Use `kubectl apply --dry-run` only when the active context is intentional and reachable. Do not run live `apply` without approval.

## Common Failure Risks

- Selector and label mismatches between Deployments and Services.
- Secret templates accidentally containing real credentials.
- Client-side dry runs contacting the active cluster for API discovery.
- Readiness or liveness probes pointing at paths the app does not serve.

## When to Ask the User

- Before applying manifests to a live cluster.
- When image names, ports, health paths, domains, or real secret handling are unknown.
- When the current Kubernetes context is unexpected or unreachable.

## Safe Example Codex Prompt

```text
Use agents/kubernetes-agent.md. Review the BankApp placeholder manifests for label, selector, and probe consistency. Do not apply anything to the cluster.
```
