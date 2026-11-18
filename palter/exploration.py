"""Role-local investigation history and acquired-record provenance."""
from copy import deepcopy


def visible_records(state,actor,room):
    definitions={c['id']:c for c in state['case']['clues']}
    definitions.update(state.get('created_documents',{}))
    return [{'id':cid,'title':definitions[cid]['title']} for cid,obj in state['objects'].items()
            if obj['holder']==room and obj['condition']!='destroyed' and not obj['hidden']]


def no_new_evidence(state,actor,room):
    """Certify only a searched local inventory whose remaining originals are read."""
    searched=any(t['actor']==actor and t['kind']=='search' and t['status']=='completed'
                 and t['location']==room for t in state['activities'])
    if not searched:return False
    return all(not obj['hidden'] and cid in state['known'][actor]
               for cid,obj in state['objects'].items()
               if obj['holder']==room and obj['condition']!='destroyed')


def observe(state,actor):
    """Persist only what this actor can see here, after an actual world action."""
    if not state.get('exploration_version'):return
    room=state['locations'][actor]
    state.setdefault('exploration_snapshots',{}).setdefault(actor,{})[room]={
        'event_index':len(state['events']),'beat':state['beat'],
        'visible_records':visible_records(state,actor,room)}
    if state.get('area_evidence_version') and no_new_evidence(state,actor,room):
        state['exploration_snapshots'][actor][room]['no_new_evidence']=True


def acquisitions(state,actor):
    events={e['id']:e for e in state['events']};first={}
    for observation in state['observations'][actor]:
        if observation['kind']=='evidence' and observation.get('evidence_id') in state['known'][actor]:
            first.setdefault(observation['evidence_id'],observation)
    result={}
    methods={'inspect':'personal_inspection','take':'personal_collection','copy':'personal_copy',
             'give':'physical_receipt','share':'presentation','document_created':'self_authored'}
    for cid in state['known'][actor]:
        observation=first.get(cid);event=events.get(observation['event_id']) if observation else None
        method=methods.get(event['kind'],'legacy_unknown') if event else 'legacy_unknown'
        if event and event['kind'] in ('inspect','take','copy','document_created') and event['actor']!=actor:
            method='legacy_unknown'
        result[cid]={'method':method,'event_id':event['id'] if event else None,
            'observation_id':observation['id'] if observation else None,
            'from_actor':event['actor'] if event and method in ('physical_receipt','presentation') else None}
    return result


def evidence(state,actor,records):
    origins=acquisitions(state,actor)
    output=[]
    for record in records:
        projected=deepcopy(record)
        # Old share snapshots copied the original inspector's metadata. Keep
        # stored history intact, but do not send contradictory source labels.
        projected.pop('via',None);projected.pop('acquired_event',None)
        projected['acquisition']=origins[record['id']];output.append(projected)
    return output


def for_role(state,actor,*,exhaustion=False):
    rooms=state['case']['rooms'];position='r1';history={r:dict(visited=False,checks=[],searches=[],last_event=None) for r in rooms}
    tasks={task['id']:task for task in state['activities']}
    definitions={c['id']:c for c in state['case']['clues']};definitions.update(state.get('created_documents',{}))
    for event in state['events']:
        kind=event['kind'];own=event['actor']==actor;facts=event['facts']
        if kind=='started':history['r1']['visited']=True;history['r1']['last_event']=event['id']
        if kind=='move' and (own or actor in facts.get('followers',[])):
            position=event['target'];history[position].update(visited=True,last_event=event['id'])
        if own and kind=='follow' and 'location' not in facts:
            # Old follow movements lack structured arrival receipts. Do not
            # assign subsequent inspections to an unverified inferred location.
            position=None
        if own and kind in ('inspect','take','copy'):
            cid=event['target'];room=facts.get('location',position);definition=definitions.get(cid,{})
            held=facts.get('evidence_holder',definition.get('private_owner') or definition.get('location'))
            if room not in rooms or held in state['known']:continue
            history[room]['visited']=True;history[room]['last_event']=event['id']
            if cid not in history[room]['checks']:history[room]['checks'].append(cid)
        if own and kind=='action_completed' and facts.get('action')=='search':
            task=tasks.get(facts.get('started_by'),{});room=task.get('location',position)
            if room in rooms:
                history[room]['visited']=True;history[room]['last_event']=event['id'];history[room]['searches'].append(event['id'])
    current=state['locations'][actor]
    if any(e['kind']=='started' for e in state['events']):history[current]['visited']=True
    received={o['event_id'] for o in state['observations'][actor]}
    # Only a notice this character actually received can request a remote revisit.
    notices=[i+1 for i,e in enumerate(state['events']) if e['id'] in received and e['kind']=='world' and e['facts'].get('choice')=='records']
    snapshots=state.get('exploration_snapshots',{}).get(actor,{})
    output=[]
    for room,definition in rooms.items():
        past=history[room];snapshot=deepcopy(snapshots.get(room))
        if room==current and past['visited']:
            snapshot={'event_index':len(state['events']),'beat':state['beat'],'visible_records':visible_records(state,actor,room)}
        if snapshot:past['visited']=True
        visible=snapshot['visible_records'] if snapshot else None
        unread=[r for r in visible if r['id'] not in state['known'][actor]] if visible is not None else None
        investigated=bool(past['checks'] or past['searches'])
        revisit=bool(snapshot and room!=current and any(i>snapshot['event_index'] for i in notices))
        status=('unvisited' if not past['visited'] else 'visited' if not investigated else
                'visible_acquired' if unread==[] and not revisit else 'partial')
        output.append({'room_id':room,'name':definition['name'],'status':status,'current':room==current,
            'personally_checked':[{'id':cid,'title':state['known'][actor][cid]['title']} for cid in past['checks'] if cid in state['known'][actor]],
            'completed_searches':len(past['searches']),'last_activity_event':past['last_event'],
            'last_observed_beat':snapshot['beat'] if snapshot else None,
            'visible_unread_records':unread,'snapshot_current':room==current and past['visited'],
            'revisit_notice':revisit})
        if exhaustion and past['visited'] and not revisit:
            confirmed=(no_new_evidence(state,actor,room) if room==current
                       else bool(snapshot and snapshot.get('no_new_evidence')))
            if confirmed:output[-1]['no_new_evidence']=True
    return output
