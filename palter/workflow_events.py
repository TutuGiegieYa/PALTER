"""Observable workflow facts and mechanical fixed-event early termination."""
from . import ensemble_world as w


def context(state,actor):
    closure=state.get('closure',{})
    seen={o['event_id'] for o in state['observations'][actor]}
    agreements={}
    for event in state['events']:
        if event['kind']=='closure_vote' and event['id'] in seen:
            agreements[event['actor']]=event['facts']['agreed']
    return {'stage':'ended' if state['phase']=='ended' else 'conclusion' if closure.get('ready') else 'investigation',
            'conclusion_ready':bool(closure.get('ready')),'required_agreements':3,
            'known_agreements':agreements,'own_agreement':actor in closure.get('votes',[])}


def terminal(state,actor,key):
    """A subscription grants no access to somebody else's unseen receipt."""
    kind,_,identity=key.partition(':')
    events={e['id']:e for e in state['events']}
    for row in state['observations'][actor]:
        event=events[row['event_id']];facts=event['facts']
        matches=(kind=='phase' and identity=='conclusion' and state.get('closure',{}).get('ready') and event['kind']=='closure_agreed' or
                 kind=='activity' and facts.get('started_by')==identity and event['kind'] in ('action_completed','action_failed','action_cancelled') or
                 kind=='invitation' and facts.get('invitation_id')==identity and event['kind']=='invitation_resolved' or
                 kind=='conversation' and event['target']==identity and event['kind']=='private_closed')
        if matches:return event
    return None


def resolve_trackers(state):
    if not state.get('workflow_events_version'):return
    for tracker in state.get('tracked_events',[]):
        if tracker['status'] not in ('pending','active'):continue
        actor=tracker['creator']
        for key in tracker.get('end_on',[]):
            source=terminal(state,actor,key)
            if not source:continue
            reason='登记的提前结束事件已有确定结果。'
            tracker.update(status='cancelled',reason=reason,progress=reason,source_ids=[source['id']],
                           resolved_by='engine',terminal_event=key,cancel_requested=False)
            receipt=w.emit(state,'tracking_resolved',actor,tracker['id'],status='cancelled',reason=reason,
                           source_ids=[source['id']],resolved_by='engine',terminal_event=key)
            w.note(state,actor,receipt,'关注事项已提前结束：'+tracker['description']+'。'+reason)
            w.enqueue(state,actor,'关注事项已有结束回执，请决定下一步。',receipt['id'])
            break
