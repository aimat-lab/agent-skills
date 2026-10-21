# Illustrated scientific reports with Marp

Create concise visual research reports in Markdown and export them to PDF.
Use this skill for paper summaries, experiment reports, method explanations,
result comparisons and research updates.

## Defaults

- Marp's default theme with page numbers and minimal styling.
- One message per static slide, understandable without a presenter.
- A useful image, SVG, diagram, plot, table or equation where it improves the explanation.
- Figures on the left with concise bullets on the right; math between explanatory text.
- Restrained color highlighting and small local size adjustments when needed.
- Text-only slides are acceptable when an illustration would be forced.

The skill includes adapted [best practices](references/best-practices.md),
[advanced features](references/advanced.md) with colored math examples, and a
[rendering workflow](references/marp-workflow.md). The
[starter](assets/report-starter.md) demonstrates a split-background SVG and an
equation. Copy it together with `assets/figures/`, then replace its illustrative
content. No custom theme is needed.

## Dependencies

Node.js and Marp CLI, plus a supported browser for PDF/image export. The workflow
uses Marp CLI 4.5.1. PDF inspection needs a viewer or a rasterizer such as Poppler.
No other agent skill is required. The skill presents supplied evidence; it does
not replace running the underlying scientific analysis.

## Install

From the repository root, copy the folder into your agent's skills directory.
For example, for Claude Code:

```bash
cp -r marp-present ~/.claude/skills/
```

Or symlink it to receive repository updates:

```bash
ln -s "$(pwd)/marp-present" ~/.claude/skills/marp-present
```

Adapt the destination for your agent. Example request:

> Use marp-present to summarize these experiment results as a short illustrated
> report. Include the setup, main comparison, failed cases and conclusions.
> Deliver the Marp source and PDF.
