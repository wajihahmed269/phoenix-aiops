# OCI BankApp Deployment Status

Last updated: 2026-06-07 05:09 PKT

## Scope

This records the first BankApp-only Argo CD deployment on the OCI K3s cluster.

No observability workload was deployed. No PFMS workload was deployed. No Terraform files were modified. No Services were exposed publicly. No secret values were printed or committed.

## Commands Used

All live commands used the explicit OCI kubeconfig:

```bash
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml config view --minify -o jsonpath='{.clusters[0].cluster.server}'
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml --request-timeout=10s get nodes
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml --request-timeout=10s -n argocd get pods
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml --request-timeout=10s -n bankapp get secret bankapp-secret ghcr-pull-secret
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n argocd get application bankapp -o jsonpath='path={.spec.source.path}{"\n"}automated={.spec.syncPolicy.automated}{"\n"}sync={.status.sync.status}{"\n"}health={.status.health.status}{"\n"}'
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n argocd patch application bankapp --type merge -p '{"operation":{"sync":{"revision":"HEAD","syncStrategy":{"hook":{}}},"initiatedBy":{"username":"codex-manual-bankapp-sync"}}}'
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp rollout status deploy/bankapp-mysql --timeout=300s
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp rollout status deploy/banking-backend --timeout=300s
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp rollout status deploy/banking-frontend --timeout=120s
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp get pods -o wide
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp get svc
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp get pvc
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n argocd get application bankapp -o jsonpath='sync={.status.sync.status}{"\n"}health={.status.health.status}{"\n"}operation={.status.operationState.phase}{"\n"}message={.status.operationState.message}{"\n"}path={.spec.source.path}{"\n"}automated={.spec.syncPolicy.automated}{"\n"}'
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp get events --sort-by=.lastTimestamp
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp logs deploy/banking-backend --previous --tail=120
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp logs deploy/banking-backend --tail=120
```

## Pre-Sync Validation

- OCI kubeconfig server: `https://127.0.0.1:6443`.
- All five OCI K3s nodes were `Ready`.
- Argo CD pods were `Running` and `1/1`.
- `bankapp-secret` existed as `Opaque` with 5 data keys.
- `ghcr-pull-secret` existed as `kubernetes.io/dockerconfigjson` with 1 data key.
- BankApp Application path was `gitops/environments/dev/bankapp`.
- Automated sync was not configured.

## Argo CD Status

Manual sync was triggered only for `Application/bankapp`.

Final status:

```text
sync=Synced
health=Healthy
operation=Succeeded
message=successfully synced (all tasks run)
path=gitops/environments/dev/bankapp
automated=
```

No broad `gitops/environments/dev` sync was run.

## Runtime Status

Pods:

```text
bankapp-mysql-67df8b4f8c-g9tdz      1/1   Running   0
banking-backend-6b5c86b54c-78x2v    1/1   Running   1
banking-frontend-76849d58c7-pft5d   1/1   Running   0
```

Services:

```text
bankapp-mysql         ClusterIP   3306/TCP
banking-app-service   ClusterIP   80/TCP
banking-backend       ClusterIP   8080/TCP
banking-frontend      ClusterIP   80/TCP
```

PVC:

```text
bankapp-mysql-data   Bound   2Gi   RWO   local-path
```

Image pulls succeeded for:

```text
ghcr.io/wajihahmed269/ai-banking-backend:9b3cdb1
ghcr.io/wajihahmed269/ai-banking-frontend:9b3cdb1
mysql:8
```

## Startup Issue

The backend had one initial failed start before becoming Ready.

Previous backend logs showed a Spring/Hibernate startup failure caused by MySQL not accepting connections yet:

```text
Unable to open JDBC Connection for DDL execution
Communications link failure
Connection refused
```

The backend then restarted, connected to MySQL, initialized JPA, and became Ready. Current backend logs show successful startup on port `8080`.

Because the requested guardrail said to stop if backend startup errors occur, local port-forward and browser smoke testing were not run.

## Smoke Test Result

Not run.

Reason: backend had one startup error before recovering. The workflow stopped before:

```bash
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp port-forward svc/banking-frontend 8088:80
```

No AI endpoint was tested.

## Blockers

Resolved:

- `bankapp-secret` exists.
- `ghcr-pull-secret` exists.
- GHCR backend and frontend image pulls succeeded.
- MySQL pod is Ready.
- Backend pod is Ready after one restart.
- Frontend pod is Ready.
- All Services remain `ClusterIP`.
- PVC is `Bound`.

Remaining:

- Frontend smoke test is still pending.
- Backend startup ordering is fragile because the backend can start before MySQL is ready and fail once.
- AI/Ollama path remains deferred and untested.

## Next Safe Step

Run a local-only frontend port-forward and smoke test only after accepting the one recovered backend restart as non-blocking for the demo:

```bash
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp port-forward svc/banking-frontend 8088:80
```

Keep access local-only. Do not deploy observability or PFMS as part of the BankApp smoke phase.

## CORS Fix - Local OCI Demo

Root cause: the deployed backend CORS configuration reads comma-separated allowed origins from `FRONTEND_URL`, but GitOps set `FRONTEND_URL` to the in-cluster service origin `http://banking-frontend`. Browser requests from the local port-forward origin `http://localhost:8088` or `http://127.0.0.1:8088` were rejected with `403 Invalid CORS request`. A live `CORS_ALLOWED_ORIGINS` value was present during diagnosis, but the backend image does not read that variable.

Fix applied through GitOps commit `e253bfc`:

```text
gitops/apps/bankapp/configmap.yaml
  FRONTEND_URL=http://localhost:8088,http://127.0.0.1:8088

gitops/apps/bankapp/backend-deployment.yaml
  bankapp.phoenix-ops/config-version=cors-local-8088-v1
```

The backend image was not rebuilt. The existing backend code already splits comma-separated `FRONTEND_URL` values. The Deployment annotation was added only to force a backend rollout after the ConfigMap change.

Manual sync was run only for `Application/bankapp`. Final Argo status after the CORS fix:

```text
sync=Synced
health=Healthy
revision=e253bfcabe3ebc4567d6e2457108dc9b887ca3b6
path=gitops/environments/dev/bankapp
automated=
```

CORS preflight verification succeeded for both local-only demo origins:

```text
Origin: http://localhost:8088      -> HTTP 200, Access-Control-Allow-Origin: http://localhost:8088
Origin: http://127.0.0.1:8088     -> HTTP 200, Access-Control-Allow-Origin: http://127.0.0.1:8088
```

Runtime status after the CORS fix:

```text
bankapp-mysql                         1/1   Running   0
banking-backend-7bb54c6f79-9jb55      1/1   Running   0
banking-frontend                      1/1   Running   0

bankapp-mysql                         ClusterIP   3306/TCP
banking-app-service                   ClusterIP   80/TCP
banking-backend                       ClusterIP   8080/TCP
banking-frontend                      ClusterIP   80/TCP

bankapp-mysql-data                    Bound       2Gi   RWO   local-path
```

Smoke test result: passed through the local frontend proxy at `http://127.0.0.1:8088/api`. The test covered signup, login, dashboard balance load, deposit/add money, and transaction history. AI/Ollama was not tested.

No public exposure was added. Observability and PFMS were not deployed. Terraform was not modified. Secret values were not printed or committed.
