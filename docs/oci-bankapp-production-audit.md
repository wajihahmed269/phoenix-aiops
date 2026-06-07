# OCI BankApp Production Audit

Last updated: 2026-06-07 05:27 PKT

## Scope

This is a production-hardening audit of the currently deployed BankApp on OCI K3s.

No observability workload was deployed. No PFMS workload was deployed. No Terraform files were modified. No OCI resources were reprovisioned. No Services were exposed publicly. No AI endpoint was tested. Secret values were not printed.

## Commands Run

```bash
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml config view --minify -o jsonpath='{.clusters[0].cluster.server}'
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml get nodes -o wide
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n argocd get application bankapp -o jsonpath='sync={.status.sync.status}{"\n"}health={.status.health.status}{"\n"}revision={.status.sync.revision}{"\n"}path={.spec.source.path}{"\n"}automated={.spec.syncPolicy.automated}{"\n"}'
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp get pods -o wide
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp get svc,pvc,cm
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp get secret bankapp-secret ghcr-pull-secret
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml top pods -A
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml top nodes
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp get deploy bankapp-mysql banking-backend banking-frontend -o yaml
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp describe pvc bankapp-mysql-data
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml get storageclass
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp get events --sort-by=.lastTimestamp
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp get namespace bankapp -o yaml
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp get networkpolicy,pdb,hpa,resourcequota,limitrange
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp logs deploy/banking-backend --tail=160
kubectl --kubeconfig /home/wajih/.kube/phoenix-k3s-oci.yaml -n bankapp exec deploy/bankapp-mysql -- sh -c 'df -h /var/lib/mysql; mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -N -e "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '\''bankappdb'\''; SELECT COUNT(*) FROM bankappdb.users; SELECT COUNT(*) FROM bankappdb.transactions;"'
kubectl kustomize gitops/apps/bankapp
kubectl kustomize gitops/environments/dev/bankapp
```

Source files inspected:

```text
gitops/apps/bankapp/*
gitops/environments/dev/bankapp/kustomization.yaml
/home/wajih/sandbox/ai-banking-app-workload/src/main/resources/application.properties
/home/wajih/sandbox/ai-banking-app-workload/src/main/java/com/wajih/banking/config/SecurityConfig.java
/home/wajih/sandbox/ai-banking-app-workload/src/main/java/com/wajih/banking/ratelimit/RateLimitingFilter.java
/home/wajih/sandbox/ai-banking-app-workload/frontend/src/api/client.js
/home/wajih/sandbox/ai-banking-app-workload/frontend/nginx.conf
/home/wajih/sandbox/ai-banking-app-workload/Dockerfile
/home/wajih/sandbox/ai-banking-app-workload/frontend/Dockerfile
```

## Deployment Health

Kubeconfig target:

```text
https://127.0.0.1:6443
```

Argo CD Application:

```text
sync=Synced
health=Healthy
revision=f3a04435d49037b4f603d3d2072082f837e274f6
path=gitops/environments/dev/bankapp
automated=
```

Nodes:

```text
aiops          Ready   10.0.1.245
app            Ready   10.0.1.120
controlplane   Ready   10.0.1.79
observatory    Ready   10.0.1.233
ollama         Ready   10.0.1.184
```

Pods:

