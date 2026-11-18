"""Explicit summary reserve and safe recovery before an unpaid role decision."""
import json

MAX_SUMMARY_ENTRIES = 6


def recovery_actors(rows,retry_state=None):
    """Preserve paid role/tool contexts; a recorded repair remains replayable."""
    paid=set();failed=set();repair=set();counts={}
    for row in rows:counts[row['stage']]=counts.get(row['stage'],0)+1
    for row in rows:
        actor=row['actor']
        if row['stage'].startswith('memory_headroom_'):repair.add(actor)
        if row['task']!='ensemble_role':continue
        if row['status']=='completed':paid.add(actor)
        if row['status']!='failed':continue
        start=(retry_state or {}).get(row['stage'],{}).get('start',0)
        if counts[row['stage']]-start>=4:continue
        feedback=json.loads(row['validation_feedback'] or '{}') or {}
        for issue in [feedback,*feedback.get('unresolved_issues',[])]:
            if issue.get('code')=='memory_capacity' and issue.get('scope')=='active_memory':failed.add(actor)
    return repair | (failed-paid)


def contract(limit):
    if type(limit) is not int or limit!=MAX_SUMMARY_ENTRIES:
        raise ValueError('unsupported memory summary reserve')
    return {'summary_maximum_entries':limit,'active_maximum_entries':12,'reserved_entries':12-limit,
            'instruction':f'本次完整摘要最多{limit}条，这是硬上限；活动记忆的12条容量用于之后的增量更新。'
                '按相容的认知种类和主题重新组织，保留必要归属与来源；不得机械截断、补造事实或把未完成行动写成已完成。'}
