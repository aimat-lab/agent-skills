# pytorch-to-static-site skill

Assess feasibility and port PyTorch inference pipelines to a fully static browser site using ONNX export, ONNX Runtime Web, and static web hosts like GitHub Pages.

## When to use it

Use it when you want to run PyTorch model inference directly in the browser without a backend server, publish an ML demo or playground on GitHub Pages, or export PyTorch models and data artifacts into browser-compatible formats.

Triggers include: `PyTorch`, `ONNX`, `ONNX Runtime Web`, `onnxruntime-web`, `GitHub Pages`, `client-side inference`, `static site ML`, or `WASM`.

Not for: applications that strictly require server-side execution (such as streaming large LLM weights, private server data, or custom CUDA-only kernels with no browser fallbacks).

## Dependencies

- Python environment with `torch`, `onnx`, and `onnxruntime` for model export and numerical equivalence testing (`export_static.py`).
- Frontend development environment for serving `onnxruntime-web` and WASM binaries locally during testing.
- GitHub repository with GitHub Pages enabled if deploying to GitHub Pages via GitHub Actions.

## Contents

- `SKILL.md` — guidelines for feasibility assessment, ONNX asset export, manifest creation, browser frontend implementation, and GitHub Pages deployment.

## Install

Copy or symlink this folder into your agent's skills directory (for Claude Code, `~/.claude/skills/`):

```bash
# copy (frozen at install time)
cp -r pytorch-to-static-site ~/.claude/skills/

# or symlink (auto-updates on git pull) — recommended
ln -s "$(pwd)/pytorch-to-static-site" ~/.claude/skills/pytorch-to-static-site
```
