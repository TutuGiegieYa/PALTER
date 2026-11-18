"""Omniscient display projection, separate from recipient history and model input."""
from copy import deepcopy
from . import ensemble_world as w


def material(state, identity):
    record=w.definition(state,identity) if identity else None
    return record.get('title','材料') if record else '材料'


def description(state,event,recipients):
    kind=event['kind'];actor=event.get('actor');target=event.get('target');facts=event['facts']
    who=w.name(state,actor) if actor in tuple(w.ACTORS) else ''
    person=w.name(state,target) if target in tuple(w.ACTORS) else ''
    title='《'+material(state,target)+'》'
    task=next((t for t in state['activities'] if t['id']==facts.get('started_by',event['id'])),{})
    room=state['case']['rooms'].get(task.get('location',facts.get('location')),{}).get('name')
    place='在'+room if room else ''
    if kind=='move':
        words=who+'来到'+state['case']['rooms'][target]['name']+'。'
        followers=facts.get('followers',[])
        if followers:words+='、'.join(w.name(state,a) for a in followers)+'随行。'
        return words
    if kind=='inspect':return who+'查看了'+title+'。'
    if kind=='share':
        others=[w.name(state,a) for a in facts.get('recipients',recipients) if a!=actor]
        return who+('向'+'、'.join(others) if others else '')+'出示了'+title+'。'
    if kind in ('take','place','give','protect','copy'):
        return who+{'take':'收起了','place':'放下了','give':'交出了','protect':'封存了','copy':'复制了'}[kind]+title+'。'
    if kind=='follow':return who+'开始留意'+person+'后续可见的移动。'
    if kind in ('search','hide','destroy','repair','clear_route'):
        action={'search':'搜查','hide':'藏匿'+title,'destroy':'销毁'+title,'repair':'修复通讯','clear_route':'清理通路'}[kind]
        return who+'开始'+place+action+'。'
    if kind in ('action_completed','action_failed','action_cancelled','cancel_work'):
        action=facts.get('action',task.get('kind'))
        label={'search':'搜查','hide':'藏匿材料','destroy':'销毁材料','repair':'修复通讯','clear_route':'清理通路'}.get(action,'行动')
        if kind=='action_completed':return who+'完成了'+place+'的'+label+'。' if place else who+'完成了'+label+'。'
        if kind=='action_failed':return who+'的'+label+'未能完成。'
        return who+'中止了'+label+'。'
    if kind=='switch':return who+'操作了现场开关。'
    if kind=='dial':return who+'调整了密码转盘。'
    if kind in ('collect','transfer'):
        item=state.get('items',{}).get(target,{}).get('name','物品')
        return who+('取走了' if kind=='collect' else '交出了')+item+'。'
    if kind=='leave':return who+'安全离开了。'
    if kind=='promise':return who+'向'+person+'提出互相支持的承诺。'
    if kind in ('agree','withdraw'):return who+('接受了双方承诺。' if kind=='agree' else '撤回了双方承诺。')
    if kind=='vote':return who+'投票支持'+person+'。'
    if kind=='pledge':return who+'承诺向'+person+'提供一份资源。'
    if kind=='fund':return who+'交给'+person+'一份资源。'
    if kind=='invitation':return who+'向'+person+'发出私聊邀请。'
    if kind=='invitation_reply':return who+('接受了' if facts.get('accepted') else '拒绝了')+person+'的私聊邀请。'
    if kind=='invitation_resolved':
        status={'accept':'已被接受','decline':'已被拒绝','expired':'已失效'}.get(facts.get('status'),'已有结果')
        return person+'向'+who+'发出的私聊邀请'+status+'。'
    if kind=='private_closed':
        participants=state['chats'].get(target,{}).get('participants',[])
        return '、'.join(w.name(state,a) for a in participants)+'结束了私聊。'
    if kind=='closure_vote':return who+('同意结束调查。' if facts.get('agreed') else '撤回了结案意愿。')
    if kind=='closure_agreed':return '角色已达成结案约定，进入独立提交阶段。'
    if kind=='conclusion_locked':return who+'锁定了自己的最终结论，内容暂不公开。'
    if kind=='wait_resolved':return who+('的等待已超时。' if facts.get('status')=='timed_out' else '的等待已结束。')
    if kind=='tracking_proposed':return who+'创建了一个事件监听。'
    if kind=='tracking_resolved':return who+'关注的事件已有结果。'
    if kind=='document_created':return who+'制作了一份文书。'
    if kind=='route_reopened':return '临时检修完成，通路恢复开放。'
    if kind=='started':return '故事开始，角色可以开始行动。'
    if kind=='world':return '现场发生了新的变化。'
    if kind=='wait':return who+'暂时留在原地。'
    names='、'.join(w.name(state,a) for a in recipients)
    return (names+'收到新的现场信息。') if names else '现场产生了新的记录。'


def build(state,observed,cues):
    by_event={}
    for actor,rows in observed.items():
        for row in rows:
            if row['kind']=='cue':continue
            by_event.setdefault(row['event_id'],[]).append((actor,row))
    result=[]
    for event in state['events']:
        identity=event['id'];copies=by_event.get(identity,[])
        if not copies and event['kind']!='move':continue
        if event['kind']=='cue':continue
        recipients=list(dict.fromkeys(actor for actor,_ in copies))
        row={'id':'watch-'+identity,'event_id':identity,'beat':event['beat'],
             'kind':'movement' if event['kind']=='move' else event['kind'],'recipients':recipients}
        if event['kind'] in ('testimony','gesture'):
            facts=event['facts']
            row.update(speaker=event['actor'],speaker_name=w.name(state,event['actor']),
                       text=facts.get('text',copies[0][1]['text']),channel=facts.get('channel','public'),
                       recipients=deepcopy(facts.get('recipients',recipients)))
            if event['kind']=='testimony':row['cues']=deepcopy(cues.get(identity,[]))
        else:
            row.update(speaker_name='行动记录' if event.get('actor') in tuple(w.ACTORS) else '场景记录',
                       text=description(state,event,recipients))
            details={}
            for actor,receipt in copies:
                key=(receipt['kind'],receipt.get('evidence_id'),receipt['text'])
                if key not in details:
                    details[key]={'kind':receipt['kind'],'text':receipt['text'],'recipients':[],
                                  'title':material(state,receipt['evidence_id']) if receipt.get('evidence_id') else '收到的回执'}
                if actor not in details[key]['recipients']:details[key]['recipients'].append(actor)
            if details:row['details']=list(details.values())
        result.append(row)
    return result
