"""Scoped request projections and conditional guidance; stored history is intact."""
from copy import deepcopy
from . import compact_context, memory_entries


def loop_context(state, actor):
    own=[d for d in state.get('decisions',[]) if d['actor']==actor][-4:]
    if len(own)<3 or sum(d['choice']=='wait' for d in own)<3:return None
    received=state['observations'][actor]
    return {'recent_own_choices':[d['choice'] for d in own],
            'recent_received_statements':[{'id':o['id'],'speaker':o.get('speaker')} for o in received[-12:] if o['kind']=='testimony'],
            'last_wait_result':deepcopy(state.get('wait_results',{}).get(actor)),
            'meaning':'Repeated choices are recorded facts, not a verdict that the dialogue is useless.'}


def guide(task, data, policies):
    result={}
    if task=='ensemble_role':
        if data.get('conclusion_task',{}).get('final'):
            result['final_submission']=policies['final_submission' if data['conclusion_task'].get('submission_format')=='per_aspect' else 'final_legacy']
        if data.get('conversation',{}).get('channel') not in (None,'public'):result['private_conversation']=policies['private_conversation']
        if data.get('temporal_facts',{}).get('facts'):result['timing']=policies['timing']
        if data.get('decision_loop'):result['repeated_choices']=policies['repeated_choices']
        if data.get('scheduling'):result['scheduling']=policies['scheduling']
    elif task=='ensemble_dm':
        if data.get('tracked_events'):result['event_judgment']=policies['event_judgment']
        if data.get('utterances'):result['speech_judgment']=policies['speech_judgment']
        if data.get('dm_event_repair'):result['event_repair']=policies['event_repair']
    return result


def deduplicate_dm(data):
    """One exact body per identity/version, retaining recipient-specific receipts."""
    out=deepcopy(data);pool=compact_context.Sources(True)
    pool.rows=out['sources']
    for context in out.get('event_recipient_contexts',{}).values():
        evidence=[]
        for record in context['acquired_evidence']:
            # The speech projection may have more metadata than the event view.
            compatible=next((key for key,body in pool.rows.items()
                if (key==record['id'] or key.startswith(record['id']+'@'))
                and all(body.get(k)==v for k,v in record.items() if k!='id')),None)
            ref=compatible or pool.add(record['id'],{k:v for k,v in record.items() if k!='id'})
            evidence.append({'id':record['id'],'source_ref':ref})
        context['acquired_evidence']=compact_context.table(evidence)
        refs={r['id']:r['source_ref'] for r in evidence}
        context['received_records']=compact_context.table([pool.observation(o,refs) for o in context['received_records']])
        if 'background_records' in context:
            context['background_records']=compact_context.table([pool.observation(o,refs) for o in context['background_records']])
        context['own_initial_facts']=compact_context.table([
            {'id':f['id'],'source_ref':pool.add(f['id'],{k:v for k,v in f.items() if k!='id'})}
            for f in context['own_initial_facts']])
    return out


def order(data, version=1):
    """Stable document bodies precede changing receipt bodies and working state."""
    data=deepcopy(data);out={};sources=data.get('sources',{})
    if 'evidence_catalog' in data:
        from .working_context import rows
        indexed={r['id']:r for r in rows(data.get('evidence'))}
        for item in rows(data.pop('evidence_catalog')):
            target=indexed.setdefault(item['id'],{'id':item['id']})
            for key,value in item.items():target.setdefault(key,value)
        data['evidence']=compact_context.table(list(indexed.values()))
        included=data.get('working_context',{}).get('included',{})
        if included:
            included.pop('evidence_catalog',None);included['evidence']=len(indexed)
    # A document's known immutable contents stay ahead of new speech. Never sort
    # histories by their text, merge occurrences, or copy full stored archives.
    stable={k:sources[k] for k in sorted(sources) if 'observation' in sources[k] or ('text' in sources[k] and 'kind' not in sources[k])}
    changing={k:sources[k] for k in sorted(sources) if k not in stable}
    out['context_format']=data.get('context_format',1);out['sources']={**stable,**changing}
    for key in ('actor','rooms','objectives','evidence','evidence_catalog'):
        if key in data:out[key]=data[key]
    for key,value in data.items():
        if key not in out and key!='active_guidance':out[key]=value
    if data.get('active_guidance'):out['active_guidance']=data['active_guidance']
    if data.get('dialogue_focus',{}).get('version',0)>=2:
        out['dialogue_focus']=out.pop('dialogue_focus')
        if out['dialogue_focus']['version']>=3:
            focus=out['dialogue_focus']
            ids={r['id'] for key in ('own_recent_speech','heard_recent_speech') for r in focus[key]}
            focus['sources']={key:out['sources'].pop(key) for key in list(out['sources']) if key in ids}
    return cache_order(out) if version>=2 else out


def cache_order(data):
    """Reorder keys only; preserve selected bodies and chronological arrays."""
    data=deepcopy(data)
    # Current speech text is a changing receipt even when its pooled body has
    # only a text field. It must not precede the creator's initial-fact bodies.
    speech_refs={u['facts']['text_ref'] for u in data.get('utterances',[])
                 if 'text_ref' in u.get('facts',{})}
    speech_refs.update(r['text_ref'] for r in data.get('private_history',[]) if 'text_ref' in r)
    if 'sources' in data:
        sources=data['sources']
        stable={k for k,v in sources.items() if 'observation' in v or
                ('text' in v and 'kind' not in v and k not in speech_refs)}
        data['sources']={k:sources[k] for k in sorted(sources,key=lambda k:(k not in stable,k))}
    if 'active_guidance' in data:
        guidance=data['active_guidance']
        priority=('scheduling','speech_judgment','timing','private_conversation',
                  'event_judgment','repeated_choices','final_submission','event_repair')
        data['active_guidance']={k:guidance[k] for k in priority if k in guidance}
        data['active_guidance'].update({k:v for k,v in guidance.items() if k not in data['active_guidance']})
    front=('context_format','actor','decision_mode','rooms','objectives','source_access',
           'snapshot_limits','conclusion_task','active_guidance','sources')
    tail=('validation_feedback','investigation_reminder','dialogue_focus')
    out={k:data[k] for k in front if k in data}
    out.update({k:v for k,v in data.items() if k not in out and k not in tail})
    out.update({k:data[k] for k in tail if k in data})
    return out


def merge_event_repair(output, feedback):
    if not (feedback or {}).get('dm_event_repair'):return output
    if not isinstance(output,dict) or not isinstance(output.get('event_decisions'),list):raise ValueError('event repair decisions required')
    expected=set(feedback['missing_ids']);rows=output['event_decisions']
    ids=[r.get('id') for r in rows if isinstance(r,dict)]
    if len(ids)!=len(rows) or len(ids)!=len(expected) or any(not isinstance(i,str) for i in ids) or set(ids)!=expected:
        raise ValueError('event repair must cover each missing ID exactly once')
    result=deepcopy(feedback['validated_result']);result['event_decisions'].extend(deepcopy(rows))
    return result
