#!/usr/bin/env python3
"""KIT KI Toolbox client with model discovery, bounded retries and JSON extraction."""

from __future__ import annotations

import json
import logging
import math
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Sequence, Union

from openai import APIConnectionError, APIStatusError, OpenAI

BASE_URL = "https://ki-toolbox.scc.kit.edu/api/v1"
MAX_WORKERS = 16  # Client default limit, not a published SCC quota.
LOCAL_ALIASES = {"alias.simple-local", "alias.medium-local", "alias.complex-local"}
DEFAULT_MODELS = ("alias.simple-local", "kit.mistral-small-4-119b-a8b",
                  "alias.medium-local", "kit.deepseek-v4-flash")
logger = logging.getLogger("kit_ki_toolbox")
JSONValue = Union[dict[str, Any], list[Any]]


class IncompleteResponseError(ValueError):
    """The model did not return a complete final answer."""


def is_local_model_id(model_id: str) -> bool:
    """Recognize documented local ID conventions; this alone does not prove routing."""
    return model_id.startswith("kit.") or model_id in LOCAL_ALIASES


def extract_connection_type(model: dict[str, Any]) -> str:
    """Read optional routing metadata, preserving conflicts and unknown values."""
    values: set[str] = set()

    def collect(node: dict[str, Any]) -> None:
        connection = node.get("connection_type")
        if isinstance(connection, str) and connection.strip():
            values.add(connection.strip().lower())
        elif connection is not None and not isinstance(connection, dict):
            values.add("unknown")
        for key in ("connection_type", "info", "openai", "meta"):
            if isinstance(node.get(key), dict):
                collect(node[key])

    collect(model)
    if "external" in values:
        return "external"
    if values == {"local"}:
        return "local"
    return "unknown" if values else "missing"


def model_scope(model_id: str, connection_type: str) -> str:
    """Classify routing conservatively; explicit external metadata always wins."""
    connection = connection_type.strip().lower()
    external_name = (model_id.startswith(("azure.", "google.")) or
                     model_id.endswith(("-gpt", "-claude")))
    if connection == "external" or external_name:
        return "external"
    if connection == "local":
        return "local"
    if connection == "missing" and is_local_model_id(model_id):
        return "local-by-name"
    return "unknown"


def is_local_model(model_id: str, connection_type: str) -> bool:
    return model_scope(model_id, connection_type) in {"local", "local-by-name"}


def clean_reasoning_tags(content: str) -> str:
    """Remove complete think blocks; reject incomplete blocks or missing final text."""
    text = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL | re.IGNORECASE)
    if re.search(r"</?think>", text, flags=re.IGNORECASE) or not text.strip():
        raise IncompleteResponseError("No complete final answer was returned.")
    return text.strip()


def _reject_constant(value: str) -> None:
    raise ValueError("Non-finite numbers are not valid JSON.")


def _json_container(value: Any) -> JSONValue:
    if not isinstance(value, (dict, list)):
        raise ValueError("Expected a JSON object or array.")
    return value


def extract_json_object(content: str) -> JSONValue:
    """Parse complete JSON first, preserving arrays; reject ambiguous fragments."""
    text = clean_reasoning_tags(content)
    decoder = json.JSONDecoder(parse_constant=_reject_constant)
    try:
        value = decoder.decode(text)
    except json.JSONDecodeError:
        pass
    else:
        return _json_container(value)

    fences = re.findall(r"```(?:json)?\s*\n?(.*?)```", text,
                        flags=re.DOTALL | re.IGNORECASE)
    if fences:
        if len(fences) != 1:
            raise ValueError("Expected one JSON block.")
        try:
            return _json_container(decoder.decode(fences[0].strip()))
        except ValueError:
            raise ValueError("The JSON block is invalid.") from None

    # Start at the first container, never at an inner object of a broken array.
    start = re.search(r"[\[{]", text)
    if start:
        try:
            value, end = decoder.raw_decode(text, start.start())
            if re.search(r"[\[\]{}]", text[end:]):
                raise ValueError("Multiple or incomplete JSON containers.")
            return _json_container(value)
        except ValueError:
            pass
    raise ValueError("No unambiguous JSON object or array was returned.")


def _positive_int(name: str, value: int, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer.")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must not exceed {maximum}.")
    return value


