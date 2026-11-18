"""A bounded causal contract for generated cases, without duplicate references.

The model authors settings, profiles and social conflict. Code constructs the
bounded physical case and assigns its identities, times, recipients and proof
dependencies once, before play. It never repairs generated prose.
"""

from copy import deepcopy
import random

from . import case_world as w


def clock(minute):
    return f"{minute//60:02d}:{minute%60:02d}"


def candidate_casts(seed):
    """Legacy roster for exact recovery of older pinned preview operations."""
    names=['林知远','周曼宁','沈文昭','陈映秋','许嘉禾','顾清和','宋予安','陆怀川','叶书瑶','孟云舒',
           '方景行','秦若岚','程砚舟','苏晚晴','江庭月','赵言溪','杜承安','韩思齐','梁疏影','郑明棠',
           '罗映山','谭望舒','何静川','夏以宁','吴闻笙','谢雨桐','魏南星','蒋念初','袁书衡','钟亦舟']
    random.Random(seed).shuffle(names)
    return [{'cast':dict(zip(w.ACTORS,names[i:i+4])),'victim':names[i+4]} for i in (0,5,10)]


def validate_generated_cast(candidate):
    """Validate distinct entity names without choosing or rewriting model prose."""
    cast=candidate['cast']
    if not isinstance(cast,dict) or set(cast)!=set(w.ACTORS):raise ValueError('preview cast')
    names=[*cast.values(),candidate['victim']]
    for name in names:w.prose(name,80)
    if len({name.strip() for name in names})!=5:raise ValueError('preview names must identify distinct people')


