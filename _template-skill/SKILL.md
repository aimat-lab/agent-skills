---
name: template-skill
description: >-
  REPLACE ME. One or two sentences: what this skill does AND when an agent
  should use it. Lead with the capability, then list concrete trigger terms the
  user would say (tool/code names, file types, commands, domain words) so the
  agent matches it reliably.
---

# <Skill title>

> Delete this template guidance as you fill the file in. Keep the headings that
> are useful for your skill; remove the rest. One skill = one task.

## When to use this

Briefly: the situation that should trigger this skill, and — if helpful — when
*not* to use it (point to a sibling skill instead).

## Preconditions

What must be true before starting. For example:

- Required software / modules loaded (e.g. a specific code and version).
- Input files that must already exist.
- Environment, accounts, or credentials needed.
- Whether this is machine-specific (name the cluster/host if so).

## Procedure

A numbered, followable sequence. Be concrete.

1. First step. Show the exact command or file edit when there is one.
2. Next step. Call out the parameters that typically change:
   ```bash
   # example — adjust <PLACEHOLDERS>
   some-command --input <FILE> --param <VALUE>
   ```
3. ...

## Verifying success

How to tell it worked: expected output, files produced, a check to run.

## Common pitfalls

- Symptom → cause → fix.
- Anything destructive or expensive that warrants confirming with the user first.

## References

Point to longer material kept alongside the skill, e.g.
`references/<topic>.md`, or external documentation links.
