"""Sourced, incremental private memory; originals and fixed knowledge stay intact."""
from copy import deepcopy

KINDS = ('observed', 'self_claim', 'heard_claim', 'unresolved', 'interpretation')
ENTRY_FIELDS = ('id', 'kind', 'text', 'sources')
MAX_ENTRIES = 12
# Historical request metadata only; current summary budgets are versioned separately.
MAX_TEXT = 950
# Historical wire metadata only. Never use these counts to reject a memory.
LEGACY_MAX_SOURCES = 30
LEGACY_MAX_ENTRY_SOURCES = 8
COMPACT_AT_ENTRIES = 9
COMPACT_AT_TEXT = 700
COMPACT_AT_SOURCES = 24
COMPACT_MAX_ENTRIES = 6
LEGACY_COMPACT_MAX_SOURCES = 20
# Historical prompt metadata; current validation uses the shared storage limits.
COMPACT_MAX_TEXT = COMPACT_AT_TEXT - 1


def required_fields(value, fields, error):
    """Consume known fields on a copy; preserve raw receipts and field order."""
    if not isinstance(value, dict) or not set(fields).issubset(value):
        raise ValueError(error)
    return {key: deepcopy(item) for key, item in value.items() if key in fields}


def source_count(rows):
    return len({s for row in rows for s in row['sources']})


def hard_limits(token_budget=False, text_budget=None, entry_limit=MAX_ENTRIES):
    if text_budget:return {'entries':entry_limit,'text_characters':text_budget-1}
    return {'entries':entry_limit} if token_budget else {'entries':entry_limit,'text_characters':MAX_TEXT}


def summary_targets(token_budget=False, text_budget=None):
    if text_budget:return {'advisory':True,'entries':6,'preferred_text_characters':[600,850],'shorter_is_valid':True}
    if token_budget:return {'advisory':True,'entries':6,'shorter_is_valid':True}
    return {'advisory':True,'entries':6,'preferred_text_characters':[400,550],'shorter_is_valid':True}


def limits(snapshot=False, source_capacity=False, source_limits=True):
    """Historical wire metadata; current validation uses hard_limits()."""
    result = {'entries': COMPACT_MAX_ENTRIES if snapshot else MAX_ENTRIES,
              'text_characters': COMPACT_MAX_TEXT if snapshot else MAX_TEXT}
    if source_limits:
        result.update(unique_sources=LEGACY_COMPACT_MAX_SOURCES if snapshot and source_capacity else LEGACY_MAX_SOURCES,
                      sources_per_entry=LEGACY_MAX_ENTRY_SOURCES)
    return result


class CapacityError(ValueError):
    """Safe numeric validation feedback, without source text or private IDs."""
    def __init__(self, message, rows, snapshot=False, source_capacity=False, text_budget=None, entry_limit=MAX_ENTRIES):
        super().__init__(message)
        self.feedback = {'code': 'memory_capacity', 'scope': 'snapshot' if snapshot else 'active_memory',
                         'actual': {'entries': len(rows), 'text_characters': sum(len(r['text']) for r in rows),
                                    'unique_sources': source_count(rows)},
                         'limits': hard_limits(token_budget=True,text_budget=text_budget,entry_limit=entry_limit),
                         'entry_lengths':[{'id':row['id'],'text_characters':len(row['text'])} for row in rows]}
        if text_budget:self.feedback['summary_text_budget']=text_budget
        if snapshot and entry_limit!=MAX_ENTRIES:self.feedback['summary_entry_limit']=entry_limit


