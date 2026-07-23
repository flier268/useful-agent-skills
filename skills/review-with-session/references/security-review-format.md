# Security Audit

Use `audit:project` with `--security`.
Keep the requested project paths as the security boundary.
Use the normal session files and P0 through P3 priorities.

Check reachable trust boundaries.
Check input validation, authentication, authorization, secret handling, file access, network exposure, unsafe deserialization, injection, and repeated vulnerable patterns.
Confirm the exploit or failure path from code before recording a finding.
Do not report a checklist item without a concrete defect.

Use the normal finding title:

```md
## F-001 [P1] Reject traversal outside the export root — src/export.py:42

<Trigger, unsafe behavior, impact, and evidence.>

### Trust boundary

<The boundary crossed by untrusted data.>

### Remediation

<The required fix direction.>
```

Keep repeated-pattern checks in `checked-paths.md`.
Keep unfinished boundaries in `next-steps.md`.
Report security findings before non-security audit notes.
