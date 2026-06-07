# OCI Argo CD Status

Last updated: 2026-06-06 22:15 UTC

## Current Status

Argo CD is operational on the recovered OCI K3s cluster.

- All 5 OCI K3s nodes are `Ready`.
- The Kubernetes API remains private.
- All Argo CD Services are `ClusterIP`.
- No Argo CD Applications are deployed.
- No ApplicationSets are deployed.
- No BankApp, PFMS, or observability workloads were synced during this phase.

## ApplicationSet Controller Issue

`argocd-applicationset-controller` was the only unhealthy pod in the `argocd` namespace.

Observed state before the fix:

- Pod: `argocd-applicationset-controller-b7669f646-gwlg6`
- Status: `CrashLoopBackOff`
- Restart count: `17`
- Last exit code: `1`
- Image: `quay.io/argoproj/argocd:v3.4.3`

Controller logs showed:

```text
failed to get restmapping: no matches for kind "ApplicationSet" in version "argoproj.io/v1alpha1"
failed to wait for applicationset caches to sync kind source: *v1alpha1.ApplicationSet
```

The live CRD inventory only contained:

```text
applications.argoproj.io
appprojects.argoproj.io
```

`applicationsets.argoproj.io` was missing.

## Root Cause

The Argo CD install had the ApplicationSet controller Deployment and RBAC, but the `applicationsets.argoproj.io` CRD was absent.

This was a CRD mismatch/incomplete Argo CD install state, not an OCI network, DNS, Redis, repo-server, API server, RBAC, stale generator, or invalid ApplicationSet configuration issue.

Supporting checks:

- `kubectl get applicationsets -A` failed before the fix because the API resource did not exist.
- Argo RBAC existed for `applicationsets`, `applicationsets/status`, and `applicationsets/finalizers`.
- `argocd-cm` and `argocd-cmd-params-cm` had no stale ApplicationSet generator or repo-server override.
- DNS resolved `kubernetes.default.svc`, `argocd-redis.argocd.svc`, `argocd-repo-server.argocd.svc`, and `argocd-server.argocd.svc`.
- TCP connectivity from `argocd-repo-server` succeeded to Redis `6379`, repo-server `8081`, and Kubernetes API `443`.

## Fix Applied

Installed only the missing ApplicationSet CRD matching the running Argo CD version:

```bash
sudo k3s kubectl apply --server-side \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.4.3/manifests/crds/applicationset-crd.yaml
```

Then recycled only the failed ApplicationSet controller pod so the existing Deployment could recreate it against the fixed API state:

```bash
sudo k3s kubectl delete pod -n argocd \
  -l app.kubernetes.io/name=argocd-applicationset-controller
```

No workloads were deployed or synced.

## Recovery Validation

Post-fix CRDs:

```text
applications.argoproj.io
applicationsets.argoproj.io
appprojects.argoproj.io
```

Post-fix ApplicationSet discovery:

```text
No resources found
```

Post-fix controller state:

- Pod: `argocd-applicationset-controller-b7669f646-f4szl`
- Status: `Running`
- Ready: `1/1`
- Restart count: `0`
- Deployment rollout: successful

Post-fix logs show the controller started successfully:

```text
Starting Controller
Starting workers
```

## GitOps Audit Findings

Repository structure:

- `gitops/apps/bankapp` renders successfully with `kubectl kustomize`.
- `gitops/apps/observability` renders successfully with `kubectl kustomize`.
- `gitops/environments/dev` currently points to `../../apps/bankapp`.
- Argo CD Application templates exist for BankApp, observability, and PFMS MVP, but none are currently deployed in the cluster.

Safe OCI restore traits:

- Argo CD values keep the server Service as `ClusterIP`.
- BankApp Services are `ClusterIP`.
- Observability Services are `ClusterIP`.
- Application templates use manual sync only; no automated sync, prune, or self-heal is configured.
- No committed ApplicationSet manifests were found under `gitops/`.

Blockers and risks:

- A broad sync of `gitops/environments/dev` would deploy BankApp because that top-level kustomization points to BankApp.
- BankApp still requires a real `bankapp-secret` and `ghcr-pull-secret` in the `bankapp` namespace before sync.
- BankApp image tags should be reviewed before restore; current manifests use immutable-looking GHCR tags, but image availability and runtime behavior still need verification.
- BankApp uses an in-cluster MySQL demo path; the README still documents the long-term RDS target as blocked pending approved infrastructure work.
- BankApp config references `OLLAMA_BASE_URL=http://ollama:11434`; no `ollama` Service is part of the BankApp kustomization.
- Observability requires a real `grafana-admin-secret` before sync.
- Observability node-exporter uses `hostNetwork: true` and `hostPort: 9100`; Services remain `ClusterIP`, but this should be reviewed before observability restore on the OCI lab.
- PFMS MVP includes `secret-template.yaml` in its kustomization and should not be synced without replacing dummy secrets through an approved secret workflow.

Stale AWS dependencies:

- No AWS, EKS, ALB, ELB, ECR, or AWS region assumptions were found in `gitops/`.
- BankApp documentation still mentions the historical RDS/MySQL target, but the current demo manifest path uses in-cluster MySQL.
- Local workstation kubeconfig was observed pointing at an old AWS EKS context during diagnostics; OCI validation was performed through `sudo k3s kubectl` over SSH to the OCI control-plane node.

## Next Safe Deployment Phase

Recommended next BankApp restore phase:

1. Keep Argo CD private and do not enable automated sync.
2. Do not sync `gitops/environments/dev` as a broad environment entry point.
3. Create or verify `bankapp-secret` and `ghcr-pull-secret` in `bankapp` through an approved secret workflow.
4. Verify GHCR image availability for the backend and frontend tags.
5. Review the BankApp diff in Argo CD.
6. Manually sync only the BankApp Application/path after explicit approval.
7. Validate pods, Services, logs, and local-only port-forward access.

Observability should remain a later phase after BankApp is stable and after the Grafana secret and node-exporter host networking choice are reviewed.
