"""Role-owned speech references, scoped lookup and versioned prompt continuity."""
from copy import deepcopy
import json
import unittest

from palter import ensemble_context as context, ensemble_world as w, source_access
from palter.model_contracts import CURRENT_PREFIX
from palter.storage import canonical
from tests import test_ensemble_review as fixture


class DialogueFocusTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.ReviewFixTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.app,self.s=self.f.app,self.f.state
        self.app.gateway.current_version=CURRENT_PREFIX
        self.app.configure_rules(self.s,self.f.caller(CURRENT_PREFIX));self.s['agenda']=[]

    def speak(self,actor,text):
        event=w.speak(self.s,actor,text)
        return next(o['id'] for o in self.s['observations'][actor] if o['event_id']==event['id'])

    def role_data(self,actor='A',version=CURRENT_PREFIX):
        state=deepcopy(self.s);self.app.turn(state,actor,self.f.caller(version),0)
        return next(data for task,data in reversed(self.f.inputs) if task=='ensemble_role')

    def test_two_actual_own_occurrences_in_order_without_text_deduplication(self):
        self.speak('A','较早的话。')
        first=self.speak('A','我确认收到。');self.speak('C','我也确认收到。')
        last=self.speak('A','我确认收到。');before=canonical(self.s)
        focus=context.dialogue_focus(self.s,'A')
        self.assertEqual(focus,{'version':1,'own_recent_speech':[{'id':first,'channel':'public'},{'id':last,'channel':'public'}]})
        self.assertEqual(canonical(self.s),before)
        self.assertEqual(context.dialogue_focus(self.s,'D')['own_recent_speech'],[])

    def test_private_channels_and_unheard_statements_do_not_cross_roles(self):
        self.s['locations'].update(A='r1',B='r1',C='r1',D='r1')
        w.apply_choice(self.s,'A','invite:B');w.apply_choice(self.s,'B','accept:i1')
        identity=self.speak('A','PRIVATE_OWN_UTTERANCE')
        focus=context.dialogue_focus(self.s,'A')
        self.assertEqual(focus['own_recent_speech'][-1]['id'],identity)
        self.assertNotEqual(focus['own_recent_speech'][-1]['channel'],'public')
        for actor in 'BCD':
            self.assertNotIn(identity,canonical(context.dialogue_focus(self.s,actor)))
        for actor in 'CD':self.assertEqual(context.dialogue_focus(self.s,actor)['own_recent_speech'],[])
        unavailable=source_access.lookup(self.s,'C',{'requests':[{'id':identity}]})
        self.assertNotIn('PRIVATE_OWN_UTTERANCE',canonical(unavailable))

    def test_current_wire_reuses_one_body_and_keeps_existing_speaker(self):
        own=self.speak('A','OWN_BODY_ONLY_ONCE_这是我自己的表态。')
        self.speak('C','OTHER_BODY_ONLY_ONCE_这是另一人的表态。')
        other=self.s['observations']['A'][-1]['id']
        before=canonical(self.s);data=self.role_data()
        body,_=self.app.gateway.payload('ensemble_role',w.baseline(self.s,'A'),data,CURRENT_PREFIX)
        wire=body['messages'][2]['content'];packed=json.loads(wire)
        self.assertEqual(packed['dialogue_focus']['own_recent_speech'],[{'id':own,'channel':'public'}])
        self.assertEqual(wire.count('OWN_BODY_ONLY_ONCE'),1)
        self.assertEqual(wire.count('OTHER_BODY_ONLY_ONCE'),1)
        self.assertNotIn(own,packed['sources']);self.assertNotIn(other,packed['sources'])
        self.assertEqual(packed['dialogue_focus']['sources'][own]['speaker'],'A')
        self.assertEqual(packed['dialogue_focus']['sources'][other]['speaker'],'C')
        self.assertEqual(canonical(self.s),before)

    def test_old_own_reference_remains_retrievable_without_readding_history(self):
        identity=self.speak('A','OLDER_OWN_BODY')
        for _ in range(30):w.note(self.s,'A',w.emit(self.s,'observed'),'现场的新记录。')
        self.s['memory']['A']['checkpoint']=len(self.s['observations']['A'])
        data=self.role_data()
        self.assertEqual(data['dialogue_focus']['own_recent_speech'][0]['id'],identity)
        self.assertNotIn(identity,{o['id'] for o in data['observations']})
        body,_=self.app.gateway.payload('ensemble_role',w.baseline(self.s,'A'),data,CURRENT_PREFIX)
        self.assertNotIn('OLDER_OWN_BODY',body['messages'][2]['content'])
        before=canonical(self.s)
        original=source_access.lookup(self.s,'A',{'requests':[{'id':identity}]})
        self.assertEqual(original['sources'][0]['text'],'OLDER_OWN_BODY')
        self.assertEqual(canonical(self.s),before)

    def test_old_prefix_does_not_receive_focus_and_output_schema_is_unchanged(self):
        self.speak('A','我此前说过的一句话。')
        self.assertNotIn('dialogue_focus',self.role_data(version='ai-tasks-v113.json'))
        old=self.app.gateway.versions['ai-tasks-v113.json']['ensemble_role']
        new=self.app.gateway.versions[CURRENT_PREFIX]['ensemble_role']
        for key in ('example','tokens','temperature','thinking','role_recovery_version'):
            self.assertEqual(new[key],old[key])
        tools=[deepcopy(spec['tools']) for spec in (old,new)]
        for definitions in tools:
            listener=next(t for t in definitions if t['function']['name']=='create_event_listener')
            # V125 renames the input projection referenced by this description;
            # the accepted tool arguments and all other tool fields stay exact.
            listener['function']['parameters']['properties']['event_ids'].pop('description')
        self.assertEqual(*tools)
        self.assertEqual(new['perspectives']['concealment']['example'],old['perspectives']['concealment']['example'])
        for spec in (new,*new['perspectives'].values()):
            self.assertIn('own_recent_speech',spec['instruction'])

    def test_focus_moves_only_supplied_bodies_and_preserves_prior_wire_pools(self):
        self.speak('A','OWN_SOURCE');self.speak('C','HEARD_SOURCE')
        old_data=self.role_data(version='ai-tasks-v116.json')
        old,_=self.app.gateway.payload('ensemble_role',w.baseline(self.s,'A'),old_data,'ai-tasks-v116.json')
        data=self.role_data()
        new,_=self.app.gateway.payload('ensemble_role',w.baseline(self.s,'A'),data,CURRENT_PREFIX)
        previous=json.loads(old['messages'][2]['content']);current=json.loads(new['messages'][2]['content'])
        self.assertNotIn('sources',previous['dialogue_focus'])
        focused=current['dialogue_focus']['sources']
        self.assertEqual(previous['sources'],{**current['sources'],**focused})
        self.assertFalse(set(current['sources'])&set(focused))
        self.assertLessEqual(len(focused),5)
        self.assertTrue(all(r['kind']=='testimony' for r in focused.values()))

    def test_new_focus_separates_received_speakers_and_appears_at_end(self):
        own=self.speak('A','我已说清楚自己的意见。');self.speak('C','这是别人已经说过的意见。')
        other=self.s['observations']['A'][-1]['id'];data=self.role_data()
        body,_=self.app.gateway.payload('ensemble_role',w.baseline(self.s,'A'),data,CURRENT_PREFIX)
        packed=json.loads(body['messages'][2]['content']);focus=packed['dialogue_focus']
        self.assertEqual(next(reversed(packed)),'dialogue_focus')
        self.assertEqual(focus['reply_as'],'A');self.assertEqual(focus['own_recent_speech'][0]['id'],own)
        self.assertEqual(focus['heard_recent_speech'],[{'id':other,'speaker':'C','channel':'public'}])
        old=self.role_data(version='ai-tasks-v114.json')['dialogue_focus']
        self.assertEqual(old,{'version':1,'own_recent_speech':[{'id':own,'channel':'public'}]})

    def test_wrong_perspective_has_field_permission_receipt_before_bad_patch(self):
        for actor,wrong,right in (('A','strategy_update','belief_update'),('B','belief_update','strategy_update')):
            state=deepcopy(self.s);before=canonical(state)
            def invalid(task,out,data):
                if task=='ensemble_role':out[wrong]={'patch':{'invented_field':'MUST_NOT_BE_PARSED'}}
            with self.assertRaises(ValueError) as caught:self.app.turn(state,actor,self.f.caller(CURRENT_PREFIX,invalid),0)
            receipt=caught.exception.feedback['validation_receipt']
            self.assertEqual(receipt['violations'][0]['path'],'response.'+wrong)
            self.assertEqual(receipt['violations'][0]['reason'],'field_not_allowed')
            self.assertIn(right,receipt['expected']['allowed_fields'])
            self.assertNotIn(wrong,receipt['expected']['allowed_fields'])
            self.assertNotIn('MUST_NOT_BE_PARSED',canonical(receipt))
            self.assertEqual(canonical(state),before)

    def test_native_source_continuation_retains_same_focus(self):
        identity=self.speak('A','我之前已经解释过自己的立场。');seen=[]
        def transform(task,out,data):
            if task!='ensemble_role':return
            seen.append(deepcopy(data['dialogue_focus']))
            if '_tool_messages' not in data:
                out.clear();out['_tool_message']={'role':'assistant','content':None,'tool_calls':[
                    {'id':'read_own_once','type':'function','function':{'name':'read_sources',
                     'arguments':canonical({'requests':[{'id':identity}]})}}]}
        self.app.turn(self.s,'A',self.f.caller(CURRENT_PREFIX,transform),0)
        self.assertEqual(len(seen),2);self.assertEqual(seen[0],seen[1])

    def test_identical_prose_remains_accepted_and_raw_history_is_not_filtered(self):
        text='我同意先核对记录。';self.speak('C',text)
        def repeat(task,out,data):
            if task=='ensemble_role':out['speech']=text
        self.app.turn(self.s,'A',self.f.caller(CURRENT_PREFIX,repeat),0)
        speeches=[(e['actor'],e['facts']['text']) for e in self.s['events'] if e['kind']=='testimony']
        self.assertIn(('C',text),speeches);self.assertIn(('A',text),speeches)


if __name__=='__main__':unittest.main()
