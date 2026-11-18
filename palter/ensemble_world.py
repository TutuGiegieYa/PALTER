"""Shared four-seat world, scoped knowledge, social obligations and causal effects."""

from copy import deepcopy
import secrets
import time

from .scenario_cases import ACTORS, SCENARIOS
from .storage import fingerprint, StoreError
from . import role_schedule as scheduling
from . import evidence_sharing
from . import exploration


def blank(identifier, scenario, humans, opening):
    return dict(id=identifier,mode='ai',gameplay='ensemble',revision=0,phase='introduction',archived=False,
        beat=0,round=0,outcome=None,title='正在准备故事',introduction='',scenario=scenario,
        humans=list(ACTORS[:humans]),opening=opening,join_code=secrets.token_hex(6) if humans else None,joined=['A'] if humans else [],
        ready=[],reading_deadline=None,intentions={},story=None,preview=None,case=None,case_hash=None,
        events=[],observations={a:[] for a in ACTORS},known={a:{} for a in ACTORS},locations={a:'r1' for a in ACTORS},
        memory={a:{'summary':'','sources':[],'checkpoint':0} for a in ACTORS},thoughts={a:[] for a in ACTORS},
        relationships={a:{} for a in ACTORS},beliefs={a:None for a in ACTORS},notes={a:{'text':'','evidence_ids':[]} for a in ACTORS},
        obligations={a:{'response':False,'explain':False,'sources':[]} for a in ACTORS},silent={a:0 for a in ACTORS},speech_interval=3,
        chats={},invitations=[],agenda=[],agenda_serial=0,background_error=None,objects={},items={},
        activities=[],following={},disruptions={},public_evidence=[],disclosures=[],assessments=[],
        contributions={a:[] for a in ACTORS},votes={},pledges={},commitments=[],submissions={},
        resources={a:2 for a in ACTORS},supplies={'battery':4,'supply':4},radio=False,route=False,
        switches=[0,0],dials=[1,1],vault=False,evacuated=[],blocked_room=None,world_due=False,world_count=0,
        last_world_beat=0,next_tick=0,ending=None,results=None)


def now(state):return state['watch']['clock'] if 'watch' in state else state.get('_operation_time',time.time())
def name(state,a):return state['case']['roles'][a]['name'] if state.get('case') else state['preview']['cast'][a]
def ai_roles(state):return [a for a in ACTORS if a not in state['humans']]
def chat_for(state,a):return next((c for c in state['chats'].values() if c['status']=='active' and a in c['participants']),None)
def local_communication(state):return state.get('communication_version',0)>=1
def audience(state,a):
    chat=chat_for(state,a)
    if chat:
        return [b for b in chat['participants'] if not local_communication(state) or state['locations'][b]==state['locations'][a]]
    return [b for b in ACTORS if not chat_for(state,b) and
            (not local_communication(state) or state['locations'][b]==state['locations'][a])]
def channel(state,a):
    chat=chat_for(state,a)
    return chat['id'] if chat else 'public'


def scene_presence(state,actor):
    """Current visible occupants, distinct from who can hear this channel."""
    room=state['locations'][actor];chat=chat_for(state,actor);listeners=audience(state,actor)
    people=[{'id':a,'name':name(state,a),'can_talk':a in listeners,
             'private_conversation':bool(chat_for(state,a))}
            for a in ACTORS if a!=actor and a not in state['evacuated']
            and state['locations'][a]==room and (not chat or a in chat['participants'])]
    return {'room_id':room,'scope':'private_conversation' if chat else 'area',
            'complete':not bool(chat),'people':people}


def arrival_description(presence):
    people=presence['people']
    if not people:return '这里没有其他人。'
    available='、'.join(p['name'] for p in people if p['can_talk'])
    occupied='、'.join(p['name'] for p in people if not p['can_talk'])
    return ((available+'也在这里，可以直接交流。' if available else '')+
            (occupied+'也在这里，正在私聊；你能看见他们，但听不到谈话内容，暂不能直接交流。' if occupied else ''))


def emit(state,kind,actor=None,target=None,**facts):
    e={'id':f'e{len(state["events"])+1:06d}','beat':state['beat'],'kind':kind,'actor':actor,'target':target,'facts':facts}
    state['events'].append(e);return e


def note(state,a,e,words,kind='observation',**extra):
    rows=state['observations'][a]
    rows.append(dict(id=f'{a}-o{len(rows)+1:06d}',event_id=e['id'],beat=state['beat'],text=words,kind=kind,**extra))


def announce(state,e,words,recipients=None):
    if recipients is None and local_communication(state) and e.get('actor') in state['locations']:
        recipients=audience(state,e['actor'])
    for a in recipients if recipients is not None else [a for a in ACTORS if not chat_for(state,a)]:note(state,a,e,words)


def enqueue(state,actor,reason,source=None,depth=0,interrupt=True):
    if scheduling.enabled(state) and (state['phase']=='ended' or actor in state['submissions']):return
    if scheduling.waiting(state,actor):
        if not interrupt:return
        depth=0
    closing=scheduling.enabled(state) and state.get('closure',{}).get('ready')
    if actor not in ai_roles(state) or (actor in state['evacuated'] and not closing) or depth>3:return
    if scheduling.enabled(state):state.setdefault('role_waits',{}).pop(actor,None)
    scope=channel(state,actor)
    if any(q['actor']==actor and q['channel']==scope for q in state['agenda']):return
    state['agenda_serial']+=1
    state['agenda'].append(dict(id=f'q{state["agenda_serial"]}',actor=actor,channel=scope,reason=reason,source=source,depth=depth))


