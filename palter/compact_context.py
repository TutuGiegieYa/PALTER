"""Versioned wire projections. Never mutate saved sources or global canonical JSON."""
from copy import deepcopy
import json

from .storage import canonical, fingerprint, StoreError
from . import memory_entries


def action_menu(choices):
    actions = {}
    for choice in choices:
        kind, *args = choice['id'].split(':')
        actions.setdefault(kind, []).append(args)
    return actions


def table(rows):
    """Column names once; empty/missing cells remain explicitly unknown."""
    if not rows:return {'columns': [], 'rows': []}
    flattened=[]
    for original in rows:
        row={}
        for key,value in original.items():
            if key=='acquisition' and isinstance(value,dict):
                row.update({key+'.'+k:v for k,v in value.items()})
            else:row[key]=value
        flattened.append(row)
    columns=list(dict.fromkeys(k for row in flattened for k in row))
    return {'columns':columns,'rows':[[row.get(k) for k in columns] for row in flattened]}


class Sources:
    def __init__(self, authorized_keys=False):
        self.rows = {}
        self.authorized_keys = authorized_keys

    def add(self, identity, body):
        body = deepcopy(body)
        key = identity
        if key in self.rows and self.rows[key] != body:
            key += '@' + fingerprint(body)[:12]
        self.rows.setdefault(key, body)
        return key

    def evidence(self, records):
        result = []
        for record in sorted(records, key=lambda r: ((r.get('acquisition') or {}).get('event_id') or r.get('acquired_event') or '', r['id'])):
            body = {k: record[k] for k in ('title', 'observation', 'location', 'source', 'category', 'author') if k in record}
            ref = self.add(record['id'], body)
            row={**{k: deepcopy(v) for k, v in record.items() if k not in body}, 'id': record['id']}
            if ref!=record['id']:row['source_ref']=ref
            result.append(row)
        return result

    def observation(self, row, evidence_refs=None):
        out = deepcopy(row)
        if out.get('kind') == 'evidence' and out.get('evidence_id') in (evidence_refs or {}):
            out.pop('text', None)
            out['source_ref'] = evidence_refs[out['evidence_id']]
        elif 'text' in out:
            # The body identity includes its occurrence and speaker, never text alone.
            body = {k: out[k] for k in ('event_id', 'kind', 'text', 'speaker', 'speaker_name', 'channel') if k in out}
            identity = row['id'] if self.authorized_keys else row.get('event_id', row['id']) + ':observation'
            ref = self.add(identity, body)
            for k in body:
                out.pop(k, None)
            out['source_ref'] = ref
        return out


def pack(task, data, authorized_keys=False, memory_capacity=False, memory_source_capacity=False, memory_source_limits=True, memory_policy=False, memory_token_budget=False, memory_character_budget=None, memory_summary_view=False, memory_snapshot_max_entries=None):
    dynamic = deepcopy(data)
    sources = Sources(authorized_keys)
    if task in ('ensemble_role', 'ensemble_memory'):
        dynamic['evidence'] = sources.evidence(dynamic.get('evidence', []))
        refs = {r['id']: r.get('source_ref',r['id']) for r in dynamic['evidence']}
        for key in ('observations', 'recalled_sources'):
            dynamic[key] = [sources.observation(o, refs) for o in dynamic.get(key, [])]
        focus = dynamic.get('focus', {})
        if 'received_requests' in focus:
            focus['received_requests'] = [sources.observation(o, refs) for o in focus['received_requests']]
        focus.pop('currently_accessible_unread_records', None)
        focus.pop('available_unread_records', None)
        if dynamic.get('action_feedback'):
            focus.pop('recent_own_actions',None);focus.pop('recent_decisions',None)
            if 'own_action_record' in dynamic:dynamic['own_action_record'].pop('recent',None)
        sharing=focus.pop('evidence_sharing',None)
        if sharing is not None:
            focus.pop('already_shared',None)
            columns=['spoken_by_me','shown_by_me','shown_to','witnessed_receivers','recipient_history_complete','observed_presentation_count']
            dynamic['presentation_receipts']={'columns':['id',*columns],
                'rows':[[cid,*[v.get(k) for k in columns]] for cid,v in sharing.items()]}
        for relation in dynamic.get('relationships',{}).values():
            relation.pop('description',None)  # The immutable role profile retains it.
            for experience in relation.get('experiences',[]):experience.pop('call_id',None)
        # Menus name visible targets without revealing unread document contents.
        choices = dynamic.pop('choices', [])
        dynamic['actions'] = action_menu(choices)
        labels = {}
        for choice in choices:
            kind, *args = choice['id'].split(':')
            if args and args[0] not in refs and args[0] not in dynamic.get('rooms',{}) and args[0] not in ('A','B','C','D','yes','no','0','1'):
                labels[args[0]] = choice['label']
        if labels:
            dynamic['visible_unread_targets'] = labels
        dynamic['memory'] = memory_entries.project(dynamic.get('memory',{'summary':'','sources':[],'checkpoint':0}),
                                                   capacity=memory_capacity, source_capacity=memory_source_capacity,
                                                   source_limits=memory_source_limits,token_budget=memory_token_budget)
        if task=='ensemble_memory':
            keep={'actor','evidence','observations','recalled_sources','memory','thoughts','exploration','belief','strategy','memory_output','source_provenance','temporal_facts'}
            if memory_summary_view:
                keep.difference_update(('recalled_sources','exploration','belief','strategy','temporal_facts'))
            if memory_policy:keep.add('memory_maintenance')
            if memory_source_capacity:
                dynamic['snapshot_limits'] = memory_entries.limits(snapshot=True, source_capacity=True,
                                                                   source_limits=memory_source_limits)
                if memory_policy:dynamic['snapshot_limits']=memory_entries.hard_limits(token_budget=memory_token_budget,text_budget=memory_character_budget)
                keep.update(('snapshot_limits', 'validation_feedback'))
            if memory_snapshot_max_entries is not None:
                from . import memory_headroom
                dynamic['summary_capacity']=memory_headroom.contract(memory_snapshot_max_entries)
                dynamic.setdefault('snapshot_limits',{})['entries']=memory_snapshot_max_entries
                if 'memory_maintenance' in dynamic:
                    dynamic['memory_maintenance']['hard_limits']['entries']=memory_snapshot_max_entries
                keep.update(('summary_capacity','snapshot_limits'))
            dynamic={k:v for k,v in dynamic.items() if k in keep}
    elif task == 'ensemble_dm':
        for utterance in dynamic.get('utterances',[]):
            facts = utterance['facts']
            knowledge = facts['speaker_knowledge']
            knowledge['evidence'] = sources.evidence(knowledge['evidence'])
            refs = {r['id']: r.get('source_ref',r['id']) for r in knowledge['evidence']}
            knowledge['observations'] = [sources.observation(o, refs) for o in knowledge['observations']]
            knowledge['memory'] = memory_entries.project(knowledge['memory'])
            # Keep the event ID usable by the existing DM verdict contract.
            facts['text_ref'] = sources.add(utterance['id'] + ':speech', {'text': facts.pop('text')})
        for key in ('private_history',):
            for row in dynamic.get(key, []):
                if 'text' in row:
                    text=row.pop('text')
                    existing=next((k for k,v in sources.rows.items() if k.startswith(row['event_id']+':') and v.get('text')==text),None)
                    row['text_ref'] = existing or sources.add(row['event_id'] + ':speech', {'text': text})
    # Rectangular metadata avoids repeating verbose keys for every receipt.
    for key in ('evidence','observations','recalled_sources'):
        if key in dynamic:dynamic[key]=table(dynamic[key])
    if 'received_requests' in dynamic.get('focus',{}):
        dynamic['focus']['received_requests']=table(dynamic['focus']['received_requests'])
    for utterance in dynamic.get('utterances',[]):
        knowledge=utterance['facts']['speaker_knowledge']
        for key in ('evidence','observations'):knowledge[key]=table(knowledge[key])
    # Source bodies precede mutable receipts/interpretations; no change to canonical().
    ordered = {'context_format': 1, 'sources': sources.rows}
    for key in ('actor', 'rooms', 'objectives', 'evidence', 'memory', 'belief', 'strategy', 'relationships'):
        if key in dynamic:
            ordered[key] = dynamic.pop(key)
    reminder=dynamic.pop('investigation_reminder',None)
    ordered.update(dynamic)
    if reminder is not None:ordered['investigation_reminder']=reminder
    return ordered


