"""Optional lookup pagination, authorization, and pinned-operation recovery."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from palter import compact_context,ensemble_world as w
from palter.storage import canonical
from tests import test_ensemble_review as context_fixture
from tests import test_spectator as recovery_fixture


class SourceLookupDefaultTests(unittest.TestCase):
    def setUp(self):
        fixture=context_fixture.ReviewFixTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.app=fixture.app;self.state=fixture.state

    def test_missing_offset_matches_explicit_zero_without_mutating_arguments(self):
        w.apply_choice(self.state,'A','inspect:c1')
        arguments={'requests':[{'id':'c1'},{'id':self.state['observations']['A'][0]['id']}]}
        before=deepcopy(arguments)
        implicit=compact_context.lookup(self.state,'A',arguments)
        explicit=compact_context.lookup(self.state,'A',{'requests':[dict(r,offset=0) for r in arguments['requests']]})
        self.assertEqual(implicit,explicit);self.assertEqual(arguments,before)
        self.assertEqual(implicit['sources'][0]['text'],self.state['known']['A']['c1']['observation'])
        self.assertEqual(implicit['sources'][0]['status'],'complete')

    def test_default_does_not_reveal_unacquired_or_unheard_sources(self):
        event=w.emit(self.state,'private_fixture');w.note(self.state,'B',event,'UNHEARD_PRIVATE_TEXT',speaker='B')
        ids=['c9',self.state['observations']['B'][-1]['id'],'unknown']
        out=compact_context.lookup(self.state,'A',{'requests':[{'id':identity} for identity in ids]})
        self.assertEqual(out['sources'],[{'id':identity,'status':'unavailable'} for identity in ids])
        self.assertNotIn('UNHEARD_PRIVATE_TEXT',canonical(out))

    def test_malformed_explicit_offsets_and_unknown_fields_still_fail(self):
        for request in ({'id':'c1','offset':None},{'id':'c1','offset':True},{'id':'c1','offset':-1},
                        {'id':'c1','offset':'0'},{'id':'c1','offset':0.5},{'id':'c1','actor':'B'},
                        {'offset':0},'c1'):
            with self.subTest(request=request),self.assertRaises(ValueError):
                compact_context.lookup(self.state,'A',{'requests':[request]})

    def test_new_schema_makes_offset_optional_and_old_prefix_stays_unchanged(self):
        def schema(version):
            tool=next(t['function'] for t in self.app.gateway.versions[version]['ensemble_role']['tools'] if t['function']['name']=='read_sources')
            return tool['parameters']['properties']['requests']['items']
        self.assertEqual(schema('ai-tasks-v68.json')['required'],['id','offset'])
        self.assertEqual(schema('ai-tasks-v69.json')['required'],['id'])
        self.assertEqual(schema('ai-tasks-v69.json')['properties']['offset']['default'],0)


class SourceLookupRecoveryTests(unittest.TestCase):
    def test_exhausted_v68_operation_recovers_with_unavailable_tool_receipt(self):
        f=recovery_fixture.SpectatorTests();f.setUp();self.addCleanup(f.doCleanups)
        app=f.app;app.gateway.current_version='ai-tasks-v68.json';app.gateway.retry_delays=(0,0,0)
        f.create();f.change(lambda s:s['watch'].update(budget_usd=2.0,call_limit=512))
        original=app.gateway.client.transport;receipts=[]
        def transport(payload):
            if 'PALTER_TASK: ensemble_role\n' not in payload['messages'][0]['content']:return original(payload)
            feedback=[m for m in payload['messages'] if m['role']=='tool']
            if not feedback:
                native={'id':'lookup_without_offset','type':'function','function':{'name':'read_sources','arguments':canonical({'requests':[{'id':'c9'}]})}}
                return {'choices':[{'finish_reason':'tool_calls','message':{'role':'assistant','content':'','tool_calls':[native]}}],
                        'usage':{'prompt_tokens':100,'completion_tokens':30,'prompt_cache_hit_tokens':40,'prompt_cache_miss_tokens':60}}
            receipts.append(json.loads(feedback[0]['content']));return original(payload)
        app.gateway.client.transport=transport
        with patch('palter.compact_context.lookup',side_effect=ValueError('source lookup request')):
            f.cmd('watch_step');failed=f.pump()
        self.assertEqual(failed['background_error']['code'],'retry_exhausted')
        before=deepcopy(failed['events']);app.gateway.current_version='ai-tasks-v69.json'
        f.cmd('watch_step');recovered=f.pump()
        self.assertIsNone(recovered['background_error']);self.assertEqual(recovered['watch']['steps'],1)
        self.assertEqual(receipts[0]['sources'],[{'id':'c9','status':'unavailable'}])
        self.assertNotIn('c9',recovered['known']['A']);self.assertGreater(len(recovered['events']),len(before))
        with app.store.transaction(False) as con:
            op=con.execute('SELECT prefix_version FROM ai_operations WHERE game_id=? AND id=?',(f.gid,failed['background_error']['operation_id'])).fetchone()
            calls=con.execute("SELECT status FROM ai_calls WHERE game_id=? AND task='ensemble_role' ORDER BY started",(f.gid,)).fetchall()
        self.assertEqual(op['prefix_version'],'ai-tasks-v68.json')
        self.assertEqual([r['status'] for r in calls],['failed']*4+['completed']*2)


if __name__=='__main__':unittest.main()
