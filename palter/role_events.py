"""DM-reviewed personal event conditions, separate from authoritative effects."""
from copy import deepcopy

from .storage import canonical, fingerprint
from . import wait_lifecycle, model_contracts as contract

ACTIVE=('pending','active')


def allowed_statuses(event):
    if event.get('record_type')=='wait_validity':return ['active','cancelled']
    return ['active','completed','cancelled']+(['rejected'] if event['status']=='pending' else [])


class EventDecisionError(ValueError):
    """Bounded correction metadata from authorized records, never model prose."""
    def __init__(self,records,message):
        super().__init__(message)
        self.feedback={'code':'event_decision_contract','instruction':message+
            ' Return the complete DM response with one decision per supplied record; preserve the actual meaning and source boundaries.',
            'expected_records':[{'id':e['id'],'record_type':e.get('record_type','custom_tracker'),
                'allowed_statuses':allowed_statuses(e),'basis_required':'decision_context' in e} for e in records]}


class DecisionBasisError(EventDecisionError):
    def __init__(self,event,message):
        ValueError.__init__(self,message)
        self.feedback={'code':'event_decision_basis','event_id':event['id'],
                       'actual_context':deepcopy(event['decision_context']),
                       'instruction':message+' Return the complete DM response; do not invent a different reason to force termination.'}


class EventSourceError(EventDecisionError):
    def __init__(self,records,event,sources,allowed):
        malformed=not isinstance(sources,list) or any(not isinstance(s,str) for s in sources)
        message=('source_ids must be an array of strings' if malformed else
                 'source_ids exceeds the eight-reference bound' if len(sources)>8 else
                 'source_ids contains IDs outside this creator\'s supplied context')
        super().__init__(records,'event decision source: '+message+'.')
        supplied=[s for s in sources if isinstance(s,str)] if isinstance(sources,list) else []
        self.feedback.update(code='event_source_contract',event_id=event['id'],creator=event['creator'],
            supplied_sources=supplied,invalid_sources=sorted(set(supplied)-allowed),
            allowed_sources=sorted(allowed),source_limit=8,
            instruction='Reassess this decision using the creator-scoped records. Cite only allowed_sources, at most eight string IDs. '
            'A current-circumstances decision may use an empty source list when no received record supports it. '
            'Do not invent another reason merely to pass validation. Return the complete DM response.')


def source_retry_feedback(feedback,upgrade):
    """New retry only: retain old paid inputs while restoring scoped background."""
    result=deepcopy(feedback)
    record=next(r for r in upgrade[0] if r['id']==result['event_id'])
    allowed=upgrade[2][record['creator']]
    result.update(event_context_repair=1,allowed_sources=sorted(allowed),
                  invalid_sources=sorted(set(result['supplied_sources'])-allowed))
    result['instruction']+=' Background records are now supplied separately; they are known history, not newly arrived messages. '
    result['instruction']+='observation_index <= review_range.from_exclusive is earlier context; only the chronological review range advances the cursor. '
    result['instruction']+='The engine owns fixed wait triggers; decide continued usefulness from the actual purpose and acquired evidence.'
    return result



def enabled(state):return state.get('scheduling_version',0)>=2


def owned(state,actor):return [e for e in state.get('tracked_events',[]) if e['creator']==actor]


def role_context(state,actor):
    events=owned(state,actor)
    active=[e for e in events if e['status'] in ACTIVE]
    return {'can_propose':len(active)<2,'active':[public_record(e) for e in active],
            'recent_results':[public_record(e) for e in events if e['status'] not in ACTIVE][-2:]}


def public_record(event):
    return {k:deepcopy(event[k]) for k in ('id','description','completion_condition','early_end_condition','status','progress','reason','end_on') if k in event}


