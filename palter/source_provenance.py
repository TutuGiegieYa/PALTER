"""Bounded source-origin index; never infer whether a free-form claim is true."""
from . import memory_entries


def for_role(state,actor,data):
    wanted={s for row in memory_entries.entries(data['memory']) for s in row['sources']}
    wanted.update(o['id'] for key in ('observations','recalled_sources') for o in data.get(key,[]))
    initial=set(state['case']['roles'][actor]['knows']);known=state['known'][actor]
    rows={o['id']:o for o in state['observations'][actor] if o['id'] in wanted}
    result={}
    for source in sorted(wanted):
        if source in known:result[source]={'kind':'acquired_record'}
        elif source in initial:result[source]={'kind':'initial_fact'}
        elif source in rows:
            row=rows[source]
            if row['kind']=='testimony':
                result[source]={'kind':'self_claim' if row.get('speaker')==actor else 'heard_claim',
                                'speaker':row.get('speaker')}
            elif row['kind']=='evidence':result[source]={'kind':'record_receipt','evidence_id':row.get('evidence_id')}
            else:result[source]={'kind':'received_event','event_kind':row['kind']}
        else:result[source]={'kind':'legacy_unresolved_origin'}
    return result
