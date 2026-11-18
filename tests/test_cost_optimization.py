"""v63 source integrity, incremental memory, menus, scoped receipts and recovery."""
from copy import deepcopy
import json
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from palter import ensemble_world as w, ensemble_context, compact_context, memory_entries, action_feedback
from palter.ai_gateway import Gateway
from palter.deepseek import DeepSeek,Settings
from palter.ensemble import EnsembleApplication
from palter.storage import canonical,StoreError
from tests import test_ensemble_review as review_fixture
from tests import test_spectator as spectator_fixture
from tests.compact_fixture import expand


class ContextOptimizationTests(unittest.TestCase):
    def setUp(self):
        f=review_fixture.ReviewFixTests();f.setUp();self.addCleanup(f.doCleanups)
        self.f=f;self.app=f.app;self.s=f.state;self.app.gateway.current_version='ai-tasks-v63.json'
        self.app.configure_rules(self.s,lambda:None)

    def data(self,a='A'):
        d=w.context(self.s,a);ensemble_context.project(self.s,a,d,concise=True,receipts=True)
        ensemble_context.investigation_state(self.s,a,d)
        return d

    def test_source_bodies_are_unique_and_expand_without_losing_acquisition(self):
        w.apply_choice(self.s,'A','inspect:c1');w.apply_choice(self.s,'A','share:c1')
        d=self.data();original=deepcopy(d);p=compact_context.pack('ensemble_role',d)
        self.assertEqual(d,original)
        text=self.s['known']['A']['c1']['observation']
        self.assertEqual(sum(v.get('observation')==text for v in p['sources'].values()),1)
        restored=expand(p)
        self.assertEqual(restored['evidence'][0]['observation'],d['evidence'][0]['observation'])
        self.assertEqual(restored['evidence'][0]['acquisition'],d['evidence'][0]['acquisition'])
        self.assertEqual([o['text'] for o in restored['observations'] if o['kind']=='testimony'],[o['text'] for o in d['observations'] if o['kind']=='testimony'])

    def test_same_words_from_different_occurrences_do_not_merge(self):
        w.speak(self.s,'A','同一句话');w.speak(self.s,'B','同一句话')
        p=compact_context.pack('ensemble_role',self.data())
        self.assertEqual(sum(v.get('text')=='同一句话' for v in p['sources'].values()),2)

    def test_v64_source_keys_are_authorized_while_v63_keeps_old_request_shape(self):
        w.speak(self.s,'B','我声称看过那份记录。');data=self.data();baseline=w.baseline(self.s,'A')
        old,_=self.app.gateway.payload('ensemble_role',baseline,data,'ai-tasks-v63.json')
        new,_=self.app.gateway.payload('ensemble_role',baseline,data,'ai-tasks-v64.json')
        a=json.loads(old['messages'][-1]['content']);b=json.loads(new['messages'][-1]['content'])
        self.assertTrue(any(k.endswith(':observation') for k in a['sources']))
        valid={o['id'] for o in self.s['observations']['A']}|set(self.s['known']['A'])
        self.assertTrue(set(b['sources'])<=valid)

    def test_menus_preserve_exact_parameter_tuples_and_all_choices(self):
        for a in 'ABCD':
            d=self.data(a);p=compact_context.pack('ensemble_role',d)
            encoded={':'.join([kind,*args]) for kind,rows in p['actions'].items() for args in rows}
            self.assertEqual(encoded,{c['id'] for c in w.choices(self.s,a)})
        choices=[{'id':'give:c1:B','label':'one'},{'id':'give:c2:C','label':'two'}]
        menu=compact_context.action_menu(choices)
        self.assertNotIn(['c1','C'],menu['give'])

    def test_source_prefix_precedes_changing_belief_and_does_not_mutate_canonical(self):
        w.apply_choice(self.s,'A','inspect:c1');d=self.data();base=w.baseline(self.s,'A')
        a,ha=self.app.gateway.payload('ensemble_role',base,d)
        d['belief']={'suspect':'B','explanation':'changed','evidence_ids':['c1']}
        b,hb=self.app.gateway.payload('ensemble_role',base,d)
        self.assertEqual(ha,hb)
        ta=a['messages'][-1]['content'];tb=b['messages'][-1]['content']
        self.assertEqual(ta.split('"belief":')[0],tb.split('"belief":')[0])
        self.assertLess(ta.index('"sources":'),ta.index('"belief":'))
        self.assertEqual(canonical({'z':1,'a':2}),'{'+'"a":2,"z":1}')

    def test_lookup_has_no_private_oracle_and_marks_excerpts(self):
        e=w.emit(self.s,'test_private');w.note(self.s,'B',e,'PRIVATE_CANARY','testimony',speaker='B')
        denied=compact_context.lookup(self.s,'A',{'requests':[{'id':self.s['observations']['B'][-1]['id'],'offset':0},{'id':'unknown','offset':0}]})
        self.assertEqual([x['status'] for x in denied['sources']],['unavailable','unavailable'])
        self.assertNotIn('PRIVATE_CANARY',canonical(denied))
        e=w.emit(self.s,'long_record');w.note(self.s,'A',e,'长'*5000)
        identity=self.s['observations']['A'][-1]['id']
        out=compact_context.lookup(self.s,'A',{'requests':[{'id':identity,'offset':0}]})['sources'][0]
        self.assertEqual(out['status'],'excerpt');self.assertLessEqual(len(out['text'].encode()),8192)
        self.assertIsNotNone(out['next_offset'])

    def test_memory_null_preserves_checkpoint_and_patches_preserve_originals(self):
        s=self.s;w.speak(s,'B','我声称九点离开了。');original=deepcopy(s['observations'])
        received=s['observations']['A'];source=received[-1]['id'];supplied={o['id'] for o in received}
        checkpoint=s['memory']['A']['checkpoint'];memory_entries.apply(s,'A',None,supplied)
        self.assertEqual(s['memory']['A']['checkpoint'],checkpoint)
        patch={'upsert':[{'id':'m1','kind':'heard_claim','text':'我听到对方说九点离开，尚未核实。','sources':[source]}],
               'archive':[],'processed_through':source}
        memory_entries.apply(s,'A',patch,supplied)
        self.assertEqual(s['memory']['A']['checkpoint'],len(received))
        self.assertEqual(next(r for r in s['memory']['A']['entries'] if r['id']=='m1')['kind'],'heard_claim')
        memory_entries.apply(s,'A',{'upsert':[],'archive':['m1'],'processed_through':None},supplied)
        self.assertNotIn('m1',{r['id'] for r in s['memory']['A']['entries']});self.assertEqual(len(s['memory_archive']['A']),1)
        self.assertEqual(s['observations'],original)

    def test_memory_cannot_skip_unsupplied_observations_or_cite_private_sources(self):
        rows=self.s['observations']['A'];patch={'upsert':[],'archive':[],'processed_through':rows[-1]['id']}
        with self.assertRaises(ValueError):memory_entries.revised(self.s,'A',patch,set())
        patch['processed_through']=None;patch['upsert']=[{'id':'m1','kind':'heard_claim','text':'不应获取私密信息。','sources':['B-o999999']}]
        with self.assertRaises(ValueError):memory_entries.revised(self.s,'A',patch,set())

    def test_belief_unchanged_and_explicit_clear_are_distinct(self):
        self.s['beliefs']['A']={'suspect':'B','explanation':'PRIVATE_REASONING','evidence_ids':[],'testimony_ids':[]}
        d=self.data();d['decision_mode']='investigation'
        raw={'action':{'kind':'wait','args':[]},'memory_update':None,'belief_update':None}
        self.assertEqual(memory_entries.decision(self.s,'A',raw,d)['reasoning'],'PRIVATE_REASONING')
        raw['belief_update']={'clear':True}
        self.assertEqual(memory_entries.decision(self.s,'A',raw,d)['reasoning'],'')
        raw['belief_update']={}
        with self.assertRaises(ValueError):memory_entries.decision(self.s,'A',raw,d)
        raw['choice']='wait'
        with self.assertRaises(ValueError):memory_entries.decision(self.s,'A',raw,d)

    def test_feedback_repetition_and_timed_completion_are_not_duplicate_executions(self):
        s=self.s;w.apply_choice(s,'A','inspect:c1');w.apply_choice(s,'A','share:c1');w.apply_choice(s,'A','share:c1')
        groups=action_feedback.for_role(s,'A')['groups']
        shares=next(g for g in groups if g['action']=='share' and g['actor']=='A')
        self.assertEqual(shares['count'],2);self.assertEqual(len(shares['recent']),2)
        w.apply_choice(s,'A','search');w.advance(s)
        search=next(g for g in action_feedback.for_role(s,'A')['groups'] if g['action']=='search')
        self.assertEqual(search['count'],1);self.assertEqual(search['recent'][-1]['status'],'completed')

    def test_feedback_does_not_learn_unseen_private_actions(self):
        before=action_feedback.for_role(self.s,'A')
        e=w.emit(self.s,'take','B','secret-hidden',execution={'actor':'B','kind':'take','args':['secret-hidden'],'location':'r3','recipients':['B']})
        w.note(self.s,'B',e,'PRIVATE_RECEIPT')
        self.assertEqual(before,action_feedback.for_role(self.s,'A'))

    def test_new_role_turn_records_incremental_memory_and_uses_v63(self):
        self.app.turn(self.s,'A',self.f.caller('ai-tasks-v63.json'),0)
        self.assertIn('entries',self.s['memory']['A'])
        wire=json.loads(self.f.provider.calls[-1][1]['messages'][-1]['content'])
        self.assertIn('sources',wire);self.assertIn('actions',wire);self.assertNotIn('choices',wire)

    def test_memory_pressure_consolidates_without_new_observations_or_idle_calls(self):
        s=self.s;source=s['observations']['A'][0]['id']
        s['memory']['A']={'summary':'已有主题','sources':[source],'checkpoint':len(s['observations']['A']),
                         'entries':[{'id':f'm{i}','kind':'unresolved','text':f'我还需要核对第{i}个时间疑点。','sources':[source]} for i in range(9)]}
        calls=[]
        def call(stage,task,baseline,data,validate,actor=None):
            calls.append(task)
            out={'entries':[{'id':'m0','kind':'unresolved','text':'我还需核对这些说法与时间记录之间的矛盾。','sources':[source]}],'processed_through':None}
            validate(out);return out,'memory-pressure-fixture'
        call.prefix_version='ai-tasks-v66.json'
        original=deepcopy(s['observations']);self.app.summarize(s,'A',call)
        self.assertEqual(calls,['ensemble_memory']);self.assertEqual(len(s['memory']['A']['entries']),1)
        self.assertEqual(len(s['memory_archive']['A']),9);self.assertEqual(s['observations'],original)
        self.assertFalse(self.app.compact(s,'A',call));self.assertEqual(len(calls),1)

    def test_dm_projection_preserves_utterance_time_knowledge(self):
        w.apply_choice(self.s,'A','inspect:c1')
        speech=w.speak(self.s,'A','我只看过第一份材料。')
        snapshot=deepcopy(speech['facts']['speaker_knowledge'])
        w.apply_choice(self.s,'A','move:r2');w.apply_choice(self.s,'A','inspect:c2')
        data={'utterances':[speech],'private_history':[]}
        restored=expand(compact_context.pack('ensemble_dm',data))['utterances'][0]
        self.assertEqual(restored['facts']['text'],speech['facts']['text'])
        self.assertEqual({r['id'] for r in restored['facts']['speaker_knowledge']['evidence']},{r['id'] for r in snapshot['evidence']})
        self.assertNotIn('c2',{r['id'] for r in restored['facts']['speaker_knowledge']['evidence']})

    def test_cancelled_timed_work_counts_one_execution(self):
        w.apply_choice(self.s,'A','search');w.apply_choice(self.s,'A','cancel_work')
        group=next(g for g in action_feedback.for_role(self.s,'A')['groups'] if g['action']=='search')
        self.assertEqual(group['count'],1);self.assertEqual(group['recent'][-1]['status'],'cancelled')


