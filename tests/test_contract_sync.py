"""Cross-task contracts, real boundaries and paid recovery without network calls."""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from palter import model_contracts as contracts, memory_entries, event_tools, source_access, output_contracts
from palter import role_events, role_schedule, ensemble_world as w, check_spectator
from palter.deepseek import DeepSeek, Settings, ROOT
from palter.ensemble import EnsembleApplication
from palter.scenario_cases import validate_story
from palter.storage import StoreError,canonical
from tests.test_ensemble import story_fixture
from tests import test_ensemble_review as fixtures
from tests.compact_fixture import expand


class ContractSyncTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.app,self.s=self.f.app,self.f.state
        self.app.configure_rules(self.s,self.f.caller(contracts.CURRENT_PREFIX));self.s['agenda']=[]

    def test_current_prefix_and_both_role_prompts_match_runtime(self):
        spec=self.app.gateway.versions[contracts.CURRENT_PREFIX]
        self.assertEqual(contracts.check_published(spec),[])
        changed=deepcopy(spec);changed['ensemble_role']['tools'][0]['function']['parameters']['properties']['description'].pop('maxLength')
        self.assertTrue(contracts.check_published(changed))
        for actor in 'ABCD':
            self.app.turn(deepcopy(self.s),actor,self.f.caller(contracts.CURRENT_PREFIX),0)

    def test_active_overflow_feedback_preserves_incremental_shape_and_archives_explicitly(self):
        row=lambda i:dict(id=f'm{i}',kind='observed',text='我记住一条旧事。',sources=['secret_A'])
        self.s['memory']['A']['entries']=[row(i) for i in range(10)]
        update={'upsert':[row(i) for i in range(10,13)],'archive':[],'processed_through':None}
        with self.assertRaises(memory_entries.CapacityError) as caught:memory_entries.revised(self.s,'A',update,set())
        fb=memory_entries.correction_feedback(caught.exception.feedback)
        self.assertEqual(fb['correction_version'],7);self.assertIn('upsert',fb['response_shape'])
        self.assertNotIn('返回完整 entries 替换快照',fb['instruction'])
        update['archive']=['m8','m9'];result,archived=memory_entries.revised(self.s,'A',update,set())
        self.assertEqual(len(result['entries']),11);self.assertEqual([r['id'] for r in archived],['m8','m9'])
        self.assertEqual(len(self.s['memory']['A']['entries']),10)
        with self.assertRaises(ValueError):memory_entries.revised(self.s,'A',{'entries':[row(0)],'processed_through':None},set())
        fb=memory_entries.correction_feedback(memory_entries.CapacityError('snapshot', [row(i) for i in range(13)],snapshot=True,text_budget=1024).feedback)
        self.assertIn('返回完整 entries 替换快照',fb['instruction']);self.assertNotIn('repair_contract',fb)

    def test_listener_text_and_source_id_exact_boundaries(self):
        base=dict(description='等待',event_ids=[],completion_condition='收到说明',early_end_condition='')
        for field,maximum in contracts.EVENT_TEXT.items():
            args={**base,field:'字'*maximum}
            call={'type':'function','id':'fixture','function':{'name':'create_event_listener','arguments':canonical(args)}}
            event_tools.validate_call(self.s,'A',call)
            args[field]+='字';call['function']['arguments']=canonical(args)
            with self.assertRaises(contracts.ContractError) as caught:event_tools.validate_call(self.s,'A',call)
            self.assertEqual(caught.exception.feedback['field'],field)
            self.assertEqual(caught.exception.feedback['maximum_characters'],maximum)
        for ids in (['x']*2,[str(i) for i in range(5)]):
            call['function']['arguments']=canonical({**base,'event_ids':ids})
            with self.assertRaises(contracts.ContractError) as caught:event_tools.validate_call(self.s,'A',call)
            self.assertEqual(caught.exception.feedback['field'],'event_ids')
        self.assertEqual(source_access.lookup(self.s,'A',{'requests':[{'id':'x'*200}]})['sources'][0]['status'],'unavailable')
        with self.assertRaises(contracts.ContractError) as caught:source_access.lookup(self.s,'A',{'requests':[{'id':'x'*201}]})
        self.assertEqual(caught.exception.feedback['field'],'requests[0].id')

    def test_all_authoring_bounds_accept_boundary_and_name_overflow_path(self):
        for field,limit in contracts.STORY_TEXT.items():
            story=story_fixture();parts=field.replace('*','A' if field.startswith('roles') else 'r1').split('.')
            row=story
            for key in parts[:-1]:row=row[key]
            if 'relationships' in field:
                row=row['relationships'];key=0;path='roles.A.relationships[0]'
            else:key=parts[-1];path='.'.join(parts)
            row[key]='字'*limit;validate_story(story)
            row[key]+='字'
            with self.assertRaises(contracts.ContractError) as caught:validate_story(story)
            self.assertEqual(caught.exception.feedback['field'],path)
            self.assertEqual(caught.exception.feedback['actual_characters'],limit+1)

    def test_human_notes_keep_all_authorized_references_but_reject_unknown(self):
        self.s['humans']=list('ABCD');ids=[f'fixture_{i}' for i in range(41)]
        for identity in ids:self.s['known']['A'][identity]={'id':identity}
        self.app.play(self.s,'A',{'kind':'notebook','text':'我的记录','evidence_ids':ids},None)
        self.assertEqual(self.s['notes']['A']['evidence_ids'],ids)
        with self.assertRaises(StoreError):self.app.play(self.s,'A',{'kind':'notebook','evidence_ids':ids+['foreign']},None)

    def test_misplaced_known_testimony_is_identified_without_granting_foreign_sources(self):
        speech=w.speak(self.s,'B','我只是提供口述。')
        heard={o['id'] for o in self.s['observations']['A'] if o['kind']=='testimony'}
        identity=next(o['id'] for o in self.s['observations']['A'] if o['event_id']==speech['id'])
        with self.assertRaises(ValueError) as caught:
            output_contracts.references([identity,'foreign'],set(self.s['known']['A']),'belief_update.evidence_ids',{'belief_update.testimony_ids':heard})
        fb=caught.exception.feedback
        self.assertEqual(fb['misplaced_sources'],[{'index':0,'id':identity,'permitted_field':'belief_update.testimony_ids'}])
        # Echoing the submitted invalid ID grants no source metadata or access.
        receipt=fb['validation_receipt'];unknown=receipt['violations'][1]
        self.assertEqual(unknown['actual']['value'],'foreign')
        self.assertEqual(unknown['permitted_fields'],[])
        self.assertNotIn('source_kind',unknown['actual'])
        self.assertFalse(receipt['rejected_update_applied'])
        output_contracts.references([identity],heard,'belief_update.testimony_ids')

    def old_record_wait(self,state):
        old=w.emit(state,'move','B','r3',secret='UNSEEN_DESTINATION')
        w.note(state,'A',old,'对方离开了这里。')
        for i in range(8):w.note(state,'A',w.emit(state,'fixture'),'背景'*100)
        w.note(state,'B',w.emit(state,'private'),'FOREIGN_SECRET')
        role_schedule.commit(state,'A',{'mode':'wait','events':['next_observation'],'wait_reason':'等待回应。'},role_schedule.context(state,'A'))
        return old

    def test_restored_old_receipt_is_scoped_bounded_and_never_new_arrival(self):
        old=self.old_record_wait(self.s);p=role_events.package(self.s,'public',True,True)
        self.assertNotIn(old['id'],p[2]['A']);before=deepcopy(self.s)
        foreign=self.s['observations']['B'][-1]['id']
        extra=role_events.additional_background(self.s,p,{'A':[old['id'],foreign]})
        revised=role_events.merge_background(p,extra,True)
        self.assertIn(old['id'],revised[2]['A']);self.assertNotIn(foreign,revised[2]['A'])
        self.assertNotIn('UNSEEN_DESTINATION',canonical(revised[1]));self.assertNotIn('FOREIGN_SECRET',canonical(revised[1]))
        self.assertEqual(revised[0],p[0]);self.assertEqual(revised[1]['A']['received_records'],[])
        self.assertEqual(role_events.checked_background(self.s,p,{'event_source_background':extra}),revised)
        dirty=deepcopy(extra);dirty['A'][0]['text']='篡改内容'
        with self.assertRaises(ValueError):role_events.checked_background(self.s,p,{'event_source_background':dirty})
        self.assertEqual(before,self.s)

    def test_current_dm_proactively_supplies_its_visible_event_as_scoped_background(self):
        old=self.old_record_wait(self.s);start=len(self.s['events'])
        w.speak(self.s,'A','我还在等对方回应。');seen=[]
        def inspect(task,out,data):
            if task!='ensemble_dm':return
            ctx=data['event_recipient_contexts']['A'];seen.append(ctx)
            self.assertIn(old['id'],ctx['allowed_source_ids'])
            self.assertTrue(any(row['event_id']==old['id'] for row in ctx['background_records']))
            self.assertNotIn('UNSEEN_DESTINATION',canonical(ctx))
        self.app.adjudicate_ensemble(self.s,start,self.f.caller(contracts.CURRENT_PREFIX,inspect))
        self.assertTrue(seen)

    def test_pinned_v108_failed_source_retries_and_paid_stage_reuses_exact_input(self):
        self.app.gateway.current_version='ai-tasks-v108.json';self.app.gateway.retry_delays=(0,0,0)
        self.s['watch'].update(budget_usd=2,call_limit=128)
        owner=self.app.store.session()['id'];saved=self.app.store.create_game(owner,{'command_id':'source_case','expected_game_id':None},lambda gid:dict(deepcopy(self.s),id=gid))
        calls=[];source=[]
        def provider(body):
            calls.append(body);data=expand(json.loads(body['messages'][2]['content']));record=data['tracked_events'][0]
            if len(calls)>1:
                self.assertIn(source[0],data['event_recipient_contexts']['A']['allowed_source_ids'])
                self.assertNotIn('UNSEEN_DESTINATION',canonical(data['event_recipient_contexts']))
            out=dict(assessments=[],cues=[],disclosures=[],event_decisions=[dict(id=record['id'],status='active',reason='继续等待回应。',progress='',source_ids=source,basis={'kind':'current_circumstances','workflow_stage':None})])
            return {'choices':[{'finish_reason':'stop','message':{'content':canonical(out)}}]}
        self.app.gateway.client.transport=provider
        def work(state,call):
            source[:]=[self.old_record_wait(state)['id']];self.app.adjudicate_ensemble(state,len(state['events']),call)
        def interrupted(state,call):work(state,call);raise StoreError('fixture interruption',503,'connection_failed')
        command={'command_id':'source_step','expected_revision':saved['revision'],'kind':'background'}
        with self.assertRaises(StoreError):self.app.operate(owner,saved['id'],command,interrupted)
        self.assertEqual(len(calls),2)
        self.app=EnsembleApplication(self.app.store.path,DeepSeek(Settings(api_key='fixture'),provider))
        result,_=self.app.operate(owner,saved['id'],command,work)
        self.assertEqual(len(calls),2);self.assertIn('A',result['role_waits'])

    def test_followup_repair_keeps_previously_restored_sources_without_cursor_rewind(self):
        older=w.emit(self.s,'fixture');w.note(self.s,'A',older,'我收到的较早记录。')
        old=self.old_record_wait(self.s);p=role_events.package(self.s,'public',True,True)
        feedback=role_events.EventSourceError(p[0],p[0][0],[old['id']],p[2]['A']).feedback
        first=role_events.source_background_feedback(self.s,p,feedback)
        expanded=role_events.checked_background(self.s,p,first)
        error=role_events.EventSourceError(p[0],p[0][0],[old['id'],older['id']],expanded[2]['A'])
        self.assertEqual(error.feedback['invalid_sources'],[older['id']])
        second=role_events.source_background_feedback(self.s,p,error.feedback)
        revised=role_events.checked_background(self.s,p,second)
        self.assertTrue({old['id'],older['id']}<=revised[2]['A']);self.assertEqual(revised[0],p[0])
        new=w.emit(self.s,'fixture');w.note(self.s,'A',new,'新的未审消息。')
        self.assertEqual(role_events.additional_background(self.s,p,{'A':[new['id']]}),{})