class KIToolboxClient:
    """Discover models once per client and validate the selected ID before inference.

    Missing routing metadata falls back only to documented KIT ID conventions.
    Unknown metadata is blocked unless allow_external=True was explicitly chosen.
    max_retries retains the original helper's meaning: total HTTP attempts per
    operation, including the initial attempt. SDK retries are disabled.
    """

    def __init__(self, model: str | None = None, base_url: str = BASE_URL,
                 api_key: str | None = None, batch_size: int = 4,
                 max_retries: int = 3, allow_external: bool = False,
                 timeout: float = 60.0, max_retry_delay: float = 30.0):
        token = api_key or os.environ.get("KIT_KI_API")
        if not token:
            raise ValueError("Set the KIT_KI_API environment variable before connecting.")
        self.batch_size = _positive_int("batch_size", batch_size, MAX_WORKERS)
        self.max_retries = _positive_int("max_retries", max_retries)
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive.")
        if not math.isfinite(max_retry_delay) or max_retry_delay < 0:
            raise ValueError("max_retry_delay must be finite and nonnegative.")
        self.model = model
        self.allow_external = allow_external
        self.max_retry_delay = max_retry_delay
        self._models: list[dict[str, Any]] | None = None
        self.client = OpenAI(base_url=base_url, api_key=token, timeout=timeout, max_retries=0)

    def _request(self, operation: Callable[[], Any]) -> Any:
        for attempt in range(self.max_retries):
            try:
                return operation()
            except (APIConnectionError, APIStatusError) as exc:
                status = getattr(exc, "status_code", None)
                transient = status is None or status in {408, 409, 429} or status >= 500
                if not transient or attempt + 1 == self.max_retries:
                    # Exception bodies may contain prompts, outputs or credentials.
                    logger.error("API request failed (%s, status=%s).", type(exc).__name__, status)
                    raise
                delay = random.uniform(0, min(self.max_retry_delay, 2 ** (attempt + 1)))
                response = getattr(exc, "response", None)
                retry_after = response.headers.get("retry-after") if response is not None else None
                if retry_after:
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        try:
                            date = parsedate_to_datetime(retry_after)
                            delay = (date - datetime.now(timezone.utc)).total_seconds()
                        except (TypeError, ValueError, OverflowError):
                            pass
                    if not math.isfinite(delay):
                        delay = self.max_retry_delay
                    # Do not retry sooner than requested if the wait exceeds our budget.
                    if delay > self.max_retry_delay:
                        raise
                delay = min(self.max_retry_delay, max(0.0, delay))
                logger.warning("Transient API failure (status=%s); retry %s/%s in %.1fs.",
                               status, attempt + 2, self.max_retries, delay)
                time.sleep(delay)
        raise RuntimeError("Request attempt budget exhausted.")

    def list_models(self, refresh: bool = False) -> list[dict[str, Any]]:
        """Fetch the catalogue without inference; reuse it until explicitly refreshed."""
        if self._models is None or refresh:
            page = self._request(lambda: self.client.models.list())
            models = [item if isinstance(item, dict) else item.model_dump() for item in page.data]
            if any(not isinstance(m.get("id"), str) or not m["id"] for m in models):
                raise ValueError("The model catalogue contains an invalid ID.")
            self._models = models
        return list(self._models)

    def _select_model(self) -> str:
        models = self.list_models()
        by_id = {m["id"]: m for m in models}
        selected = self.model
        if selected is None:
            selected = next((name for name in DEFAULT_MODELS if name in by_id and
                             is_local_model(name, extract_connection_type(by_id[name]))), None)
            if selected is None:
                raise ValueError("No default local chat model is available; select a catalogue ID explicitly.")
        if selected not in by_id:
            raise ValueError("The selected model is absent from the current catalogue.")
        if not self.allow_external and not is_local_model(selected, extract_connection_type(by_id[selected])):
            raise PermissionError("The selected model has external or unknown routing; explicit authorization is required.")
        self.model = selected
        return selected

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.0,
             max_tokens: int = 512, clean_think: bool = True, **kwargs: Any) -> str:
        """Return a complete non-streaming answer; do not retry permanent API errors."""
        if kwargs.get("stream"):
            raise ValueError("This helper supports non-streaming completions only.")
        model = self._select_model()
        response = self._request(lambda: self.client.chat.completions.create(
            model=model, messages=messages, temperature=temperature,
            max_tokens=max_tokens, **kwargs))
        if not response.choices or response.choices[0].finish_reason != "stop":
            raise IncompleteResponseError("The completion did not finish with a complete answer.")
        content = response.choices[0].message.content or ""
        cleaned = clean_reasoning_tags(content)
        return cleaned if clean_think else content

    def prompt(self, prompt_text: str, system_prompt: str = "You are a helpful assistant.",
               temperature: float = 0.0, max_tokens: int = 512, **kwargs: Any) -> str:
        return self.chat([{"role": "system", "content": system_prompt},
                          {"role": "user", "content": prompt_text}],
                         temperature=temperature, max_tokens=max_tokens, **kwargs)

    def structured_json(self, prompt_text: str,
                        system_prompt: str = "You are a structured data extractor. Respond ONLY with valid JSON.",
                        temperature: float = 0.0, max_tokens: int = 1024,
                        max_json_attempts: int = 2,
                        validator: Callable[[JSONValue], None] | None = None) -> JSONValue:
        """Parse JSON and optionally validate its shape; validator raises ValueError.

        At most max_json_attempts * max_retries completion HTTP attempts, plus
        initial catalogue discovery. Invalid/truncated answers consume an attempt.
        Raw outputs and validator exception messages are never logged.
        """
        _positive_int("max_json_attempts", max_json_attempts)
        for attempt in range(max_json_attempts):
            try:
                raw = self.prompt(prompt_text, system_prompt, temperature=temperature,
                                  max_tokens=max_tokens)
            except IncompleteResponseError:
                pass
            else:
                try:
                    value = extract_json_object(raw)
                    if validator:
                        validator(value)
                    return value
                except ValueError:
                    pass
            if attempt + 1 == max_json_attempts:
                logger.error("JSON extraction or validation failed after %s attempts.", max_json_attempts)
                raise ValueError("No complete JSON answer passed parsing and validation.") from None
        raise RuntimeError("JSON attempt budget exhausted.")

    def batch_map(self, items: Sequence[Any], fn: Callable[[Any], Any],
                  max_workers: int | None = None, desc: str = "Processing batch") -> list[Any]:
        """Apply fn in input order with at most 16 workers; errors propagate."""
        workers = self.batch_size if max_workers is None else _positive_int("max_workers", max_workers, MAX_WORKERS)
        if not items:
            return []
        # Discover/select once before concurrent prompts share the cached catalogue.
        self._select_model()
        with ThreadPoolExecutor(max_workers=min(workers, len(items))) as executor:
            return list(executor.map(fn, items))

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> KIToolboxClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


if __name__ == "__main__":
    import sys

    try:
        with KIToolboxClient() as client:
            print(client.prompt("Give a one-sentence definition of supercapacitors."))
    except Exception as exc:
        print(f"Request failed ({type(exc).__name__}); check credentials, catalogue and connectivity.", file=sys.stderr)
        sys.exit(1)
