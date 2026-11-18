"""Version-two evidence structures, compiled once before play.

These are bounded causal puzzles, not a generator of arbitrary physical worlds.
The old compiler remains available for operations pinned before this version.
"""

from copy import deepcopy


def diversify(case, seed):
    family=case['family']
    if family=='clock':return
    cast={a:r['name'] for a,r in case['roles'].items()}
    killer=case['solution']['killer'];witness=case['arrival'][2]
    culprit=cast[killer];lender=cast[witness]
    history={f['id']:f for f in case['history']};t=history['crime']['time']
    lower=18*60+seed%70
    clock=lambda n:f'{n//60:02d}:{n%60:02d}'
    loan,returned=clock(lower-9),clock(lower+9)
    code='K'+str(11+seed%70)
    records={c['id']:c for c in case['clues']}

    def replace(cid,title,words,location,protected=False,locked=False,category='document'):
        records[cid].update(title=title,target=title,observation=words,location=location,
                            protected=protected,locked=locked,category=category)

    history['access']['text']='现场没有覆盖所有人的连续人脸进出记录；身份、器物保管与行为需要分别核对。'
    if family=='substitution':
        replace('c3','无声的换杯片段',f'{t}，佩戴 {code} 工作牌的人将蓝缺口杯与白缺口杯交换；镜头只拍到工作牌和双手，没有脸。随后死者拿起蓝杯饮用。片段没有显示杯中成分，也不能把工作牌直接当作佩戴者身份。','r2')
        replace('c7','席位与杯底编号',f'原始席位照片中，蓝缺口杯在{culprit}的席位，白缺口杯在死者席位。照片中的杯底编号与现场封存编号相同，照片早于最后存活记录。','r1',category='trace')
        replace('c8','工作牌初始领用表',f'工作牌 {code} 最初由{lender}领用。表末特别留有临时借用栏，原始登记只证明初始领用，不能证明后来谁在佩戴。','r2',protected=True)
        transfer=f'{loan}，{lender}把 {code} 工作牌借给{culprit}；{returned}，由{culprit}亲自归还。双方签名和借还时间均在原件上；期间没有再次转借。'
        replace('c9','工作牌借还原件',transfer,'r3',protected=True,locked=True)
        replace('c10','独立保存的换杯底片',records['c3']['observation']+' 底片连续，编号与原片一致。','r3',protected=True,locked=True)
        replace('c11','封存检验副本',records['c4']['observation'],'r3',protected=True,locked=True)
        case['proofs']={'identity':[['c1','c2','c3','c4','c7','c8','c9'],['c1','c2','c10','c11','c7','c8','c14']],
                        'time':[['c1','c2']], 'method':[['c3','c4','c7'],['c10','c11','c7']]}
        explanation='工作牌的最初领用者不等于换杯者；借还时间确定实际佩戴者，再将换杯过程、杯底编号与检验对应。仅凭到过现场或持有工作牌都不能独立证明杀害。'
    else:
        replace('c3','公共区域的声音记录',f'{t} 左右公共区域能听到{culprit}说话，画面没有出现说话者。另一段事前录音也有相近的背景杂音；声音是否实时需要比对。','r1')
        replace('c4','播放任务与音轨校验',f'终端在 {t} 自动播放先前保存的{culprit}发言。字句、停顿和背景敲击与公共区记录逐段相同。终端的播放任务是预先设置的，发声不能证明人在终端旁。','r3',locked=True)
        replace('c7','伤口内的工具断片',f'调查开始前的封存照片和检验记录显示，致命伤中的断片与编号 {code} 工具的断口严密吻合；另有死者现场血迹留在这件工具上。工具是现场近距离使用的，没有远程装置。','r2',category='trace')
        replace('c8','工具初始保管单',f'编号 {code} 的工具最初登记在{lender}名下，近期有借出标记。登记人不一定是使用者；需要核对实际借还和断口形成时间。','r2',protected=True)
        transfer=f'{loan}，{lender}将完好的 {code} 工具交给{culprit}，{returned}由{culprit}亲自归还。借还凭据与连续保管记录相互对应，这段期间工具未交给第三人。'
        replace('c9','工具借还与连续保管记录',transfer,'r3',protected=True,locked=True)
        replace('c10','借出与归还的端面照片',f'编号 {code} 工具在 {loan} 借出时端面完整；{returned} 归还时有一处新缺口。照片带有原始签时，缺口轮廓与现场断片可以逐点比对。','r3',protected=True,locked=True)
        replace('c11','工具断片封存副本',records['c7']['observation'],'r3',protected=True,locked=True)
        case['proofs']={'identity':[['c1','c2','c3','c4','c7','c8','c9','c10'],['c1','c2','c3','c4','c11','c8','c14','c10']],
                        'time':[['c1','c2']], 'method':[['c3','c4','c7','c10'],['c3','c4','c11','c10']]}
        explanation='录音只能解释虚假的声音不在场证明，不能单独确定杀害者；工具的实际保管区间、新断口和伤口内断片共同指向使用者。最初登记的工具主人只是一个需要核实的线索。'

    # A role can trade a first-hand record, while an independent public archive
    # remains discoverable if that person refuses. Neither route needs a confession.
    private=deepcopy(records['c9'])
    private.update(id='c14',title='带私人备注的交接存根',target='带私人备注的交接存根',
                   observation=transfer+' 存根附有私人往来备注：'+case['roles'][witness]['secret_record'],
                   private_owner=witness,protected=False,locked=True,reveals=['s'+witness])
    case['clues'].append(private)
    history_fact={'id':'handover','time':loan+'—'+returned,'text':transfer}
    case['history'].append(history_fact)
    for a in (witness,killer):
        case['roles'][a]['knows'].append('handover')
        case['roles'][a]['memories'].append(history_fact['time']+'：'+transfer)
    case['roles'][witness]['memories'].append('你随身保留了这次交接的存根；出示存根也会暴露上面的私人备注。')
    case['solution']['reconstruction']+=' '+explanation
    if case['rules_version']>=3:
        # Initial ownership is a misleading lead, not a necessary premise once
        # actual custody is established independently by the signed transfer.
        case['proofs']['identity']=[[cid for cid in route if cid!='c8'] for route in case['proofs']['identity']]
        if case['rules_version']>=4 and family=='recording':
            # The verified comparison already contains the raw audio premise.
            for aspect in ('identity','method'):
                case['proofs'][aspect]=[[cid for cid in route if cid!='c3'] for route in case['proofs'][aspect]]
        case['evidence_equivalents']=({'c10':'c3','c11':'c4','c14':'c9'} if family=='substitution'
                                      else {'c11':'c7','c14':'c9'})