```text
bankapp-mysql-67df8b4f8c-g9tdz      1/1   Running   0   node=ollama
banking-backend-7bb54c6f79-9jb55    1/1   Running   0   node=aiops
banking-frontend-76849d58c7-pft5d   1/1   Running   0   node=observatory
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

Namespace:

```text
bankapp   Active
```

## Resource Consumption

`kubectl top pods -A`:

```text
argocd/argocd-application-controller-0                    3m   166Mi
argocd/argocd-applicationset-controller-b7669f646-f4szl   1m   158Mi
argocd/argocd-dex-server-569b757-jh98b                    0m   154Mi
argocd/argocd-notifications-controller-58ff87546-cjc7w    1m   111Mi
argocd/argocd-redis-b9496d8bf-hcl9w                       4m   4Mi
argocd/argocd-repo-server-75ffcfc9df-nhsbt                1m   70Mi
argocd/argocd-server-76755b46f8-l75x8                     1m   157Mi
bankapp/bankapp-mysql-67df8b4f8c-g9tdz                    7m   447Mi
bankapp/banking-backend-7bb54c6f79-9jb55                  3m   236Mi
bankapp/banking-frontend-76849d58c7-pft5d                 1m   9Mi
kube-system/coredns-8db54c48d-8gw74                       2m   83Mi
kube-system/local-path-provisioner-5d9d9885bc-x26t5       1m   8Mi
kube-system/metrics-server-786d997795-trrhp               4m   23Mi
kube-system/traefik-9bcdbbd9-8cp7j                        1m   164Mi
```

`kubectl top nodes`:

```text
aiops          19m   0%   1349Mi   22%
app            14m   0%   1301Mi   21%
controlplane   53m   2%   2131Mi   35%
observatory    19m   0%   1345Mi   22%
ollama         22m   1%   1626Mi   27%
```

Assessment:

- Current CPU load is very low.
- Current memory headroom is acceptable across all nodes.
- MySQL uses the most BankApp memory at `447Mi`, close to its `512Mi` request but below its `1Gi` limit.
- Backend uses `236Mi`, below its `512Mi` request and `1Gi` limit.
- Frontend uses `9Mi`, far below its `64Mi` request and `128Mi` limit.

## Manifest Audit

Deployments:

```text
bankapp-mysql      replicas=1 strategy=RollingUpdate ready=1 updated=1 restartPolicy=Always
banking-backend    replicas=1 strategy=RollingUpdate ready=1 updated=1 restartPolicy=Always
banking-frontend   replicas=1 strategy=RollingUpdate ready=1 updated=1 restartPolicy=Always
```

Images:

```text
bankapp-mysql      mysql:8
banking-backend    ghcr.io/wajihahmed269/ai-banking-backend:9b3cdb1
banking-frontend   ghcr.io/wajihahmed269/ai-banking-frontend:9b3cdb1
```

Image pull secrets:

```text
banking-backend    ghcr-pull-secret
banking-frontend   ghcr-pull-secret
bankapp-mysql      none
```

Secrets:

```text
bankapp-secret     Opaque                         DATA=5
ghcr-pull-secret   kubernetes.io/dockerconfigjson DATA=1
```

Secret references:

```text
banking-backend    envFrom bankapp-secret
bankapp-mysql      SPRING_DATASOURCE_PASSWORD -> MYSQL_PASSWORD
bankapp-mysql      MYSQL_ROOT_PASSWORD -> MYSQL_ROOT_PASSWORD
```

ConfigMap:

```text
bankapp-config DATA=12
FRONTEND_URL=http://localhost:8088,http://127.0.0.1:8088
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:1b
SENDGRID_ENABLED=false
CLOUDINARY_ENABLED=false
SPRING_JPA_SHOW_SQL=false
```

Render validation:

```text
kubectl kustomize gitops/apps/bankapp                 succeeded
kubectl kustomize gitops/environments/dev/bankapp     succeeded
```

## Probe Audit

MySQL:

```text
readiness: mysqladmin ping -h 127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD", initialDelaySeconds=20, periodSeconds=10, timeoutSeconds=5
liveness:  mysqladmin ping -h 127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD", initialDelaySeconds=60, periodSeconds=20, timeoutSeconds=5
```

Backend:

```text
readiness: HTTP GET / on port http, initialDelaySeconds=45, periodSeconds=10, timeoutSeconds=1
liveness:  HTTP GET / on port http, initialDelaySeconds=60, periodSeconds=15, timeoutSeconds=1
```

Frontend:

```text
readiness: HTTP GET / on port http, initialDelaySeconds=10, periodSeconds=10, timeoutSeconds=1
liveness:  HTTP GET / on port http, initialDelaySeconds=30, periodSeconds=20, timeoutSeconds=1
```

Assessment:

- Probes exist for all containers.
- Backend probes use `/`, not a dedicated health endpoint. This is acceptable for a demo but weak for production because it does not explicitly distinguish process health, DB readiness, and application dependency health.
- Backend has emitted readiness timeouts during rollouts, consistent with slow startup and DB initialization.
- MySQL probes rely on root-password access and are functional, but command-line password use creates warning noise and is not ideal operationally.

## Backend Audit

Startup behavior:

- Current backend pod starts successfully and connects to MySQL.
- Startup logs show Hikari starting, connecting to MySQL, JPA initialization, Tomcat start on `8080`, and successful app startup in roughly 35 seconds.
- Historical first deployment had one backend restart because the backend started before MySQL accepted connections.
- Recent backend rollouts had readiness probe timeout warnings during startup but recovered.

Database retry/dependency behavior:

- There is no initContainer or explicit wait-for-MySQL gate in the Deployment.
- The backend depends on Spring Boot, Hikari, and Hibernate startup behavior.
- `spring.jpa.hibernate.ddl-auto=update` runs schema migration/update during app startup.
- If MySQL is unavailable during startup, the backend can fail and rely on Kubernetes restart behavior.
- The app does not expose a dedicated `/actuator/health` or DB-aware readiness endpoint in the current manifests.

Failure recovery:

- Kubernetes `restartPolicy=Always` and Deployment control loop recover failed backend starts.
- One replica means a backend pod restart causes user-visible downtime until readiness recovers.
- No PodDisruptionBudget, HPA, or multi-replica setup exists.

## Frontend Audit

API behavior:

- Frontend defaults to `VITE_API_BASE_URL || '/api'`.
- The deployed nginx config proxies `/api/` to `http://banking-app-service:80/api/`.
- `banking-app-service` is a compatibility ClusterIP Service that forwards port `80` to backend port `8080`.
- Local-only frontend access through port-forward on `8088` is compatible after the CORS fix.

