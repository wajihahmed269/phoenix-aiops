# Governed Remediation Engine

Phoenix-Ops now adds a governed remediation layer on top of the existing read-only intelligence pipeline.

The design goal is not autonomous repair. The design goal is a bounded, deterministic, human-approved remediation path that can later support fallback survivability without turning the platform into unrestricted infrastructure automation.

Core properties:

- remediation actions come only from a static catalog
- plan generation is deterministic
- approval is explicit and time-bound
- execution guardrails evaluate namespace, blast radius, duplicate runs, cluster reachability, and simulation mode
- snapshot capture runs before any execution attempt
- execution audit records are append-only
- verification remains separate from execution

Execution stays disabled by default through config. Simulation mode stays enabled by default.
