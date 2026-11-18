"""Durable role subscriptions. Delivery and readiness do not require a model."""
from copy import deepcopy
from . import wait_lifecycle

WAIT_REPLY_WINDOW=3


def frequency(state,actor,version=1):
    if version>=2:
        blocked=bool(state.get('role_next_observation_wait',{}).get(actor,False))
        return {'version':2,'event':'next_observation','reply_window':2,'maximum_waits':1,
                'next_observation_allowed':not blocked,'other_replies_required':int(blocked)}
    recent=state.get('role_wait_history',{}).get(actor,[])[-(WAIT_REPLY_WINDOW-1):]
    remaining=max((i+WAIT_REPLY_WINDOW-len(recent) for i,waited in enumerate(recent) if waited),default=0)
    return {'reply_window':WAIT_REPLY_WINDOW,'maximum_waits':1,
            'wait_allowed':remaining==0,'non_wait_replies_required':remaining}


def is_wait_reply(plan,choice,speech,gesture):
    return plan['mode']=='wait' or (choice=='wait' and not (isinstance(speech,str) and speech.strip()) and not gesture)


def observation_wait(plan,data):
    return plan['mode']=='wait' and bool(set(plan['events']) & set(data['wait_frequency']['matching_events']))


def record_reply(state,actor,plan,data,choice,speech,gesture):
    if 'wait_frequency' not in data:return
    if data['wait_frequency'].get('version',1)>=2:
        state.setdefault('role_next_observation_wait',{})[actor]=observation_wait(plan,data)
        return
    histories=state.setdefault('role_wait_history',{})
    histories[actor]=(histories.get(actor,[])+[is_wait_reply(plan,choice,speech,gesture)])[-(WAIT_REPLY_WINDOW-1):]


def enabled(state):return state.get('scheduling_version',0)>=1


def waiting(state,actor):return enabled(state) and actor in state.get('role_waits',{})


def options(state,actor):
    from . import ensemble_world as w
    seen={o['event_id'] for o in state['observations'][actor]}
    out=[{'id':'next_observation','label':'下一条我实际收到的新信息'}]
    for task in state['activities']:
        if task['status']=='running' and (task['actor']==actor or task['id'] in seen):
            out.append({'id':'activity:'+task['id'],'label':('我' if task['actor']==actor else w.name(state,task['actor']))+'正在进行的行动结束'})
    for inv in state['invitations']:
        if inv['status']=='pending' and actor in (inv['from'],inv['to']):
            out.append({'id':'invitation:'+inv['id'],'label':'与'+w.name(state,inv['to'] if inv['from']==actor else inv['from'])+'的私聊邀请得到答复或失效'})
    for chat in state['chats'].values():
        if chat['status']=='active' and (actor in chat['participants'] or chat.get('started_by') in seen):
            out.append({'id':'conversation:'+chat['id'],'label':'、'.join(w.name(state,a) for a in chat['participants'])+'的私聊结束'})
    for event in state.get('tracked_events',[]):
        if event['creator']==actor and event['status'] in ('pending','active'):
            out.append({'id':'tracked:'+event['id'],'label':event['description']})
    if state.get('workflow_events_version') and state['phase']=='active' and not state.get('closure',{}).get('ready'):
        out.append({'id':'phase:conclusion','label':'已达成结案约定，进入独立提交阶段'})
    eligible={e['id'] for e in out}
    for listener in state.get('event_listeners',[]):
        if listener['actor']==actor and any(e in eligible for e in listener['events']):
            out.append({'id':'listener:'+listener['id'],'label':listener['description']})
    return out


def decision_options(data):
    quota=data.get('wait_frequency')
    if quota and quota.get('version',1)>=2:
        blocked=[] if quota['next_observation_allowed'] else list(quota['matching_events'])
        result={'allowed_modes':['continue','wait'],'disallowed_wait_events':blocked,
                'stationary_action_requires_response':False,
                'instruction':('本轮不可再次等待next_observation，包括指向它的监听器；可继续行动或等待其他可用事件。'
                    if blocked else '按已有行动和信息自主选择继续或等待；仅next_observation不可连续两次等待。')}
        from . import wait_progress
        return wait_progress.decision_options(result,data)
    blocked=bool(quota and not quota['wait_allowed'])
    return {'allowed_modes':['continue'] if blocked else ['continue','wait'],
        'stationary_action_requires_response':blocked,
        'instruction':('本轮不可等待：next_decision使用continue、events=[]。action=wait仅表示原地回应，必须同时有speech或gesture；'
            '否则从当前行动菜单自主选择实际行动。私下策略或记忆更新不代替行动。' if blocked else
            '按已有行动和信息自主选择继续或等待；保持发言义务和事件权限。')}


