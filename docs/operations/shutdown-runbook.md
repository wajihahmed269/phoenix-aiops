# Shutdown Runbook

Shutdown is read-only with respect to the cluster. No live remediation changes are part of this phase.

## Stop The Lab

```bash
scripts/oci-stop-lab.sh
```

## Optional Status Check

```bash
scripts/oci-status-lab.sh
```

## Cleanup Notes

- Close the `scripts/oci-k3s-tunnel.sh` session if it is still open.
- Confirm there are no lingering port-forwards before stopping work.
- Leave incident artifacts and runtime files intact unless they are temporary demo outputs.
