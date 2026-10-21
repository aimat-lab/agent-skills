# Connect Other Clients Through LiteLLM Proxy

Use this when a client needs an LLM API format other than KIT's OpenAI-compatible
format. For example, Claude Code sends Anthropic Messages requests to
`/v1/messages`; LiteLLM Proxy can translate these to the configured KIT backend.
See [LiteLLM's Claude Code guide](https://docs.litellm.ai/docs/proxy/client_setup/claude_code).
This applies to formats supported by LiteLLM, not arbitrary service APIs.

The request path is:

```text
Client (e.g. Claude Code) -> local LiteLLM Proxy -> KIT KI Toolbox -> KIT model
```

## Configure the KIT Backend

First use [smoke_test.py](../examples/smoke_test.py) with `--list-only` to confirm
the backend model is available and check its routing. The following mapping was
reported to work by the skill's author. Preserve it when reproducing that setup;
choose another discovered KIT model when appropriate.

Save this as `config.yaml` in the directory from which you will start the proxy:

```yaml
model_list:
  - model_name: claude-3-5-sonnet-20241022  # Alias requested by the client
    litellm_params:
      model: "openai/kit.deepseek-v4-flash"  # Actual KIT backend, using OpenAI format
      api_base: "https://ki-toolbox.scc.kit.edu/api/v1"
      api_key: os.environ/KIT_KI_API

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
```

`model_name` is the name the client sends; it does not select Anthropic hosting
or make the backend a Claude model. `litellm_params.model` chooses the backend,
and `openai/` tells LiteLLM which API adapter to use with the supplied `api_base`.
The `os.environ/…` syntax reads secrets from the proxy process's environment.
See [LiteLLM configuration](https://docs.litellm.ai/docs/proxy/configs).

Set `KIT_KI_API` to the KIT token and `LITELLM_MASTER_KEY` to a separate proxy
secret beginning with `sk-`. Do not put either secret in the YAML file. The
example uses the master key for a personal local proxy; shared deployments
should issue scoped client keys rather than distributing an administrative key.

## Start the Proxy

Use a Pixi environment that provides `litellm[proxy]` and a supported Python
version. LiteLLM 1.84.0+ requires Python 3.10+. From the directory containing
`config.yaml`, with both environment variables set, run:

```bash
pixi run litellm --config config.yaml --host 127.0.0.1 --port 4000
```

This runs the proxy on the local machine. For troubleshooting with a synthetic,
non-sensitive prompt, the author's original command adds `--detailed_debug`:

```bash
pixi run litellm --config config.yaml --host 127.0.0.1 --port 4000 --detailed_debug
```

Detailed logs can include request/response contents; leave this flag off for
ordinary use. See [LiteLLM CLI setup](https://docs.litellm.ai/docs/proxy/quick_start).

## Point Claude Code at the Proxy

In the shell used to launch Claude Code, make the same `LITELLM_MASTER_KEY`
available, then run:

```bash
export ANTHROPIC_BASE_URL="http://127.0.0.1:4000"
export ANTHROPIC_AUTH_TOKEN="$LITELLM_MASTER_KEY"
export ANTHROPIC_MODEL="claude-3-5-sonnet-20241022"
unset ANTHROPIC_API_KEY
claude
```

These settings apply to this shell session. The base URL is the proxy root;
Claude Code appends the Anthropic API path. The client receives the proxy key,
while the KIT token stays with LiteLLM. The historical Claude-style alias is kept
to reproduce the author's setup; clients that accept custom names can use a
clearer alias such as `kit-deepseek`, provided `model_name` matches.

If the client sends additional model IDs for auxiliary tasks or model switching,
map those IDs explicitly or configure those tasks to use the defined alias.
Do not add wildcard routes or external fallbacks to fix an alias mismatch.

## Other Services and Verification

For another service, select an API format that LiteLLM exposes, point the service
at the corresponding proxy URL, provide a proxy credential, and set its model
name to the configured alias. Check that service's base-URL convention: some
expect the root URL, others include an API prefix. A remotely hosted service
cannot reach a proxy on your laptop through its own `127.0.0.1`; it needs a
reachable, authenticated deployment with HTTPS and an agreed data path.

Verify with one short synthetic prompt through the consuming client. Confirm
that the requested alias resolves to the intended KIT backend, then check any
features the integration needs, especially streaming and tool calls. Protocol
translation does not guarantee the backend supports every client feature.

This proxy does not call `KIToolboxClient`; its catalogue checks, reasoning
cleanup, output validation, and retry limits do not automatically wrap proxy
traffic. Keep the proxy's model list explicit, retain local routing, and configure
timeouts and retries in LiteLLM or the consuming client as needed. This example
was checked against upstream documentation, not retested against a live KIT
endpoint as part of this update.
