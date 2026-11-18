"""Native reasoning stays intact and metered without consuming the game-data quota."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
from palter.ai_gateway import request_sizes,reserve_cost,MAX_DYNAMIC_CONTEXT_BYTES
from palter.deepseek import DeepSeek,Settings
from palter.ensemble import EnsembleApplication
from palter.storage import canonical,StoreError
from tests import test_event_tools as native,test_ensemble_review as fixtures


class ToolReasoningAdmissionTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.ReviewFixTests();f.setUp();self.addCleanup(f.doCleanups)
        self.gateway=f.app.gateway

    def data(self,reasoning='思'*6000,context='x'*34000,result='receipt'):
        return {'context':context,'_tool_messages':[
            {'role':'assistant','content':None,'tool_calls':[native.tool(native.proposal())],'reasoning_content':reasoning},
            {'role':'tool','tool_call_id':'native_call_1','content':result}]}

    def test_reasoning_roundtrip_does_not_consume_game_budget_but_is_billed(self):
        data=self.data();before=deepcopy(data)
        body,_=self.gateway.payload('ensemble_role',{},data,'ai-tasks-v83.json')
        wire=canonical(body);sizes=request_sizes(body,2)
        self.assertGreater(len(canonical(body['messages'][2:]).encode()),MAX_DYNAMIC_CONTEXT_BYTES)
        self.assertLess(sizes['dynamic_bytes'],MAX_DYNAMIC_CONTEXT_BYTES);self.assertLess(sizes['total_bytes'],90000)
        self.assertEqual(body['messages'][-2]['reasoning_content'],'思'*6000)
        self.assertEqual(canonical(body),wire);self.assertEqual(data,before)
        without=deepcopy(body);without['messages'][-2].pop('reasoning_content')
        self.assertGreater(reserve_cost(body),reserve_cost(without))

    def test_tool_results_and_assistant_content_still_consume_game_budget(self):
        for field in ('tool','assistant'):
            data=self.data(context='x'*44000,result='y'*9000 if field=='tool' else 'receipt')
            if field=='assistant':data['_tool_messages'][0]['content']='y'*9000
            with self.subTest(field=field),self.assertRaises(StoreError) as error:
                self.gateway.payload('ensemble_role',{},data,'ai-tasks-v83.json')
            self.assertEqual(error.exception.code,'context_budget')

    def test_reasoning_remains_inside_full_envelope_limit(self):
        with self.assertRaises(StoreError) as error:
            self.gateway.payload('ensemble_role',{},self.data(reasoning='x'*65000,context='small'),'ai-tasks-v83.json')
        self.assertEqual(error.exception.code,'context_budget')

    def test_named_fields_do_not_exempt_user_or_tool_data(self):
        samples=[{'reasoning_content':'x'*MAX_DYNAMIC_CONTEXT_BYTES},
                 {'_tool_messages':[{'role':'tool','tool_call_id':'id','content':'result','reasoning_content':'x'*MAX_DYNAMIC_CONTEXT_BYTES}]},
                 {'_tool_messages':[{'role':'assistant','content':None,'tool_calls':[],'reasoning_content':'x'*MAX_DYNAMIC_CONTEXT_BYTES}]}]
        for data in samples:
            with self.subTest(data_type=list(data)),self.assertRaises(StoreError):
                self.gateway.payload('ensemble_role',{},data,'ai-tasks-v83.json')

    def test_non_thinking_requests_keep_the_original_sub_budget(self):
        with self.assertRaises(StoreError):self.gateway.payload('ensemble_role',{},self.data(),'ai-tasks-v79.json')

    def test_paused_native_step_resumes_once_without_rebuying_paid_tool_call(self):
        f=native.NativeToolRecoveryTests();f.setUp();self.addCleanup(f.doCleanups)
        f.app.gateway.current_version='ai-tasks-v83.json';provider=f.app.gateway.client.transport
        def thinking(payload):
            out=provider(payload)
            if out['choices'][0]['finish_reason']=='tool_calls':out['choices'][0]['message']['reasoning_content']='r'*41000
            return out
        f.app.gateway.client.transport=thinking;f.create()
        def old_meter(body,prefix_messages):
            sizes=request_sizes(body,prefix_messages)
            sizes['dynamic_bytes']=len(canonical(body['messages'][prefix_messages:]).encode())
            return sizes
        with patch('palter.ai_gateway.request_sizes',side_effect=old_meter),patch('palter.ai_gateway.MAX_DYNAMIC_CONTEXT_BYTES',40000):
            f.cmd('watch_step');f.app.pump(f.gid,True)
        self.assertEqual(f.state()['background_error']['code'],'context_budget')
        self.assertFalse(f.state().get('event_listeners'))
        with f.app.store.transaction(False) as con:
            original=dict(con.execute("SELECT * FROM ai_calls WHERE task='ensemble_role'").fetchone())
        f.app=EnsembleApplication(f.app.store.path,DeepSeek(Settings(api_key='fixture'),thinking))
        f.cmd('watch_step');f.app.pump(f.gid,True)
        self.assertIsNone(f.state()['background_error']);self.assertEqual(len(f.state()['event_listeners']),1)
        role_requests=[p for p in f.requests if 'PALTER_TASK: ensemble_role\n' in p['messages'][0]['content']]
        self.assertEqual(len(role_requests),2)
        self.assertEqual(next(m for m in role_requests[-1]['messages'] if m['role']=='assistant')['reasoning_content'],'r'*41000)
        with f.app.store.transaction(False) as con:
            self.assertEqual(dict(con.execute('SELECT * FROM ai_calls WHERE id=?',(original['id'],)).fetchone()),original)


if __name__=='__main__':unittest.main()
