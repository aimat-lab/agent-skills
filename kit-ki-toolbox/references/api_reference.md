# KIT KI Toolbox API Reference

The KIT KI Toolbox endpoint provides OpenAI-compatible REST endpoints hosted on
SCC infrastructure.

- **Base URL**: `https://ki-toolbox.scc.kit.edu/api/v1`
- **Protocol**: HTTPS
- **Authentication**: Bearer Token via `KIT_KI_API`

```http
Authorization: Bearer <KIT_KI_API>
Content-Type: application/json
```

---

## Endpoints

### `GET /models`

Retrieves the list of currently deployed and accessible models.

```bash
curl -s -H "Authorization: Bearer $KIT_KI_API" \
  https://ki-toolbox.scc.kit.edu/api/v1/models
```

Illustrative response (additional fields and routing metadata may vary):
```json
{
  "object": "list",
  "data": [
    {
      "id": "kit.deepseek-v4-flash",
      "name": "DeepSeek V4 Flash",
      "connection_type": "local"
    }
  ]
}
```

Do not assume every catalogue entry supplies `connection_type`. When present,
`"local"` identifies local routing and `"external"` identifies external routing.
The helpers inspect this optional field at the top level and inside `info`,
`openai`, and `meta`; these are defensive compatibility paths, not a guaranteed
KIT schema. Explicit external metadata takes precedence, and unrecognized
metadata values remain unknown. If metadata is missing, only documented local
ID conventions are accepted as a `local-by-name` fallback. Confirm deployment
routing with KIT documentation when handling sensitive data.

---

### `POST /chat/completions`

Standard OpenAI chat completion schema:

| Field | Type | Required | Notes |
| :--- | :--- | :--- | :--- |
| `model` | string | ✓ | e.g. `kit.deepseek-v4-flash` |
| `messages` | array | ✓ | `[{"role": "system"|"user"|"assistant", "content": "…"}]` |
| `temperature` | float | | `0.0`–`0.2` recommended for deterministic extraction |
| `max_tokens` | integer | | Maximum tokens to generate |
| `stream` | boolean | | SSE streaming; default `false` |

---

## Discover Current Models

Query `GET /models` or use the included
[smoke_test.py](../examples/smoke_test.py) with `--list-only` to retrieve the
models accessible with the current token. From the skill directory, with
`KIT_KI_API` set and the `openai` package installed:

```bash
python3 examples/smoke_test.py --list-only
```

This lists models without sending a completion request. Treat IDs such as
`alias.simple-local` or `kit.deepseek-v4-flash` as examples, and check their
availability in the returned catalogue. Labels distinguish local/external
metadata, `local-by-name` fallback, and unknown routing. Confirm routing and
capabilities against
[KIT's current model documentation](https://www.scc.kit.edu/en/services/ki-toolbox.php).
For API usage and model aliases, see
[KIT's API guide](https://www.zml.kit.edu/downloads/KI.Toolbox_API.pdf).

External models send requests outside KIT infrastructure and require explicit
user consent under this skill's local-model policy.

---

## Common Error Codes

| Status | Meaning | Remedy |
| :--- | :--- | :--- |
| `400` | `Model not found` — ID invalid or decommissioned | Query `/models` for current IDs. |
| `401` | Invalid or missing token | Verify `KIT_KI_API` is exported. |
| `429` | Rate limit exceeded | Reduce `batch_size`, add exponential backoff. |
| `502/503/504` | Transient server overload | Retry with exponential backoff. |
