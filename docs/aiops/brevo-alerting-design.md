# Brevo Alerting Design

Phoenix-Ops alerting stays advisory-first in this phase.

The notification path now:

1. Loads alert configuration from `.env.aiops` through environment variables.
2. Validates required keys before sending.
3. Builds a bounded incident email from structured recommendation data.
4. Uses a provider abstraction with Brevo support and dry-run behavior.
5. Records notification results in `incident-artifacts/<incident-id>/notifications.log`.

Safety constraints:

- Dry-run remains supported through `ALERT_DRY_RUN=true`.
- Missing env values fail safe and block delivery.
- Brevo delivery uses bounded timeout and retry settings from config.
- Notification payloads exclude secrets, raw dumps, full logs, and unbounded stderr.
- Notification failures degrade gracefully and do not stop incident persistence.
