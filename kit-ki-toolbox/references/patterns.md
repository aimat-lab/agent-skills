# Reliable Inference Patterns

## Final Answers and Reasoning Blocks

Some models put reasoning in `<think>…</think>` blocks in their text output.
Use `clean_reasoning_tags()` from
[toolbox_client.py](../examples/toolbox_client.py) to remove complete blocks.
The helper raises `IncompleteResponseError` if blocks are unclosed or no final
answer remains. Never fall back to the original reasoning or parse JSON from it.
The client also rejects missing choices and any completion whose `finish_reason`
is not `stop`, including answers truncated by the token limit. Increase the
output budget deliberately if the task needs more tokens. Streaming and tool
execution are outside this text helper's scope.

## JSON Parsing and Validation

`extract_json_object()` first parses the complete response so that an array such
as `[{"id": 1}]` stays an array. If necessary, it accepts a single fenced JSON
block or a single container surrounded by prose. Malformed outer containers and
ambiguous fragments are rejected instead of salvaging an inner object. Scalars
and non-finite numbers are rejected.

Valid JSON does not establish the shape or meaning required by a task. Supply a
validator to `structured_json()` that raises `ValueError` for invalid fields or
types. For example, with `toolbox_client.py` on the Python import path:

```python
from toolbox_client import KIToolboxClient


def validate_decision(value):
    if (not isinstance(value, dict)
            or type(value.get("decision")) is not int
            or value["decision"] not in (0, 1)):
        raise ValueError("Expected an integer decision of 0 or 1.")


with KIToolboxClient() as client:
    result = client.structured_json(
        'Classify this item. Respond with {"decision": 0 or 1}.',
        validator=validate_decision,
        max_json_attempts=2,
    )
```

The requested temperature is preserved for every attempt. Parsing, validation,
and incomplete-answer failures consume the explicit `max_json_attempts` budget;
permanent API errors propagate immediately. Logs contain status and attempt
counts, not raw responses or exception bodies. Callers should likewise avoid
logging SDK exception bodies or validator messages containing private input.

## Discovery and Routing

Both the client and [smoke test](../examples/smoke_test.py) use the same model
checks. A selected model must exist in the fetched catalogue, even when external
routing is authorized. Discovery is cached per client; call
`client.list_models(refresh=True)` to refresh it. Do not discover repeatedly for
each batch item. Use a new client or explicitly refresh a long-lived client when
the service catalogue changes.

Without an explicit model, the client prefers `alias.simple-local`, then a small
set of known local chat alternatives that are present in the catalogue. It does
not choose an arbitrary embedding, audio, or image model as a chat fallback.
If none is available, inspect `--list-only` output and select a chat ID explicitly.
For external or unknown routing, set `allow_external=True` (or CLI
`--allow-external`) only when the user has authorized that routing. No automatic
external fallback is performed. Missing routing metadata uses only documented
KIT ID conventions, with the distinct label `local-by-name`; unknown or
conflicting values do not silently become local.

## Timeouts, Retries and Batch Limits

The OpenAI SDK's own retries are disabled so retry loops do not multiply.
`max_retries=3` retains this helper's original meaning of **three total HTTP
attempts per operation**, not three retries after the first request. Requests
have a 60-second timeout by default. Connection/timeout failures and HTTP
408, 409, 429, and 5xx responses are retryable. Authentication, permission,
invalid-request, and programming errors are not retried.

Transient failures use exponential backoff with jitter, capped by
`max_retry_delay=30` seconds. `Retry-After` is respected; if it exceeds that wait
budget, the error propagates so the caller can defer the work. With structured
extraction the maximum is `max_json_attempts * max_retries` completion HTTP
attempts, plus initial discovery (also bounded by `max_retries`).

Start with at most 4 workers for interactive jobs. The helper accepts 1–16 batch
workers and preserves input order. These are conservative client limits, not SCC
service guarantees. Consult [KIT's API guide](https://www.zml.kit.edu/downloads/KI.Toolbox_API.pdf)
before planning large automated workloads. Worker failures propagate to the
caller; batch execution is not transactional and already submitted tasks may
finish.

Run offline regressions from the skill directory with:

```bash
python3 -m unittest discover -s tests -v
```

The tests use the installed OpenAI SDK with an in-memory HTTP transport and do
not require a KIT token or send requests to KIT.
