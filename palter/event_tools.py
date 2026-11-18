"""Native role tools with scoped arguments, durable receipts and bounded feedback."""
from copy import deepcopy
import json

from . import role_events, role_schedule as scheduling
from .storage import canonical
from . import model_contracts as contract


def validate_call(state,actor,tool):
    if tool.get('type')!='function' or not isinstance(tool.get('id'),str) or not tool['id'] or len(tool['id'])>200:raise ValueError('tool call identity')
    function=tool.get('function',{})
    if function.get('name')!='create_event_listener':raise ValueError('role tool not allowed')
    args=json.loads(function['arguments'])
    required={'description','event_ids','completion_condition','early_end_condition'}
    optional={'end_on'} if state.get('workflow_events_version') else set()
    if not isinstance(args,dict) or not required<=set(args) or set(args)-required-optional:raise ValueError('event tool arguments')
    end_on=args.get('end_on',[])
    fixed={o['id'] for o in scheduling.options(state,actor) if o['id'].partition(':')[0] in ('phase','activity','invitation','conversation')}
    if not isinstance(end_on,list) or len(end_on)>contract.LISTENER_TARGETS or any(not isinstance(k,str) for k in end_on) or len(set(end_on))!=len(end_on) or not set(end_on)<=fixed:
        raise contract.ContractError('end_on',f'Use at most {contract.LISTENER_TARGETS} distinct authorized fixed event IDs.')
    if args['event_ids'] and end_on:raise ValueError('end_on belongs to custom listeners')
    for key,limit in contract.EVENT_TEXT.items():
        contract.text(args[key],key,limit,empty=key!='description')
    if not args['description'].strip():raise ValueError('listener description')
    ids=args['event_ids']
    if not isinstance(ids,list) or len(ids)>contract.LISTENER_TARGETS or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids):raise contract.ContractError('event_ids',f'Use at most {contract.LISTENER_TARGETS} distinct string IDs.')
    if ids:
        allowed={o['id'] for o in scheduling.options(state,actor) if not o['id'].startswith('listener:')}
        if not set(ids)<=allowed or args['completion_condition'] or args['early_end_condition']:raise ValueError('fixed listener scope')
    else:
        role_events.validate({'event_request':{k:args[k] for k in ('description','completion_condition','early_end_condition')}},role_events.role_context(state,actor))
    return args


def execute(state,actor,tool,call_id):
    args=json.loads(tool['function']['arguments'])
    records=state.setdefault('event_tool_receipts',[])
    prior=next((r for r in records if r['call_id']==call_id and r['tool_call_id']==tool['id']),None)
    if prior:
        if prior['actor']!=actor or prior['arguments']!=args:raise ValueError('tool receipt conflict')
        return deepcopy(prior['result'])
    args=validate_call(state,actor,tool)
    targets=list(args['event_ids']);status='registered'
    if not targets:
        identity=role_events.request(state,actor,{'event_request':{k:args[k] for k in ('description','completion_condition','early_end_condition')}})
        if args.get('end_on'):
            next(e for e in state['tracked_events'] if e['id']==identity)['end_on']=list(args['end_on'])
        targets=['tracked:'+identity];status='pending_dm'
    listeners=state.setdefault('event_listeners',[]);identity='listener-'+str(len(listeners)+1)
    listeners.append({'id':identity,'actor':actor,'description':args['description'],'events':targets})
    result={'listener_id':identity,'wait_event':'listener:'+identity,'status':status,
            'description':args['description'],'events':targets}
    records.append({'actor':actor,'call_id':call_id,'tool_call_id':tool['id'],'name':'create_event_listener',
                    'arguments':deepcopy(args),'result':deepcopy(result)})
    return result


