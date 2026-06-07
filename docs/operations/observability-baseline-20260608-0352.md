# Observability Baseline Snapshot

## Metadata

- Timestamp: 2026-06-08 03:52:47 PKT
- Git commit: `26a626c`
- OCI kubeconfig: `/home/wajih/.kube/phoenix-k3s-oci.yaml`

## Summary

- Git repo was clean and synced with `origin/master` at capture time.
- All five OCI K3s nodes were `Ready`.
- `metrics-server` was healthy and `kubectl top` returned data.
- BankApp was healthy: MySQL, backend, and frontend were all `Running`.
- `argocd/bankapp` was `Healthy` and `OutOfSync`.
- The only current out-of-sync resource was `Deployment/banking-backend`.
- `observability` namespace did not exist yet.
- No current node memory warning: highest observed node memory was `37%` on `controlplane`.
- `kubectl debug` was not used for node-level disk inspection because the baseline already had safe metrics from `kubectl top`, and adding debug pods was unnecessary before rollout.

## Nodes

```text
NAME           STATUS   ROLES           AGE   VERSION        INTERNAL-IP   EXTERNAL-IP   OS-IMAGE             KERNEL-VERSION      CONTAINER-RUNTIME
aiops          Ready    <none>          47h   v1.35.5+k3s1   10.0.1.245    <none>        Ubuntu 22.04.5 LTS   6.8.0-1054-oracle   containerd://2.2.3-k3s1
app            Ready    <none>          47h   v1.35.5+k3s1   10.0.1.120    <none>        Ubuntu 22.04.5 LTS   6.8.0-1054-oracle   containerd://2.2.3-k3s1
controlplane   Ready    control-plane   2d    v1.35.5+k3s1   10.0.1.79     <none>        Ubuntu 22.04.5 LTS   6.8.0-1054-oracle   containerd://2.2.3-k3s1
observatory    Ready    <none>          47h   v1.35.5+k3s1   10.0.1.233    <none>        Ubuntu 22.04.5 LTS   6.8.0-1054-oracle   containerd://2.2.3-k3s1
ollama         Ready    <none>          47h   v1.35.5+k3s1   10.0.1.184    <none>        Ubuntu 22.04.5 LTS   6.8.0-1054-oracle   containerd://2.2.3-k3s1
```

## Pods

```text
NAMESPACE     NAME                                               READY   STATUS      RESTARTS      AGE   IP           NODE           NOMINATED NODE   READINESS GATES
argocd        argocd-application-controller-0                    1/1     Running     2 (83m ago)   46h   10.42.3.11   app            <none>           <none>
argocd        argocd-applicationset-controller-b7669f646-f4szl   1/1     Running     1 (83m ago)   24h   10.42.1.8    ollama         <none>           <none>
argocd        argocd-dex-server-569b757-jh98b                    1/1     Running     2 (83m ago)   46h   10.42.2.12   observatory    <none>           <none>
argocd        argocd-notifications-controller-58ff87546-cjc7w    1/1     Running     2 (83m ago)   46h   10.42.3.10   app            <none>           <none>
argocd        argocd-redis-b9496d8bf-hcl9w                       1/1     Running     1 (21h ago)   31h   10.42.0.20   controlplane   <none>           <none>
argocd        argocd-repo-server-75ffcfc9df-nhsbt                1/1     Running     2 (83m ago)   46h   10.42.4.12   aiops          <none>           <none>
argocd        argocd-server-76755b46f8-l75x8                     1/1     Running     2 (83m ago)   46h   10.42.2.11   observatory    <none>           <none>
bankapp       bankapp-mysql-67df8b4f8c-g9tdz                     1/1     Running     1 (83m ago)   23h   10.42.1.9    ollama         <none>           <none>
bankapp       banking-backend-84674d78d5-c5dr7                   1/1     Running     0             72m   10.42.3.12   app            <none>           <none>
bankapp       banking-frontend-76849d58c7-pft5d                  1/1     Running     1 (83m ago)   23h   10.42.2.10   observatory    <none>           <none>
kube-system   coredns-8db54c48d-8gw74                            1/1     Running     2 (21h ago)   2d    10.42.0.18   controlplane   <none>           <none>
kube-system   helm-install-traefik-cjd4c                         0/1     Completed   2             2d    <none>       controlplane   <none>           <none>
kube-system   helm-install-traefik-crd-qfz9v                     0/1     Completed   1             2d    <none>       controlplane   <none>           <none>
kube-system   local-path-provisioner-5d9d9885bc-x26t5            1/1     Running     4 (21h ago)   2d    10.42.0.16   controlplane   <none>           <none>
kube-system   metrics-server-786d997795-trrhp                    1/1     Running     3 (21h ago)   2d    10.42.0.17   controlplane   <none>           <none>
kube-system   svclb-traefik-a0b18cd9-84llx                       2/2     Running     4 (21h ago)   2d    10.42.0.15   controlplane   <none>           <none>
kube-system   svclb-traefik-a0b18cd9-8bq4b                       2/2     Running     4 (83m ago)   47h   10.42.2.9    observatory    <none>           <none>
kube-system   svclb-traefik-a0b18cd9-8kl9q                       2/2     Running     4 (83m ago)   47h   10.42.4.10   aiops          <none>           <none>
kube-system   svclb-traefik-a0b18cd9-97mzp                       2/2     Running     4 (83m ago)   47h   10.42.1.10   ollama         <none>           <none>
kube-system   svclb-traefik-a0b18cd9-cgchc                       2/2     Running     4 (83m ago)   47h   10.42.3.9    app            <none>           <none>
kube-system   traefik-9bcdbbd9-8cp7j                             1/1     Running     2 (21h ago)   2d    10.42.0.19   controlplane   <none>           <none>
```

