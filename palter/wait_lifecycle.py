"""Finite subscriptions and scoped DM validity, independent of event success."""
from copy import deepcopy
from .storage import fingerprint

DEFAULT_TIMEOUT=30
MIN_TIMEOUT=10
MAX_TIMEOUT=300


def enabled(state):return bool(state.get('wait_lifecycle_version'))


def now(state):
    from . import ensemble_world as w
    return state.get('paused_at',w.now(state)) if state['phase']=='paused' and 'watch' not in state else w.now(state)


def circumstances(state,actor):
    from . import ensemble_world as w
    activity=w.running(state,actor)
    result={'presence':w.scene_presence(state,actor),
            'own_activity':{k:activity[k] for k in ('id','kind','status') if k in activity} if activity else None}
    if state.get('workflow_events_version'):
        from . import workflow_events
        result['workflow']=workflow_events.context(state,actor)
    return result


def configure(state):
    state['wait_lifecycle_version']=1
    for actor,wait in state.get('role_waits',{}).items():
        if 'deadline' not in wait:attach(state,actor,wait,{})


def attach(state,actor,wait,plan):
    state['wait_serial']=state.get('wait_serial',0)+1
    wait.update(id='wait-'+str(state['wait_serial']),started_at=now(state),
        deadline=now(state)+plan.get('timeout_seconds',DEFAULT_TIMEOUT),
        timeout_seconds=plan.get('timeout_seconds',DEFAULT_TIMEOUT),
        wait_reason=plan.get('wait_reason') or '；'.join(wait['labels']) or '等待直接联系。')
    # Fixed terminal events and explicit custom trackers keep their own owner.
    if not wait['events'] or set(wait['events'])=={'next_observation'}:
        wait.update(review_pending=True,review_checkpoint=len(state['observations'][actor]),
                    reviewed_circumstances=None,progress='',source_ids=[])


def validate(plan):
    if 'timeout_seconds' in plan:
        duration=plan['timeout_seconds']
        if type(duration) is not int or not MIN_TIMEOUT<=duration<=MAX_TIMEOUT:raise ValueError('wait timeout range')
    if 'wait_reason' in plan and (not isinstance(plan['wait_reason'],str) or len(plan['wait_reason'])>240):
        raise ValueError('wait reason')


def due(state,actor,wait):
    if 'review_pending' not in wait:return False
    if wait['review_pending'] or wait['reviewed_circumstances']!=fingerprint(circumstances(state,actor)):return True
    return any(o['kind']!='cue' for o in state['observations'][actor][wait['review_checkpoint']:])


def review_records(state,scope=None):
    from . import ensemble_world as w
    if not enabled(state):return []
    records=[]
    for actor,wait in state.get('role_waits',{}).items():
        if (scope is not None and w.channel(state,actor)!=scope) or not due(state,actor,wait):continue
        record={'id':wait['id'],'creator':actor,'status':'active','record_type':'wait_validity',
            'description':wait['wait_reason'],
            'completion_condition':'；'.join(wait['labels']) or '收到直接联系',
            'early_end_condition':'等待条件失去意义或不再可行时，可提前取消等待。',
            'progress':wait['progress'],'reason':'','source_ids':list(wait['source_ids']),
            'cancel_requested':False}
        if state.get('event_contract_version'):
            rows=state['observations'][actor];boundary=wait['after_observation']
            record['wait_context']={'review_scope':'continued_usefulness_of_subscription',
                'fixed_completion_owner':'engine','targets':list(wait['events']),
                'started_after_observation':rows[boundary-1]['id'] if boundary else None}
        records.append(record)
    return records


def resolve(state,actor,status,reason,call_id=None,review=None):
    from . import ensemble_world as w
    wait=state.get('role_waits',{}).pop(actor,None)
    if not wait:return
    details={}
    if review is not None:
        details={'resolution_kind':'purpose_satisfied','reported_status':review['status'],
                 'source_ids':deepcopy(review['source_ids']),'decision_basis':deepcopy(review['basis'])}
    receipt=w.emit(state,'wait_resolved',actor,wait_id=wait['id'],status=status,reason=reason,call_id=call_id,**details)
    title='等待已超时' if status=='timed_out' else '等待已结束' if review is not None else '等待已提前结束'
    w.note(state,actor,receipt,title+'：'+reason,'wait_result',speaker_name=w.name(state,actor)+' · 等待状态')
    result={'wait_id':wait['id'],'status':status,'reason':reason,'event_id':receipt['id'],**details}
    state.setdefault('wait_results',{})[actor]=result
    w.enqueue(state,actor,title+'，请根据实际收到的信息决定下一步。',receipt['id'])


def apply_review(state,decision,call_id,checkpoint=None):
    for actor,wait in list(state.get('role_waits',{}).items()):
        if wait.get('id')!=decision['id'] or 'review_pending' not in wait:continue
        if decision['status']=='cancelled':resolve(state,actor,'cancelled',decision['reason'],call_id)
        elif decision['status']=='completed' and state.get('event_basis_version'):
            resolve(state,actor,'cancelled',decision['reason'],call_id,review=decision)
        elif decision['status']=='active':
            wait.update(review_pending=False,review_checkpoint=len(state['observations'][actor]) if checkpoint is None else checkpoint,
                reviewed_circumstances=fingerprint(circumstances(state,actor)),
                progress=decision['progress'],source_ids=deepcopy(decision['source_ids']))
        else:raise ValueError('invalid wait review status')
        return True
    return False


def expire(state):
    if not enabled(state) or state['phase']!='active':return
    for actor,wait in list(state.get('role_waits',{}).items()):
        if now(state)>=wait['deadline']:
            resolve(state,actor,'timed_out','已达到本次等待时限；这不表示所等事项已经完成。')


def shift(state,duration):
    if 'watch' in state:return
    for wait in state.get('role_waits',{}).values():
        if 'deadline' in wait:wait['deadline']+=duration;wait['started_at']+=duration


def view(state,actor):
    wait=state.get('role_waits',{}).get(actor)
    result={'last_result':deepcopy(state.get('wait_results',{}).get(actor))}
    if wait and 'deadline' in wait:
        result.update(remaining_seconds=max(0,round(wait['deadline']-now(state))),
                      timeout_seconds=wait['timeout_seconds'],wait_reason=wait['wait_reason'])
    return result
