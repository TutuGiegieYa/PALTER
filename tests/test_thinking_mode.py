"""Lowest enabled effort, immutable old contracts and reasoning-aware tools."""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from palter.deepseek import DeepSeek,Settings
from palter.ensemble import EnsembleApplication
from palter import ensemble_world as w
from palter.storage import canonical
from tests import test_ensemble_review as fixtures, test_event_tools as native

VERSION='ai-tasks-v82.json'


class ThinkingModeTests(unittest.TestCase):
    def test_v85_disables_thinking_for_all_tasks_without_changing_contracts(self):
        f=fixtures.ReviewFixTests();f.setUp();self.addCleanup(f.doCleanups)
        app=EnsembleApplication(f.app.store.path,DeepSeek(Settings(api_key='fixture'),f.provider))
        gateway=app.gateway
        gateway.current_version='ai-tasks-v85.json'
        for task in gateway.versions['ai-tasks-v84.json']:
            for baseline in ({},{'decision_mode':'concealment'} if task=='ensemble_role' else {}):
                before,_=gateway.payload(task,baseline,{},'ai-tasks-v84.json')
                after,_=gateway.payload(task,baseline,{})
                expected=dict(before,thinking={'type':'disabled'});expected.pop('reasoning_effort')
                self.assertEqual(after,expected)

    def test_v85_native_tools_complete_without_thinking_or_memory_leakage(self):
        f=native.NativeToolRecoveryTests();f.setUp();self.addCleanup(f.doCleanups)
        f.app.gateway.current_version='ai-tasks-v85.json'
        f.create();f.cmd('watch_step');f.app.pump(f.gid,True)
        continuations=[p for p in f.requests if any(m['role']=='tool' for m in p['messages'])]
        self.assertTrue(continuations)
        for payload in f.requests:
            self.assertEqual(payload['thinking'],{'type':'disabled'})
            self.assertNotIn('reasoning_effort',payload)
        self.assertIsNone(f.state()['background_error'])
        self.assertEqual(len(f.state()['event_listeners']),1)

    def test_all_new_task_payloads_use_low_and_preserve_old_contracts(self):
        f=fixtures.ReviewFixTests();f.setUp();self.addCleanup(f.doCleanups)
        gateway=f.app.gateway
        old=gateway.versions['ai-tasks-v79.json'];new=gateway.versions[VERSION]
        for task in old:
            for baseline in ({},{'decision_mode':'concealment'} if task=='ensemble_role' else {}):
                with self.subTest(task=task,baseline=baseline):
                    before,_=gateway.payload(task,baseline,{},'ai-tasks-v79.json')
                    after,_=gateway.payload(task,baseline,{},VERSION)
                    self.assertEqual(before['thinking'],{'type':'disabled'})
                    self.assertEqual(after['thinking'],{'type':'enabled'});self.assertEqual(after['reasoning_effort'],'low')
                    self.assertEqual(after['model'],'deepseek-flash')
                    expected=8192 if task in ('initial_setup','case_setup','ensemble_setup') else before['max_tokens']+1024
                    self.assertEqual(after['max_tokens'],expected)
                    if task=='ensemble_role':
                        self.assertIn('CUSTOM LISTENER RECEIPTS:',after['messages'][0]['content'])
                        self.assertEqual(after['messages'][1:],before['messages'][1:])
                    else:self.assertEqual(after['messages'],before['messages'])
        root=Path('palter/prefixes');manifest=json.loads((root/'manifest.json').read_text())
        for name,digest in manifest.items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)

    def test_native_tool_reasoning_is_returned_to_provider_but_not_role_history(self):
        f=native.NativeToolRecoveryTests();f.setUp();self.addCleanup(f.doCleanups)
        f.app.gateway.current_version=VERSION;provider=f.app.gateway.client.transport
        def thinking(payload):
            response=provider(payload)
            if response['choices'][0]['finish_reason']=='tool_calls':response['choices'][0]['message']['reasoning_content']='SYNTHETIC_PRIVATE_REASONING'
            return response
        f.app.gateway.client.transport=thinking;f.create();f.cmd('watch_step');f.app.pump(f.gid,True)
        continuations=[p for p in f.requests if any(m['role']=='tool' for m in p['messages'])]
        self.assertTrue(continuations)
        for p in continuations:
            message=next(m for m in p['messages'] if m['role']=='assistant')
            self.assertEqual(message['reasoning_content'],'SYNTHETIC_PRIVATE_REASONING')
        state=f.state()
        for actor in w.ACTORS:self.assertNotIn('SYNTHETIC_PRIVATE_REASONING',canonical(w.context(state,actor)))

    def test_short_thinking_calls_have_time_to_return_final_output(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,limit):return b'{}'
        class Opener:
            def open(self,request,timeout):seen.append(timeout);return Response()
        seen=[];client=DeepSeek(Settings(api_key='fixture'))
        with patch('palter.deepseek.urllib.request.build_opener',return_value=Opener()):
            for enabled in (False,True):client._send({'thinking':{'type':'enabled' if enabled else 'disabled'},'max_tokens':1204})
        self.assertEqual(seen,[25,90])


if __name__=='__main__':unittest.main()