def context(state,actor,*,limit_waits=False,explicit_options=False,own_action_completion=False,message_wait_guard=False):
    result={'waitable_events':options(state,actor),
            'after_action_events':[{'id':'own_activity','actions':['search','hide','destroy','repair','clear_route']},
                                   {'id':'own_invitation','actions':['invite']}],
            'previous_wait':deepcopy(state.get('role_waits',{}).get(actor))}
    if message_wait_guard:
        from . import wait_progress
        result['message_wait_guard']=wait_progress.availability(state,actor,result['waitable_events'])
    if own_action_completion:
        from . import ensemble_world as w
        result['own_action_completion']=1
        result['after_action_events'][0]['actions']=sorted({c['id'].partition(':')[0] for c in w.choices(state,actor)})
        result['after_action_events'][0]['requires_outward_response_for']=['wait']
    if wait_lifecycle.enabled(state):
        result['wait_policy']={'default_timeout_seconds':wait_lifecycle.DEFAULT_TIMEOUT,
            'minimum_timeout_seconds':wait_lifecycle.MIN_TIMEOUT,'maximum_timeout_seconds':wait_lifecycle.MAX_TIMEOUT,
            'clock':'active_seconds','last_result':deepcopy(state.get('wait_results',{}).get(actor))}
    if limit_waits:
        result['wait_frequency']=frequency(state,actor,limit_waits)
        if limit_waits>=2:
            eligible={o['id'] for o in result['waitable_events']}
            result['wait_frequency']['matching_events']=['next_observation']+[
                'listener:'+e['id'] for e in state.get('event_listeners',[])
                if e['actor']==actor and 'next_observation' in e['events'] and 'listener:'+e['id'] in eligible]
    if explicit_options:result['decision_options']=decision_options(result)
    return result


def validate(plan,data,choice,has_proposal=False,*,speech=None,gesture=None):
    extra={'timeout_seconds','wait_reason'} if 'wait_policy' in data else set()
    if (not isinstance(plan,dict) or not {'mode','events'}<=set(plan) or set(plan)-{'mode','events'}-extra
            or plan['mode'] not in ('continue','wait')):raise ValueError('next decision')
    if extra:wait_lifecycle.validate(plan)
    ids=plan['events']
    if not isinstance(ids,list) or len(ids)>4 or any(not isinstance(x,str) for x in ids) or len(set(ids))!=len(ids):raise ValueError('wait events')
    if plan['mode']=='continue' and ids:raise ValueError('continue cannot subscribe')
    from . import wait_progress
    if choice not in data.get('message_wait_guard',{}).get('terminal_actions',[]):
        wait_progress.check(plan,data,empty_continuation=(plan['mode']=='continue' and choice=='wait'
            and not (isinstance(speech,str) and speech.strip()) and not gesture))
    quota=data.get('wait_frequency')
    if quota and quota.get('version',1)>=2:
        if not quota['next_observation_allowed'] and observation_wait(plan,data):
            from .model_contracts import ContractError
            raise ContractError('next_decision.events',
                'Consecutive waits for next_observation are unavailable. Select an authorized wait target '
                'outside disallowed_wait_events, or use mode=continue with events=[].',
                actual_events=list(ids),disallowed_wait_events=list(quota['matching_events']),
                other_replies_required=quota['other_replies_required'])
    elif quota and not quota['wait_allowed'] and is_wait_reply(plan,choice,speech,gesture):
        from .model_contracts import ContractError
        raise ContractError('next_decision',
            'Waiting is unavailable for this reply. Use mode=continue with events=[] and choose an available action, '
            'speech or gesture; an empty stationary continuation also counts as waiting. Do not invent facts or actions.',
            non_wait_replies_required=quota['non_wait_replies_required'])
    if has_proposal and plan['mode']=='wait' and ids!=['proposed_event']:raise ValueError('new event wait must reference proposal')
    allowed={o['id'] for o in data['waitable_events']}
    kind=choice.partition(':')[0]
    for option in data['after_action_events']:
        if kind in option['actions']:allowed.add(option['id'])
    # Immediate actions also have a real occurrence. This compatible validation
    # change does not alter historical paid context bytes on an explicit retry.
    if kind!='wait' or (isinstance(speech,str) and speech.strip()) or gesture:
        allowed.add('own_activity')
    else:allowed.discard('own_activity')
    if has_proposal:allowed.add('proposed_event')
    if not set(ids)<=allowed:
        from .model_contracts import ContractError
        raise ContractError('next_decision.events',
            'Use only the supplied authorized targets or the completion target created by this action. '
            'own_activity follows this action result, including immediate results; an empty stationary '
            'wait creates no completion event. Use mode=continue with events=[] to continue directly.',
            action=choice,actual_events=list(ids),invalid_events=[i for i in ids if i not in allowed],
            allowed_events=sorted(allowed))


