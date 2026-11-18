"""Bounded projections of acquired records; never an alternative world history."""
from copy import deepcopy

from . import ensemble_world as w
from . import exploration
from .storage import canonical


def within_budget(rows, limit):
    selected=[];size=0
    for row in rows:
        cost=len(canonical(row).encode())
        if size+cost>limit:continue
        selected.append(deepcopy(row));size+=cost
    return selected


def observation(row, actor):
    out = deepcopy(row)
    out['provenance'] = ('self_claim' if row.get('speaker') == actor else 'heard_claim') if row['kind'] == 'testimony' else 'acquired_record' if row['kind'] == 'evidence' else 'observed_event'
    return out


def project(state, actor, data, concise=False, receipts=False):
    """Keep original snapshots intact and rehydrate cited older observations."""
    for relation in data['relationships'].values():
        relation['experience_count'] = len(relation['experiences'])
        relation['experiences'] = list(reversed(within_budget(reversed(relation['experiences'][-3:]), 2400)))
    if concise:
        pending=len(state['observations'][actor])-state['memory'][actor]['checkpoint']
        data['observations']=data['observations'][-max(12,pending):]
    data['observations'] = [observation(o, actor) for o in data['observations']]
    belief = state['beliefs'][actor] or {}
    wanted = list(dict.fromkeys([
        *(data.get('strategy') or {}).get('sources',[]),
        *([] if data.get('decision_mode')=='concealment' else belief.get('testimony_ids', [])), *state['memory'][actor]['sources'],
        *(s for r in data['relationships'].values() for e in r['experiences'] for s in e['sources'])]))
    recent = {o['id'] for o in data['observations']}
    acquired = {o['id']: o for o in state['observations'][actor]}
    candidates = [observation(acquired[s], actor) for s in wanted if s in acquired and s not in recent]
    data['recalled_sources'] = within_budget(candidates, 6000)[:12]
    if concise:
        # Evidence texts already appear verbatim in the acquired evidence array.
        for row in [*data['observations'],*data['recalled_sources']]:
            if row.get('evidence_id') in state['known'][actor]:row.pop('text',None)
    # No object state learned remotely, nor global action log in a role's prompt.
    data['visible_record_state'] = [dict(id=cid, protected=obj['protected'], holder=obj['holder'])
        for cid, obj in state['objects'].items() if cid in state['known'][actor] and w.accessible(state, actor, cid)]
    if receipts:
        data['heard_statement_ids']=[o['id'] for o in state['observations'][actor] if o['kind']=='testimony']
        actions=[e for e in state['events'] if e['actor']==actor and e['kind'] not in ('testimony','gesture','cue')]
        data['own_action_record']={'count':len(actions),'recent':[{'kind':e['kind'],'target':e['target'],'action':e['facts'].get('action')} for e in actions[-6:]]}
        data['visible_record_state']=[dict(id=cid,protected=obj['protected'],holder=obj['holder'])
            for cid,obj in state['objects'].items() if w.accessible(state,actor,cid)]
    return data


def testimony(state, actor, ids):
    acquired = {o['id']: o for o in state['observations'][actor] if o['kind'] == 'testimony'}
    return [observation(acquired[s], actor) for s in ids]


def dialogue_focus(state, actor, version=1):
    """Index only the speaker's actual utterances; never infer their purpose."""
    recent=[]
    for row in reversed(state['observations'][actor]):
        if row['kind']=='testimony' and row.get('speaker')==actor:
            recent.append({'id':row['id'],'channel':row.get('channel')})
            if len(recent)==2:break
    result={'version':version,'own_recent_speech':list(reversed(recent))}
    if version>=2:
        heard=[]
        for row in reversed(state['observations'][actor]):
            if row['kind']=='testimony' and row.get('speaker')!=actor:
                heard.append({'id':row['id'],'speaker':row.get('speaker'),'channel':row.get('channel')})
                if len(heard)==3:break
        result.update(reply_as=actor,heard_recent_speech=list(reversed(heard)))
    return result


def investigation_state(state,actor,data,*,exhaustion=False):
    data['evidence']=exploration.evidence(state,actor,data['evidence'])
    data['exploration']=exploration.for_role(state,actor,exhaustion=exhaustion)


def recent_delivery(state, speeches, scope):
    received = {o['event_id'] for e in speeches for o in e['facts']['speaker_knowledge']['observations']}
    events = {e['id']: e for e in state['events']}
    rows = {}
    for e in speeches:
        for o in e['facts']['speaker_knowledge']['observations']:
            event = events.get(o['event_id'], {})
            source = events.get(event.get('facts', {}).get('source'), {})
            if o['kind'] == 'cue' and o['event_id'] in received and source.get('facts', {}).get('channel') == scope:
                rows[o['event_id']] = {'speaker': event['actor'], 'text': o['text']}
    return list(rows.values())[-6:]
