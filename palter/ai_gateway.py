"""Versioned, scoped model tasks with persisted usage and no scripted fallback."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import secrets
import time
import urllib.error

from .deepseek import RATES
from .storage import StoreError, canonical, fingerprint
from . import compact_context, memory_entries, role_recovery

MAX_RETRY_COMPLETION_TOKENS = 8192
MAX_DYNAMIC_CONTEXT_BYTES = 51_200
MAX_REQUEST_BYTES = 90_000
DM_MAX_DYNAMIC_CONTEXT_BYTES = 512_000
DM_MAX_REQUEST_BYTES = 1_000_000


def request_sizes(body, prefix_messages):
    """Separate game context from required native reasoning, without editing wire data."""
    dynamic=deepcopy(body['messages'][prefix_messages:])
    thinking=body.get('thinking',{}).get('type')=='enabled'
    reasoning_bytes=0
    for message in dynamic:
        if (thinking and body.get('tools') and message.get('role')=='assistant'
                and isinstance(message.get('tool_calls'),list) and message['tool_calls']
                and isinstance(message.get('reasoning_content'),str)):
            reasoning_bytes+=len(canonical(message.pop('reasoning_content')).encode())
    return {'dynamic_bytes':len(canonical(dynamic).encode()),'reasoning_bytes':reasoning_bytes,
            'total_bytes':len(canonical(body).encode())}


def retry_request_settings(spec, previous):
    """Raise only an actually truncated thinking call; retain prior allowances."""
    if previous is None:return None
    settings=json.loads(previous['request_settings']) if previous['request_settings'] else None
    if spec.get('thinking',{}).get('type')!='enabled' or previous['status']!='failed':return settings
    response=json.loads(previous['response']) if previous['response'] else None
    if not isinstance(response,dict):return settings
    choices=response.get('choices')
    if not isinstance(choices,list) or not choices or not isinstance(choices[0],dict):return settings
    if choices[0].get('finish_reason')!='length':return settings
    current=(settings or {}).get('max_tokens',spec['tokens'])
    limit=max(current,min(current*2,MAX_RETRY_COMPLETION_TOKENS))
    return {'max_tokens':limit} if limit>spec['tokens'] else settings


def memory_rewrite_feedback(max_tokens, length_failures=1):
    """Change the rewrite strategy without enlarging the completion allowance."""
    length_failures=max(1,length_failures)
    target=min(max_tokens,(1200,1000,800)[min(length_failures-1,2)])
    return {'code':'memory_output_truncated','correction_version':2,
            'max_tokens':max_tokens,'length_failures':length_failures,
            'preferred_output_tokens':target,'target_is_advisory':True,
            'summary_text_budget':1024,'preferred_text_characters':[600,850],
            'memory_summary_view':1,
            'instruction':
            '上次摘要达到输出上限而被截断，未写入记忆。请重新组织完整摘要，不要接写半截JSON，'
            '不要沿着旧条目逐段复制再追加内容。完整JSON须在max_tokens内，preferred_output_tokens只是留余量的建议。'
            '所有entry.text合计必须少于1024字符，建议约600—800字；标点和空格算字符，来源编号与JSON字段不计入正文。'
            '此要求覆盖旧提示中的无字数限制。以约4—6个当前问题为主题，每条用一两句短句写结论、关键限定、'
            '矛盾、未履行承诺或待查事项。初始底牌每次已提供，不重抄；证据原文可查询，不复述全文；'
            '同一人的重复主张不逐次抄录，也不变成事实。本人取得的事实、我对外的说法、他人的主张和我的判断保持区别。'
            '保留支撑保留内容所需的授权来源，来源数量不限。遗漏的旧条目会归档，原始记录不删除。'
            '直接输出简洁完整的JSON，保持原定processed_through，不加说明或自检步骤。'}


class PausedWork(Exception):
    pass


def retryable(code):
    return code in ('connection_failed','invalid_model_output','process_interrupted','retry_exhausted') or code in ('http_408','http_409','http_425','http_429') or (isinstance(code,str) and code.startswith('http_5'))


def manually_retryable(code):
    # Admission failures make no provider call and must never enter an automatic
    # retry loop; a changed admission policy can permit an explicit later retry.
    return retryable(code) or code in ('context_budget','http_402')


def error_message(code):
    return {'invalid_model_output':'模型返回的信息不完整或格式有误', 'connection_failed':'模型连接中断或等待超时',
            'http_429':'模型服务暂时繁忙','retry_exhausted':'模型步骤已用完本轮自动重试机会',
            'not_configured':'请配置模型服务后重试','http_401':'模型服务凭证未通过验证',
            'http_402':'DeepSeek 账户余额不足，请充值后手动重试；不会自动重复请求',
            'http_403':'模型服务拒绝了访问'}.get(code,'模型步骤未完成')


def reserve_cost(payload):
    """Conservative admission estimate: uncached UTF-8 bytes plus framing and output cap."""
    _,input_rate,output_rate=RATES[payload['model']]
    input_bound=len(canonical(payload).encode('utf-8'))+128*len(payload['messages'])
    return (input_bound*input_rate+payload['max_tokens']*output_rate)/1_000_000


def normalize_output(task, output):
    """Normalize equivalent machine fields; never rewrite player-facing prose."""
    if task in ("dm", "private_dm", "case_dm") and isinstance(output,dict):
        assessments=output.get("assessments")
        if isinstance(assessments,list):
            for assessment in assessments:
                if isinstance(assessment,dict) and assessment.get("verdict") in ("true", "truthful"):
                    # Older task versions omitted the verdict enum. Preserve their
                    # affirmative assessment; ambiguous negative verdicts stay invalid.
                    assessment["verdict"]="supported"
    if task=="memory" and isinstance(output,dict):
        updates=output.get("relationships")
        if isinstance(updates,dict) and all(isinstance(v,dict) for v in updates.values()):
            updates=[{**value,"target":target} for target,value in updates.items()]
        if isinstance(updates,list):
            # No-op entries without evidence assert no relationship change.
            output["relationships"]=[r for r in updates if not (isinstance(r,dict) and r.get("trust_delta")==0 and r.get("sources")==[])]
    return output


def decode_response(task, response, tools=False):
    choice=response['choices'][0]
    if choice.get('finish_reason')=='tool_calls' and tools:
        message=choice['message']
        output={'_tool_message':{k:deepcopy(message[k]) for k in ('role','content','tool_calls','reasoning_content') if k in message}}
        output['_tool_message']['role']='assistant'
    elif choice.get('finish_reason')=='stop':output=json.loads(choice['message']['content'])
    else:raise ValueError('truncated model output')
    if not isinstance(output,dict):raise ValueError('expected object')
    return normalize_output(task,output)


def restored_output(row):
    """Preserve JSON field order used by later ordered prompts in this operation."""
    stored=json.loads(row['result'])
    if row['response']:
        try:original=decode_response(row['task'],json.loads(row['response']),tools=True)
        except (ValueError,KeyError,TypeError,IndexError,AttributeError):pass
        else:
            if canonical(original)==canonical(stored):return original
    return stored  # Legacy receipts without raw responses keep their existing form.


class Gateway:
    def __init__(self, store, client):
        self.store,self.client=store,client
        self.retry_delays=(1,2,4)
        directory=Path(__file__).parent/"prefixes"
        manifest=json.loads((directory/"manifest.json").read_text())
        from .model_contracts import CURRENT_PREFIX,check_published
        self.current_version=CURRENT_PREFIX
        files=[f for f in manifest if f.startswith(("ai-core-","ai-tasks-","event-protocol-","memory-text-repair-","economy-guidance-"))]
        for file in files:
            if hashlib.sha256((directory/file).read_bytes()).hexdigest()!=manifest[file]:
                raise ValueError("Published AI prefix changed")
        self.core=(directory/"ai-core-v1.txt").read_text()
        self.cores={f:(directory/f).read_text() for f in files if f.startswith('ai-core-')}
        self.event_protocols={f:(directory/f).read_text() for f in files if f.startswith('event-protocol-')}
        self.memory_repairs={f:(directory/f).read_text() for f in files if f.startswith('memory-text-repair-')}
        self.economy_guidance={f:json.loads((directory/f).read_text()) for f in files if f.startswith('economy-guidance-')}
        self.versions={file:json.loads((directory/file).read_text()) for file in files if file.startswith("ai-tasks-")}
        issues=check_published(self.versions[self.current_version])
        if issues:raise ValueError('current prefix contract: '+ '; '.join(issues))
        with store.transaction() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS ai_operations (
                  game_id TEXT NOT NULL, id TEXT NOT NULL, digest TEXT NOT NULL,
                  base_state TEXT NOT NULL, status TEXT NOT NULL, started REAL NOT NULL,
                  result TEXT, error TEXT, PRIMARY KEY(game_id,id));
                CREATE TABLE IF NOT EXISTS ai_calls (
                  id TEXT PRIMARY KEY, game_id TEXT NOT NULL, operation_id TEXT NOT NULL,
                  stage TEXT NOT NULL, task TEXT NOT NULL, actor TEXT,
                  prefix_hash TEXT NOT NULL, request_hash TEXT NOT NULL,
                  status TEXT NOT NULL, started REAL NOT NULL, latency_ms INTEGER,
                  usage TEXT, cost_upper_usd REAL, result TEXT, error TEXT,
                  attempt INTEGER NOT NULL);
            """)
            columns={row[1] for row in con.execute("PRAGMA table_info(ai_calls)")}
            for column in ("response", "diagnostic", "model", "validation_feedback", "request_feedback", "request_settings"):
                if column not in columns:con.execute(f"ALTER TABLE ai_calls ADD COLUMN {column} TEXT")
            if 'reserved_cost_usd' not in columns:con.execute('ALTER TABLE ai_calls ADD COLUMN reserved_cost_usd REAL')
            if "command" not in {row[1] for row in con.execute("PRAGMA table_info(ai_operations)")}:
                con.execute("ALTER TABLE ai_operations ADD COLUMN command TEXT")
            if "prefix_version" not in {row[1] for row in con.execute("PRAGMA table_info(ai_operations)")}:
                con.execute("ALTER TABLE ai_operations ADD COLUMN prefix_version TEXT")
            if "retry_state" not in {row[1] for row in con.execute("PRAGMA table_info(ai_operations)")}:
                con.execute("ALTER TABLE ai_operations ADD COLUMN retry_state TEXT NOT NULL DEFAULT '{}'")
            con.execute("UPDATE ai_calls SET status='interrupted',error='process_interrupted' WHERE status='pending'")
            con.execute("UPDATE ai_operations SET status='interrupted' WHERE status='pending'")

    def payload(self,task,baseline,data,version=None,request_settings=None):
        spec=self.versions[version or self.current_version][task]
        if task=='ensemble_role' and (data.get('validation_feedback') or {}).get('role_recovery_version'):
            from . import role_schedule
            data=deepcopy(data)
            if 'scheduling' in data:
                data['scheduling']['decision_options']=role_schedule.decision_options(data['scheduling'])
        if '_event_review_upgrade' in data:
            data=deepcopy(data);upgrade=data.pop('_event_review_upgrade')
            if (data.get('validation_feedback') or {}).get('event_context_repair')==1:
                data.update(upgrade)
        extra=(data.get('validation_feedback') or {}).get('event_source_background')
        if task=='ensemble_dm' and extra:
            from . import role_events
            data=deepcopy(data)
            contexts=data['event_recipient_contexts']
            allowed={actor:{row[key] for field in ('received_records','background_records') for row in ctx.get(field,[]) for key in ('id','event_id')}
                |{row['id'] for field in ('own_initial_facts','acquired_evidence') for row in ctx.get(field,[])} for actor,ctx in contexts.items()}
            _,data['event_recipient_contexts'],_=role_events.merge_background((data['tracked_events'],contexts,allowed),extra,True)
        economy=bool(spec.get('context_economy'))
        order_version=spec.get('context_order_version',1)
        if economy:
            from . import context_economy
            data=deepcopy(data)
            feedback=data.get('validation_feedback') or {}
            if feedback.get('dm_event_repair'):
                missing=set(feedback['missing_ids'])
                data['tracked_events']=[r for r in data['tracked_events'] if r['id'] in missing]
                creators={r['creator'] for r in data['tracked_events']}
                data['event_recipient_contexts']={a:v for a,v in data['event_recipient_contexts'].items() if a in creators}
                for key in ('utterances','new_utterance_ids','private_history','recent_delivery','recent_actual_events'):data[key]=[]
                data['dm_event_repair']=True
                data['validation_feedback']={'code':'missing_event_decisions','missing_ids':feedback['missing_ids']}
            data['active_guidance']=context_economy.guide(task,data,self.economy_guidance[spec['economy_guidance']])
        repair=(data.get('validation_feedback') or {}).get('repair_contract') if task=='ensemble_memory' else None
        if repair:
            feedback=data['validation_feedback']
            if repair not in self.memory_repairs or not feedback.get('validated_draft'):
                raise ValueError('unrecognized memory text repair contract')
            spec={**spec,'instruction':self.memory_repairs[repair],
                'example':{'text_replacements':[{'id':'m0','text':'我仍需核实双方说法的矛盾。'}]},
                'tools':[],'response_format':{'type':'json_object'},'bounded_context':False,
                'compact_context':False,'memory_summary_view':False}
            baseline={'actor':(baseline or {}).get('actor')}
            if repair=='memory-text-repair-v1.txt':
                data={'validation_feedback':deepcopy(feedback),'snapshot_limits':deepcopy(feedback['limits'])}
            else:
                targets={r['id']:r['preferred_characters'] for r in feedback['entry_text_targets']}
                data={'repair_contract':repair,'snapshot_limits':deepcopy(feedback['limits']),
                    'target_text_characters':600,'rewrite_entries':[
                        {'id':r['id'],'kind':r['kind'],'text':r['text'],'target_characters':targets[r['id']]}
                        for r in feedback['rejected_snapshot']]}
        summary_view=task=='ensemble_memory' and bool(spec.get('memory_summary_view') or (data.get('validation_feedback') or {}).get('memory_summary_view'))
        if task=='ensemble_memory' and spec.get('memory_summary_view') and baseline is not None:
            baseline={key:deepcopy(baseline[key]) for key in ('actor','cast','experienced_facts') if key in baseline}
        if task=='ensemble_role':
            variant=spec.get('perspectives',{}).get((baseline or {}).get('decision_mode'))
            if variant:spec={**spec,**variant}
        elif task=='ensemble_theory':
            variant=spec.get('perspectives',{}).get(data.get('review_mode'))
            if variant:spec={**spec,**variant}
        if task=='ensemble_role' and spec.get('scheduling_terms_version'):
            from . import scheduling_terms
            data=scheduling_terms.project(data)
        # Keep the outward task name generic; a private role variant must not
        # reveal an identity through the usage trace available to other players.
        protocol=self.event_protocols[spec['event_protocol']]+'\n' if spec.get('event_protocol') else ''
        instructions=self.cores[spec.get('core_version','ai-core-v1.txt')]+'\n'+protocol+"PALTER_TASK: "+task+"\n"+spec["instruction"]+"\nEXAMPLE JSON:\n"+json.dumps(spec["example"],ensure_ascii=False,indent=2)
        messages=[{"role":"system","content":instructions}]
        if baseline is not None:messages.append({"role":"system","content":"IMMUTABLE AUTHORIZED BASELINE:\n"+canonical(baseline)})
        prefix={"model":spec.get("model",self.client.settings.model),"messages":deepcopy(messages),"thinking":spec.get("thinking",{"type":"disabled"}),
                "temperature":spec.get("temperature",0.3),"max_tokens":spec["tokens"],"response_format":spec.get("response_format",{"type":"json_object"}),"stream":False}
        if request_settings:
            if set(request_settings)-{'max_tokens','json_final_only'}:raise ValueError('invalid persisted request settings')
            if 'json_final_only' in request_settings and (task!='ensemble_role' or request_settings['json_final_only'] is not True):
                raise ValueError('invalid final JSON correction setting')
            limit=request_settings.get('max_tokens',spec['tokens'])
            if (type(limit) is not int
                    or not spec['tokens']<=limit<=MAX_RETRY_COMPLETION_TOKENS):
                raise ValueError('invalid persisted completion allowance')
            prefix['max_tokens']=limit
        if "reasoning_effort" in spec:prefix["reasoning_effort"]=spec["reasoning_effort"]
        if spec.get('tools'):prefix.update(tools=deepcopy(spec['tools']),tool_choice='auto')
        if (request_settings or {}).get('json_final_only'):
            prefix['response_format']={'type':'json_object'}
            if spec.get('tools'):prefix['tool_choice']='none'
        body=deepcopy(prefix)
        dynamic=deepcopy(data);tool_messages=dynamic.pop('_tool_messages',[]) if spec.get('tools') else []
        packed=(compact_context.pack(task,dynamic,authorized_keys=spec.get('authorized_source_keys',False),
            memory_capacity=spec.get('memory_capacity',False),memory_source_capacity=spec.get('memory_source_capacity',False),
            memory_source_limits=spec.get('memory_source_limits',True),memory_policy=bool(spec.get('memory_policy')),
            memory_token_budget=bool(spec.get('memory_token_budget')),
            memory_character_budget=spec.get('memory_character_budget'),
            memory_summary_view=summary_view,
            memory_snapshot_max_entries=data.get('_memory_snapshot_max_entries',spec.get('memory_snapshot_max_entries'))
                if task=='ensemble_memory' else None) if spec.get('compact_context') else dynamic)
        if economy and task=='ensemble_dm':packed=context_economy.deduplicate_dm(packed)
        def assemble(value):
            request=deepcopy(prefix)
            content=compact_context.dumps(value) if spec.get('compact_context') else canonical(value)
            request['messages'].append({'role':'user','content':content})
            if tool_messages:request['messages'].extend(deepcopy(tool_messages))
            return request
        limits=spec.get('context_limits',{}) if task=='ensemble_dm' else {}
        # Admission limits are runtime policy, not prompt content. Old pinned DM
        # operations can retry under the larger guard without changing paid bytes.
        dynamic_limit=limits.get('dynamic_bytes',DM_MAX_DYNAMIC_CONTEXT_BYTES if task=='ensemble_dm' else MAX_DYNAMIC_CONTEXT_BYTES)
        request_limit=limits.get('total_bytes',DM_MAX_REQUEST_BYTES if task=='ensemble_dm' else MAX_REQUEST_BYTES)
        if task=='ensemble_dm' and spec.get('knowledge_sharing_version'):
            from . import dm_context
            packed=dm_context.pack(packed,lambda value:request_sizes(assemble(value),len(messages))['total_bytes'])
        if spec.get('bounded_context'):
            from . import working_context
            final_order=economy and packed.get('dialogue_focus',{}).get('version',0)>=3
            packed=working_context.fit(packed,lambda value:request_sizes(
                assemble(context_economy.order(value,order_version) if final_order else value),len(messages)),
                dynamic_limit,request_limit,
                optional_body_bytes=0 if summary_view else (
                    spec.get('final_source_body_budget',spec.get('source_body_budget',3000)) if economy and data.get('conclusion_task',{}).get('final')
                    else spec.get('source_body_budget',3000) if economy else working_context.OPTIONAL_BODY_BYTES),
                economy=economy,evidence_first=bool(spec.get('evidence_first')))
        if economy:packed=context_economy.order(packed,order_version)
        elif order_version>=2:
            from . import context_economy
            packed=context_economy.cache_order(packed)
        body=assemble(packed)
        # Game data and tool results retain their own bound. Provider reasoning
        # must roundtrip unchanged and remains covered by the total/cost bounds.
        sizes=request_sizes(body,len(messages))
        if sizes['dynamic_bytes']>dynamic_limit or sizes['total_bytes']>request_limit:
            raise StoreError(f"本轮上下文超过预算（动态内容最多 {dynamic_limit/1000:g} KB，总请求最多 {request_limit/1000:g} KB）。",409,"context_budget")
        return body,fingerprint(prefix)

    def retry_state(self,con,game_id,operation_id):
        row=con.execute('SELECT retry_state FROM ai_operations WHERE game_id=? AND id=?',(game_id,operation_id)).fetchone()
        return json.loads(row['retry_state']) if row else {}

    def renew_retry(self,con,game_id,operation_id):
        """Called only inside an idempotent, explicitly requested control transaction."""
        operation=con.execute('SELECT status FROM ai_operations WHERE game_id=? AND id=?',(game_id,operation_id)).fetchone()
        if not operation or operation['status'] in ('completed','cancelled','pending'):
            raise StoreError('这一步已结束或仍在处理中。',409,'ai_pending')
        progress=self.retry_state(con,game_id,operation_id)
        rows=con.execute('SELECT stage,COUNT(*) AS n FROM ai_calls WHERE game_id=? AND operation_id=? GROUP BY stage',(game_id,operation_id)).fetchall()
        for row in rows:
            latest=con.execute('SELECT status,error FROM ai_calls WHERE game_id=? AND operation_id=? AND stage=? ORDER BY attempt DESC LIMIT 1',(game_id,operation_id,row['stage'])).fetchone()
            if latest['status']=='completed':continue
            prior=progress.get(row['stage'],{})
            progress[row['stage']]={'start':row['n'],'round':prior.get('round',0)+1}
        con.execute('UPDATE ai_operations SET retry_state=? WHERE game_id=? AND id=?',(canonical(progress),game_id,operation_id))

    def _wait_retry(self,owner,game_id,operation_id,until):
        while True:
            with self.store.transaction(False) as con:
                state=self.store.load(con,owner,game_id)
                op=con.execute('SELECT status FROM ai_operations WHERE game_id=? AND id=?',(game_id,operation_id)).fetchone()
            if state['archived'] or (op and op['status']=='cancelled'):raise StoreError('操作已取消。',409,'cancelled')
            if state['phase']=='paused':raise PausedWork()
            remaining=until-time.time()
            if remaining<=0:return
            time.sleep(min(.1,remaining))

    def call(self,owner,game_id,operation_id,stage,task,baseline,data,validator,actor=None,version=None):
        while True:
            with self.store.transaction(False) as con:
                progress=self.retry_state(con,game_id,operation_id).get(stage,{})
            self._wait_retry(owner,game_id,operation_id,progress.get('next_at',0))
            try:
                result=self._attempt(owner,game_id,operation_id,stage,task,baseline,data,validator,actor,version)
                if progress:
                    with self.store.transaction() as con:
                        all_progress=self.retry_state(con,game_id,operation_id)
                        all_progress.get(stage,{}).pop('next_at',None)
                        con.execute('UPDATE ai_operations SET retry_state=? WHERE game_id=? AND id=?',(canonical(all_progress),game_id,operation_id))
                return result
            except StoreError as exc:
                if not retryable(exc.code) or exc.code=='retry_exhausted':raise
                with self.store.transaction() as con:
                    progress=self.retry_state(con,game_id,operation_id)
                    record=progress.setdefault(stage,{'start':0,'round':0})
                    count=con.execute('SELECT COUNT(*) FROM ai_calls WHERE game_id=? AND operation_id=? AND stage=?',(game_id,operation_id,stage)).fetchone()[0]
                    used=count-record['start'];record.update(error=exc.code,attempts=used)
                    if used<4:
                        delay=max(self.retry_delays[min(max(used-1,0),2)],getattr(exc,'retry_after',0))
                        record['next_at']=time.time()+min(delay,30)
                    else:record.pop('next_at',None)
                    con.execute('UPDATE ai_operations SET retry_state=? WHERE game_id=? AND id=?',(canonical(progress),game_id,operation_id))
                if used>=4:
                    raise StoreError(error_message(exc.code)+'。已尝试 4 次（含 3 次自动重试），已有进展保留；请决定是否再次重试。',503,'retry_exhausted') from None

    def _attempt(self,owner,game_id,operation_id,stage,task,baseline,data,validator,actor=None,version=None):
        spec=self.versions[version or self.current_version][task]
        capacity_feedback=spec.get('memory_source_capacity',False)
        event_feedback=spec.get('event_basis_version',False)
        position_feedback=spec.get('role_review_version',0)>=2
        with self.store.transaction() as con:
            state=self.store.load(con,owner,game_id)
            if state["archived"]:raise StoreError("这局已归档，停止新的模型调用。",409,"archived")
            operation=con.execute("SELECT status,base_state FROM ai_operations WHERE game_id=? AND id=?",(game_id,operation_id)).fetchone()
            if operation and operation["status"]=="cancelled":raise StoreError("本轮操作已取消。",409,"cancelled")
            if operation:
                base=json.loads(operation['base_state'])
                if state['events']!=base['events'] or state['observations']!=base['observations']:
                    raise StoreError('游戏状态已变化，旧请求未再次发送。',409,'context_changed')
            cached=con.execute("SELECT * FROM ai_calls WHERE game_id=? AND operation_id=? AND stage=? AND status='completed' ORDER BY started DESC LIMIT 1",(game_id,operation_id,stage)).fetchone()
            attempt_data=data;request_feedback=None
            if capacity_feedback or event_feedback or position_feedback or task.startswith('ensemble_'):
                # Reconstruct the same bounded correction across retry rounds and
                # restarts. A completed receipt uses only its preceding failures.
                feedback=con.execute("""SELECT * FROM ai_calls
                    WHERE game_id=? AND operation_id=? AND stage=? AND task=? AND actor IS ?
                      AND status='failed' AND validation_feedback IS NOT NULL AND (? IS NULL OR attempt<?)
                    ORDER BY attempt DESC LIMIT 1""",
                    (game_id,operation_id,stage,task,actor,cached['attempt'] if cached else None,cached['attempt'] if cached else None)).fetchone()
                if cached and cached['request_feedback'] is not None:
                    request_feedback=json.loads(cached['request_feedback'])
                elif feedback:
                    request_feedback=json.loads(feedback['validation_feedback'])
                    # Upgrade old generic source feedback locally. These two
                    # validators are pure; never change a paid request or receipt.
                    if (not cached and task in ('ensemble_role','ensemble_memory')
                            and request_feedback.get('code')=='memory_entry_sources'
                            and 'invalid_sources' not in request_feedback and feedback['result']):
                        try:validator(restored_output(feedback))
                        except memory_entries.EntrySourcesError as exc:request_feedback=exc.feedback
                        except (ValueError,KeyError,TypeError,IndexError,AttributeError):pass
                    if (not cached and task=='ensemble_dm' and feedback['result']
                            and request_feedback.get('code') in ('event_decision_contract','event_source_contract')):
                        from .role_events import EventSourceError
                        if hasattr(validator,'prepare_request'):validator.prepare_request(request_feedback)
                        try:validator(restored_output(feedback))
                        except EventSourceError as exc:request_feedback=json.loads(canonical(exc.feedback))
                        except (ValueError,KeyError,TypeError,IndexError,AttributeError):pass
                    # New retry inputs get actionable correction. Old paid
                    # stages retain the exact historical input during recovery.
                    if not cached and request_feedback.get('code') in ('memory_capacity','memory_entry_sources'):
                        request_feedback=json.loads(canonical(memory_entries.correction_feedback(request_feedback)))
                    if (not cached and task=='ensemble_memory' and spec.get('memory_token_budget')
                            and request_feedback.get('code')=='memory_output_truncated'):
                        failures=con.execute("""SELECT COUNT(*) FROM ai_calls
                            WHERE game_id=? AND operation_id=? AND stage=? AND task=? AND actor IS ?
                              AND status='failed' AND json_extract(validation_feedback,'$.code')='memory_output_truncated'""",
                            (game_id,operation_id,stage,task,actor)).fetchone()[0]
                        request_feedback=json.loads(canonical(memory_rewrite_feedback(
                            request_feedback.get('max_tokens',spec['tokens']),failures)))
                if request_feedback:
                    attempt_data=deepcopy(data)
                    attempt_data['validation_feedback']=request_feedback
            if not cached and role_recovery.enabled(task,spec):
                failures=con.execute("""SELECT * FROM ai_calls WHERE game_id=? AND operation_id=?
                    AND stage=? AND task=? AND actor IS ? AND status='failed'
                    AND validation_feedback IS NOT NULL ORDER BY attempt""",
                    (game_id,operation_id,stage,task,actor)).fetchall()
                revalidate=bool(getattr(validator,'revalidate_role_feedback',False))
                recovered=role_recovery.recover(failures,validator,decode_response,revalidate=revalidate)
                if revalidate and not recovered:
                    request_feedback=None;attempt_data=data
                if recovered:
                    request_feedback=json.loads(canonical(recovered))
                    attempt_data=deepcopy(data);attempt_data['validation_feedback']=request_feedback
            if cached:
                request_settings=json.loads(cached['request_settings']) if cached['request_settings'] else None
            else:
                previous=con.execute("""SELECT status,response,request_settings FROM ai_calls
                    WHERE game_id=? AND operation_id=? AND stage=? AND task=? AND actor IS ?
                    ORDER BY attempt DESC LIMIT 1""",(game_id,operation_id,stage,task,actor)).fetchone()
                request_settings=retry_request_settings(spec,previous)
                if role_recovery.enabled(task,spec) and (request_feedback or {}).get('json_final_only'):
                    request_settings={**(request_settings or {}),'json_final_only':True}
            payload,prefix_hash=self.payload(task,baseline,attempt_data,version,request_settings)
            if hasattr(validator,'prepare_request'):validator.prepare_request(request_feedback)
            reserved=reserve_cost(payload)
            request_hash=fingerprint(payload)
            if cached:
                if cached["request_hash"]!=request_hash:raise StoreError("恢复任务的上下文已改变，请开始新的操作。",409,"context_changed")
                return restored_output(cached),cached["id"]
            if state["phase"]=="paused":raise PausedWork()
            attempts=con.execute("SELECT COUNT(*) FROM ai_calls WHERE game_id=? AND operation_id=? AND stage=?",(game_id,operation_id,stage)).fetchone()[0]
            retry_start=self.retry_state(con,game_id,operation_id).get(stage,{}).get('start',0)
            if attempts-retry_start>=4:raise StoreError('本轮已尝试 4 次；请在页面决定是否再次重试。',409,'retry_exhausted')
            if not self.client.configured:raise StoreError('请在 .env 配置 DEEPSEEK_API_KEY。',503,'not_configured')
            if task=="review" and con.execute("SELECT COUNT(*) FROM ai_calls WHERE game_id=? AND task='review'",(game_id,)).fetchone()[0]>=3:
                raise StoreError("本局线索整理已达到三次上限。",409,"review_budget")
            count,cost=con.execute("SELECT COUNT(*),COALESCE(SUM(COALESCE(cost_upper_usd,reserved_cost_usd,0.015)),0) FROM ai_calls WHERE game_id=?",(game_id,)).fetchone()
            if 'watch' in state:
                limit=state['watch'].get('call_limit',128)
                if count>=limit:raise StoreError(f'已达到本局 {limit} 次调用上限，已有进展保留；可增加 64 次后继续。',409,'watch_call_limit')
                if cost+reserved>state['watch']['budget_usd']+1e-9:
                    raise StoreError('剩余预算不足以预留下一次调用，已暂停；可增加 0.05 美元后继续。',409,'watch_budget')
            else:
                legacy_cost=con.execute('SELECT COALESCE(SUM(COALESCE(cost_upper_usd,0.015)),0) FROM ai_calls WHERE game_id=?',(game_id,)).fetchone()[0]
                if count>=128 or legacy_cost>=0.25:raise StoreError("本局已达到 AI 调用预算，已停止新增调用。",409,"ai_budget")
            call_id=secrets.token_hex(12)
            con.execute("INSERT INTO ai_calls(id,game_id,operation_id,stage,task,actor,prefix_hash,request_hash,status,started,attempt) VALUES (?,?,?,?,?,?,?,?,'pending',?,?)",
                        (call_id,game_id,operation_id,stage,task,actor,prefix_hash,request_hash,time.time(),attempts+1))
            con.execute("UPDATE ai_calls SET model=?,reserved_cost_usd=?,request_feedback=?,request_settings=? WHERE id=?",
                        (payload["model"],reserved,canonical(request_feedback),canonical(request_settings),call_id))
        start=time.monotonic();usage=None;cost=None;output=None;error=None;response=None;diagnostic=None;retry_after=0;feedback=None;validated=False;validation_error=None
        try:
            if not self.client.configured:raise StoreError("请在 .env 配置 DEEPSEEK_API_KEY；正式模式不会切换成脚本。",503,"not_configured")
            response=self.client.transport(payload)
            if not isinstance(response,dict):raise ValueError("invalid response")
            raw=response.get("usage")
            if isinstance(raw,dict):
                keys=("prompt_tokens","completion_tokens","prompt_cache_hit_tokens","prompt_cache_miss_tokens")
                usage={k:raw[k] if type(raw.get(k)) is int and raw[k]>=0 else None for k in keys}
                if all(usage[k] is not None for k in keys) and usage["prompt_tokens"]==usage["prompt_cache_hit_tokens"]+usage["prompt_cache_miss_tokens"]:
                    h,m,o=RATES[payload["model"]]
                    cost=(usage["prompt_cache_hit_tokens"]*h+usage["prompt_cache_miss_tokens"]*m+usage["completion_tokens"]*o)/1e6
            output=decode_response(task,response,tools=bool(payload.get('tools')) and payload.get('tool_choice')!='none')
            if task=='ensemble_dm' and (request_feedback or {}).get('dm_event_repair'):
                from . import context_economy
                output=json.loads(canonical(context_economy.merge_event_repair(output,request_feedback)))
            if task=='ensemble_memory' and (request_feedback or {}).get('repair_contract'):
                output=json.loads(canonical(memory_entries.repaired_snapshot(output,request_feedback)))
            validator(output)
            validated=True
            # New summaries and explicitly corrected old retries share the new
            # size contract; cached paid stages above retain their old validator.
            text_budget=spec.get('memory_character_budget') or (request_feedback or {}).get('summary_text_budget')
            entry_limit=data.get('_memory_snapshot_max_entries',spec.get('memory_snapshot_max_entries'))
            if task=='ensemble_memory' and (text_budget or entry_limit) and '_tool_message' not in output:
                options={'entry_limit':entry_limit} if entry_limit is not None else {}
                memory_entries.validate_snapshot(output['entries'],text_budget=text_budget,**options)
        except urllib.error.HTTPError as exc:
            error=f"http_{exc.code}"
            try:retry_after=min(30,max(0,float(exc.headers.get('Retry-After',0))))
            except (ValueError,TypeError,AttributeError):pass
        except (urllib.error.URLError,TimeoutError,OSError) as exc:
            error="connection_failed"
            reason=exc.reason if isinstance(exc,urllib.error.URLError) else exc
            # Record category/errno only, never URLs, headers, keys or provider text.
            diagnostic=f'{type(exc).__name__}: {type(reason).__name__}; errno={getattr(reason,"errno",None)}'
        except StoreError as exc:error=exc.code
        except (memory_entries.CapacityError, memory_entries.EntrySourcesError, memory_entries.CheckpointError) as exc:
            validation_error=exc
            error="invalid_model_output";diagnostic=f"ValueError: {exc}"
            if capacity_feedback:
                feedback=exc.feedback
                summary_budget=spec.get('memory_character_budget') or (request_feedback or {}).get('summary_text_budget')
                if task=='ensemble_memory' and summary_budget:
                    feedback['summary_text_budget']=summary_budget
                if (task=='ensemble_memory' and isinstance(exc,memory_entries.CapacityError)
                        and feedback.get('summary_text_budget') and isinstance(output,dict)):
                    # One rejected draft, never a chain of drafts or accepted knowledge.
                    # The next bounded retry can actually shorten what was rejected.
                    feedback['rejected_snapshot']=deepcopy(output['entries'])
                    if validated:
                        feedback.update(validated_draft=True,processed_through=output['processed_through'])
        except (ValueError,KeyError,TypeError,IndexError,AttributeError) as exc:
            validation_error=exc
            error="invalid_model_output";diagnostic=f"{type(exc).__name__}: {exc}"
            if spec.get('context_economy') and hasattr(exc,'feedback'):feedback=exc.feedback
            if (spec.get('memory_token_budget') and task=='ensemble_memory' and isinstance(response,dict)
                    and isinstance(response.get('choices'),list) and response['choices']
                    and isinstance(response['choices'][0],dict) and response['choices'][0].get('finish_reason')=='length'):
                failures=(request_feedback or {}).get('length_failures',0)+1
                feedback=memory_rewrite_feedback(payload['max_tokens'],failures)
            if event_feedback:
                from .role_events import EventDecisionError
                if isinstance(exc,EventDecisionError):
                    feedback=exc.feedback
                    if (request_feedback or {}).get('event_context_repair')==1:feedback['event_context_repair']=1
            if position_feedback:
                from .ensemble_position_review import PositionReviewError
                if isinstance(exc,PositionReviewError):feedback=exc.feedback
            legacy_thinking_length=(spec.get('thinking',{}).get('type')=='enabled'
                and isinstance(response,dict) and isinstance(response.get('choices'),list)
                and response['choices'] and isinstance(response['choices'][0],dict)
                and response['choices'][0].get('finish_reason')=='length')
            if feedback is None and task.startswith('ensemble_') and not legacy_thinking_length:
                from . import output_contracts
                feedback=getattr(exc,'feedback',None) or output_contracts.feedback(task,exc)
        except Exception:error="unexpected_failure"
        if validation_error is not None and role_recovery.enabled(task,spec):
            feedback=role_recovery.failure(validation_error,feedback,request_feedback,output,response)
        with self.store.transaction() as con:
            con.execute("UPDATE ai_calls SET status=?,latency_ms=?,usage=?,cost_upper_usd=?,result=?,error=?,response=?,diagnostic=?,validation_feedback=? WHERE id=?",
                         ("failed" if error else "completed",round((time.monotonic()-start)*1000),canonical(usage),cost,canonical(output) if output is not None else None,error,canonical(response) if response is not None else None,diagnostic,canonical(feedback) if feedback else None,call_id))
        if error:
            exc=StoreError(error_message(error)+'。这一步尚未保存，已有进展保留。',503,error)
            exc.retry_after=retry_after
            raise exc
        return output,call_id

    def trace(self,owner,game_id):
        with self.store.transaction(False) as con:
            state=self.store.load(con,owner,game_id)
            calls=[dict(row) for row in con.execute("SELECT id,task,actor,model,status,latency_ms,usage,cost_upper_usd,reserved_cost_usd,error FROM ai_calls WHERE game_id=? ORDER BY started",(game_id,)).fetchall()]
            operation=con.execute("SELECT id,status,retry_state FROM ai_operations WHERE game_id=? ORDER BY started DESC LIMIT 1",(game_id,)).fetchone()
        for c in calls:c["usage"]=json.loads(c["usage"]) if c["usage"] else None
        accounted=sum(c['cost_upper_usd'] if c['cost_upper_usd'] is not None else c['reserved_cost_usd'] if c['reserved_cost_usd'] is not None else .015 for c in calls)
        budget=state.get('watch',{}).get('budget_usd',.25)
        return {"model":self.client.settings.model,"calls":calls,"limit":state.get('watch',{}).get('call_limit',128),"cost_upper_usd":sum(c["cost_upper_usd"] or 0 for c in calls),
                'accounted_cost_usd':accounted,'budget_usd':budget,'remaining_usd':max(0,budget-accounted),
                'budget_warning':accounted>=budget*.8,'reserved_cost_usd':sum(c['reserved_cost_usd'] or .015 for c in calls if c['cost_upper_usd'] is None),
                "unknown_usage":any(c["usage"] is None for c in calls),"operation_status":operation["status"] if operation else None,
                "operation_id":operation["id"] if operation else None,
                'retry_progress':next(({'retry':v.get('attempts',0),'maximum':3} for v in json.loads(operation['retry_state']).values() if v.get('next_at') and operation['status']=='pending'),None) if operation else None}