## Services

```text
NAMESPACE     NAME                                      TYPE           CLUSTER-IP      EXTERNAL-IP                                             PORT(S)                      AGE
argocd        argocd-applicationset-controller          ClusterIP      10.43.171.198   <none>                                                  7000/TCP,8080/TCP            46h
argocd        argocd-dex-server                         ClusterIP      10.43.143.99    <none>                                                  5556/TCP,5557/TCP,5558/TCP   46h
argocd        argocd-metrics                            ClusterIP      10.43.217.189   <none>                                                  8082/TCP                     46h
argocd        argocd-notifications-controller-metrics   ClusterIP      10.43.106.30    <none>                                                  9001/TCP                     46h
argocd        argocd-redis                              ClusterIP      10.43.154.77    <none>                                                  6379/TCP                     46h
argocd        argocd-repo-server                        ClusterIP      10.43.194.233   <none>                                                  8081/TCP,8084/TCP            46h
argocd        argocd-server                             ClusterIP      10.43.39.190    <none>                                                  80/TCP,443/TCP               46h
argocd        argocd-server-metrics                     ClusterIP      10.43.202.94    <none>                                                  8083/TCP                     46h
bankapp       bankapp-mysql                             ClusterIP      10.43.229.23    <none>                                                  3306/TCP                     23h
bankapp       banking-app-service                       ClusterIP      10.43.199.118   <none>                                                  80/TCP                       23h
bankapp       banking-backend                           ClusterIP      10.43.239.76    <none>                                                  8080/TCP                     23h
bankapp       banking-frontend                          ClusterIP      10.43.106.92    <none>                                                  80/TCP                       23h
default       kubernetes                                ClusterIP      10.43.0.1       <none>                                                  443/TCP                      2d
kube-system   kube-dns                                  ClusterIP      10.43.0.10      <none>                                                  53/UDP,53/TCP,9153/TCP       2d
kube-system   metrics-server                            ClusterIP      10.43.254.66    <none>                                                  443/TCP                      2d
kube-system   traefik                                   LoadBalancer   10.43.116.6     10.0.1.120,10.0.1.184,10.0.1.233,10.0.1.245,10.0.1.79   80:32653/TCP,443:32669/TCP   2d
```

## PVCs

```text
NAMESPACE   NAME                 STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
bankapp     bankapp-mysql-data   Bound    pvc-af4a219a-9897-44fa-8c3f-3e742f930517   2Gi        RWO            local-path     <unset>                 23h
```

## Storage Classes

```text
NAME                   PROVISIONER             RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION   AGE
local-path (default)   rancher.io/local-path   Delete          WaitForFirstConsumer   false                  2d
```

## Top Nodes

```text
NAME           CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)
aiops          12m          0%       1137Mi          19%
app            15m          0%       1542Mi          26%
controlplane   67m          3%       2248Mi          37%
observatory    13m          0%       1336Mi          22%
ollama         24m          1%       1676Mi          28%
```

## Top Pods

```text
NAMESPACE     NAME                                               CPU(cores)   MEMORY(bytes)
argocd        argocd-application-controller-0                    2m           170Mi
argocd        argocd-applicationset-controller-b7669f646-f4szl   1m           158Mi
argocd        argocd-dex-server-569b757-jh98b                    1m           154Mi
argocd        argocd-notifications-controller-58ff87546-cjc7w    1m           82Mi
argocd        argocd-redis-b9496d8bf-hcl9w                       4m           41Mi
argocd        argocd-repo-server-75ffcfc9df-nhsbt                1m           68Mi
argocd        argocd-server-76755b46f8-l75x8                     1m           160Mi
bankapp       bankapp-mysql-67df8b4f8c-g9tdz                     8m           515Mi
bankapp       banking-backend-84674d78d5-c5dr7                   2m           281Mi
bankapp       banking-frontend-76849d58c7-pft5d                  1m           11Mi
kube-system   coredns-8db54c48d-8gw74                            2m           83Mi
kube-system   local-path-provisioner-5d9d9885bc-x26t5            1m           57Mi
kube-system   metrics-server-786d997795-trrhp                    4m           88Mi
kube-system   svclb-traefik-a0b18cd9-84llx                       0m           1Mi
kube-system   svclb-traefik-a0b18cd9-8bq4b                       0m           2Mi
kube-system   svclb-traefik-a0b18cd9-8kl9q                       0m           2Mi
kube-system   svclb-traefik-a0b18cd9-97mzp                       0m           2Mi
kube-system   svclb-traefik-a0b18cd9-cgchc                       0m           2Mi
kube-system   traefik-9bcdbbd9-8cp7j                             1m           165Mi
```

## Argo Applications

```text
NAMESPACE   NAME      SYNC STATUS   HEALTH STATUS   REVISION                                   PROJECT
argocd      bankapp   OutOfSync     Healthy         26a626c7e811f2c12451a8fdcaacefea42a2fc89   default
```

## BankApp Status

```json
{
  "sync": "OutOfSync",
  "health": "Healthy",
  "out_of_sync_resources": [
    {
      "kind": "Deployment",
      "namespace": "bankapp",
      "name": "banking-backend"
    }
  ]
}
```

## Observability Namespace Status

```text
Error from server (NotFound): namespaces "observability" not found
```
