"""Deterministic, byte-budgeted request views; stored knowledge is never edited."""
from copy import deepcopy

from . import compact_context
from .storage import canonical

SOFT_DYNAMIC_BYTES = 36_000
SOFT_TOTAL_BYTES = 76_000
OPTIONAL_BODY_BYTES = 6000


def rows(value):
    if isinstance(value, dict) and 'columns' in value:
        return [dict(zip(value['columns'], row)) for row in value['rows']]
    return value or []


def references(value):
    if isinstance(value, dict):
        if 'columns' in value:
            yield from references(rows(value))
        else:
            for key, item in value.items():
                if key in ('source_ref', 'text_ref') and isinstance(item, str):yield item
                else:yield from references(item)
    elif isinstance(value, list):
        for item in value:yield from references(item)


def select(items, budget):
    selected=[];size=0
    for item in items:
        cost=len(canonical(item).encode())
        if size+cost<=budget:selected.append(item);size+=cost
    return selected


def fit(packed, measure, dynamic_limit, total_limit, optional_body_bytes=OPTIONAL_BODY_BYTES,economy=False,evidence_first=False):
    """Keep current receipts intact; spend the remaining space on older originals.

    measure includes the immutable prefix, native messages and JSON escaping.
    The caller retains the hard guard for irreducible mandatory input.
    """
    data=deepcopy(packed);originals=data.get('sources',{})
    evidence=rows(data.get('evidence'))
    protected=set(references(data.get('observations',{})))
    protected.update(references(data.get('focus',{}).get('received_requests',{})))
    preferred=set()
    for value in (data.get('belief') or {}, data.get('strategy') or {}):
        for key in ('sources','evidence_ids','testimony_ids'):preferred.update(value.get(key,[]))
    for entry in data.get('memory',{}).get('entries',[]):preferred.update(entry['sources'])
    # Most recently acquired records break ties without guessing semantic truth.
    order={row.get('source_ref',row['id']):i for i,row in enumerate(evidence)}
    candidates=sorted((key for key in originals if key not in protected),
        key=lambda key:((key not in order,) if evidence_first else ())+
                       (key not in preferred, originals[key].get('location')!=data.get('location'),
                        -order.get(key,-1),key))
    optional=select([(key,originals[key]) for key in candidates],optional_body_bytes)
    optional_ids=[key for key,_ in optional]
    data['sources']={key:body for key,body in originals.items() if key in protected or key in optional_ids}
    relevant=set(data['sources'])|preferred
    ordered_evidence=sorted(evidence,key=lambda row:(row['id'] not in relevant,-order.get(row.get('source_ref',row['id']),-1)))
    catalog=[{'id':row['id'],'title':originals.get(row.get('source_ref',row['id']),{}).get('title',''),
              'location':originals.get(row.get('source_ref',row['id']),{}).get('location')}
             for row in ordered_evidence]
    catalog=select(catalog,2000 if economy else 4000)
    evidence=select(ordered_evidence,4000 if economy else 6000)
    data['evidence']=compact_context.table(evidence)
    data['evidence_catalog']=compact_context.table(catalog)
    data['source_access']={'version':1,'list_tool':'list_sources','read_tool':'read_sources',
        'missing_body':'on_demand_not_unknown','max_tool_rounds':2}
    data.pop('source_lookup',None)
    totals={'evidence':len(ordered_evidence),'source_bodies':len(originals)}
    # The full received-ID set remains in state and in the authorization checks.
    heard=data.get('heard_statement_ids',[])
    totals['heard_statements']=len(heard)
    supplied={row['id'] for key in ('observations','recalled_sources') for row in rows(data.get(key))}
    data['heard_statement_ids']=select([key for key in heard if key in supplied or key in preferred][::-1],1000 if economy else 2000)
    provenance=data.get('source_provenance',{})
    totals['source_origins']=len(provenance)
    origin_items=sorted(provenance.items(),key=lambda item:(item[0] not in protected,item[0] not in relevant,item[0]))
    data['source_provenance']=dict(select(origin_items,2000 if economy else 4000))
    receipts=rows(data.get('presentation_receipts'))
    totals['presentation_receipts']=len(receipts)
    data['presentation_receipts']=compact_context.table(select(sorted(receipts,key=lambda row:row['id'] not in relevant),1500 if economy else 3000))

    def refresh():
        data['working_context']={'version':1,'totals':totals,
            'included':{'source_bodies':len(data['sources']),'evidence':len(rows(data['evidence'])),
                'evidence_catalog':len(rows(data['evidence_catalog'])),
                'heard_statements':len(data['heard_statement_ids']),
                'source_origins':len(data['source_provenance']),
                'presentation_receipts':len(rows(data['presentation_receipts']))},
            'indexes_are_partial':True,'originals_preserved':True}
    refresh()
    def over_target():
        size=measure(data)
        return size['dynamic_bytes']>min(28_000 if economy else SOFT_DYNAMIC_BYTES,dynamic_limit) or size['total_bytes']>min(68_000 if economy else SOFT_TOTAL_BYTES,total_limit)
    # Native tool receipts and validation feedback are never truncated or removed.
    while optional_ids and over_target():
        data['sources'].pop(optional_ids.pop(),None);refresh()
    # All these indexes can be retrieved through the scoped directory/read tools.
    for key in ('source_provenance','heard_statement_ids','presentation_receipts','evidence_catalog','evidence'):
        while over_target():
            value=data[key]
            if isinstance(value,dict) and 'rows' in value:
                if not value['rows']:break
                value['rows'].pop()
            elif isinstance(value,dict):
                if not value:break
                value.pop(next(reversed(value)))
            elif value:value.pop()
            else:break
            refresh()
    return data
