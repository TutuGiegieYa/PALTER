"""Frozen causal scenario assets; AI supplies setting and social histories."""

from copy import deepcopy
import random
from . import model_contracts as contract

ACTORS = 'ABCD'
SCENARIOS = {
    'murder': ('悬疑推理 · 命案', '重建时间、机会与手法；个人秘密会影响取舍。'),
    'theft': ('悬疑推理 · 失窃', '核对归属、追踪实物交接，把物品交还合法持有人。'),
    'family': ('关系与秘密', '核实旧事，选择公开或保留秘密，建立双方同意的承诺。'),
    'council': ('议事与继任', '调查资格、争取选票和资源，并兑现自己的承诺。'),
    'rescue': ('隔绝与救援', '分配补给、修复通讯、打开撤离路线并选择何时离开。'),
    'house': ('异象与探索', '查明场所变化的固定机制，取回私人物品并离开。'),
    'archive': ('封存档案', '拼合分散的机关信息，开启档案并决定保留和公开哪些记录。'),
}
FAMILIES = ('clock', 'recording', 'substitution')


def text(value, limit=1200):
    if not isinstance(value, str) or not value.strip() or len(value)>limit:
        raise ValueError('invalid authored text')


def validate_story(story):
    if not isinstance(story,dict):raise contract.ContractError('story','Return an object.')
    for k in ('title','briefing'):contract.text(story.get(k),k,contract.STORY_TEXT[k])
    for key,expected in (('rooms',{'r1','r2','r3'}),('roles',set(ACTORS))):
        if not isinstance(story.get(key),dict) or set(story[key])!=expected:
            raise contract.ContractError(key,'Use exactly these entity keys: '+','.join(sorted(expected)))
    for group,fields in (('rooms',('name','description')),('roles',('persona','secret','secret_record'))):
        for identity,row in story[group].items():
            path=group+'.'+identity
            if not isinstance(row,dict):raise contract.ContractError(path,'Return an object.')
            for field in fields:contract.text(row.get(field),path+'.'+field,contract.STORY_TEXT[group+'.*.'+field])
            if group=='roles':
                relations=row.get('relationships')
                if not isinstance(relations,list) or len(relations)!=contract.RELATIONSHIPS:
                    raise contract.ContractError(path+'.relationships',f'Return exactly {contract.RELATIONSHIPS} descriptions in roster order.')
                for index,relation in enumerate(relations):
                    contract.text(relation,f'{path}.relationships[{index}]',contract.STORY_TEXT['roles.*.relationships[*]'])


def opening_order(seed, humans, intentions):
    """One actual killer; willing humans have priority, then willing AI."""
    rng=random.Random(seed);order=list(ACTORS);rng.shuffle(order)
    willing=[a for a in order if intentions[a]['volunteer']]
    candidates=[a for a in willing if a in humans] or [a for a in willing if a not in humans]
    candidates=candidates or [a for a in order if a not in humans] or order
    killer=candidates[0]
    return killer,[killer,*[a for a in order if a!=killer]]


