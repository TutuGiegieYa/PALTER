"""Out-of-fiction spectator controls; none of these records enter role prompts."""
from copy import deepcopy
import json
import time
from . import ensemble_world as w
from . import role_schedule as scheduling
from . import role_events
from . import wait_progress
from .storage import StoreError, canonical, fingerprint
from .ai_gateway import retryable, manually_retryable

CONTROL_KEYS=('budget_usd','speed','call_limit')


def initialize(state):
    state['watch']={'budget_usd':.10,'call_limit':128,'speed':'normal','clock':0.,'steps':0,
        'turns':dict.fromkeys(w.ACTORS,0),'stagnant':0,'window':dict.fromkeys(w.ACTORS,0),
        'seen_progress':[],'pause_reason':None,'single_step':False,'recovery_operation':None,'tick_after_turns':0}
    return state


def merge_controls(work,current,base):
    if 'watch' not in work:return
    for key in CONTROL_KEYS:
        if current['watch'].get(key)!=base['watch'].get(key):work['watch'][key]=current['watch'][key]


def progress_keys(state):
    """Credit new grounded states once, rather than wording changes or round trips."""
    keys=set()
    def add(kind,value):keys.add(kind+':'+fingerprint(value))
    for a in w.ACTORS:
        for cid in state['known'][a]:add('knowledge',(a,cid))
        belief=state['beliefs'][a] or {}
        if state.get('interaction_version',1)>=2:
            if belief.get('explanation'):
                for source in belief.get('evidence_ids',[]):add('deduction',(a,belief.get('suspect'),source))
        elif belief.get('evidence_ids'):add('deduction',(a,belief.get('suspect'),sorted(set(belief['evidence_ids']))))
    for d in state['disclosures']:add('disclosure',(d['evidence_id'],d['channel'],d['event_id'] and next((e['actor'] for e in state['events'] if e['id']==d['event_id']),None)))
    for cid,obj in state['objects'].items():add('object',(cid,obj))
    for key,item in state['items'].items():add('item',(key,item['holder']))
    for a,room in state['locations'].items():add('visit',(a,room))
    for key in ('votes','pledges','resources','radio','route','switches','dials','vault','evacuated'):
        add(key,state[key])
    for c in state['commitments']:add('commitment',(c['from'],c['to'],c['status']))
    if state.get('closure'):add('closure',(sorted(state['closure']['votes']),state['closure']['ready']))
    for a in state['submissions']:add('submitted',a)
    for a,record in state.get('grounded_progress',{}).items():
        if record['kind']=='none':continue
        observations={o['id']:o for o in state['observations'][a]};events={e['id']:e for e in state['events']}
        sources=[]
        for source in record['sources']:
            observation=observations.get(source)
            if not observation:sources.append(('record',source));continue
            event=events.get(observation['event_id'],{})
            if event.get('kind')=='testimony':
                # A heard claim is usable information, not automatically truth. For
                # stagnation only, repeated exchanges with the same participants
                # and evidentiary basis do not manufacture endless new progress.
                facts=event['facts']
                sources.append(('heard',event['actor'],event['target'],
                                tuple(sorted(c['id'] for c in facts['speaker_knowledge']['evidence']))))
            else:sources.append(('observed',event.get('kind'),event.get('actor'),event.get('target')))
        if state.get('interaction_version',1)>=2:
            for source in sources:add('answer',(a,canonical(source)))
        elif sources:add('answer',(a,record['kind'],sorted(set(canonical(s) for s in sources))))
    return keys


def pause(app,owner,gid,reason,error=None):
    with app.store.transaction() as con:
        old=app.store.load(con,owner,gid)
        if old['phase'] not in ('active','paused'):return old
        state=deepcopy(old);state['phase']='paused';state['watch']['pause_reason']=reason
        state['watch']['single_step']=False
        if error:
            state['background_error']=error;state['watch']['recovery_operation']=error['operation_id']
        state['revision']+=1;app.store.save(con,state,old)
    return state


