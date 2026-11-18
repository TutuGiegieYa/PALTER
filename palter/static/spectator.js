/* A spectator controls playback, never a character. This data never becomes role input. */
let watchPane='all',watchGame=null;
const watchReasons={waiting_stalled:'角色已轮流重新决策，但仍无进展，已暂停',waiting:'所有角色都在等待，目前没有可推进的事件',manual:'已暂停',step:'单步已完成',disconnected:'观看连接已离开，自动暂停',stagnation:'连续多次决策没有实质进展，已暂停',budget:'剩余预算不足，已暂停',call_limit:'已达到本局调用次数上限',error:'本步骤遇到错误，已暂停'};
function watchWaitDetails(s){
  if(!s)return '';
  const remaining=s.waiting&&s.remaining_seconds!==undefined?`<p class="tiny muted">等待时限：剩余 ${escapeHTML(s.remaining_seconds)} 秒游戏活动时间；暂停期间不计时。</p>`:'';
  const result=s.last_result?`<p class="tiny muted">上次等待${s.last_result.status==='timed_out'?'超时':'提前结束'}：${escapeHTML(s.last_result.reason)}</p>`:'';
  return remaining+result;
}
function watchTranscript(rows,key,who){
  const h=escapeHTML;
  return `<section class="panel"><h2>${key==='all'?'全局交流与动态':'这个角色实际获得的信息'}</h2><div class="watch-timeline" data-scroll-key="watch-talk-${key}" data-scroll-follow>${rows.filter(o=>!(o.kind==='cue'&&o.utterance_event_id)).map(o=>`<article class="case-utterance"><strong>${h(o.speaker_name||'现场')}</strong>${o.channel?`<span class="tiny muted"> · ${o.channel==='public'?'公开':'私聊'+(o.recipients?' · '+o.recipients.map(who).join('、'):'')}</span>`:''}<p>${h(o.text)}</p>${enCues(o)}${key==='all'&&o.details?.length?`<details id="watch-receipts-${h(o.event_id)}"><summary>材料与回执（${o.details.length}）</summary>${o.details.map(d=>`<div class="evidence-card"><strong>${h(d.title)}</strong><p class="tiny muted">${h(d.recipients.map(who).join('、'))}收到的原文</p><p>${h(d.text)}</p></div>`).join('')}</details>`:''}</article>`).join('')||'<p class="muted">尚未开始，角色还没有新的行动。</p>'}</div></section>`;
}
function renderSpectator(locked){
  if(watchGame!==view.id){watchGame=view.id;watchPane='all';}
  const expanded=new Set([...app.querySelectorAll('details[open]')].map(n=>n.id));
  const h=escapeHTML,w=view.watch,trace=view.ai_trace,ended=view.phase==='ended',off=locked||view.archived;
  const button=(label,action,disabled=false)=>`<button class="button quiet" data-watch="${action}" ${disabled?'disabled':''}>${h(label)}</button>`;
  const who=a=>view.cast.find(c=>c.id===a)?.name||a;
  const holder=a=>view.truth?.rooms[a]?.name||who(a)||'未记录';
  const condition=value=>({intact:'完好',destroyed:'已毁损'}[value]||'未记录');
  const reason=watchReasons[w.pause_reason]||(view.phase==='reading'?'剧本已准备，等待开始':view.phase==='active'?'正在自主推进':'准备故事');
  document.querySelector('footer span:last-child').textContent='观海 · 四位 AI 自主行动 · 旁观不介入故事';
  let html=`<div class="case-heading"><div><div class="eyebrow">PALTER / 观海</div><h1>${h(view.title)}</h1><p>上帝视角 · 四位 AI · 你不占用角色席位</p></div><p role="status">${ended?'故事已结束':h(reason)}</p></div>`;
  html+=`<section class="panel watch-controls"><div class="dialogue-row">${view.phase==='introduction'?button('确认故事，准备观海','confirm',off||view.ai_busy):''}${['reading','paused'].includes(view.phase)?button(view.background_error?'恢复这一步':'开始 / 继续','watch_resume',(view.background_error?busy||view.archived||view.ai_busy:off)||view.background_error?.retryable===false):''}${view.phase==='active'?button('暂停','watch_pause',controlBusy||view.archived):''}${['reading','paused'].includes(view.phase)?button('单步推进','watch_step',off||view.background_error?.retryable===false):''}${!ended?button(w.speed==='fast'?'切为正常速度':'切为快速播放','watch_speed',off):''}</div><p class="tiny muted">已推进 ${w.steps} 步 · 模型调用 ${trace.calls.length} / ${trace.limit} 次 · ${w.speed==='fast'?'快速':'正常'}播放</p><p>用量费用估算 <strong>$${trace.cost_upper_usd.toFixed(4)}</strong> / 本局预算 <strong>$${trace.budget_usd.toFixed(2)}</strong> · 可用余额 $${trace.remaining_usd.toFixed(4)}<span class="watch-reserve${trace.reserved_cost_usd?'':' is-idle'}"${trace.reserved_cost_usd?'':' aria-hidden="true"'}>在途或未知用量预留 $${(trace.reserved_cost_usd||0).toFixed(4)}</span></p><progress class="watch-budget" max="${trace.budget_usd}" value="${Math.min(trace.budget_usd,trace.accounted_cost_usd)}" aria-label="本局预算使用情况"></progress>${trace.budget_warning?'<p class="required">已达到预算的 80%，余额不足以预留下一次调用时会暂停。</p>':''}${!ended?`<div class="dialogue-row">${button('增加 $0.05 预算','watch_add_budget',off)}${button('增加 64 次调用','watch_add_calls',off)}</div>`:''}<p class="tiny muted">预算包含开局、游玩、结案和重试。费用预算与调用次数分别追加；追加不会自动继续。</p>${processingStatus(trace.retry_progress ? `模型暂未成功，正在自动重试 ${trace.retry_progress.retry} / 3。可以继续阅读或暂停。` : '正在处理一个步骤，完成前可以继续阅读或暂停。',view.ai_busy)}${view.background_error?`<p class="required">${h(view.background_error.message)}</p>${view.phase==='introduction'?button('再次尝试（最多自动重试 3 次）','retry_ai',busy||view.archived||view.ai_busy||view.background_error.retryable===false):''}${button('取消这个未完成步骤','cancel_pending',busy||view.archived||view.ai_busy)}`:''}</section>`;
  if(view.phase==='introduction')html+=`<section class="panel"><p>${h(view.introduction)}</p><p class="tiny muted">确认后生成固定的真相和角色剧本；点击开始才会推进故事。</p></section>`;
  if(view.truth){
    html+=`<nav class="watch-tabs" aria-label="观海视角"><button class="button quiet" data-watch-pane="all" aria-pressed="${watchPane==='all'}">全局动态</button>${view.cast.map(c=>`<button class="button quiet" data-watch-pane="${c.id}" aria-pressed="${watchPane===c.id}">${h(c.name)}</button>`).join('')}<button class="button quiet" data-watch-pane="truth" aria-pressed="${watchPane==='truth'}">固定真相</button></nav>`;
    const transcript=(rows,key)=>watchTranscript(rows,key,who);
    if(watchPane==='all'){
      html+=`<div class="watch-role-grid">${view.cast.map(c=>{const r=view.roles[c.id];return `<section class="panel"><h3>${h(c.name)}</h3><p>${h(r.location)} · ${r.submitted?'已锁定结论':r.scheduling?.waiting?'等待事件':r.activity?'正在行动':'可行动'}</p>${r.scheduling?.waiting?`<p class="tiny muted">等待：${h(r.scheduling.events.join('；')||'直接联系或与我有关的结果')} · 待整理进记忆 ${r.scheduling.unread} 条记录</p><p class="tiny muted">记录数包含本轮自己的行动，不表示等待条件已满足；收到符合条件的新信息才会继续。</p>`:''}${watchWaitDetails(r.scheduling)}<p class="tiny muted">已获得 ${r.evidence.length} 份材料 · ${w.turns[c.id]} 次决策</p><button class="button quiet" data-watch-pane="${c.id}">查看角色视角</button></section>`;}).join('')}</div>`;
      if(view.closure)html+=`<p class="tiny muted">结案意愿：${view.closure.votes.map(who).join('、')||'尚无人提出'} · ${view.closure.ready?'已达成约定，等待各自提交':'三人同意后进入独立提交'}</p>`;
      html+=transcript(view.timeline,'all');
    }else if(watchPane==='truth'){
      html+=`<section class="panel"><h2>开局已确定的真实经过</h2><p>${h(view.truth.solution.reconstruction||'以下记录和目标构成本局的固定事实。')}</p>${view.truth.history.map(e=>`<p><strong>${h(e.time)}</strong> ${h(e.text)}</p>`).join('')}<details id="watch-truth-evidence"><summary>全部材料与当前保管状态</summary>${view.truth.evidence.map(c=>`<article class="evidence-card"><strong>${h(c.title)}</strong><p>${h(c.observation)}</p><p class="tiny muted">保管：${h(holder(view.truth.objects[c.id]?.holder))} · ${h(condition(view.truth.objects[c.id]?.condition))}</p>${evidenceSharingOverview(view.truth.evidence_sharing?.[c.id],who,c.id)}</article>`).join('')}</details></section>`;
    }else{
      const r=view.roles[watchPane];
      const eventStatus={pending:'待确认',active:'进行中',completed:'条件达成',cancelled:'提前结束',rejected:'未成立'};
      const trackers=r.tracked_events?[...r.tracked_events.active,...r.tracked_events.recent_results]:[];
      const tracking=trackers.length?`<details id="watch-tracking-${watchPane}"><summary>关注事件（${trackers.length}）</summary>${trackers.map(e=>`<article class="evidence-card"><strong>${h(e.description)}</strong><p class="tiny muted">${h(eventStatus[e.status]||e.status)}</p><p>等待条件：${h(e.completion_condition)}</p>${e.early_end_condition?`<p>可提前结束：${h(e.early_end_condition)}</p>`:''}${e.progress?`<p>已知进展：${h(e.progress)}</p>`:''}${e.reason?`<p>${h(e.reason)}</p>`:''}</article>`).join('')}</details>`:'';
      const concealment=r.perspective==='concealment';
      const assessment=concealment?`<h2>局势与应对</h2><p class="tiny muted">根据自己实际获知的信息判断暴露风险，并决定如何回应与行动。</p><h3>当前局势</h3><p>${h(r.strategy?.situation||'尚未评估当前局势。')}</p><h3>应对计划</h3><p>${h(r.strategy?.plan||'尚未制定应对计划。')}</p>${!r.strategy&&r.belief?.explanation?`<details id="watch-legacy-${watchPane}"><summary>历史输出（旧版通用模板）</summary><p>${h(r.belief.explanation)}</p></details>`:''}`:`<h2>${view.scenario==='murder'?'案件推断':'目标与判断'}</h2><p class="tiny muted">这些是该角色自己的理解，可能错误。</p><p>${h(r.belief?.explanation||(view.scenario==='murder'?'尚未形成明确推断。':'尚未形成明确判断。'))}</p>`;
      html+=`<div class="investigation-layout"><div><section class="panel"><h2>${h(r.name)}的剧本与目标</h2>${r.briefing.map(p=>`<p>${h(p)}</p>`).join('')}${r.objectives.map(g=>`<p><strong>${g.id==='primary'?'主要目标':'个人目标'}：</strong>${h(g.text)}</p>`).join('')}</section><section class="panel">${assessment}${explorationMarkup(r.exploration,'watch-exploration-'+watchPane)}${tracking}${r.scheduling?.waiting?`<p class="tiny muted">正在等待：${h(r.scheduling.events.join('；')||'直接联系或与我有关的结果')}。等待期间的新记录会保留。</p>`:''}${watchWaitDetails(r.scheduling)}<h3>个人记忆</h3><p>${h(r.memory.summary)}</p>${r.recent_decisions.length?`<details id="watch-decisions-${watchPane}"><summary>近期实际选择</summary>${r.recent_decisions.map(d=>`<p>${h(d.label)}</p>`).join('')}</details>`:''}<details id="watch-relations-${watchPane}"><summary>关系与态度</summary>${Object.entries(r.relationships).map(([a,x])=>`<p>${h(who(a))}：${h(x.description)} · 信任 ${x.trust.toFixed(1)} · 亲近 ${x.affinity.toFixed(1)}</p>`).join('')}</details></section>${transcript(r.observations,watchPane)}</div><aside class="panel"><h2>已经获得的材料</h2>${r.evidence.map(c=>`<article class="evidence-card"><strong>${h(c.title)}</strong><p>${h(c.observation)}</p>${evidenceOriginMarkup(c,who)}${evidenceSharingMarkup(c.sharing,who)}</article>`).join('')||'<p>尚未取得材料。</p>'}</aside></div>`;
    }
  }
  if(view.ending)html+=`<section class="panel outcome"><h2>${h(view.ending.title)}</h2><p>${h(view.ending.narrative)}</p>${Object.values(view.results.participants).map(r=>`<p><strong>${h(r.name)}</strong> · 主要目标${r.primary?'达成':'未达成'} · 个人目标${r.personal?'达成':'未达成'}</p>`).join('')}${conclusionReviewMarkup(view.results,who)}</section>`;
  app.innerHTML=html+caseTraceMarkup(trace);
  for(const key of expanded){const node=document.getElementById(key);if(node)node.open=true;}
}
app.addEventListener('click',async event=>{
  const b=event.target.closest('button');if(!b||!view?.spectator)return;
  if(b.dataset.watchPane){watchPane=b.dataset.watchPane;render();return;}
  const action=b.dataset.watch;if(!action)return;
  if(action==='watch_pause'){
    if(controlBusy)return;controlBusy=true;
    try{const result=await request(`/api/games/${view.id}/commands`,{command_id:id(),expected_revision:view.revision,kind:action});apply(result.view);tell(result.receipt.message);}catch(e){tell(e.message,true);}finally{controlBusy=false;render();}
    return;
  }
  const extra=action==='watch_speed'?{speed:view.watch.speed==='fast'?'normal':'fast'}:action==='cancel_pending'?{operation_id:view.background_error?.operation_id||view.ai_trace.operation_id}:{};
  await command(action,extra);
});
