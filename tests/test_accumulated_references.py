"""Long-running deltas must not hit hidden citation-count limits."""
from copy import deepcopy
import json
import ssl
import unittest
import urllib.error
from palter import ensemble_world as w, final_arguments, ensemble_review, output_contracts, memory_entries
from palter.storage import canonical, StoreError
from palter.ensemble import EnsembleApplication
from palter.deepseek import DeepSeek, Settings
from palter.ai_gateway import retryable, manually_retryable
from tests import test_ensemble_review as fixtures


class AccumulatedReferenceTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.app,self.s=self.f.app,self.f.state
        self.app.gateway.current_version='ai-tasks-v107.json'
        self.app.configure_rules(self.s,self.f.caller('ai-tasks-v107.json'));self.s['agenda']=[]

    def statements(self,count=40):
        for i in range(count):w.speak(self.s,'D',f'这是我实际说过的第{i}条说明。')
        for a in w.ACTORS:self.s['memory'][a]['checkpoint']=len(self.s['observations'][a])
        return {a:[o['id'] for o in self.s['observations'][a] if o['kind']=='testimony'] for a in w.ACTORS}

    def test_old_pinned_increment_from_twelve_to_thirteen_keeps_action_and_all_references(self):
        ids=self.statements(13)['A']
        self.s['beliefs']['A']={'suspect':None,'explanation':'需要继续核对。','evidence_ids':[],'testimony_ids':ids[:12]}
        def change(task,out,data):
            if task=='ensemble_role':out['belief_update']={'patch':{'testimony_ids_add':[ids[-1]]}}
        self.app.turn(self.s,'A',self.f.caller('ai-tasks-v106.json',change),0)
        self.assertEqual(self.s['beliefs']['A']['testimony_ids'],ids)
        self.assertTrue(self.s['decisions'])

    def test_unchanged_belief_and_culprit_strategy_can_keep_more_than_thirty_sources(self):
        ids=self.statements()
        self.s['beliefs']['A']={'suspect':None,'explanation':'保留当前判断。','evidence_ids':[],'testimony_ids':ids['A']}
        def unchanged(task,out,data):
            if task=='ensemble_role':out['belief_update']=None
        self.app.turn(self.s,'A',self.f.caller('ai-tasks-v107.json',unchanged),0)
        self.assertEqual(self.s['beliefs']['A']['testimony_ids'],ids['A'])
        actor=self.s['case']['solution']['killer']
        self.s.setdefault('strategies',{})[actor]={'situation':'局面未变。','plan':'保留说法。','sources':ids[actor]}
        def strategy(task,out,data):
            if task=='ensemble_role':out['strategy_update']={'patch':{'plan':'根据已有来源继续应对。'}}
        self.app.turn(self.s,actor,self.f.caller('ai-tasks-v107.json',strategy),0)
        self.assertEqual(self.s['strategies'][actor]['sources'],ids[actor])

    def test_final_submission_and_evaluation_keep_all_authorized_citations(self):
        ids=self.statements()['A']
        value={'suspect':'B','aspects':[{'aspect':a,'explanation':'我按已知记录说明。','gaps':'','evidence_ids':[],
                                     'testimony_ids':ids} for a in final_arguments.dimensions(self.s['case'])]}
        out=final_arguments.normalize(self.s,'A',value)
        self.assertEqual(out['testimony_ids'],ids)
        response={'claims':[{'aspect':a,'supported':False,'reason':'口述不足以替代物证。','evidence_ids':ids}
                            for a in ('identity','time','method')],'argument_sources':ids}
        ensemble_review.validate_response(response,set(ids))
        value['aspects'][0]['testimony_ids'].append('B-o999999')
        with self.assertRaises(ValueError):final_arguments.normalize(self.s,'A',value)

    def test_source_and_text_feedback_are_precise_without_rewriting_values(self):
        with self.assertRaises(ValueError) as error:output_contracts.references(['known','foreign'],{'known'},'belief_update.testimony_ids')
        self.assertEqual(error.exception.feedback['invalid_source_indexes'],[1])
        with self.assertRaises(ValueError) as error:output_contracts.text('长'*1801,'belief_update.explanation',1800,True)
        self.assertEqual(error.exception.feedback['actual_characters'],1801)
        self.assertEqual(error.exception.feedback['maximum_characters'],1800)

    def test_unstructured_contract_failure_gets_feedback_and_paid_retry_replays(self):
        self.app.gateway.retry_delays=(0,0,0);self.s['watch'].update(budget_usd=2,call_limit=128)
        owner=self.app.store.session()['id']
        def factory(identity):s=deepcopy(self.s);s['id']=identity;return s
        saved=self.app.store.create_game(owner,{'command_id':'contract_feedback_game','expected_game_id':None},factory)
        calls=[]
        def provider(body):
            calls.append(body)
            if len(calls)==1:return {'choices':[{'finish_reason':'stop','message':{'content':canonical({'unexpected':True})}}]}
            data=json.loads(body['messages'][2]['content'])
            self.assertEqual(data['validation_feedback']['validation_error'],'unexpected decision fields')
            self.assertEqual(self.app.store.state(owner,saved['id'])['events'],saved['events'])
            return self.f.provider(body)
        self.app.gateway.client.transport=provider
        command={'command_id':'contract_feedback_step','expected_revision':saved['revision'],'kind':'background'}
        def work(state,call):self.app.turn(state,'A',call,0)
        def interrupt(state,call):work(state,call);raise StoreError('fixture interruption',503,'connection_failed')
        with self.assertRaises(StoreError):self.app.operate(owner,saved['id'],command,interrupt)
        self.assertEqual(len(calls),2)
        with self.app.store.transaction(False) as con:before=[dict(r) for r in con.execute('SELECT * FROM ai_calls ORDER BY attempt')]
        self.app=EnsembleApplication(self.app.store.path,DeepSeek(Settings(api_key='fixture'),provider))
        self.app.operate(owner,saved['id'],command,work)
        self.assertEqual(len(calls),2)
        with self.app.store.transaction(False) as con:self.assertEqual([dict(r) for r in con.execute('SELECT * FROM ai_calls ORDER BY attempt')],before)

    def test_connection_diagnostic_keeps_category_without_provider_error_text(self):
        self.app.gateway.retry_delays=(0,0,0);self.s['watch'].update(budget_usd=2,call_limit=128)
        owner=self.app.store.session()['id']
        def factory(identity):s=deepcopy(self.s);s['id']=identity;return s
        saved=self.app.store.create_game(owner,{'command_id':'transport_diagnostic_game','expected_game_id':None},factory)
        def failure(body):raise urllib.error.URLError(ssl.SSLEOFError(8,'PRIVATE_TRANSPORT_TEXT'))
        self.app.gateway.client.transport=failure
        with self.assertRaises(StoreError) as caught:
            self.app.operate(owner,saved['id'],{'command_id':'transport_diagnostic_step','expected_revision':saved['revision'],'kind':'background'},
                             lambda state,call:self.app.turn(state,'A',call,0))
        self.assertEqual(caught.exception.code,'retry_exhausted')
        with self.app.store.transaction(False) as con:rows=[dict(r) for r in con.execute('SELECT error,diagnostic FROM ai_calls')]
        self.assertEqual(len(rows),4)
        self.assertTrue(all(r['diagnostic']=='URLError: SSLEOFError; errno=8' for r in rows))
        self.assertNotIn('PRIVATE_TRANSPORT_TEXT',canonical(rows))

    def test_dm_disclosure_uses_speech_snapshot_not_following_acquisition(self):
        start=len(self.s['events']);speech=w.speak(self.s,'B','我现在要看这份材料。')
        w.acquire(self.s,'B','c1',w.emit(self.s,'inspect','B',target='c1'),'inspection')
        self.assertIn('c1',self.s['known']['B'])
        def invalid(task,out,data):
            if task=='ensemble_dm':
                self.assertNotIn('c1',data['disclosure_sources'][speech['id']])
                out['disclosures']=[{'event_id':speech['id'],'evidence_id':'c1'}]
        before=deepcopy(self.s)
        with self.assertRaises(output_contracts.DisclosureError) as error:
            self.app.adjudicate_ensemble(self.s,start,self.f.caller('ai-tasks-v108.json',invalid))
        self.assertEqual(self.s,before)
        self.assertEqual(error.exception.feedback['event_id'],speech['id'])
        self.assertNotIn('c1',error.exception.feedback['allowed_evidence_ids'])
        self.assertIn('secret_B',error.exception.feedback['allowed_evidence_ids'])
        start=len(self.s['events']);later=w.speak(self.s,'B','我已经看过这份材料，说明内容。')
        def valid(task,out,data):
            if task=='ensemble_dm':out['disclosures']=[{'event_id':later['id'],'evidence_id':'c1'}]
        self.app.adjudicate_ensemble(self.s,start,self.f.caller('ai-tasks-v108.json',valid))
        self.assertTrue(any(d['event_id']==later['id'] and d['evidence_id']=='c1' for d in self.s['disclosures']))

    def test_old_pinned_dm_has_no_new_request_fields_but_gets_precise_disclosure_feedback(self):
        start=len(self.s['events']);speech=w.speak(self.s,'B','我准备查看那份材料。')
        def invalid(task,out,data):
            if task=='ensemble_dm':
                self.assertNotIn('disclosure_sources',data)
                out['disclosures']=[{'event_id':speech['id'],'evidence_id':'c1'}]
        with self.assertRaises(output_contracts.DisclosureError) as error:
            self.app.adjudicate_ensemble(self.s,start,self.f.caller('ai-tasks-v107.json',invalid))
        self.assertEqual(error.exception.feedback['code'],'disclosure_source')
        self.assertEqual(error.exception.feedback['field'],'disclosures[0].evidence_id')

    def test_balance_failure_stops_immediately_and_allows_explicit_paid_stage_reuse(self):
        self.assertFalse(retryable('http_402'));self.assertTrue(manually_retryable('http_402'))
        self.app.gateway.retry_delays=(0,0,0);self.s['watch'].update(budget_usd=2,call_limit=128)
        owner=self.app.store.session()['id']
        saved=self.app.store.create_game(owner,{'command_id':'balance_fixture','expected_game_id':None},
            lambda gid:dict(deepcopy(self.s),id=gid))
        attempts=[]
        def insufficient(body):
            attempts.append(body)
            raise urllib.error.HTTPError('https://api.deepseek.com/chat/completions',402,'Insufficient Balance',{},None)
        self.app.gateway.client.transport=insufficient
        command={'command_id':'balance_step','expected_revision':saved['revision'],'kind':'background'}
        def work(state,call):self.app.turn(state,'A',call,0)
        with self.assertRaises(StoreError) as error:self.app.operate(owner,saved['id'],command,work)
        self.assertEqual(error.exception.code,'http_402');self.assertIn('余额不足',str(error.exception))
        self.assertEqual(len(attempts),1)
        with self.app.store.transaction() as con:self.app.gateway.renew_retry(con,saved['id'],command['command_id'])
        self.app.gateway.client.transport=self.f.provider
        self.app.operate(owner,saved['id'],command,work)
        with self.app.store.transaction(False) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM ai_calls WHERE error='http_402'").fetchone()[0],1)
            self.assertGreater(con.execute("SELECT count(*) FROM ai_calls WHERE status='completed'").fetchone()[0],0)

    def test_memory_entry_overflow_requests_regrouping_not_thirteen_text_edits(self):
        rows=[{'id':f'm{i}','kind':'observed','text':'短条目。','sources':['secret_A']} for i in range(13)]
        with self.assertRaises(memory_entries.CapacityError) as error:
            memory_entries.validate_snapshot(rows,text_budget=1024)
        feedback=deepcopy(error.exception.feedback);feedback['rejected_snapshot']=rows
        feedback=memory_entries.correction_feedback(feedback)
        self.assertEqual(feedback['correction_version'],6)
        self.assertEqual(set(feedback['exceeded']),{'entries'})
        self.assertNotIn('entry_text_targets',feedback);self.assertNotIn('repair_contract',feedback)
        self.assertIn('只缩短每条文字不能解决',feedback['instruction'])
        self.assertNotIn('上次摘要正文超限',feedback['instruction'])
        self.assertEqual(feedback['rejected_snapshot'],rows)


if __name__=='__main__':unittest.main()
