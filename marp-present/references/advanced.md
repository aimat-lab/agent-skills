# Marp advanced features

Adapted from the supplied advanced-features notes. Use only the features the
report needs; ordinary slides should retain the default theme. Examples target
Marp CLI 4.5.1 with Marp Core 4.x. Consult matching version documentation when
changing the toolchain.

## Math between explanatory text

Set `math: katex` in frontmatter. Use `$...$` inline and `$$...$$` for a displayed
equation. Define symbols near their first use. For example:

```markdown
## Regularization adds a penalty

The objective combines data fit with a penalty on parameter magnitude.

$$
\mathcal{L}(\theta) = \mathcal{L}_{\mathrm{data}}(\theta)
+ \textcolor{#a84e00}{\lambda \lVert\theta\rVert_2^2}
$$

- $\theta$: model parameters.
- <span style="color: #a84e00;">The penalty term</span> discourages large weights; $\lambda$ sets its strength.
```

`\textcolor{#a84e00}{...}` colors only its argument. Prefer it to a bare `\color`
command whose scope is easier to extend accidentally. One or two purposeful
colors are enough. For a second contrasting term, a dark blue such as `#245b87`
works on the default light background. Label each term as well as coloring it.
HTML spans require the CLI's `--html` option; math color commands do not.

### Aligned equations and annotations

```markdown
$$
\begin{aligned}
  f(x) &= x^2 + 2x + 1 \\
       &= (x + 1)^2
\end{aligned}
$$

$$
\mathcal{L} = \underbrace{\mathcal{L}_{\mathrm{data}}}_{\text{data fit}}
+ \underbrace{\textcolor{#a84e00}{\lambda R}}_{\text{penalty}}
$$
```

Use alignment or a short brace label when it clarifies the relationship. Avoid
long derivations on one slide. KaTeX supports a subset of LaTeX; check the
[supported functions](https://katex.org/docs/supported.html) for unfamiliar syntax.

### Local sizing

Keep the theme's normal sizes first. A short secondary formula can use a grouped
size command, without shrinking equations throughout the report:

```markdown
$$
{\small \mathrm{RMSE} = \sqrt{\frac{1}{n}\sum_{i=1}^{n}(y_i-\hat y_i)^2}}
$$
```

For a citation or a short symbol key, use `<small>...</small>`. If one slide needs
a modest adjustment, scope it to that slide rather than overriding the theme:

```html
<style scoped>
  small { font-size: 0.7em; }
</style>
```

Do not rely on automatic scaling to fit arbitrary content. Core 4.x scales
certain elements horizontally, including math and code; that does not guarantee
that the whole slide fits vertically. Split crowded content and inspect the PDF.
Avoid generic CSS class names such as `.accent`, which can collide with KaTeX.

## Images, SVGs and diagrams

Use local, relative paths and preserve proportions:

```markdown
![bg left:50% fit](figures/method.svg)

![w:900](figures/wide-result.png)
```

Use these as alternative layouts. `bg left` reserves the left region for an
image and puts text on the right. `fit` keeps the whole background image visible.
For inline images, set one dimension (`w:` or `h:`) unless both are intentional.

An SVG should have a `viewBox`, readable labels, and no external fonts or linked
assets needed to display it. Keep diagram source files. For the documented Core
4.x workflow, render Mermaid or other diagram source to SVG/PNG before embedding;
do not assume a fenced diagram will be rendered by the installed Marp version.

## HTML and static output

Use HTML sparingly for colored spans or small supporting text. Marp CLI's
`--html` flag permits HTML in Markdown. It does not mean “standalone HTML using
a CDN.” Normal Markdown is easier to maintain than custom layout containers.

Use `-` for ordinary bullets. `*` marks fragmented lists, whose reveal behavior
depends on the HTML presentation app. A static PDF displays their content
without interactive reveals. Do not use fragmentation for reports.

Use `paginate: true` for page numbers. `--pdf-notes` adds presenter-note
annotations to a PDF; it does not remove page numbers. Keep essential sources
and explanations visible on the slide, not only in comments or PDF annotations.

## References

- [Marp Core 4.x: math, themes and scaling](https://github.com/marp-team/marp-core/tree/v4)
- [KaTeX supported functions](https://katex.org/docs/supported.html)
- [Marpit image syntax](https://marpit.marp.app/image-syntax)
- [Fragmented lists](https://marpit.marp.app/fragmented-list)
- [Marp CLI](https://github.com/marp-team/marp-cli); see [local export commands](marp-workflow.md)