def initialize(state,case):
    state['case']=deepcopy(case);state['case_hash']=fingerprint(case);state['title']=case['title']
    state['phase']='reading';state['reading_deadline']=now(state)+120 if len(state['humans'])>1 else None
    for a,role in case['roles'].items():
        state['memory'][a]['summary']='；'.join(role['memories'])
        state['relationships'][a]={b:{'description':description,'trust':0.,'affinity':0.,'experiences':[]} for b,description in role['relationships'].items()}
    state['objects']={c['id']:{'holder':c['location'],'condition':'intact','hidden':c['locked'],'protected':c['protected']} for c in case['clues']}
    state['items']=deepcopy(case['items'])
    # Each person can inspect their own private record; others must find it.
    for c in case['clues']:
        if c['private_owner']:state['objects'][c['id']]['holder']=c['private_owner']


def start(state):
    state['phase']='active';e=emit(state,'started')
    announce(state,e,state['case']['public_briefing'],list(ACTORS))
    for a in ai_roles(state):enqueue(state,a,'调查开始，决定自己的第一个行动。',e['id'])


def baseline(state,a):
    return {'actor':a,'profile':deepcopy(state['case']['roles'][a]),
            'experienced_facts':[deepcopy(f) for f in state['case']['history'] if f['id'] in state['case']['roles'][a]['knows']],
            'cast':{b:name(state,b) for b in ACTORS},'scenario':state['scenario']}


def perspective(state,a):
    """Derive decision focus from this role's own fixed knowledge and goal only."""
    if state['scenario']!='murder':return 'objectives'
    profile=state['case']['roles'][a]
    if 'crime' in profile['knows'] and any(g['kind']=='avoid' for g in profile['objectives']):return 'concealment'
    return 'investigation'


def speech_limit(state,a):
    # Three received lines in a four-person exchange are only one rotation.
    return state['speech_interval']*(max(1,len(audience(state,a))-1) if state.get('interaction_version',1)>=2 else 1)


def must_speak(state,a):
    # Leaving a conversation does not create a duty to speak to an empty area.
    listeners=not local_communication(state) or any(b!=a for b in audience(state,a))
    return state['obligations'][a]['explain'] or (listeners and state['silent'][a]>=speech_limit(state,a))


def snapshot(state,a):
    records=deepcopy(list(state['known'][a].values()))
    if state.get('exploration_version'):records=exploration.evidence(state,a,records)
    return {'evidence':records, 'memory':deepcopy(state['memory'][a]),
            'belief':deepcopy(state['beliefs'][a]),'observations':deepcopy(state['observations'][a][-12:])}


def speak(state,a,words,target=None,gesture=False,challenge=False,depth=0,allow_unheard=False):
    recipients=audience(state,a)
    if target not in (None,*ACTORS):raise StoreError('没有这个交谈对象。')
    unheard=target is not None and target not in recipients
    if unheard and not allow_unheard:raise StoreError('对方当前不在这个谈话范围内。')
    if gesture and must_speak(state,a):raise StoreError('这次需要用话语回应，动作不能代替解释或定期发言。')
    e=emit(state,'gesture' if gesture else 'testimony',a,target,text=words,channel=channel(state,a),recipients=recipients,
           locations=deepcopy(state['locations']),speaker_knowledge=snapshot(state,a))
    if local_communication(state):e['facts']['room']=state['locations'][a]
    if unheard:e['facts']['unheard_target']=target
    for b in recipients:
        note(state,b,e,words,e['kind'],speaker=a,speaker_name=name(state,a),channel=e['facts']['channel'])
        state['silent'][b]+=1
        if b!=a and must_speak(state,b):enqueue(state,b,'需要实际发言，不能一直旁观。',e['id'],depth+1,interrupt=False)
    if not gesture:state['silent'][a]=0
    state['obligations'][a]={'response':False,'explain':False,'sources':[]}
    if unheard:note(state,a,e,name(state,target)+'不在当前谈话范围，没有收到这次问话；原话只被当前谈话中的人听见。')
    if target and target!=a and not unheard:
        state['obligations'][target]['response']=True
        state['obligations'][target]['explain']|=challenge
        state['obligations'][target]['sources'].append(e['id'])
        enqueue(state,target,'收到需要解释的质证。' if challenge else '收到直接对话，请回应。',e['id'],depth+1)
    chat=chat_for(state,a)
    if chat:
        chat['turns'].append({'event_id':e['id'],'speaker':a,'text':words})
        partner=next(b for b in chat['participants'] if b!=a)
        if len(chat['turns'])<8:enqueue(state,partner,'继续这段已同意的私聊。',e['id'],0)
    state['round']+=1
    return e


def close_chat(state,chat):
    chat['status']='closed';e=emit(state,'private_closed',target=chat['id'])
    recipients=[a for a in ACTORS if a in chat['participants'] or not chat_for(state,a)]
    if local_communication(state):
        rooms={state['locations'][a] for a in chat['participants']}
        recipients=[a for a in recipients if a in chat['participants'] or state['locations'][a] in rooms]
    announce(state,e,'、'.join(name(state,a) for a in chat['participants'])+'结束了私聊。',
             recipients)
    state['agenda']=[q for q in state['agenda'] if q['channel']!=chat['id']]
    if scheduling.enabled(state):
        private_sources={e['id'] for e in state['events'] if e['facts'].get('channel')==chat['id']}
        for actor in chat['participants']:
            obligation=state['obligations'][actor]
            obligation['sources']=[s for s in obligation['sources'] if s not in private_sources]
            if not obligation['sources']:obligation.update(response=False,explain=False)


def expire(state):
    reconcile_communication(state)
    for c in list(state['chats'].values()):
        if c['status']=='active' and (len(c['turns'])>=8 or now(state)>=c['expires']):close_chat(state,c)
    for invitation in state['invitations']:
        if invitation['status']=='pending' and now(state)>=invitation['expires']:
            invitation['status']='expired';invitation_result(state,invitation)