def validate(out,data):
    proposal=out.get('event_request')
    if proposal is not None:
        if not data['can_propose'] or not isinstance(proposal,dict) or set(proposal)!={'description','completion_condition','early_end_condition'}:raise ValueError('event proposal')
        for key,limit in contract.EVENT_TEXT.items():
            contract.text(proposal[key],'event_request.'+key,limit,empty=key=='early_end_condition')
    cancelled=out.get('cancel_events',[])
    if not isinstance(cancelled,list) or len(cancelled)>2 or any(not isinstance(e,str) for e in cancelled) or len(set(cancelled))!=len(cancelled):raise ValueError('cancel events')
    if not set(cancelled)<={e['id'] for e in data['active']}:raise ValueError('cannot cancel another role event')


def request(state,actor,out):
    from . import ensemble_world as w
    for event in owned(state,actor):
        if event['id'] in out.get('cancel_events',[]):event['cancel_requested']=True
    proposal=out.get('event_request')
    if proposal is None:return None
    events=state.setdefault('tracked_events',[]);identity='condition-'+str(len(events)+1)
    event=dict(id=identity,creator=actor,**deepcopy(proposal),status='pending',progress='',reason='',source_ids=[],
               cancel_requested=False,checkpoint=len(state['observations'][actor]))
    events.append(event)
    receipt=w.emit(state,'tracking_proposed',actor,identity)
    w.note(state,actor,receipt,'你提出关注事项：'+proposal['description']+'，等待判断是否成立。')
    return identity


def relevant_rows(state,event):
    return [o for o in state['observations'][event['creator']][event['checkpoint']:]
            if o['kind']!='cue']


def scopes_due(state):
    if not enabled(state):return set()
    from . import ensemble_world as w
    from . import workflow_events
    workflow_events.resolve_trackers(state)
    scopes={w.channel(state,e['creator']) for e in state.get('tracked_events',[]) if e['status'] in ACTIVE
            and (e['status']=='pending' or e['cancel_requested'] or relevant_rows(state,e)
                 or (wait_lifecycle.enabled(state) and e.get('reviewed_circumstances')!=fingerprint(wait_lifecycle.circumstances(state,e['creator']))))}
    scopes.update(w.channel(state,e['creator']) for e in wait_lifecycle.review_records(state))
    return scopes


def due(state,event):
    return (event['status']=='pending' or event['cancel_requested'] or bool(relevant_rows(state,event))
            or (wait_lifecycle.enabled(state) and event.get('reviewed_circumstances')!=fingerprint(wait_lifecycle.circumstances(state,event['creator']))))