def decide(state,actor,call,baseline,data,validate,allowed):
    """One optional native tool batch followed by one final decision, no idle loop."""
    if data.get('context_format')==1:
        return decide_compact(state,actor,call,baseline,data,validate,allowed)
    def validate_response(out):
        if '_tool_message' not in out:return validate(out)
        message=out['_tool_message'];calls=message.get('tool_calls')
        if not isinstance(calls,list) or not 1<=len(calls)<=2:raise ValueError('role tool batch limit')
        if len({t.get('id') for t in calls})!=len(calls):raise ValueError('duplicate tool call id')
        arguments=[validate_call(state,actor,tool) for tool in calls]
        if sum(not args['event_ids'] for args in arguments)+len(role_events.role_context(state,actor)['active'])>2:raise ValueError('event capacity')
    out,cid=call('role_'+actor,'ensemble_role',baseline,data,validate_response,actor)
    if '_tool_message' not in out:return out,cid
    message=out['_tool_message'];messages=[deepcopy(message)];custom_waits=[]
    for tool in message['tool_calls']:
        result=execute(state,actor,tool,cid)
        if result['status']=='pending_dm':custom_waits.append(result['wait_event'])
        messages.append({'role':'tool','tool_call_id':tool['id'],'content':canonical(result)})
    # Tool definitions and generic protocol remain unchanged. Only this actor's
    # new instances and the native call/result messages enter the dynamic suffix.
    data['scheduling']=scheduling.context(state,actor,
        limit_waits=data.get('scheduling',{}).get('wait_frequency',{}).get('version',int('wait_frequency' in data.get('scheduling',{}))),
        explicit_options='decision_options' in data.get('scheduling',{}),
        own_action_completion=bool(data.get('scheduling',{}).get('own_action_completion')),
        message_wait_guard=bool(data.get('scheduling',{}).get('message_wait_guard')))
    data['event_tracking']=role_events.role_context(state,actor)
    data['_tool_messages']=messages
    allowed.update(o['id'] for o in state['observations'][actor])
    def final_only(out):
        if '_tool_message' in out:raise ValueError('one event tool batch per decision')
        validate(out)
        if custom_waits and out['next_decision']['mode']=='wait' and set(out['next_decision']['events'])!=set(custom_waits):
            raise ValueError('new custom listener wait must reference the complete proposal')
    return call('role_'+actor+'_after_tools','ensemble_role',baseline,data,final_only,actor)


def decide_compact(state,actor,call,baseline,data,validate,allowed):
    from . import compact_context, source_access
    bounded=data.get('source_access',{}).get('version')==1
    used=set();messages=[];custom_waits=[]
    for round_index in range(3):
        def check(out):
            if '_tool_message' not in out:
                validate(out)
                if custom_waits and out['next_decision']['mode']=='wait' and set(out['next_decision']['events'])!=set(custom_waits):
                    raise ValueError('wait must use registered custom listeners')
                return
            if round_index==2:raise ValueError('tool continuation budget exhausted')
            calls=out['_tool_message'].get('tool_calls')
            if not isinstance(calls,list) or not 1<=len(calls)<=3:raise ValueError('tool batch limit')
            identities=[t.get('id') for t in calls]
            if any(not isinstance(i,str) or not i or len(i)>200 for i in identities) or len(set(identities))!=len(identities):raise ValueError('tool call identities')
            kinds=[];custom=0
            for tool in calls:
                name=tool.get('function',{}).get('name');kinds.append(name)
                if name in used and not (bounded and name in ('read_sources','list_sources')):raise ValueError('tool family already used this decision')
                if bounded and name in ('read_sources','list_sources'):
                    source_access.execute(state,actor,tool)
                elif name=='read_sources':
                    if tool.get('type')!='function':raise ValueError('tool type')
                    compact_context.lookup(state,actor,json.loads(tool['function']['arguments']))
                else:
                    args=validate_call(state,actor,tool);custom+=not args['event_ids']
            if kinds.count('read_sources')>1 or kinds.count('list_sources')>1 or kinds.count('create_event_listener')>2:raise ValueError('tool family batch limit')
            if custom+len(role_events.role_context(state,actor)['active'])>2:raise ValueError('event capacity')
        stage='role_'+actor+(('_continuation_'+str(round_index)) if round_index else '')
        out,cid=call(stage,'ensemble_role',baseline,data,check,actor)
        if '_tool_message' not in out:return out,cid
        message=out['_tool_message'];messages.append(deepcopy(message))
        for tool in message['tool_calls']:
            name=tool['function']['name'];used.add(name)
            if bounded and name in ('read_sources','list_sources'):result=source_access.execute(state,actor,tool)
            elif name=='read_sources':result=compact_context.lookup(state,actor,json.loads(tool['function']['arguments']))
            else:
                result=execute(state,actor,tool,cid)
                if result['status']=='pending_dm':custom_waits.append(result['wait_event'])
            messages.append({'role':'tool','tool_call_id':tool['id'],'content':canonical(result)})
        data['scheduling']=scheduling.context(state,actor,
            limit_waits=data.get('scheduling',{}).get('wait_frequency',{}).get('version',int('wait_frequency' in data.get('scheduling',{}))),
            explicit_options='decision_options' in data.get('scheduling',{}),
            own_action_completion=bool(data.get('scheduling',{}).get('own_action_completion')),
            message_wait_guard=bool(data.get('scheduling',{}).get('message_wait_guard')))
        data['event_tracking']=role_events.role_context(state,actor)
        data['_tool_messages']=deepcopy(messages)
        allowed.update(o['id'] for o in state['observations'][actor])
    raise ValueError('decision did not terminate')
