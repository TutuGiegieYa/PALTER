"""Own claims stay claims; bounded snapshots and pinned retries remain usable."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from palter import ensemble_world as w, ensemble_context, memory_entries
from tests import test_ensemble_review as context_fixture
from tests import test_spectator as recovery_fixture
from tests.compact_fixture import expand


class MemoryContractTests(unittest.TestCase):
    def setUp(self):
        f=context_fixture.ReviewFixTests();f.setUp();self.addCleanup(f.doCleanups)
        self.app=f.app;self.state=f.state
        w.speak(self.state,'A','我声称已经把材料封存了。')
        self.source=self.state['observations']['A'][-1]['id']

    def snapshot(self,length=645,kind='self_claim'):
        sizes=[length//3,length//3,length-2*(length//3)]
        return {'entries':[{'id':f'm{i}','kind':kind,'text':'述'*size,'sources':[self.source]}
                           for i,size in enumerate(sizes)],'processed_through':self.source}

    def caller(self,out,version='ai-tasks-v70.json'):
        def call(stage,task,baseline,data,validate,actor=None):
            validate(out);return deepcopy(out),'memory-contract-fixture'
        call.prefix_version=version
        return call

    def test_self_claim_preserves_text_and_sources_without_creating_evidence_or_actions(self):
        before=deepcopy(self.state)
        entry={'id':'m1','kind':'self_claim','text':'我声称已封存材料，这仍只是我的说法。','sources':[self.source]}
        self.app.summarize_chunk(self.state,'A',self.caller({'entries':[entry],'processed_through':self.source}),
                                 len(self.state['observations']['A']))
        self.assertEqual(self.state['memory']['A']['entries'],[entry])
        for key in ('events','observations','known','objects','case'):
            self.assertEqual(self.state[key],before[key],key)
        data=w.context(self.state,'A');ensemble_context.project(self.state,'A',data)
        own=next(o for o in data['observations'] if o['id']==self.source)
        self.assertEqual(own['provenance'],'self_claim')
        self.assertEqual(self.state['memory']['A']['checkpoint'],len(self.state['observations']['A']))

    def test_complete_recorded_size_and_upper_bound_work_for_old_and_new_prefixes(self):
        for version in ('ai-tasks-v69.json','ai-tasks-v70.json'):
            for length in (645,699):
                with self.subTest(version=version,length=length):
                    state=deepcopy(self.state)
                    self.app.summarize_chunk(state,'A',self.caller(self.snapshot(length),version),len(state['observations']['A']))
                    self.assertEqual(sum(len(r['text']) for r in state['memory']['A']['entries']),length)
                    self.assertFalse(self.app.compact(state,'A',self.caller(self.snapshot(length),version)))

    def test_snapshot_above_retired_character_limit_is_accepted(self):
        before=deepcopy(self.state)
        self.app.summarize_chunk(self.state,'A',self.caller(self.snapshot(1500)),len(self.state['observations']['A']))
        self.assertEqual(sum(len(r['text']) for r in self.state['memory']['A']['entries']),1500)
        for key in ('events','observations','known'):self.assertEqual(self.state[key],before[key])

    def test_unknown_kind_and_unacquired_sources_remain_invalid(self):
        for kind,sources in (('fact',[self.source]),('self_claim',['B-o999999']),('self_claim',['c9'])):
            out=self.snapshot(150,kind);out['entries'][0]['sources']=sources
            with self.subTest(kind=kind,sources=sources),self.assertRaises(ValueError):
                self.app.summarize_chunk(self.state,'A',self.caller(out),len(self.state['observations']['A']))

    def test_pressure_compaction_archives_prior_versions_without_idle_repeat(self):
        self.state['memory']['A']={'entries':[{'id':f'm{i}','kind':'unresolved','text':'疑'*85,'sources':[self.source]}
                                             for i in range(9)],
                                  'summary':'疑'*765,'sources':[self.source],
                                  'checkpoint':len(self.state['observations']['A'])}
        out=self.snapshot();out['processed_through']=None
        self.assertTrue(self.app.compact(self.state,'A',self.caller(out)))
        self.assertEqual(len(self.state['memory_archive']['A']),9)
        self.assertFalse(self.app.compact(self.state,'A',self.caller(out)))

    def test_new_prompt_and_budget_match_contract_while_old_prefix_is_immutable(self):
        old=self.app.gateway.versions['ai-tasks-v69.json']['ensemble_memory']
        new=self.app.gateway.versions['ai-tasks-v70.json']['ensemble_memory']
        self.assertEqual(old['tokens'],700);self.assertEqual(new['tokens'],1400)
        self.assertIn('600 Chinese text characters',old['instruction'])
        self.assertIn(str(memory_entries.COMPACT_MAX_TEXT)+' characters',new['instruction'])
        for kind in memory_entries.KINDS:
            self.assertIn(kind,new['instruction'])
            self.assertIn(kind,self.app.gateway.versions['ai-tasks-v70.json']['ensemble_role']['instruction'])
        self.assertEqual(self.app.gateway.versions['ai-tasks-v69.json']['ensemble_dm'],
                         self.app.gateway.versions['ai-tasks-v70.json']['ensemble_dm'])


class MemoryRecoveryTests(unittest.TestCase):
    def test_exhausted_old_operation_accepts_self_claim_on_explicit_retry(self):
        f=recovery_fixture.SpectatorTests();f.setUp();self.addCleanup(f.doCleanups)
        app=f.app;app.gateway.current_version='ai-tasks-v69.json';app.gateway.retry_delays=(0,0,0)
        f.create()
        def seed(s):
            s['watch'].update(budget_usd=2.0,call_limit=512)
            w.speak(s,'A','我声称已经完成检查。')
            source=s['observations']['A'][-1]['id']
            s['memory']['A']={'entries':[{'id':f'm{i}','kind':'unresolved','text':'疑'*85,'sources':[source]} for i in range(9)],
                              'summary':'疑'*765,'sources':[source],'checkpoint':len(s['observations']['A'])}
        f.change(seed)
        saved=f.state();source=saved['observations']['A'][-1]['id']
        original=app.gateway.client.transport;caps=[]
        def transport(payload):
            if 'PALTER_TASK: ensemble_memory\n' not in payload['messages'][0]['content']:return original(payload)
            caps.append(payload['max_tokens'])
            supplied=expand(json.loads(payload['messages'][-1]['content']))['observations']
            out={'entries':[{'id':f'm{i}','kind':'self_claim','text':'述'*215,'sources':[source]} for i in range(3)],
                 'processed_through':supplied[-1]['id'] if supplied else None}
            return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps(out,ensure_ascii=False)}}],
                    'usage':{'prompt_tokens':100,'completion_tokens':600,'prompt_cache_hit_tokens':40,'prompt_cache_miss_tokens':60}}
        app.gateway.client.transport=transport
        with patch.object(memory_entries,'KINDS',('observed','heard_claim','unresolved','interpretation')):
            f.cmd('watch_step');failed=f.pump()
        self.assertEqual(failed['background_error']['code'],'retry_exhausted')
        self.assertEqual(failed['memory']['A'],saved['memory']['A'])
        app.gateway.current_version='ai-tasks-v70.json'
        f.cmd('watch_step');recovered=f.pump()
        self.assertIsNone(recovered['background_error']);self.assertEqual(recovered['watch']['steps'],1)
        self.assertTrue(any(r['kind']=='self_claim' for r in recovered['memory']['A']['entries']))
        self.assertEqual(recovered['observations']['A'][:len(saved['observations']['A'])],saved['observations']['A'])
        with app.store.transaction(False) as con:
            op=con.execute('SELECT prefix_version FROM ai_operations WHERE game_id=? AND id=?',
                           (f.gid,failed['background_error']['operation_id'])).fetchone()
            calls=con.execute("SELECT status FROM ai_calls WHERE game_id=? AND task='ensemble_memory' ORDER BY started",(f.gid,)).fetchall()
        self.assertEqual(op['prefix_version'],'ai-tasks-v69.json')
        self.assertEqual([r['status'] for r in calls],['failed']*4+['completed'])
        self.assertEqual(caps,[700]*5)


if __name__=='__main__':unittest.main()
