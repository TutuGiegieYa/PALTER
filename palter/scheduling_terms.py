"""Versioned model-facing names; scheduling rules and stored receipts stay exact."""
from copy import deepcopy


def rename(value, names):
    return {names.get(key,key):item for key,item in value.items()}


def feedback(value):
    result=deepcopy(value)
    if str(result.get('field','')).startswith('next_decision'):
        result=rename(result,{
            'message_wait_allowed':'message_only_subscription_allowed',
            'disallowed_wait_events':'frequency_blocked_event_ids'})
        if 'instruction' in result:
            result['instruction']=result['instruction'].replace(
                'disallowed_wait_events','frequency_blocked_event_ids')
    if 'unresolved_issues' in result:
        result['unresolved_issues']=[feedback(issue) for issue in result['unresolved_issues']]
    return result


def project(data):
    """Render new terminology only at the gateway, including tool continuations."""
    result=deepcopy(data)
    if 'scheduling' in result:
        schedule=rename(result['scheduling'],{'waitable_events':'event_candidates'})
        quota=schedule.get('wait_frequency',{})
        if quota.get('version',1)>=2:
            schedule['wait_frequency']=rename(quota,{
                'next_observation_allowed':'passes_consecutive_wait_check'})
        guard=schedule.get('message_wait_guard',{})
        if guard:
            schedule['message_wait_guard']=rename(guard,{
                'message_wait_allowed':'message_only_subscription_allowed',
                'direct_contact_wait_allowed':'empty_subscription_allowed'})
        if 'decision_options' in schedule:
            menu=rename(schedule['decision_options'],{
                'allowed_modes':'supported_modes',
                'disallowed_wait_events':'frequency_blocked_event_ids',
                'message_only_wait_allowed':'message_only_subscription_allowed',
                'empty_wait_allowed':'empty_subscription_allowed'})
            if quota.get('version',1)>=2:
                menu['instruction']=(
                    '频率检查'+('通过' if quota['next_observation_allowed'] else '未通过')+
                    '；frequency_blocked_event_ids只列出连续等待规则禁止的目标，不代表全部调度限制。'
                    'event_candidates是已知候选，supported_modes是支持的格式，都不单独授予本轮等待许可。'
                    'mode=continue时events=[]；等待须同时满足频率检查、消息等待条件和目标自身条件。')
                if guard:
                    menu['instruction']+=(
                        ' 本轮消息等待条件允许纯消息订阅，但仍须通过频率检查。' if guard['message_wait_allowed'] else
                        ' 本轮message_only_subscription_allowed=false：不能仅订阅next_observation及其纯消息监听器，'
                        '也不能空events等待直接联系；等待须至少包含一个获准的具体事件。'
                        '混合OR订阅仍须通过频率检查。继续时自主选择实际行动、speech或gesture，不能原地空转；'
                        '终结动作沿用terminal_actions列出的例外。调度条件不透露他人的剧情状态。')
            schedule['decision_options']=menu
        result['scheduling']=schedule
    if result.get('validation_feedback'):
        result['validation_feedback']=feedback(result['validation_feedback'])
    return result
