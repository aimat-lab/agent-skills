---
name: kit-ki-toolbox
description: >-
  Interact with the Karlsruhe Institute of Technology (KIT) KI Toolbox
  OpenAI-compatible LLM endpoint (https://ki-toolbox.scc.kit.edu/api/v1). Use when
  querying KIT-hosted language models, running inference or batch extraction on
  SCC infrastructure, testing API connectivity, or configuring OpenAI-compatible
  clients using KIT_KI_API, including connecting Claude Code or other supported
  API formats to KIT through LiteLLM Proxy. Defaults to local models and checks
  model availability and routing before inference.
---

# KIT KI Toolbox Agent Skill

The **KIT KI Toolbox** provides an OpenAI-compatible REST API
(`https://ki-toolbox.scc.kit.edu/api/v1`) hosted on KIT SCC infrastructure.
It exposes locally-hosted open-weight models as well as proxied external
endpoints.

--------------------------------------------------------------------------------

## Golden Rules

1. **Default to local models.** Use an external model only when the user has
   authorized that routing. Check catalogue metadata when available; explicit
   external metadata overrides local-looking names. When metadata is absent,
   the helpers recognize documented `kit.*` IDs and the three local aliases
   (`alias.simple-local`, `alias.medium-local`, `alias.complex-local`). They label
   this fallback `local-by-name`; it is not independent proof of routing. Unknown
   routing is blocked by default. Never silently fall back to an external model.

2. **Discover available models before inference.** Reuse the catalogue within a
   client session and refresh it when availability changes. No live discovery is
   needed merely to write or review code.
   Use [smoke_test.py](./examples/smoke_test.py) with `--list-only`; see
   [Discover Current Models](#discover-current-models) below.

3. **Authenticate via environment variable** `KIT_KI_API`.  Never print, log,
   or hardcode API keys.
   ```bash
   export KIT_KI_API="<your-api-token>"
   ```

4. **Strip `<think>…</think>` tags** before parsing output.  Reasoning models
   (e.g. DeepSeek) emit chain-of-thought traces that must be removed before
   extracting JSON or returning content. Reject unclosed blocks, reasoning-only
   responses, and completions stopped by the token limit. Do not recover answers
   from reasoning text or log raw model outputs on failure.

5. **Bound concurrency and retries.** Start with at most 4 workers for interactive
   work; the helper caps batch concurrency at 16. These are client defaults, not
   published SCC quotas. Retry transient failures only, with timeouts and a finite
   attempt budget. See [patterns.md](./references/patterns.md) for details.

--------------------------------------------------------------------------------

## Minimal Usage (Python)

Run this with `toolbox_client.py` beside your script, or from `examples/`:

```python
from toolbox_client import KIToolboxClient

# Reads KIT_KI_API; discovers the catalogue before the first completion.
# Selects an available local chat default, or pass a discovered model ID.
with KIToolboxClient() as client:
    text = client.prompt("Hello")
    print(text)
```

Check that the token is available without displaying it, discover models, select
an appropriate local chat model, and start with one small request before batching.
For JSON extraction, use `structured_json()` with a validator for the task's
required fields and types; see [patterns.md](./references/patterns.md).

--------------------------------------------------------------------------------

## Discover Current Models

Use the included [smoke_test.py](./examples/smoke_test.py) to list the models
accessible with the current token. With `KIT_KI_API` set and the
`openai` package installed, run this from the skill directory (the directory
containing `SKILL.md`):

```bash
python3 examples/smoke_test.py --list-only
```

`--list-only` fetches and displays the catalogue without running a completion.
Use the returned IDs when selecting a model. Examples include the local alias
`alias.simple-local` and the concrete ID `kit.deepseek-v4-flash`; these are
illustrative, not a maintained inventory or a guarantee of availability.

Confirm model capabilities and local/external routing against
[KIT's model documentation](https://www.scc.kit.edu/en/services/ki-toolbox.php).
The script distinguishes metadata-based routing, the `local-by-name` fallback,
and unknown routing; confirm the fallback before processing sensitive data.
See also [KIT's API guide](https://www.zml.kit.edu/downloads/KI.Toolbox_API.pdf)
and [api_reference.md](./references/api_reference.md).

--------------------------------------------------------------------------------

## Reference Implementations

| File | Purpose |
| :--- | :--- |
| [smoke_test.py](./examples/smoke_test.py) | CLI: list models, validate token, run a test completion |
| [toolbox_client.py](./examples/toolbox_client.py) | Reusable `KIToolboxClient` with local-model guard, retries, `<think>` stripping, batch map, and structured JSON extraction |

--------------------------------------------------------------------------------

## Connect Other Clients Through LiteLLM

For clients that require another supported LLM API format, such as Claude Code's
Anthropic Messages API, use LiteLLM Proxy to translate requests to KIT's
OpenAI-compatible endpoint. See [litellm_proxy.md](./references/litellm_proxy.md)
for the configuration, Pixi launch command, Claude Code settings, and verification.
The client-facing model alias and the actual KIT backend ID can differ.

--------------------------------------------------------------------------------

## Deep-Dive References

- [api_reference.md](./references/api_reference.md) — REST endpoints, headers, error codes, and current-model discovery.
- [patterns.md](./references/patterns.md) — `<think>` handling, JSON extraction strategy, concurrency budgeting.
- [litellm_proxy.md](./references/litellm_proxy.md) — connect Claude Code and other supported API clients through a local protocol bridge.
- [README.md](./README.md) — How to export this skill to other projects or install it globally.
