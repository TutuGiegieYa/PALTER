"""An explicit solution-oracle argument for execution checks, not a playtest."""


def argument(case):
    solution=case['solution'];clues={c['id']:c for c in case['clues']}
    def cited(aspect):
        return '；'.join(clues[c]['title']+'显示：'+clues[c]['observation'] for c in case['proofs'][aspect][0])
    culprit=case['roles'][solution['killer']]['name']
    return (f"我指认{culprit}。身份推理：{cited('identity')}。"
            f"把死亡时间、在场痕迹、其他人的完整不在场记录以及出入口条件合在一起，排除其余人和外来者，能在这个时段到场作案的人是{culprit}。\n"
            f"时间推理：{cited('time')}。前一记录证明死者当时还活着，后一记录证明死者已经死亡，两者把作案时间限定在{solution['time']}，不能仅凭这些材料断定更精确的分钟。\n"
            f"手法推理：{cited('method')}。这些痕迹与{solution['method']}相吻合，我据此还原杀人方式和现场误导。")