class EntrySourcesError(ValueError):
    """Entry-local correction; never echo unknown source IDs or source bodies."""
    def __init__(self, identity, sources, allowed):
        super().__init__('memory entry sources')
        self.invalid = [(index, source) for index, source in enumerate(sources)
                        if not isinstance(source, str) or source not in allowed] if isinstance(sources, list) else []
        problems = []
        actual = {}
        if not isinstance(sources, list):
            problems.append('expected_list')
        else:
            actual['sources_per_entry'] = len(sources)
            if not sources:problems.append('empty_sources')
            if any(not isinstance(s, str) or s not in allowed for s in sources):
                problems.append('unavailable_sources')
            strings = [s for s in sources if isinstance(s, str)]
            if len(set(strings)) != len(strings):problems.append('duplicate_sources')
        self.feedback = {
            'code': 'memory_entry_sources', 'entry_id': identity,
            'actual': actual, 'requirements': {'nonempty': True, 'unique': True, 'authorized': True},
            'problems': problems,
            'instruction': (
                'The rejected update was not applied. Each entry needs a nonempty list of distinct authorized '
                'source IDs. Recompute this entry from the supplied current memory and observations; '
                'an upsert replaces its text and sources, so do not accumulate every repeated occurrence. '
                'Source ID counts have no per-entry or total limit. Keep the citations needed to support '
                'the retained claims. Preserve important contradictions '
                'and attribution; never drop necessary citations while retaining unsupported claims. '
                'Use only this role\'s received observation IDs, acquired evidence IDs or initial fact IDs; '
                'do not invent sources or cite global event/text reference IDs. Original records remain stored. '
                'Return the complete requested response: a full role decision with corrected memory_update, '
                'or a complete entries snapshot for a memory task. Preserve the required processed_through.')}

    def with_context(self, data):
        """Identify only target IDs already disclosed in this role's action menu."""
        unread = {c['id'].partition(':')[2] for c in data.get('choices', [])
                  if c['id'].startswith('inspect:')}
        details = []
        for index, source in self.invalid[:12]:
            detail = {'index': index, 'reason': 'not_authorized'}
            if isinstance(source, str) and source in unread:
                detail.update(id=source, reason='visible_but_unread', permitted_use='action_target_only')
            details.append(detail)
        self.feedback.update(invalid_sources=details, invalid_source_count=len(self.invalid),
                             invalid_sources_truncated=len(self.invalid)>len(details))
        return self


class CheckpointError(ValueError):
    """Only pending, supplied observations can advance processing progress."""
    def __init__(self, message, observations, checkpoint, supplied, end):
        super().__init__(message)
        if end is not None:
            choices = [observations[end-1]['id']] if end > checkpoint else [None]
        else:
            choices = [None]
            for row in observations[checkpoint:]:
                if row['id'] not in supplied:break
                choices.append(row['id'])
        self.feedback = {'code': 'memory_checkpoint', 'allowed_processed_through': choices,
            'instruction': ('The rejected update was not applied. Set processed_through to one of '
                'allowed_processed_through. A memory snapshot must cover its supplied pending chunk. '
                'When the list is [null], there are no new observations to acknowledge: use null and '
                'keep the existing checkpoint. recalled_sources and citations in old memory are historical '
                'reference material, not newly pending observations. Never rewind progress to a recalled '
                'record. Return the complete requested response with the corrected checkpoint and supported '
                'memory content; keep necessary authorized citations, with no source-ID count limit.')}


