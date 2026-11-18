from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from palter.ensemble import EnsembleApplication
from palter import ensemble_world as w
from palter.scenario_cases import opening_order, build
from palter.deepseek import DeepSeek, Settings
from palter.storage import StoreError, canonical
from palter.case_authoring import candidate_casts, validate_generated_cast


def story_fixture():
    return {'title':'共同的原始记录','briefing':'四位参与者需要核实记录并作出自己的选择。',
        'rooms':{r:{'name':n,'description':'这里保存着可检查的资料和工具。'} for r,n in zip(('r1','r2','r3'),('会客室','工作室','档案间'))},
        'roles':{a:{'persona':'参与者'+a,'secret':a+'_PRIVATE_SECRET_CANARY：曾经替人隐瞒一笔私人借款。',
                       'secret_record':'签署文件记载了'+a+'承担的那笔私人借款。','relationships':['旧识','合作伙伴','曾有分歧']} for a in 'ABCD'}}


class EnsembleProvider:
    def __init__(self):
        self.calls=[];self.policy=lambda d:'accept:'+d['invitations'][0]['id'] if d['invitations'] else 'wait'
        self.address=None;self.fail=None;self.block=None;self.entered=threading.Event();self.release=threading.Event()
        self.question=None;self.world='none';self.relation=False
        self.next_decision=lambda d:{'mode':'wait' if d.get('scheduling',{}).get('wait_frequency',{}).get('wait_allowed',True) else 'continue','events':[]}
    def __call__(self,payload):
        task=payload['messages'][0]['content'].split('PALTER_TASK: ')[1].split('\n')[0]
        data=json.loads(next(m['content'] for m in reversed(payload['messages']) if m['role']=='user'))
        optimized=data.get('context_format')==1
        if optimized:
            from tests.compact_fixture import expand
            data=expand(data)
        self.calls.append((task,deepcopy(payload),deepcopy(data)))
        if task==self.fail:raise TimeoutError()
        if task==self.block:self.entered.set();self.release.wait(5)
        if task=='ensemble_preview':out={'candidates':[{'title':'故事'+str(i),'introduction':'四个人在共同的场所调查旧事。',
            'cast':dict(zip('ABCD',['陶铸生','樊素琴','骆行简','纪惟真'])),'victim':'聂守仁'} for i in range(3)]}
        elif task=='ensemble_setup':out=story_fixture()
        elif task=='ensemble_opening':out={'volunteer':False,'handling':'inspect'}
        elif task=='ensemble_address':out={'target':self.address}
        elif task=='ensemble_role':
            out={'choice':self.policy(data),'speech':'我会核对已经看到的原始材料，再决定怎样回应。','gesture':None,'question_to':self.question,
                 'memory':'我保留已经听到的说法，还需要核对矛盾。','memory_sources':[o['id'] for o in data['observations'][-1:]],
                 'relationships':[],'suspect':None,'evidence_ids':[],'reasoning':''}
            if 'scheduling' in data:out['next_decision']=self.next_decision(data)
            if out['choice']=='lock_conclusion':out['final_conclusion']={k:v for k,v in dict(suspect=out['suspect'],explanation=out['reasoning'],evidence_ids=out['evidence_ids'],testimony_ids=[]).items()}
            if self.relation and data['observations']:
                target=next(a for a in 'ABCD' if a!=data['actor'])
                out['relationships']=[{'target':target,'trust_delta':.1,'affinity_delta':-.1,'reason':'刚才听到的说法让我重新考虑。','sources':[data['observations'][-1]['id']]}]
            if data.get('decision_mode')=='concealment':
                for key in ('suspect','reasoning','evidence_ids'):out.pop(key,None)
                out.update(situation='我只根据已经听到的质疑判断风险。',strategy='我先回应眼前的问题，再决定行动。',assessment_sources=[o['id'] for o in data['observations'][-1:]])
        elif task=='ensemble_dm':
            out={'assessments':[],'cues':[],'disclosures':[]}
            if 'tracked_events' in data:
                out['event_decisions']=[{'id':e['id'],'status':'active','reason':'尚待实际结果。','progress':e['progress'],'source_ids':[]} for e in data['tracked_events']]
            for item,event in zip(out.get('event_decisions',[]),data.get('tracked_events',[])):
                if 'decision_context' in event:item['basis']={'kind':'current_circumstances','workflow_stage':None}
        elif task=='ensemble_world':out={'choice':self.world}
        elif task=='ensemble_memory':out={'summary':'自己的经历与判断。','sources':[o['id'] for o in data['observations'][-1:]]}
        elif task=='ensemble_action':out={'choice':'wait','clarification':''}
        elif task=='ensemble_theory' and data.get('review_mode')=='concealment':
            out={'position_summary':'角色保留自己的对外立场；定案与目标结果按实际提交结算。','evidence_checks':[]}
        elif task in ('case_theory','ensemble_theory'):
            out={'argument_sources':[c['id'] for c in data['cited_evidence']],'claims':[{'aspect':a,'quote':data['explanation'],'supported':True,'evidence_ids':[c['id'] for c in data['cited_evidence']]} for a in ('identity','time','method')]}
            if data.get('review_version'):
                for claim in out['claims']:claim['reason']='测试替身确认这部分论述。'
        elif task=='ensemble_ending':out={'title':'各自的结果','narrative':'按实际取得的材料和做出的选择，分别结算主要目标与私人目标。'}
        else:raise AssertionError(task)
        if optimized:
            from tests.compact_fixture import response
            out=response(task,out,data)
        return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps(out,ensure_ascii=False)}}],
                'usage':{'prompt_tokens':100,'completion_tokens':30,'prompt_cache_hit_tokens':40,'prompt_cache_miss_tokens':60}}


class EnsembleTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.provider=EnsembleProvider();self.client=DeepSeek(Settings(api_key='fixture'),self.provider)
        self.app=EnsembleApplication(Path(self.directory.name)/'test.sqlite3',self.client)
        self.owners={a:self.app.store.session()['id'] for a in 'ABCD'};self.serial=0;self.gid=None
    def create(self,scenario='murder',humans=4,opening='after',ready=True):
        state=self.app.create_game(self.owners['A'],{'command_id':'new_game_0001','expected_game_id':None,'category':scenario,'humans':humans,'opening':opening});self.gid=state['id']
        for a in 'ABCD'[1:humans]:self.app.join(self.owners[a],{'command_id':'join_game_'+a,'code':state['join_code']})
        self.cmd('A','confirm')
        if opening=='interactive':return self.state()
        if ready:
            for a in 'ABCD'[:humans]:self.cmd(a,'ready')
        return self.state()
    def state(self):return self.app.store.state(self.owners['A'],self.gid)
    def cmd(self,a,kind,**extra):
        self.serial+=1;s=self.state()
        return self.app.command(self.owners[a],self.gid,{'command_id':f'command_{self.serial:06d}','expected_revision':s['revision'],'kind':kind,**extra})
    def change(self,fn):
        with self.app.store.transaction() as con:
            old=self.app.store.load(con,self.owners['A'],self.gid);s=deepcopy(old);fn(s);s['revision']+=1;self.app.store.save(con,s,old)
    def drain(self,limit=30):
        for _ in range(limit):
            if not self.app.pump(self.gid,force=True):return
            self.assertIsNone(self.state()['background_error'])
        self.fail('background agenda did not terminate')
    def inspect_all(self,a='A'):
        for room in ('r1','r2','r3'):
            if self.state()['locations'][a]!=room:self.cmd(a,'act',choice='move:'+room)
            self.cmd(a,'act',choice='search');self.cmd(a,'act',choice='wait')
            for choice in list(w.choices(self.state(),a)):
                if choice['id'].startswith('inspect:'):self.cmd(a,'act',choice=choice['id'])
    def close_all(self,**submission):
        for a in self.state()['humans']:self.cmd(a,'submit',**submission)

    def test_model_names_survive_preview_setup_and_duplicate_creation(self):
        s=self.create();preview=next(c for c in self.provider.calls if c[0]=='ensemble_preview')
        self.assertNotIn('rosters',preview[2]);self.assertEqual(preview[2]['participants'],list('ABCD'))
        expected=dict(zip('ABCD',['陶铸生','樊素琴','骆行简','纪惟真']))
        self.assertEqual(s['preview']['cast'],expected)
        self.assertEqual({a:r['name'] for a,r in s['case']['roles'].items()},expected)
        self.assertEqual(s['case']['victim'],'聂守仁')
        count=len(self.provider.calls)
        repeated=self.app.create_game(self.owners['A'],{'command_id':'new_game_0001','expected_game_id':None,'category':'murder','humans':4,'opening':'after'})
        self.assertEqual(repeated['preview'],s['preview']);self.assertEqual(len(self.provider.calls),count)

    def test_pinned_legacy_preview_keeps_original_roster_request(self):
        self.app.gateway.current_version='ai-tasks-v59.json'
        s=self.create();call=next(c for c in self.provider.calls if c[0]=='ensemble_preview')
        rosters=candidate_casts(int(s['id'][:8],16));index=int(s['id'][8:16],16)%3
        self.assertNotIn('participants',call[2]);self.assertEqual(call[2]['rosters'],rosters)
        self.assertEqual(s['preview']['cast'],rosters[index]['cast']);self.assertEqual(s['preview']['victim'],rosters[index]['victim'])

    def test_generated_cast_requires_distinct_entities_without_a_name_dictionary(self):
        candidate={'cast':dict(zip('ABCD',['阿依古丽','卡洛斯·维加','欧阳修竹','山田梓'])),'victim':'罗莎'}
        validate_generated_cast(candidate)
        for broken in ({**candidate,'victim':'阿依古丽'}, {**candidate,'cast':{'A':'阿依古丽'}},
                       {**candidate,'victim':'  '}, {**candidate,'cast':{**candidate['cast'],'D':' 阿依古丽 '}}):
            with self.assertRaises(ValueError):validate_generated_cast(broken)

    def test_scoped_seats_and_unjoined_access(self):
        s=self.create(humans=2)
        for a in 'AB':
            v=self.app.view(self.owners[a],s);self.assertEqual(v['actor'],a)
            raw=canonical(v)
            for other in 'ABCD':
                if other!=a:self.assertNotIn(other+'_PRIVATE_SECRET_CANARY',raw)
        with self.assertRaises(StoreError):self.app.store.state(self.owners['C'],self.gid)
        self.assertEqual(len(self.app.store.games(self.owners['B'])),1)
        with self.assertRaises(StoreError):self.cmd('B','say',text='x',actor='A')

    def test_multiplayer_reading_barrier_deadline_and_review(self):
        self.create(humans=2,ready=False)
        self.cmd('A','ready');self.assertEqual(self.state()['phase'],'reading')
        self.assertFalse(self.app.pump(self.gid,force=True))
        self.change(lambda s:s.update(reading_deadline=time.time()-1))
        self.app.pump(self.gid,force=True);self.assertEqual(self.state()['phase'],'active')
        with self.assertRaises(StoreError):self.cmd('A','pause')
        before=len(self.provider.calls);self.app.view(self.owners['B'],self.state())
        self.assertEqual(len(self.provider.calls),before)

    def test_all_ready_starts_early_and_single_reading_has_no_timer(self):
        self.create(humans=1,ready=False)
        self.assertIsNone(self.state()['reading_deadline']);self.assertFalse(self.app.pump(self.gid,force=True))
        self.cmd('A','ready');self.assertEqual(self.state()['phase'],'active')

    def test_multiplayer_reading_interval_starts_after_setup_delivery(self):
        from unittest.mock import patch
        with patch('palter.ensemble_world.now',return_value=time.time()-3600):
            self.create(humans=2,ready=False)
        self.assertGreater(self.state()['reading_deadline'],time.time()+115)

    def test_opening_priority_fallback_and_one_killer(self):
        for humans in (['A'],list('ABCD')):
            for seed in range(6):
                intentions={a:{'volunteer':False,'handling':'leave'} for a in 'ABCD'}
                killer,order=opening_order(seed,humans,intentions)
                self.assertIn(killer,[a for a in 'ABCD' if a not in humans] or humans);self.assertEqual(len(set(order)),4)
                intentions['A']['volunteer']=True;intentions['D']['volunteer']=True
                killer,order=opening_order(seed,['A'],intentions);self.assertEqual(killer,'A');self.assertEqual(order[0],'A')
        self.create(humans=2,opening='interactive')
        self.cmd('A','opening',volunteer=True,handling='leave');self.assertEqual(self.state()['phase'],'opening')
        self.cmd('B','opening',volunteer=False,handling='leave');s=self.state()
        self.assertEqual(s['phase'],'reading');self.assertEqual(s['case']['solution']['killer'],'A')
        self.assertIn('crime',s['case']['roles']['A']['knows']);self.assertNotIn('crime',s['case']['roles']['B']['knows'])
        self.assertTrue(any('立即离开' in h['text'] for h in s['case']['history'] if h['id']=='visit_B'))

    def test_ai_private_chat_actually_advances_and_ends(self):
        self.create(humans=1);self.change(lambda s:s.update(agenda=[]))
        self.provider.policy=lambda d:'invite:C' if d['actor']=='B' and not any(i['to']=='C' for i in self.state()['invitations']) else 'accept:'+d['invitations'][0]['id'] if d['invitations'] else 'wait'
        self.cmd('A','say',target='B',text='你可以自己决定找谁交流。')
        self.drain()
        chats=[c for c in self.state()['chats'].values() if set(c['participants'])=={'B','C'}]
        self.assertTrue(chats);self.assertEqual(len(chats[0]['turns']),8);self.assertEqual(chats[0]['status'],'closed')
        private_ids={t['event_id'] for t in chats[0]['turns']}
        self.assertFalse(private_ids&{o['event_id'] for o in self.state()['observations']['A']})
        self.assertTrue(any(t=='ensemble_dm' and d['private_history'] for t,_,d in self.provider.calls))

    def test_response_obligation_and_periodic_words(self):
        self.create();self.cmd('B','say',target='A',text='你刚才在哪里？')
        with self.assertRaises(StoreError):self.cmd('A','act',choice='move:r2')
        self.cmd('A','gesture',text='点头');self.cmd('A','act',choice='move:r2')
        self.cmd('A','gesture',text='点头')
        self.assertFalse(w.must_speak(self.state(),'A'))
        self.cmd('A','act',choice='move:r1')
        self.change(lambda s:s['silent'].update(A=w.speech_limit(s,'A')))
        with self.assertRaises(StoreError):self.cmd('A','gesture',text='点头')
        self.cmd('A','say',target='B',text='我愿意说明自己的经历。')
        self.assertFalse(w.must_speak(self.state(),'A'))

    def test_challenge_needs_words_and_does_not_end_case(self):
        self.create();self.cmd('A','act',choice='inspect:c1')
        self.cmd('A','challenge',target='B',text='请解释这份记录与你的话为何不同。',evidence_ids=['c1'])
        with self.assertRaises(StoreError):self.cmd('B','gesture',text='点头')
        self.cmd('B','say',target='A',text='我还需要核对时间，但可以解释自己看过什么。')
        self.assertEqual(self.state()['phase'],'active')

    def test_dm_receives_acquired_knowledge_at_speech_not_future_state(self):
        self.create();self.cmd('B','act',choice='inspect:c1')
        self.cmd('B','say',target='A',text='我刚看过这份原件。')
        dm=next(d for t,_,d in reversed(self.provider.calls) if t=='ensemble_dm')
        self.assertIn('c1',{c['id'] for c in dm['utterances'][0]['facts']['speaker_knowledge']['evidence']})
        self.cmd('B','act',choice='move:r2');self.cmd('B','act',choice='inspect:c2')
        self.assertNotIn('c2',{c['id'] for c in dm['utterances'][0]['facts']['speaker_knowledge']['evidence']})

    def test_private_absence_does_not_create_public_knowledge_or_obligation(self):
        self.create();self.cmd('A','act',choice='invite:B');self.cmd('B','act',choice='accept:i1')
        before=deepcopy(self.state()['observations']['A']);silent=self.state()['silent']['A']
        self.cmd('C','say',target='D',text='OUTSIDE_PRIVATE_CANARY')
        self.assertEqual(self.state()['observations']['A'],before);self.assertEqual(self.state()['silent']['A'],silent)
        self.cmd('A','act',choice='end_private')
        self.assertNotIn('OUTSIDE_PRIVATE_CANARY',canonical(self.app.view(self.owners['A'],self.state())))

    def test_private_exit_does_not_require_answering_a_challenge_or_disclose_it(self):
        self.create();self.cmd('A','act',choice='invite:B');self.cmd('B','act',choice='accept:i1')
        self.change(lambda s:w.speak(s,'B','PRIVATE_UNANSWERED_CHALLENGE','A',challenge=True))
        self.assertTrue(self.state()['obligations']['A']['explain']);before=len(self.provider.calls)
        self.cmd('A','act',choice='end_private');s=self.state()
        self.assertIsNone(w.chat_for(s,'A'));self.assertEqual(len(self.provider.calls),before)
        self.assertFalse(s['obligations']['A']['response']);self.assertFalse(s['obligations']['A']['explain'])
        self.assertIn('PRIVATE_UNANSWERED_CHALLENGE',canonical(s['observations']['A']))
        self.assertNotIn('PRIVATE_UNANSWERED_CHALLENGE',canonical(w.view(s,'C')))
        self.cmd('A','act',choice='move:r2')

    def test_ai_addressing_absent_role_preserves_words_without_delivering_or_blocking(self):
        self.create(humans=1)
        def prepare(s):
            w.apply_choice(s,'B','inspect:sB');w.apply_choice(s,'C','invite:D');w.apply_choice(s,'D','accept:'+s['invitations'][-1]['id'])
            s['agenda']=[];w.enqueue(s,'B','回应当前公开交流。')
        self.change(prepare);before=self.state()
        self.provider.question='D';self.provider.policy=lambda d:'share:sB'
        self.assertTrue(self.app.pump(self.gid,force=True));after=self.state()
        self.assertIsNone(after['background_error'])
        speech=next(e for e in after['events'][len(before['events']):] if e['kind']=='testimony')
        self.assertEqual(speech['target'],'D');self.assertEqual(speech['facts']['unheard_target'],'D')
        self.assertEqual(speech['facts']['recipients'],['A','B'])
        self.assertEqual(speech['facts']['text'],'我会核对已经看到的原始材料，再决定怎样回应。')
        for a in 'CD':
            self.assertEqual(after['observations'][a],before['observations'][a])
            self.assertEqual(after['obligations'][a],before['obligations'][a])
            self.assertNotIn('sB',after['known'][a])
        self.assertIn('sB',after['known']['A']);self.assertEqual(after['case_hash'],before['case_hash'])

    def test_private_unheard_question_does_not_escape_its_channel(self):
        s=self.create();w.apply_choice(s,'C','invite:D');w.apply_choice(s,'D','accept:'+s['invitations'][-1]['id'])
        outside={a:deepcopy(s['observations'][a]) for a in 'AB'}
        e=w.speak(s,'C','PRIVATE_UNHEARD_CANARY',target='A',allow_unheard=True)
        self.assertEqual(e['facts']['recipients'],['C','D']);self.assertEqual(e['target'],'A')
        for a in 'AB':self.assertEqual(s['observations'][a],outside[a])
        self.assertFalse(s['obligations']['A']['response'])
        with self.assertRaises(StoreError):w.speak(s,'C','不能发给不存在的对象',target='DM',allow_unheard=True)

    def test_inferred_human_addressee_can_be_unheard_without_rewriting_words(self):
        self.create();self.cmd('C','act',choice='invite:D');self.cmd('D','act',choice='accept:i1')
        before=self.state();self.provider.address='D';words='我想问你当时看到的情况。'
        self.cmd('A','say',text=words);s=self.state()
        speech=next(e for e in s['events'][len(before['events']):] if e['kind']=='testimony')
        self.assertEqual(speech['facts']['text'],words);self.assertEqual(speech['facts']['unheard_target'],'D')
        self.assertEqual(s['observations']['D'],before['observations']['D'])
        data=next(d for task,_,d in reversed(self.provider.calls) if task=='ensemble_address')
        self.assertIn('D',data['cast']);self.assertNotIn('D',data['conversation']['listeners'])
        with self.assertRaises(StoreError):self.cmd('A','say',target='D',text='显式选择的对象必须仍在当前谈话中。')

    def test_unknown_ai_addressee_still_rejects_invalid_model_output(self):
        self.create(humans=1);before=self.state();self.provider.question='DM'
        self.app.pump(self.gid,force=True);after=self.state()
        self.assertIsNotNone(after['background_error']);self.assertEqual(after['events'],before['events'])

    def test_conversation_context_is_versioned_for_pinned_recovery(self):
        s=self.create();w.apply_choice(s,'C','invite:D');w.apply_choice(s,'D','accept:'+s['invitations'][-1]['id'])
        def call(*args):pass
        call.prefix_version='ai-tasks-v28.json';data=w.context(s,'B');original=deepcopy(data)
        self.app.conversation_context(s,'B',data,call,'ensemble_role');self.assertEqual(data,original)
        call.prefix_version=self.app.gateway.current_version
        self.app.conversation_context(s,'B',data,call,'ensemble_role')
        self.assertEqual(set(data['conversation']['listeners']),{'A'})
        self.assertEqual(set(data['conversation']['unavailable_addressees']),{'C','D'})

    def test_periodic_speech_rejection_identifies_actual_obligation(self):
        self.create();self.change(lambda s:s['silent'].update(A=w.speech_limit(s,'A')))
        with self.assertRaisesRegex(StoreError,'连续几次交流没有发言'):self.cmd('A','act',choice='search')
        v=self.app.view(self.owners['A'],self.state())
        self.assertTrue(v['must_speak']);self.assertFalse(v['must_respond']);self.assertFalse(v['must_explain'])

    def test_dialogue_attaches_only_received_cues_to_their_original_words(self):
        s=self.create();w.apply_choice(s,'C','invite:D');w.apply_choice(s,'D','accept:i1')
        s['locations']['B']='r2'
        def utterance(actor,words,cues):
            start=len(s['events']);speech=w.speak(s,actor,words)
            def call(stage,task,baseline,data,validate):
                out={'assessments':[],'disclosures':[],
                     'cues':[{'event_id':speech['id'],'cue':cue} for cue in cues]}
                validate(out);return out,'fixture'
            call.prefix_version='ai-tasks-v35.json'
            self.app.adjudicate_ensemble(s,start,call)
            return speech['id']
        first=utterance('A','我会保留原话。',['pause','gaze'])
        second=utterance('B','我在另一个房间回答。',['pause','gaze'])
        plain=utterance('B','这句话没有附带动作。',[])
        private=utterance('C','PRIVATE_CUE_CANARY',['pause','gaze'])
        original=deepcopy(s)
        def speeches(actor):
            return {o['event_id']:o for o in w.view(s,actor)['observations'] if o['kind']=='testimony'}
        a,b,c=speeches('A'),speeches('B'),speeches('C')
        self.assertEqual(a[first]['text'],'我会保留原话。')
        self.assertEqual(len(a[first]['cues']),2)
        self.assertNotIn(second,a)  # A different room receives neither words nor cues.
        self.assertEqual(len(b[second]['cues']),2)
        self.assertNotIn(plain,a);self.assertNotIn(private,a)
        self.assertIn(private,c);self.assertNotIn(first,c);self.assertNotIn(second,c)
        self.assertNotIn('PRIVATE_CUE_CANARY',canonical(w.view(s,'A')))
        self.assertEqual(s,original,'presentation must not rewrite saved observations')
        attached=[o for o in w.view(s,'A')['observations'] if o['kind']=='cue']
        self.assertEqual({o['utterance_event_id'] for o in attached},{first})

    def test_contextual_microexpressions_preserve_words_and_visibility(self):
        s=self.create();s['locations']['B']='r2'
        start=len(s['events']);words='我没有碰过那份记录。'
        speech=w.speak(s,'A',words)
        cue={'event_id':speech['id'],'modality':'visible','text':'嘴角绷了一瞬，又恢复了原来的神情。'}
        def call(stage,task,baseline,data,validate):
            self.assertEqual(data['utterances'][0]['facts']['text'],words)
            self.assertIn('speaker_knowledge',data['utterances'][0]['facts'])
            out={'assessments':[{'event_id':speech['id'],'verdict':'uncertain'}],'disclosures':[],'cues':[cue],'event_decisions':[]}
            validate(out);return out,'fixture'
        self.app.adjudicate_ensemble(s,start,call)
        def received(actor):
            return next(o for o in w.view(s,actor)['observations'] if o['event_id']==speech['id'])
        self.assertEqual(received('A')['text'],words)
        self.assertEqual(received('C')['cues'],[{'text':cue['text']}])
        self.assertFalse(any(o['event_id']==speech['id'] for o in w.view(s,'B')['observations']))
        self.assertNotIn('uncertain',canonical(w.view(s,'C')))
        start=len(s['events']);speech=w.speak(s,'A','我再说明一次。')
        cue={'event_id':speech['id'],'modality':'audible','text':'说到最后几个字时，语速放慢了一点。'}
        words='我再说明一次。'
        self.app.adjudicate_ensemble(s,start,call)
        self.assertFalse(any(o['event_id']==speech['id'] for o in w.view(s,'B')['observations']))
        self.assertEqual(received('C')['cues'],[{'text':cue['text']}])

    def test_directional_relationship_changes_have_sources(self):
        self.create(humans=1);self.change(lambda s:s.update(agenda=[]));self.provider.relation=True
        self.cmd('A','say',target='C',text='请说明刚才的观察。');self.app.pump(self.gid,force=True)
        r=self.state()['relationships']['C']['A'];self.assertEqual(r['trust'],.1);self.assertTrue(r['experiences'][0]['sources'])
        self.assertEqual(self.state()['relationships']['A']['C']['trust'],0)

    def test_hide_destroy_and_forgery_preserve_acquired_evidence_and_truth(self):
        self.create();fixed=self.state()['case_hash'];self.cmd('A','act',choice='inspect:sA')
        snapshot=deepcopy(self.state()['known']['A']['sA'])
        self.cmd('A','act',choice='destroy:sA');self.cmd('A','act',choice='wait')
        self.assertEqual(self.state()['objects']['sA']['condition'],'destroyed');self.assertEqual(self.state()['known']['A']['sA'],snapshot)
        self.assertTrue(w.must_speak(self.state(),'A'))
        with self.assertRaises(StoreError):self.cmd('A','gesture',text='点头')
        self.cmd('A','say',target='B',text='我处理了这张纸，但你们已经看到的内容不会因此消失。')
        self.cmd('A','forge',text='某人承认了所有事情。');doc=next(c for c in self.state()['known']['A'] if c.startswith('document'))
        self.assertNotIn(doc,{c['id'] for c in self.state()['case']['clues']});self.assertEqual(self.state()['case_hash'],fixed)
        self.cmd('A','act',choice='share:sA');self.assertIn('sA',self.state()['known']['B'])

    def test_timed_actions_cancel_and_shared_clock(self):
        self.create('rescue');self.cmd('A','act',choice='move:r2');self.cmd('A','act',choice='repair')
        self.assertFalse(self.state()['radio']);self.assertEqual(self.state()['supplies']['battery'],2)
        self.cmd('A','act',choice='cancel_work');self.cmd('B','act',choice='wait')
        self.assertFalse(self.state()['radio']);self.assertEqual(self.state()['supplies']['battery'],2)
        self.cmd('A','act',choice='repair');self.cmd('B','act',choice='wait');self.assertTrue(self.state()['radio'])

    def test_competing_custody_change_records_failed_timed_effect(self):
        self.create();self.cmd('A','act',choice='place:sA');self.cmd('A','act',choice='hide:sA')
        self.cmd('B','act',choice='take:sA')
        self.assertEqual(self.state()['activities'][-1]['status'],'failed')
        self.assertEqual(self.state()['objects']['sA']['holder'],'B')
        self.assertFalse(self.state()['objects']['sA']['hidden'])
        self.assertTrue(any(e['kind']=='action_failed' and e['facts']['action']=='hide' for e in self.state()['events']))

    def test_world_effect_has_real_state_and_restores_access(self):
        self.create();self.change(lambda s:s.update(world_due=True));self.provider.world='block:r2'
        self.app.pump(self.gid,force=True);self.assertEqual(self.state()['blocked_room'],'r2')
        with self.assertRaises(StoreError):self.cmd('A','act',choice='move:r2')
        for _ in range(3):self.cmd('A','act',choice='wait')
        self.assertIsNone(self.state()['blocked_room'])

    def test_following_observes_future_movement_only(self):
        self.create();self.cmd('A','act',choice='follow:B');self.cmd('B','act',choice='move:r2')
        self.assertEqual(self.state()['locations']['A'],'r2');self.assertNotIn('A',self.state()['following'])
        self.assertTrue(any('跟随' in o['text'] for o in self.state()['observations']['A']))

    def test_theft_requires_actual_return_not_claim(self):
        self.create('theft');s=self.state();holder=s['items']['artifact']['holder'];owner=s['items']['artifact']['owner']
        if holder!=owner:
            self.cmd(holder,'say',target=owner,text='东西已经归还了。')
            self.assertFalse(w.results(self.state(),{})['shared_success'])
            self.cmd(holder,'act',choice='transfer:artifact:'+owner)
        self.assertTrue(w.results(self.state(),{})['shared_success'])

    def test_family_commitments_require_both_and_can_be_broken(self):
        self.create('family');self.cmd('A','act',choice='promise:B');c=self.state()['commitments'][0]
        self.assertEqual(c['status'],'proposed');self.cmd('B','act',choice='agree:'+c['id'])
        self.assertEqual(self.state()['commitments'][0]['status'],'agreed')
        self.cmd('A','act',choice='withdraw:'+c['id']);self.assertEqual(self.state()['commitments'][0]['status'],'withdrawn')

    def test_council_votes_and_resource_pledges_have_distinct_results(self):
        self.create('council')
        for a in 'ABC':self.cmd(a,'act',choice='vote:D')
        self.cmd('A','act',choice='pledge:D');r=w.results(self.state(),{})
        self.assertTrue(r['shared_success']);self.assertFalse(r['participants']['A']['personal'])
        self.cmd('A','act',choice='fund:D');self.assertTrue(w.results(self.state(),{})['participants']['A']['personal'])
        self.assertEqual(self.state()['resources']['A'],1)

    def test_house_fixed_mechanism_and_personal_keepsake(self):
        self.create('house');self.cmd('A','act',choice='move:r3');self.cmd('A','act',choice='collect:keepsake_A')
        self.cmd('A','act',choice='switch:1');self.cmd('A','act',choice='move:r1');self.cmd('A','act',choice='leave')
        result=w.results(self.state(),{})['participants']['A'];self.assertTrue(result['primary']);self.assertTrue(result['personal'])

    def test_archive_requires_correct_dials_and_actual_recovery(self):
        self.create('archive');self.cmd('A','act',choice='move:r3');solution=self.state()['case']['solution']['dials']
        for i,value in enumerate(solution):self.cmd('A','act',choice=f'dial:{i}:{value}')
        self.assertTrue(self.state()['vault']);self.assertFalse(w.results(self.state(),{})['shared_success'])
        for i in (1,2):self.cmd('A','act',choice='collect:archive_'+str(i))
        self.assertTrue(w.results(self.state(),{})['participants']['A']['success'])

    def test_passive_innocent_does_not_win_and_personal_goal_can_fail(self):
        self.create();s=self.state();killer=s['case']['solution']['killer'];innocent=next(a for a in 'ABCD' if a!=killer)
        evaluations={killer:{'result':'established'}}
        self.assertFalse(w.results(s,evaluations)['participants'][innocent]['success'])
        for a in 'ABCD':
            s['contributions'][a]=list(s['case']['proofs']['identity'][0]);s['public_evidence']=['s'+c for c in 'ABCD']
            if a!=killer:evaluations[a]={'result':'unproven','established':['time'],'suspect':killer}
        r=w.results(s,evaluations)
        a=next(a for a in 'AC' if a!=killer)
        self.assertTrue(r['participants'][a]['primary']);self.assertFalse(r['participants'][a]['personal'])

    def test_final_waits_for_every_human_and_reveals_only_after(self):
        self.create('family');self.cmd('A','submit',text='我愿意结束。')
        v=self.app.view(self.owners['B'],self.state());self.assertNotIn('resolution',v);self.assertEqual(v['phase'],'active')
        for a in 'BCD':self.cmd(a,'submit',text='同意结束。')
        self.assertEqual(self.state()['phase'],'ended');self.assertIn('resolution',self.app.view(self.owners['B'],self.state()))

    def test_all_families_have_multiple_routes_and_no_perfect_alibi(self):
        self.create();preview=self.state()['preview'];families=set()
        for seed in range(6):
            case=build(story_fixture(),preview,'murder',seed,['A']);families.add(case['family'])
            self.assertEqual(len(case['proofs']['identity']),2)
            self.assertNotIn('全程不在场',canonical(case));self.assertNotIn('始终在',canonical(case))
            for actor in 'ABCD':self.assertEqual('crime' in case['roles'][actor]['knows'],actor==case['solution']['killer'])
        self.assertEqual(len(families),3)

    def test_background_failure_is_visible_and_retry_reuses_completed_stages(self):
        self.create(humans=1);self.provider.fail='ensemble_dm';self.app.pump(self.gid,force=True)
        self.assertIsNotNone(self.state()['background_error']);count=sum(t=='ensemble_role' for t,_,_ in self.provider.calls)
        self.provider.fail=None;self.app.retry_background(self.owners['A'],self.gid)
        self.assertEqual(sum(t=='ensemble_role' for t,_,_ in self.provider.calls),count)
        self.assertIsNone(self.state()['background_error'])

    def test_paused_background_resumes_same_operation(self):
        self.create(humans=1);self.provider.block='ensemble_role'
        with ThreadPoolExecutor(1) as pool:
            pending=pool.submit(self.app.pump,self.gid,True);self.assertTrue(self.provider.entered.wait(2))
            self.cmd('A','pause');self.provider.release.set();pending.result(3)
        self.assertEqual(self.state()['phase'],'paused');count=sum(t=='ensemble_role' for t,_,_ in self.provider.calls)
        self.cmd('A','resume');self.provider.block=None;self.app.pump(self.gid,force=True)
        self.assertEqual(sum(t=='ensemble_role' for t,_,_ in self.provider.calls),count)

    def test_new_game_does_not_archive_other_players_active_room(self):
        self.create(humans=2);gid=self.gid
        self.app.create_game(self.owners['B'],{'command_id':'other_game_0001','expected_game_id':gid,'category':'family','humans':1})
        self.assertFalse(self.state()['archived'])

    def test_duplicate_command_and_foreign_identity_cannot_replay_peer_action(self):
        self.create();s=self.state();cmd={'command_id':'shared_command_0001','expected_revision':s['revision'],'kind':'act','choice':'move:r2'}
        result,_=self.app.command(self.owners['A'],self.gid,cmd);count=len(result['events'])
        again,receipt=self.app.command(self.owners['A'],self.gid,cmd);self.assertTrue(receipt['duplicate']);self.assertEqual(len(again['events']),count)
        with self.assertRaises(StoreError):self.app.command(self.owners['B'],self.gid,cmd)

    def test_compaction_covers_every_unprocessed_observation_and_keeps_scope(self):
        self.create()
        def add(s):
            for i in range(70):
                e=w.emit(s,'fixture');w.note(s,'A',e,'A 自己看到的事件 '+str(i))
                w.note(s,'B',e,'B_ONLY_LATE_CANARY')
        self.change(add);before=self.state();prefix=w.baseline(before,'A')
        self.cmd('A','thought',text='整理目前看到的事件。')
        calls=[d for task,_,d in self.provider.calls if task=='ensemble_memory']
        supplied=[o['id'] for d in calls for o in d['observations']]
        self.assertEqual(supplied,[o['id'] for o in before['observations']['A']])
        self.assertNotIn('B_ONLY_LATE_CANARY',canonical(calls))
        self.assertEqual(w.baseline(self.state(),'A'),prefix)
        self.assertEqual(self.state()['observations'],before['observations'])
        self.assertEqual(self.state()['memory']['A']['checkpoint'],71)

    def test_initial_secret_and_acquired_alias_disclosures_count_for_goals(self):
        s=self.create();start=len(s['events']);e=w.speak(s,'B',s['case']['roles']['B']['secret'])
        def call(stage,task,baseline,data,validator,*args):
            out={'assessments':[],'cues':[],'disclosures':[{'event_id':e['id'],'evidence_id':'secret_B'}],'event_decisions':[]};validator(out);return out,'fixture'
        self.app.adjudicate_ensemble(s,start,call)
        self.assertIn('sB',{d['evidence_id'] for d in s['disclosures']})
        w.contribute(s,'A','active')
        self.assertFalse(w.results(s,{})['participants']['A']['personal'])
        start=len(s['events']);record=w.emit(s,'inspect','D');w.acquire(s,'D','copy_B',record,'fixture')
        e=w.speak(s,'D',s['known']['D']['copy_B']['observation'])
        def alias(stage,task,baseline,data,validator,*args):
            out={'assessments':[],'cues':[],'disclosures':[{'event_id':e['id'],'evidence_id':'copy_B'}],'event_decisions':[]};validator(out);return out,'fixture'
        self.app.adjudicate_ensemble(s,start,alias)
        self.assertTrue(w.results(s,{})['participants']['D']['personal'])

    def test_unexpected_background_error_stops_automatic_retry(self):
        from unittest.mock import patch
        self.create(humans=1)
        with patch.object(self.app,'background',side_effect=ValueError('internal')),patch('traceback.print_exc'):
            self.assertTrue(self.app.pump(self.gid,force=True))
            self.assertFalse(self.app.pump(self.gid,force=True))
        self.assertIsNotNone(self.state()['background_error'])

    def test_legacy_investigation_recovers_creation_and_closes_under_new_app(self):
        from palter.investigation import InvestigationApplication
        from tests.test_investigation import CaseProvider
        client=DeepSeek(Settings(api_key='fixture'),CaseProvider());path=Path(self.directory.name)/'legacy-case.sqlite3'
        legacy=InvestigationApplication(path,client);owner=legacy.store.session()['id']
        creation={'command_id':'legacy_create_001','expected_game_id':None,'category':'mystery'}
        s=legacy.create_game(owner,creation)
        s,_=legacy.command(owner,s['id'],{'command_id':'legacy_confirm_001','expected_revision':s['revision'],'kind':'confirm'})
        fixed=s['case_hash'];upgraded=EnsembleApplication(path,client)
        self.assertEqual(upgraded.create_game(owner,creation),s)
        self.assertEqual(upgraded.view(owner,s)['gameplay'],'investigation')
        for kind in ('ready','close_case'):
            s,r=upgraded.command(owner,s['id'],{'command_id':'legacy_'+kind+'_001','expected_revision':s['revision'],'kind':kind})
            self.assertTrue(r['accepted'])
        self.assertEqual(s['phase'],'ended');self.assertEqual(s['case_hash'],fixed)

    def test_legacy_item_game_recovers_original_category_and_commands(self):
        from palter.ai_runtime import AIApplication
        from tests.test_ai import ProviderDouble
        client=DeepSeek(Settings(api_key='fixture'),ProviderDouble());path=Path(self.directory.name)/'legacy-item.sqlite3'
        legacy=AIApplication(path,client);owner=legacy.store.session()['id']
        creation={'command_id':'legacy_create_001','expected_game_id':None,'category':'drama'}
        s=legacy.create_game(owner,creation);upgraded=EnsembleApplication(path,client)
        self.assertEqual(upgraded.create_game(owner,creation),s)
        for kind in ('confirm','ready'):
            s,r=upgraded.command(owner,s['id'],{'command_id':'legacy_'+kind+'_001','expected_revision':s['revision'],'kind':kind})
            self.assertTrue(r['accepted'])
        self.assertEqual(s['phase'],'active');self.assertNotEqual(s.get('gameplay'),'ensemble')
        self.assertNotIn('B_PRIVATE_CANARY',canonical(upgraded.view(owner,s)))


if __name__=='__main__':unittest.main()
