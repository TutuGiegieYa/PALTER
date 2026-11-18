"""Cache layout changes key order, never knowledge, history or call settings."""
from copy import deepcopy
import json
import unittest

from palter import context_economy, compact_context, ensemble_world as w
from palter.ai_gateway import request_sizes
from palter.storage import canonical
from tests import test_ensemble_review as fixture

OLD='ai-tasks-v117.json'
NEW='ai-tasks-v118.json'


class CacheOrderTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.app=self.f.app;self.state=self.f.state

    def capture(self,dm=False):
        state=deepcopy(self.state);start=len(state['events'])
        w.speak(state,'A','我只记录自己实际收到的信息。')
        captured=[]
        class Captured(Exception):pass
        def call(stage,task,baseline,data,validate,actor=None):
            captured.append((task,deepcopy(baseline),deepcopy(data)));raise Captured()
        call.prefix_version=NEW
        with self.assertRaises(Captured):
            if dm:self.app.adjudicate_ensemble(state,start,call)
            else:self.app.turn(state,'A',call,0)
        return captured[0]

    def compare(self,task,baseline,data):
        before=canonical(data)
        old,old_hash=self.app.gateway.payload(task,baseline,data,OLD)
        new,new_hash=self.app.gateway.payload(task,baseline,data,NEW)
        self.assertEqual(old_hash,new_hash)
        self.assertEqual(old['messages'][:2],new['messages'][:2])
        self.assertEqual(old['messages'][3:],new['messages'][3:])
        a=json.loads(old['messages'][2]['content']);b=json.loads(new['messages'][2]['content'])
        self.assertEqual(a,b)
        self.assertEqual(request_sizes(old,2),request_sizes(new,2))
        self.assertEqual({k:v for k,v in old.items() if k!='messages'},
                         {k:v for k,v in new.items() if k!='messages'})
        self.assertEqual(canonical(data),before)
        return a,b

    def test_role_layout_preserves_body_selection_and_trailing_focus(self):
        a,b=self.compare(*self.capture())
        keys=list(b)
        for key in ('actor','rooms','objectives','source_access','active_guidance'):
            self.assertLess(keys.index(key),keys.index('sources'))
        self.assertEqual(keys[-1],'dialogue_focus')
        self.assertGreater(list(a).index('rooms'),list(a).index('sources'))

    def test_dm_layout_keeps_utterance_and_recipient_histories_identical(self):
        a,b=self.compare(*self.capture(dm=True))
        self.assertEqual(a['utterances'],b['utterances'])
        self.assertLess(list(b).index('active_guidance'),list(b).index('sources'))

    def test_memory_layout_does_not_enable_unrelated_economy_features(self):
        _,baseline,data=self.capture()
        a,b=self.compare('ensemble_memory',baseline,data)
        self.assertEqual(set(a),set(b))
        self.assertLess(list(b).index('actor'),list(b).index('sources'))
        self.assertNotIn('context_economy',self.app.gateway.versions[NEW]['ensemble_memory'])

    def test_native_tool_messages_and_retry_feedback_survive_reordering(self):
        task,baseline,data=self.capture()
        data['validation_feedback']={'code':'fixture','instruction':'Correct the specified field.'}
        data['_tool_messages']=[{'role':'assistant','content':None,'tool_calls':[
            {'id':'lookup-fixture','type':'function','function':{'name':'list_sources','arguments':'{}'}}]},
            {'role':'tool','tool_call_id':'lookup-fixture','content':'{"sources":[]}'}]
        _,new=self.compare(task,baseline,data)
        self.assertGreater(list(new).index('validation_feedback'),list(new).index('observations'))

    def test_current_speech_is_not_sorted_ahead_of_initial_fact_bodies(self):
        data={'context_format':1,'sources':{
            'e1:speech':{'text':'New utterance'},'secret_A':{'text':'Authorized initial fact'},
            'c1':{'observation':'Acquired original'},'A-o1':{'kind':'testimony','text':'Earlier utterance'}},
            'utterances':[{'facts':{'text_ref':'e1:speech'}}],
            'private_history':[],'observations':[{'id':'z2'},{'id':'z1'}]}
        before=deepcopy(data);out=context_economy.cache_order(data)
        self.assertEqual(out,data);self.assertEqual(data,before)
        self.assertEqual(list(out['sources'])[:2],['c1','secret_A'])
        self.assertEqual(out['observations'],[{'id':'z2'},{'id':'z1'}])
        self.assertEqual(len(compact_context.dumps(out).encode()),len(compact_context.dumps(data).encode()))
        self.assertEqual(compact_context.dumps(out),compact_context.dumps(context_economy.cache_order(out)))

    def test_unknown_fields_and_guidance_remain_present(self):
        data={'sources':{},'future_field':{'value':7},'active_guidance':{
            'future_guidance':'retained','event_judgment':'events','speech_judgment':'speech'},
            'dialogue_focus':{'reply_as':'A'},'validation_feedback':{'code':'pending'}}
        out=context_economy.cache_order(data)
        self.assertEqual(out,data)
        self.assertEqual(list(out['active_guidance']),['speech_judgment','event_judgment','future_guidance'])
        self.assertEqual(list(out)[-1],'dialogue_focus')

    def test_published_change_only_opts_three_tasks_into_ordering(self):
        old=self.app.gateway.versions[OLD];new=deepcopy(self.app.gateway.versions[NEW])
        for task in ('ensemble_role','ensemble_dm','ensemble_memory'):
            self.assertEqual(new[task].pop('context_order_version'),2)
        self.assertEqual(old,new)


if __name__=='__main__':unittest.main()
