"""Objective recipient-scoped execution history; no judgment of usefulness."""
from collections import defaultdict
from copy import deepcopy

from .storage import canonical

TERMINAL = {'action_completed': 'completed', 'action_failed': 'failed', 'action_cancelled': 'cancelled'}
TIMED = {'search', 'hide', 'destroy', 'repair', 'clear_route'}
EXCLUDE = {'started', 'ended', 'cue', 'closure_agreed'}


def record(state, actor, choice, start):
    """Enrich only newly produced occurrences, before the enclosing atomic commit."""
    events = state['events'][start:]
    root = next((e for e in events if e['actor'] == actor), None)
    if root is None:
        root = next((e for e in events if e['kind'] == 'private_closed'), None)
    if root is None:
        return
    kind, *args = choice.split(':')
    root['facts']['execution'] = {'actor': actor, 'kind': kind, 'args': args,
                                 'location': state['locations'][actor]}
    root['facts']['execution']['recipients'] = [a for a, rows in state['observations'].items()
        if any(o['event_id'] == root['id'] for o in rows)]


def for_role(state, actor, limit=2048):
    seen = defaultdict(list)
    for row in state['observations'][actor]:
        seen[row['event_id']].append(row)
    executions = {};groups = {};last_index = {}
    for index, event in enumerate(state['events']):
        facts = event['facts'];receipt = facts.get('execution')
        performer = receipt['actor'] if receipt else event['actor']
        own = performer == actor
        if not own and event['id'] not in seen:
            continue
        kind = receipt['kind'] if receipt else event['kind']
        if kind in EXCLUDE:
            continue
        if event['kind'] in TERMINAL:
            execution = executions.get(facts.get('started_by'))
            if execution:
                execution['status'] = TERMINAL[event['kind']]
                execution['last_event'] = event['id']
                execution['result_sources'] = [r['id'] for r in seen[event['id']]]
                last_index[execution['group']] = index
            continue
        args = receipt['args'] if receipt else ([event['target']] if event['target'] is not None else [])
        # Source location is meaningful only when personally observed or recorded.
        location = receipt.get('location') if receipt else facts.get('location')
        movement=facts.get('movement_views',{}).get(actor)
        if kind=='move' and facts.get('movement_views') is not None:
            # The root receipt is omniscient. Departure witnesses must not get
            # its destination, remote audience, or the arrival group's location.
            if movement is None:continue
            args=movement['args'];location=movement['location']
        scope = facts.get('channel')
        identity = canonical([performer, kind, args, location, scope])
        if identity not in groups:
            groups[identity] = {'actor': performer, 'action': kind, 'args': args,
                                'location': location, 'channel': scope, 'count': 0, 'recent': []}
        row = {'event_id': event['id'], 'last_event': event['id'], 'beat': event['beat'],
               'status': 'running' if kind in TIMED else 'completed',
               'result_sources': [r['id'] for r in seen[event['id']]]}
        recipients = receipt.get('recipients') if receipt else facts.get('recipients')
        if movement is not None:recipients=None
        if recipients is not None:
            row['recipients'] = list(recipients)
        else:
            row['recipients'] = None  # Missing legacy metadata is unknown.
        group = groups[identity];group['count'] += 1;group['recent'].append(row)
        # Use the same row for lifecycle updates, without counting them as new acts.
        executions[event['id']] = row;row['group'] = identity
        last_index[identity] = index
    ordered = sorted(groups, key=lambda k: last_index[k], reverse=True)
    selected = [];size = 0
    for identity in ordered:
        group = deepcopy(groups[identity]);group['recent'] = group['recent'][-2:]
        for row in group['recent']:
            row.pop('group', None)
            if row['last_event']==row['event_id']:row.pop('last_event')
            if row['recipients'] is None:row.pop('recipients')
        group['older_details_omitted'] = group['count'] - len(group['recent'])
        n = len(canonical(group).encode())
        if size + n <= limit:
            selected.append(group);size += n
    return {'groups': selected, 'omitted_groups': len(groups) - len(selected)}
