# Remediation Catalog Design

Phoenix-Ops uses a static remediation catalog because unrestricted command synthesis is unsafe.

Each catalog entry defines:

- remediation id
- namespace and resource constraints
- risk class and blast radius
- rollback posture
- verification expectations
- timeout and cooldown values
- approval level
- whether the action is executable in the current phase

This allows Phoenix-Ops to distinguish between:

- cataloged but non-executable future actions
- cataloged and executable bounded actions

That distinction is important. The platform can reason about future rollback or rollout actions without silently enabling them.
