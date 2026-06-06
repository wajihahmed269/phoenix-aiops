# OCI K3s Cluster Status

Phoenix-Ops OCI K3s cluster is operational.

## Nodes

All five nodes are Ready.

## Access

Use SSH tunnel:

./scripts/oci-k3s-tunnel.sh

Then:

export KUBECONFIG=~/.kube/phoenix-k3s-oci.yaml
kubectl get nodes
kubectl get pods -A

## Firewall Fix

OCI Ubuntu blocked private node-to-node TCP traffic.

Live fix applied:
iptables INPUT allow source 10.0.0.0/16

Permanent fix:
ansible/roles/oci_private_firewall/

This allows only private VCN traffic and does not expose public access.

## Next Phase

Restore Argo CD on OCI.