def package(state,scope,selective=False,background=False):
    from . import ensemble_world as w
    events=[e for e in state.get('tracked_events',[]) if e['status'] in ACTIVE and w.channel(state,e['creator'])==scope]
    if selective:events=[e for e in events if due(state,e)]
    events+=wait_lifecycle.review_records(state,scope)
    contexts={};allowed={};review_ends={};review_starts={}
    for actor in dict.fromkeys(e['creator'] for e in events):
        rows=state['observations'][actor];mine=[e for e in events if e['creator']==actor]
        wanted={source for e in mine for source in e['source_ids']}
        candidates=[o for o in rows[-20:] if o['id'] not in wanted and o['event_id'] not in wanted]
        candidates.extend(o for o in rows if o['id'] in wanted or o['event_id'] in wanted)
        if selective:
            # All unseen receipts, including quiet arrivals, remain available.
            # No tail-window truncation may advance past unexamined information.
            selected=set()
            for event in mine:
                start=event.get('checkpoint',state.get('role_waits',{}).get(actor,{}).get('review_checkpoint',0))
                review_starts[event['id']]=start
                end=start;used=0
                for index,row in enumerate(rows[start:],start):
                    cost=len(canonical({k:v for k,v in row.items() if k in ('id','event_id','kind','text','speaker','channel','evidence_id')}).encode())
                    if used and used+cost>4000:break
                    used+=cost;end=index+1;selected.add(row['id'])
                review_ends[event['id']]=end
            candidates=[o for o in rows if o['id'] in selected or o['id'] in wanted or o['event_id'] in wanted]
        background_rows=[]
        if background and selective:
            # A new wait has no post-checkpoint messages yet. Retain a small,
            # explicitly historical window without treating it as a new arrival.
            prior={o['id'] for o in candidates if o['id'] not in selected}
            before=max(review_starts[e['id']] for e in mine)
            used=0;count=0
            for row in reversed(rows[:before]):
                if row['id'] in selected or row['id'] in prior:continue
                cost=len(canonical(row).encode())
                if count>=6 or used+cost>2000:break
                prior.add(row['id']);used+=cost;count+=1
            background_rows=[o for o in rows if o['id'] in prior]
            candidates=[o for o in candidates if o['id'] in selected]
        # All receipts belong to the creator; no other role's private history is
        # an eligible condition source, even though the DM knows world truth.
        receipts=[];size=0
        for row in reversed(candidates):
            value={k:v for k,v in row.items() if k in ('id','event_id','kind','text','speaker','channel','evidence_id')}
            cost=len(canonical(value).encode())
            if not selective and size+cost>5000:continue
            receipts.append(deepcopy(value));size+=cost
        receipts.reverse()
        facts=[deepcopy(f) for f in state['case']['history'] if f['id'] in state['case']['roles'][actor]['knows']]
        evidence=[{k:deepcopy(c[k]) for k in ('id','title','observation')} for c in state['known'][actor].values()]
        contexts[actor]={'received_records':receipts,'own_initial_facts':facts,'acquired_evidence':evidence}
        if background and selective:
            positions={row['id']:i+1 for i,row in enumerate(rows)}
            for row in receipts:row['observation_index']=positions[row['id']]
            contexts[actor]['background_records']=[
                {**{k:deepcopy(v) for k,v in row.items() if k in ('id','event_id','kind','text','speaker','channel','evidence_id')},
                 'observation_index':positions[row['id']]} for row in background_rows]
        if wait_lifecycle.enabled(state):contexts[actor]['current_circumstances']=wait_lifecycle.circumstances(state,actor)
        allowed[actor]={o['id'] for o in receipts}|{o['event_id'] for o in receipts}|{f['id'] for f in facts}|{c['id'] for c in evidence}
        allowed[actor].update(o[key] for o in background_rows for key in ('id','event_id'))
    records=[{**public_record(e),'creator':e['creator'],'cancel_requested':e['cancel_requested'],'source_ids':list(e['source_ids'])} for e in events]
    for record,event in zip(records,events):
        if selective:record['review_range']={'through':review_ends[event['id']],
            'remaining':len(state['observations'][event['creator']])-review_ends[event['id']]}
        if background and selective:record['review_range']['from_exclusive']=review_starts[event['id']]
        if event.get('record_type'):record['record_type']=event['record_type']
        if state.get('event_contract_version'):
            record['allowed_statuses']=allowed_statuses(event)
            if 'wait_context' in event:record['wait_context']=deepcopy(event['wait_context'])
        if state.get('event_basis_version'):
            from . import workflow_events
            record['decision_context']={'workflow_stage':workflow_events.context(state,event['creator'])['stage'],
                                        'owner_cancel_requested':event['cancel_requested']}
    return records,contexts,allowed


def additional_background(state,package,requested):
    """Restore only creator-received OLD receipts, bounded independently of new pages.

    A global event may disclose more than a recipient saw. Always supply the
    recipient's original observation; never the global event's hidden facts.
    """
    records,contexts,allowed=package;extra={}
    for actor,ids in requested.items():
        mine=[r for r in records if r['creator']==actor]
        if actor not in contexts or not mine:continue
        before=min(r.get('review_range',{}).get('from_exclusive',0) for r in mine)
        rows=[];used=0
        for index,row in reversed(list(enumerate(state['observations'][actor][:before],1))):
            if not ({row['id'],row['event_id']}&set(ids))-allowed[actor]:continue
            value={k:deepcopy(v) for k,v in row.items() if k in ('id','event_id','kind','text','speaker','channel','evidence_id')}
            value['observation_index']=index;cost=len(canonical(value).encode())
            if len(rows)>=8 or used+cost>4000:continue
            rows.append(value);used+=cost
        if rows:extra[actor]=list(reversed(rows))
    return extra


