"""Presentation receipts, separate from knowledge, speech and contribution credit.

Old saves are projected from immutable observations; no migration rewrites them.
Role projections never inspect another role's privately acquired evidence.
"""
from copy import deepcopy


def ledger(state):
    actors=list(state['known'])
    delivered={}
    for actor in actors:
        for observation in state['observations'][actor]:
            delivered.setdefault(observation['event_id'],set()).add(actor)
    starts={chat['started_by']:chat for chat in state['chats'].values() if chat.get('started_by')}
    # Missing old start markers cannot establish whether a two-person delivery
    # was public or private. Never guess from its recipient count.
    complete_intervals=all(chat.get('started_by') for chat in state['chats'].values())
    active={};events={};presentations=[]
    for event in state['events']:
        events[event['id']]=event
        if event['id'] in starts:
            chat=starts[event['id']]
            active.update({a:chat['id'] for a in chat['participants']})
        if event['kind']=='private_closed':
            active={a:cid for a,cid in active.items() if cid!=event['target']}
        if event['kind']!='share':continue
        facts=event['facts']
        recipients=facts.get('recipients',delivered.get(event['id'],set()))
        presentations.append(dict(event_id=event['id'],actor=event['actor'],evidence_id=event['target'],
            channel=facts.get('channel',active.get(event['actor'],'public' if complete_intervals else None)),
            recipients_recorded='recipients' in facts or event['id'] in delivered,
            recipients=[a for a in actors if a in recipients]))
    disclosures=[];seen=set()
    for disclosure in state['disclosures']:
        event=events.get(disclosure['event_id'])
        if not event:continue
        key=(event['id'],disclosure['evidence_id'])
        if key in seen:continue
        seen.add(key)
        recipients=event['facts'].get('recipients',delivered.get(event['id'],set()))
        disclosures.append(dict(event_id=event['id'],actor=event['actor'],evidence_id=disclosure['evidence_id'],
            channel=disclosure['channel'],recipients=[a for a in actors if a in recipients]))
    return {'presentations':presentations,'disclosures':disclosures}


def for_role(state,actor,receipts=None,witnessed=False):
    receipts=ledger(state) if receipts is None else receipts
    result={}
    for cid in state['known'][actor]:
        visible=lambda row:row['evidence_id']==cid and (row['actor']==actor or actor in row['recipients'])
        presentations=[r for r in receipts['presentations'] if visible(r)]
        disclosures=[r for r in receipts['disclosures'] if visible(r)]
        own=[r for r in presentations if r['actor']==actor]
        shown={a for r in own for a in r['recipients'] if a!=actor}
        result[cid]=dict(spoken_by_me=any(r['actor']==actor for r in disclosures),shown_by_me=bool(own),
            recipient_history_complete=all(r['recipients_recorded'] for r in own),
            shown_to=[a for a in state['known'] if a in shown],
            not_shown_to=[a for a in state['known'] if a!=actor and a not in shown],
            observed_presentation_count=len(presentations))
        if witnessed:
            received={a for r in presentations for a in r['recipients'] if a!=actor}
            result[cid]['witnessed_receivers']=[a for a in state['known'] if a in received]
            result[cid]['not_witnessed_receiving']=[a for a in state['known'] if a!=actor and a not in received]
    return result


def evidence(state,actor,receipts=None,witnessed=False):
    statuses=for_role(state,actor,receipts,witnessed)
    return [dict(deepcopy(record),sharing=statuses[cid]) for cid,record in state['known'][actor].items()]


def omniscient(state):
    receipts=ledger(state)
    ids=[c['id'] for c in state['case']['clues']]+list(state.get('created_documents',{}))
    return {cid:dict(known_by=[a for a in state['known'] if cid in state['known'][a]],
        presentations=[r for r in receipts['presentations'] if r['evidence_id']==cid],
        disclosures=[r for r in receipts['disclosures'] if r['evidence_id']==cid]) for cid in ids}