Localhost assumptions:

- `FRONTEND_URL` is currently set to `http://localhost:8088,http://127.0.0.1:8088` for the local OCI demo.
- This is intentionally local-demo-specific and not a production external URL strategy.

OCI compatibility:

- No public frontend exposure exists.
- All traffic remains inside the cluster or through local port-forward.
- No AWS/EKS/ECR/ALB assumptions are present in the GitOps BankApp path.

## MySQL Audit

PVC and storage:

```text
StorageClass: local-path
Status: Bound
Capacity: 2Gi
AccessModes: RWO
Selected node: ollama
Mounted at: /var/lib/mysql
Filesystem usage from pod: 49G total, 7.1G used, 42G available, 15% used
```

Persistence validation:

```text
database present: bankappdb
users count: 1
transactions count: 1
```

Assessment:

- PVC is healthy and bound.
- `local-path` is node-local storage with `Delete` reclaim policy and no expansion support.
- MySQL pod is pinned by its volume to node-local persistence behavior on the selected node.
- This is acceptable for demo continuity but not HA or production-grade database storage.
- `mysql:8` is a floating major tag and should be pinned to a full version or digest before production.

## Security Findings

Critical:

- None found in the deployed BankApp path during this audit.

High:

- H1: No NetworkPolicy. The namespace has no explicit ingress/egress isolation, so any pod with cluster network reachability can attempt to connect to BankApp Services.
- H2: No pod/container security contexts in manifests. Pods run with default service account and no explicit `runAsNonRoot`, `allowPrivilegeEscalation: false`, dropped capabilities, read-only root filesystem, or seccomp profile.
- H3: In-cluster MySQL on `local-path` is not HA and has node-local data risk. Node loss or local disk loss can take the database with it.

Medium:

- M1: Backend has one replica and no PodDisruptionBudget, so node drain, restart, or rollout can cause downtime.
- M2: Backend startup depends on MySQL readiness indirectly. There is no initContainer, retry policy tuned for DB startup, or DB-aware readiness endpoint.
- M3: Backend readiness/liveness probes use `/` with `timeoutSeconds=1`, which has already produced readiness timeout events during startup.
- M4: MySQL image uses floating tag `mysql:8`.
- M5: CORS is configured for local demo origins only. This is correct for current local-only access, but must be changed deliberately before any future non-local access pattern.
- M6: `OLLAMA_BASE_URL=http://ollama:11434` remains configured even though AI is deferred and no `ollama` Service is part of the BankApp slice.
- M7: No ResourceQuota or LimitRange exists for the namespace.