def merge_background(package,extra,explicit=False):
    records,contexts,allowed=deepcopy(package)
    for actor,rows in extra.items():
        ctx=contexts[actor];existing={r['id'] for r in ctx.get('background_records',[])}
        ctx.setdefault('background_records',[]).extend(deepcopy(r) for r in rows if r['id'] not in existing)
        ctx['background_records'].sort(key=lambda r:r['observation_index'])
        allowed[actor].update(r[k] for r in rows for k in ('id','event_id'))
    if explicit:
        for actor,ctx in contexts.items():ctx['allowed_source_ids']=sorted(allowed[actor])
    return records,contexts,allowed


def source_background_feedback(state,package,feedback):
    """Persist a small, authorized repair only for the next unpaid attempt."""
    result=deepcopy(feedback)
    # Carry all still-needed references on each correction, including ones
    # restored by an earlier failed attempt; otherwise retries can oscillate.
    extra=additional_background(state,package,{result['creator']:result['supplied_sources']})
    if not extra:return result
    repaired=merge_background(package,extra,True);allowed=repaired[2][result['creator']]
    result.update(event_source_background=extra,allowed_sources=sorted(allowed),
        invalid_sources=sorted(set(result['supplied_sources'])-allowed))
    result['instruction']+=' Restored background contains this creator\'s actual earlier receipts, not new arrivals. Use only their visible contents; a departure receipt does not reveal a destination. Review cursors and fixed wake triggers are unchanged.'
    return result


def checked_background(state,package,feedback):
    extra=(feedback or {}).get('event_source_background') or {}
    if not extra:return package
    requested={actor:[r['id'] for r in rows] for actor,rows in extra.items()}
    if additional_background(state,package,requested)!=extra:raise ValueError('event background repair provenance')
    return merge_background(package,extra,True)


def validate_decisions(out,records,allowed):
    decisions=out.get('event_decisions')
    if not isinstance(decisions,list) or len(decisions)!=len(records):
        raise EventDecisionError(records,'event decisions: return exactly one item per supplied record, including wait validity reviews.')
    indexed={e['id']:e for e in records};seen=set()
    for decision in decisions:
        if not isinstance(decision,dict):raise EventDecisionError(records,'event decision must be an object.')
        identity=decision.get('id')
        if not isinstance(identity,str) or identity not in indexed or identity in seen:
            raise EventDecisionError(records,'event decision identity: use each supplied ID exactly once.')
        seen.add(identity);event=indexed[identity]
        status=decision.get('status')
        if event.get('review_range',{}).get('remaining') and status!='active':
            raise EventDecisionError(records,'More unreviewed receipts remain. Keep active with partial progress until all pending chunks have been examined.')
        if 'decision_context' in event:
            basis=decision.get('basis')
            if (not isinstance(basis,dict) or set(basis)!={'kind','workflow_stage'} or
                    basis['kind'] not in ('received_condition','current_circumstances','owner_request','workflow_transition')):
                raise DecisionBasisError(event,'Return basis with kind and workflow_stage for each event decision.')
            if basis['kind']=='workflow_transition':
                if basis['workflow_stage'] not in ('conclusion','ended') or basis['workflow_stage']!=event['decision_context']['workflow_stage']:
                    raise DecisionBasisError(event,'The claimed workflow transition has not occurred. Individual votes do not end investigation; keep the tracker active unless a separate authorized condition actually holds.')
            elif basis['workflow_stage'] is not None:
                raise DecisionBasisError(event,'Only workflow_transition may name a workflow_stage; other bases require null.')
            if basis['kind']=='owner_request' and not event['decision_context']['owner_cancel_requested']:
                raise DecisionBasisError(event,'The creator has not requested cancellation.')
        # A sourced legacy "completed" for a validity review means its purpose
        # is already satisfied. Application ends only this subscription, never
        # reports that a fixed event completed or changes its underlying work.
        purpose_satisfied=(event.get('record_type')=='wait_validity' and status=='completed' and 'decision_context' in event)
        if status not in allowed_statuses(event) and not purpose_satisfied:
            raise EventDecisionError(records,'event status transition: wait_validity reviews only whether waiting remains useful. Use cancelled when its purpose is already satisfied; fixed event completion belongs to engineering.')
        for key,limit in (('reason',300),('progress',400)):
            value=decision.get(key)
            if not isinstance(value,str) or len(value)>limit or (key=='reason' and not value.strip()):
                raise EventDecisionError(records,'event decision explanation: reason is required (maximum 300 characters); progress is a string (maximum 400 characters).')
        sources=decision.get('source_ids')
        if not isinstance(sources,list) or len(sources)>8 or any(not isinstance(s,str) for s in sources) or not set(sources)<=allowed[event['creator']]:
            if 'review_range' not in event:
                raise EventDecisionError(records,'event decision source: cite at most eight IDs actually supplied in this creator\'s context, never another role\'s records.')
            raise EventSourceError(records,event,sources,allowed[event['creator']])
        if status=='completed' and not sources:
            raise EventDecisionError(records,'completion requires acquired support: cite a relevant received record; do not invent support.')


