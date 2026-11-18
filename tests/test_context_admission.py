"""Independent dynamic/full-envelope admission with safe manual recovery."""
import unittest
from copy import deepcopy
from palter import spectator
from palter.ai_gateway import retryable,manually_retryable,request_sizes,MAX_DYNAMIC_CONTEXT_BYTES
from palter.storage import StoreError,canonical
from tests import test_ensemble_review as fixtures


class ContextAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.gateway=self.f.app.gateway

    def test_large_fixed_prefix_does_not_take_dynamic_allowance(self):
        body,_=self.gateway.payload('ensemble_role',{'immutable':'x'*24000},{'context':'y'*28000},'ai-tasks-v78.json')
        self.assertGreater(len(canonical(body).encode()),60000)
        self.assertLess(len(canonical(body).encode()),90000)

    def test_mutable_history_and_tool_results_share_one_bound(self):
        for data in ({'context':'x'*MAX_DYNAMIC_CONTEXT_BYTES}, {'context':'x'*44000,'_tool_messages':[{'role':'tool','tool_call_id':'x','content':'y'*9000}]}):
            with self.assertRaises(StoreError) as error:self.gateway.payload('ensemble_role',{},data,'ai-tasks-v79.json')
            self.assertEqual(error.exception.code,'context_budget')

    def test_expanded_dynamic_allowance_includes_serialization_overhead(self):
        for version in ('ai-tasks-v79.json',self.gateway.current_version):
            with self.subTest(version=version):
                body,_=self.gateway.payload('ensemble_role',{}, {'context':''},version)
                overhead=request_sizes(body,2)['dynamic_bytes']
                data={'context':'x'*(51200-overhead)}
                body,_=self.gateway.payload('ensemble_role',{},data,version)
                self.assertEqual(request_sizes(body,2)['dynamic_bytes'],51200)
                data['context']+='x'
                with self.assertRaises(StoreError) as error:self.gateway.payload('ensemble_role',{},data,version)
                self.assertEqual(error.exception.code,'context_budget')
                self.assertIn('51.2 KB',str(error.exception));self.assertIn('90 KB',str(error.exception))

    def test_total_envelope_is_still_bounded(self):
        with self.assertRaises(StoreError):self.gateway.payload('ensemble_role',{'immutable':'x'*80000},{'context':'small'},'ai-tasks-v79.json')

    def test_admission_failure_can_be_manually_retried_but_never_auto_loops(self):
        self.assertFalse(retryable('context_budget'));self.assertTrue(manually_retryable('context_budget'))

    def test_spectator_can_explicitly_recover_preflight_failure_with_pinned_operation(self):
        app=self.f.app;app.gateway.current_version='ai-tasks-v78.json'
        owner=app.store.session()['id']
        state=app.store.create_game(owner,{'command_id':'admission_fixture','expected_game_id':None},
            lambda gid:dict(deepcopy(self.f.state),id=gid))
        with app.store.transaction() as con:con.execute('INSERT INTO game_members VALUES (?,?,?)',(state['id'],owner,'observer'))
        command={'command_id':'preflight_failed','expected_revision':state['revision'],'kind':'background','_actor':'system'}
        def oversized(s,call):self.gateway.payload('ensemble_role',{}, {'context':'x'*MAX_DYNAMIC_CONTEXT_BYTES},'ai-tasks-v78.json')
        with self.assertRaises(StoreError):app.operate(owner,state['id'],command,oversized)
        error={'code':'context_budget','message':'Synthetic preflight failure','operation_id':command['command_id'],'retryable':False}
        spectator.pause(app,owner,state['id'],'error',error)
        state=app.store.state(owner,state['id']);self.assertTrue(app.view(owner,state)['background_error']['retryable'])
        self.assertFalse(self.f.provider.calls)
        app.command(owner,state['id'],{'command_id':'manual_recover','expected_revision':state['revision'],'kind':'watch_step'})
        app.pump(state['id'],force=True);result=app.store.state(owner,state['id'])
        self.assertIsNone(result['background_error']);self.assertEqual(result['watch']['pause_reason'],'step')
        with app.store.transaction(False) as con:
            op=con.execute('SELECT status,prefix_version FROM ai_operations WHERE id=?',(command['command_id'],)).fetchone()
        self.assertEqual(op['status'],'completed');self.assertEqual(op['prefix_version'],'ai-tasks-v78.json')


if __name__=='__main__':unittest.main()
