# Marp slide creation best practices

Adapted from the supplied best-practices notes for concise scientific reports.

## One slide, one message

Use a concise `##` title that identifies the message or subject. State a finding
in the title when the evidence supports it. A method, definition or experimental
setup can have a direct subject title. Avoid titles that merely announce what
will be explained.

Arrange slides in the order needed to understand the research. Include an agenda,
cover or summary only when useful; a short report does not need all three.
Keep the report readable without a presenter. Do not spread a single static
explanation over repeated reveal slides.

## Prefer useful visual explanations

Before writing a text-only slide, consider what relationship could be shown:

| Information | Possible visual |
| --- | --- |
| Quantitative result or comparison | Plot from real data, or a compact table |
| Method, workflow or experimental setup | Simple SVG or diagram of the relevant steps and relationships |
| Observation or qualitative result | Image with meaningful labels or annotations |
| Mathematical relationship | Equation with the important term highlighted |
| Categories, differences or dependencies | Comparison table or labeled schematic |

Use the visual to explain the slide's message, not to fill empty space. If a
visual adds no information, concise text is acceptable. Do not invent data or
imply a mechanism just to illustrate a finding. Conceptual diagrams need labels
that distinguish them from observed results. Retain editable diagram or plot
sources where practical.

## Simple layout

Start with `theme: default`, `paginate: true` and the theme's own typography.
Do not add a bespoke palette, background texture, card grid, progress bar or
custom font system by default.

For a figure and interpretation, place the figure on the left and bullets on
the right using Marp's split background:

```markdown
![bg left:50% fit](figures/result.svg)

## Main finding

- State what the figure shows.
- Explain the relevant comparison.
- Include the qualification that affects the conclusion.

<small>[1] Source or experiment identifier.</small>
```

The title also occupies the right text region. Keep it short. Start with half
of the slide for the figure and adjust the split if needed. Use `fit` to keep the
whole figure visible. Place its caption and source in the text region. If the
figure needs the full slide width, use a large inline image with a short caption
instead. Do not force a wide chart into a narrow half-slide.

For math, use a short introductory sentence, a displayed equation, and a brief
interpretation or symbol definitions below. Equations can be the main visual;
there is no need for an unrelated picture on the same slide.

## Concise text and whitespace

Use short, parallel bullets. Three to five is a useful upper working range,
not a required count; two clear bullets may be enough. Avoid deep nesting and
long prose broken into bullet fragments. Preserve important scientific context
rather than obeying a word count mechanically.

Allow whitespace around the evidence and explanation. Remove redundant text or
split an overloaded slide before reducing font sizes. Use smaller text locally
for a short citation, symbol key or supporting detail, while keeping it readable
at normal PDF viewing size. Essential caveats should not become fine print.

## Color and emphasis

Use bold for a few key words and one or two accent colors only when they encode
meaning. Match an equation term's color to the corresponding text explanation.
Keep meanings consistent across related slides and retain labels so color is
not the only distinguishing cue. See [advanced features](advanced.md) for syntax.

Preserve the default theme's colors. The palette and pixel sizes in the supplied
notes belonged to another theme and are not defaults for this skill.

## Review

- Does each slide have one identifiable message?
- Does the visual explain that message, and is it readable?
- Could a text-heavy slide become clearer through a diagram, equation or table?
- Are the title, bullets and figure complementary rather than repetitive?
- Are evidence, sources and consequential qualifications visible?
- Is there enough whitespace without excessive styling?
- Does the exported PDF preserve images, equations and page numbers?