class AcceptanceGateTests(unittest.TestCase):
    def test_missing_results_and_pauses_fail_but_complete_chain_passes(self):
        state={'scenario':'murder','phase':'ended','submissions':dict.fromkeys('ABCD',{'suspect':'B','explanation':'我的结论'}),'ending':{'narrative':'结束'},
               'results':{'participants':{a:{'reasoning':{'result':'unproven'}} for a in 'ABCD'}}}
        self.assertTrue(check_spectator.acceptance(state)['passed'])
        self.assertFalse(check_spectator.acceptance(state,pending_calls=1)['passed'])
        for key in ('submissions','results','ending'):
            broken=deepcopy(state);broken.pop(key);self.assertFalse(check_spectator.acceptance(broken)['passed'])
        state['phase']='paused';self.assertEqual(check_spectator.acceptance(state)['status'],'paused')

    def test_runner_creation_failure_returns_nonzero_and_does_not_claim_completed(self):
        class Stub:
            def __init__(self,path):
                self.store=type('Store',(),{'session':lambda s:{'id':'fixture'}})()
                self.gateway=type('Gateway',(),{'current_version':'fixture'})()
            def create_game(self,*a,**kw):raise RuntimeError('synthetic creation failure')
        with tempfile.TemporaryDirectory(dir=ROOT/'.local/verification') as folder:
            argv=['check_spectator','--count','1','--parallel','1','--output',folder]
            with patch.object(check_spectator,'EnsembleApplication',Stub),patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):
                status=check_spectator.main()
            self.assertEqual(status,1)
            report=json.loads(next(Path(folder).glob('*.json')).read_text())
            self.assertTrue(report['runner_finished']);self.assertFalse(report['completed']);self.assertFalse(report['acceptance_passed'])
            self.assertEqual(report['summary']['failed'],1)
