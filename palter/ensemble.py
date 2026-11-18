"""Authenticated ensemble play over the durable, prefix-pinned model runtime."""

from copy import deepcopy
from . import output_contracts
import json
import secrets
import threading
import time

from .investigation import InvestigationApplication
from .ai_runtime import AIApplication, text, references
from . import ensemble_world as w
from . import spectator
from . import ensemble_context as context
from . import role_schedule as scheduling
from . import role_events
from . import compact_context, memory_entries, memory_policy, action_feedback
from . import event_tools, ensemble_review, investigation_reminders
from .ai_gateway import retryable, manually_retryable, error_message, request_sizes, MAX_DYNAMIC_CONTEXT_BYTES, MAX_REQUEST_BYTES
from .scenario_cases import build, validate_story, SCENARIOS
from .case_authoring import candidate_casts, validate_generated_cast
from .storage import StoreError, canonical, fingerprint


class EnsembleApplication(InvestigationApplication):
    gameplay='ensemble'

    def __init__(self,database,model=None):
        super().__init__(database,model)
        self._stop=threading.Event();self._worker=None;self._seen={};self._watch_due={}

    def actor(self,owner,gid):
        with self.store.transaction(False) as con:
            self.store.load(con,owner,gid)
            row=con.execute('SELECT actor FROM game_members WHERE game_id=? AND session_id=?',(gid,owner)).fetchone()
        if row is None:raise StoreError('你还没有加入这局。',403,'not_member')
        return row['actor']

    def create_game(self,owner,command):
        if not self.model.configured:raise StoreError('请先配置 DeepSeek。',503,'not_configured')
        command_id=self.store.command_id(command.get('command_id'))
        with self.store.transaction(False) as con:
            saved=con.execute('SELECT g.state FROM creations c JOIN games g ON g.id=c.game_id WHERE c.owner=? AND c.id=?',(owner,command_id)).fetchone()
        if saved:
            previous=json.loads(saved['state'])
            if previous.get('gameplay')=='investigation':return InvestigationApplication.create_game(self,owner,command)
            if previous.get('gameplay')!='ensemble':
                if previous.get('mode')=='ai':return AIApplication.create_game(self,owner,command)
                return self.store.create_game(owner,command)
        scenario=command.get('category','murder');scenario='murder' if scenario=='mystery' else scenario
        humans=command.get('humans',1);opening=command.get('opening','after')
        if scenario not in SCENARIOS or type(humans) is not int or humans not in range(5) or opening not in ('after','interactive'):raise StoreError('请选择支持的场景、真人人数和开场方式。')
        def factory(gid):
            state=w.blank(gid,scenario,humans,opening if scenario=='murder' else 'after')
            return spectator.initialize(state) if humans==0 else state
        state=self.store.create_game(owner,command,factory)
        with self.store.transaction() as con:con.execute('INSERT OR IGNORE INTO game_members VALUES (?,?,?)',(state['id'],owner,'observer' if humans==0 else 'A'))
        operation={'command_id':'preview_'+command['command_id'],'expected_revision':0,'kind':'preview','_actor':'A'}
        state,_=self.operate(owner,state['id'],operation,self.generate_preview)
        return state

    def generate_preview(self,s,call):
        version=getattr(call,'prefix_version',self.gateway.current_version)
        generated=self.gateway.versions[version]['ensemble_preview'].get('generated_cast',False)
        rosters=None if generated else candidate_casts(int(s['id'][:8],16))
        data={'scenario':SCENARIOS[s['scenario']],'seed':s['id'][:8]}
        if generated:data['participants']=list(w.ACTORS)
        else:data['rosters']=rosters
        def validate(out):
            if not isinstance(out['candidates'],list) or len(out['candidates'])!=3:raise ValueError('three previews')
            for c in out['candidates']:
                text(c['title'],100);text(c['introduction'],1000)
                if generated:validate_generated_cast(c)
        out,_=call('preview','ensemble_preview',None,data,validate)
        index=int(s['id'][8:16],16)%3
        chosen={k:out['candidates'][index][k] for k in ('title','introduction','cast','victim')} if generated else {**out['candidates'][index],**rosters[index]}
        s.update(preview=chosen,title=chosen['title'],introduction=chosen['introduction'])

    def join(self,owner,command):
        if set(command)!={'code','command_id'} or not isinstance(command['code'],str):raise StoreError('加入请求格式无效。')
        self.store.command_id(command['command_id'])
        with self.store.transaction() as con:
            rows=con.execute("SELECT id,state FROM games WHERE json_extract(state,'$.gameplay')='ensemble' AND json_extract(state,'$.join_code')=?",(command['code'].strip(),)).fetchall()
            if not rows:raise StoreError('没有找到这个房间。',404,'not_found')
            previous=json.loads(rows[0]['state']);gid=previous['id']
            member=con.execute('SELECT actor FROM game_members WHERE game_id=? AND session_id=?',(gid,owner)).fetchone()
            if member:
                con.execute('UPDATE sessions SET active_game=? WHERE id=?',(gid,owner));return previous
            if con.execute("SELECT 1 FROM ai_operations WHERE game_id=? AND status IN ('pending','buffered')",(gid,)).fetchone():
                raise StoreError('故事正在准备，请稍后再加入。',503,'ai_pending')
            if previous['phase'] not in ('introduction','lobby') or previous['archived']:raise StoreError('这局已经开始，不能再占用角色。')
            free=[a for a in previous['humans'] if a not in previous['joined']]
            if not free:raise StoreError('真人席位已满。')
            state=deepcopy(previous);actor=free[0];state['joined'].append(actor);state['revision']+=1
            con.execute('INSERT INTO game_members VALUES (?,?,?)',(gid,owner,actor))
            con.execute('UPDATE sessions SET active_game=? WHERE id=?',(gid,owner));self.store.save(con,state,previous)
        return state

    def view(self,owner,state):
        if state.get('gameplay')!='ensemble':return super().view(owner,state)
        actor=self.actor(owner,state['id']);self._seen[state['id']]=time.time()
        result=spectator.view(state) if 'watch' in state else w.view(state,actor,actor=='A')
        if state.get('structured_conclusion_version') and state.get('scenario')=='murder' and 'case' in state:
            from . import final_arguments
            result['final_dimensions']=final_arguments.dimensions(state['case'])
        result['background_error']=deepcopy(result['background_error'])
        result['ai_trace']=self.gateway.trace(owner,state['id'])
        result['ai_busy']=result['ai_trace']['operation_status']=='pending'
        if not result['background_error'] and result['ai_trace']['operation_status'] in ('failed','interrupted'):
            with self.store.transaction(False) as con:
                op=con.execute('SELECT id,command,retry_state,error FROM ai_operations WHERE game_id=? AND id=?',(state['id'],result['ai_trace']['operation_id'])).fetchone()
                failed=con.execute('SELECT stage,error FROM ai_calls WHERE game_id=? AND operation_id=? ORDER BY started DESC LIMIT 1',(state['id'],op['id'])).fetchone() if op else None
            command=json.loads(op['command']) if op else {}
            try:failure=json.loads(op['error'] or '{}') if op else {}
            except ValueError:failure={}  # Legacy operations stored the exception class name.
            code=failure.get('code') or (failed['error'] if failed else None)
            own=command.get('_actor')==actor or (command.get('kind') in ('background','confirm','preview') and actor in ('A','observer'))
            if code and (own or actor in ('A','observer')):
                attempts=json.loads(op['retry_state']).get(failed['stage'],{}).get('attempts',0) if failed else 0
                detail=f'已尝试 {attempts} 次（含自动重试）' if attempts else '本次调用未完成'
                message=(failure.get('message') or error_message(code)+'。'+detail+'，请决定是否重试。') if own else '有位参与者的操作未完成。可等待该参与者恢复，或由房主取消此步骤。'
                result['background_error']={'operation_id':op['id'],'code':code,'message':message,'retryable':manually_retryable(code),'can_retry':own}
        if result['background_error']:
            code=result['background_error'].get('code')
            result['background_error']['retryable']=(manually_retryable(code) or code=='watch_budget') and result['background_error'].get('can_retry',True)
            if state.get('background_error') and actor not in ('A','observer'):
                result['background_error']['retryable']=False
        result['pending_ai']=len(state['agenda']);return result

    def command(self,owner,gid,command):
        state=self.store.state(owner,gid)
        if state.get('gameplay')!='ensemble':return super().command(owner,gid,command)
        actor=self.actor(owner,gid)
        if 'watch' in state:return spectator.command(self,owner,state,command)
        allowed={'command_id','expected_revision','kind','choice','text','target','channel','evidence_ids','testimony_ids','suspect','volunteer','handling','operation_id','trust','affinity','aspects'}
        if set(command)-allowed or type(command.get('expected_revision')) is not int:raise StoreError('操作格式或版本无效。')
        for key,limit in (('text',4000),('choice',120),('target',50),('suspect',20),('channel',80),('handling',20)):
            if key in command and (not isinstance(command[key],str) or len(command[key])>limit):raise StoreError('操作字段无效。')
        kind=command.get('kind')
        if kind in ('pause','resume'):
            if len(state['humans'])>1:raise StoreError('多人游戏查看剧本不会暂停其他人的行动。')
            return self.control(owner,gid,command)
        if kind=='retry_ai':return self.retry_background(owner,gid,command)
        if kind=='cancel_pending':
            if actor!='A':raise StoreError('仅房主可取消共同的后台任务。',403)
            return self.cancel_step(owner,gid,command)
        internal={**command,'_actor':actor}
        state,receipt=self.operate(owner,gid,internal,lambda s,call:self.play(s,actor,command,call))
        if receipt.get('accepted'):receipt['message']='你的行动已保存。' if state['phase']!='ended' else '故事结束，可以查看每个人的目标结果。'
        self._seen[gid]=time.time();return state,receipt

    def prepare(self,state,call):
        if set(state['joined'])!=set(state['humans']):raise StoreError('请等待所有真人加入。')
        def validate(out):validate_story(out)
        story,_=call('story','ensemble_setup',None,{'premise':state['preview'],'scenario':SCENARIOS[state['scenario']],
                        'family':('clock','recording','substitution')[int(state['id'][:8],16)%3],
                        'rooms_contract':'r1 shared meeting area; r2 central scene/worksite; r3 records/equipment area. Documents are placed by runtime; describe objects without naming a conflicting room.'},validate)
        state['story']=story
        if state['scenario']=='murder' and state['opening']=='interactive' and state['humans']:state['phase']='opening'
        else:self.finish_setup(state,call)

    def finish_setup(self,state,call):
        self.configure_rules(state,call)
        intentions=state['intentions'] if state['opening']=='interactive' else None
        if intentions is not None:
            for a in w.ai_roles(state):
                def validate(out):
                    if type(out['volunteer']) is not bool or out['handling'] not in ('leave','inspect','touch'):raise ValueError('opening choice')
                out,_=call('opening_'+a,'ensemble_opening',{'actor':a,'profile':state['story']['roles'][a],
                    'name':state['preview']['cast'][a]}, {'public_premise':state['preview']['introduction']},validate,a)
                intentions[a]=out
        version=getattr(call,'prefix_version',self.gateway.current_version)
        rules=self.gateway.versions[version]['ensemble_setup'].get('rules_version',1)
        case=build(state['story'],state['preview'],state['scenario'],int(state['id'][:8],16),state['humans'],intentions,rules_version=rules)
        if self.gateway.versions[version]['ensemble_role'].get('context_version',1)>=4:
            state['closure']={'votes':[],'ready':False}
        w.initialize(state,case)

    def play(self,state,actor,command,call):
        self.configure_rules(state,call)
        kind=command['kind']
        if kind=='confirm' and state['phase']=='introduction':
            if actor!='A':raise StoreError('由房主确认故事。')
            if len(state['joined'])<len(state['humans']):state['phase']='lobby'
            else:self.prepare(state,call)
            return
        if kind=='prepare' and state['phase']=='lobby':
            if actor!='A':raise StoreError('由房主开始准备。')
            self.prepare(state,call);return
        if kind=='opening' and state['phase']=='opening':
            if type(command.get('volunteer')) is not bool or command.get('handling') not in ('leave','inspect','touch'):raise StoreError('请选择开场意愿和到场后的处理方式。')
            state['intentions'][actor]={'volunteer':command['volunteer'],'handling':command['handling']}
            if all(a in state['intentions'] for a in state['humans']):self.finish_setup(state,call)
            return
        if kind=='ready' and state['phase']=='reading':
            if actor not in state['ready']:state['ready'].append(actor)
            if set(state['ready'])==set(state['humans']):w.start(state)
            return
        if state['phase']!='active':raise StoreError('请先完成准备或恢复游戏。')
        w.expire(state)
        if actor in state['submissions']:raise StoreError('你已提交最终结论，正在等待其他真人。')
        ids=command.get('evidence_ids',[])
        if not isinstance(ids,list) or any(not isinstance(cid,str) for cid in ids) or not set(ids)<=set(state['known'][actor]):raise StoreError('只能引用自己已经获得的材料。')
        if command.get('channel',w.channel(state,actor))!=w.channel(state,actor):raise StoreError('谈话范围已经变化，内容未发送。')
        words=command.get('text','').strip();target=command.get('target') or None
        if kind in ('say','present','challenge','gesture') and target and target not in w.audience(state,actor):raise StoreError('对方不在当前谈话范围。')
        if kind=='notebook':state['notes'][actor]={'text':words,'evidence_ids':list(dict.fromkeys(ids))};return
        if kind=='thought':
            if not words:raise StoreError('请填写自己的想法。')
            state['thoughts'][actor].append(words);self.summarize(state,actor,call);return
        if kind=='attitude':
            if target not in w.ACTORS or target==actor:raise StoreError('请选择另一个角色。')
            delta=command.get('trust',0);affinity=command.get('affinity',0)
            if any(type(v) not in (int,float) or not -.2<=v<=.2 for v in (delta,affinity)):raise StoreError('关系变化幅度无效。')
            if not words:raise StoreError('请写下你改变看法的原因。')
            self.relationship(state,actor,{'target':target,'trust_delta':delta,'affinity_delta':affinity,'reason':words,'sources':[]},'human')
            return
        if kind not in ('say','present','challenge','gesture','act','intent','forge','submit'):raise StoreError('不支持的操作。')
        consent_reply=kind=='act' and command.get('choice','').split(':')[0] in ('accept','decline') and not state['obligations'][actor]['explain']
        leaving_private=scheduling.enabled(state) and kind=='act' and command.get('choice')=='end_private' and w.chat_for(state,actor)
        travel_speech=w.local_communication(state) and kind=='act' and command.get('choice','').startswith('move:') and bool(words)
        if kind not in ('say','present','challenge','gesture','submit') and not consent_reply and not leaving_private and not travel_speech and (state['obligations'][actor]['response'] or w.must_speak(state,actor)):
            if state['obligations'][actor]['explain']:raise StoreError('请先在交流与质证中用话语解释收到的质疑，再继续行动。')
            if w.must_speak(state,actor):raise StoreError('已经连续几次交流没有发言，请先在交流与质证中说话，再继续行动；动作不能代替这次发言。')
            raise StoreError('有人等你回应，请先用话语或允许的动作作答。')
        if kind=='submit':
            structured=None
            if 'aspects' in command:
                if state['scenario']!='murder' or not state.get('structured_conclusion_version'):raise StoreError('当前剧本不支持分项结论。')
                from . import final_arguments
                try:structured=final_arguments.normalize(state,actor,{'suspect':command.get('suspect') or None,'aspects':command['aspects']})
                except (ValueError,KeyError,TypeError) as exc:raise StoreError('请按所需维度填写说明，只引用自己已取得的材料和实际听到的发言。') from exc
                words=structured['explanation'];ids=structured['evidence_ids']
            if w.chat_for(state,actor):raise StoreError('请先结束私聊再提交最终结论。')
            if state['scenario']=='murder' and (command.get('suspect') not in ('',None,*w.ACTORS) or (command.get('suspect') and not words)):raise StoreError('请选择指认对象并写下推理，也可以选择暂未查明。')
            heard=structured['testimony_ids'] if structured else command.get('testimony_ids',[])
            acquired={o['id'] for o in state['observations'][actor] if o['kind']=='testimony'}
            if not isinstance(heard,list) or any(not isinstance(s,str) or s not in acquired for s in heard):raise StoreError('只能引用自己实际听到的发言。')
            state['submissions'][actor]={'suspect':command.get('suspect'),'explanation':words,'evidence_ids':ids}
            if heard:state['submissions'][actor]['testimony_ids']=list(dict.fromkeys(heard))
            if structured:state['submissions'][actor]=structured
            if set(state['submissions'])==set(state['humans']):self.conclude_ensemble(state,call)
            return
        start=len(state['events'])
        if kind in ('say','present','challenge'):
            if kind in ('present','challenge') and not ids:raise StoreError('请先选择要质证的材料。')
            if not words:raise StoreError('请填写要说的话。')
            if target is None and w.chat_for(state,actor):target=next(a for a in w.audience(state,actor) if a!=actor)
            if target is None:
                def validate(out):
                    if out['target'] not in (None,*w.ACTORS):raise ValueError('addressed actor')
                data={'speaker':actor,'cast':{a:w.name(state,a) for a in w.audience(state,actor)},
                      'utterance':words,'recent_conversation':state['observations'][actor][-8:]}
                self.conversation_context(state,actor,data,call,'ensemble_address')
                if 'conversation' in data:data['cast']={a:w.name(state,a) for a in w.ACTORS}
                out,_=call('address','ensemble_address',None,data,validate,actor)
                target=out['target']
            if kind in ('present','challenge'):
                for cid in ids:w.apply_choice(state,actor,'share:'+cid)
            e=w.speak(state,actor,words,target,challenge=kind in ('present','challenge'),allow_unheard=True)
            if not target or target not in w.audience(state,actor):
                eligible=[a for a in w.audience(state,actor) if a in w.ai_roles(state)]
                if eligible:w.enqueue(state,max(eligible,key=lambda a:state['silent'][a]),'回应当前公开交流。',e['id'],interrupt=False)
        elif kind=='gesture':
            if words not in ('点头','摇头','示意稍后回答'):raise StoreError('请选择提供的回应动作。')
            w.speak(state,actor,words,target,gesture=True)
        elif kind in ('act','intent'):
            choice=command.get('choice')
            if kind=='intent':
                def validate(out):
                    if out['choice'] is not None and out['choice'] not in {x['id'] for x in w.choices(state,actor)}:raise ValueError('unsupported choice')
                    text(out['clarification'],1000,True)
                out,_=call('interpret','ensemble_action',w.baseline(state,actor),{'request':words,'view':w.context(state,actor)},validate,actor)
                choice=out['choice']
                if choice is None:raise StoreError(out['clarification'] or '请明确要尝试的动作。')
            if w.local_communication(state) and kind=='act' and str(choice).startswith('move:') and words:
                if len(words)>1200:raise StoreError('移动时的发言请不超过 1200 字。')
                if choice not in {c['id'] for c in w.choices(state,actor)}:raise StoreError('当前不能这样移动，请查看最新现场。')
                w.speak(state,actor,words,target)
            w.apply_choice(state,actor,choice)
            if choice=='wait':
                w.advance(state)
                for a in w.ai_roles(state):w.enqueue(state,a,'获得一次自主行动机会。',interrupt=False)
        elif kind=='forge':
            if not words or len(words)>1000:raise StoreError('请写下不超过 1000 字的文书内容。')
            if w.running(state,actor):raise StoreError('请先结束当前行动。')
            e=w.emit(state,'document_created',actor);cid='document'+str(len(state['events']))
            state.setdefault('created_documents',{})[cid]={'id':cid,'title':'一张手写文书','observation':'纸面写着：“'+words+'”。文字内容是一份主张，尚未核实。',
                'location':state['locations'][actor],'source':'手写纸张','category':'document','author':actor}
            state['objects'][cid]={'holder':actor,'condition':'intact','hidden':False,'protected':False};w.acquire(state,actor,cid,e,'自己写成');w.advance(state)
        self.adjudicate_ensemble(state,start,call)
        w.expire(state)
        scheduling.reconcile(state)

    def relationship(self,state,actor,update,call_id):
        r=state['relationships'][actor][update['target']]
        for key,delta in (('trust','trust_delta'),('affinity','affinity_delta')):r[key]=max(-1,min(1,r[key]+update[delta]))
        r['experiences'].append({'reason':update['reason'],'sources':update['sources'],'call_id':call_id})

    def summarize(self,state,actor,call):
        compacted=self.compact(state,actor,call)
        if compacted and state['memory'][actor]['checkpoint']==len(state['observations'][actor]):return
        version=getattr(call,'prefix_version',self.gateway.current_version)
        if self.gateway.versions[version]['ensemble_memory'].get('memory_policy') and state['memory'][actor]['checkpoint']==len(state['observations'][actor]):return
        self.summarize_chunk(state,actor,call,len(state['observations'][actor]))

    def compact(self,state,actor,call):
        compacted=False
        while len(state['observations'][actor])-state['memory'][actor]['checkpoint']>24:
            end=min(state['memory'][actor]['checkpoint']+32,len(state['observations'][actor]))
            self.summarize_chunk(state,actor,call,end)
            compacted=True
        version=getattr(call,'prefix_version',self.gateway.current_version)
        if self.gateway.versions[version]['ensemble_memory'].get('memory_snapshot'):
            source_capacity=self.gateway.versions[version]['ensemble_memory'].get('memory_source_capacity',False)
            source_limits=self.gateway.versions[version]['ensemble_memory'].get('memory_source_limits',True)
            if self.gateway.versions[version]['ensemble_memory'].get('memory_policy'):
                needed=not compacted and memory_policy.needed(state,actor,token_budget=bool(self.gateway.versions[version]['ensemble_memory'].get('memory_token_budget')),
                    text_budget=self.gateway.versions[version]['ensemble_memory'].get('memory_character_budget'),
                    entry_trigger=self.gateway.versions[version]['ensemble_memory'].get('memory_entry_trigger'))
            else:
                current=memory_policy.stats(state['memory'][actor])
                relaxed=compacted and (current['entries']>memory_entries.COMPACT_MAX_ENTRIES or current['text_characters']>memory_entries.COMPACT_MAX_TEXT)
                needed=not relaxed and memory_entries.needs_compaction(state['memory'][actor],source_capacity and source_limits)
            if needed:
                self.summarize_chunk(state,actor,call,len(state['observations'][actor]))
                compacted=True
        return compacted

    def summarize_chunk(self,state,actor,call,end,*,headroom_recovery=False):
        data=w.context(state,actor)
        data['observations']=deepcopy(state['observations'][actor][state['memory'][actor]['checkpoint']:end])
        version=getattr(call,'prefix_version',self.gateway.current_version)
        entry_limit=self.gateway.versions[version]['ensemble_memory'].get('memory_snapshot_max_entries')
        if headroom_recovery:
            from .memory_headroom import MAX_SUMMARY_ENTRIES
            entry_limit=MAX_SUMMARY_ENTRIES
            data['_memory_snapshot_max_entries']=entry_limit
        policy=bool(self.gateway.versions[version]['ensemble_memory'].get('memory_policy'))
        token_budget=bool(self.gateway.versions[version]['ensemble_memory'].get('memory_token_budget'))
        text_budget=self.gateway.versions[version]['ensemble_memory'].get('memory_character_budget')
        before=memory_policy.stats(state['memory'][actor]) if policy else None
        if policy:data['memory_maintenance']=memory_policy.context(state,actor,token_budget=token_budget,text_budget=text_budget)
        if self.gateway.versions[version]['ensemble_memory'].get('context_version',1)>=2:context.project(state,actor,data)
        if self.gateway.versions[version]['ensemble_memory'].get('exploration_version'):context.investigation_state(state,actor,data)
        if self.gateway.versions[version]['ensemble_memory'].get('source_integrity_version'):
            from . import source_provenance, temporal_facts
            data['source_provenance']=source_provenance.for_role(state,actor,data)
            data['temporal_facts']=temporal_facts.for_role(state,actor)
        # Older received requests can still appear in focus or sourced memory
        # after leaving the recent 24-observation window. They remain this role's
        # legitimate knowledge; other roles' observations never enter this set.
        allowed={o['id'] for o in state['observations'][actor]}|set(state['memory'][actor]['sources'])|set(state['known'][actor])|set(state['case']['roles'][actor]['knows'])
        if self.gateway.versions[version]['ensemble_memory'].get('compact_context'):
            supplied={o['id'] for o in data['observations']}
            snapshot=self.gateway.versions[version]['ensemble_memory'].get('memory_snapshot',False)
            source_capacity=self.gateway.versions[version]['ensemble_memory'].get('memory_source_capacity',False)
            if snapshot:data['memory_output']='entries_snapshot'
            def patch(out):
                if not snapshot:
                    return memory_entries.required_fields(out,('memory_update',),'memory output fields')['memory_update']
                out=memory_entries.required_fields(out,('entries','processed_through'),'compaction requires entries and processed_through')
                if not isinstance(out['entries'],list):
                    raise ValueError('compaction requires entries and processed_through')
                out['entries']=[memory_entries.required_fields(row,memory_entries.ENTRY_FIELDS,'memory entry fields') for row in out['entries']]
                options={'entry_limit':entry_limit} if entry_limit is not None else {}
                memory_entries.validate_snapshot(out['entries'],source_capacity,**options)
                kept={r['id'] for r in out['entries']}
                return {'upsert':out['entries'],'archive':[r['id'] for r in memory_entries.entries(state['memory'][actor]) if r['id'] not in kept],
                        'processed_through':out['processed_through']}
            def validate_entries(out):
                update=patch(out)
                if update is None:raise ValueError('compaction must process pending observations')
                try:memory_entries.revised(state,actor,update,supplied,end)
                except memory_entries.EntrySourcesError as exc:raise exc.with_context(data)
            stage=('memory_headroom_' if headroom_recovery else 'memory_')+actor+'_'+str(end)
            if self.gateway.versions[version]['ensemble_memory'].get('bounded_context'):
                from . import source_access
                out,_=source_access.memory_decision(state,actor,call,stage,w.baseline(state,actor),data,validate_entries)
            else:out,_=call(stage,'ensemble_memory',w.baseline(state,actor),data,validate_entries,actor)
            memory_entries.apply(state,actor,patch(out),supplied,end)
            if policy:memory_policy.record(state,actor,before,token_budget=token_budget,text_budget=text_budget)
            return
        def validate(out):text(out['summary'],1200);references(out['sources'],allowed,maximum=None)
        out,_=call('memory_'+actor+'_'+str(end),'ensemble_memory',w.baseline(state,actor),data,validate,actor)
        state['memory'][actor]={'summary':out['summary'],'sources':out['sources'],'checkpoint':end}

    def configure_rules(self,state,call):
        version=getattr(call,'prefix_version',self.gateway.current_version)
        for flag in ('source_integrity_version','structured_conclusion_version','workflow_events_version','event_basis_version','event_contract_version','message_wait_guard_version','area_evidence_version'):
            if self.gateway.versions[version]['ensemble_role'].get(flag):state[flag]=1
        if self.gateway.versions[version]['ensemble_role'].get('wait_lifecycle_version'):
            scheduling.wait_lifecycle.configure(state)
        if self.gateway.versions[version]['ensemble_role'].get('communication_version'):
            state['communication_version']=1
            w.reconcile_communication(state)
        if self.gateway.versions[version]['ensemble_role'].get('presence_version'):
            state['presence_version']=1
        if self.gateway.versions[version]['ensemble_role'].get('compact_context'):
            state['action_feedback_version']=1
        if self.gateway.versions[version]['ensemble_role'].get('evidence_sharing_version'):
            state['evidence_sharing_version']=1
        if self.gateway.versions[version]['ensemble_role'].get('exploration_version'):
            state['exploration_version']=1
        if self.gateway.versions[version]['ensemble_role'].get('context_version',1)>=7:state['interaction_version']=2
        if self.gateway.versions[version]['ensemble_role'].get('event_driven',False) and not scheduling.enabled(state):
            state.update(scheduling_version=1,role_waits={},wake_cursors={a:len(state['observations'][a]) for a in w.ACTORS})
            if state['phase']=='active':
                for a in w.ai_roles(state):
                    if a not in state['submissions']:w.enqueue(state,a,'根据已经收到的信息决定继续行动或等待事件。')
        if self.gateway.versions[version]['ensemble_role'].get('custom_events',False):state['scheduling_version']=2

    def turn(self,state,actor,call,depth,reason=None,_context_retry=False):
        self.configure_rules(state,call)
        version=getattr(call,'prefix_version',self.gateway.current_version)
        scheduled=self.gateway.versions[version]['ensemble_role'].get('event_driven',False)
        custom_events=self.gateway.versions[version]['ensemble_role'].get('custom_events',False)
        if scheduled:state['agenda']=[q for q in state['agenda'] if q['actor']!=actor]
        compacted=self.compact(state,actor,call) if not _context_retry else False
        if actor in getattr(call,'memory_headroom_recovery',()):
            from .memory_headroom import MAX_SUMMARY_ENTRIES
            if len(memory_entries.entries(state['memory'][actor]))>MAX_SUMMARY_ENTRIES:
                self.summarize_chunk(state,actor,call,len(state['observations'][actor]),headroom_recovery=True)
                compacted=True
        data=w.context(state,actor);choices={x['id'] for x in data['choices']}
        self.conversation_context(state,actor,data,call,'ensemble_role')
        version=getattr(call,'prefix_version',self.gateway.current_version)
        focused=self.gateway.versions[version]['ensemble_role'].get('context_version',1)>=3
        collective=self.gateway.versions[version]['ensemble_role'].get('context_version',1)>=4
        received_progress=self.gateway.versions[version]['ensemble_role'].get('progress_sources_version',1)>=2
        grounded=self.gateway.versions[version]['ensemble_role'].get('context_version',1)>=7
        independent_final=self.gateway.versions[version]['ensemble_role'].get('context_version',1)>=10
        specialized=self.gateway.versions[version]['ensemble_role'].get('context_version',1)>=11
        optimized=bool(self.gateway.versions[version]['ensemble_role'].get('compact_context'))
        mode=w.perspective(state,actor) if specialized else None
        concealment=mode=='concealment'
        baseline=w.baseline(state,actor)
        if specialized:
            baseline['decision_mode']=mode;data['decision_mode']=mode
        if scheduled:data['scheduling']=scheduling.context(state,actor,
            limit_waits=self.gateway.versions[version]['ensemble_role'].get('wait_frequency_version',0),
            explicit_options=bool(self.gateway.versions[version]['ensemble_role'].get('role_recovery_version')),
            own_action_completion=bool(self.gateway.versions[version]['ensemble_role'].get('own_action_completion')),
            message_wait_guard=bool(self.gateway.versions[version]['ensemble_role'].get('message_wait_guard_version')))
        if custom_events:data['event_tracking']=role_events.role_context(state,actor)
        if self.gateway.versions[version]['ensemble_role'].get('submission_only',False) and state.get('closure',{}).get('ready'):
            data['choices']=[c for c in data['choices'] if c['id']=='lock_conclusion']
            choices={c['id'] for c in data['choices']}
        if concealment:
            data.pop('belief')
            data['strategy']=deepcopy(state.get('strategies',{}).get(actor))
        if grounded:
            context_version=self.gateway.versions[version]['ensemble_role'].get('context_version',1)
            context.project(state,actor,data,concise=context_version>=8,receipts=context_version>=9)
        if self.gateway.versions[version]['ensemble_role'].get('dialogue_focus_version'):
            data['dialogue_focus']=context.dialogue_focus(state,actor,
                self.gateway.versions[version]['ensemble_role']['dialogue_focus_version'])
        if focused:data['focus']=w.decision_focus(state,actor,reason,
            sharing=bool(self.gateway.versions[version]['ensemble_role'].get('evidence_sharing_version')),
            witnessed=bool(self.gateway.versions[version]['ensemble_role'].get('exploration_version')))
        if self.gateway.versions[version]['ensemble_role'].get('context_version',1)>=5:
            data['focus']['recent_decisions']=[deepcopy(d) for d in state.get('decisions',[]) if d['actor']==actor][-5:]
            data['focus']['available_unread_records']=[c for c in data['choices'] if c['id'].startswith('inspect:')]
            if self.gateway.versions[version]['ensemble_role'].get('context_version',1)>=6:
                data['focus']['recent_decisions']=[{'action':d['label']} for d in data['focus']['recent_decisions']]
        if self.gateway.versions[version]['ensemble_role'].get('exploration_version'):
            context.investigation_state(state,actor,data,
                exhaustion=bool(self.gateway.versions[version]['ensemble_role'].get('area_evidence_version')))
            data['focus']['currently_accessible_unread_records']=data['focus'].pop('available_unread_records')
        if collective:
            closure=state.get('closure',{'votes':[],'ready':False})
            acquired={o['event_id'] for o in state['observations'][actor]};agreements={}
            for e in state['events']:
                if e['kind']=='closure_vote' and e['id'] in acquired:agreements[e['actor']]=e['facts']['agreed']
            data['closure']={'ready':closure['ready'],'own_agreement':actor in closure['votes'],
                             'known_agreements':agreements,'required_agreements':3}
            if closure['ready']:data.update(must_speak=False,must_respond=False)
        if grounded:
            data['conclusion_task']={'final':bool(state.get('closure',{}).get('ready')),
                'dimensions':['identity','time','method'] if state['scenario']=='murder' else [],
                'instruction':'独立整理已有判断：谁因何能实施、死亡时间的上下界、实际手法及误导。明确列出每一步实际使用的材料和听到的证言；不必等口供，也不要把尚待核实的说法当事实。证据不足时说明具体缺口。'}
            if concealment:
                data['conclusion_task']={'final':data['conclusion_task']['final'],
                    'instruction':'选择服务自己目标的对外结案立场。私下已知的作案经历不需要重新推断，也不应自动成为对外指认；结合已收到的质疑和材料决定如何回应。'}
        if optimized:
            data['context_format']=1
            compact_context.recall(state,actor,data)
            data['action_feedback']=action_feedback.for_role(state,actor)
        if self.gateway.versions[version]['ensemble_role'].get('bounded_context'):
            data['source_access']={'version':1}
        if self.gateway.versions[version]['ensemble_role'].get('memory_policy'):
            data['memory_maintenance']=memory_policy.context(state,actor,token_budget=bool(self.gateway.versions[version]['ensemble_role'].get('memory_token_budget')),
                text_budget=self.gateway.versions[version]['ensemble_role'].get('memory_character_budget'))
        if self.gateway.versions[version]['ensemble_role'].get('source_integrity_version'):
            from . import source_provenance, temporal_facts
            data['source_provenance']=source_provenance.for_role(state,actor,data)
            data['temporal_facts']=temporal_facts.for_role(state,actor)
        if self.gateway.versions[version]['ensemble_role'].get('structured_conclusion_version') and state['scenario']=='murder':
            from . import final_arguments
            data['conclusion_task']['dimensions']=final_arguments.dimensions(state['case'])
            data['conclusion_task']['submission_format']='per_aspect'
        if self.gateway.versions[version]['ensemble_role'].get('workflow_events_version'):
            from . import workflow_events
            data['workflow']=workflow_events.context(state,actor)
        economy=bool(self.gateway.versions[version]['ensemble_role'].get('context_economy'))
        if economy:
            from . import context_economy, delta_updates
            loop=context_economy.loop_context(state,actor)
            if loop:data['decision_loop']=loop
            if not data.get('conclusion_task',{}).get('final'):
                data.pop('conclusion_task',None)
        reminder_ticket=None
        if self.gateway.versions[version]['ensemble_role'].get('investigation_reminder_version'):
            reminder_ticket=investigation_reminders.prepare(state,actor,data)
            if reminder_ticket['reminder'] is not None:
                data['investigation_reminder']=reminder_ticket['reminder']
        if self.gateway.versions[version]['ensemble_role'].get('memory_policy') and not compacted and not _context_retry:
            pressure=False
            try:
                payload,_=self.gateway.payload('ensemble_role',baseline,data,version)
                size=request_sizes(payload,2)
                pressure=size['dynamic_bytes']>=MAX_DYNAMIC_CONTEXT_BYTES*.9 or size['total_bytes']>=MAX_REQUEST_BYTES*.9
            except StoreError as exc:
                if exc.code!='context_budget':raise
                pressure=True
            if pressure and memory_policy.needed(state,actor,context_pressure=True,token_budget=bool(self.gateway.versions[version]['ensemble_role'].get('memory_token_budget')),
                    text_budget=self.gateway.versions[version]['ensemble_role'].get('memory_character_budget'),
                    entry_trigger=self.gateway.versions[version]['ensemble_role'].get('memory_entry_trigger')):
                self.summarize_chunk(state,actor,call,len(state['observations'][actor]))
                return self.turn(state,actor,call,depth,reason,_context_retry=True)
        # Actual acquisition remains valid after a message leaves the recent window.
        allowed={o['id'] for o in state['observations'][actor]}|set(state['memory'][actor]['sources'])|set(state['known'][actor])|set(state['case']['roles'][actor]['knows'])
        heard_sources={o['id'] for o in state['observations'][actor] if o['kind']=='testimony'}
        source_kinds={o['id']:o['kind'] for o in state['observations'][actor]}
        source_kinds.update({i:'initial_fact' for i in state['case']['roles'][actor]['knows']})
        source_kinds.update({i:'acquired_record' for i in state['known'][actor]})
        def validation_steps(out):
            yield 'decision_shape'
            # Check perspective permissions before parsing an inapplicable patch.
            if optimized and isinstance(out,dict) and ('belief_update' if concealment else 'strategy_update') in out:
                key='strategy_update' if concealment else 'belief_update'
                output_contracts.object_fields(out,{'action','speech','gesture','question_to','memory_update',key,
                    'relationships','progress','final_conclusion','next_decision','cancel_events'},'response',required=(key,))
            if economy:out=delta_updates.expand(state,actor,out)
            if optimized:out=memory_entries.decision(state,actor,out,data)
            yield 'action'
            if out['choice'] not in choices:
                if economy:raise delta_updates.ContractError('action','Select one exact kind/argument tuple from actions; do not invent a talk action. Speech is the separate speech field.')
                raise ValueError('role choice')
            yield 'event_tracking'
            if custom_events:role_events.validate(out,data['event_tracking'])
            yield 'next_decision'
            if scheduled:scheduling.validate(out.get('next_decision'),data['scheduling'],out['choice'],custom_events and out.get('event_request') is not None,
                speech=out.get('speech'),gesture=out.get('gesture'))
            yield 'speech'
            output_contracts.text(out['speech'],'speech',1200,True)
            # Incremental memory has already passed the sourced-entry validator.
            if not optimized:text(out['memory'],1000)
            references(out['memory_sources'],allowed,maximum=None)
            if out.get('gesture') not in (None,'点头','摇头','示意稍后回答'):raise ValueError('gesture')
            leaving_private=scheduled and out['choice']=='end_private' and w.chat_for(state,actor)
            if not leaving_private and (data['must_speak'] or (data['must_respond'] and not out.get('gesture'))) and not out['speech'].strip():raise ValueError('missing required speech')
            if out.get('question_to') not in (None,*w.ACTORS):raise ValueError('question target')
            yield 'interpretation'
            if concealment:
                output_contracts.text(out['situation'],'strategy_update.situation',1200,True)
                output_contracts.text(out['strategy'],'strategy_update.plan',1200,True)
                output_contracts.references(out['assessment_sources'],allowed,'strategy_update.sources',source_kinds=source_kinds)
            else:
                if out['suspect'] not in (None,*w.ACTORS):raise ValueError('belief')
                if focused:output_contracts.text(out['reasoning'],'belief_update.explanation',1800,True)
                output_contracts.references(out['evidence_ids'],set(state['known'][actor]),'belief_update.evidence_ids',{'belief_update.testimony_ids':heard_sources},
                    source_kinds=source_kinds,expected_kinds=('acquired_record',))
            if grounded:
                heard=out.get('testimony_ids',[])
                output_contracts.references(heard,heard_sources,'belief_update.testimony_ids',{'belief_update.evidence_ids':set(state['known'][actor])},
                    source_kinds=source_kinds,expected_kinds=('testimony',))
            yield 'final_conclusion'
            if independent_final and out['choice']=='lock_conclusion':
                final=out['final_conclusion']
                if not isinstance(final,dict) or final.get('suspect') not in (None,*w.ACTORS):raise ValueError('final conclusion')
                output_contracts.text(final['explanation'],'final_conclusion.explanation',6000 if 'aspects' in final else 1800,True)
                output_contracts.references(final['evidence_ids'],set(state['known'][actor]),'final_conclusion.evidence_ids',
                    {'final_conclusion.testimony_ids':heard_sources},source_kinds=source_kinds,expected_kinds=('acquired_record',))
                output_contracts.references(final['testimony_ids'],heard_sources,'final_conclusion.testimony_ids',
                    {'final_conclusion.evidence_ids':set(state['known'][actor])},source_kinds=source_kinds,expected_kinds=('testimony',))
            yield 'progress'
            if collective and 'progress' in out:
                progress=out['progress']
                if progress.get('kind') not in ('none','deduction','answer'):raise ValueError('progress kind')
                output_contracts.references(progress.get('sources'),allowed if received_progress else set(state['known'][actor])|set(state['case']['roles'][actor]['knows']),'progress.sources',source_kinds=source_kinds)
            yield 'relationships'
            if not isinstance(out['relationships'],list) or len(out['relationships'])>3:raise ValueError('relationships')
            for index,r in enumerate(out['relationships']):
                if r['target'] not in state['relationships'][actor]:raise ValueError('relationship target')
                for k in ('trust_delta','affinity_delta'):
                    if type(r[k]) not in (int,float) or not -.2<=r[k]<=.2:raise ValueError('relationship change')
                output_contracts.text(r['reason'],f'relationships[{index}].reason',500)
                output_contracts.references(r['sources'],allowed,f'relationships[{index}].sources',source_kinds=source_kinds)
                if not r['sources']:raise ValueError('relationship requires an acquired source')
        def validate(out):
            from . import role_recovery
            role_recovery.validate_steps(validation_steps(out))
        if self.gateway.versions[version]['ensemble_role'].get('native_event_tools',False):
            out,cid=event_tools.decide(state,actor,call,baseline,data,validate,allowed)
        else:out,cid=call('role_'+actor,'ensemble_role',baseline,data,validate,actor)
        raw=delta_updates.expand(state,actor,out) if economy else out
        if optimized:out=memory_entries.decision(state,actor,raw,data)
        if self.gateway.versions[version]['ensemble_role'].get('context_version',1)>=5:
            state.setdefault('decisions',[]).append({'actor':actor,'choice':out['choice'],
                'label':next(c['label'] for c in data['choices'] if c['id']==out['choice']),'call_id':cid})
        if optimized:memory_entries.apply(state,actor,raw['memory_update'],{o['id'] for o in data['observations']})
        else:state['memory'][actor]={'summary':out['memory'],'sources':out['memory_sources'],'checkpoint':len(state['observations'][actor])}
        if concealment:
            if not optimized or raw['strategy_update'] is not None:
                state.setdefault('strategies',{})[actor]={'situation':out['situation'],'plan':out['strategy'],'sources':out['assessment_sources']}
            state['beliefs'][actor]=None
        else:
            if not optimized or raw['belief_update'] is not None:
                state['beliefs'][actor]={'suspect':out['suspect'],'evidence_ids':out['evidence_ids'],'explanation':out['reasoning'] if focused else out['speech']}
                if grounded:state['beliefs'][actor]['testimony_ids']=out.get('testimony_ids',[])
        if collective:state.setdefault('grounded_progress',{})[actor]=deepcopy(out.get('progress',{'kind':'none','sources':[]}))
        for r in out['relationships']:self.relationship(state,actor,r,cid)
        start=len(state['events'])
        action_event=None
        if out['speech']:action_event=w.speak(state,actor,out['speech'],out.get('question_to'),depth=depth,allow_unheard=True)
        elif out.get('gesture'):action_event=w.speak(state,actor,out['gesture'],out.get('question_to'),gesture=True,depth=depth,allow_unheard=True)
        if out['choice']!='wait':
            final=out['final_conclusion'] if independent_final and out['choice']=='lock_conclusion' else None
            action_event=w.apply_choice(state,actor,out['choice'],spoken=focused and bool(out['speech']),conclusion=final)
        for e in state['events'][start:]:e['facts']['decision_call_id']=cid
        if scheduled:
            proposed=role_events.request(state,actor,out) if custom_events else None
            scheduling.reconcile(state)
            scheduling.record_reply(state,actor,out['next_decision'],data['scheduling'],out['choice'],out['speech'],out.get('gesture'))
            scheduling.commit(state,actor,out['next_decision'],data['scheduling'],proposed,action_event=action_event)
        if reminder_ticket is not None:investigation_reminders.commit(state,actor,reminder_ticket)

    def conversation_context(self,state,actor,data,call,task):
        # Additions to dynamic context are versioned too: older completed stages
        # must retain their original payload hashes when an operation resumes.
        version=getattr(call,'prefix_version',self.gateway.current_version)
        if self.gateway.versions[version][task].get('context_version',1)<2:return
        listeners=[a for a in w.audience(state,actor) if a!=actor]
        data['conversation']={'channel':w.channel(state,actor),
            'listeners':{a:w.name(state,a) for a in listeners},
            'unavailable_addressees':{a:w.name(state,a) for a in w.ACTORS if a!=actor and a not in listeners}}
        if self.gateway.versions[version][task].get('local_communication'):
            data['conversation'].update(area=state['locations'][actor],reach='same_area_only',speech_before_move=True)
        if self.gateway.versions[version][task].get('presence_version'):
            data['conversation']['presence']=w.scene_presence(state,actor)

    def adjudicate_ensemble(self,state,start,call):
        version=getattr(call,'prefix_version',self.gateway.current_version)
        expressive=self.gateway.versions[version]['ensemble_dm'].get('cue_version',1)>=2
        custom_events=self.gateway.versions[version]['ensemble_dm'].get('custom_events',False)
        event_spec=self.gateway.versions[version]['ensemble_dm']
        utterances=[e for e in state['events'][start:] if e['kind']=='testimony']
        scopes={e['facts']['channel'] for e in utterances}
        if custom_events:scopes|=role_events.scopes_due(state)
        for scope in sorted(scopes):
            speeches=[e for e in utterances if e['facts']['channel']==scope];indexed={e['id']:e for e in speeches}
            participants=set().union(*(set(e['facts']['recipients']) for e in speeches))
            if custom_events:
                tracked,received,allowed_event_sources=role_events.package(state,scope,
                    selective=bool(event_spec.get('context_economy')),
                    background=bool(event_spec.get('event_background_version')))
                participants.update(received)
            baseline={'scope':scope,'history':state['case']['history'],'initial_knowledge':{a:w.baseline(state,a) for a in participants}}
            if scope!='public':baseline={'scope':scope,'history':state['case']['history'],'initial_knowledge':state['chats'][scope]['baseline']}
            relevant_ids={o['event_id'] for e in speeches for o in e['facts']['speaker_knowledge']['observations']}
            relevant=[e for e in state['events'] if e['id'] in relevant_ids and e['kind']!='testimony'][-16:]
            data={'utterances':speeches,'recent_actual_events':relevant,
                  'private_history':state['chats'][scope]['turns'][-8:] if scope!='public' else []}
            disclosure_sources=output_contracts.disclosure_sources(state,speeches)
            if event_spec.get('disclosure_source_version'):
                data['disclosure_sources']=disclosure_sources
            if self.gateway.versions[version]['ensemble_dm'].get('context_version',1)>=2:
                data['new_utterance_ids']=list(indexed)
            if self.gateway.versions[version]['ensemble_dm'].get('context_version',1)>=3:
                data['recent_delivery']=context.recent_delivery(state,speeches,scope)
            if custom_events and event_spec.get('event_source_view_version'):
                hints={e['id'] for e in relevant}|set(indexed)
                package=(tracked,received,allowed_event_sources)
                extra=role_events.additional_background(state,package,{actor:hints for actor in received})
                tracked,received,allowed_event_sources=role_events.merge_background(package,extra,True)
            if custom_events:data.update(tracked_events=tracked,event_recipient_contexts=received)
            upgrade=None
            if custom_events and event_spec.get('context_economy') and not event_spec.get('event_background_version'):
                upgrade=role_events.package(state,scope,True,True)
                data['_event_review_upgrade']={'tracked_events':upgrade[0],'event_recipient_contexts':upgrade[1]}
            review_records,review_allowed=(tracked,allowed_event_sources) if custom_events else ([],{})
            def prepare_request(feedback):
                nonlocal review_records,review_allowed
                package=upgrade if upgrade and (feedback or {}).get('event_context_repair') else (tracked,received,allowed_event_sources)
                prepared=role_events.checked_background(state,package,feedback)
                review_records,review_allowed=prepared[0],prepared[2]
            def validate(out):
                if not all(isinstance(out.get(k),list) for k in ('assessments','cues','disclosures')):raise ValueError('DM arrays')
                for a in out['assessments']:
                    if a['event_id'] not in indexed or a['verdict'] not in ('supported','known_contradiction','mistaken','uncertain'):raise ValueError('assessment')
                if len(out['cues'])>(len(indexed) if expressive else 2):raise ValueError('cue cap')
                cued=set()
                for cue in out['cues']:
                    if cue['event_id'] not in indexed:raise ValueError('cue event')
                    if expressive:
                        if cue['event_id'] in cued or cue.get('modality') not in ('audible','visible'):raise ValueError('cue')
                        text(cue.get('text'),160)
                        cued.add(cue['event_id'])
                    elif cue['cue'] not in ('pause','gaze'):raise ValueError('cue')
                for index,d in enumerate(out['disclosures']):
                    if d['event_id'] not in indexed:raise ValueError('disclosure event')
                    allowed=disclosure_sources[d['event_id']]
                    if d['evidence_id'] not in allowed:raise output_contracts.DisclosureError(index,d['event_id'],allowed)
                if custom_events:
                    try:role_events.validate_decisions(out,review_records,review_allowed)
                    except role_events.EventDecisionError as exc:
                        if upgrade and isinstance(exc,role_events.EventSourceError):
                            exc.feedback=role_events.source_retry_feedback(exc.feedback,upgrade)
                        if isinstance(exc,role_events.EventSourceError):
                            package=upgrade if upgrade else (tracked,received,allowed_event_sources)
                            exc.feedback=role_events.source_background_feedback(state,package,exc.feedback)
                        if self.gateway.versions[version]['ensemble_dm'].get('context_economy'):
                            from . import dm_repairs
                            dm_repairs.attach(exc,out,review_records,review_allowed)
                        raise
            if custom_events:validate.prepare_request=prepare_request
            out,cid=call('dm_'+scope,'ensemble_dm',baseline,data,validate)
            state['assessments'].append({'call_id':cid,'channel':scope,**out})
            if custom_events:role_events.apply(state,out['event_decisions'],cid,
                {r['id']:r['review_range']['through'] for r in tracked if 'review_range' in r})
            for d in out['disclosures']:
                source=d['evidence_id'];definition=w.definition(state,source)
                exposed=[source,*((definition or {}).get('reveals',[]))]
                if source.startswith('secret_'):exposed.append('s'+source.removeprefix('secret_'))
                for record in exposed:
                    disclosure={**d,'evidence_id':record,'channel':scope}
                    speech=indexed[d['event_id']]
                    if 'room' in speech['facts']:
                        disclosure['public_received']=any(a!=speech['actor'] for a in speech['facts']['recipients'])
                    state['disclosures'].append(disclosure)
                    if w.public_disclosure(disclosure):w.publish_contribution(state,speech['actor'],record)
            for cue in out['cues']:
                speech=indexed[cue['event_id']];actor=speech['actor'];e=w.emit(state,'cue',actor,source=speech['id'],call_id=cid)
                visible=cue['modality']=='visible' if expressive else cue['cue']=='gaze'
                words=cue['text'] if expressive else w.name(state,actor)+('停顿了一下。' if cue['cue']=='pause' else '移开了视线。')
                for recipient in speech['facts']['recipients']:
                    if visible and speech['facts']['locations'][recipient]!=speech['facts']['locations'][actor]:continue
                    w.note(state,recipient,e,words,'cue')

    def conclude_ensemble(self,state,call):
        evaluations={}
        if state['scenario']=='murder':
            version=getattr(call,'prefix_version',self.gateway.current_version)
            role_reviews=self.gateway.versions[version].get('ensemble_theory',{}).get('role_review_version',0)>=2
            order=sorted(w.ACTORS,key=lambda a:w.perspective(state,a)=='concealment') if role_reviews else w.ACTORS
            for a in order:
                submission=state['submissions'].get(a) or state['beliefs'].get(a) or {}
                version=getattr(call,'prefix_version',self.gateway.current_version)
                if role_reviews and w.perspective(state,a)=='concealment':
                    from . import ensemble_position_review
                    evaluations[a]=ensemble_position_review.evaluate(state,a,call,evaluations)
                    continue
                if self.gateway.versions[version].get('ensemble_theory',{}).get('review_version',0)>=1:
                    evaluations[a]=ensemble_review.evaluate(state,a,call)
                    continue
                if self.gateway.versions[version]['ensemble_role'].get('context_version',1)>=11 and w.perspective(state,a)=='concealment':
                    # A historical private self-identification is not a chosen
                    # accusation. Grade only an actual submitted position.
                    submission=state['submissions'].get(a) or {}
                explanation=submission.get('explanation','');ids=submission.get('evidence_ids',[]);suspect=submission.get('suspect')
                theory_task='ensemble_theory' if 'ensemble_theory' in self.gateway.versions[version] else 'case_theory'
                with_testimony=self.gateway.versions[version]['case_theory'].get('context_version',1)>=3
                heard=submission.get('testimony_ids',[]) if with_testimony else []
                established=[]
                if explanation and suspect:
                    def validate(out):
                        if not isinstance(out['claims'],list) or len(out['claims'])>9:raise ValueError('claims')
                        for c in out['claims']:
                            if c['aspect'] not in ('identity','time','method') or type(c['supported']) is not bool:raise ValueError('claim')
                            if theory_task=='case_theory' and (not c['quote'] or c['quote'] not in explanation):raise ValueError('invented argument')
                            references(c['evidence_ids'],set(ids)|set(heard))
                        if self.gateway.versions[version]['case_theory'].get('context_version',1)>=4:
                            references(out['argument_sources'],set(ids)|set(heard))
                    # A connected argument can cite the time boundary in its time
                    # paragraph and reuse it in the identity paragraph. Each
                    # aspect still needs its own actually supported claim.
                    version=getattr(call,'prefix_version',self.gateway.current_version)
                    theory_data={'submitted_suspect':suspect,'explanation':explanation,
                        'cited_evidence':[state['known'][a][cid] for cid in ids], 'solution':state['case']['solution']}
                    if self.gateway.versions[version]['case_theory'].get('context_version',1)>=2:
                        theory_data['proof_routes']={aspect:[route for route in routes if set(route)<=set(ids)] for aspect,routes in state['case']['proofs'].items()}
                    if with_testimony:theory_data['cited_testimony']=context.testimony(state,a,heard)
                    out,_=call('theory_'+a,theory_task,None,theory_data,validate,a)
                    connected=self.gateway.versions[version]['ensemble_role'].get('context_version',1)>=3
                    support={cid for c in out['claims'] if c['supported'] for cid in c['evidence_ids']}
                    if self.gateway.versions[version]['case_theory'].get('context_version',1)>=4:
                        support=set(out['argument_sources'])
                    for aspect,routes in state['case']['proofs'].items():
                        used=support if connected else {cid for c in out['claims'] if c['aspect']==aspect and c['supported'] for cid in c['evidence_ids']}
                        if any(c['aspect']==aspect and c['supported'] for c in out['claims']) and any(set(route)<=used for route in routes):established.append(aspect)
                result='unresolved' if not suspect else 'incorrect' if suspect!=state['case']['solution']['killer'] else 'established' if len(established)==3 else 'unproven'
                evaluations[a]={'result':result,'established':established,'suspect':suspect}
        version=getattr(call,'prefix_version',self.gateway.current_version)
        isolated=self.gateway.versions[version].get('ensemble_theory',{}).get('admission_isolation',False)
        state['results']=w.results(state,evaluations,isolate_admission=isolated)
        ensemble_review.attach_process(state)
        state['outcome']='established' if state['results']['shared_success'] else 'partial' if any(p['primary'] for p in state['results']['participants'].values()) else 'unresolved'
        def validate(out):text(out['title'],100);text(out['narrative'],3000)
        ending_data={'scenario':state['scenario'],'solution':state['case']['solution'],
            'results':state['results'],'history':state['case']['history'],'actual_events':[e for e in state['events'][-30:] if e['kind']!='testimony'],
            'relationships':state['relationships']}
        version=getattr(call,'prefix_version',self.gateway.current_version)
        if self.gateway.versions[version]['ensemble_ending'].get('context_version',1)>=2:
            ending_data.pop('results');ending_data['closure']={'truth_established':state['results']['shared_success']}
        if self.gateway.versions[version]['ensemble_ending'].get('context_version',1)>=3:
            ending_data['public_dialogue']=[{'speaker':w.name(state,e['actor']),'text':e['facts']['text']}
                for e in state['events'] if e['kind']=='testimony' and e['facts']['channel']=='public'][-8:]
        if self.gateway.versions[version]['ensemble_ending'].get('context_version',1)>=4:
            for relations in ending_data['relationships'].values():
                for r in relations.values():r['experiences']=r['experiences'][-3:]
        if self.gateway.versions[version]['ensemble_ending'].get('source_integrity_version'):
            from . import temporal_facts
            ending_data['temporal_facts']=temporal_facts.project(state['case']['history']+state['case']['clues'])
        out,_=call('ending','ensemble_ending',None,ending_data,validate)
        state['ending']=out;state['phase']='ended';state['agenda']=[]
        if scheduling.enabled(state):role_events.end_story(state)
        for c in state['chats'].values():
            if c['status']=='active':w.close_chat(state,c)
        w.emit(state,'ended',outcome=state['outcome'])

    def background(self,state,call):
        self.configure_rules(state,call)
        if 'watch' in state:return spectator.background(self,state,call)
        if state['phase']=='reading':
            if state['reading_deadline'] is not None and w.now(state)>=state['reading_deadline']:w.start(state)
            return
        if state['phase']!='active':return
        w.expire(state);scheduling.reconcile(state);start=len(state['events'])
        if scheduling.enabled(state) and w.now(state)>=state['next_tick'] and any(t['status']=='running' for t in state['activities']):
            w.advance(state)
        elif state['agenda'] and not (scheduling.enabled(state) and state['world_due']):
            q=state['agenda'].pop(0)
            if q['channel']==w.channel(state,q['actor']) and q['actor'] not in state['submissions'] and (q['actor'] not in state['evacuated'] or state.get('closure',{}).get('ready')):self.turn(state,q['actor'],call,q['depth'],q['reason'])
        elif any(t['status']=='running' for t in state['activities']) and not (scheduling.enabled(state) and state['world_due']):w.advance(state)
        elif state['world_due']:
            def validate(out):
                if out['choice'] not in {c['id'] for c in w.world_choices(state)}:raise ValueError('world choice')
            out,cid=call('world','ensemble_world',{'scenario':state['scenario'],'rooms':state['case']['rooms']},
                         {'choices':w.world_choices(state),'beat':state['beat'],'recent_events':[{'kind':e['kind'],'beat':e['beat']} for e in state['events'][-12:]]},validate)
            w.apply_world(state,out['choice'],cid)
        self.adjudicate_ensemble(state,start,call);w.expire(state)
        scheduling.reconcile(state)
        state['background_error']=None

    def pump(self,gid,force=False):
        with self.store.transaction(False) as con:
            row=con.execute('SELECT owner,state FROM games WHERE id=?',(gid,)).fetchone()
        if not row:return False
        state=json.loads(row['state']);owner=row['owner']
        if 'watch' in state:return spectator.pump(self,state,owner,force)
        if state.get('gameplay')!='ensemble' or state['archived'] or state['phase'] not in ('reading','active') or state['background_error']:return False
        if not force and time.time()-self._seen.get(gid,0)>60:return False
        due=state['phase']=='reading' and state['reading_deadline'] is not None and time.time()>=state['reading_deadline']
        due|=state['phase']=='active' and (bool(state['agenda']) or state['world_due'] or (time.time()>=state['next_tick'] and any(t['status']=='running' for t in state['activities'])) or any(c['status']=='active' and time.time()>=c['expires'] for c in state['chats'].values()) or (scheduling.enabled(state) and any(i['status']=='pending' and time.time()>=i['expires'] for i in state['invitations'])))
        due|=state['phase']=='active' and bool(role_events.scopes_due(state))
        if state['phase']=='active' and scheduling.wait_lifecycle.enabled(state):
            deadline=scheduling.next_deadline(state)
            due|=deadline is not None and time.time()>=deadline
        if not due:return False
        command={'command_id':'auto_'+gid[:8]+'_'+str(state['revision']),'expected_revision':state['revision'],'kind':'background','_actor':'system'}
        with self.store.transaction(False) as con:
            recovery=con.execute("SELECT command FROM ai_operations WHERE game_id=? AND status IN ('buffered','interrupted') AND json_extract(command,'$.kind')='background' ORDER BY started LIMIT 1",(gid,)).fetchone()
            if recovery:command=json.loads(recovery['command'])
        try:self.operate(owner,gid,command,self.background)
        except Exception as exc:
            if isinstance(exc,StoreError) and exc.code in ('ai_pending','stale_revision'):return False
            if isinstance(exc,StoreError) and exc.code=='cancelled':return True
            message=str(exc) if isinstance(exc,StoreError) else '后台步骤遇到内部错误，已停止继续调用；可以恢复或取消这一步。'
            with self.store.transaction() as con:
                previous=self.store.load(con,owner,gid);current=deepcopy(previous)
                operation=con.execute('SELECT status FROM ai_operations WHERE game_id=? AND id=?',(gid,command['command_id'])).fetchone()
                if operation and operation['status']=='cancelled':return True
                attempts=con.execute('SELECT MAX(n) FROM (SELECT COUNT(*) n FROM ai_calls WHERE game_id=? AND operation_id=? GROUP BY stage)',(gid,command['command_id'])).fetchone()[0] or 0
                code=getattr(exc,'code','internal_error')
                current['background_error']={'message':message,'operation_id':command['command_id'],'code':code,
                    'retryable':retryable(code)}
                current['revision']+=1;self.store.save(con,current,previous)
            if not isinstance(exc,StoreError):
                import traceback
                traceback.print_exc()
        return True

    def cancel_step(self,owner,gid,command):
        """Cancel only this operation; repeated requests never consume another turn."""
        from .storage import fingerprint
        command_id=self.store.command_id(command.get('command_id'));digest=fingerprint(command)
        with self.store.transaction() as con:
            old=self.store.load(con,owner,gid)
            previous=con.execute('SELECT * FROM commands WHERE game_id=? AND id=?',(gid,command_id)).fetchone()
            if previous:
                if previous['digest']!=digest:raise StoreError('这个操作标识已用于不同内容。',409,'command_conflict')
                return old,{**json.loads(previous['receipt']),'duplicate':True}
            op=con.execute('SELECT * FROM ai_operations WHERE game_id=? AND id=?',(gid,command.get('operation_id'))).fetchone()
            if not op or op['status']=='completed':raise StoreError('这项操作已完成或不存在，不能取消。',409,'invalid_operation')
            if op['status']=='cancelled':return old,{'accepted':True,'code':'cancelled','duplicate':True,'message':'这项操作已经取消。'}
            if old['revision']!=command['expected_revision']:raise StoreError('页面状态已更新，请刷新后再取消。',409,'stale_revision')
            new=deepcopy(old);base=json.loads(op['base_state']);operation=json.loads(op['command'])
            if operation.get('kind')=='background' and base['agenda'] and 'watch' not in new:
                queue_id=base['agenda'][0]['id'];new['agenda']=[q for q in new['agenda'] if q['id']!=queue_id]
            if new.get('background_error',{} ) and new['background_error']['operation_id']==op['id']:new['background_error']=None
            if 'watch' in new and new['watch']['recovery_operation']==op['id']:new['watch']['recovery_operation']=None
            con.execute("UPDATE ai_operations SET status='cancelled' WHERE game_id=? AND id=?",(gid,op['id']))
            new['revision']+=1;self.store.save(con,new,old)
            receipt={'accepted':True,'code':'cancelled','message':'这一步已取消，已保存的进展和调用用量保留。'}
            con.execute('INSERT INTO commands VALUES (?,?,?,?)',(gid,command_id,digest,canonical(receipt)))
        return new,receipt

    def retry_background(self,owner,gid,request=None):
        state=self.store.state(owner,gid)
        request=request or {'command_id':'manual_retry_'+secrets.token_hex(8),'expected_revision':state['revision'],'kind':'retry_ai'}
        identity=self.store.command_id(request['command_id']);digest=fingerprint(request);actor=self.actor(owner,gid)
        with self.store.transaction(False) as con:
            prior=con.execute('SELECT digest,receipt FROM commands WHERE game_id=? AND id=?',(gid,identity)).fetchone()
        if prior:
            if prior['digest']!=digest:raise StoreError('操作标识已用于不同内容。',409,'command_conflict')
            return state,{**json.loads(prior['receipt']),'duplicate':True}
        error=self.view(owner,state)['background_error']
        if not error:raise StoreError('没有待恢复的后台步骤。')
        with self.store.transaction() as con:
            current=self.store.load(con,owner,gid)
            prior=con.execute('SELECT digest,receipt FROM commands WHERE game_id=? AND id=?',(gid,identity)).fetchone()
            if prior:
                if prior['digest']!=digest:raise StoreError('操作标识已用于不同内容。',409,'command_conflict')
                return current,{**json.loads(prior['receipt']),'duplicate':True}
            if current['revision']!=request['expected_revision']:raise StoreError('页面状态已更新。',409,'stale_revision')
            row=con.execute('SELECT command FROM ai_operations WHERE game_id=? AND id=?',(gid,error['operation_id'])).fetchone()
            command=json.loads(row['command'])
            if command.get('kind') in ('background','preview'):
                if actor not in ('A','observer'):raise StoreError('仅房主可恢复共同后台任务。',403,'forbidden')
            elif command.get('_actor', 'observer' if 'watch' in state else 'A')!=actor:
                raise StoreError('只能恢复自己的操作。',403,'forbidden')
            if not error.get('retryable'):raise StoreError('请先处理当前错误，或取消该步骤。',409,error['code'])
            self.gateway.renew_retry(con,gid,error['operation_id'])
            receipt={'accepted':False,'pending':True,'code':'retry_requested','message':'已开始新一轮尝试。'}
            con.execute('INSERT INTO commands VALUES (?,?,?,?)',(gid,identity,digest,canonical(receipt)))
        if command.get('kind')=='background':builder=lambda s,call:spectator.background(self,s,call) if 'watch' in s else self.background(s,call)
        elif command.get('kind')=='preview':builder=self.generate_preview
        elif 'watch' in state:builder=lambda s,call:self.prepare(s,call)
        else:builder=lambda s,call:self.play(s,command['_actor'],command,call)
        try:
            result=self.operate(owner,gid,command,builder)
        except Exception as exc:
            receipt={'accepted':False,'pending':False,'code':getattr(exc,'code','retry_failed'),'message':str(exc)}
            with self.store.transaction() as con:con.execute('UPDATE commands SET receipt=? WHERE game_id=? AND id=?',(canonical(receipt),gid,identity))
            raise
        with self.store.transaction() as con:con.execute('UPDATE commands SET receipt=? WHERE game_id=? AND id=?',(canonical(result[1]),gid,identity))
        return result

    def review(self,owner,gid,command):
        if self.store.state(owner,gid).get('gameplay')!='ensemble':return super().review(owner,gid,command)
        state,receipt=self.command(owner,gid,{**command,'kind':'thought','text':'请整理我已经获得的信息和仍待核实的问题。'})
        return {'status':'completed' if receipt.get('accepted') else 'pending','receipt':receipt,'message':receipt['message'],'view':self.view(owner,state)}

    def start_background(self):
        if self._worker:return
        def loop():
            while not self._stop.wait(.5):
                for gid in list(self._seen):
                    if self._stop.is_set():break
                    try:self.pump(gid)
                    except Exception:
                        # Errors must be visible to a developer; no scripted role fallback.
                        import traceback
                        traceback.print_exc()
        self._worker=threading.Thread(target=loop,name='palter-agenda',daemon=True);self._worker.start()

    def stop_background(self):self._stop.set()