def apply(state,decisions,call_id,review_checkpoints=None):
    from . import ensemble_world as w
    from . import role_schedule as scheduling
    indexed={e['id']:e for e in state.get('tracked_events',[])}
    validity_ids={wait['id'] for wait in state.get('role_waits',{}).values() if 'review_pending' in wait}
    for decision in decisions:
        if wait_lifecycle.apply_review(state,decision,call_id,(review_checkpoints or {}).get(decision['id'])):continue
        # An earlier terminal tracker in this batch can already have woken the
        # same role. Its now-obsolete validity review must not resolve a second
        # event or address a nonexistent custom tracker. Preserve receipt order.
        if decision['id'] in validity_ids:continue
        event=indexed[decision['id']];actor=event['creator']
        event.update({k:deepcopy(decision[k]) for k in ('status','reason','progress','source_ids')})
        if 'basis' in decision:event['decision_basis']=deepcopy(decision['basis'])
        event.update(checkpoint=(review_checkpoints or {}).get(decision['id'],len(state['observations'][actor])),
            cancel_requested=event['cancel_requested'] if (review_checkpoints or {}).get(decision['id'],len(state['observations'][actor]))<len(state['observations'][actor]) else False,last_call_id=call_id)
        if wait_lifecycle.enabled(state):event['reviewed_circumstances']=fingerprint(wait_lifecycle.circumstances(state,actor))
        if event['status']=='active':continue
        status={'completed':'条件已达成','cancelled':'已提前结束','rejected':'未获准建立'}[event['status']]
        receipt=w.emit(state,'tracking_resolved',actor,event['id'],status=event['status'],call_id=call_id)
        w.note(state,actor,receipt,'你关注的事项“'+event['description']+'”'+status+'：'+event['reason'])
        w.enqueue(state,actor,'自己关注的事项已有结果，请查看原因并决定下一步。',receipt['id'])
    scheduling.reconcile(state)


def end_story(state):
    """Ending ends operational waits without asserting their conditions succeeded."""
    decisions=[{'id':e['id'],'status':'cancelled','reason':'故事已经结束，这项等待随之终止。',
                'progress':e['progress'],'source_ids':e['source_ids']}
               for e in state.get('tracked_events',[]) if e['status'] in ACTIVE]
    apply(state,decisions,None)
    state['role_waits']={}
