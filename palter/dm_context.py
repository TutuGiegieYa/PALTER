"""Lossless, request-local DM sharing; stored events and authority stay intact."""
from collections import defaultdict
from copy import deepcopy
import re

from . import compact_context, memory_entries
from .storage import canonical


def events(data):
    return data.get('utterances', []) + data.get('recent_actual_events', [])


def normalize_history(original):
    """Give historical gestures the same projection as current utterances."""
    data = deepcopy(original)
    sources = compact_context.Sources(True)
    sources.rows = data['sources']
    for event in data.get('recent_actual_events', []):
        facts = event['facts']
        if 'speaker_knowledge' not in facts:
            continue
        knowledge = facts['speaker_knowledge']
        knowledge['evidence'] = sources.evidence(knowledge['evidence'])
        refs = {r['id']: r.get('source_ref', r['id']) for r in knowledge['evidence']}
        knowledge['observations'] = [sources.observation(o, refs) for o in knowledge['observations']]
        knowledge['memory'] = memory_entries.project(knowledge['memory'])
        for key in ('evidence', 'observations'):
            knowledge[key] = compact_context.table(knowledge[key])
        if 'text' in facts:
            facts['text_ref'] = sources.add(event['id'] + ':speech', {'text': facts.pop('text')})
    return data


def snapshot_references(original):
    """Pool exact snapshots per actor, then exact shared components. Never union."""
    data = deepcopy(original)
    snapshots, index = {}, {}
    for event in events(data):
        facts = event['facts']
        if 'speaker_knowledge' not in facts:
            continue
        snapshot = {'actor': event['actor'], 'knowledge': facts.pop('speaker_knowledge')}
        key = canonical(snapshot)
        if key not in index:
            identity = f'k{len(index)+1}'
            index[key] = identity
            snapshots[identity] = snapshot
        facts['speaker_knowledge_ref'] = index[key]
    if not snapshots:
        return data
    groups = defaultdict(list)
    for snapshot in snapshots.values():
        for field, value in snapshot['knowledge'].items():
            groups[(field, canonical(value))].append(snapshot['knowledge'])
    parts = {}
    size = lambda value: len(compact_context.dumps(value).encode())
    for (field, _), owners in groups.items():
        if len(owners) < 2:
            continue
        identity = f'p{len(parts)+1}'
        ref = {'part_ref': identity}
        body = owners[0][field]
        if len(owners) * size(body) <= size({identity: body}) + len(owners) * size(ref):
            continue
        parts[identity] = body
        for owner in owners:
            owner[field] = deepcopy(ref)
    data['knowledge_snapshots'] = snapshots
    if parts:
        data['knowledge_parts'] = parts
    return data


def split_id(value):
    if not isinstance(value, str) or '~' in value:
        return None
    match = re.fullmatch(r'(.*?)([0-9]+)', value)
    if not match:
        return None
    digits = match[2]
    width = len(digits) if len(digits) > 1 and digits[0] == '0' else 0
    return match[1], width, int(digits)


def id_ranges(original):
    """Encode actual consecutive runs only; retain holes, repeats and order."""
    fields = {'sources', 'source_ids', 'evidence_ids', 'testimony_ids'}
    def encode(value, field=None):
        if isinstance(value, dict):
            return {k: deepcopy(v) if k == 'validation_feedback' else encode(v, k)
                    for k, v in value.items()}
        if not isinstance(value, list):
            return deepcopy(value)
        if field not in fields or not value or not all(split_id(v) for v in value):
            return [encode(v) for v in value]
        result = []
        i = 0
        while i < len(value):
            start = split_id(value[i])
            j = i + 1
            while j < len(value):
                item = split_id(value[j])
                if item[:2] != start[:2] or item[2] != start[2] + j - i:
                    break
                j += 1
            if j - i >= 3:
                result.append(value[i] + '~' + value[j-1])
                i = j
            else:
                result.append(value[i])
                i += 1
        candidate = {'id_ranges': result}
        return candidate if len(compact_context.dumps(candidate).encode()) < len(compact_context.dumps(value).encode()) else deepcopy(value)
    return encode(original)


def pack(original, measure):
    """Choose the smallest complete wire request; a small input may stay inline."""
    normalized = normalize_history(original)
    candidates = [original, normalized, snapshot_references(normalized)]
    candidates += [id_ranges(value) for value in candidates]
    return deepcopy(min(candidates, key=measure))
