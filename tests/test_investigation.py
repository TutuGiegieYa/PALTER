from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import unittest

from palter.investigation import InvestigationApplication
from palter.deepseek import DeepSeek,Settings
from palter import case_world as w
from palter.case_authoring import frame,compile_case,candidate_casts
from palter.storage import StoreError,canonical


def case_fixture():
    history=[
        ("20:00","死者在实时通话中仍然活着。"),("20:05","B 在办公室实施了杀人行为。SECRET_SOLUTION_CANARY"),
        ("20:04","B 的声音来自预先录制的广播，并非现场说话。"),("20:12","C 在死者已死后进入办公室，拿走了自己的欠条。"),
        ("20:00–20:10","D 一直出现在外部实时会议画面中。"),("20:04","A 在走廊亲眼看到 B 进入办公室。"),
        ("此前","B 篡改了项目账目，死者准备揭露此事。"),("20:00–20:12","办公室只有走廊一个入口，没有其他进入者。")]
    roles={c:{"name":{"A":"周岚","B":"陆平","C":"陈墨","D":"许青"}[c],"persona":"档案馆项目参与者。","goal":"查清案件并守住自己的秘密。", "location":"r1",
              "memories":[f"{c}_PRIVATE_CANARY"],"knows":{"A":["h6"],"B":["h2","h3","h7"],"C":["h4"],"D":["h5"]}[c],"cover_story":"我愿意谈自己亲眼见过的事。",
              "relationships":{o:"工作伙伴" for o in 'ABCD' if o!=c}} for c in 'ABCD'}
    observations=["20:00 的实时通话仍能听到死者回答问题。","20:10 的现场记录确认死者已遇害。","播放器记录显示 20:04 自动播放了陆平的讲话。","走廊记录显示陆平 20:04 进入办公室。","许青在 20:00 到 20:10 的实时会议中不断回答问题。","陈墨的进入记录是 20:12，此后欠条不见了。","原始账本和陆平签署的报表数额不一致。","办公室只有一个入口；进入记录覆盖整个时间段。"]
    clues=[{"id":f"c{i}","location":f"r{(i-1)%3+1}","title":f"记录 {i}","target":f"材料柜 {i}","observation":observation,"source":"馆内原始记录","time":f"20:{i:02d}","facts":[f"h{i}"]} for i,observation in enumerate(observations,1)]
    for clue,kind in zip(clues,('last_alive','first_dead','mechanism','presence','exclusion','exclusion','motive','context')):
        clue['kind']=kind;clue['minute']=1200 if kind=='last_alive' else 1210 if kind=='first_dead' else None
    clues[2]['source']='SECRET_ORIGIN_CANARY: the killer hid this recording.'
    return {"title":"散场后的记录","public_briefing":"项目负责人死在办公室，四位参与者需要还原当晚发生的事。","victim":"馆长",
            "rooms":{r:{"name":name,"description":"有可供检查的原始资料。"} for r,name in zip(('r1','r2','r3'),('放映厅','机房','办公室'))},"roles":roles,
            "history":[{"id":f"h{i}","time":t,"text":s,"minute":1205 if i==2 else None} for i,(t,s) in enumerate(history,1)],"clues":clues,
            "solution":{"killer":"B","crime_fact":"h2","window":[1200,1210],"time":"20:00 到 20:10","method":"在办公室当面作案，以录音伪装不在场。","motive":"掩盖篡改账目的事。","reconstruction":"陆平进入办公室作案，录音制造了假象，陈墨在死者死后拿走欠条。"},
            "proofs":{"identity":[["c4","c5","c6","c8"],["c1","c2","c4","c5","c6"]],"time":[["c1","c2"]],"method":[["c3","c4"]]}}


