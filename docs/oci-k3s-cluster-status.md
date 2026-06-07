# OCI K3s Cluster Status

## Status

Phoenix-Ops OCI K3s cluster is operational.

## Nodes

| Node | Role | Private IP | Status |
| --- | --- | --- | --- |
| phoenix-node-control-plane | control-plane | 10.0.1.79 | Ready |
| phoenix-node-app | app | 10.0.1.120 | Ready |
| phoenix-node-observatory | observability | 10.0.1.233 | Ready |
| phoenix-node-ai-ops | ai-ops | 10.0.1.245 | Ready |
| phoenix-node-ollama | ollama | 10.0.1.184 | Ready |

## Access Model

Kubernetes API port 6443 is not public.

Use SSH tunnel:

```bash
./scripts/oci-k3s-tunnel.sh