def command(app,owner,state,body):
    gid=state['id'];kind=body.get('kind')
    if kind not in ('confirm','retry_ai','cancel_pending','watch_pause','watch_resume','watch_step','watch_speed','watch_add_budget','watch_add_calls'):
        raise StoreError('观海者不能替角色发言、行动或提交结论。',403,'spectator_only')
    allowed={'command_id','expected_revision','kind','speed','operation_id'}
    if set(body)-allowed or type(body.get('expected_revision')) is not int:raise StoreError('观海操作格式无效。')
    if kind=='retry_ai':return app.retry_background(owner,gid,body)
    if kind=='confirm':
        if set(body)-{'command_id','expected_revision','kind'}:raise StoreError('观海操作格式无效。')
        return app.operate(owner,gid,body,lambda s,call:app.prepare(s,call) if s['phase']=='introduction' else wrong_phase())
    if kind=='cancel_pending':
        result=app.cancel_step(owner,gid,body)
        return result
    if kind not in ('watch_pause','watch_resume','watch_step','watch_speed','watch_add_budget','watch_add_calls'):
        raise StoreError('观海者不能替角色发言、行动或提交结论。',403,'spectator_only')
    identity=app.store.command_id(body.get('command_id'));digest=fingerprint(body)
    with app.store.transaction() as con:
        old=app.store.load(con,owner,gid)
        prior=con.execute('SELECT * FROM commands WHERE game_id=? AND id=?',(gid,identity)).fetchone()
        if prior:
            if prior['digest']!=digest:raise StoreError('操作标识已用于不同内容。',409,'command_conflict')
            return old,{**json.loads(prior['receipt']),'duplicate':True}
        if old['revision']!=body['expected_revision']:raise StoreError('页面状态已更新，请重试。',409,'stale_revision')
        if old['archived'] or old['phase']=='ended':raise StoreError('这局已结束或归档，仅可回顾。')
        state=deepcopy(old);watch=state['watch'];message='设置已保存。'
        if kind=='watch_add_budget':
            watch['budget_usd']=round(watch['budget_usd']+.05,6);message='本局预算已增加 0.05 美元；调用次数上限不变。'
        elif kind=='watch_add_calls':
            watch['call_limit']=watch.get('call_limit',128)+64
            message=f"调用次数上限已增加 64 次，当前为 {watch['call_limit']} 次；费用预算不变。"
            if state['background_error'] and state['background_error'].get('code')=='watch_call_limit':
                # Keep recovery_operation and its completed stages for explicit resume.
                state['background_error']=None;watch['pause_reason']='manual'
        elif kind=='watch_speed':
            if body.get('speed') not in ('normal','fast'):raise StoreError('请选择正常或快速播放。')
            watch['speed']=body['speed']
        elif kind=='watch_pause':
            if state['phase']!='active':wrong_phase()
            state['phase']='paused';watch.update(pause_reason='manual',single_step=False)
            message='已暂停；在途结果会保留，继续后应用。'
        else:
            if state['phase'] not in ('reading','paused'):wrong_phase()
            count=con.execute('SELECT COUNT(*) FROM ai_calls WHERE game_id=?',(gid,)).fetchone()[0]
            if count>=watch.get('call_limit',128):
                raise StoreError(f"已达到本局 {watch.get('call_limit',128)} 次调用上限，已有进展保留；可增加 64 次后继续。",409,'watch_call_limit')
            if state['background_error'] and not (manually_retryable(state['background_error'].get('code')) or state['background_error'].get('code')=='watch_budget'):
                raise StoreError('这一步已达到重试上限，请先取消该步骤。')
            recovery=watch.get('recovery_operation')
            if recovery:
                op=con.execute('SELECT status FROM ai_operations WHERE game_id=? AND id=?',(gid,recovery)).fetchone()
                if op and op['status']=='failed':app.gateway.renew_retry(con,gid,recovery)
            if state['phase']=='reading':w.start(state)
            else:state['phase']='active'
            if watch['pause_reason']=='stagnation':watch.update(stagnant=0,window=dict.fromkeys(w.ACTORS,0))
            if watch['pause_reason']=='waiting_stalled':
                watch.pop('wait_recovery',None)
                watch.update(stagnant=0,window=dict.fromkeys(w.ACTORS,0))
            watch.update(pause_reason=None,single_step=kind=='watch_step')
            state['background_error']=None
            if not watch['seen_progress']:watch['seen_progress']=sorted(progress_keys(state))
            message='准备推进一步，完成后暂停。' if kind=='watch_step' else '已开始继续观海。'
        state['revision']+=1;app.store.save(con,state,old)
        receipt={'accepted':True,'code':kind,'message':message,'duplicate':False}
        con.execute('INSERT INTO commands VALUES (?,?,?,?)',(gid,identity,digest,canonical(receipt)))
    app._seen[gid]=time.time();return state,receipt


def wrong_phase():raise StoreError('当前阶段不能执行这项观海操作。',409,'wrong_phase')


