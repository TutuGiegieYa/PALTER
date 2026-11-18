"""Permit missing independent judgments only after all retained output validates."""
from copy import deepcopy
from . import role_events


def attach(error, output, records, allowed):
    rows=output.get('event_decisions')
    if not isinstance(rows,list):return
    ids=[r.get('id') for r in rows if isinstance(r,dict)]
    if len(ids)!=len(rows) or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids):return
    indexed={r['id']:r for r in records}
    if not set(ids)<set(indexed):return
    try:role_events.validate_decisions(output,[indexed[i] for i in ids],allowed)
    except ValueError:return
    error.feedback.update(dm_event_repair=1,validated_result=deepcopy(output),
        missing_ids=[r['id'] for r in records if r['id'] not in ids])
