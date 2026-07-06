# Template skill

> This folder is a **template**, not a real skill. Copy it to start a new one:
> `cp -r _template-skill my-new-skill`. See the repo's
> [`CONTRIBUTING.md`](../CONTRIBUTING.md) for the full guide.

## Summary

One line: what the skill does.

## When to use it

- Use it when … (the triggering situation).
- Don't use it when … (point to the right skill instead, if any).

## Dependencies

What a user needs installed/available for this skill to work (codes, modules,
accounts, cluster access). Remove if none.

## Install

Copy or symlink this folder into your agent's skills directory. For Claude Code
that is `~/.claude/skills/`:

```bash
# copy (frozen at install time)
cp -r my-new-skill ~/.claude/skills/

# or symlink (auto-updates on git pull) — recommended
ln -s "$(pwd)/my-new-skill" ~/.claude/skills/my-new-skill
```