def reconcile_communication(state):
    """Retire impossible legacy/pending conversations without replaying speech."""
    if not local_communication(state):return
    for chat in state['chats'].values():
        if chat['status']=='active' and len({state['locations'][a] for a in chat['participants']})>1:
            close_chat(state,chat)
    for invitation in state['invitations']:
        if invitation['status']=='pending' and state['locations'][invitation['from']]!=state['locations'][invitation['to']]:
            invitation['status']='expired';invitation_result(state,invitation)


def move_locally(state,a,target,e):
    """Separate observations from the authoritative route, including followers."""
    origin=state['locations'][a]
    followers=[]
    for follower,watched in list(state['following'].items()):
        if watched!=a:continue
        if state['locations'][follower]==origin and not chat_for(state,follower) and not running(state,follower):followers.append(follower)
        del state['following'][follower]
    travelling=[a,*followers]
    e['facts'].update(origin=origin,followers=followers,movement_views={})
    for actor in travelling:state['locations'][actor]=target
    for observer in ACTORS:
        extra={}
        if observer in travelling:
            words=('你' if observer==a else '你跟随'+name(state,a))+'来到'+state['case']['rooms'][target]['name']+'。'
            view={'visibility':'travel','args':[target],'location':target}
            if state.get('presence_version'):
                presence=scene_presence(state,observer)
                words+=arrival_description(presence)
                extra['arrival_presence']=presence
        elif not chat_for(state,observer) and state['locations'][observer]==origin:
            words='、'.join(name(state,b) for b in travelling)+'离开了这里。'
            view={'visibility':'departure','args':[],'location':origin}
        elif not chat_for(state,observer) and state['locations'][observer]==target:
            words='、'.join(name(state,b) for b in travelling)+'来到了这里。'
            view={'visibility':'arrival','args':[target],'location':target}
        else:continue
        note(state,observer,e,words,**extra)
        e['facts']['movement_views'][observer]=view
    for follower in followers:exploration.observe(state,follower)
    reconcile_communication(state)


def invitation_result(state,invitation):
    if not scheduling.enabled(state):return
    e=emit(state,'invitation_resolved',invitation['to'],invitation['from'],invitation_id=invitation['id'],status=invitation['status'])
    message={'accept':'已被接受','decline':'已被拒绝','expired':'已失效'}[invitation['status']]
    announce(state,e,name(state,invitation['from'])+'向'+name(state,invitation['to'])+'发出的私聊邀请'+message+'。',[invitation['from'],invitation['to']])


def definition(state,cid):
    return next((c for c in state['case']['clues'] if c['id']==cid),state.get('created_documents',{}).get(cid))


def acquire(state,a,cid,e,via):
    c=definition(state,cid)
    if cid not in state['known'][a]:
        record={k:deepcopy(c[k]) for k in ('id','title','observation','location','source','category')}
        for key in ('temporal','clock_calibration'):
            if key in c:record[key]=deepcopy(c[key])
        record.update(acquired_event=e['id'],via=via)
        state['known'][a][cid]=record;note(state,a,e,c['observation'],'evidence',evidence_id=cid)


def local_observers(state,a):
    return [b for b in ACTORS if b==a or (not chat_for(state,b) and state['locations'][b]==state['locations'][a])]


def running(state,a):return next((x for x in state['activities'] if x['actor']==a and x['status']=='running'),None)


def accessible(state,a,cid):
    obj=state['objects'][cid]
    return obj['condition']!='destroyed' and obj['holder'] in (a,state['locations'][a]) and (not obj['hidden'] or obj['holder']==a)


