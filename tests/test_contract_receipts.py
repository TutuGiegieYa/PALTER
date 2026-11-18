"""Reusable correction facts, source isolation and unchanged paid requests."""
from copy import deepcopy
import json
import unittest

from palter import ensemble_world as w, output_contracts, role_recovery
from palter.ensemble import EnsembleApplication
from palter.model_contracts import CURRENT_PREFIX
from palter.storage import canonical, StoreError
from tests import test_ensemble_review as fixture


class ContractReceiptTests(unittest.TestCase):
    def receipt(self,value,known=None,**kwargs):
        with self.assertRaises(ValueError) as caught:
            output_contracts.references(value,known or set(),'claim.sources',**kwargs)
        return caught.exception.feedback

    def test_exact_invalid_value_kind_and_expected_constraint(self):
        feedback=self.receipt(['heard','seen','document','unknown'],{'heard'},
            other_fields={'claim.records':{'document'}},
            source_kinds={'heard':'testimony','seen':'observation','document':'acquired_record'},
            expected_kinds=('testimony',))
        receipt=feedback['validation_receipt'];rows=receipt['violations']
        self.assertEqual([r['actual']['value'] for r in rows],['seen','document','unknown'])
        self.assertEqual([r['actual']['source_kind'] for r in rows],['observation','acquired_record','unavailable'])
        self.assertEqual(rows[0]['path'],'claim.sources[1]')
        self.assertEqual(rows[0]['reason'],'source_kind_mismatch')
        self.assertEqual(rows[1]['permitted_fields'],['claim.records'])
        self.assertEqual(rows[2]['permitted_fields'],[])
        self.assertEqual(rows[2]['reason'],'source_not_authorized_for_field')
        self.assertEqual(receipt['expected']['items']['source_kinds'],['testimony'])
        self.assertFalse(receipt['rejected_update_applied'])

    def test_container_and_member_type_errors_are_machine_readable(self):
        for value in (None,'wrong',{'id':'wrong'}):
            r=self.receipt(value)['validation_receipt']
            self.assertEqual(r['violations'][0]['reason'],'type_mismatch')
            self.assertEqual(r['expected']['type'],'array')
        r=self.receipt([None,{'id':'wrong'},False])['validation_receipt']
        self.assertEqual([v['actual']['type'] for v in r['violations']],['null','object','boolean'])
        self.assertTrue(all(v['reason']=='type_mismatch' for v in r['violations']))

    def test_diagnostics_are_bounded_without_capping_authorized_citations(self):
        values=['id'+str(i) for i in range(500)];before=deepcopy(values)
        output_contracts.references(values,set(values),'claim.sources')
        self.assertEqual(values,before)
        r=self.receipt(['x'*10000+str(i) for i in range(50)])['validation_receipt']
        self.assertEqual(r['violation_count'],50);self.assertEqual(r['omitted_violations'],42)
        self.assertTrue(all(v['actual']['truncated'] for v in r['violations']))
        self.assertLess(len(canonical(r)),5000)

    def test_text_errors_use_same_shape_without_echoing_prose(self):
        for value,reason in (('private '*300,'text_too_long'),('  ','nonblank_required'),(None,'type_mismatch')):
            with self.assertRaises(ValueError) as caught:output_contracts.text(value,'claim.explanation',100)
            r=caught.exception.feedback['validation_receipt']
            self.assertEqual(r['violations'][0]['reason'],reason)
            self.assertEqual(r['expected']['max_characters'],100)
            self.assertNotIn('private',canonical(r))
        output_contracts.text('', 'claim.explanation',100,True)

    def test_invalid_json_retains_structured_correction(self):
        original=self.receipt(['bad'])
        first=ValueError('invalid source');first.role_group='interpretation';first.role_checked=[]
        prior=role_recovery.failure(first,original,output={})
        try:json.loads('{')
        except json.JSONDecodeError as error:result=role_recovery.failure(error,None,prior)
        self.assertEqual(result['unresolved_issues'][0]['validation_receipt'],original['validation_receipt'])
        self.assertEqual([i['group'] for i in result['unresolved_issues']],['interpretation','json'])


class ReceiptIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.app,self.state=self.f.app,self.f.state
        self.app.gateway.current_version=CURRENT_PREFIX;self.app.gateway.retry_delays=(0,0,0)
        self.app.configure_rules(self.state,self.f.caller(CURRENT_PREFIX));self.state['agenda']=[]
        w.speak(self.state,'C','我看过这份记录，但还需要核对。')
        self.heard=self.state['observations']['A'][-1]['id']
        w.note(self.state,'A',w.emit(self.state,'observed'),'我看到有人展示材料。')
        self.seen=self.state['observations']['A'][-1]['id']
        self.state['memory']['A']['checkpoint']=len(self.state['observations']['A'])
        self.state['watch'].update(budget_usd=2,call_limit=128)

    def decision(self,out):
        out.update(action={'kind':'inspect','args':['c1']},speech='',gesture=None,memory_update=None,
            belief_update={'patch':{'testimony_ids_add':[self.heard,self.seen]}},
            next_decision={'mode':'continue','events':[]})

    def test_patch_receipt_identifies_expanded_invalid_member_without_applying(self):
        def invalid(task,out,data):
            if task=='ensemble_role':self.decision(out)
        before=canonical(self.state)
        with self.assertRaises(ValueError) as caught:self.app.turn(self.state,'A',self.f.caller(CURRENT_PREFIX,invalid),0)
        r=caught.exception.feedback['validation_receipt']
        self.assertEqual(r['violations'][0]['actual']['value'],self.seen)
        self.assertEqual(r['violations'][0]['actual']['source_kind'],'observation')
        self.assertEqual(r['value_basis'],'expanded_value')
        self.assertEqual(canonical(self.state),before)

    def test_other_role_receipt_and_unknown_id_have_same_unavailable_diagnostics(self):
        w.note(self.state,'B',w.emit(self.state,'observed'),'PRIVATE_SOURCE_BODY')
        foreign=self.state['observations']['B'][-1]['id'];results=[]
        for identity in (foreign,'not-a-known-source'):
            def invalid(task,out,data):
                if task=='ensemble_role':
                    self.decision(out);out['belief_update']['patch']['testimony_ids_add']=[identity]
            with self.assertRaises(ValueError) as caught:self.app.turn(self.state,'A',self.f.caller(CURRENT_PREFIX,invalid),0)
            row=caught.exception.feedback['validation_receipt']['violations'][0]
            row=deepcopy(row);row['actual'].pop('value');row['actual'].pop('characters');results.append(row)
            self.assertNotIn('PRIVATE_SOURCE_BODY',canonical(caught.exception.feedback))
        self.assertEqual(results[0],results[1])

    def test_older_received_source_is_still_accepted(self):
        for _ in range(50):w.note(self.state,'A',w.emit(self.state,'observed'),'新的现场记录。')
        self.state['memory']['A']['checkpoint']=len(self.state['observations']['A'])
        def valid(task,out,data):
            if task=='ensemble_role':
                self.decision(out);out['belief_update']['patch']['testimony_ids_add']=[self.heard]
        self.app.turn(self.state,'A',self.f.caller(CURRENT_PREFIX,valid),0)
        self.assertEqual(self.state['beliefs']['A']['testimony_ids'],[self.heard])

    def test_retry_receipt_and_paid_stage_survive_later_failure_and_restart(self):
        owner=self.app.store.session()['id']
        saved=self.app.store.create_game(owner,{'command_id':'receipt_create','expected_game_id':None},lambda gid:dict(deepcopy(self.state),id=gid))
        command={'command_id':'receipt_step','expected_revision':saved['revision'],'kind':'background'}
        sent=[]
        def provider(body):
            response=self.f.provider(body)
            if 'PALTER_TASK: ensemble_role\n' in body['messages'][0]['content']:
                sent.append(deepcopy(body));out=json.loads(response['choices'][0]['message']['content']);self.decision(out)
                if len(sent)>1:
                    data=json.loads(body['messages'][2]['content'])
                    receipt=data['validation_feedback']['validation_receipt']
                    bad={r['actual']['value'] for r in receipt['violations']}
                    out['belief_update']['patch']['testimony_ids_add']=[i for i in out['belief_update']['patch']['testimony_ids_add'] if i not in bad]
                response['choices'][0]['message']['content']=canonical(out)
            return response
        self.app.gateway.client.transport=provider
        def build(state,call):
            self.app.turn(state,'A',call,0)
            call('later','ensemble_dm',None,{},lambda out:None)
        self.f.provider.fail='ensemble_dm'
        with self.assertRaises(StoreError):self.app.operate(owner,saved['id'],command,build)
        with self.app.store.transaction(False) as con:
            rows=[dict(r) for r in con.execute("SELECT * FROM ai_calls WHERE task='ensemble_role' ORDER BY attempt")]
        self.assertEqual([r['status'] for r in rows],['failed','completed'])
        self.assertEqual(json.loads(rows[1]['request_feedback'])['validation_receipt']['violations'][0]['actual']['value'],self.seen)
        self.f.provider.fail=None;self.app=EnsembleApplication(self.app.store.path,self.app.gateway.client)
        with self.app.store.transaction() as con:self.app.gateway.renew_retry(con,saved['id'],command['command_id'])
        state,_=self.app.operate(owner,saved['id'],command,build)
        with self.app.store.transaction(False) as con:
            after=[dict(r) for r in con.execute("SELECT * FROM ai_calls WHERE task='ensemble_role' ORDER BY attempt")]
        self.assertEqual(rows,after);self.assertEqual(len(sent),2)
        self.assertEqual(state['beliefs']['A']['testimony_ids'],[self.heard])


if __name__=='__main__':unittest.main()
