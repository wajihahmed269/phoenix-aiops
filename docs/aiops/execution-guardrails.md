# Execution Guardrails

Phoenix-Ops execution guardrails exist to stop unsafe remediation before any mutation is attempted.

Current checks include:

- valid approval present and unexpired
- remediation namespace allowlist
- protected namespace blocking
- cluster API reachability
- duplicate execution prevention
- blast radius threshold enforcement
- simulation-only enforcement
- executable catalog entry enforcement

The runner also keeps an explicit kubectl allowlist. Commands outside the bounded verb set are rejected before subprocess execution.

This means K8sGPT findings, summaries, or operator convenience paths cannot bypass the guard system.
