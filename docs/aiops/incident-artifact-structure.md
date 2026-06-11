# Incident Artifact Structure

Each incident now writes bounded, sanitized artifacts under:

`incident-artifacts/<incident-id>/`

Expected files:

- `summary.md`
- `timeline.md`
- `recommendation.json`
- `evidence.json`
- `k8sgpt.json`
- `notifications.log`

Design notes:

- Incident IDs are sanitized before filesystem use.
- Artifact filenames are allowlisted to prevent path traversal.
- Timeline writes are append-only.
- JSON and text files are size-bounded.
- Write failures remain non-fatal to the polling pipeline.
- K8sGPT unavailability is stored as advisory evidence, not treated as a pipeline failure.