def correction_feedback(feedback):
    """Correct actual limits; retire obsolete source counts only on unpaid retries."""
    result=deepcopy(feedback)
    text_budget=result.get('summary_text_budget')
    entry_limit=result.get('summary_entry_limit',MAX_ENTRIES) if result.get('scope')=='snapshot' else MAX_ENTRIES
    result['correction_version']=2
    result['source_count_limited']=False
    result['limits']={k:v for k,v in result.get('limits',{}).items()
                      if k not in ('unique_sources','sources_per_entry','text_characters')}
    result['text_character_limited']=bool(text_budget)
    if result['code']=='memory_capacity':
        result['limits']=hard_limits(token_budget=True,text_budget=text_budget,entry_limit=entry_limit)
        result['targets']=summary_targets(token_budget=True,text_budget=text_budget)
        result['correction_version']=5 if text_budget else 4
        if text_budget:result['memory_summary_view']=1
        entry_overflow=result.get('actual',{}).get('entries',0)>entry_limit
        if entry_overflow:
            result['correction_version']=6
            result.pop('entry_text_targets',None)
            result.pop('entry_targets_are_advisory',None)
            result.pop('repair_contract',None)
        if text_budget and result.get('rejected_snapshot') and not entry_overflow:
            rows=result['rejected_snapshot'];total=max(1,sum(len(row['text']) for row in rows))
            target=min(600,text_budget-1)
            result['entry_text_targets']=[{'id':row['id'],
                'preferred_characters':max(1,len(row['text'])*target//total)} for row in rows]
            result['entry_targets_are_advisory']=True
            if result.get('validated_draft'):
                result['repair_contract']='memory-text-repair-v2.txt'
    result['exceeded']={key:{'actual':actual,'maximum':result['limits'][key],
                            'reduce_by_at_least':actual-result['limits'][key]}
                       for key,actual in result.get('actual',{}).items()
                       if key in result['limits'] and actual>result['limits'][key]}
    if result['code']=='memory_entry_sources':
        result['problems']=[p for p in result.get('problems',[]) if p!='too_many_sources']
        result['requirements']={'nonempty':True,'unique':True,'authorized':True}
        instruction=(
            'Correct the named entry and invalid_sources. Their index is zero-based in the rejected entry. '
            'A disclosed ID with reason visible_but_unread is an available action target, NOT an acquired source. '
            'Do not put that ID in memory sources, even for unresolved or interpretation entries. Selecting '
            'inspect in this same response does not acquire it yet: memory_update is based on pre-action knowledge. '
            'Keep the intended inspection if useful, but cite the received observation ID for what someone told '
            'you about that record, or other acquired sources supporting the retained claim. A read_sources '
            'result marked unavailable supplies no contents and grants no source authorization. Do not simply '
            'delete a needed citation while retaining an unsupported factual claim; revise its attribution '
            'or keep it as a supported unresolved question. Unknown/foreign IDs are not disclosed by this feedback. ')
        if text_budget:
            instruction+=f'Keep the full summary below {text_budget} characters across all entry.text values. '
    elif result['code']=='memory_capacity' and result.get('scope')=='active_memory':
        result['correction_version']=7
        result['response_shape']='memory_update: {upsert, archive, processed_through}'
        instruction=(
            f'本次角色增量更新后有{result["actual"]["entries"]}条活动记忆，最多允许{MAX_ENTRIES}条。'
            '返回完整角色决策；memory_update 仍使用 upsert、archive、processed_through。'
            '只缩短文字不会减少条目数。按相容的认知种类与主题合并，在 upsert 更新保留条目，'
            '在 archive 显式列出当前已存储且被合并替代的旧条目ID。遗漏旧条目不会自动归档；'
            '不要输出 entries 替换快照，不要归档本次失败中尚未保存的新ID。'
            '归档与 upsert 不得包含同一个ID。保持原定 processed_through、归属与必要授权来源；'
            '只按有效内容更新记忆，不修改角色原本选择的动作来规避错误。')
    elif result['code']=='memory_capacity' and 'entries' in result['exceeded']:
        actual=result['actual']['entries']
        instruction=(
            f'本次失败是条目数量：返回了{actual}条，最多允许{entry_limit}条。'
            '只缩短每条文字不能解决这个错误。请重新按主题合并为约4—6条，返回完整 entries 替换快照。'
            '不要逐一保留 rejected_snapshot 中所有旧条目或为每个旧ID输出一条；'
            '合并后保留一个合法条目ID即可，未保留旧条目会归档，原始来源仍然完整可查。'
            '只合并认知种类与主题相容的内容，保持亲历事实、他人主张、自我说法、推断与未决事项的区分；'
            '保留合并后事实所需的授权来源，不要机械拼接或截断文本。'
            'rejected_snapshot 只是被拒绝的编辑草稿，不能授予新知识或来源权限。'
            '仍使用原定 processed_through；这是重新组织快照，不是逐条 text_replacements。')
        if text_budget:
            instruction+=f' 当前正文{result["actual"].get("text_characters",0)}字符；合并后总正文仍须少于{text_budget}字符，整个JSON仍受max_tokens约束。'
    elif text_budget:
        instruction=(
            f'上次摘要正文超限，尚未保存。所有 entries[*].text 合计必须少于 {text_budget} 字符，'
            f'最多{entry_limit}条；JSON字段和来源编号不计入正文，但计入 request.max_tokens。'
            '这一明确要求覆盖旧提示中的“无字数限制”。'
            'rejected_snapshot 是刚才被拒绝的草稿，不是已接受的记忆或新的证据；'
            '请以它为缩写对象重新合并主题，把全文缩到约500—700字，不要又从更长的旧 memory 全文照抄。'
            'entry_text_targets 已按这份草稿分配每条 text 的建议字数，请逐条缩写到该目标附近；'
            '通常一句短句即可，不要仍写整段。允许合并条目、更短或重新分配预算，不必凑字；这些不是逐条硬上限。'
            '每条尽量只写一两句，删去重复背景、反复对话和原文复述，保留关键结论、限定条件、'
            '有归属的矛盾和未履行的承诺。引用仍必须由本角色实际已知来源支持，草稿不会授予来源权限。'
            '来源编号按保留内容的需要保留，不靠砍引用或机械截断文本省字。'
            '仍返回完整替换后的JSON和原定 processed_through，不返回修改说明。 ')
    else:
        instruction=(
            f'The current memory structural limit is {entry_limit} entries. Text length is controlled by the '
            'request max_tokens for the complete JSON; there is no total or per-entry character limit '
            'and no character-count target. This supersedes historical text limits in the pinned prompt. '
            'Aim for roughly six enduring topics; shorter complete summaries need no padding. '
            'Rework the whole set, merge related '
            'topics and archive superseded interpretations while preserving important contradictions and '
            'attribution. Do not duplicate full evidence or the private deduction inside memory. '
            'Exceeding a target alone is valid; correct genuine hard-limit violations without truncating '
            'prose or removing citations needed by retained claims. Preserve the required processing range. ')
    text_note=('There is no per-entry text limit; the character ceiling applies only to the complete summary. '
               if text_budget else 'Memory text has no character-count limit. ')
    result['instruction']=(instruction+text_note+
        'Source ID counts have no per-entry or total limit; '
        'this current runtime policy supersedes historical count limits in instructions or capacity metadata. '
        'Keep all necessary authorized citations. '
        'Do not drop sources to meet an obsolete count. Source bodies and total request bytes remain budgeted. '
        'The rejected update was not applied. Return the complete requested response, preserving attribution '
        'and the required processed_through; a memory task requires a full snapshot, a role task a full decision.')
    return result


def repaired_snapshot(output, feedback):
    """Apply model-written text edits to a fully validated, unsaved snapshot."""
    if not feedback or not feedback.get('repair_contract'):
        return output
    if 'text_replacements' not in output:
        if feedback['repair_contract']=='memory-text-repair-v1.txt':return output
        raise ValueError('memory text repair requires text_replacements')
    edits=required_fields(output,('text_replacements',),'memory text repair fields')['text_replacements']
    if not isinstance(edits,list):raise ValueError('memory text repair list')
    rows=deepcopy(feedback['rejected_snapshot']);expected={row['id'] for row in rows};texts={}
    for edit in edits:
        edit=required_fields(edit,('id','text'),'memory text repair entry')
        if edit['id'] not in expected or edit['id'] in texts:raise ValueError('memory text repair identity')
        if not isinstance(edit['text'],str) or not edit['text'].strip():raise ValueError('memory text repair text')
        texts[edit['id']]=edit['text']
    if set(texts)!=expected:raise ValueError('memory text repair incomplete')
    for row in rows:row['text']=texts[row['id']]
    return {'entries':rows,'processed_through':feedback['processed_through']}


def validate_snapshot(rows, source_capacity=False, text_budget=None, *, entry_limit=MAX_ENTRIES):
    if len(rows) > entry_limit:
        raise CapacityError('memory snapshot entry capacity', rows, True, source_capacity,text_budget,entry_limit)
    if text_budget and sum(len(r['text']) for r in rows)>=text_budget:
        raise CapacityError('memory snapshot text capacity',rows,True,source_capacity,text_budget,entry_limit)


def needs_compaction(memory, source_capacity=False):
    # source_capacity is used only to reconstruct pre-v91 operation scheduling.
    rows = entries(memory)
    return (len(rows) >= COMPACT_AT_ENTRIES
            or sum(len(r['text']) for r in rows) >= COMPACT_AT_TEXT
            or (source_capacity and source_count(rows) >= COMPACT_AT_SOURCES))


def entries(memory):
    if 'entries' in memory:
        return deepcopy(memory['entries'])
    return ([{'id': 'm0', 'kind': 'interpretation', 'text': memory['summary'],
              'sources': list(memory['sources'])}] if memory.get('summary') else [])


def project(memory, capacity=False, source_capacity=False, source_limits=True, token_budget=False):
    result = {'entries': entries(memory), 'checkpoint': memory['checkpoint']}
    if capacity:
        result['capacity'] = {'active': len(result['entries']), 'maximum': MAX_ENTRIES,
            'free_entries': max(0, MAX_ENTRIES-len(result['entries'])),
            'text_characters': sum(len(r['text']) for r in result['entries']), 'maximum_text_characters': MAX_TEXT}
        if token_budget:
            result['capacity'].pop('text_characters')
            result['capacity'].pop('maximum_text_characters')
        if source_capacity:
            count = source_count(result['entries'])
            result['capacity']['unique_sources'] = count
            if source_limits:
                result['capacity'].update(maximum_unique_sources=LEGACY_MAX_SOURCES,
                    free_sources=max(0, LEGACY_MAX_SOURCES-count), maximum_sources_per_entry=LEGACY_MAX_ENTRY_SOURCES)
    return result


def revised(state, actor, patch, supplied, end=None):
    """Pure validation/preview. Null never consumes unprocessed observations."""
    old = state['memory'][actor]
    if patch is None:
        return deepcopy(old), []
    patch = required_fields(patch, ('upsert', 'archive', 'processed_through'), 'memory update fields')
    if not isinstance(patch['upsert'], list) or not isinstance(patch['archive'], list):
        raise ValueError('memory update lists')
    current = {row['id']: row for row in entries(old)}
    all_sources = ({o['id'] for o in state['observations'][actor]} | set(state['known'][actor])
                   | set(state['case']['roles'][actor]['knows']) | set(old['sources']))
    archived = []
    touched = set()
    for identity in patch['archive']:
        if not isinstance(identity, str) or identity not in current or identity in touched:
            raise ValueError('memory archive identity')
        touched.add(identity)
        archived.append(current.pop(identity))
    for row in patch['upsert']:
        row = required_fields(row, ENTRY_FIELDS, 'memory entry fields')
        identity = row['id']
        if (not isinstance(identity, str) or not identity.startswith('m')
                or not identity[1:].isdigit() or len(identity) > 12 or identity in touched):
            raise ValueError('memory entry identity')
        touched.add(identity)
        if row['kind'] not in KINDS:
            raise ValueError('memory entry kind')
        if not isinstance(row['text'], str) or not row['text'].strip():
            raise ValueError('memory entry text')
        sources = row['sources']
        if (not isinstance(sources, list) or not sources
                or any(not isinstance(s, str) or s not in all_sources for s in sources)
                or len(set(sources)) != len(sources)):
            raise EntrySourcesError(identity, sources, all_sources)
        if identity in current and current[identity] != row:
            archived.append(current[identity])
        current[identity] = deepcopy(row)
    if len(current) > MAX_ENTRIES:
        raise CapacityError('active memory capacity', list(current.values()))
    observations = state['observations'][actor]
    through = patch['processed_through']
    checkpoint = old['checkpoint']
    def checkpoint_error(message):
        return CheckpointError(message, observations, old['checkpoint'], supplied, end)
    if through is not None:
        indices = {o['id']: i + 1 for i, o in enumerate(observations)}
        if not isinstance(through, str) or through not in indices:
            raise checkpoint_error('memory checkpoint source')
        checkpoint = indices[through]
        if checkpoint < old['checkpoint'] or (end is not None and checkpoint != end):
            raise checkpoint_error('memory checkpoint range')
        if any(o['id'] not in supplied for o in observations[old['checkpoint']:checkpoint]):
            raise checkpoint_error('memory cannot skip unseen pending observations')
    elif end is not None and end > old['checkpoint']:
        raise checkpoint_error('memory compaction must cover the supplied chunk')
    rows = list(current.values())
    return {'entries': rows, 'summary': '\n'.join(r['text'] for r in rows),
            'sources': list(dict.fromkeys(s for r in rows for s in r['sources'])),
            'checkpoint': checkpoint}, archived


def apply(state, actor, patch, supplied, end=None):
    memory, archived = revised(state, actor, patch, supplied, end)
    if patch is not None:
        state['memory'][actor] = memory
        if archived:
            state.setdefault('memory_archive', {}).setdefault(actor, []).extend(
                dict(row, archived_revision=state['revision']) for row in archived)


def decision(state, actor, raw, data):
    """Decode the versioned wire response for the existing decision validator."""
    if not isinstance(raw, dict):
        raise ValueError('decision object')
    out = deepcopy(raw)
    fields={'action','speech','gesture','question_to','memory_update','belief_update','strategy_update',
            'relationships','progress','final_conclusion','next_decision','cancel_events'}
    if set(out)-fields:
        raise ValueError('unexpected decision fields')
    action = out.get('action')
    if not isinstance(action, dict) or set(action) != {'kind', 'args'}:
        raise ValueError('action fields')
    if (not isinstance(action['kind'], str) or not isinstance(action['args'], list)
            or any(not isinstance(a, str) or ':' in a for a in action['args'])):
        raise ValueError('action arguments')
    out['choice'] = ':'.join([action['kind'], *action['args']])
    if 'memory_update' not in out:
        raise ValueError('memory_update required')
    supplied = {o['id'] for o in data['observations']}
    try:
        memory, _ = revised(state, actor, out['memory_update'], supplied)
    except EntrySourcesError as exc:
        raise exc.with_context(data)
    out.update(memory=memory['summary'], memory_sources=memory['sources'])
    concealment = data.get('decision_mode') == 'concealment'
    key = 'strategy_update' if concealment else 'belief_update'
    if ('belief_update' if concealment else 'strategy_update') in out:
        raise ValueError('interpretation belongs to a different role perspective')
    if key not in out:
        raise ValueError(key + ' required')
    update = out[key]
    if update is not None and not isinstance(update, dict):
        raise ValueError('interpretation update')
    expected = {'situation', 'plan', 'sources'} if concealment else {'suspect', 'explanation', 'evidence_ids', 'testimony_ids'}
    if update is not None and update != {'clear': True} and set(update) != expected:
        raise ValueError('interpretation update fields')
    if update == {'clear': True}:
        update = {}
    if concealment:
        prior = state.get('strategies', {}).get(actor) or {}
        value = prior if update is None else update
        out.update(situation=value.get('situation', ''), strategy=value.get('plan', ''),
                   assessment_sources=value.get('sources', []))
        if update and set(update) != {'situation', 'plan', 'sources'}:
            raise ValueError('strategy update fields')
    else:
        prior = state['beliefs'][actor] or {}
        value = prior if update is None else update
        out.update(suspect=value.get('suspect'), reasoning=value.get('explanation', ''),
                   evidence_ids=value.get('evidence_ids', []), testimony_ids=value.get('testimony_ids', []))
        if update and set(update) != {'suspect', 'explanation', 'evidence_ids', 'testimony_ids'}:
            raise ValueError('belief update fields')
    if out['choice']=='lock_conclusion' and data.get('conclusion_task',{}).get('submission_format')=='per_aspect':
        from . import final_arguments
        out['final_conclusion']=final_arguments.normalize(state,actor,out.get('final_conclusion'))
    out.setdefault('relationships', [])
    return out