def commit(state,actor,plan,data,proposed=None,action_event=None):
    from . import ensemble_world as w
    from . import wait_progress
    if (data.get('message_wait_guard') and actor in wait_progress.participants(state) and state['phase']=='active'
            and not any(q['actor']==actor for q in state['agenda'])):
        fresh={'message_wait_guard':wait_progress.availability(state,actor,options(state,actor))}
        wait_progress.check(plan,fresh,empty_continuation=plan['mode']=='continue' and action_event is None)
    waits=state.setdefault('role_waits',{});waits.pop(actor,None)
    if actor in state['submissions'] or state['phase']!='active':return
    if plan['mode']=='continue':
        w.enqueue(state,actor,'继续自己尚未完成的行动。',interrupt=False)
        return
    # Required events created during this same action take precedence over sleep.
    if any(q['actor']==actor for q in state['agenda']):return
    ids=[];labels={o['id']:o['label'] for o in data['waitable_events']}
    for key in plan['events']:
        if key=='own_activity':
            if action_event is None:
                raise ValueError('own_activity requires this decision action event')
            task=next((t for t in state['activities'] if t['actor']==actor and t['id']==action_event['id']),None)
            if task is None or task['status']!='running':
                # Receipts precede this enqueue. Coalescing and ordinary queue
                # dispatch provide one continuation, never an inline model loop.
                w.enqueue(state,actor,'本次行动已有结果，请根据实际收到的信息决定下一步。',action_event['id'])
                return
            key='activity:'+task['id'];labels[key]='我正在进行的行动结束'
        elif key=='own_invitation':
            inv=next(i for i in reversed(state['invitations']) if i['from']==actor)
            key='invitation:'+inv['id'];labels[key]='我发出的私聊邀请得到答复或失效'
        elif key=='proposed_event':
            key='tracked:'+proposed;labels[key]=next(e['description'] for e in state['tracked_events'] if e['id']==proposed)
        elif key.startswith('listener:'):
            listener=next(e for e in state['event_listeners'] if 'listener:'+e['id']==key and e['actor']==actor)
            for target in listener['events']:
                if target not in ids:ids.append(target);labels[target]=listener['description']
            continue
        ids.append(key)
    waits[actor]={'events':ids,'labels':[labels[x] for x in ids],
                  'after_observation':len(state['observations'][actor]),'channel':w.channel(state,actor)}
    if wait_lifecycle.enabled(state):wait_lifecycle.attach(state,actor,waits[actor],plan)
    reconcile(state)


def reconcile(state):
    """Only match actual terminal receipts visible to each subscriber."""
    if not enabled(state):return
    from . import ensemble_world as w
    from . import workflow_events
    workflow_events.resolve_trackers(state)
    events={e['id']:e for e in state['events']}
    cursors=state.setdefault('wake_cursors',{})
    for actor in w.ai_roles(state):
        rows=state['observations'][actor]
        for row in rows[cursors.get(actor,0):]:
            event=events[row['event_id']];kind=event['kind']
            own_result=event['actor']==actor and kind in ('action_completed','action_failed','action_cancelled')
            private_end=kind=='private_closed' and actor in state['chats'][event['target']]['participants']
            invitation_end=kind=='invitation_resolved' and event['target']==actor
            received_item=kind=='give' and row['kind']=='evidence'
            if own_result or private_end or invitation_end or received_item:
                w.enqueue(state,actor,'与你有关的事件已有结果，请查看实际收到的信息。',event['id'])
        cursors[actor]=len(rows)
    for actor,wait in list(state.get('role_waits',{}).items()):
        rows=state['observations'][actor];seen=list(dict.fromkeys(o['event_id'] for o in rows))
        reason=None;source=None
        if wait['channel']!=w.channel(state,actor):reason='谈话范围已变化，请重新决定自己的下一步。'
        for key in wait['events']:
            if reason:break
            if key=='next_observation':
                fresh=[o for o in rows[wait['after_observation']:] if events[o['event_id']].get('actor')!=actor]
                if fresh:reason='收到了等待期间的新信息。';source=fresh[0]['event_id']
                continue
            if key=='phase:conclusion' and state.get('workflow_events_version'):
                result=workflow_events.terminal(state,actor,key)
                if result:reason='已进入独立结案提交阶段。';source=result['id']
                continue
            kind,identity=key.split(':',1)
            for eid in seen:
                event=events[eid];facts=event['facts']
                matches=(kind=='activity' and facts.get('started_by')==identity and event['kind'] in ('action_completed','action_failed','action_cancelled') or
                         kind=='invitation' and facts.get('invitation_id')==identity and event['kind']=='invitation_resolved' or
                         kind=='conversation' and event['target']==identity and event['kind']=='private_closed' or
                         kind=='tracked' and event['target']==identity and event['kind']=='tracking_resolved')
                if matches:reason='等待的事件已有结果，请根据实际收到的信息决定下一步。';source=eid;break
        if reason:w.enqueue(state,actor,reason,source)
    wait_lifecycle.expire(state)


def next_deadline(state):
    deadlines=[c['expires'] for c in state['chats'].values() if c['status']=='active']
    deadlines.extend(i['expires'] for i in state['invitations'] if i['status']=='pending')
    if wait_lifecycle.enabled(state):deadlines.extend(w['deadline'] for w in state.get('role_waits',{}).values())
    return min(deadlines) if deadlines else None


def view(state,actor):
    wait=state.get('role_waits',{}).get(actor)
    if not enabled(state):return None
    result={'waiting':bool(wait),'events':list(wait['labels']) if wait else [],
            'unread':max(0,len(state['observations'][actor])-state['memory'][actor]['checkpoint'])}
    if wait_lifecycle.enabled(state):result.update(wait_lifecycle.view(state,actor))
    return result
