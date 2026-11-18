"""Bounded working views preserve source access, authorization and replay."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from palter import ensemble_world as w, ensemble_context, compact_context, source_access, working_context
from palter import source_provenance, temporal_facts, event_tools
from palter.ai_gateway import request_sizes
from palter.deepseek import DeepSeek, Settings
from palter.ensemble import EnsembleApplication
from palter.storage import canonical, StoreError
from tests import test_ensemble_review as fixtures

VERSION='ai-tasks-v93.json'


def tool(name,args,identity='source_call'):
    return {'id':identity,'type':'function','function':{'name':name,'arguments':canonical(args)}}


class WorkingContextTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.ReviewFixTests();f.setUp();self.addCleanup(f.doCleanups)
        self.f=f;self.app=f.app;self.s=f.state
        self.app.gateway.current_version=VERSION;self.app.configure_rules(self.s,lambda:None)

    def data(self):
        data=w.context(self.s,'A')
        ensemble_context.project(self.s,'A',data,concise=True,receipts=True)
        ensemble_context.investigation_state(self.s,'A',data)
        compact_context.recall(self.s,'A',data)
        data['source_provenance']=source_provenance.for_role(self.s,'A',data)
        data['temporal_facts']=temporal_facts.for_role(self.s,'A')
        return data

    def long_history(self):
        for index in range(1000):
            event=w.emit(self.s,'testimony','B')
            w.note(self.s,'A',event,f'我第{index}次提到旧账的原始凭据。','testimony',speaker='B')
        self.old=self.s['observations']['A'][-1000]['id']
        self.s['memory']['A']={'entries':[{'id':'m1','kind':'heard_claim','text':'我听到对方谈及旧账，尚未核实。','sources':[self.old]}],
            'summary':'我听到对方谈及旧账，尚未核实。','sources':[self.old],'checkpoint':len(self.s['observations']['A'])}
        template=next(iter(self.s['case']['clues']))
        for index in range(80):
            identity=f'archive{index}'
            self.s['known']['A'][identity]={**deepcopy(template),'id':identity,'title':f'第{index}份凭据',
                'observation':f'独立原文{index}：'+('“账目\\内容”\n'*65),'acquired_event':f'e{index:06}','via':'亲自检查'}
        # These newly received bodies must survive selection even when very large.
        event=w.emit(self.s,'evidence','A')
        w.note(self.s,'A',event,self.s['known']['A']['archive0']['observation'],'evidence',evidence_id='archive0')
        w.note(self.s,'A',event,'这是必须完整保留的新回执。','observation')

    def payload(self,data=None,baseline=None):
        return self.app.gateway.payload('ensemble_role',w.baseline(self.s,'A') if baseline is None else baseline,
            self.data() if data is None else data,VERSION)[0]

    def test_long_history_fits_without_deleting_sources_or_new_receipts(self):
        self.long_history();data=self.data();before=deepcopy(self.s);body=self.payload(data)
        wire=json.loads(body['messages'][2]['content']);sizes=request_sizes(body,2)
        self.assertLessEqual(sizes['dynamic_bytes'],51200);self.assertLessEqual(sizes['total_bytes'],90000)
        self.assertEqual(wire['sources']['archive0']['observation'],self.s['known']['A']['archive0']['observation'])
        for row in working_context.rows(wire['observations']):self.assertIn(row['source_ref'],wire['sources'])
        self.assertLess(len(wire['heard_statement_ids']),1000)
        self.assertEqual(wire['working_context']['totals']['heard_statements'],1000)
        deferred=next(identity for identity in self.s['known']['A'] if identity not in wire['sources'])
        fetched=source_access.lookup(self.s,'A',{'requests':[{'id':deferred}]})['sources'][0]
        self.assertEqual(fetched['text'],self.s['known']['A'][deferred]['observation'])
        self.assertEqual(fetched['origin'],'acquired_record')
        self.assertEqual(self.s,before);self.assertEqual(data,self.data())

    def test_directory_paging_covers_all_authorized_records_and_searches_old_speech(self):
        self.long_history();seen=[];offset=0
        while True:
            page=source_access.directory(self.s,'A',{'kind':'evidence','offset':offset})
            self.assertLessEqual(len(canonical(page).encode()),source_access.LIST_BYTES)
            seen.extend(row['id'] for row in page['rows'])
            if page['next_offset'] is None:break
            self.assertGreater(page['next_offset'],offset);offset=page['next_offset']
        self.assertEqual(len(seen),len(set(seen)));self.assertEqual(set(seen),set(self.s['known']['A']))
        page=source_access.directory(self.s,'A',{'kind':'testimony','query':'第0次'})
        self.assertEqual([row['id'] for row in page['rows']],[self.old])
        fetched=source_access.lookup(self.s,'A',{'requests':[{'id':self.old}]})['sources'][0]
        self.assertEqual(fetched['origin'],'heard_claim');self.assertEqual(fetched['speaker'],'B')

    def test_queries_and_reads_cannot_discover_unheard_or_unacquired_sources(self):
        event=w.emit(self.s,'testimony','B');w.note(self.s,'B',event,'PRIVATE_CANARY','testimony',speaker='B')
        identity=self.s['observations']['B'][-1]['id']
        for category in ('evidence','testimony','observation','initial'):
            result=source_access.directory(self.s,'A',{'kind':category,'query':'PRIVATE_CANARY'})
            self.assertEqual(result['total'],0)
        result=source_access.lookup(self.s,'A',{'requests':[{'id':identity},{'id':'c12'},{'id':'nonexistent'}]})
        self.assertEqual([row['status'] for row in result['sources']],['unavailable']*3)
        self.assertNotIn('PRIVATE_CANARY',canonical(result))

    def test_multibyte_escaped_original_paginates_by_character_without_loss(self):
        original='中文“引号”\\\n'*2300;event=w.emit(self.s,'observation','A');w.note(self.s,'A',event,original)
        identity=self.s['observations']['A'][-1]['id'];offset=0;parts=[]
        while True:
            result=source_access.lookup(self.s,'A',{'requests':[{'id':identity,'offset':offset}]})
            self.assertLessEqual(len(canonical(result).encode()),source_access.READ_BYTES)
            row=result['sources'][0];parts.append(row['text'])
            if row['next_offset'] is None:break
            self.assertGreater(row['next_offset'],offset);offset=row['next_offset']
        self.assertEqual(''.join(parts),original)

    def test_batch_byte_budget_includes_unavailable_unicode_identifiers(self):
        event=w.emit(self.s,'observation','A');w.note(self.s,'A',event,'长'*6000)
        identity=self.s['observations']['A'][-1]['id']
        result=source_access.lookup(self.s,'A',{'requests':[{'id':identity}]+[{'id':'未知'*99+str(i)} for i in range(7)]})
        self.assertEqual(len(result['sources']),8)
        self.assertLessEqual(len(canonical(result).encode()),source_access.READ_BYTES)
        self.assertTrue(all(row['status']=='unavailable' for row in result['sources'][1:]))

    def test_native_receipts_and_retry_feedback_stay_exact_under_joint_budget(self):
        self.long_history();data=self.data()
        data['_tool_messages']=[{'role':'assistant','content':None,'tool_calls':[tool('read_sources',{'requests':[{'id':'archive1'}]})]},
            {'role':'tool','tool_call_id':'source_call','content':canonical({'text':'实\\\n'*3500})}]
        data['validation_feedback']={'code':'test','instruction':'保留必要引用。'*100}
        body=self.payload(data);wire=json.loads(body['messages'][2]['content'])
        self.assertEqual(body['messages'][3:],data['_tool_messages'])
        self.assertEqual(wire['validation_feedback'],data['validation_feedback'])
        self.assertLessEqual(request_sizes(body,2)['dynamic_bytes'],51200)
        self.assertLessEqual(request_sizes(body,2)['total_bytes'],90000)

    def test_large_immutable_prefix_reduces_optional_context_within_total_limit(self):
        self.long_history()
        body=self.payload(baseline={'immutable':'x'*30000})
        sizes=request_sizes(body,2);wire=json.loads(body['messages'][2]['content'])
        self.assertLessEqual(sizes['dynamic_bytes'],51200);self.assertLessEqual(sizes['total_bytes'],90000)
        self.assertIn('archive0',wire['sources'])

    def test_memory_reference_ids_have_no_count_cap_or_silent_truncation(self):
        self.long_history();sources=[row['id'] for row in self.s['observations']['A'] if row['kind']=='testimony']
        self.s['memory']['A']['entries'][0]['sources']=sources;self.s['memory']['A']['sources']=sources
        wire=json.loads(self.payload()['messages'][2]['content'])
        self.assertEqual(wire['memory']['entries'][0]['sources'],sources)
        self.assertLess(len(wire['source_provenance']),len(sources))

    def test_irreducible_required_information_fails_instead_of_truncating(self):
        data=self.data();data['thoughts']='原'*20000
        with self.assertRaises(StoreError) as error:self.payload(data)
        self.assertEqual(error.exception.code,'context_budget')

    def test_fit_is_deterministic_and_historical_prefix_keeps_full_context(self):
        data=self.data();before=deepcopy(data)
        a=self.payload(data);b=self.payload(data);self.assertEqual(a,b);self.assertEqual(data,before)
        old,_=self.app.gateway.payload('ensemble_role',w.baseline(self.s,'A'),data,'ai-tasks-v92.json')
        wire=json.loads(old['messages'][2]['content']);self.assertNotIn('working_context',wire)
        expected=compact_context.pack('ensemble_role',data,authorized_keys=True,memory_capacity=True,memory_source_capacity=True,memory_source_limits=False)
        self.assertEqual(old['messages'][2]['content'],compact_context.dumps(expected))
        root=Path('palter/prefixes');manifest=json.loads((root/'manifest.json').read_text())
        for name,digest in manifest.items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)

    def test_memory_can_list_then_read_without_advancing_to_recalled_history(self):
        self.long_history();observations=deepcopy(self.s['observations']);stages=[];tools=[]
        source=self.old
        def call(stage,task,baseline,data,validate,actor=None):
            stages.append(stage);payload,_=self.app.gateway.payload(task,baseline,data,VERSION)
            tools.append([m for m in payload['messages'] if m['role']=='tool'])
            if len(stages)==1:out={'_tool_message':{'role':'assistant','content':None,'tool_calls':[tool('list_sources',{'kind':'testimony','query':'第0次'})]}}
            elif len(stages)==2:out={'_tool_message':{'role':'assistant','content':None,'tool_calls':[tool('read_sources',{'requests':[{'id':source}]},'read_call')]}}
            else:out={'entries':deepcopy(self.s['memory']['A']['entries']),'processed_through':data['observations'][-1]['id']}
            validate(out);return out,stage
        call.prefix_version=VERSION
        self.app.summarize_chunk(self.s,'A',call,len(self.s['observations']['A']))
        self.assertEqual(len(stages),3);self.assertEqual([len(t) for t in tools],[0,1,2])
        self.assertEqual(self.s['observations'],observations)
        self.assertEqual(self.s['memory']['A']['checkpoint'],len(observations['A']))

    def test_role_can_page_source_reads_but_stops_after_two_batches(self):
        data=self.data();data['context_format']=1;data['source_access']={'version':1}
        source=self.s['case']['roles']['A']['knows'][0];stages=[]
        def call(stage,task,baseline,data,validate,actor=None):
            stages.append(stage)
            if len(stages)<=2:out={'_tool_message':{'role':'assistant','content':None,'tool_calls':[tool('read_sources',{'requests':[{'id':source}]},str(len(stages)))]}}
            else:out={'next_decision':{'mode':'continue','events':[]}}
            validate(out);return out,stage
        out,_=event_tools.decide_compact(self.s,'A',call,w.baseline(self.s,'A'),data,lambda out:None,set())
        self.assertEqual(len(stages),3);self.assertEqual(out['next_decision']['mode'],'continue')
        def repeat(stage,task,baseline,data,validate,actor=None):
            out={'_tool_message':{'role':'assistant','content':None,'tool_calls':[tool('list_sources',{'kind':'evidence'})]}}
            validate(out);return out,stage
        with self.assertRaisesRegex(ValueError,'tool continuation budget'):event_tools.decide_compact(self.s,'A',repeat,{},data,lambda out:None,set())

    def test_paid_memory_source_stage_replays_after_restart_and_manual_retry(self):
        source=self.s['case']['roles']['A']['knows'][0];fail=True;native_calls=[]
        def provider(payload):
            if not any(m['role']=='tool' for m in payload['messages']):
                native_calls.append(deepcopy(payload))
                message={'role':'assistant','content':None,'tool_calls':[tool('read_sources',{'requests':[{'id':source}]})]}
                choice={'finish_reason':'tool_calls','message':message}
            else:
                if fail:raise TimeoutError('synthetic interruption after paid retrieval plan')
                data=json.loads(next(m['content'] for m in payload['messages'] if m['role']=='user'))
                observations=working_context.rows(data['observations'])
                out={'entries':[{'id':'m1','kind':'observed','text':'我核对了自己的初始记录。','sources':[source]}],
                    'processed_through':observations[-1]['id'] if observations else None}
                choice={'finish_reason':'stop','message':{'content':canonical(out)}}
            return {'choices':[choice],'usage':{'prompt_tokens':100,'completion_tokens':30,'prompt_cache_hit_tokens':40,'prompt_cache_miss_tokens':60}}
        self.app.gateway.client.transport=provider;self.app.gateway.retry_delays=(0,0,0)
        owner=self.app.store.session()['id']
        saved=self.app.store.create_game(owner,{'command_id':'source_recovery_create','expected_game_id':None},
            lambda gid:dict(deepcopy(self.s),id=gid))
        command={'command_id':'source_recovery_operation','expected_revision':saved['revision'],'kind':'probe'}
        def work(state,call):self.app.summarize_chunk(state,'A',call,len(state['observations']['A']))
        with self.assertRaises(StoreError):self.app.operate(owner,saved['id'],command,work)
        with self.app.store.transaction(False) as con:
            original=dict(con.execute("SELECT * FROM ai_calls WHERE status='completed'").fetchone())
            self.assertEqual(con.execute("SELECT count(*) FROM ai_calls WHERE status='failed'").fetchone()[0],4)
        path=self.app.store.path;fail=False
        self.app=EnsembleApplication(path,DeepSeek(Settings(api_key='fixture'),provider));self.app.gateway.current_version='ai-tasks-v92.json'
        self.app.gateway.retry_delays=(0,0,0)
        with self.app.store.transaction() as con:self.app.gateway.renew_retry(con,saved['id'],command['command_id'])
        result,_=self.app.operate(owner,saved['id'],command,work)
        self.assertEqual(len(native_calls),1);self.assertIn(source,result['memory']['A']['sources'])
        with self.app.store.transaction(False) as con:
            self.assertEqual(dict(con.execute('SELECT * FROM ai_calls WHERE id=?',(original['id'],)).fetchone()),original)
            op=con.execute('SELECT prefix_version,status FROM ai_operations WHERE id=?',(command['command_id'],)).fetchone()
            self.assertEqual(tuple(op),(VERSION,'completed'))


if __name__=='__main__':unittest.main()