def background(app,state,call):
    app.configure_rules(state,call)
    watch=state['watch'];watch['clock']+=2;start=len(state['events']);actor=None;activity_count=len(state['activities'])
    w.expire(state)
    scheduling.reconcile(state)
    if state['closure']['ready'] and set(state['submissions'])==set(w.ACTORS):
        app.conclude_ensemble(state,call)
    elif any(t['status']=='running' for t in state['activities']) and w.now(state)>=state['next_tick'] and (sum(watch['turns'].values())>=watch.get('tick_after_turns',0) or (scheduling.enabled(state) and not state['agenda'])):
        w.advance(state)
    elif state['world_due'] and not state['closure']['ready']:
        def validate(out):
            if out['choice'] not in {c['id'] for c in w.world_choices(state)}:raise ValueError('world choice')
        out,cid=call('world','ensemble_world',{'scenario':state['scenario'],'rooms':state['case']['rooms']},
                    {'choices':w.world_choices(state),'beat':state['beat'],'recent_events':[{'kind':e['kind'],'beat':e['beat']} for e in state['events'][-12:]]},validate)
        w.apply_world(state,out['choice'],cid)
    else:
        eligible=[a for a in w.ACTORS if a not in state['submissions']]
        if scheduling.enabled(state):
            state['agenda']=[q for q in state['agenda'] if q['channel']==w.channel(state,q['actor']) and q['actor'] in eligible]
            eligible=[a for a in eligible if any(q['actor']==a for q in state['agenda']) and not scheduling.waiting(state,a)]
            if not eligible:
                deadline=scheduling.next_deadline(state)
                if state.get('message_wait_guard_version') and any(t['status']=='running' for t in state['activities']):
                    deadline=state['next_tick'] if deadline is None else min(deadline,state['next_tick'])
                if role_events.scopes_due(state):
                    app.adjudicate_ensemble(state,start,call)
                    if watch['single_step']:state['phase']='paused';watch['pause_reason']='step'
                elif wait_progress.recover(state):
                    if watch['single_step'] and state['phase']=='active':state['phase']='paused';watch['pause_reason']='step'
                elif deadline is not None:
                    watch['clock']=max(watch['clock'],deadline);w.expire(state);scheduling.reconcile(state)
                    app.adjudicate_ensemble(state,start,call)
                    if watch['single_step']:state['phase']='paused';watch['pause_reason']='step'
                else:
                    state['phase']='paused';watch['pause_reason']='waiting'
                watch['steps']+=1;watch['single_step']=False;watch['recovery_operation']=None;state['background_error']=None
                return
        if not eligible:return
        minimum=min(watch['turns'][a] for a in eligible)
        fair=[a for a in eligible if watch['turns'][a]==minimum]
        queued=[q for q in state['agenda'] if q['actor'] in fair and q['channel']==w.channel(state,q['actor'])]
        choice=queued[0] if queued else None
        actor=choice['actor'] if choice else fair[0]
        state['agenda']=[q for q in state['agenda'] if q['actor']!=actor]
        reason=choice['reason'] if choice else '根据自己已知的材料、未完成的目标和现场条件，选择下一步。'
        app.turn(state,actor,call,choice['depth'] if choice else 0,reason)
        watch['turns'][actor]+=1
        if len(state['activities'])>activity_count:
            # Let another character react before an autonomous timed-work tick.
            watch['tick_after_turns']=sum(watch['turns'].values())+1
        app.adjudicate_ensemble(state,start,call)
        if state['closure']['ready'] and set(state['submissions'])==set(w.ACTORS):app.conclude_ensemble(state,call)
    if actor is None and state['phase']=='active':app.adjudicate_ensemble(state,start,call)
    scheduling.reconcile(state)
    watch['steps']+=1;watch['recovery_operation']=None;state['background_error']=None
    keys=progress_keys(state);novel=keys-set(watch['seen_progress']);watch['seen_progress']=sorted(set(watch['seen_progress'])|keys)
    if novel:
        watch.update(stagnant=0,window=dict.fromkeys(w.ACTORS,0))
        watch.pop('wait_recovery',None)
    elif actor and not any(t['status']=='running' for t in state['activities']):
        watch['stagnant']+=1;watch['window'][actor]+=1
    active=[a for a in w.ACTORS if a not in state['submissions'] and not scheduling.waiting(state,a)]
    if not active and scheduling.wait_lifecycle.enabled(state):active=[a for a in w.ACTORS if a not in state['submissions']]
    stalled=watch['stagnant']>=12 and active and all(watch['window'][a]>=2 for a in active)
    if state['phase']!='ended' and (stalled or watch['single_step']):
        state['phase']='paused';watch['pause_reason']='stagnation' if stalled else 'step'
    watch['single_step']=False