def dumps(data):
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))


def lookup(state, actor, arguments):
    """Exact authorized source lookup; no semantic search or global ID oracle."""
    if not isinstance(arguments, dict) or set(arguments) != {'requests'}:
        raise ValueError('source lookup arguments')
    requests = arguments['requests']
    if not isinstance(requests, list) or not 1 <= len(requests) <= 8:
        raise ValueError('source lookup batch')
    available = {o['id']: o for o in state['observations'][actor]}
    available.update(state['known'][actor])
    available.update({f['id']: f for f in state['case']['history'] if f['id'] in state['case']['roles'][actor]['knows']})
    rows = [];remaining = 8192
    for request in requests:
        if not isinstance(request, dict) or 'id' not in request or set(request)-{'id', 'offset'}:
            raise ValueError('source lookup request')
        # Reading a source from its beginning needs no explicit pagination value.
        # Keep this compatible with already pinned calls that omitted the offset.
        identity, offset = request['id'], request.get('offset', 0)
        if not isinstance(identity, str) or type(offset) is not int or offset < 0:
            raise ValueError('source lookup identity')
        if identity not in available:
            rows.append({'id': identity, 'status': 'unavailable'})
            continue
        original = available[identity]
        text = original.get('text', original.get('observation', ''))
        if offset > len(text):
            rows.append({'id': identity, 'status': 'invalid_range'})
            continue
        stop = offset
        while stop < len(text) and len(text[offset:stop + 1].encode()) <= remaining:
            stop += 1
        excerpt = text[offset:stop];remaining -= len(excerpt.encode())
        rows.append({'id': identity, 'status': 'complete' if offset == 0 and stop == len(text) else 'excerpt',
            'kind': original.get('kind', 'acquired_record'), 'speaker': original.get('speaker'),
            'event_id': original.get('event_id', original.get('acquired_event')), 'text': excerpt,
            'offset': offset, 'next_offset': stop if stop < len(text) else None, 'total_characters': len(text)})
    return {'sources': rows, 'range_unit': 'characters', 'body_byte_limit': 8192}


def recall(state, actor, data):
    """Keep explicit current reasoning and memory references; relationship history is indexed."""
    current = state['beliefs'][actor] or {}
    wanted = set(current.get('testimony_ids', [])) | set(state['memory'][actor]['sources'])
    wanted.update((state.get('strategies', {}).get(actor) or {}).get('sources', []))
    data['recalled_sources'] = [o for o in data.get('recalled_sources', []) if o['id'] in wanted]
    # Full IDs remain authorized and can be looked up even outside the active window.
    data['source_lookup'] = {'available': True, 'max_requests': 8, 'max_body_bytes': 8192}