class RecoveryOptimizationTests(unittest.TestCase):
    def setUp(self):
        f=spectator_fixture.SpectatorTests();f.setUp();self.addCleanup(f.doCleanups)
        self.f=f;self.app=f.app;self.app.gateway.retry_delays=(0,0,0)
        f.create();f.change(lambda s:s['watch'].update(budget_usd=2.0,call_limit=512));self.original=self.app.gateway.client.transport

    def calls(self):
        with self.app.store.transaction(False) as c:
            return [dict(r) for r in c.execute("SELECT * FROM ai_calls WHERE game_id=? AND task='ensemble_role' ORDER BY started",(self.f.gid,))]

    def test_success_on_fourth_attempt_commits_once(self):
        remaining=[3]
        def transport(payload):
            if 'PALTER_TASK: ensemble_role\n' in payload['messages'][0]['content'] and remaining[0]:
                remaining[0]-=1;raise TimeoutError()
            return self.original(payload)
        self.app.gateway.client.transport=transport;self.f.cmd('watch_step');s=self.f.pump()
        self.assertIsNone(s['background_error']);self.assertEqual(s['watch']['steps'],1)
        self.assertEqual([r['status'] for r in self.calls()],['failed']*3+['completed'])
        self.assertEqual(len({r['request_hash'] for r in self.calls()}),1)

    def test_four_failures_stop_then_manual_round_can_succeed(self):
        self.f.provider.fail='ensemble_role'
        self.f.cmd('watch_step');before=deepcopy(self.f.state()['events']);s=self.f.pump()
        self.assertEqual(len(self.calls()),4);self.assertEqual(s['events'],before)
        self.assertEqual(s['background_error']['code'],'retry_exhausted');self.assertTrue(s['background_error']['retryable'])
        self.f.pump(3);self.assertEqual(len(self.calls()),4)
        self.f.provider.fail=None
        body={'command_id':'manual_resume_001','expected_revision':s['revision'],'kind':'watch_step'}
        self.app.command(self.f.owner,self.f.gid,body);self.app.command(self.f.owner,self.f.gid,body)
        s=self.f.pump();self.assertIsNone(s['background_error']);self.assertEqual(len(self.calls()),5)
        self.assertEqual(s['watch']['steps'],1)

    def test_nontransient_http_error_is_not_automatically_retried(self):
        def transport(payload):
            raise urllib.error.HTTPError('https://example.invalid',401,'unauthorized',{},None)
        self.app.gateway.client.transport=transport;self.f.cmd('watch_step');s=self.f.pump()
        self.assertEqual(len(self.calls()),1);self.assertFalse(s['background_error']['retryable'])

    def test_restart_does_not_renew_exhausted_allowance(self):
        self.f.provider.fail='ensemble_role';self.f.cmd('watch_step');s=self.f.pump()
        self.app=EnsembleApplication(self.app.store.path,DeepSeek(Settings(api_key='fixture'),self.f.provider));self.f.app=self.app
        self.app.gateway.retry_delays=(0,0,0)
        self.f.pump(2);self.assertEqual(len(self.calls()),4)
        self.assertEqual(self.f.state()['events'],s['events'])

    def test_preview_failure_is_visible_and_manual_recovery_is_idempotent(self):
        owner=self.app.store.session()['id'];self.f.provider.fail='ensemble_preview'
        with self.assertRaises(StoreError):
            self.app.create_game(owner,{'command_id':'new_preview_retry','expected_game_id':None,'category':'murder','humans':0})
        with self.app.store.transaction(False) as con:
            gid=con.execute('SELECT game_id FROM game_members WHERE session_id=?',(owner,)).fetchone()[0]
        before=self.app.store.state(owner,gid)
        self.assertTrue(self.app.view(owner,before)['background_error']['retryable'])
        self.f.provider.fail=None
        command={'command_id':'retry_preview_001','expected_revision':before['revision'],'kind':'retry_ai'}
        state,receipt=self.app.command(owner,gid,command)
        self.assertTrue(receipt['accepted']);self.assertIsNotNone(state['preview']);self.assertIsNone(state['story'])
        count=len(self.f.provider.calls)
        _,again=self.app.command(owner,gid,command)
        self.assertTrue(again['accepted']);self.assertTrue(again['duplicate']);self.assertEqual(len(self.f.provider.calls),count)

    def test_paid_role_and_dm_resume_preserves_original_json_field_order(self):
        original=self.original;counts={'ensemble_role':0,'ensemble_dm':0};paused=[False]
        def transport(payload):
            task=payload['messages'][0]['content'].split('PALTER_TASK: ')[1].split('\n')[0]
            response=original(payload)
            if task in counts:counts[task]+=1
            if task=='ensemble_role':
                out=json.loads(response['choices'][0]['message']['content'])
                for i,row in enumerate(out['memory_update']['upsert']):
                    out['memory_update']['upsert'][i]={k:row[k] for k in ('text','sources','kind','id')}
                response['choices'][0]['message']['content']=json.dumps(out,ensure_ascii=False)
            if task=='ensemble_dm' and not paused[0]:
                paused[0]=True;self.f.cmd('watch_pause')
            return response
        self.app.gateway.client.transport=transport;self.f.cmd('watch_step');s=self.f.pump()
        self.assertEqual(s['watch']['steps'],0);self.assertEqual(s['phase'],'paused')
        self.f.cmd('watch_step');s=self.f.pump()
        self.assertIsNone(s['background_error']);self.assertEqual(s['watch']['steps'],1)
        self.assertEqual(counts,{'ensemble_role':1,'ensemble_dm':1})

    def test_host_can_see_blocked_guest_control_without_guest_private_error(self):
        guest=self.app.store.session()['id']
        with self.app.store.transaction() as con:
            con.execute("INSERT INTO game_members VALUES (?,?,?)",(self.f.gid,guest,'B'))
        state=self.f.state();command={'command_id':'guest_failed_step','expected_revision':state['revision'],'kind':'say','_actor':'B'}
        def fail(s,call):raise StoreError('PRIVATE_GUEST_ERROR',409,'context_budget')
        with self.assertRaises(StoreError):self.app.operate(guest,self.f.gid,command,fail)
        view=self.app.view(self.f.owner,self.f.state())
        self.assertFalse(view['background_error']['retryable']);self.assertNotIn('PRIVATE_GUEST_ERROR',canonical(view))
        with self.assertRaises(StoreError):
            self.app.retry_background(self.f.owner,self.f.gid,{'command_id':'host_retry_guest','expected_revision':state['revision'],'kind':'retry_ai'})
        self.f.cmd('cancel_pending',operation_id='guest_failed_step')

    def test_foreground_budget_error_keeps_paid_setup_and_exposes_recovery(self):
        owner=self.app.store.session()['id']
        state=self.app.create_game(owner,{'command_id':'budget_preview_001','expected_game_id':None,'category':'murder','humans':0,'opening':'interactive'})
        gid=state['id'];original=self.original
        def transport(payload):
            response=original(payload)
            if 'PALTER_TASK: ensemble_setup\n' in payload['messages'][0]['content']:
                with self.app.store.transaction() as con:
                    old=self.app.store.load(con,owner,gid);new=deepcopy(old);new['watch']['budget_usd']=0;new['revision']+=1;self.app.store.save(con,new,old)
            return response
        self.app.gateway.client.transport=transport
        with self.assertRaises(StoreError) as error:
            self.app.command(owner,gid,{'command_id':'budget_confirm_001','expected_revision':state['revision'],'kind':'confirm'})
        self.assertEqual(error.exception.code,'watch_budget')
        current=self.app.store.state(owner,gid);view=self.app.view(owner,current)
        self.assertEqual(view['background_error']['code'],'watch_budget');self.assertTrue(view['background_error']['retryable'])
        self.app.gateway.client.transport=original
        current,_=self.app.command(owner,gid,{'command_id':'budget_add_001','expected_revision':current['revision'],'kind':'watch_add_budget'})
        current,receipt=self.app.command(owner,gid,{'command_id':'budget_retry_001','expected_revision':current['revision'],'kind':'retry_ai'})
        self.assertTrue(receipt['accepted']);self.assertEqual(current['phase'],'reading')
        with self.app.store.transaction(False) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM ai_calls WHERE game_id=? AND task='ensemble_setup'",(gid,)).fetchone()[0],1)

    def test_cancellation_during_backoff_stops_before_second_call(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading,time
        entered=threading.Event();self.app.gateway.retry_delays=(2,2,2)
        def transport(payload):
            entered.set();raise TimeoutError()
        self.app.gateway.client.transport=transport;self.f.cmd('watch_step')
        with ThreadPoolExecutor() as pool:
            future=pool.submit(self.f.pump);self.assertTrue(entered.wait(2))
            trace=self.app.gateway.trace(self.f.owner,self.f.gid)
            self.f.cmd('watch_pause')
            self.f.cmd('cancel_pending',operation_id=trace['operation_id'])
            future.result(4)
        self.assertEqual(len(self.calls()),1)
        with self.app.store.transaction(False) as con:
            status=con.execute('SELECT status FROM ai_operations WHERE game_id=? AND id=?',(self.f.gid,trace['operation_id'])).fetchone()[0]
        self.assertEqual(status,'cancelled')

    def test_source_lookup_then_listener_uses_two_bounded_continuations(self):
        from tests.test_event_tools import tool,proposal
        source=self.f.state()['case']['roles']['A']['knows'][0];original=self.original;requests=[]
        def transport(payload):
            if 'PALTER_TASK: ensemble_role\n' not in payload['messages'][0]['content']:return original(payload)
            requests.append(deepcopy(payload));feedback=[m for m in payload['messages'] if m['role']=='tool']
            if len(feedback)<2:
                native=({'id':'lookup_1','type':'function','function':{'name':'read_sources','arguments':canonical({'requests':[{'id':source,'offset':0}]})}}
                    if not feedback else tool(proposal(),'listener_1'))
                return {'choices':[{'finish_reason':'tool_calls','message':{'role':'assistant','content':None,'tool_calls':[native]}}],
                    'usage':{'prompt_tokens':100,'completion_tokens':30,'prompt_cache_hit_tokens':40,'prompt_cache_miss_tokens':60}}
            response=original(payload);out=json.loads(response['choices'][0]['message']['content'])
            out['next_decision']={'mode':'wait','events':[json.loads(feedback[-1]['content'])['wait_event']]}
            response['choices'][0]['message']['content']=canonical(out);return response
        self.app.gateway.client.transport=transport;self.f.cmd('watch_step');s=self.f.pump()
        self.assertIsNone(s['background_error']);self.assertEqual(len(requests),3)
        self.assertEqual(len(s['event_listeners']),1)
        feedback=[json.loads(m['content']) for m in requests[-1]['messages'] if m['role']=='tool']
        self.assertEqual(feedback[0]['sources'][0]['id'],source)
        self.assertEqual(feedback[0]['sources'][0]['status'],'complete')

    def test_failed_stage_blocks_new_unrelated_operations(self):
        self.f.provider.fail='ensemble_role';self.f.cmd('watch_step');self.f.pump()
        with self.assertRaises(StoreError) as error:
            self.app.operate(self.f.owner,self.f.gid,{'command_id':'unrelated_operation','expected_revision':self.f.state()['revision']},lambda s,call:None)
        self.assertEqual(error.exception.code,'ai_pending')


if __name__=='__main__':unittest.main()