def pump(app,state,owner,force=False):
    gid=state['id']
    if state['archived'] or state['phase']!='active':return False
    if not force and time.time()-app._seen.get(gid,0)>60:
        pause(app,owner,gid,'disconnected');return False
    if state['background_error']:return False
    if not force and time.monotonic()<app._watch_due.get(gid,0):return False
    with app.store.transaction(False) as con:
        # Preserve the exact pinned operation and cached stages after pause/restart.
        row=con.execute("SELECT command FROM ai_operations WHERE game_id=? AND (id=? OR status IN ('buffered','interrupted')) AND status NOT IN ('cancelled','completed') ORDER BY started LIMIT 1",
                        (gid,state['watch']['recovery_operation'])).fetchone()
    body=json.loads(row['command']) if row else {'command_id':'watch_'+gid[:8]+'_'+str(state['revision']),'expected_revision':state['revision'],'kind':'background','_actor':'system'}
    try:app.operate(owner,gid,body,lambda s,call:background(app,s,call))
    except Exception as exc:
        if isinstance(exc,StoreError) and exc.code in ('ai_pending','stale_revision','cancelled'):return False
        with app.store.transaction(False) as con:
            attempts=con.execute('SELECT MAX(n) FROM (SELECT COUNT(*) n FROM ai_calls WHERE game_id=? AND operation_id=? GROUP BY stage)',(gid,body['command_id'])).fetchone()[0] or 0
        code=getattr(exc,'code','internal_error')
        error={'message':str(exc) if isinstance(exc,StoreError) else '后台步骤遇到错误，已暂停并保留进展。',
               'operation_id':body['command_id'],'code':code,'retryable':code=='watch_budget' or retryable(code)}
        pause(app,owner,gid,'budget' if code=='watch_budget' else 'call_limit' if code=='watch_call_limit' else 'error',error)
        if not isinstance(exc,StoreError):
            import traceback
            traceback.print_exc()
    app._watch_due[gid]=time.monotonic()+(2 if state['watch']['speed']=='normal' else .25)
    return True


def view(state):
    result={k:deepcopy(state[k]) for k in ('id','mode','gameplay','revision','phase','archived','beat','title','introduction','scenario','outcome','background_error')}
    result.update(spectator=True,watch=deepcopy({k:v for k,v in state['watch'].items() if k!='seen_progress'}),
                  cast=[{'id':a,'name':w.name(state,a)} for a in w.ACTORS] if state['preview'] else [],
                  roles={},timeline=[],truth=None,ending=deepcopy(state['ending']),results=deepcopy(state['results']) if 'results' in state else None,
                  closure=deepcopy(state.get('closure')))
    if not state['case']:return result
    result['truth']={'history':deepcopy(state['case']['history']),'solution':deepcopy(state['case']['solution']),
                     'evidence':deepcopy(state['case']['clues']),'objects':deepcopy(state['objects']),
                     'rooms':deepcopy(state['case']['rooms']), 'evidence_sharing':w.evidence_sharing.omniscient(state)}
    observed={a:w.observed_dialogue(state,a) for a in w.ACTORS};cues={}
    for observations in observed.values():
        for row in observations:
            for cue in row.get('cues',[]):
                attached=cues.setdefault(row['event_id'],[])
                if cue not in attached:attached.append(cue)
    for a in w.ACTORS:
        role=w.view(state,a)
        result['roles'][a]={'name':w.name(state,a),'briefing':role['briefing'],'objectives':role['objectives'],
            'evidence':w.exploration.evidence(state,a,w.evidence_sharing.evidence(state,a,witnessed=True)),
            'exploration':w.exploration.for_role(state,a,exhaustion=True),'observations':observed[a],
            'memory':deepcopy(state['memory'][a]),'belief':deepcopy(state['beliefs'][a]),
            'relationships':deepcopy(state['relationships'][a]),'location':state['case']['rooms'][state['locations'][a]]['name'],
            'activity':deepcopy(w.running(state,a)),'submitted':a in state['submissions'],
            'recent_decisions':[deepcopy(d) for d in state.get('decisions',[]) if d['actor']==a][-5:]}
        result['roles'][a].update(perspective=w.perspective(state,a),
            strategy=deepcopy(state.get('strategies',{}).get(a)),scheduling=scheduling.view(state,a),
            tracked_events=role_events.role_context(state,a) if role_events.enabled(state) else None)
    from . import spectator_timeline
    result['timeline']=spectator_timeline.build(state,observed,cues)
    return result
