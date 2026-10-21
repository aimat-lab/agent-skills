---
name: marp-present
description: >-
  Create illustrated scientific reports and research presentations in Marp
  Markdown with PDF output. Use for condensed paper summaries, experiment
  reports, method explanations, result comparisons and research updates,
  or to revise an existing Marp report.
---

# Illustrated scientific reports with Marp

Deliver an editable Markdown report, its local visual assets and a checked PDF.
Default to self-contained, static slides that can be understood without a
presenter. Use Marp's **default theme with page numbers**, minimal styling and
**one message per slide**. Do not add incremental builds unless requested.

## Workflow

1. Inspect the supplied material. Identify the research question, evidence,
   findings and limitations. Distinguish published results, the user's experiments
   and your interpretation. Preserve requested scope and length.
2. Read [best practices](references/best-practices.md). Plan each slide around a
   message and a useful visual: a plot, image, SVG, diagram, table or equation.
   If no image exists, consider whether a simple schematic or mathematical
   relationship would explain the information better. Use text alone when a
   visual would be forced or misleading.
3. Copy the [starter](assets/report-starter.md) and its `figures/` folder to the
   report directory. Replace the illustrative content and remove unused assets.
   Prefer `![bg left:50% fit](figures/figure.svg)` with a concise title and bullets
   on the right. For math, place the equation between explanatory text and use
   restrained color to connect terms to their meaning. Adapt the layout when
   the content needs more space rather than adding a custom design system.
4. Read [advanced features](references/advanced.md) when using math coloring,
   local sizing, SVGs or HTML. Keep the default typography and palette unless
   a local adjustment materially improves readability or the user asks otherwise.
5. Export and inspect using [the rendering workflow](references/marp-workflow.md).
   Check every PDF page for missing figures, clipped content, unreadable labels,
   broken math and scientific meaning. Shorten or split crowded content before
   shrinking it. Re-render after layout fixes.

## Scientific content

- Use real data for quantitative plots and supplied or sourced images for
  observations. Label conceptual schematics and illustrative examples. Never
  invent measurements, exact values read from pixels, sources or uncertainty.
- Identify the comparison, metric, units and evaluation conditions needed to
  interpret a result. Explain uncertainty marks and sample counts when available;
  flag missing information when it limits the conclusion.
- Keep axes, legends and conditions legible. Preserve relevant comparison groups
  and qualifications. Use consistent scales and visual meanings across related
  figures, or clearly explain differences.
- State what the evidence supports. Distinguish a measured difference from a
  proposed explanation, and keep consequential limitations visible on the slide.
- Put short source citations beside claims and adapted figures, with complete
  references or links elsewhere in the report. Identify local experiment inputs
  where relevant. Essential explanations and citations must not exist only in
  HTML comments, which do not appear on ordinary PDF pages.

## Delivery

Provide the Markdown, PDF and assets needed to rebuild it, including editable
figure sources when available. Record the export command and Marp version when
reproducibility matters. If rendering fails, preserve the source and identify
what is missing; do not claim that export or visual inspection succeeded.