class CaseProvider:
    def __init__(self):
        self.calls=[];self.fail=None;self.block=None;self.entered=threading.Event();self.release=threading.Event()
        self.choice=lambda data:'accept:'+data['invitations'][0]['id'] if data['invitations'] else 'wait'
    def __call__(self,payload):
        task=payload['messages'][0]['content'].split('PALTER_TASK: ')[1].split('\n')[0]
        data=json.loads(payload['messages'][-1]['content']);self.calls.append((task,deepcopy(payload),data))
        if self.fail==task:raise TimeoutError()
        if self.block==task:self.entered.set();self.release.wait(5)
        if task=='case_introduction':out={'candidates':[{'title':f'独立案件{i}','introduction':f'案情{i}等待调查。','cast':{c:r['name'] for c,r in case_fixture()['roles'].items()},'victim':'馆长'} for i in range(3)]}
        elif task=='case_setup':out=case_fixture()
        elif task=='case_character':out={'choice':self.choice(data),'speech':'我记得当时的情况，还需要核对记录。','memory':'我记得自己听到的发言。','memory_sources':[o['id'] for o in data['observations'][-1:]],'trust_delta':0.1,'suspect':'B' if data['evidence'] else None,'evidence_ids':[c['id'] for c in data['evidence']],'question_to':None}
        elif task=='case_dm':out={'assessments':[],'cues':[]}
        elif task=='case_memory':out={'summary':'我把自己的想法留在心里。'}
        elif task=='case_action':out={'choice':'wait','clarification':''}
        elif task=='case_theory':out={'claims':[{'aspect':a,'quote':data['explanation'],'supported':True,'evidence_ids':[c['id'] for c in data['cited_evidence']]} for a in w.ASPECTS]}
        elif task=='case_ending':out={'title':'调查结束','narrative':'根据固定事实和本次提交的证据进行复盘。'}
        else:raise AssertionError(task)
        return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps(out,ensure_ascii=False)}}], 'usage':{'prompt_tokens':100,'completion_tokens':30,'prompt_cache_hit_tokens':40,'prompt_cache_miss_tokens':60}}


class InvestigationTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.provider=CaseProvider();self.path=Path(self.directory.name)/'game.sqlite3'
        self.client=DeepSeek(Settings(api_key='test-key'),self.provider)
        self.app=InvestigationApplication(self.path,self.client);self.owner=self.app.store.session()['id']
        self.state=self.app.create_game(self.owner,{'command_id':'new_case_0001','expected_game_id':None,'category':'mystery'})
        self.n=0
    def command(self,kind,**data):
        self.n+=1;command={'command_id':f'case_operation_{self.n:04d}','expected_revision':self.state['revision'],'kind':kind,**data}
        self.state,receipt=self.app.command(self.owner,self.state['id'],command)
        return command,receipt
    def start(self):self.command('confirm');self.command('ready')
    def collect(self):
        for room in ('r1','r2','r3'):
            if self.state['locations']['A']!=room:self.command('act',choice='move:'+room)
            for clue in self.state['case']['clues']:
                if clue['location']==room:self.command('act',choice='inspect:'+clue['id'])

    def test_setup_locked_before_play_and_no_hidden_answer_in_view(self):
        self.assertEqual([c[0] for c in self.provider.calls],['case_introduction'])
        self.command('confirm');self.assertEqual(self.state['phase'],'reading')
        raw=canonical(self.app.view(self.owner,self.state))
        self.assertIn(self.state['case']['history'][5]['text'],raw)
        for secret in ('SECRET_SOLUTION_CANARY','B_PRIVATE_CANARY','C_PRIVATE_CANARY','D_PRIVATE_CANARY','proofs','solution','case_hash'):self.assertNotIn(secret,raw)
        before=deepcopy(self.state)
        for _ in range(3):self.app.view(self.owner,self.state)
        self.assertEqual(self.state,before)
        damaged=deepcopy(self.state);damaged['case']['solution']['killer']='C'
        with self.assertRaisesRegex(RuntimeError,'case'):
            with self.app.store.transaction() as con:self.app.store.save(con,damaged,before)

    def test_preview_rosters_are_stable_and_keep_victim_separate(self):
        self.assertNotIn('candidate_rosters',self.provider.calls[0][2])
        self.assertEqual(self.state['preview']['cast'],{a:r['name'] for a,r in case_fixture()['roles'].items()})
        self.command('confirm')
        self.assertEqual({a:r['name'] for a,r in self.state['case']['roles'].items()},self.state['preview']['cast'])
        # Legacy pinned operations still reconstruct their original roster.
        self.assertEqual(candidate_casts(19),candidate_casts(19))
        self.assertNotEqual(candidate_casts(19),candidate_casts(20))
        for roster in candidate_casts(19):
            self.assertEqual(set(roster['cast']),set(w.ACTORS))
            self.assertEqual(len(set([*roster['cast'].values(),roster['victim']])),5)

    def test_invalid_time_proofs_or_ignorant_killer_block_initialization(self):
        for mutate in (lambda c:c['proofs'].update(time=[['c3','c4']]),
                       lambda c:c['roles']['B'].update(knows=['h1']),
                       lambda c:c['roles']['A'].update(knows=['h2']),
                       lambda c:c['solution'].update(window=[1100,1200])):
            case=case_fixture();mutate(case)
            with self.assertRaises(ValueError):w.validate_case(case)

    def test_case_generation_routes_and_accounts_for_actual_model(self):
        self.command('confirm')
        setup=next(c for c in self.app.gateway.trace(self.owner,self.state['id'])['calls'] if c['task']=='case_setup')
        self.assertEqual(setup['model'],'deepseek-flash')
        self.assertAlmostEqual(setup['cost_upper_usd'],(40*.006+60*.30+30*1.20)/1e6)
        for task in self.app.gateway.versions[self.app.gateway.current_version]:
            with self.subTest(task=task):
                payload,_=self.app.gateway.payload(task,None,{})
                self.assertEqual(payload['model'],'deepseek-flash')

    def test_pinned_older_setup_keeps_its_model_and_accounting(self):
        self.app.gateway.current_version='ai-tasks-v22.json'
        self.command('confirm')
        setup=next(c for c in self.app.gateway.trace(self.owner,self.state['id'])['calls'] if c['task']=='case_setup')
        self.assertEqual(setup['model'],'deepseek-v4-pro')
        self.assertAlmostEqual(setup['cost_upper_usd'],(40*.044+60*1.32+30*3.96)/1e6)

    def test_initial_memory_sources_allowed_but_other_roles_secrets_rejected(self):
        self.start();original=self.client.transport
        foreign=[False]
        def transport(payload):
            response=original(payload)
            if 'PALTER_TASK: case_character\n' in payload['messages'][0]['content']:
                out=json.loads(response['choices'][0]['message']['content'])
                out['memory_sources']=['h4' if foreign[0] else 'h2']
                response['choices'][0]['message']['content']=json.dumps(out)
            return response
        self.client.transport=transport
        self.command('say',target='B',text='你记得自己经历的事吗？')
        foreign[0]=True;before=deepcopy(self.state)
        with self.assertRaises(StoreError):self.command('say',target='B',text='还有什么？')
        self.assertEqual(self.app.store.state(self.owner,self.state['id']),before)

    def test_npc_can_suspect_human_without_changing_truth(self):
        self.start();original=self.client.transport
        def transport(payload):
            response=original(payload)
            if 'PALTER_TASK: case_character\n' in payload['messages'][0]['content']:
                out=json.loads(response['choices'][0]['message']['content']);out['suspect']='A'
                response['choices'][0]['message']['content']=json.dumps(out)
            return response
        self.client.transport=transport
        self.command('say',target='B',text='你怀疑谁？')
        self.assertEqual(self.state['beliefs']['B']['suspect'],'A')
        self.assertEqual(self.state['case']['solution']['killer'],'B')

    def test_inspections_and_notebook_are_local_and_no_fixed_act_end(self):
        self.start();count=len(self.provider.calls);fixed=deepcopy(self.state['case'])
        self.collect()
        for _ in range(12):
            room='r1' if self.state['locations']['A']!='r1' else 'r2'
            self.command('act',choice='move:'+room)
        self.command('notebook',text='我怀疑声音并不能证明人在场。',evidence_ids=['c1','c3'])
        self.assertEqual(self.state['phase'],'active');self.assertGreater(self.state['beat'],6)
        self.assertEqual(len(self.provider.calls),count);self.assertEqual(self.state['case'],fixed)
        self.assertNotIn('SECRET_ORIGIN_CANARY',canonical(self.app.view(self.owner,self.state)))
        self.assertEqual(self.state['notebook']['evidence_ids'],['c1','c3'])

    def test_hidden_and_remote_evidence_cannot_be_inspected_or_cited(self):
        self.start();before=deepcopy(self.state)
        with self.assertRaises(StoreError):self.command('act',choice='inspect:c2')
        with self.assertRaises(StoreError):self.command('present',target='B',evidence_ids=['c2'])
        self.assertEqual(self.app.store.state(self.owner,self.state['id']),before)

    def test_targeted_response_and_role_action_are_scoped_and_effective(self):
        self.start();self.provider.choice=lambda data:'inspect:c1'
        self.command('say',target='B',text='你能看看身边有什么线索吗？')
        roles=[c for c in self.provider.calls if c[0]=='case_character']
        self.assertEqual(len(roles),1);self.assertEqual(roles[0][2]['actor'],'B')
        self.assertIn('c1',self.state['known']['B']);self.assertNotIn('c1',self.state['known']['A'])
        for secret in ('A_PRIVATE_CANARY','C_PRIVATE_CANARY','D_PRIVATE_CANARY'):self.assertNotIn(secret,canonical(roles[0][1]))
        self.provider.choice=lambda data:'share:c1'
        self.command('say',target='B',text='请把你找到的材料给我们看看。')
        self.assertIn('c1',self.state['known']['A'])
        self.assertTrue(any(e['facts'].get('decision_call_id') for e in self.state['events']))

    def test_private_consent_and_evidence_isolation(self):
        self.start();self.command('act',choice='inspect:c1')
        self.command('act',choice='invite:B');chat=w.chat_for(self.state,'A');self.assertIsNotNone(chat)
        self.command('present',target='B',text='PRIVATE_WORDS_CANARY',evidence_ids=['c1'],channel=chat['id'])
        self.assertIn('c1',self.state['known']['B']);self.assertNotIn('c1',self.state['known']['C'])
        self.assertNotIn('PRIVATE_WORDS_CANARY',canonical(self.state['observations']['C']))
        for task,payload,data in self.provider.calls:
            if task=='case_character' and data['actor']=='B':self.assertNotIn('C_PRIVATE_CANARY',canonical(payload))
        self.command('act',choice='end_private',channel=chat['id'])
        with self.assertRaises(StoreError):self.command('say',text='stale private words',channel=chat['id'])

    def test_proof_based_ending_and_idempotent_final_submission(self):
        self.start();self.collect()
        command,receipt=self.command('accuse',suspect='B',text='综合时间记录、进入记录与录音，可以还原陆平当面作案并伪装不在场。',evidence_ids=list(self.state['known']['A']))
        self.assertTrue(receipt['accepted']);self.assertEqual(self.state['outcome'],'established')
        count=len(self.provider.calls);state,receipt=self.app.command(self.owner,self.state['id'],command)
        self.assertTrue(receipt['duplicate']);self.assertEqual(state,self.state);self.assertEqual(len(self.provider.calls),count)
        view=self.app.view(self.owner,state);self.assertEqual(view['resolution']['killer'],'陆平')
        self.assertEqual(set(view['resolution']['evaluation']['established']),set(w.ASPECTS))

    def test_outside_activity_is_not_backfilled_after_private_chat(self):
        self.start();self.command('act',choice='invite:B')
        chat=w.chat_for(self.state,'A')
        self.provider.choice=lambda data:'inspect:c1' if data['actor'] in 'CD' else 'wait'
        self.command('say',target='B',text='PRIVATE_ONLY',channel=chat['id'])
        outsiders=[c for c in self.provider.calls if c[0]=='case_character' and c[2]['actor'] in 'CD']
        self.assertEqual(len(outsiders),1)
        actor=outsiders[0][2]['actor']
        self.assertNotIn('PRIVATE_ONLY',canonical(outsiders[0][1]))
        self.assertIn('c1',self.state['known'][actor]);self.assertNotIn('c1',self.state['known']['A'])
        self.provider.choice=lambda data:'wait'
        self.command('act',choice='end_private',channel=chat['id'])
        self.assertNotIn('c1',self.state['known']['A'])
        self.assertFalse(any(o.get('evidence_id')=='c1' for o in self.state['observations']['A']))

    def test_authoring_contract_derives_consistent_times_knowledge_and_proofs(self):
        source=case_fixture()
        for seed in range(3):
            contract=frame(f'{seed:012x}')
            authored={k:deepcopy(source[k]) for k in ('title','public_briefing','victim','rooms','roles')}
            authored.update(crime='PRIVATE_CRIME',**{k:source['solution'][k] for k in ('method','motive','reconstruction')})
            authored['records']={key:{'actual_history':key,'time':'案发前后','location':'r1','title':key,'target':key,'observation':key} for key in contract['records']}
            case=compile_case(authored,contract)
            killer=contract['killer']
            self.assertIn('h_crime',case['roles'][killer]['knows'])
            for actor in w.ACTORS:
                if actor!=killer:self.assertNotIn('PRIVATE_CRIME',canonical(case['roles'][actor]))
            self.assertEqual(case['solution']['window'],[case['clues'][0]['minute'],case['clues'][1]['minute']])
            self.assertEqual(len(case['proofs']['identity'][0]),4)
            changed=deepcopy(case);changed['clues'][1]['minute']+=1
            with self.assertRaises(ValueError):w.validate_case(changed)

    def test_bounded_case_preserves_cast_and_physical_proof_for_each_culprit(self):
        source=case_fixture();cast={a:r['name'] for a,r in source['roles'].items()}
        for seed in range(6):
            contract=frame(f'{seed:012x}',cast,source['victim'])
            authored={k:deepcopy(source[k]) for k in ('title','public_briefing','victim','rooms','roles')}
            authored.update(format='bounded-v1',conflict={'truth':'债务纠纷。','title':'借据','target':'桌面借据','observation':'尚未偿还的借据。'},innocent_secret={'truth':'私下出售自己的旧书。','title':'收据','target':'信封','observation':'旧书买卖收据。'})
            for actor,profile in authored['roles'].items():profile['relationships']=['旧相识']*3
            original=deepcopy(authored);case=compile_case(authored,contract)
            self.assertEqual(authored,original)
            self.assertEqual(len(case['clues']),9)
            self.assertIn(cast[contract['killer']],case['clues'][2]['observation'])
            self.assertIn(['c3','c8'],case['proofs']['identity'])
            self.assertIn('h_dead',case['roles']['A']['knows'])
            self.assertIn('发现者进门前',case['clues'][7]['observation'])
            for actor in w.ACTORS:
                self.assertEqual(set(case['roles'][actor]['relationships']),set(w.ACTORS)-{actor})
                self.assertNotIn('h_access',case['roles'][actor]['knows'])
                self.assertNotIn('h_presence',case['roles'][actor]['knows'])
            state=w.blank('test');w.initialize(state,case)
            self.assertNotIn(case['history'][8]['text'],canonical(w.view(state)))

    def test_correct_guess_is_not_established(self):
        self.start();self.command('accuse',suspect='B',text='我觉得就是他。',evidence_ids=[])
        self.assertEqual(self.state['outcome'],'unproven')

    def test_supported_argument_can_span_multiple_quoted_claims(self):
        self.start();self.collect();original=self.client.transport
        def transport(payload):
            response=original(payload)
            if 'PALTER_TASK: case_theory\n' in payload['messages'][0]['content']:
                claims=[]
                for aspect in w.ASPECTS:
                    route=self.state['case']['proofs'][aspect][0];middle=len(route)//2
                    for ids in (route[:middle],route[middle:]):
                        claims.append({'aspect':aspect,'quote':'我依据这些证据逐步推断','supported':True,'evidence_ids':ids})
                response['choices'][0]['message']['content']=json.dumps({'claims':claims})
            return response
        self.client.transport=transport
        self.command('accuse',suspect='B',text='我依据这些证据逐步推断。',evidence_ids=list(self.state['known']['A']))
        self.assertEqual(self.state['outcome'],'established')

    def test_rejected_reasoning_cannot_pass_by_selecting_every_clue(self):
        self.start();self.collect();original=self.client.transport
        def transport(payload):
            response=original(payload)
            if 'PALTER_TASK: case_theory\n' in payload['messages'][0]['content']:
                out=json.loads(response['choices'][0]['message']['content'])
                for claim in out['claims']:claim['supported']=False
                response['choices'][0]['message']['content']=json.dumps(out)
            return response
        self.client.transport=transport
        self.command('accuse',suspect='B',text='我只是随便猜的。',evidence_ids=list(self.state['known']['A']))
        self.assertEqual(self.state['outcome'],'unproven')

    def test_wrong_accusation_cannot_override_truth_even_with_all_evidence(self):
        self.start();self.collect();fixed=deepcopy(self.state['case'])
        self.command('accuse',suspect='C',text='我认为陈墨实施了这起案件。',evidence_ids=list(self.state['known']['A']))
        self.assertEqual(self.state['outcome'],'incorrect');self.assertEqual(self.state['case'],fixed)

    def test_voluntary_unresolved_ending_is_not_a_timeout(self):
        self.start();self.command('close_case');self.assertEqual(self.state['outcome'],'unresolved')

    def test_pause_buffers_and_reuses_completed_character_stage(self):
        self.start();self.provider.block='case_character'
        cmd={'command_id':'paused_case_0001','expected_revision':self.state['revision'],'kind':'say','target':'B','text':'你当时在哪里？'}
        with ThreadPoolExecutor(1) as pool:
            future=pool.submit(self.app.command,self.owner,self.state['id'],cmd)
            self.assertTrue(self.provider.entered.wait(3));self.command('pause');self.provider.release.set()
            state,receipt=future.result(10)
        self.assertTrue(receipt['pending']);self.assertEqual(state['phase'],'paused')
        self.command('resume');self.state,receipt=self.app.command(self.owner,self.state['id'],cmd)
        self.assertTrue(receipt['accepted']);self.assertEqual(sum(c[0]=='case_character' for c in self.provider.calls),1)

    def test_model_failure_does_not_commit_partial_action_or_change_case(self):
        self.start();self.provider.fail='case_dm';before=deepcopy(self.state)
        with self.assertRaises(StoreError):self.command('say',target='B',text='请解释刚才的情况。')
        self.assertEqual(self.app.store.state(self.owner,self.state['id']),before)

    def test_restarting_restores_notebook_and_case_without_model_calls(self):
        self.start();self.collect();self.command('notebook',text='保留我的判断。',evidence_ids=['c1'])
        count=len(self.provider.calls);other=InvestigationApplication(self.path,self.client)
        self.assertEqual(other.store.state(self.owner,self.state['id']),self.state)
        self.assertEqual(len(self.provider.calls),count)


if __name__=='__main__':unittest.main()
