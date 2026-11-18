"""Scoped wait admission and bounded spectator recovery, without invented events."""
from . import ensemble_world as w


def participants(state):
    return [a for a in w.ACTORS if a not in state['submissions']
            and (a not in state.get('evacuated',[]) or state.get('closure',{}).get('ready'))]


def availability(state,actor,options):
    eligible=participants(state)
    blocked=actor in eligible and all(a in state.get('role_waits',{}) for a in eligible if a!=actor)
    authorized={o['id'] for o in options}
    message_only=['next_observation']+['listener:'+listener['id'] for listener in state.get('event_listeners',[])
        if listener['actor']==actor and set(listener['events']) & authorized=={'next_observation'}
        and 'listener:'+listener['id'] in authorized]
    return {'version':1,'message_wait_allowed':not blocked,'message_only_events':message_only,
            'direct_contact_wait_allowed':not blocked,
            'terminal_actions':['lock_conclusion']+([] if state.get('closure',{}).get('ready') else ['leave'])}


def check(plan,data,*,empty_continuation=False):
    guard=data.get('message_wait_guard')
    if not guard or guard['message_wait_allowed']:return
    pure=plan['mode']=='wait' and set(plan['events'])<=set(guard['message_only_events'])
    if not pure and not empty_continuation:return
    from .model_contracts import ContractError
    raise ContractError('next_decision',
        'A message-only wait is unavailable for this decision, including direct-contact waits with no targets. '
        'Choose an available action or outward response and continue, or an authorized concrete event. '
        'An empty stationary continuation is not a response. Select from your own known information; '
        'this scheduling permission is not evidence about other participants.',
        actual_mode=plan['mode'],actual_events=list(plan['events']),message_wait_allowed=False,
        message_only_events=list(guard['message_only_events']),empty_continuation=empty_continuation)


def decision_options(result,data):
    guard=data.get('message_wait_guard')
    if guard:
        result.update(message_only_wait_allowed=guard['message_wait_allowed'],
                      empty_wait_allowed=guard['direct_contact_wait_allowed'])
        if not guard['message_wait_allowed']:
            result['stationary_action_requires_response']=True
            result['wait_requires_concrete_event']=True
            result['instruction']+=' 本轮继续时，next_decision必须用mode=continue、events=[]，并自主选择实际行动、speech或gesture；不能原地空转。如选择mode=wait，events必须至少含一个本轮获准的具体事件，不能为空，也不能仅含next_observation及其纯消息监听器。action、私下计划和发言中说想等待都不能代替next_decision许可；完成最终提交或离场不再等待。调度权限不代表获知他人的状态。'
    return result


def recover(state):
    """Called only after normal work and due DM reviews have had their chance."""
    if (not state.get('message_wait_guard_version') or 'watch' not in state or state.get('humans')
            or state['phase']!='active'):
        return False
    eligible=participants(state)
    if not eligible or not all(a in state.get('role_waits',{}) for a in eligible):return False
    if any(q['actor'] in eligible for q in state['agenda']):return False
    if (any(t['status']=='running' for t in state['activities']) or state['world_due']
            or any(c['status']=='active' for c in state['chats'].values())
            or any(i['status']=='pending' for i in state['invitations'])):
        return False
    from . import spectator,wait_lifecycle
    watch=state['watch'];keys=spectator.progress_keys(state)
    if keys-set(watch['seen_progress']):
        watch.pop('wait_recovery',None)
        watch['seen_progress']=sorted(set(watch['seen_progress'])|keys)
    episode=watch.setdefault('wait_recovery',{'reconsidered':[]})
    candidates=[a for a in eligible if a not in episode['reconsidered']]
    if not candidates:
        state['phase']='paused';watch['pause_reason']='waiting_stalled'
        return True
    actor=min(candidates,key=lambda a:(state['role_waits'][a].get('started_at',0),watch['turns'].get(a,0),a))
    episode['reconsidered'].append(actor)
    wait_lifecycle.resolve(state,actor,'cancelled',
        '本次等待先结束；尚未收到使等待事项完成的结果，请根据已有信息与未完成目标重新决定下一步。')
    return True
