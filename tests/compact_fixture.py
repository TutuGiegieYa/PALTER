"""Fixture-only adapter for old scenario policies and the new wire contract."""
from copy import deepcopy
import re


def expand_dm_references(value):
    """Independent fixture decoder; never used to change model output or saves."""
    def ranges(value):
        if isinstance(value,dict):
            if set(value)=={'id_ranges'}:
                result=[]
                for item in value['id_ranges']:
                    if '~' not in item:result.append(item);continue
                    start,end=item.split('~')
                    a=re.fullmatch(r'(.*?)([0-9]+)',start);b=re.fullmatch(r'(.*?)([0-9]+)',end)
                    assert a[1]==b[1]
                    width=len(a[2]) if len(a[2])>1 and a[2][0]=='0' else 0
                    result.extend(a[1]+str(n).zfill(width) for n in range(int(a[2]),int(b[2])+1))
                return result
            return {k:ranges(v) for k,v in value.items()}
        return [ranges(v) for v in value] if isinstance(value,list) else deepcopy(value)
    data=ranges(value)
    snapshots=data.pop('knowledge_snapshots',{})
    parts=data.pop('knowledge_parts',{})
    for event in data.get('utterances',[])+data.get('recent_actual_events',[]):
        facts=event['facts']
        if 'speaker_knowledge_ref' not in facts:continue
        snapshot=snapshots[facts.pop('speaker_knowledge_ref')]
        assert snapshot['actor']==event['actor']
        knowledge=deepcopy(snapshot['knowledge'])
        for field,value in knowledge.items():
            if isinstance(value,dict) and set(value)=={'part_ref'}:knowledge[field]=deepcopy(parts[value['part_ref']])
        facts['speaker_knowledge']=knowledge
    return data


def expand(data):
    data=expand_dm_references(data);sources={**data['sources'],**data.get('dialogue_focus',{}).get('sources',{})}
    def untabulate(value):
        if not isinstance(value,dict) or 'columns' not in value:return value
        result=[]
        for cells in value['rows']:
            row={}
            for key,v in zip(value['columns'],cells):
                if '.' in key:
                    parent,child=key.split('.',1);row.setdefault(parent,{})[child]=v
                elif v is not None:row[key]=v
            result.append(row)
        return result
    def observations(rows):
        for row in rows:
            ref=row.get('source_ref')
            if ref:
                source=sources[ref]
                if row.get('kind')=='evidence':row['text']=source['observation']
                else:
                    for k,v in source.items():row.setdefault(k,deepcopy(v))
        return rows
    def knowledge(value):
        for key in ('evidence','observations'):
            if key in value:value[key]=untabulate(value[key])
        for record in value.get('evidence',[]):
            source=sources[record.get('source_ref',record['id'])]
            for k,v in source.items():record.setdefault(k,deepcopy(v))
        observations(value.get('observations',[]))
        if 'entries' in value.get('memory',{}):
            m=value['memory'];m['summary']='\n'.join(r['text'] for r in m['entries']);m['sources']=list(dict.fromkeys(s for r in m['entries'] for s in r['sources']))
    knowledge(data)
    if 'recalled_sources'in data:data['recalled_sources']=untabulate(data['recalled_sources'])
    observations(data.get('recalled_sources',[]))
    if 'actions' in data:
        data['choices']=[{'id':':'.join([kind,*args]),'label':kind} for kind,tuples in data['actions'].items() for args in tuples]
    for u in data.get('utterances',[]):
        f=u['facts'];f['text']=sources[f['text_ref']]['text'];knowledge(f['speaker_knowledge'])
    for e in data.get('recent_actual_events',[]):
        f=e['facts']
        if 'text_ref' in f:
            f['text']=sources[f['text_ref']]['text']
            if 'speaker_knowledge' in f:knowledge(f['speaker_knowledge'])
    for context in data.get('event_recipient_contexts',{}).values():
        for key in ('received_records','acquired_evidence','own_initial_facts','background_records'):
            if key not in context:continue
            context[key]=untabulate(context[key])
            for row in context[key]:
                ref=row.get('source_ref')
                if ref:
                    for k,v in sources[ref].items():row.setdefault(k,deepcopy(v))
    for row in data.get('private_history',[]):
        if 'text_ref' in row:row['text']=sources[row['text_ref']]['text']
    if 'received_requests' in data.get('focus',{}):data['focus']['received_requests']=untabulate(data['focus']['received_requests'])
    observations(data.get('focus',{}).get('received_requests',[]))
    return data


def response(task,out,data):
    if task not in ('ensemble_role','ensemble_memory'):return out
    sources=out.get('memory_sources',out.get('sources',[]))
    text=out.get('memory',out.get('summary',''))
    patch={'upsert':[{'id':'m1','kind':'interpretation','text':text,'sources':sources}] if sources else [],
           'archive':[],'processed_through':data['observations'][-1]['id'] if data['observations'] else None}
    if task=='ensemble_memory':
        if data.get('memory_output')=='entries_snapshot':return {'entries':patch['upsert'],'processed_through':patch['processed_through']}
        return {'memory_update':patch}
    out=deepcopy(out);kind,*args=out.pop('choice').split(':');out['action']={'kind':kind,'args':args}
    out['memory_update']=patch;out.pop('memory');out.pop('memory_sources')
    if data.get('decision_mode')=='concealment':
        out['strategy_update']={'situation':out.pop('situation'),'plan':out.pop('strategy'),'sources':out.pop('assessment_sources')}
    else:
        out['belief_update']={'suspect':out.pop('suspect'),'explanation':out.pop('reasoning'),'evidence_ids':out.pop('evidence_ids'),'testimony_ids':out.pop('testimony_ids',[])}
    if out.get('final_conclusion') and data.get('conclusion_task',{}).get('submission_format')=='per_aspect':
        old=out['final_conclusion']
        out['final_conclusion']={'suspect':old['suspect'],'aspects':[
            {'aspect':a,'explanation':old['explanation'],'evidence_ids':old['evidence_ids'],
             'testimony_ids':old['testimony_ids'],'gaps':''} for a in data['conclusion_task']['dimensions']]}
    return out