def choices(state,a):
    out=[]
    def add(cid,label):out.append({'id':cid,'label':label})
    add('wait','留意现场进展')
    closure=state.get('closure')
    if closure and a not in state['submissions']:
        if closure['ready']:
            add('lock_conclusion','独立提交并锁定自己的最终结论')
        elif not chat_for(state,a):
            add('close_vote:no' if a in closure['votes'] else 'close_vote:yes',
                '撤回结案意愿，继续调查' if a in closure['votes'] else '提议或同意结束调查，独立提交结论')
    if a in state['evacuated']:return out
    chat=chat_for(state,a)
    if chat:add('end_private','结束私聊')
    else:
        for b in ACTORS:
            if b!=a and b in audience(state,a) and not any(i['status']=='pending' and i['from']==a and i['to']==b for i in state['invitations']):add('invite:'+b,'邀请'+name(state,b)+'私聊')
        for i in state['invitations']:
            if i['status']=='pending' and i['to']==a and (not local_communication(state) or i['from'] in audience(state,a)):
                add('accept:'+i['id'],'接受'+name(state,i['from'])+'的私聊邀请');add('decline:'+i['id'],'拒绝这次邀请')
        if running(state,a):add('cancel_work','中止正在进行的行动')
        else:
            for r,room in state['case']['rooms'].items():
                if r!=state['locations'][a] and r!=state['blocked_room']:add('move:'+r,'前往'+room['name'])
            add('search','仔细搜查当前区域（2 个时间单位）')
            for b in ACTORS:
                if b!=a and state['locations'][a]==state['locations'][b] and not chat_for(state,b):add('follow:'+b,'留意并跟随'+name(state,b)+'的下一次移动')
            for cid,obj in state['objects'].items():
                if accessible(state,a,cid):
                    title=definition(state,cid)['title']
                    if cid not in state['known'][a]:add('inspect:'+cid,'检查'+title)
                    if not obj['protected']:
                        if obj['holder']==a:
                            add('place:'+cid,'放下'+title)
                            for b in ACTORS:
                                if b!=a and state['locations'][b]==state['locations'][a]:add('give:'+cid+':'+b,'把'+title+'交给'+name(state,b))
                        else:add('take:'+cid,'收起'+title)
                        category=state['disruptions'].get(a+':'+str(state['beat']//1440))
                        if state['scenario']!='murder' or category in (None,definition(state,cid)['category']):
                            if not obj['hidden']:add('hide:'+cid,'藏起'+title+'（2 个时间单位）')
                            add('destroy:'+cid,'销毁'+title+'（2 个时间单位）')
                    if state.get('interaction_version',1)<2 or not obj['protected']:add('protect:'+cid,'封存保护'+title)
                    if state.get('interaction_version',1)<2 or cid not in state.get('copies',{}).get(a,[]):add('copy:'+cid,'保存'+title+'的副本')
            for key,item in state['items'].items():
                if item['holder']==state['locations'][a] or (item['holder']=='vault' and state['vault'] and state['locations'][a]=='r3'):add('collect:'+key,'取走'+item['name'])
                if item['holder']==a:
                    for b in ACTORS:
                        if b!=a and state['locations'][b]==state['locations'][a]:add('transfer:'+key+':'+b,'把'+item['name']+'交给'+name(state,b))
            scenario=state['scenario']
            if scenario=='rescue':
                if not state['radio'] and state['locations'][a]=='r2' and state['supplies']['battery']>=2:add('repair','修复通讯（消耗 2 份电池，2 个时间单位）')
                if not state['route'] and state['locations'][a]=='r3' and state['supplies']['supply']>=2:add('clear_route','清理撤离通路（消耗 2 份补给，2 个时间单位）')
                if state['route'] and state['radio'] and state['locations'][a]=='r3':add('leave','乘接应离开')
            if scenario=='house':
                if state['locations'][a] in ('r2','r3'):add('switch:'+str(int(state['locations'][a][-1])-2),'切换这里的开关')
                if state['switches'][0]!=state['switches'][1] and state['locations'][a]=='r1':add('leave','通过已经接通的出口离开')
            if scenario=='archive' and state['locations'][a]=='r3':
                for d in range(2):
                    for value in range(1,4):add(f'dial:{d}:{value}',f'把第 {d+1} 枚转盘拨到 {value}')
    for cid,c in state['known'][a].items():add('share:'+cid,'出示'+c['title'])
    for b in audience(state,a):
        if b!=a:
            if state['scenario']=='family':add('promise:'+b,'向'+name(state,b)+'提出互相支持的承诺')
            if state['scenario']=='council':
                add('vote:'+b,'把自己的选票投给'+name(state,b));add('pledge:'+b,'承诺向'+name(state,b)+'提供一份资源')
                if state['resources'][a]>0:add('fund:'+b,'实际向'+name(state,b)+'转交一份资源')
    if state['scenario']=='council':add('vote:'+a,'投票支持自己')
    for c in state['commitments']:
        partner=c['to'] if c['from']==a else c['from']
        reachable=not local_communication(state) or partner in audience(state,a)
        if c['to']==a and c['status']=='proposed' and reachable:add('agree:'+c['id'],'接受'+name(state,c['from'])+'提出的承诺')
        if a in (c['from'],c['to']) and c['status']=='agreed' and reachable:add('withdraw:'+c['id'],'撤回与'+name(state,partner)+'的承诺')
    return out


def contribute(state,a,source):
    if source not in state['contributions'][a]:state['contributions'][a].append(source)


def publish_contribution(state,a,source):
    identity_routes=state['case']['proofs'].get('identity',[])
    if state['case'].get('rules_version',1)>=2 and any(source in route for route in identity_routes):
        first=state.setdefault('first_disclosures',{})
        credit=state['case'].get('evidence_equivalents',{}).get(source,source)
        if credit in first:return
        first[credit]=a
    contribute(state,a,source)


def apply_choice(state,a,choice,spoken=False,conclusion=None):
    start=len(state['events'])
    result=_apply_choice(state,a,choice,spoken,conclusion)
    if state.get('action_feedback_version'):
        from . import action_feedback
        action_feedback.record(state,a,choice,start)
    return result


def _apply_choice(state,a,choice,spoken=False,conclusion=None):
    if choice not in {x['id'] for x in choices(state,a)}:raise StoreError('当前条件不支持这个行动，请查看最新现场。')
    exploration.observe(state,a)
    kind,*parts=choice.split(':');target=parts[0] if parts else None
    if kind=='close_vote':
        closure=state['closure']
        if target=='yes':closure['votes'].append(a)
        else:closure['votes'].remove(a)
        e=emit(state,'closure_vote',a,agreed=target=='yes')
        announce(state,e,name(state,a)+('同意结束调查，准备提交自己的结论。' if target=='yes' else '撤回结案意愿，认为还需要调查。'),audience(state,a))
        if len(closure['votes'])>=3:
            closure['ready']=True
            for chat in state['chats'].values():
                if chat['status']=='active':close_chat(state,chat)
            announce(state,emit(state,'closure_agreed'),'已有三人同意结案。请各自独立锁定最终结论，提交完成后共同揭晓。',list(ACTORS))
            for b in ai_roles(state):enqueue(state,b,'已经达成结案约定，请独立提交自己的最终结论。')
        return e
    if kind=='lock_conclusion':
        state['submissions'][a]=deepcopy(conclusion if conclusion is not None else state['beliefs'][a] or {'suspect':None,'explanation':'','evidence_ids':[]})
        e=emit(state,'conclusion_locked',a)
        announce(state,e,name(state,a)+'已锁定自己的最终结论，内容暂不公开。',list(ACTORS))
        return e
    if kind=='invite':
        if spoken:
            e=emit(state,'invitation',a,target)
            announce(state,e,name(state,a)+'向'+name(state,target)+'发出私聊邀请，等待同意。',audience(state,a))
            state['obligations'][target]['response']=True;state['obligations'][target]['sources'].append(e['id'])
            enqueue(state,target,'请决定是否接受私聊邀请。',e['id'])
        else:e=speak(state,a,name(state,target)+'，我想和你单独聊聊，可以吗？',target)
        state['invitations'].append(dict(id=f'i{len(state["invitations"])+1}',from_=a,**{'from':a},to=target,status='pending',expires=now(state)+300))
        return e
    if kind in ('accept','decline'):
        inv=next(i for i in state['invitations'] if i['id']==target)
        if local_communication(state) and inv['from'] not in audience(state,a):raise StoreError('对方已经不在同一区域，请见面后重新邀请。')
        if chat_for(state,inv['from']):raise StoreError('发起者已进入其他私聊。')
        if spoken:
            e=emit(state,'invitation_reply',a,inv['from'],accepted=kind=='accept')
            announce(state,e,name(state,a)+('接受了' if kind=='accept' else '拒绝了')+name(state,inv['from'])+'的私聊邀请。',audience(state,a))
        else:e=speak(state,a,'我同意单独聊聊。' if kind=='accept' else '我想先留在这里。')
        inv['status']=kind
        invitation_result(state,inv)
        if kind=='accept':
            cid=f'private-{len(state["chats"])+1}';participants=[inv['from'],a]
            state['chats'][cid]=dict(id=cid,participants=participants,status='active',turns=[],expires=now(state)+300,
                                      baseline={b:baseline(state,b) for b in participants})
            if scheduling.enabled(state):state['chats'][cid]['started_by']=e['id']
            for i in state['invitations']:
                if i['status']=='pending' and any(b in participants for b in (i['from'],i['to'])):
                    i['status']='expired';invitation_result(state,i)
            state['agenda']=[q for q in state['agenda'] if q['actor'] not in participants]
            enqueue(state,inv['from'],'私聊已经得到同意，可以开始。',e['id'])
        return e
    if kind=='end_private':close_chat(state,chat_for(state,a));return state['events'][-1]
    e=emit(state,kind,a,target)
    if state.get('exploration_version'):
        e['facts']['location']=state['locations'][a]
        if target in state['objects']:e['facts']['evidence_holder']=state['objects'][target]['holder']
    if kind=='inspect':acquire(state,a,target,e,'亲自检查');return e
    if kind=='share':
        if state.get('evidence_sharing_version'):
            e['facts'].update(channel=channel(state,a),recipients=audience(state,a))
        if local_communication(state):e['facts']['room']=state['locations'][a]
        for b in audience(state,a):
            if target not in state['known'][b]:
                state['known'][b][target]=deepcopy(state['known'][a][target]);note(state,b,e,state['known'][a][target]['observation'],'evidence',evidence_id=target)
                if state.get('exploration_version'):
                    state['known'][b][target].update(acquired_event=e['id'],via='由'+name(state,a)+'出示')
        announce(state,e,name(state,a)+'出示了'+state['known'][a][target]['title']+'。',audience(state,a))
        if channel(state,a)=='public' and (not local_communication(state) or any(b!=a for b in audience(state,a))):
            for disclosed in [target,*definition(state,target).get('reveals',[])]:
                if disclosed not in state['public_evidence']:state['public_evidence'].append(disclosed)
                publish_contribution(state,a,disclosed)
        return e
    if kind=='wait':return e
    if kind=='move':
        if local_communication(state):
            move_locally(state,a,target,e)
            advance(state);exploration.observe(state,a)
            return e
        origin=state['locations'][a];state['locations'][a]=target
        recipients=[b for b in ACTORS if b==a or (not chat_for(state,b) and state['locations'][b] in (origin,target))]
        announce(state,e,name(state,a)+'前往'+state['case']['rooms'][target]['name']+'。',recipients)
        for follower,watched in list(state['following'].items()):
            if watched==a:
                if state['locations'][follower]==origin and not chat_for(state,follower) and not running(state,follower):
                    state['locations'][follower]=target;note(state,follower,e,'你看到'+name(state,a)+'离开，并跟随到了'+state['case']['rooms'][target]['name']+'。')
                    if state.get('exploration_version'):e['facts'].setdefault('followers',[]).append(follower)
                    exploration.observe(state,follower)
                del state['following'][follower]
    elif kind=='follow':state['following'][a]=target;note(state,a,e,'你开始留意'+name(state,target)+'下一次可见的移动。')
    elif kind in ('take','place','give','protect','copy'):
        obj=state['objects'][target];title=definition(state,target)['title']
        if kind=='take':obj.update(holder=a,hidden=False);acquire(state,a,target,e,'收取时检查')
        elif kind=='place':obj.update(holder=state['locations'][a],hidden=False)
        elif kind=='give':obj.update(holder=parts[1],hidden=False);acquire(state,parts[1],target,e,'收到实物')
        elif kind=='protect':obj['protected']=True
        else:
            acquire(state,a,target,e,'保存副本')
            if state.get('interaction_version',1)>=2:state.setdefault('copies',{}).setdefault(a,[]).append(target)
        announce(state,e,name(state,a)+{'take':'收起了','place':'放下了','give':'交出了','protect':'封存了','copy':'复制了'}[kind]+title+'。',local_observers(state,a))
        contribute(state,a,e['id'])
    elif kind in ('search','hide','destroy','repair','clear_route'):
        if kind in ('hide','destroy') and state['scenario']=='murder':
            category=definition(state,target)['category'];key=a+':'+str(state['beat']//1440)
            if key in state['disruptions'] and state['disruptions'][key]!=category:raise StoreError('本日只能干预一种证据类别。')
            state['disruptions'][key]=category
        if kind in ('repair','clear_route'):state['supplies']['battery' if kind=='repair' else 'supply']-=2
        state['activities'].append(dict(id=e['id'],actor=a,kind=kind,target=target,location=state['locations'][a],
                                        status='running',start=state['beat'],end=state['beat']+2))
        state['next_tick']=now(state)+2
        note(state,a,e,'你开始'+next(x['label'] for x in choices_for_label(kind,target))+'；可以在完成前中止。')
    elif kind=='cancel_work':
        task=running(state,a);task['status']='cancelled'
        if scheduling.enabled(state):e['kind']='action_cancelled';e['facts']['started_by']=task['id']
        note(state,a,e,'你中止了正在进行的行动，已经投入的资源不会恢复。')
    elif kind in ('collect','transfer'):
        item=state['items'][target];item['holder']=a if kind=='collect' else parts[1]
        announce(state,e,name(state,a)+('取走了' if kind=='collect' else '交出了')+item['name']+'。',local_observers(state,a));contribute(state,a,e['id'])
        if kind=='transfer':contribute(state,parts[1],e['id'])
    elif kind=='switch':
        index=int(target);state['switches'][index]=1-state['switches'][index]
        announce(state,e,'你们看到照明随开关变化，出口指示灯'+('亮起。' if state['switches'][0]!=state['switches'][1] else '熄灭。'),local_observers(state,a));contribute(state,a,e['id'])
    elif kind=='dial':
        state['dials'][int(target)]=int(parts[1]);state['vault']=state['dials']==state['case']['solution']['dials']
        announce(state,e,'转盘停在新的位置，内柜'+('打开了。' if state['vault'] else '仍然关闭。'),local_observers(state,a));contribute(state,a,e['id'])
    elif kind=='leave':
        state['evacuated'].append(a);announce(state,e,name(state,a)+'安全离开了。');contribute(state,a,e['id'])
    elif kind=='promise':
        state['commitments'].append(dict(id=e['id'],**{'from':a},to=target,status='proposed'))
        announce(state,e,name(state,a)+'向'+name(state,target)+'提出互相支持的承诺，等待对方同意。',audience(state,a));enqueue(state,target,'请决定是否接受承诺。',e['id'])
    elif kind in ('agree','withdraw'):
        commitment=next(c for c in state['commitments'] if c['id']==target);commitment['status']='agreed' if kind=='agree' else 'withdrawn'
        announce(state,e,name(state,a)+('接受了双方承诺。' if kind=='agree' else '撤回了双方承诺。'),audience(state,a));contribute(state,a,e['id'])
    elif kind=='vote':state['votes'][a]=target;announce(state,e,name(state,a)+'投票支持'+name(state,target)+'。');contribute(state,a,e['id'])
    elif kind=='pledge':state['pledges'][a]={'target':target,'fulfilled':False};announce(state,e,name(state,a)+'承诺向'+name(state,target)+'提供一份资源。')
    elif kind=='fund':
        state['resources'][a]-=1;state['resources'][target]+=1
        if state['pledges'].get(a,{}).get('target')==target:state['pledges'][a]['fulfilled']=True
        announce(state,e,name(state,a)+'实际交给'+name(state,target)+'一份资源。');contribute(state,a,e['id'])
    advance(state)
    exploration.observe(state,a)
    return e


def choices_for_label(kind,target):
    return [{'label':{'search':'搜查当前区域','hide':'藏匿材料','destroy':'销毁材料','repair':'修复通讯','clear_route':'清理通路'}[kind]}]


def advance(state):
    state['beat']+=1
    if state['blocked_room'] and state['beat']>=state.get('blocked_until',0):
        state['blocked_room']=None;announce(state,emit(state,'route_reopened'),'临时检修完成，通路恢复开放。')
    for task in state['activities']:
        if task['status']!='running' or state['beat']<task['end']:continue
        a=task['actor'];kind=task['kind'];cid=task['target'];task['status']='completed'
        e=emit(state,'action_completed',a,cid,action=kind,started_by=task['id'])
        if state['locations'][a]!=task['location']:
            task['status']='failed';e['kind']='action_failed';note(state,a,e,'位置已经变化，这次行动未完成。');continue
        if kind=='search':
            found=[]
            for key,obj in state['objects'].items():
                if obj['holder']==task['location'] and obj['condition']!='destroyed' and obj['hidden']:
                    obj['hidden']=False;found.append(definition(state,key)['title'])
            note(state,a,e,'搜查完成：'+('、'.join(found) if found else '没有发现新的隐藏材料')+'。')
            exploration.observe(state,a)
        elif kind in ('hide','destroy'):
            obj=state['objects'][cid]
            if obj['protected'] or obj['condition']=='destroyed' or obj['holder'] not in (a,task['location']):
                task['status']='failed';e['kind']='action_failed';note(state,a,e,'材料的保管条件已经变化，行动没有成功。');continue
            obj.update(holder=task['location'],hidden=kind=='hide')
            if kind=='destroy':obj['condition']='destroyed'
            announce(state,e,name(state,a)+('藏起了' if kind=='hide' else '损毁了')+definition(state,cid)['title']+'。',local_observers(state,a))
            if any(b!=a for b in local_observers(state,a)):
                state['obligations'][a]['explain']=True;state['obligations'][a]['sources'].append(e['id'])
                note(state,a,e,'在场的人看到了你对材料的处理，这件事需要你开口解释。')
                enqueue(state,a,'被在场者看到处理材料，需要实际说话解释。',e['id'])
            # A new trace records a real action, without revealing an unobserved actor.
            traceid='trace'+str(len(state['events']))
            state.setdefault('created_documents',{})[traceid]=dict(id=traceid,title='新留下的处理痕迹',observation='这里新出现了翻动和材料处理的痕迹，不能单凭痕迹确定是谁造成的。',location=task['location'],source='现场表面',category='trace')
            state['objects'][traceid]={'holder':task['location'],'condition':'intact','hidden':False,'protected':False}
        elif kind=='repair':state['radio']=True;announce(state,e,'通讯已修复，接应确认收到信号。')
        elif kind=='clear_route':state['route']=True;announce(state,e,'撤离通路已经清理完成。')
        contribute(state,a,e['id'])
    state['next_tick']=now(state)+2
    if state['beat']-state['last_world_beat']>=6 and state['world_count']<4:state['world_due']=True


def context(state,a):
    result= {'actor':a,'location':state['locations'][a],'rooms':deepcopy(state['case']['rooms']),
        'observations':deepcopy(state['observations'][a][-24:]),'evidence':deepcopy(list(state['known'][a].values())),
        'memory':deepcopy(state['memory'][a]),'relationships':deepcopy(state['relationships'][a]),'belief':deepcopy(state['beliefs'][a]),
        'thoughts':state['thoughts'][a][-3:],'choices':choices(state,a),'recipients':audience(state,a),
        'must_respond':state['obligations'][a]['response'],'must_speak':must_speak(state,a),
        'invitations':[deepcopy(i) for i in state['invitations'] if i['status']=='pending' and i['to']==a],
        'own_items':[v['name'] for v in state['items'].values() if v['holder']==a],
        'objectives':deepcopy(state['case']['roles'][a]['objectives'])}
    if state.get('source_integrity_version'):
        from . import source_provenance, temporal_facts
        result['source_provenance']=source_provenance.for_role(state,a,result)
        result['temporal_facts']=temporal_facts.for_role(state,a)
    return result


def decision_focus(state,a,reason=None,sharing=True,witnessed=False):
    """Only facts this participant received, with no global truth or other thoughts."""
    owed=set(state['obligations'][a]['sources'])
    questions=[deepcopy(o) for o in state['observations'][a] if o['event_id'] in owed][-4:]
    actions=[{'kind':e['kind'],'target':e['target'],'action':e['facts'].get('action')}
             for e in state['events'] if e['actor']==a and e['kind'] not in ('testimony','gesture','cue')][-6:]
    statuses=evidence_sharing.for_role(state,a,witnessed=witnessed) if sharing else None
    shared=([cid for cid,status in statuses.items() if status['shown_by_me']] if sharing else
            [cid for cid in state['contributions'][a] if cid in state['known'][a]])
    result={'reason':reason,'received_requests':questions,'recent_own_actions':actions,
            'activity':deepcopy(running(state,a)),'already_shared':shared}
    if sharing:result['evidence_sharing']=statuses
    return result


def world_choices(state):
    options=[{'id':'none','label':'暂时没有新的外部变化'}]
    if state['blocked_room']:options.append({'id':'reopen','label':'先前受阻的通路恢复开放'})
    else:options.append({'id':'block:r2','label':'公共区域出现临时检修，暂时限制进入第二个地点'})
    if state['scenario']=='rescue':options.append({'id':'supplies','label':'接应送来一份电池和一份补给'})
    if any(o['hidden'] and o['holder'] in ('r1','r2','r3') and o['protected'] for o in state['objects'].values()):options.append({'id':'records','label':'保管流程完成，封存的原始记录可供核对'})
    return options


def apply_world(state,choice,call_id):
    if choice not in {o['id'] for o in world_choices(state)}:raise ValueError('unsupported world event')
    state['world_due']=False;state['last_world_beat']=state['beat'];state['world_count']+=1
    if choice=='none':return
    e=emit(state,'world',choice=choice,decision_call_id=call_id)
    if choice=='reopen':state['blocked_room']=None;words='先前受阻的通路恢复了。'
    elif choice.startswith('block:'):
        state['blocked_room']=choice.split(':')[1];state['blocked_until']=state['beat']+3
        words='临时检修使'+state['case']['rooms'][state['blocked_room']]['name']+'暂时不能进入，三次时间推进后恢复。'
    elif choice=='supplies':
        state['supplies']['battery']+=1;state['supplies']['supply']+=1;words='接应补充了一份电池和一份补给。'
    else:
        for o in state['objects'].values():
            if o['protected'] and o['holder'] in ('r1','r2','r3'):o['hidden']=False
        words='保管流程完成，封存记录现在可以就地查阅。'
    announce(state,e,words)


def results(state,evaluations,isolate_admission=False):
    scenario=state['scenario'];solution=state['case']['solution']
    established=any(v.get('result')=='established' for v in evaluations.values())
    isolated=isolate_admission and scenario=='murder'
    investigation_established=any(a!=solution.get('killer') and v.get('result')=='established'
                                 for a,v in evaluations.items()) if isolated else established
    leader=next((a for a in ACTORS if sum(v==a for v in state['votes'].values())>=3),None)
    recovered=sum(k.startswith('archive_') and v['holder'] in ACTORS for k,v in state['items'].items())
    shared={'murder':established,'theft':state['items'].get('artifact',{}).get('holder')==solution.get('owner'),
            'family':sum(c['status']=='agreed' for c in state['commitments'])>=2,'council':leader is not None,
            'rescue':len(state['evacuated'])==4,'house':len(state['evacuated'])==4,'archive':recovered>=2}[scenario]
    exposed=set(state['public_evidence'])|{d['evidence_id'] for d in state['disclosures'] if public_disclosure(d)}
    output={}
    for a in ACTORS:
        objectives=state['case']['roles'][a]['objectives'];active=bool(state['contributions'][a])
        kind=objectives[0]['kind'];ev=evaluations.get(a,{})
        if kind=='avoid':primary=not established and active
        elif kind=='solve':
            key_records=set().union(*(set(route) for route in state['case']['proofs']['identity']))
            contributed=investigation_established and len(set(state['contributions'][a])&key_records)>=2
            if state['case'].get('rules_version',1)>=2:
                contributed=contributed and ev.get('result')=='unproven' and bool(set(ev.get('established',[]))&{'time','method'})
            primary=ev.get('result')=='established' or contributed
        elif kind=='reconcile':primary=active and any(c['status']=='agreed' and a in (c['from'],c['to']) for c in state['commitments']) and any(cid.startswith('c') for cid in state['contributions'][a])
        elif kind=='elect':primary=bool(leader and state['votes'].get(a)==leader)
        elif kind in ('rescue','escape'):primary=a in state['evacuated'] and active
        else:primary=shared and active
        secondary=objectives[1];kind2=secondary['kind'];target=secondary['target']
        if kind2=='protect':personal='s'+target not in exposed and active
        elif kind2=='expose':personal='s'+target in state['contributions'][a]
        elif kind2=='keepsake':personal=a in state['evacuated'] and state['items']['keepsake_'+a]['holder']==a
        elif kind2=='pledge':personal=state['pledges'].get(a,{}).get('fulfilled',False)
        else:personal=any(k.startswith('archive_') and item['holder']==a for k,item in state['items'].items())
        output[a]={'name':name(state,a),'primary':bool(primary),'personal':bool(personal),'success':bool(primary and personal),
                   'objectives':deepcopy(objectives),'reasoning':deepcopy(ev)}
    result={'shared_success':shared,'leader':leader,'participants':output,'evacuated':list(state['evacuated']),'recovered':recovered}
    if isolated:
        result.update(scoring_version=2,investigation_success=investigation_established,
                      admission_established=evaluations.get(solution['killer'],{}).get('result')=='established')
    return result


def public_disclosure(disclosure):
    return disclosure['channel']=='public' and disclosure.get('public_received',True)


def observed_dialogue(state,a):
    """Attach only this recipient's observed cues, including pre-existing saves."""
    observations=deepcopy(state['observations'][a])
    speeches={o['event_id']:o for o in observations if o['kind']=='testimony'}
    sources={e['id']:e['facts'].get('source') for e in state['events'] if e['kind']=='cue'}
    for observation in observations:
        if observation['kind']!='cue':continue
        source=sources.get(observation['event_id'])
        if source not in speeches:continue
        speeches[source].setdefault('cues',[]).append({'text':observation['text']})
        observation['utterance_event_id']=source
    return observations


def view(state,a,is_host=False):
    result={k:deepcopy(state[k]) for k in ('id','mode','gameplay','revision','phase','archived','beat','title','introduction','scenario','outcome')}
    if local_communication(state):result['local_communication']=True
    result.update(actor=a,is_host=is_host,humans=state['humans'],joined=state['joined'],ready=state['ready'],
                  reading_deadline=state['reading_deadline'],join_code=state['join_code'] if is_host and state['phase'] in ('introduction','lobby','opening') else None,
                  cast=[{'id':b,'name':name(state,b),'human':b in state['humans']} for b in ACTORS] if state['preview'] else [],
                  opening=state['opening'],opening_submitted=a in state['intentions'],opening_waiting=[b for b in state['humans'] if b not in state['intentions']],
                  background_error=state['background_error'],briefing=[],evidence=[],observations=[],options=[],relationships={},memory=None,
                  notes=deepcopy(state['notes'][a]),chat=None,ending=None,results=None,submitted=a in state['submissions'])
    if not state['case']:
        if state['phase']=='opening':
            profile=state['story']['roles'][a]
            result['briefing']=[profile['persona'],profile['secret']]
        return result
    profile=state['case']['roles'][a]
    result.update(player_name=name(state,a),briefing=[state['case']['public_briefing'],profile['persona'],*profile['memories'],
                *['你与'+name(state,b)+'：'+r for b,r in profile['relationships'].items()]],objectives=profile['objectives'])
    if state['phase']=='reading':return result
    chat=chat_for(state,a)
    result.update(scene={'id':state['locations'][a],**state['case']['rooms'][state['locations'][a]]},
        evidence=exploration.evidence(state,a,evidence_sharing.evidence(state,a,witnessed=True)),
        exploration=exploration.for_role(state,a,exhaustion=True),observations=observed_dialogue(state,a),
        relationships=deepcopy(state['relationships'][a]),memory=deepcopy(state['memory'][a]),
        options=choices(state,a) if state['phase']=='active' and not state['archived'] and a not in state['submissions'] else [],
        must_respond=state['obligations'][a]['response'],must_speak=must_speak(state,a),must_explain=state['obligations'][a]['explain'],
        recipients=audience(state,a),own_items=[v['name'] for v in state['items'].values() if v['holder']==a],
        activity=deepcopy(running(state,a)),votes=deepcopy(state['votes']),resources=state['resources'][a],
        supplies=deepcopy(state['supplies']) if state['scenario']=='rescue' else None,
        commitments=[deepcopy(c) for c in state['commitments'] if a in (c['from'],c['to'])],
        submitted_count=len(state['submissions']),evacuated=a in state['evacuated'])
    if chat:result['chat']={'id':chat['id'],'participants':list(chat['participants']),'turns':deepcopy(chat['turns']),'limit':8}
    if state['phase']=='ended':
        result.update(ending=deepcopy(state['ending']),results=deepcopy(state['results']),resolution=deepcopy(state['case']['solution']),history=deepcopy(state['case']['history']))
    return result
