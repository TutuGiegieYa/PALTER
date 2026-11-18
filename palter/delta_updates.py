"""Versioned field patches expanded before the existing atomic validators."""
from copy import deepcopy
from . import memory_entries


class ContractError(ValueError):
    def __init__(self, field, requirement):
        super().__init__(field + ': ' + requirement)
        self.feedback={'code':'role_contract','field':field,'instruction':requirement+
            ' Return a complete coherent role decision; no action or memory has been applied.'}


def fields(prior, patch, allowed, list_fields):
    if not isinstance(patch,dict) or set(patch)-set(allowed)-{k+s for k in list_fields for s in ('_add','_remove')}:
        raise ContractError('patch','Use only defined fields and their documented list add/remove operations.')
    out=deepcopy(prior)
    for key in allowed:
        if key in patch:out[key]=deepcopy(patch[key])
    for key in list_fields:
        add=patch.get(key+'_add',[]);remove=patch.get(key+'_remove',[])
        if key in patch and (key+'_add' in patch or key+'_remove' in patch):
            raise ContractError(key,'Choose a full list replacement OR add/remove, never both.')
        if any(not isinstance(v,list) or any(not isinstance(x,str) for x in v) or len(v)!=len(set(v)) for v in (add,remove)):
            raise ContractError(key,'List edits require distinct string IDs.')
        if set(add)&set(remove) or not set(remove)<=set(out.get(key,[])):
            raise ContractError(key,'Remove only existing IDs; do not both add and remove an ID.')
        if add or remove:out[key]=list(dict.fromkeys([x for x in out.get(key,[]) if x not in remove]+add))
    return out


def interpretation(prior,value,allowed,lists,key):
    if not isinstance(value,dict) or 'patch' not in value:return value
    patch=value['patch']
    if not isinstance(patch,dict):raise ContractError(key+'.patch','Supply an object of changed fields.')
    names=set(allowed)|{k+s for k in lists for s in ('_add','_remove')}
    extra=set(value)-{'patch'}
    if extra-names:raise ContractError(key,'Use patch plus only defined interpretation fields; do not mix clear with a patch.')
    merged=deepcopy(patch)
    for field in sorted(extra):
        if field in merged and merged[field]!=value[field]:
            raise ContractError(key+'.'+field,'Conflicting outer and patch values; supply one unambiguous value inside patch.')
        merged[field]=deepcopy(value[field])
    try:return fields(prior,merged,allowed,lists)
    except ContractError as exc:
        raise ContractError(key+'.'+exc.feedback['field'],exc.feedback['instruction']) from None


def expand(state, actor, raw):
    out=deepcopy(raw)
    update=out.get('memory_update')
    if isinstance(update,dict):
        prior={r['id']:r for r in memory_entries.entries(state['memory'][actor])}
        update.setdefault('upsert',[]);update.setdefault('archive',[])
        if 'processed_through' not in update:raise ContractError('memory_update.processed_through','Supply a received observation ID or null.')
        if not isinstance(update['upsert'],list):raise ContractError('memory_update.upsert','Supply an array.')
        rows=[]
        for row in update['upsert']:
            if not isinstance(row,dict) or not isinstance(row.get('id'),str):raise ContractError('memory_update.upsert','Each patch needs a string id.')
            used={k:v for k,v in row.items() if k in (*memory_entries.ENTRY_FIELDS,'sources_add','sources_remove')}
            value=fields(prior.get(row['id'],{}),used,('id','kind','text','sources'),('sources',))
            if not set(memory_entries.ENTRY_FIELDS)<=set(value):raise ContractError('memory_update.upsert','New entries require id, kind, text and sources; existing entries may omit unchanged fields.')
            rows.append(value)
        update['upsert']=rows
    for key,prior,allowed,lists in (
        ('belief_update',{'suspect':None,'explanation':'','evidence_ids':[],'testimony_ids':[],**(state['beliefs'][actor] or {})},
         ('suspect','explanation','evidence_ids','testimony_ids'),('evidence_ids','testimony_ids')),
        ('strategy_update',{'situation':'','plan':'','sources':[],**(state.get('strategies',{}).get(actor) or {})},
         ('situation','plan','sources'),('sources',))):
        if key in out:out[key]=interpretation(prior,out[key],allowed,lists,key)
    return out
