"""Advisory summary targets and deterministic capacity-pressure scheduling."""
from . import memory_entries
from .storage import fingerprint

TRIGGER_TEXT=850
URGENT_TEXT=900
TRIGGER_ENTRIES=9
URGENT_ENTRIES=11
NEW_OBSERVATIONS=8
NEW_DECISIONS=4


def stats(memory):
    rows=memory_entries.entries(memory)
    return {'entries':len(rows),'text_characters':sum(len(row['text']) for row in rows),
            'entry_lengths':[{'id':row['id'],'text_characters':len(row['text'])} for row in rows]}


def decisions(state,actor):
    return sum(row['actor']==actor for row in state.get('decisions',[]))


def progress(state,actor):
    current=stats(state['memory'][actor]);last=state.get('memory_compactions',{}).get(actor)
    if last is None:return current,last,0,0,False
    received=max(0,len(state['observations'][actor])-last['observations'])
    turns=max(0,decisions(state,actor)-last['role_decisions'])
    grew=current['text_characters']>last['text_characters'] or current['entries']>last['entries']
    return current,last,received,turns,grew


def token_progress(state,actor):
    rows=memory_entries.entries(state['memory'][actor])
    current={'entries':len(rows)}
    last=state.get('memory_compactions',{}).get(actor)
    received=max(0,len(state['observations'][actor])-last['observations']) if last else 0
    turns=max(0,decisions(state,actor)-last['role_decisions']) if last else 0
    changed=not last or last.get('memory_fingerprint')!=fingerprint(rows)
    return current,last,received,turns,changed


def needed(state,actor,context_pressure=False,token_budget=False,text_budget=None,entry_trigger=None):
    if token_budget:
        current,last,received,turns,changed=token_progress(state,actor)
        text_pressure=bool(text_budget and stats(state['memory'][actor])['text_characters']>=text_budget)
        if not context_pressure and not text_pressure and current['entries']<(entry_trigger or TRIGGER_ENTRIES):return False
        pending=len(state['observations'][actor])-state['memory'][actor]['checkpoint']
        if context_pressure and not current['entries'] and pending<=12:return False
        if last is None:return True
        if text_pressure and last.get('text_budget')!=text_budget:return True
        if not received and not changed:return False
        if text_pressure:return True
        if context_pressure:return changed or pending>12
        if current['entries']>=URGENT_ENTRIES and current['entries']>last['entries']:return True
        return received>=NEW_OBSERVATIONS or turns>=NEW_DECISIONS
    current,last,received,turns,grew=progress(state,actor)
    pressure=current['text_characters']>=TRIGGER_TEXT or current['entries']>=TRIGGER_ENTRIES
    if not pressure and not context_pressure:return False
    pending=len(state['observations'][actor])-state['memory'][actor]['checkpoint']
    # Rewriting a short memory cannot shrink an oversized immutable baseline or
    # the minimum recent window. Do not buy a call with no reducible input.
    if context_pressure and pending<=12 and current['text_characters']<=550 and current['entries']<=6:return False
    if last is None:return True
    if not received and not grew:return False
    if context_pressure and (grew or pending>12):return True
    if grew and (current['text_characters']>=URGENT_TEXT or current['entries']>=URGENT_ENTRIES):return True
    return received>=NEW_OBSERVATIONS or turns>=NEW_DECISIONS


def record(state,actor,before,token_budget=False,text_budget=None):
    if token_budget:
        rows=memory_entries.entries(state['memory'][actor])
        state.setdefault('memory_compactions',{})[actor]={
            'policy_version':2,'observations':len(state['observations'][actor]),
            'processed_checkpoint':state['memory'][actor]['checkpoint'],
            'role_decisions':decisions(state,actor),'entries':len(rows),
            'memory_fingerprint':fingerprint(rows),'previous_entries':before['entries']}
        if text_budget:
            state['memory_compactions'][actor].update(policy_version=3,text_budget=text_budget,
                text_characters=sum(len(row['text']) for row in rows))
        return
    current=stats(state['memory'][actor])
    state.setdefault('memory_compactions',{})[actor]={
        'observations':len(state['observations'][actor]),'processed_checkpoint':state['memory'][actor]['checkpoint'],
        'role_decisions':decisions(state,actor),'entries':current['entries'],'text_characters':current['text_characters'],
        'previous_text_characters':before['text_characters'],
        'target_met':current['entries']<=6 and current['text_characters']<=550}


def context(state,actor,token_budget=False,text_budget=None):
    if token_budget:
        current,last,received,turns,changed=token_progress(state,actor)
        previous={key:last[key] for key in ('observations','processed_checkpoint','role_decisions','entries') if key in last} if last else None
        result={'current':current,'targets':memory_entries.summary_targets(token_budget=True,text_budget=text_budget),
                'hard_limits':memory_entries.hard_limits(token_budget=True,text_budget=text_budget),
                'output_budget':'request.max_tokens','last_consolidation':previous,
                'new_observations':received,'decisions_since_consolidation':turns,'memory_changed':changed}
        if text_budget:
            current['text_characters']=stats(state['memory'][actor])['text_characters']
            result['character_budget']={'trigger_at':text_budget,'snapshot_maximum':text_budget-1,
                'unit':'characters_in_entry_text','applies_to':'standalone_summary'}
        return result
    current,last,received,turns,grew=progress(state,actor)
    return {'current':current,'targets':memory_entries.summary_targets(),
            'hard_limits':memory_entries.hard_limits(),'last_consolidation':dict(last) if last else None,
            'new_observations':received,'decisions_since_consolidation':turns,'capacity_grew':grew}
