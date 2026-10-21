# Marp authoring and rendering

## Source and dependencies

Keep `report.md` and a local `figures/` directory together. Copy the
[starter](../assets/report-starter.md) and its `figures/` directory, then replace
the illustrative content. It uses the built-in default theme with page numbers,
without a custom stylesheet. Use paths relative to the Markdown file.

Use `---` on its own line between slides. Write paragraphs on a single source
line when you do not want forced line breaks. For math and image syntax, see
[advanced features](advanced.md).

Use an existing Marp installation when available. Otherwise the pinned commands
below use CLI 4.5.1. PDF/image export needs a supported browser such as Chrome,
Edge or Firefox. Record the version used; for a sustained project, use a local
development dependency and lockfile. Avoid external fonts and image URLs when
the report needs to rebuild offline.

## Export

Run from the report directory:

```bash
npx --yes @marp-team/marp-cli@4.5.1 --version
npx --yes @marp-team/marp-cli@4.5.1 report.md --html -o report.html
npx --yes @marp-team/marp-cli@4.5.1 report.md --html --pdf --allow-local-files -o report.pdf
```

`--html` permits HTML markup such as colored spans. `--allow-local-files` lets
the conversion browser load local assets; use it with inspected source and
assets. Distribute local figures with Markdown and HTML, since HTML export does
not bundle them. The PDF contains rendered figures.

For multiple source files and a corresponding output directory, use directory
mode rather than a glob with a single `-o` destination:

```bash
npx --yes @marp-team/marp-cli@4.5.1 --input-dir reports --output rendered --pdf --html --allow-local-files
```

## Inspect the PDF

Open the PDF in a viewer or render it with Poppler:

```bash
mkdir -p review
pdftoppm -scale-to 1600 -png report.pdf review/page
```

Inspect every page at a readable size. Confirm the intended figure/text balance,
legible axes and sources, correct colored math, page numbers and no overflow.
Review neighboring pages for continuity. Fix and re-render affected content.

For faster iteration, Marp also renders numbered slide images:

```bash
npx --yes @marp-team/marp-cli@4.5.1 report.md --html --allow-local-files --images png -o review/slide.png
```

`--image` renders only the first slide; `--images` renders all slides. A successful
command alone does not prove the layout is readable.

## Troubleshooting

| Symptom | Correction |
| --- | --- |
| Missing local figures | Check relative paths, conversion warnings and `--allow-local-files`. |
| Browser unavailable | Locate a supported browser. Set `BROWSER_PATH` to its executable if discovery fails. |
| HTML shown literally or missing | Check `--html` and HTML block boundaries. |
| Figure too small in a split slide | Adjust the split or use a full-width inline image with a short caption. |
| Crowded text or clipped math | Shorten, split, or simplify before making a small local size adjustment. |
| Unexpected styling in math | Remove broad CSS overrides and check for class names colliding with KaTeX. |

[Official Marp CLI documentation](https://github.com/marp-team/marp-cli) describes
version-specific browser and export options.
