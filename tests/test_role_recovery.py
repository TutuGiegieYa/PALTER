"""Mixed role failures preserve corrections, permissions and paid-stage identity."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from palter import delta_updates, role_recovery, role_schedule, ensemble_world as w
from palter.ensemble import EnsembleApplication
# These recovery fixtures exercise historical all-wait corrections.
CURRENT_PREFIX = 'ai-tasks-v118.json'
from palter.storage import canonical, StoreError
from tests import test_ensemble_review as fixture


class RoleRecoveryTests(unittest.TestCase):
    def setUp(self):
        fixture.ReviewFixTests.setUp(self)
        self.app.gateway.current_version=CURRENT_PREFIX
        self.app.gateway.retry_delays=(0,0,0)
        self.app.configure_rules(self.state,self.caller())
        self.state['agenda']=[];self.state['role_wait_history']={'B':[True]}
        self.state['watch'].update(budget_usd=2,call_limit=128)
        self.sent=[];self.serial=0

    def caller(self,transform=None):return fixture.ReviewFixTests.caller(self,CURRENT_PREFIX,transform)

    def good(self,out):
        out.update(action={'kind':'inspect','args':['c1']},speech='',gesture=None,memory_update=None,
            strategy_update=None,next_decision={'mode':'continue','events':[]})

    def seed(self):
        self.owner=self.app.store.session()['id'];s=deepcopy(self.state)
        self.saved=self.app.store.create_game(self.owner,{'command_id':'recovery_create','expected_game_id':None},lambda gid:dict(s,id=gid))
        self.command={'command_id':'recovery_background','expected_revision':self.saved['revision'],'kind':'background'}
        return self.saved

    def rows(self):
        with self.app.store.transaction(False) as con:
            return [dict(r) for r in con.execute('SELECT * FROM ai_calls WHERE game_id=? ORDER BY started',(self.saved['id'],))]

    def run_turn(self,after=None):
        def build(s,call):
            self.app.turn(s,'B',call,0)
            if after:after(s,call)
        return self.app.operate(self.owner,self.saved['id'],self.command,build)[0]

    def install(self,mutate):
        original=self.provider_original=self.provider
        def transport(body):
            response=original(body)
            if 'PALTER_TASK: ensemble_role\n' in body['messages'][0]['content']:
                self.sent.append(deepcopy(body));out=json.loads(response['choices'][0]['message']['content'])
                self.good(out);mutate(len(self.sent),out,response)
                if response['choices'][0]['finish_reason']=='stop' and not response.pop('_keep_text',False):
                    response['choices'][0]['message']['content']=canonical(out)
            return response
        self.app.gateway.client.transport=transport

    def mixed(self,n,out,response,valid_fourth=True):
        if n==1:out['strategy_update']={'patch':{'plan':'甲'},'plan':'乙'}
        if n==2 or (n==4 and not valid_fourth):out['action']={'kind':'wait','args':[]}
        if n==3:
            response['choices'][0]['message']['content']=canonical(out)[:-1];response['_keep_text']=True

    def test_equivalent_envelope_preserves_sources_and_raw_values(self):
        s=self.state
        raw={'strategy_update':{'patch':{'plan':'我继续核查。'},'sources':['crime']}}
        before=deepcopy(raw);out=delta_updates.expand(s,'B',raw)
        self.assertEqual(out['strategy_update']['sources'],['crime']);self.assertEqual(raw,before)
        self.assertEqual(out['strategy_update']['plan'],'我继续核查。')
        same={'strategy_update':{'patch':{'plan':'同一计划'},'plan':'同一计划'}}
        self.assertEqual(delta_updates.expand(s,'B',same)['strategy_update']['plan'],'同一计划')

    def test_conflicts_and_replace_add_overlap_have_precise_errors(self):
        for value,field in (({'patch':{'plan':'甲'},'plan':'乙'},'strategy_update.plan'),
                ({'patch':{'sources':['crime']},'sources_add':['handover']},'strategy_update.sources'),
                ({'patch':{},'clear':True},'strategy_update')):
            with self.subTest(value=value),self.assertRaises(delta_updates.ContractError) as caught:
                delta_updates.expand(self.state,'B',{'strategy_update':value})
            self.assertEqual(caught.exception.feedback['field'],field)

    def test_normalized_envelope_still_rejects_foreign_sources(self):
        def invalid(task,out,data):
            if task=='ensemble_role':
                self.good(out);out['strategy_update']={'patch':{'plan':'我的计划'},'sources':['FOREIGN_SECRET']}
        before=canonical(self.state.get('strategies',{}))
        with self.assertRaises(ValueError) as caught:self.app.turn(self.state,'B',self.caller(invalid),0)
        self.assertEqual(caught.exception.feedback['field'],'strategy_update.sources')
        self.assertEqual(canonical(self.state.get('strategies',{})),before)

    def test_conflict_wait_json_then_success_within_four_attempts(self):
        self.seed();self.install(self.mixed);saved=self.run_turn()
        rows=self.rows();self.assertEqual(len(rows),4)
        self.assertEqual([r['status'] for r in rows],['failed']*3+['completed'])
        issues=[json.loads(r['validation_feedback'])['unresolved_issues'] for r in rows[:3]]
        self.assertEqual([[i['group'] for i in group] for group in issues],
            [['decision_shape'],['next_decision'],['next_decision','json']])
        last=self.sent[-1];self.assertEqual(last['response_format'],{'type':'json_object'})
        self.assertEqual(last['tool_choice'],'none');self.assertEqual(last['max_tokens'],6144)
        data=json.loads(last['messages'][2]['content'])
        self.assertEqual(data['scheduling']['decision_options']['allowed_modes'],['continue'])
        self.assertEqual(saved['role_wait_history']['B'],[True,False])
        self.assertEqual(len(saved['decisions']),1)
        self.assertNotIn('role_recovery_version',self.sent[0]['messages'][2]['content'])

    def test_wait_issue_clears_when_later_semantic_check_fails(self):
        self.seed()
        def errors(n,out,response):
            if n==1:out['action']={'kind':'wait','args':[]}
            if n==2:out['strategy_update']={'situation':'','plan':'','sources':['FOREIGN_SECRET']}
        self.install(errors);self.run_turn();rows=self.rows()
        self.assertEqual([i['group'] for i in json.loads(rows[1]['validation_feedback'])['unresolved_issues']],['interpretation'])

    def test_exhaustion_restart_and_manual_retry_preserve_ledger(self):
        self.seed();self.install(lambda n,o,r:self.mixed(n,o,r,False))
        with self.assertRaises(StoreError) as caught:self.run_turn()
        self.assertEqual(caught.exception.code,'retry_exhausted');before=self.rows()
        self.assertEqual(len(before),4)
        self.assertEqual(self.app.store.state(self.owner,self.saved['id'])['role_wait_history']['B'],[True])
        self.app=EnsembleApplication(self.app.store.path,self.app.gateway.client);self.app.gateway.retry_delays=(0,0,0)
        with self.app.store.transaction() as con:self.app.gateway.renew_retry(con,self.saved['id'],self.command['command_id'])
        saved=self.run_turn();self.assertEqual(len(self.sent),5)
        self.assertEqual(self.sent[-1]['response_format'],{'type':'json_object'})
        self.assertIn('next_decision',canonical(json.loads(self.sent[-1]['messages'][2]['content'])['validation_feedback']['unresolved_issues']))
        self.assertEqual(self.rows()[:4],before)
        self.assertEqual(saved['role_wait_history']['B'],[True,False])

    def test_unpaid_v112_recovery_upgrades_without_changing_old_requests(self):
        self.app.gateway.current_version='ai-tasks-v112.json'
        self.seed();self.install(lambda n,o,r:self.mixed(n,o,r,False))
        with patch('palter.role_recovery.enabled',return_value=False),self.assertRaises(StoreError):self.run_turn()
        before=self.rows()
        self.assertNotIn('decision_options',self.sent[0]['messages'][2]['content'])
        with self.app.store.transaction() as con:self.app.gateway.renew_retry(con,self.saved['id'],self.command['command_id'])
        self.run_turn();self.assertEqual(self.rows()[:4],before)
        self.assertEqual(self.sent[-1]['tool_choice'],'none')
        self.assertIn('decision_options',self.sent[-1]['messages'][2]['content'])

    def test_paid_corrected_role_reuses_exact_request_after_later_failure(self):
        self.seed();self.install(self.mixed)
        def later(s,call):call('later','ensemble_dm',None,{},lambda out:None)
        self.provider_original.fail='ensemble_dm'
        with self.assertRaises(StoreError):self.run_turn(later)
        role_rows=[r for r in self.rows() if r['task']=='ensemble_role'];self.assertEqual(len(role_rows),4)
        self.provider_original.fail=None
        self.app=EnsembleApplication(self.app.store.path,self.app.gateway.client);self.app.gateway.retry_delays=(0,0,0)
        with self.app.store.transaction() as con:self.app.gateway.renew_retry(con,self.saved['id'],self.command['command_id'])
        saved=self.run_turn(later)
        self.assertEqual(len(self.sent),4);self.assertEqual(saved['role_wait_history']['B'],[True,False])
        self.assertEqual([r for r in self.rows() if r['task']=='ensemble_role'],role_rows)

    def test_native_receipts_survive_json_correction_without_duplicate_tools(self):
        self.seed()
        def tool(n,out,response):
            if n==1:
                response['choices'][0].update(finish_reason='tool_calls',message={'role':'assistant','content':None,'tool_calls':[
                    {'id':'listener_once','type':'function','function':{'name':'create_event_listener','arguments':canonical({
                        'description':'等实际新消息','event_ids':['next_observation'],'completion_condition':'','early_end_condition':''})}}]})
            if n==2:response['choices'][0]['message']['content']=' ';response['_keep_text']=True
        self.install(tool);saved=self.run_turn()
        self.assertEqual(len(self.sent),3);self.assertEqual(self.sent[-1]['tool_choice'],'none')
        self.assertTrue(any(m['role']=='tool' and m['tool_call_id']=='listener_once' for m in self.sent[-1]['messages']))
        self.assertEqual(len(saved['event_tool_receipts']),1);self.assertEqual(len(saved['event_listeners']),1)
        self.assertEqual(saved['role_wait_history']['B'],[True,False])

    def test_bad_tool_arguments_keep_tool_mode_and_do_not_create_listener(self):
        self.seed()
        def bad_tool(n,out,response):
            if n==1:response['choices'][0].update(finish_reason='tool_calls',message={'role':'assistant','content':None,'tool_calls':[
                {'id':'bad_listener','type':'function','function':{'name':'create_event_listener','arguments':'{'}}]})
        self.install(bad_tool);saved=self.run_turn()
        self.assertEqual(len(self.sent),2);self.assertEqual(self.sent[-1]['tool_choice'],'auto')
        self.assertEqual(self.sent[-1]['response_format'],{'type':'text'})
        self.assertFalse(saved.get('event_tool_receipts'))


if __name__=='__main__':unittest.main()