Low:

- L1: Backend and frontend image tags are short SHA-like tags, not full digests.
- L2: MySQL readiness/liveness command emits the standard MySQL warning about using a password on the command line.
- L3: The frontend depends on a compatibility Service name `banking-app-service`; this should eventually be removed after the frontend image is rebuilt for the native backend service name.
- L4: Backend Deployment has a manual config-version annotation for CORS rollout. This is harmless but should not become a long-term ad hoc rollout mechanism.

## Operational Risks

- A single MySQL pod and local-path PVC create a single point of failure.
- A single backend pod creates a user-visible outage during backend restarts or node disruptions.
- Backend startup can fail if MySQL is not ready and currently relies on Kubernetes retry.
- Probes are not dependency-specific enough for production-grade automation.
- No network isolation or pod security hardening is declared.
- No native metrics, alerts, dashboards, or log pipeline are deployed yet by rule; operational visibility is limited to manual `kubectl` checks until observability is introduced later.

## OCI-Specific Findings

- All OCI nodes are Ready and use private internal IPs.
- Kubernetes API access is through `https://127.0.0.1:6443` via the local tunnel model.
- BankApp Services are all `ClusterIP`; no public exposure exists.
- `local-path` storage is the default StorageClass and selected node-local storage on `ollama` for MySQL.
- Current node resource pressure is low.
- The app is compatible with the OCI private-cluster access model for local demos.

## Recommended Fixes

Priority 1:

- Add NetworkPolicy for `bankapp` after confirming K3s CNI enforcement is available and expected. Allow frontend to backend, backend to MySQL, DNS egress, and explicitly scoped required egress only.
- Add explicit pod/container security contexts for backend, frontend, and MySQL. Start with non-root where image-compatible, `allowPrivilegeEscalation: false`, drop all capabilities where possible, and seccomp `RuntimeDefault`.
- Move persistent database risk out of the demo path before production. Options include an approved managed/private database or an HA storage/database design.

Priority 2:

- Add backend startup dependency handling. Prefer a DB-aware readiness endpoint and/or initContainer wait gate over relying on crash/restart.
- Add a dedicated health endpoint such as Spring Actuator health groups, then point readiness to DB-aware readiness and liveness to process health.
- Add a PodDisruptionBudget for backend and frontend once replicas are increased beyond one.
- Pin `mysql:8` to a full version or digest.

Priority 3:

- Add namespace ResourceQuota and LimitRange after observing realistic load.
- Replace image tags with immutable digests for backend/frontend in GitOps.
- Remove the `banking-app-service` compatibility Service after rebuilding the frontend to use the native backend service name.
- Remove or neutralize AI/Ollama config from the first production BankApp profile until AI is deliberately introduced.

## Priority Ranking

Critical:

- None.

High:

- H1: Missing NetworkPolicy.
- H2: Missing pod/container security contexts.
- H3: MySQL data is on non-HA node-local `local-path` storage.

Medium:

- M1: Single backend replica and no PDB.
- M2: Backend startup depends on MySQL without explicit wait/retry guardrails.
- M3: Weak backend probes and observed readiness timeout events.
- M4: Floating MySQL image tag.
- M5: Local-demo-only CORS configuration.
- M6: Deferred AI/Ollama config remains present.
- M7: No namespace ResourceQuota or LimitRange.

Low:

- L1: Backend/frontend tags are not digests.
- L2: MySQL probe warning noise from command-line password use.
- L3: Frontend compatibility Service should be retired later.
- L4: Manual config-version annotation is operationally clumsy.

## Deployment Readiness Score

Score: **6.5 / 10**

Rationale:

- The app is healthy, private, GitOps-managed, smoke-tested, resource-bounded, and working for the local OCI demo.
- It is not production-ready because database persistence is node-local and non-HA, network/pod security controls are missing, backend startup depends on MySQL timing, and the app has only one replica per tier.
- The next hardening work should stay focused on security boundaries, database durability, and dependency-aware readiness before adding observability, AI workloads, or PFMS.