def frame(identifier,cast=None,victim=None):
    seed=int(identifier[:12],16)
    killer=w.NPCS[seed%3]
    others=[c for c in w.NPCS if c!=killer]
    lower=1080+(seed//3)%120
    upper=lower+10+(seed//360)%11
    crime=lower+(upper-lower)//2
    records={
        "alive":{"kind":"last_alive","minute":lower,"known_by":["A"],"requirement":f"An independently timed, interactive observation proves the victim alive at {clock(lower)}. A experienced it."},
        "dead":{"kind":"first_dead","minute":upper,"known_by":["A"],"requirement":f"An independent timed physical record proves the victim already dead at {clock(upper)}. A discovered the death; original records remain inspectable."},
        "presence":{"kind":"presence","minute":None,"known_by":[],"requirement":f"Objective evidence places {killer} at the crime scene within the window, without revealing the killing directly. A distinctive trace must be attributable through visible comparison material."},
        "alibi_one":{"kind":"exclusion","minute":None,"known_by":[others[0]],"requirement":f"Objective continuous evidence excludes {others[0]} from the scene throughout {clock(lower)}–{clock(upper)}. A booking, signature or self-report alone is insufficient."},
        "alibi_two":{"kind":"exclusion","minute":None,"known_by":[others[1]],"requirement":f"Different objective continuous evidence excludes {others[1]} from the scene throughout {clock(lower)}–{clock(upper)}. No reliance on a suspect vouching for themselves."},
        "mechanism":{"kind":"mechanism","minute":None,"known_by":[killer],"requirement":"Observable physical details establish the chosen killing method and expose its misleading appearance. Include any comparison needed; do not require unavailable laboratory results."},
        "motive":{"kind":"motive","minute":None,"known_by":[killer],"requirement":f"A discoverable original record exposes the conflict motivating {killer}, without itself proving identity."},
        "access":{"kind":"exclusion","minute":None,"known_by":[],"requirement":"Observable access records and physical layout establish that no outsider or unrecorded entrance was possible in the window. Explain the evidence's completeness within this setting."},
        "innocent_secret":{"kind":"context","minute":None,"known_by":[others[0]],"requirement":f"A suspicious trace from {others[0]}'s unrelated secret, with a concrete innocent explanation in actual_history. It must agree with their continuous alibi."},
    }
    if cast:
        for spec in records.values():
            # Structured role references in our own authoring instructions use
            # the already-published names; no generated prose is rewritten.
            for actor,name in cast.items():
                spec["requirement"]=spec["requirement"].replace(" "+actor+" "," "+name+" ")
        records['innocent_secret']['requirement']=f"A suspicious trace from {cast[others[0]]}'s unrelated secret, with a concrete innocent explanation. It must agree with {cast[others[0]]}'s continuous alibi."
    return {"killer":killer,"killer_name":cast[killer] if cast else killer,"cast":cast,"victim":victim,"crime_minute":crime,"window":[lower,upper],"crime_time":clock(crime),
            "window_text":clock(lower)+" 至 "+clock(upper),"records":records,
            "constraint":"A face-to-face killing by the assigned killer within this single-day window. No delayed mechanism, accomplice or outsider. Exactly A/B/C/D are the living participants. A is innocent. Past facts only: do not predetermine future choices or the ending."}


def compile_case(authored,contract):
    if authored.get('format')=='bounded-v1':
        authored=materialize(authored,contract)
    # Pending operations created with earlier immutable prompts remain resumable.
    if "records" not in authored:
        w.validate_case(authored)
        return authored
    if set(authored["records"])!=set(contract["records"]):
        raise ValueError("case authoring records")
    if contract['cast'] and ({c:r['name'] for c,r in authored['roles'].items()}!=contract['cast'] or authored['victim']!=contract['victim']):
        raise ValueError("case roster differs from premise")
    for key in ("crime","method","motive","reconstruction"):
        w.prose(authored[key],2500)
    history=[{"id":"h_crime","time":contract["crime_time"],"minute":contract["crime_minute"],"text":authored["crime"]}]
    knows={c:[] for c in w.ACTORS};knows[contract["killer"]].append("h_crime")
    clues=[];index={}
    for i,(key,spec) in enumerate(contract["records"].items(),1):
        record=authored["records"][key];w.prose(record["actual_history"],800)
        fact="h_"+key;clue="c"+str(i);index[key]=clue
        when=clock(spec["minute"]) if spec["minute"] is not None else record["time"]
        history.append({"id":fact,"time":when,"minute":spec["minute"],"text":record["actual_history"]})
        for actor in spec["known_by"]:knows[actor].append(fact)
        clues.append({"id":clue,"facts":[fact],"kind":spec["kind"],"minute":spec["minute"],"time":when,
                      "source":record["actual_history"],**{k:record[k] for k in ("location","title","target","observation")}})
    roles={}
    for actor,profile in authored["roles"].items():
        # Initial experience has one source of truth, rather than a second
        # independently generated memory that could forget or invent the crime.
        roles[actor]={**{k:profile[k] for k in ("name","persona","goal","cover_story","relationships")},"location":"r1",
                      "knows":knows[actor],"memories":[h["time"]+"："+h["text"] for h in history if h["id"] in knows[actor]]}
    case={k:authored[k] for k in ("title","public_briefing","victim","rooms")}
    case.update(roles=roles,history=history,clues=clues,
                solution={"killer":contract["killer"],"crime_fact":"h_crime","window":contract["window"],"time":contract["window_text"],
                          **{k:authored[k] for k in ("method","motive","reconstruction")}},
                proofs={"identity":[[index[k] for k in ("presence","alibi_one","alibi_two","access")]],
                        "time":[[index["alive"],index["dead"]]],"method":[[index["mechanism"]]]})
    # Every role receives its own experiences, including the killer's crime.
    if authored.get('format')=='bounded-v1':
        # A complete single-entrance record plus identifiable presence also
        # suffices; the final reconstruction separately requires time/method.
        case['proofs']['identity'].append([index['presence'],index['access']])
    w.validate_case(case)
    return case


def materialize(story,contract):
    """Authoritative physical records for an explicit, bounded puzzle family.

    This is the normal case construction path, not a model-failure fallback.
    The AI authors social conflict and character profiles; these mechanics are
    deliberately rule-defined so an unattended machine cannot become an alibi.
    """
    story=deepcopy(story);cast=contract['cast'];killer=contract['killer'];culprit=cast[killer]
    for actor,profile in story['roles'].items():
        relations=profile['relationships']
        if isinstance(relations,list):
            if len(relations)!=3:raise ValueError('three ordered relationships required')
            profile['relationships']=dict(zip((c for c in w.ACTORS if c!=actor),relations))
    first,second=[c for c in w.NPCS if c!=killer];one,two=cast[first],cast[second]
    human=cast['A'];victim=contract['victim'];lower,upper=contract['window'];minute=contract['crime_minute']
    a,b,t=clock(lower),clock(upper),clock(minute)
    rooms=story['rooms'];scene=rooms['r2']['name'];hall=rooms['r1']['name'];work=rooms['r3']['name']
    # Vary the mistaken chronology without changing the evidence during play.
    offset=upper-lower+3 if int(contract['crime_minute'])%2 else -(upper-lower+4)
    shown=clock(minute+offset);offset_text=('快' if offset>0 else '慢')+str(abs(offset))+'分钟'
    conflict=story['conflict'];secret=story['innocent_secret']
    for group in (conflict,secret):
        for key in ('truth','title','target','observation'):w.prose(group[key],600)
    story.update(victim=victim,
        crime=f'{t}，{culprit}进入{scene}，当面用室内的细麻绳勒死{victim}，把绳子留在现场；此后没有人移动尸体或伪造录像。',
        method=f'当面用细麻绳勒颈致死。门口摄像机的画面时钟比主时钟{offset_text}，画面中的{shown}实际对应{t}，不能把画面时刻直接当成进门时刻。',
        motive=conflict['truth'],
        reconstruction=f'{a}，{human}与{victim}进行实时视频通话，死者仍活着。{t}，{culprit}进入{scene}实施杀害，门口画面因时钟{offset_text}显示为{shown}。{one}全程在{hall}，{two}全程在{work}，两份连续录像均覆盖作案窗口。{b}，{human}进入现场发现死者。出入口记录排除了外来者和第二条通道。{conflict["truth"]}另一个可疑之处实际是：{secret["truth"]}')
    def record(truth,when,location,title,target,observation):
        return dict(actual_history=truth,time=when,location=location,title=title,target=target,observation=observation)
    story['records']={
        'alive':record(f'{a}，{human}通过实时视频与{victim}交谈；死者根据临时提问翻转桌上卡片并回答，{human}亲眼看见这一过程。',a,'r1','最后一段实时通话','通话终端的原始录像',f'主时钟{a}，画面中{victim}听到{human}临时提出的问题，翻转桌面卡片并回答。声音、动作连贯。终端保存了通话原始文件和主时钟签时记录。'),
        'dead':record(f'{b}，{human}进入{scene}，发现{victim}已经死亡；记录仪保留了进门到检查现场的连续画面。',b,'r2','发现现场的连续记录','现场记录仪',f'主时钟{b}，记录仪拍到{human}进门；{victim}已死亡，颈部有清晰绳状压痕，细麻绳在椅脚旁。记录从进入房间前开始连续保存，没有人在此前搬动尸体。'),
        'presence':record(f'{t}，{culprit}独自进入{scene}；门口摄像机画面时间为{shown}，它的时钟偏差始终是{offset_text}。',f'画面显示 {shown}','r2','门口的进出片段','门口摄像机原始存储卡',f'画面显示{shown}，{culprit}正面经过镜头，面容清晰，独自进入{scene}，数分钟后离开。镜头只拍得到门口，看不到室内。视频角落的画面时间与文件管理器时间不一致。'),
        'alibi_one':record(f'{a}至{b}，{one}一直留在{hall}，持续处于原始录像的完整画面内，没有离开或替身。',f'{a}–{b}','r1','连续室内影像','公共区域摄像机原始存储卡',f'这段由主时钟签时的连续影像完整覆盖{a}至{b}：{one}的正脸和上身始终在{hall}画面内，期间与视频另一端持续对话，人物没有离开、被遮挡或切换；原文件无断帧。'),
        'alibi_two':record(f'{a}至{b}，{two}一直在{work}参加实时远程核对，原始双向录像完整显示其持续在场。',f'{a}–{b}','r3','双向实时核对录像','工作终端的原始会议文件',f'主时钟{a}至{b}的完整录像里，{two}的正脸和双手始终可见，并根据远端临时提问展示不同页码。镜头包括房门，人物未离开，画面没有切换或断帧。'),
        'mechanism':record(f'{culprit}用现场的细麻绳勒颈杀害{victim}；没有使用延迟装置、毒物或其他武器。','案发时','r2','压痕与绳股','椅脚旁的细麻绳与现场照片','颈部压痕呈连续的细绳股纹理，宽窄与椅脚旁麻绳一致，绳的两端有明显拉紧痕迹。桌椅有近距离挣动的擦痕，现场没有其他伤害方式的痕迹。'),
        'motive':record(conflict['truth'],'案发之前','r3',conflict['title'],conflict['target'],conflict['observation']),
        'access':record(f'{scene}只有一个可通行入口，其余开口为固定封闭结构；案发窗口内至发现者进门前，没有其他进入者。所有原始记录均完整保存；只有门口摄像机的叠加画面时钟{offset_text}，这不是人为篡改。',f'{a}–{b}','r3','校时记录与通道图','设备维护档案夹',f'维护记录：门口摄像机的画面时钟比主时钟{offset_text}，前后两次校准结果相同；其余设备均用主时钟，独立备用电源使原始记录连续完整。通道图及实物封条显示{scene}只有这一扇门可通行，其余开口封闭。从{a}直到{b}发现者进门前的完整文件里，除死者外只有门口片段中的那个人进入。'),
        'innocent_secret':record(secret['truth'],'案发之前','r1',secret['title'],secret['target'],secret['observation']),
    }
    return story
