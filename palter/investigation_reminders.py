"""Optional, role-local investigation reminders attached to ordinary decisions."""
from copy import deepcopy

from . import exploration
from .storage import fingerprint

QUIET_DECISIONS = 2
REMINDER_INTERVAL = 4


def progress(state, actor, rooms=None):
    """Observable investigation changes, not an assessment of dialogue quality."""
    rooms = exploration.for_role(state, actor) if rooms is None else rooms
    records = [(cid, {k: record[k] for k in ('title', 'observation', 'source', 'category', 'author') if k in record})
               for cid, record in sorted(state['known'][actor].items())]
    visits = [(r['room_id'], r['status'] != 'unvisited',
               sorted(c['id'] for c in r['personally_checked']), r['completed_searches']) for r in rooms]
    return fingerprint([records, visits])


def closure_signal(state, actor, data):
    """Only a proposal actually heard and still known to be in effect."""
    agreed = {a for a, yes in data.get('closure', {}).get('known_agreements', {}).items() if yes and a != actor}
    received = {o['event_id'] for o in state['observations'][actor]}
    return next((e['id'] for e in reversed(state['events'])
                 if e['id'] in received and e['kind'] == 'closure_vote'
                 and e['actor'] in agreed and e['facts'].get('agreed')), None)


def prepare(state, actor, data):
    """Pure preview. Retries and native-tool continuations reuse this same notice."""
    old = state.get('investigation_reminders', {}).get(actor, {})
    rooms = data.get('exploration', [])
    marker = progress(state, actor, rooms)
    quiet = old.get('quiet_decisions', 0) if old.get('progress') == marker else 0
    completed = old.get('completed_decisions', 0)
    menu = {c['id'] for c in data['choices']}
    areas = [{'room_id': r['room_id'], 'name': r['name'], 'status': r['status'],
              'current': r['current'], 'can_move': 'move:'+r['room_id'] in menu}
             for r in rooms if r['status'] in ('unvisited', 'visited')]
    area_key = fingerprint([(r['room_id'], r['status']) for r in areas])
    signal = closure_signal(state, actor, data)
    ticket = {'progress': marker, 'quiet_decisions': quiet, 'completed_decisions': completed,
              'area_key': area_key, 'closure_signal': signal, 'reminder': None}
    if (not areas or data.get('closure', {}).get('ready') or actor in state['submissions']
            or data.get('conversation', {}).get('channel') != 'public'
            or data.get('focus', {}).get('activity')
            or not any(c == 'search' or c.startswith(('move:', 'inspect:')) for c in menu)):
        return ticket
    new_proposal = signal is not None and signal != old.get('last_closure_signal')
    interval_passed = (old.get('last_reminder_at') is None
                       or completed - old['last_reminder_at'] >= REMINDER_INTERVAL
                       or area_key != old.get('last_area_key'))
    if new_proposal or (quiet >= QUIET_DECISIONS and interval_passed):
        ticket['reminder'] = {
            'trigger': 'received_closure_proposal' if new_proposal else 'no_new_investigation',
            'own_decisions_without_new_investigation': quiet,
            'personally_unchecked_areas': areas}
    return ticket


def commit(state, actor, ticket):
    """Called once after a successful role action, inside its atomic operation."""
    tracker = deepcopy(state.get('investigation_reminders', {}).get(actor, {}))
    after = progress(state, actor)
    tracker.update(progress=after, completed_decisions=ticket['completed_decisions']+1,
                   quiet_decisions=ticket['quiet_decisions']+1 if after == ticket['progress'] else 0)
    if ticket['reminder'] is not None:
        tracker.update(last_reminder_at=ticket['completed_decisions'], last_area_key=ticket['area_key'],
                       last_closure_signal=ticket['closure_signal'])
    state.setdefault('investigation_reminders', {})[actor] = tracker
