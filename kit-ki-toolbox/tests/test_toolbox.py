"""Offline regressions using real SDK serialization and an in-memory transport."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import sys
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

import httpx
from openai import APIConnectionError, APIStatusError, OpenAI as SDKClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
import smoke_test
import toolbox_client as toolbox

LOCAL = {"id": "alias.simple-local", "object": "model", "created": 0, "owned_by": "kit"}


def completion(content='{"decision":1}', finish_reason="stop", choices=True):
    return {"id": "test", "object": "chat.completion", "created": 0,
            "model": LOCAL["id"], "choices": [{"index": 0, "finish_reason": finish_reason,
            "message": {"role": "assistant", "content": content}}] if choices else []}


class ParsingTests(unittest.TestCase):
    def test_preserves_json_containers(self):
        for value in ([{"id": 1}], [{"id": 1}, {"id": 2}], [], {}, {"a": [1, {"b": "} ["}]}):
            for text in (json.dumps(value), '```json\n' + json.dumps(value) + '\n```',
                         'Answer: ' + json.dumps(value) + ' Done.'):
                with self.subTest(text=text):
                    self.assertEqual(toolbox.extract_json_object(text), value)

    def test_rejects_scalars_ambiguous_and_broken_containers(self):
        for text in ('42', 'true', 'null', '"text"', '[{"id":1}',
                     '{"id":1}, {"id":2}', '```json\n{"id":1}\n```\n```json\n{}\n```',
                     '{"x": NaN}', '{"x": Infinity}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                toolbox.extract_json_object(text)

    def test_reasoning_is_removed_before_json_parsing(self):
        self.assertEqual(toolbox.extract_json_object('<think>{"secret":0}</think>[{"id":1}]'), [{"id":1}])
        self.assertEqual(toolbox.clean_reasoning_tags('<think>a</think><THINK>b</THINK> answer'), 'answer')

    def test_reasoning_only_unclosed_or_empty_is_incomplete(self):
        for text in ('', '   ', '<think>private</think>', '<think>private',
                     '<think>{"decision":0}</think>', 'private</think>answer'):
            with self.subTest(text=text), self.assertRaises(toolbox.IncompleteResponseError):
                toolbox.extract_json_object(text)


class RoutingTests(unittest.TestCase):
    def test_metadata_does_not_get_lost_in_nested_info(self):
        self.assertEqual(toolbox.extract_connection_type({'connection_type':'external', 'info':{}}), 'external')
        self.assertEqual(toolbox.extract_connection_type({'info': {'openai': {'connection_type':'local'}}}), 'local')

    def test_external_and_conflicting_metadata_override_local_name(self):
        for model in ({'connection_type':'external'},
                      {'connection_type':'local', 'info':{'connection_type':'external'}},
                      {'connection_type':'unrecognized'},
                      {'connection_type':'local', 'info':{'connection_type':'unrecognized'}}):
            with self.subTest(model=model):
                self.assertFalse(toolbox.is_local_model('kit.example', toolbox.extract_connection_type(model)))

    def test_missing_metadata_distinguishes_named_local_from_unknown(self):
        self.assertEqual(toolbox.model_scope('kit.example', 'missing'), 'local-by-name')
        self.assertEqual(toolbox.model_scope('alias.simple-local', 'missing'), 'local-by-name')
        for name in ('unverified-local', 'standard-local', 'custom'):
            self.assertEqual(toolbox.model_scope(name, 'missing'), 'unknown')
        self.assertEqual(toolbox.model_scope('azure.example', 'local'), 'external')


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.models = [dict(LOCAL)]
        self.replies = []
        self.requests = []
        self.clients = []
        sleep_patch = patch.object(toolbox.time, 'sleep')
        client_patch = patch.object(toolbox, 'OpenAI', side_effect=self.make_sdk)
        self.sleep = sleep_patch.start()
        client_patch.start()
        self.addCleanup(sleep_patch.stop)
        self.addCleanup(client_patch.stop)

    def make_sdk(self, **kwargs):
        client = SDKClient(http_client=httpx.Client(transport=httpx.MockTransport(self.handle)), **kwargs)
        self.clients.append(client)
        return client

    def tearDown(self):
        for client in self.clients:
            client.close()

    def handle(self, request):
        self.requests.append(request)
        if request.url.path == '/api/v1/models':
            return httpx.Response(200, json={'object':'list', 'data':self.models})
        self.assertEqual(request.url.path, '/api/v1/chat/completions')
        item = self.replies.pop(0) if self.replies else completion()
        if isinstance(item, Exception):
            raise item
        if isinstance(item, tuple):
            status, headers = item
            return httpx.Response(status, headers=headers,
                                  json={'error':{'message':'PRIVATE_SENTINEL', 'type':'test'}})
        return httpx.Response(200, json=item)

    def client(self, **kwargs):
        return toolbox.KIToolboxClient(api_key='offline-dummy-token', **kwargs)

    def chat_requests(self):
        return [r for r in self.requests if r.url.path.endswith('/chat/completions')]

    def test_discovery_precedes_inference_and_is_cached(self):
        client = self.client()
        client.prompt('hello')
        client.prompt('hello again')
        self.assertEqual([r.url.path for r in self.requests],
                         ['/api/v1/models', '/api/v1/chat/completions', '/api/v1/chat/completions'])
        self.assertEqual(client.model, LOCAL['id'])
        self.assertEqual(client.client.max_retries, 0)
        self.assertEqual(client.client.timeout, 60.0)

    def test_refresh_updates_availability(self):
        client = self.client()
        client.prompt('hello')
        self.models = []
        client.list_models(refresh=True)
        with self.assertRaises(ValueError):
            client.prompt('hello')
        self.assertEqual(len(self.chat_requests()), 1)

    def test_absent_model_never_sends_completion_even_with_override(self):
        for allow_external in (False, True):
            with self.assertRaises(ValueError):
                self.client(model='kit.nonexistent', allow_external=allow_external).prompt('private')
        self.assertEqual(len(self.chat_requests()), 0)

    def test_explicit_external_metadata_blocks_local_looking_id(self):
        self.models = [{**LOCAL, 'id':'kit.example', 'connection_type':'external', 'info':{}}]
        with self.assertRaises(PermissionError):
            self.client(model='kit.example').prompt('private')
        self.assertEqual(len(self.chat_requests()), 0)

    def test_unknown_routing_requires_explicit_override(self):
        self.models = [{**LOCAL, 'id':'custom'}]
        with self.assertRaises(PermissionError):
            self.client(model='custom').prompt('private')
        self.client(model='custom', allow_external=True).prompt('authorized')
        self.assertEqual(len(self.chat_requests()), 1)

    def test_default_does_not_pick_arbitrary_non_chat_model(self):
        self.models = [{**LOCAL, 'id':'kit.embedding'}]
        with self.assertRaises(ValueError):
            self.client().prompt('hello')
        self.assertEqual(len(self.chat_requests()), 0)

    def test_permanent_http_failures_are_not_retried(self):
        for status in (400, 401, 403, 404):
            with self.subTest(status=status):
                self.requests.clear()
                self.replies = [(status, {})]
                with self.assertRaises(APIStatusError):
                    self.client().prompt('private')
                self.assertEqual(len(self.chat_requests()), 1)
        self.sleep.assert_not_called()

    def test_transient_failures_are_retried_with_retry_after(self):
        self.replies = [(429, {'retry-after':'2'}), (503, {}), completion()]
        self.client().prompt('hello')
        self.assertEqual(len(self.chat_requests()), 3)
        self.assertEqual(self.sleep.call_args_list[0].args, (2.0,))
        self.assertLessEqual(self.sleep.call_args_list[1].args[0], 30)

    def test_retry_after_exceeding_wait_budget_stops(self):
        self.replies = [(429, {'retry-after':'120'})]
        with self.assertRaises(APIStatusError):
            self.client().prompt('hello')
        self.assertEqual(len(self.chat_requests()), 1)
        self.sleep.assert_not_called()

    def test_transport_failure_and_http_attempt_budget(self):
        self.replies = [httpx.ConnectError('PRIVATE_SENTINEL'), (503, {}), (503, {})]
        with self.assertRaises(APIStatusError):
            self.client().prompt('hello')
        self.assertEqual(len(self.chat_requests()), 3)
        self.assertEqual(self.sleep.call_count, 2)

    def test_programming_error_is_not_retried(self):
        client = self.client()
        with patch.object(client.client.chat.completions, 'create', side_effect=TypeError('bad argument')) as create:
            with self.assertRaises(TypeError):
                client.prompt('hello')
            self.assertEqual(create.call_count, 1)
        self.sleep.assert_not_called()

    def test_incomplete_responses_are_rejected(self):
        for reply in (completion('{}', 'length'), completion('{}', 'content_filter'),
                      completion(choices=False), completion(None), completion('<think>only reasoning</think>')):
            with self.subTest(reply=reply):
                self.replies = [reply]
                with self.assertRaises(toolbox.IncompleteResponseError):
                    self.client().prompt('hello')

    def test_json_validation_retries_and_honors_temperature(self):
        self.replies = [completion('{"decision":"yes"}'), completion('{"decision":1}')]
        def validate(value):
            if type(value.get('decision')) is not int:
                raise ValueError('PRIVATE_SENTINEL')
        result = self.client().structured_json('classify', temperature=0.7, validator=validate)
        self.assertEqual(result, {'decision':1})
        self.assertEqual([json.loads(r.content)['temperature'] for r in self.chat_requests()], [0.7, 0.7])

    def test_incomplete_json_uses_json_attempt_budget(self):
        self.replies = [completion('{"x":', 'length'), completion('[{"id":1}]')]
        self.assertEqual(self.client().structured_json('classify'), [{'id':1}])
        self.assertEqual(len(self.chat_requests()), 2)

    def test_logs_do_not_contain_raw_api_output_or_validator_errors(self):
        self.replies = [(503, {}), completion('PRIVATE_SENTINEL'), completion('{"decision":1}')]
        def reject(value):
            raise ValueError('PRIVATE_SENTINEL')
        with self.assertLogs(toolbox.logger, level='WARNING') as logs:
            with self.assertRaises(ValueError) as error:
                self.client().structured_json('private', validator=reject)
        self.assertNotIn('PRIVATE_SENTINEL', '\n'.join(logs.output))
        self.assertNotIn('PRIVATE_SENTINEL', str(error.exception))
        self.assertNotIn('offline-dummy-token', '\n'.join(logs.output))

    def test_permanent_api_error_does_not_trigger_json_retry(self):
        self.replies = [(400, {})]
        with self.assertRaises(APIStatusError):
            self.client().structured_json('hello')
        self.assertEqual(len(self.chat_requests()), 1)

    def test_streaming_rejected_before_network(self):
        with self.assertRaises(ValueError):
            self.client().prompt('hello', stream=True)
        self.assertEqual(self.requests, [])

    def test_concurrency_limits_and_batch_input_order(self):
        for size in (0, -1, 17):
            with self.assertRaises(ValueError):
                self.client(batch_size=size)
            with self.assertRaises(ValueError):
                self.client().batch_map([1], lambda x:x, max_workers=size)
        client = self.client(batch_size=2)
        self.assertEqual(client.batch_map([], lambda x:x), [])
        self.assertEqual(self.requests, [])
        # The second item can finish first; output must still follow input order.
        second_finished = threading.Event()
        def work(item):
            if item == 1:
                self.assertTrue(second_finished.wait(2))
            else:
                second_finished.set()
            return item * 10
        self.assertEqual(client.batch_map([1, 2], work), [10, 20])
        self.assertEqual(len(self.requests), 1)  # one shared discovery, no completion

    def test_cli_list_only_does_not_submit_completion(self):
        with patch.dict(os.environ, {'KIT_KI_API':'offline-dummy-token'}), \
             patch.object(sys, 'argv', ['smoke_test.py', '--list-only']), redirect_stdout(io.StringIO()):
            smoke_test.main()
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(len(self.chat_requests()), 0)

    def test_cli_absent_model_stops_without_exposing_api_body(self):
        with patch.dict(os.environ, {'KIT_KI_API':'offline-dummy-token'}), \
             patch.object(sys, 'argv', ['smoke_test.py', '--model', 'kit.nonexistent']), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as errors:
            with self.assertRaises(SystemExit):
                smoke_test.main()
        self.assertEqual(len(self.chat_requests()), 0)
        self.assertNotIn('offline-dummy-token', errors.getvalue())


if __name__ == '__main__':
    unittest.main()
