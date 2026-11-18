"""Per-dimension submissions with one mechanically derived citation union."""
from copy import deepcopy

LABELS={'identity':'人物与机会','time':'时间边界','method':'作案手法'}


def dimensions(case):
    return [k for k in LABELS if k in case['proofs']]+[k for k in case['proofs'] if k not in LABELS]


def normalize(state,actor,value):
    from . import output_contracts as checks
    if not isinstance(value,dict) or set(value)!={'suspect','aspects'} or value['suspect'] not in (None,'A','B','C','D'):
        raise ValueError('final conclusion requires suspect and aspects')
    rows=value['aspects'];required=dimensions(state['case'])
    if not isinstance(rows,list) or len(rows)!=len(required):raise ValueError('one final argument per dimension')
    heard={o['id'] for o in state['observations'][actor] if o['kind']=='testimony'}
    seen=set();evidence=[];testimony=[];words=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'aspect','explanation','evidence_ids','testimony_ids','gaps'}:
            raise ValueError('final aspect fields')
        aspect=row['aspect']
        if not isinstance(aspect,str) or aspect not in required or aspect in seen:raise ValueError('final aspect identity')
        seen.add(aspect);checks.text(row['explanation'],f'final_conclusion.{aspect}.explanation',1200,True)
        checks.text(row['gaps'],f'final_conclusion.{aspect}.gaps',400,True)
        checks.references(row['evidence_ids'],set(state['known'][actor]),f'final_conclusion.{aspect}.evidence_ids')
        checks.references(row['testimony_ids'],heard,f'final_conclusion.{aspect}.testimony_ids')
        evidence.extend(row['evidence_ids']);testimony.extend(row['testimony_ids'])
        words.append(LABELS.get(aspect,aspect)+'：'+row['explanation']+('；未解决：'+row['gaps'] if row['gaps'] else ''))
    return {**deepcopy(value),'explanation':'\n'.join(words),'evidence_ids':list(dict.fromkeys(evidence)),
            'testimony_ids':list(dict.fromkeys(testimony))}
