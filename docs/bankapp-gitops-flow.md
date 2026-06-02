# BankApp GitOps Flow

## Current Status

BankApp deployment is intentionally paused while the live application is debugged separately for API and CORS behavior. The repository now contains a future Argo CD `Application` template at:

```text
gitops/apps/bankapp/application.yaml
```

Do not create that Application in the cluster until the live BankApp issues are resolved, the real Git repository URL is known, and the image references are replaced with approved image names.

## GitHub Actions to Registry to Argo CD

The future deployment flow should be:

1. A developer merges application code to the chosen release branch.
2. GitHub Actions runs tests and builds frontend and backend container images.
3. GitHub Actions pushes immutable image tags to the approved container registry.
4. The GitOps repository is updated with the new image tags.
5. Argo CD detects the GitOps change.
6. An operator reviews the diff in Argo CD.
7. An operator runs a manual sync.

This keeps the cluster state driven by Git while avoiding automatic rollout during the early lab phase.

## Image Update Strategy

Use immutable image tags for BankApp releases. A commit SHA, build number, or semantic version tag is acceptable after the registry and release process are defined.

Do not use `latest` for GitOps-managed deployments. Do not invent image names in manifests. Keep placeholder image values until the real registry, repository names, and tag policy are known.

Recommended future options:

- Update Kustomize image fields in Git after CI publishes a new image.
- Use a controlled pull request from CI to change image tags.
- Consider Argo CD Image Updater later only after registry access, tag policy, and rollback behavior are documented.

## Manual Sync Strategy

Argo CD automated sync must remain disabled for BankApp until the deployment path is proven.

Manual rollout steps should be:

1. Confirm the active Argo CD Application points at the expected repository, branch, and path.
2. Review the Argo CD diff.
3. Confirm the target namespace is `bankapp`.
4. Run a manual sync from the Argo CD UI or CLI.
5. Watch deployment health, pod readiness, services, and application logs.
6. Leave auto-prune and self-heal disabled unless a later phase explicitly enables them.

## Rollback Strategy

Prefer Git-based rollback:

1. Revert the GitOps commit that changed the image tag or manifest.
2. Let Argo CD detect the reverted desired state.
3. Review the Argo CD diff.
4. Run a manual sync.
5. Verify BankApp readiness and API behavior.

For an urgent rollback, an operator may use Argo CD history and rollback features, then reconcile Git so the repository matches the intended cluster state.

## Phase 3 Observability Preparation

No Prometheus, Grafana, Loki, dashboards, scrape targets, or alerts should be installed as part of this GitOps cleanup.

Before Phase 3 starts, document:

- Namespaces and labels that observability tools should watch.
- BankApp metrics endpoint paths and ports, if any.
- Log fields that help debug API, CORS, and dependency failures.
- Alert ownership and severity conventions.
- Dashboard scope for cluster health, Argo CD health, and BankApp health.

Keep observability changes declarative and reviewable when that phase begins.