def build(story, preview, scenario, seed, humans, intentions=None, rules_version=3):
    validate_story(story)
    rng=random.Random(seed);cast=preview['cast'];victim=preview['victim']
    killer,arrival=opening_order(seed,humans,intentions) if intentions else (rng.choice([a for a in ACTORS if a not in humans] or list(ACTORS)),list(ACTORS))
    arrival=[killer,*[a for a in arrival if a!=killer]]
    family=FAMILIES[seed%len(FAMILIES)];others=[a for a in arrival if a!=killer]
    roles={a:{'name':cast[a],**deepcopy(story['roles'][a]),'relationships':dict(zip([b for b in ACTORS if b!=a],story['roles'][a]['relationships'])),
              'knows':[],'memories':[],'objectives':[]} for a in ACTORS}
    rooms=deepcopy(story['rooms']);hall,scene,work=[rooms[r]['name'] for r in ('r1','r2','r3')]
    case={'title':story['title'],'public_briefing':story['briefing'],'scenario':scenario,'family':family,'victim':victim,
          'roles':roles,'rooms':rooms,'history':[],'clues':[],'items':{},'solution':{},'proofs':{},'arrival':arrival}

    def fact(fid,when,words,knowers=()):
        case['history'].append({'id':fid,'time':when,'text':words})
        for a in knowers:
            roles[a]['knows'].append(fid);roles[a]['memories'].append(when+'：'+words)

    def clue(cid,title,observation,location='r1',*,private=None,protected=False,category='document',locked=False,source='原始留存记录'):
        case['clues'].append({'id':cid,'title':title,'observation':observation,'location':location,'target':title,
                              'source':source,'category':category,'private_owner':private,'protected':protected,'locked':locked})

    for a in ACTORS:
        fact('secret_'+a,'事发之前',roles[a]['secret'],[a])
        clue('s'+a,cast[a]+'留下的私人记录',roles[a]['secret_record'],'r3',private=a,locked=True)
        clue('copy_'+a,cast[a]+'的往来留底',roles[a]['secret_record'],'r3',locked=True)
        case['clues'][-1]['reveals']=['s'+a]
        roles[a]['private_evidence']='s'+a

    if scenario=='murder':
        lower=18*60+seed%70;crime=lower+6;upper=lower+12
        clock=lambda n:f'{n//60:02d}:{n%60:02d}'
        l,t,u=map(clock,(lower,crime,upper));offset=17 if seed%2 else -19
        display=clock(crime+offset);direction=('快' if offset>0 else '慢')+str(abs(offset))+'分钟'
        culprit=cast[killer];finder=cast[others[0]];later=cast[others[1]]
        method={'clock':'在近距离冲突中以现场细绳勒颈致死',
                'recording':'近距离刺伤致死，并用预先录下的发言制造仍在公共区域的假象',
                'substitution':'将现场两只可辨认的杯子调换，使死者喝下事先放入危险物质的那一杯'}[family]
        if rules_version>=5 and family=='recording':
            method='近距离刺伤致死，并用自己预先录下的发言制造自己仍在公共区域的假象'
        fact('alive',l,f'{cast[others[2]]}在实时通话中提出临时问题，{victim}当场回应并拿起指定物品。',[others[2]])
        fact('crime',t,f'{culprit}在{scene}{method}。杀害者只有此人。',[killer])
        fact('dead',u,f'{finder}到达{scene}时，{victim}已经死亡。',[others[0]])
        fact('late',clock(upper+3),f'{later}在死亡之后才进入{scene}，想取回自己的私人记录。',[others[1]])
        fact('access',l+'—'+clock(upper+5),f'{scene}只有一个实际通行入口。最后存活记录后、发现死亡前，只有{culprit}进入；其余人的相关到访发生在发现死亡时或之后。')
        clue('c1','最后一次即时回应',f'主时钟 {l}，原始双向记录中，{victim}按临时要求拿起指定物品并当场回答。记录保留签时凭据。','r1',protected=True)
        clue('c2','发现现场的原始记录',f'主时钟 {u}，{finder}进入现场前启动的记录持续保留，随后看到{victim}已经死亡；这只能证明此时已经死亡。','r2',protected=True)
        clue('c8','入口结构与连续记录目录',f'{scene}只有这一条可供人员通行的入口，其余开口有未破坏封条。目录完整记录每次进出，正文分别保存在现场存储和备份终端；不能用某一段片段代替完整目录。','r2',protected=True)
        clue('c9','主时钟与导出签时凭据','导出凭据连续标明主时钟，能够核对原始目录的起止时间、各段顺序和文件完整性；没有遗漏、剪辑或另一条入口。','r3',protected=True)
        clue('c10','独立入口备份',f'独立主时钟记录在 {t} 拍到{culprit}独自进入{scene}，随后离开；其余来访者分别在 {u}、{clock(upper+3)} 和 {clock(upper+6)} 到达。只有进出，没有室内杀害画面。','r3',locked=True,protected=True)
        if family=='clock':
            clue('c3','带叠加时刻的进门片段',f'镜头拍到{culprit}正面进入{scene}，角落显示 {display}。角落时刻与文件签时不相同。','r2')
            clue('c4','设备校时对照','同一时刻的校时照片和维护记录显示，入口设备的叠加时刻比主时钟'+direction+'；前后校准一致，原文件连续保存。','r3',locked=True)
            clue('c7','现场绳结与压痕记录','现场照片记录颈部细股状压痕、椅边拉紧的细绳和近距离挣动痕迹；没有任何自动收紧装置。','r2',category='trace')
        elif family=='recording':
            clue('c3','公共区域的发言录音',f'{t} 左右公共区域传出{culprit}的声音，但记录只收录声音，没有拍到说话者。','r1')
            clue('c4','播放任务和原始音轨',f'播放终端在 {t} 自动启动事先保存的音轨；同样的停顿和背景声逐段重复，内容与所谓现场发言一致。音轨属于{culprit}早先的发言。','r3',locked=True)
            clue('c7','现场伤口与工具照片','现场原始照片记录近距离刺伤和留在桌边的工具，记录人员封存了工具。伤害已在发现现场时存在；声音记录不能证明人员在场。','r2',category='trace')
        else:
            clue('c3','器皿交接片段',f'{t}，片段中{culprit}在{scene}将带蓝缺口的杯子与带白缺口的杯子交换位置，随后{victim}拿起蓝缺口杯。','r2')
            clue('c4','封存检验记录','调查开始前已完成的封存检验记录注明：危险残留仅在蓝缺口杯；检材、杯底编号和现场照片对应。白缺口杯未检出。记录说明该物质在这次案件中很快引发致命反应。','r3',locked=True)
            clue('c7','原始席位与杯底照片',f'带蓝缺口杯原本属于{culprit}的席位，白缺口杯在{victim}席位。照片摄于最后存活记录之前，杯底编号可与交接片段核对。','r1',category='trace')
        for visit,(i,a) in enumerate(zip((5,6,13),others)):
            when=clock(upper+visit*3)
            handling=(intentions or {}).get(a,{}).get('handling','inspect')
            detail={'touch':'检查身体时留下接触痕迹','inspect':'留在门口观察现场，没有接触身体或移动物品','leave':'看到情况后立即离开，没有检查或接触现场'}[handling]
            fact('visit_'+a,when,f'{cast[a]}在死者已死亡后到访，{detail}，与自己的秘密有关。',[a])
            clue('c'+str(i),cast[a]+'的到访痕迹',f'入口与室内记录留有{cast[a]}的到访痕迹。个人记录中的片段关联主时钟 {when}；需要与死亡边界核对，不能仅凭到访就判定作案。其到访原因与这份记录相连：'+roles[a]['secret_record'],'r2',category='trace')
            case['clues'][-1]['reveals']=['s'+a]
        clue('c11','封存现场副本','独立封存袋保留了现场照片与编号清单。'+next(c['observation'] for c in case['clues'] if c['id']=='c7'),'r3',protected=True,locked=True)
        clue('c12','案前争执的原始材料',f'{victim}准备公开的一项问题涉及{culprit}：'+roles[killer]['secret_record'],'r3',locked=True)
        case['clues'][-1]['reveals']=['s'+killer]
        case['solution']={'killer':killer,'time':l+' 至 '+u,'method':method,'motive':roles[killer]['secret'],
                          'reconstruction':f'{l} 死者仍活着；{t} {culprit}实施杀害；{u} {finder}发现死亡。后到访者的痕迹和秘密不能直接证明杀人。'+method+'。'}
        primary=['c1','c2','c3','c4','c8','c9'] if family!='recording' else ['c1','c2','c3','c4','c8','c10']
        case['proofs']={'identity':[primary,['c1','c2','c8','c9','c10']], 'time':[['c1','c2']],
                        'method':[['c7','c4'] if family=='substitution' else ['c7'],['c11','c4'] if family=='substitution' else ['c11']]}
    else:
        owner=ACTORS[(seed+1)%4]
        if scenario=='theft' and owner==killer:owner=ACTORS[(ACTORS.index(killer)+1)%4]
        fact('ownership','过去',f'原始约定把重要物品及处置权交给{cast[owner]}。',[owner])
        facts={
            'theft': [('归属原件',f'原始交接约定由各方签署，合法持有人是{cast[owner]}。'),('转移记录',f'{cast[killer]}此前将重要物品收入自己的随身保管袋；这不等于拥有处置权。'),('交接核验表','归还必须核对原件编号和领取者，并由双方确认交接。')],
            'family':[('当年的原件','四人的旧事记录各保留一部分；单独转述不能代替原件。'),('共同约定','新的承诺只有提出者和受诺者都明确同意才成立，未同意不能被代为承诺。'),('未公开的来信','原件澄清了旧事中的一项误会；公开它也会暴露相关人的私人经历。')],
            'council':[('议事章程','四人各有一票，至少三票支持同一候选人才形成稳定授权。'),('资源清册','每人起始有两份可调配资源，向候选人实际转交才算兑现资源承诺。'),('资格原件','候选人的资格可以被讨论，但不能靠口头声称替别人投票或转交资源。')],
            'rescue':[('维修说明','通讯修复需要两份电池和两个时间单位，完成后可呼叫接应。'),('路线勘察','后部撤离路线需要两份补给和两个时间单位清理，完成后才能逐人撤离。'),('储备清单','公共储备有四份电池和四份补给，私人保留物品可以在撤离前取回。')],
            'house':[('旧电路图','两个独立开关控制出口；出口只在两者不同的状态下接通。'),('现场检修记录','所谓异响由同一电路控制，切换开关会改变真实照明和通路，不会改写旧事。'),('失物登记','每个人的旧物分别封存，离开后不能替还未离开的人选择去留。')],
            'archive':[('左侧机关笔记',f'第一枚转盘的正确位置为 {1+seed%3}。'),('右侧机关笔记',f'第二枚转盘的正确位置为 {1+(seed//3)%3}。'),('保管规约','两枚转盘都正确才打开内柜。档案需要亲自取出或出示，打开柜门本身不等于完成保存。')],
        }[scenario]
        for i,(title,words) in enumerate(facts,1):
            clue('c'+str(i),title,words,'r'+str(i),protected=True,locked=i==3)
            fact('record_'+str(i),'事前留存',words)
        case['solution']={'custodian':killer,'owner':owner,'dials':[1+seed%3,1+(seed//3)%3],
                          'reconstruction':'；'.join(words for _,words in facts)}
        if scenario=='theft':case['items']['artifact']={'name':'待交接的重要物品','holder':killer,'owner':owner}
        if scenario=='theft':fact('transfer','开场之前',f'{cast[killer]}将待交接的物品收入自己的保管袋。',[killer])
        if scenario in ('house','rescue'):
            for a in ACTORS:case['items']['keepsake_'+a]={'name':cast[a]+'的私人旧物','holder':'r3','owner':a}
        if scenario=='archive':
            for i in range(1,4):case['items']['archive_'+str(i)]={'name':'封存档案第'+str(i)+'册','holder':'vault','owner':None}
    if rules_version>=2:
        case['rules_version']=rules_version
        if scenario=='murder':
            from .murder_cases import diversify
            diversify(case,seed)
            if rules_version>=4:
                from .temporal_facts import compile_case
                compile_case(case,lower,crime,upper,offset)
    for index,a in enumerate(ACTORS):
        primary={'murder':('avoid' if a==killer else 'solve'),'theft':'return','family':'reconcile','council':'elect','rescue':'rescue','house':'escape','archive':'recover'}[scenario]
        personal='protect' if index%2==0 else 'expose'
        if scenario in ('rescue','house'):personal='keepsake'
        if scenario=='council':personal='pledge'
        if scenario=='archive':personal='preserve'
        target={'A':'B','B':'D','C':'D','D':'B'}[a]
        primary_text={'avoid':'通过自己的实际行动避免杀害行为被完整举证','solve':'还原案件，并亲自提供至少两项关键材料或提交充分论证',
                      'return':'查明归属并参与把实物交还合法持有人','reconcile':'核实并分享旧事，与另一人达成双方同意的承诺',
                      'elect':'参与形成至少三票支持的稳定授权','rescue':'参与救援并安全撤离','escape':'查明出口机制并亲自离开','recover':'参与打开内柜并保存至少两册档案'}[primary]
        secondary_text={'protect':'保护'+cast[target]+'的私人记录，同时参与调查','expose':'公开'+cast[target]+'的私人记录，承担关系后果',
                        'keepsake':'撤离时带上自己的私人旧物','pledge':'兑现自己记录的资源承诺','preserve':'结案时保有一册未被销毁的档案'}[personal]
        if rules_version>=2 and primary=='solve':primary_text='提交充分论证；或在共同查明真相时，正确指认、解释时间或手法，并首次公开至少两项关键材料'
        roles[a]['objectives']=[{'id':'primary','kind':primary,'text':primary_text},
                                {'id':'personal','kind':personal,'target':target,'text':secondary_text}]
    return case
