"""Versioned read-only, recipient-scoped source discovery and original retrieval."""
from copy import deepcopy
import json

from .storage import canonical
from . import model_contracts as contract

LIST_BYTES=4096
READ_BYTES=8192


def available(state,actor):
    result={o['id']:o for o in state['observations'][actor]}
    result.update(state['known'][actor])
    result.update({f['id']:f for f in state['case']['history'] if f['id'] in state['case']['roles'][actor]['knows']})
    return result


def kind(state,actor,identity,row):
    if identity in state['known'][actor]:return 'evidence'
    if identity in state['case']['roles'][actor]['knows']:return 'initial'
    return 'testimony' if row.get('kind')=='testimony' else 'observation'


def directory(state,actor,args):
    if not isinstance(args,dict) or set(args)-{'kind','query','offset'} or args.get('kind') not in ('evidence','testimony','observation','initial'):
        raise ValueError('source directory kind')
    query=args.get('query','');offset=args.get('offset',0)
    if not isinstance(query,str) or len(query)>contract.SOURCE_ID_LENGTH or type(offset) is not int or offset<0:raise ValueError('source directory range')
    matches=[]
    for identity,row in reversed(list(available(state,actor).items())):
        if kind(state,actor,identity,row)!=args['kind']:continue
        if query and query.casefold() not in ' '.join(str(row.get(k,'')) for k in ('id','title','text','observation','speaker','speaker_name')).casefold():continue
        matches.append((identity,row))
    result={'kind':args['kind'],'total':len(matches),'offset':offset,'rows':[],
            'next_offset':None,'complete':True,'byte_limit':LIST_BYTES}
    for index,(identity,row) in enumerate(matches[offset:],offset):
        item={'id':identity,'kind':row.get('kind', 'acquired_record' if args['kind']=='evidence' else 'initial_fact')}
        for key in ('title','speaker','speaker_name','event_id','acquired_event','location'):
            if key in row:item[key]=deepcopy(row[key])
        if len(canonical(item).encode())>2000:
            item={'id':identity,'kind':item['kind'],'metadata_deferred':True}
        if args['kind']!='evidence':
            original=row.get('text',row.get('observation',''))
            item['preview']=original[:100];item['preview_is_excerpt']=len(original)>100
        trial=deepcopy(result);trial['rows'].append(item)
        trial.update(next_offset=index+1 if index+1<len(matches) else None,complete=index+1>=len(matches))
        if len(canonical(trial).encode())>LIST_BYTES or len(trial['rows'])>32:
            result.update(next_offset=index,complete=False);break
        result=trial
    return result


def lookup(state,actor,args):
    if not isinstance(args,dict) or set(args)!={'requests'}:raise ValueError('source lookup arguments')
    requests=args['requests']
    if not isinstance(requests,list) or not 1<=len(requests)<=8:raise ValueError('source lookup batch')
    for index,request in enumerate(requests):
        if not isinstance(request,dict) or 'id' not in request or set(request)-{'id','offset'}:raise ValueError('source lookup request')
        contract.text(request['id'],f'requests[{index}].id',contract.SOURCE_ID_LENGTH,empty=True)
        if type(request.get('offset',0)) is not int or request.get('offset',0)<0:raise ValueError('source lookup range')
    sources=available(state,actor)
    result={'sources':[],'range_unit':'characters','response_byte_limit':READ_BYTES}
    from . import evidence_sharing
    sharing=evidence_sharing.for_role(state,actor,witnessed=bool(state.get('exploration_version'))) if state.get('evidence_sharing_version') else {}
    for index,request in enumerate(requests):
        identity=request['id'];offset=request.get('offset',0)
        if identity not in sources:
            result['sources'].append({'id':identity,'status':'unavailable'});continue
        original=sources[identity];text=original.get('text',original.get('observation',''))
        if offset>len(text):result['sources'].append({'id':identity,'status':'invalid_range'});continue
        origin=kind(state,actor,identity,original)
        if origin=='evidence' and state.get('exploration_version'):
            from . import exploration
            original=exploration.evidence(state,actor,[original])[0]
        provenance=('self_claim' if original.get('speaker')==actor else 'heard_claim') if origin=='testimony' else {
            'evidence':'acquired_record','initial':'initial_fact','observation':'received_event'}[origin]
        row={'id':identity,'kind':original.get('kind','acquired_record' if origin=='evidence' else 'initial_fact'),
             'origin':provenance,'offset':offset,'total_characters':len(text)}
        if original.get('kind')=='evidence':row['origin']='record_receipt'
        for key in ('title','speaker','speaker_name','channel','event_id','acquired_event','via','location','source','temporal','clock_calibration','author','category','evidence_id','arrival_presence','acquisition'):
            if key in original:row[key]=deepcopy(original[key])
        if identity in sharing:row['presentation']=deepcopy(sharing[identity])
        def candidate(end):
            return {**row,'status':'complete' if offset==0 and end==len(text) else 'excerpt',
                'text':text[offset:end],'next_offset':end if end<len(text) else None}
        # Reserve small receipts for the remaining requested IDs, including errors.
        reserve=sum(len(canonical({'id':pending['id'],'status':'deferred','next_offset':pending.get('offset',0)}).encode())+32
                    for pending in requests[index+1:])
        def fits(end):return len(canonical({**result,'sources':result['sources']+[candidate(end)]}).encode())<=READ_BYTES-reserve
        if not fits(offset):
            result['sources'].append({'id':identity,'status':'deferred','next_offset':offset});continue
        lo,hi=offset,len(text)
        while lo<hi:
            middle=(lo+hi+1)//2
            if fits(middle):lo=middle
            else:hi=middle-1
        result['sources'].append(candidate(lo))
    return result


def execute(state,actor,tool):
    if tool.get('type')!='function':raise ValueError('source tool type')
    function=tool.get('function',{});args=json.loads(function['arguments'])
    if function.get('name')=='list_sources':return directory(state,actor,args)
    if function.get('name')=='read_sources':return lookup(state,actor,args)
    raise ValueError('source tool not allowed')


def memory_decision(state,actor,call,stage,baseline,data,validate):
    """At most two read-only batches, then one required memory snapshot."""
    data=deepcopy(data);messages=[]
    for round_index in range(3):
        def check(out):
            if '_tool_message' not in out:return validate(out)
            calls=out['_tool_message'].get('tool_calls')
            if round_index==2 or not isinstance(calls,list) or not 1<=len(calls)<=2:raise ValueError('memory source tool budget')
            ids=[tool.get('id') for tool in calls]
            if any(not isinstance(i,str) or not i or len(i)>200 for i in ids) or len(set(ids))!=len(ids):raise ValueError('source tool identities')
            for tool in calls:execute(state,actor,tool)
        out,cid=call(stage+(f'_continuation_{round_index}' if round_index else ''),'ensemble_memory',baseline,data,check,actor)
        if '_tool_message' not in out:return out,cid
        message=out['_tool_message'];messages.append(deepcopy(message))
        for tool in message['tool_calls']:
            messages.append({'role':'tool','tool_call_id':tool['id'],'content':canonical(execute(state,actor,tool))})
        data['_tool_messages']=deepcopy(messages)
    raise ValueError('memory source loop did not terminate')
