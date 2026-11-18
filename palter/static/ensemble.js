/* Four-seat play: drafts remain local; the server owns seats and knowledge. */
let ensembleDraft={game:null,text:'',target:'',selected:[],testimony:[],notes:'',argument:'',suspect:'',choice:'',thought:'',intent:'',forgery:'',reason:'',travelSpeech:''};
const enEsc=escapeHTML;
function enCues(observation){return (observation.cues||[]).map(c=>`<p class="utterance-cue">${enEsc(c.text)}</p>`).join('');}
function evidenceOriginMarkup(record,who){
  const origin=record.acquisition;if(!origin)return '';
  const labels={personal_inspection:'我亲自检查所得',personal_collection:'我收取时查看',personal_copy:'我亲自保存副本',self_authored:'我写成的文书（内容仍是主张）',legacy_unknown:'旧记录未能确认取得方式'};
  const text=origin.method==='presentation'?`由${who(origin.from_actor)}向我出示`:origin.method==='physical_receipt'?`由${who(origin.from_actor)}交给我实物`:labels[origin.method];
  return `<p class="tiny muted evidence-origin">${enEsc(text||labels.legacy_unknown)}</p>`;
}
function explorationMarkup(rooms,id){
  if(!rooms)return '';
  const labels={unvisited:'本轮尚未调查',visited:'已到访，尚未检查',partial:'部分调查',visible_acquired:'所见材料已掌握'};
  return `<details id="${enEsc(id)}" class="exploration"><summary>我的调查进度 · ${rooms.filter(r=>r.status==='unvisited').length} 处尚未调查</summary><p class="tiny muted">只记录自己的实际行动；收到材料或听到口述不会把来源地点标为已调查。已掌握所见材料不代表没有隐藏线索。</p>${rooms.map(r=>`<article class="evidence-card"><strong>${enEsc(r.name)}</strong><p>${labels[r.status]}${r.current?' · 当前所在':''}</p><p class="tiny muted">亲自查看 ${r.personally_checked.length} 份 · 完成搜查 ${r.completed_searches} 次${r.last_observed_beat!==null?` · 最近观察于第 ${r.last_observed_beat} 个时间单位`:''}</p>${r.personally_checked.length?`<p class="tiny">亲自查看：${r.personally_checked.map(c=>enEsc(c.title)).join('、')}</p>`:''}${r.visible_unread_records?.length?`<p class="tiny">${r.snapshot_current?'眼前':'上次所见'}待查：${r.visible_unread_records.map(c=>enEsc(c.title)).join('、')}</p>`:''}${r.no_new_evidence?`<p class="tiny">${r.snapshot_current?'本区域已搜查，当前可发现材料均已读完，暂无新证据可调查。':'上次核查时，本区域已搜查且可发现材料均已读完。'}</p>`:''}${r.revisit_notice?'<p class="tiny">收到材料开放通知，可以返回核查。</p>':''}${!r.snapshot_current&&r.status!=='unvisited'?'<p class="tiny muted">这里显示上次调查记录，当前情况需到场确认。</p>':''}</article>`).join('')}</details>`;
}
function evidenceSharingMarkup(status,who){
  if(!status)return '';
  const names=ids=>ids.map(a=>enEsc(who(a))).join('、');
  const shown=status.shown_to.length?`我已出示给：${names(status.shown_to)}`:status.shown_by_me?(status.recipient_history_complete?'我出示时没有其他接收人':'我曾出示，接收人记录不完整'):'我尚未实际出示';
  const remaining=status.shown_by_me&&status.not_shown_to.length?`<br>${status.recipient_history_complete?'我尚未出示给':'未记录我向这些人出示'}：${names(status.not_shown_to)}（对方可能自行获得）`:'';
  const witnessed=status.witnessed_receivers?.length?`<br>我见证实际出示到达：${names(status.witnessed_receivers)}`:'';
  return `<p class="tiny muted evidence-sharing">${status.spoken_by_me?'我已口头提及 · ':''}${shown}${remaining}${witnessed}</p>`;
}
function evidenceSharingOverview(status,who,id){
  if(!status)return '';
  const names=ids=>ids.map(a=>enEsc(who(a))).join('、')||'暂无';
  const receipt=(r,verb)=>`${enEsc(who(r.actor))}${verb} · ${r.channel==='public'?'公开':r.channel?'私聊':'旧记录未注明频道'} · 接收：${r.recipients_recorded===false?'旧记录不完整':names(r.recipients.filter(a=>a!==r.actor))}`;
  return `<div class="evidence-sharing-overview"><p class="tiny muted">已掌握：${names(status.known_by)}</p><p class="tiny muted">实际出示 ${status.presentations.length} 次 · 口头披露 ${status.disclosures.length} 次</p>${status.presentations.length||status.disclosures.length?`<details id="watch-evidence-sharing-${enEsc(id)}"><summary>查看共享记录</summary>${status.presentations.map(r=>`<p class="tiny">${receipt(r,'出示')}</p>`).join('')}${status.disclosures.map(r=>`<p class="tiny muted">${receipt(r,'口头披露')}</p>`).join('')}</details>`:''}</div>`;
}
function enButton(label,action,disabled=false){return `<button class="button quiet" data-en="${action}" ${disabled?'disabled':''}>${enEsc(label)}</button>`;}
function enBrief(){return view.briefing.map(p=>`<p>${enEsc(p)}</p>`).join('')+(view.objectives||[]).map(g=>`<p><strong>${g.id==='primary'?'主要目标':'个人目标'}：</strong>${enEsc(g.text)}</p>`).join('');}
function renderEnsemble(locked){
  const expanded=[...app.querySelectorAll('details[open]')].map(x=>x.id).filter(Boolean);
  const focused=document.activeElement,focusId=focused?.id,start=focused?.selectionStart,end=focused?.selectionEnd;
  if(ensembleDraft.game!==view.id)ensembleDraft={game:view.id,text:'',target:'',selected:[...(view.notes?.evidence_ids||[])],testimony:[],notes:view.notes?.text||'',argument:'',suspect:'',choice:'',thought:'',intent:'',forgery:'',reason:'',travelSpeech:''};
  const d=ensembleDraft,h=enEsc,off=locked||view.ai_busy||view.archived;
  const cast=view.cast||[],who=a=>cast.find(c=>c.id===a)?.name||a;
  document.querySelector('footer span:last-child').textContent='独立角色 · 共同世界 · 行动与话语决定结果';
  const header=`<div class="case-heading"><div><div class="eyebrow">PALTER / ENSEMBLE</div><h1>${h(view.title)}</h1><p>${view.player_name?'你扮演 '+h(view.player_name)+' · ':''}${view.humans.length} 位真人 · ${4-view.humans.length} 位 AI</p></div></div>`;
  const room=view.join_code?`<p>邀请房间码：<strong class="room-code">${h(view.join_code)}</strong></p><p class="tiny muted">让其他参与者在独立浏览器会话打开本页，点击“加入房间”。</p>`:'';
  const members=`<div class="ensemble-seats">${cast.map(c=>`<span>${h(c.name)} · ${c.human?(view.joined.includes(c.id)?'已加入':'等待真人'):'AI'}</span>`).join('')}</div>`;
  const trace=view.ai_trace?caseTraceMarkup(view.ai_trace):'';
  let html=header;
  html+=processingStatus(view.ai_trace?.retry_progress ? `模型暂未成功，正在自动重试 ${view.ai_trace.retry_progress.retry} / 3。你可以继续阅读或暂停。` : '正在处理这一轮，完成后会显示新进展。你可以继续阅读已获得的材料。',view.ai_busy);
  if(view.background_error)html+=`<section class="panel required"><p>${h(view.background_error.message)}</p>${view.background_error.retryable===false?'<p>这一步已无法继续重试。可以取消这一步，保留此前的进展。</p>':''}${enButton('再次尝试（最多自动重试 3 次）','retry_ai',busy||view.archived||view.ai_busy||view.background_error.retryable===false)}${view.is_host?enButton('取消未完成的后台步骤','cancel_ai',busy||view.archived||view.ai_busy):''}</section>`;
  if(view.phase==='introduction'){
    html+=`<section class="panel phase-card"><p>${h(view.introduction)}</p>${members}${room}${view.is_host?enButton('确认故事','confirm',off):'<p>等待房主确认。</p>'}</section>`;
  }else if(view.phase==='lobby'){
    html+=`<section class="panel phase-card"><h2>等待参与者</h2>${members}${room}${view.is_host?enButton('所有人到齐，准备剧本','prepare',off||view.joined.length!==view.humans.length):'<p>到齐后由房主准备剧本。</p>'}</section>`;
  }else if(view.phase==='opening'){
    html+=`<section class="panel phase-card"><h2>到场之前，你的选择</h2>${enBrief()}<p>这次开场只会产生一位实际凶手。愿意行动的真人优先；没有人愿意时，会分配给 AI，纯真人局则随机分配。</p>${view.opening_submitted?'<p>你的选择已保存，等待其他人。可以在所有人提交前重新选择。</p>':''}<label for="en-volunteer">你的角色是否有杀害目标的意愿？</label><select id="en-volunteer"><option value="no">没有</option><option value="yes">有</option></select><label for="en-handling">如果到场时发现对方已经死亡</label><select id="en-handling"><option value="inspect">观察现场，不触碰</option><option value="leave">立即离开</option><option value="touch">接触并检查身体</option></select>${enButton('提交开场选择','opening',off)}<p class="tiny muted">正式调查前，实际经过和每个人的初始剧本会固定下来。</p></section>`;
  }else if(['reading','paused'].includes(view.phase)){
    html+=`<section class="panel phase-card"><h2>你的角色剧本</h2>${enBrief()}${view.phase==='paused'?enButton('继续游戏','resume',controlBusy||view.archived):view.ready.includes(view.actor)?'<p>你已完成阅读，等待其他人或阅读时间结束。</p>':enButton('阅读完成','ready',off)}<p class="muted tiny">${view.humans.length===1?'阅读不限时。':`多人阅读剩余约 ${Math.max(0,Math.ceil((view.reading_deadline*1000-Date.now())/1000))} 秒；全员准备好可提前开始。`}</p></section>`;
  }else{
    const active=view.phase==='active'&&!view.archived&&!view.submitted;
    const blocked=off||!active;
    const needsReply=view.must_speak||view.must_respond;
    const replyHint=view.must_explain?'请先在“交流与质证”中用话语解释质疑，再继续行动。':view.must_speak?'已连续几次交流没有发言，请先在“交流与质证”中说话，再继续行动。':'有人等你回应，请先在“交流与质证”中说话或作出回应动作。';
    const selected=view.evidence.filter(c=>d.selected.includes(c.id));
    const recipients=cast.filter(c=>c.id!==view.actor&&view.recipients.includes(c.id));
    if(d.target&&!recipients.some(c=>c.id===d.target))d.target='';
    const talk=view.observations.filter(o=>['testimony','gesture'].includes(o.kind));
    const timeline=view.observations.filter(o=>!(o.kind==='cue'&&o.utterance_event_id));
    const history=timeline.filter(o=>!['testimony','gesture','evidence'].includes(o.kind));
    const options=view.options.filter(c=>!c.id.startsWith('move:')&&(!needsReply||c.id==='end_private'||(!view.must_explain&&['accept','decline'].includes(c.id.split(':')[0]))));
    const moves=view.options.filter(c=>c.id.startsWith('move:'));
    const travelSpeech=view.local_communication?`<label for="en-travel-speech">离开前说一句（可选）</label><textarea id="en-travel-speech" maxlength="1200" placeholder="由我决定是否透露去向；留空即静默移动。" ${blocked?'disabled':''}>${h(d.travelSpeech||'')}</textarea><p class="tiny muted">先向当前同一区域的听众发言，再移动。目的地的人听不到这句话。</p>`:'';
    const moveBlocked=blocked||(needsReply&&!(view.local_communication&&d.travelSpeech?.trim()));
    if(!options.some(c=>c.id===d.choice))d.choice=options[0]?.id||'';
    let ending='';
    if(view.ending)ending=`<section class="panel outcome"><h2>${h(view.ending.title)}</h2><p>${h(view.ending.narrative)}</p><div class="trace-table" data-scroll-key="ending-results"><table><thead><tr><th>角色</th><th>主要目标</th><th>个人目标</th><th>完整胜利</th></tr></thead><tbody>${Object.values(view.results.participants).map(r=>`<tr><td>${h(r.name)}</td><td>${r.primary?'达成':'未达成'}</td><td>${r.personal?'达成':'未达成'}</td><td>${r.success?'达成':'未达成'}</td></tr>`).join('')}</tbody></table></div>${conclusionReviewMarkup(view.results,who)}<details id="en-reveal"><summary>真实经过与每个人的目标</summary><p>${h(view.resolution.reconstruction)}</p>${view.history.map(e=>`<p><strong>${h(e.time)}</strong> ${h(e.text)}</p>`).join('')}${Object.values(view.results.participants).map(r=>`<p><strong>${h(r.name)}</strong>：${r.objectives.map(g=>h(g.text)).join('；')}</p>`).join('')}</details>${enButton('开始新故事','new',off)}</section>`;
    const scene=`<section class="panel"><div class="eyebrow">当前现场</div><h2>${h(view.scene.name)}</h2><p>${h(view.scene.description)}</p>${moves.length?travelSpeech:''}<div class="dialogue-row">${moves.map(m=>`<button class="button quiet" data-en-choice="${h(m.id)}" ${moveBlocked?'disabled':''}>${h(m.label)}</button>`).join('')}</div>${view.activity?`<p class="required">你正在进行一项行动，约剩 ${Math.max(0,view.activity.end-view.beat)} 个时间单位；可以选择中止。</p>`:''}${needsReply?`<p class="required">${h(replyHint)}</p>`:''}<label for="en-choice">可以尝试的行动</label><select id="en-choice" ${blocked||!options.length?'disabled':''}>${options.map(c=>`<option value="${h(c.id)}" ${d.choice===c.id?'selected':''}>${h(c.label)}</option>`).join('')}</select>${enButton('执行所选行动','act',blocked||!options.length)}<p>随身物品：${view.own_items.map(h).join('、')||'暂无'}</p>${view.supplies?`<p>公共补给：电池 ${view.supplies.battery} / 补给 ${view.supplies.supply}</p>`:''}</section>`;
    const dialogue=`<section class="panel"><h2>${view.chat?'与 '+h(who(view.chat.participants.find(a=>a!==view.actor)))+' 私聊':'交流与质证'}</h2>${view.local_communication?`<p class="tiny muted">当前听众：${recipients.map(c=>h(c.name)).join('、')||'暂无其他角色'}。只有同一区域且不在其他私聊中的人能收到发言与出示。</p>`:''}${view.chat?`<p class="tiny muted">仅双方收到内容 · ${view.chat.turns.length} / ${view.chat.limit} 条 · 双方均可随时结束</p>${enButton('结束私聊','end_private',blocked)}`:''}${view.must_speak?'<p class="required">这次需要实际说话，解释质疑或参与讨论。</p>':view.must_respond?'<p class="required">有人等你回应，可以说话或作出允许的动作。</p>':''}<div class="recent-talk" data-scroll-key="dialogue" data-scroll-follow>${talk.slice(-6).map(o=>`<article class="case-utterance" data-utterance="${h(o.event_id)}"><strong>${h(o.speaker_name)}</strong><span class="tiny muted"> · ${o.channel==='public'?'公开':'私聊'}</span><p>${h(o.text)}</p>${enCues(o)}${o.speaker!==view.actor?`<button class="button quiet small" data-en-follow="${h(o.id)}">继续追问</button>`:''}</article>`).join('')}</div><label for="en-target">交谈对象</label><select id="en-target"><option value="">按发言内容识别对象</option>${recipients.map(c=>`<option value="${c.id}" ${d.target===c.id?'selected':''}>${h(c.name)}</option>`).join('')}</select><label for="en-text">你想说什么？</label><textarea id="en-text" maxlength="1600">${h(d.text)}</textarea><div class="dialogue-row">${enButton('发送','say',blocked)}${enButton('出示并质证','challenge',blocked||!selected.length)}${enButton('点头','nod',blocked||view.must_speak)}${enButton('摇头','shake',blocked||view.must_speak)}</div><p class="tiny muted">质证后仍可继续调查和追问，不会直接结案。</p></section>`;
    const evidence=`<section class="panel case-notebook" data-scroll-key="notebook"><h2>调查与个人记录</h2><details id="en-script"><summary>重读自己的剧本</summary>${enBrief()}${view.humans.length===1&&active?enButton('暂停阅读','pause',controlBusy||view.archived):'<p class="tiny muted">多人阅读不会暂停其他参与者。</p>'}</details>${explorationMarkup(view.exploration,'en-exploration')}<h3>已获得的材料</h3><p class="tiny muted">勾选后可以出示或引用。原件之后被处理，也不会抹掉你已经看到的内容。</p>${view.evidence.map(c=>`<article class="evidence-card"><label><input type="checkbox" data-en-evidence="${h(c.id)}" ${d.selected.includes(c.id)?'checked':''}> <strong>${h(c.title)}</strong></label><p>${h(c.observation)}</p><span class="tiny muted">${h(c.source)}</span>${evidenceOriginMarkup(c,who)}${evidenceSharingMarkup(c.sharing,who)}</article>`).join('')||'<p>检查现场或向其他人取得材料。</p>'}<details id="en-notes"><summary>我的推理草稿</summary><textarea id="en-notes-text" placeholder="用“我”记录判断、依据和疑点。" maxlength="4000">${h(d.notes)}</textarea>${enButton('保存笔记','notebook',blocked)}${enButton('把我的笔记带入最终论证','use_notes',blocked)}</details><details id="en-memory"><summary>我的记忆与关系</summary><p>${h(view.memory.summary)}</p>${Object.entries(view.relationships).map(([a,r])=>`<p><strong>${h(who(a))}</strong>：${h(r.description)}<br><span class="tiny muted">信任 ${r.trust.toFixed(1)} · 亲近 ${r.affinity.toFixed(1)} · ${h(r.experiences.at(-1)?.reason||'初始关系')}</span></p>`).join('')}<label for="en-relation-target">我对谁改变了看法</label><select id="en-relation-target">${cast.filter(c=>c.id!==view.actor).map(c=>`<option value="${c.id}">${h(c.name)}</option>`).join('')}</select><textarea id="en-reason" maxlength="500" placeholder="例如：我愿意暂时相信对方，因为……">${h(d.reason)}</textarea>${enButton('更信任一些','trust_up',blocked)}${enButton('更怀疑一些','trust_down',blocked)}${enButton('更亲近一些','affinity_up',blocked)}${enButton('更疏远一些','affinity_down',blocked)}</details><details id="en-history"><summary>完整发言与现场动态</summary>${[...timeline].reverse().map(o=>`<div class="history-entry"><p><strong>${h(o.speaker_name||'现场')}</strong>：${h(o.text)}</p>${enCues(o)}</div>`).join('')}</details></section>`;
    const optional=`<section class="panel"><details id="en-thoughts"><summary>私下的想法与行动尝试</summary><label for="en-thought">只记录自己的想法</label><textarea id="en-thought" placeholder="用“我”写下此刻的想法，例如：我还不能确定这份记录是否可信。">${h(d.thought)}</textarea>${enButton('记录想法','thought',blocked)}<label for="en-intent">现在要尝试的行动</label><textarea id="en-intent" placeholder="例如：我现在检查这份材料。">${h(d.intent)}</textarea>${enButton('理解并尝试','intent',blocked||needsReply)}<label for="en-forgery">写一张可能误导他人的文书</label><textarea id="en-forgery" maxlength="1000">${h(d.forgery)}</textarea>${enButton('写成随身文书','forge',blocked||needsReply)}<p class="tiny muted">写成文书只产生一件物品，不会让它描述的事情成为真实历史。</p></details></section>`;
    const final=`<section class="panel"><details id="en-final"><summary>准备最终结论</summary><p>先完成质证和追问，再决定是否结束。所有真人提交后才会揭晓真相。</p>${view.scenario==='murder'?`<label for="en-suspect">最终指认</label><select id="en-suspect"><option value="">暂未查明</option>${cast.map(c=>`<option value="${c.id}" ${d.suspect===c.id?'selected':''}>${h(c.name)}</option>`).join('')}</select><p class="tiny muted">完整论证需要说明人物与机会、时间边界、作案方式及材料之间的联系。</p>`:''}${view.final_dimensions?finalAspectsMarkup(view,d,talk):`<label for="en-argument">我的最终说明</label><textarea id="en-argument" placeholder="用“我”说明判断、依据及仍不确定的地方。" maxlength="4000">${h(d.argument)}</textarea><p>引用：${selected.map(c=>h(c.title)).join('、')||'没有选择材料'}</p><details id="en-testimony"><summary>引用我听到的发言（可选，已选 ${d.testimony.length} 条）</summary><p class="tiny muted">可以引用、质疑或不使用这些话。发言是证言，听到不代表已证实；请说明它与材料的关系。</p><div class="testimony-list" data-scroll-key="final-testimony">${talk.filter(o=>o.kind==='testimony').map(o=>`<label class="history-entry"><input type="checkbox" data-en-testimony="${h(o.id)}" ${d.testimony.includes(o.id)?'checked':''}> <strong>${h(o.speaker_name)}</strong>：${h(o.text)}</label>`).join('')||'<p>还没有听到发言。</p>'}</div></details>`}${enButton('确认提交，等待共同结案','submit',blocked)}</details></section>`;
    html+=ending+(view.submitted&&view.phase!=='ended'?`<section class="panel"><p>你的最终结论已保存，等待其他真人（${view.submitted_count} / ${view.humans.length}）。</p></section>`:'')+`<div class="investigation-layout"><div>${scene}${active?dialogue+optional+final:''}<section class="panel"><h3>最近现场变化</h3>${history.slice(-6).map(o=>`<p>${h(o.text)}</p>`).join('')}</section></div><aside>${evidence}</aside></div>`;
  }
  app.innerHTML=html+trace;
  for(const key of expanded){const node=document.getElementById(key);if(node)node.open=true;}
  if(focusId?.startsWith('en-')){const field=document.getElementById(focusId);field?.focus({preventScroll:true});if(typeof start==='number'&&field?.setSelectionRange)field.setSelectionRange(start,end);}
}
app.addEventListener('input',e=>{
  const fields={'en-text':'text','en-notes-text':'notes','en-argument':'argument','en-thought':'thought','en-intent':'intent','en-forgery':'forgery','en-reason':'reason','en-travel-speech':'travelSpeech'};
  if(fields[e.target.id])ensembleDraft[fields[e.target.id]]=e.target.value;
  if(e.target.dataset.finalAspect&&e.target.dataset.finalField){ensembleDraft.aspects[e.target.dataset.finalAspect][e.target.dataset.finalField]=e.target.value;}
  if(e.target.id==='en-travel-speech')render();
});
app.addEventListener('change',e=>{
  const fields={'en-target':'target','en-suspect':'suspect','en-choice':'choice'};
  if(fields[e.target.id])ensembleDraft[fields[e.target.id]]=e.target.value;
  if(e.target.dataset.finalAspect&&e.target.dataset.finalSource){
    const row=ensembleDraft.aspects[e.target.dataset.finalAspect],key=e.target.dataset.finalSource,id=e.target.value;
    row[key]=e.target.checked?[...new Set([...row[key],id])]:row[key].filter(s=>s!==id);render();
  }
  if(e.target.dataset.enTestimony){const sid=e.target.dataset.enTestimony;ensembleDraft.testimony=e.target.checked?[...new Set([...ensembleDraft.testimony,sid])]:ensembleDraft.testimony.filter(s=>s!==sid);render();}
  if(e.target.dataset.enEvidence){const cid=e.target.dataset.enEvidence;ensembleDraft.selected=e.target.checked?[...new Set([...ensembleDraft.selected,cid])]:ensembleDraft.selected.filter(c=>c!==cid);render();}
});
app.addEventListener('click',async e=>{
  if(view?.gameplay!=='ensemble')return;
  const button=e.target.closest('button');if(!button)return;
  const action=button.dataset.en,d=ensembleDraft;
  if(button.dataset.enFollow){const o=view.observations.find(o=>o.id===button.dataset.enFollow);d.target=o.speaker;d.text='你刚才说“'+o.text+'”。请解释依据和当时的情况。';render();return;}
  if(action==='use_notes'){d.argument=d.notes;render();return;}
  if(['pause','resume'].includes(action))return void aiControl(action);
  if(busy||(hasPending()&&!['retry_ai','cancel_ai'].includes(action))||view.ai_busy)return;
  if(button.dataset.enChoice){
    const choice=button.dataset.enChoice,extra={choice};
    if(view.local_communication&&choice.startsWith('move:'))extra.text=d.travelSpeech||'';
    const result=await command('act',extra);
    if(result?.receipt?.accepted&&choice.startsWith('move:')){d.travelSpeech='';render();}
    return;
  }
  if(!action)return;
  if(action==='new')return void newGame();
  let kind=action,extra={channel:view.chat?.id||'public'};
  if(['say','challenge'].includes(action)){extra.text=d.text;if(d.target)extra.target=d.target;}
  if(['challenge','notebook','submit'].includes(action))extra.evidence_ids=d.selected;
  if(action==='act'){extra.choice=d.choice;if(view.local_communication&&d.choice.startsWith('move:'))extra.text=d.travelSpeech||'';}
  if(action==='opening'){extra={volunteer:document.querySelector('#en-volunteer').value==='yes',handling:document.querySelector('#en-handling').value};}
  if(action==='notebook')extra.text=d.notes;
  if(action==='thought')extra.text=d.thought;
  if(action==='intent')extra.text=d.intent;
  if(action==='forge')extra.text=d.forgery;
  if(action==='end_private'){kind='act';extra.choice='end_private';}
  if(['nod','shake'].includes(action)){kind='gesture';extra.text=action==='nod'?'点头':'摇头';}
  if(['trust_up','trust_down','affinity_up','affinity_down'].includes(action)){kind='attitude';extra.target=document.querySelector('#en-relation-target').value;extra.trust=action==='trust_up'?.2:action==='trust_down'?-.2:0;extra.affinity=action==='affinity_up'?.2:action==='affinity_down'?-.2:0;extra.text=d.reason;}
  if(action==='submit'){
    if(!confirm('提交后不能继续行动；所有真人提交后会结束故事并揭晓结果。确定吗？'))return;
    extra.text=d.argument;extra.suspect=d.suspect;extra.testimony_ids=d.testimony;
    if(view.final_dimensions){extra.aspects=view.final_dimensions.map(aspect=>({aspect,...d.aspects[aspect]}));extra.evidence_ids=[];extra.testimony_ids=[];}
  }
  if(action==='cancel_ai'){kind='cancel_pending';extra.operation_id=view.background_error.operation_id;}
  const result=await command(kind,extra);
  if(result?.receipt?.accepted&&['say','challenge'].includes(action)){d.text='';render();}
  if(result?.receipt?.accepted&&action==='act'&&extra.choice.startsWith('move:')){d.travelSpeech='';render();}
});
document.querySelector('#join-game')?.addEventListener('click',async()=>{
  if(busy||hasPending())return;
  const code=prompt('输入房主提供的房间码');if(!code)return;
  await post('/api/join',{code:code.trim(),command_id:id()});
});
setInterval(async()=>{
  if(runtimeGameplay!=='ensemble'||busy||!view||view.gameplay!=='ensemble'||view.phase==='ended'||view.archived)return;
  try{const result=await request(`/api/games/${view.id}`);apply(result.view);}catch{}
},1500);
/* The score is already merged by runtime. Process observations never add credit. */
function finalAspectsMarkup(v,d,talk){
  const h=enEsc,labels={identity:'人物与机会',time:'时间边界',method:'作案手法'};
  d.aspects??={};
  return (d.argument?`<details id="en-final-draft"><summary>带入的推理草稿</summary><p>${h(d.argument)}</p></details>`:'')+`<p class="tiny muted">分别写下判断并选择这一项使用的依据；不足之处可以直接说明。</p>`+v.final_dimensions.map(aspect=>{
    const row=d.aspects[aspect]??={explanation:'',gaps:'',evidence_ids:[],testimony_ids:[]};
    return `<fieldset><legend>${h(labels[aspect]||aspect)}</legend><label for="en-final-${aspect}">我的说明</label><textarea id="en-final-${aspect}" data-final-aspect="${aspect}" data-final-field="explanation" maxlength="1200">${h(row.explanation)}</textarea><label for="en-gap-${aspect}">尚未解决的疑点（可选）</label><textarea id="en-gap-${aspect}" data-final-aspect="${aspect}" data-final-field="gaps" maxlength="400">${h(row.gaps)}</textarea><details id="en-final-sources-${aspect}"><summary>引用材料（已选 ${row.evidence_ids.length} 份）</summary>${v.evidence.map(c=>`<label class="history-entry"><input type="checkbox" data-final-aspect="${aspect}" data-final-source="evidence_ids" value="${h(c.id)}" ${row.evidence_ids.includes(c.id)?'checked':''}>${h(c.title)}</label>`).join('')||'<p>暂无已取得材料。</p>'}</details><details id="en-final-heard-${aspect}"><summary>引用听到的发言（已选 ${row.testimony_ids.length} 条）</summary><p class="tiny muted">发言保留说话者归属，听到不等于已经证实。</p><div class="testimony-list" data-scroll-key="final-heard-${aspect}">${talk.filter(o=>o.kind==='testimony').map(o=>`<label class="history-entry"><input type="checkbox" data-final-aspect="${aspect}" data-final-source="testimony_ids" value="${h(o.id)}" ${row.testimony_ids.includes(o.id)?'checked':''}>${h(o.speaker_name)}：${h(o.text)}</label>`).join('')||'<p>还没有听到发言。</p>'}</div></details></fieldset>`;
  }).join('');
}

function concealmentReviewMarkup(actor,p,who){
  const h=escapeHTML,r=p.reasoning,process=r.process,admission=r.assessment_type==='admission'||(r.submission?.suspect===actor);
  const assessment=r.position_assessment,submission=r.submission;
  const sources=[...(r.comparison_sources||[]),...(r.sources||[])];
  const sourceName=id=>sources.find(s=>s.id===id)?.title||(r.testimony?.some(t=>t.id===id)?'已引用发言':'已引用材料');
  const status=process?(process.truth_established?'真实经过已被证据支持':'尚未形成完整定案'):'已结算';
  const position=submission?`<h4>最终对外立场</h4><p>${submission.suspect===actor?'明确选择了自我指认。':submission.suspect?`最终指认：${h(who(submission.suspect))}。`:'未明确指认任何人。'}</p>${submission.explanation?`<blockquote>${h(submission.explanation)}</blockquote>`:'<p class="muted">没有提交最终说明。</p>'}`:'<p class="muted">旧版记录未保存独立的最终说明，保留原有结算结果。</p>';
  const exposure=r.exposure?.established_by?.length?`<p>形成完整定案的提交：${r.exposure.established_by.map(s=>h(s.name)+(s.self_submission?'（本人供述）':'')).join('、')}。</p>`:'';
  let detail='';
  if(admission&&r.aspects){
    const labels={identity:'责任与实施关联',time:'供述中的时间',method:'供述中的作案方式'};
    detail=`<h4>供述与证据核对</h4><p class="tiny muted">主动认罪是允许的选择；认罪本身不自动补齐证据。以下核对实际提交的供述。</p>`+Object.entries(labels).map(([key,label])=>{
      const a=r.aspects[key];if(!a)return '';
      return `<article class="ending-aspect"><h4>${label} · ${a.evaluated?(a.established?'有充分支持':'支持尚不完整'):'未评估'}</h4><p>${h(a.reason)}</p>${a.evaluated?`<p>供述论述：${a.semantic_supported?'支持':'未获支持'}；证据覆盖：${a.proof_covered?'完整':'不足'}。</p>`:''}${a.matched_evidence_ids?.length?`<p class="tiny muted">使用的相关材料：${a.matched_evidence_ids.map(id=>h(sourceName(id))).join('、')}。</p>`:''}</article>`;
    }).join('');
  }else if(assessment){
    const labels={consistent:'与所列材料相符',contradicted:'与所列材料冲突',unresolved:'现有依据无法确定'};
    detail=`<h4>立场与结案证据</h4><p>${h(assessment.position_summary)}</p><p class="tiny muted">这是结案后的材料对照，不表示角色当时见过所有材料，也不据此推断其他人是否相信了这些话。</p>`+assessment.evidence_checks.map(c=>`<article class="ending-position-check"><h4>${h(labels[c.status]||'材料对照')}</h4><blockquote>${h(c.statement)}</blockquote><p>${h(c.reason)}</p>${c.source_ids.length?`<p class="tiny muted">对照依据：${c.source_ids.map(id=>h(sourceName(id))).join('、')}。</p>`:''}</article>`).join('');
  }else{
    detail=`<p class="muted">${r.review_version===2?'没有可供评估的最终说明。':'旧版结案未记录独立的立场点评；保留原有目标结果，不重新评分。'}</p>`;
  }
  const ownSources=r.sources||[],testimony=r.testimony||[];
  const comparisons=(r.comparison_sources||[]).filter(s=>!ownSources.some(o=>o.id===s.id));
  const materials=(ownSources.length||testimony.length||comparisons.length)?`<details id="ending-sources-${h(actor)}"><summary>提交材料与结案对照</summary>${ownSources.map(s=>`<article class="evidence-card"><strong>${h(s.title)}</strong><p>${h(s.observation)}</p></article>`).join('')}${testimony.map(t=>`<p>${h(t.speaker_name||who(t.speaker))}：${h(t.text)}<span class="tiny muted">（引用的发言，未自动当作独立验证）</span></p>`).join('')}${comparisons.length?'<h4>其他提交使用的材料（结案后对照）</h4>':''}${comparisons.map(s=>`<article class="evidence-card"><strong>${h(s.title)}</strong><p>${h(s.observation)}</p></article>`).join('')}</details>`:'';
  return `<details class="ending-role-review" id="ending-review-${h(actor)}"><summary>${h(p.name)} · 对外立场与目标 · ${h(status)}</summary><p><strong>主要目标${p.primary?'达成':'未达成'}：</strong>${h(process?.primary_reason||'按本局保存的目标结果结算。')}</p><p><strong>个人目标${p.personal?'达成':'未达成'}：</strong>${h(process?.personal_reason||'按本局保存的目标结果结算。')}</p>${exposure}${position}${detail}${materials}${process?`<h4>参与记录（不额外计分）</h4><p>已掌握 ${process.known_records} 份材料，有 ${process.directed_utterances} 次定向发言。</p>`:''}</details>`;
}

function conclusionReviewMarkup(results,who){
  if(!results?.participants)return '';
  const h=escapeHTML,labels={identity:'人物与机会',time:'作案时间',method:'作案方式'};
  const verdicts={established:'论证成立',unproven:'指认正确，论证未完整成立',incorrect:'指认与真相不符',unresolved:'未作明确指认'};
  const gaps={not_acquired:'尚未取得的支持材料（结案后对照）',not_cited:'已掌握，但最终没有引用',not_used:'已选择，但最终论述没有使用'};
  const rows=Object.entries(results.participants).filter(([,r])=>r.reasoning?.result);
  if(!rows.length)return '';
  const closure=results.scoring_version===2&&results.admission_established&&!results.investigation_success
    ?'凶手的供述已有证据支持；非凶手玩家的评测按各自提交独立保留。'
    :results.shared_success?'已有完整论证支持定案。':'本局尚无完整论证支持定案。';
  return `<div class="conclusion-review"><h3>结案点评</h3><p>${closure}</p>${rows.map(([actor,p])=>{
    const r=p.reasoning,conceal=r.perspective==='concealment'||p.objectives?.some(o=>o.kind==='avoid'),process=r.process;
    if(conceal)return concealmentReviewMarkup(actor,p,who);
    const heading='调查与论证';
    const status=verdicts[r.result]||'已结算';
    if(!r.review_version)return `<details id="ending-review-${h(actor)}"><summary>${h(p.name)} · ${h(verdicts[r.result]||'已结算')}</summary><p class="tiny muted">这是旧版结算，未保存详细点评。保留原始结果，不重新评分。</p>${r.established?.length?`<p>原始记录中成立的部分：${r.established.map(a=>h(labels[a]||a)).join('、')}。</p>`:''}</details>`;
    const sourceName=id=>r.sources.find(s=>s.id===id)?.title||(r.testimony.some(t=>t.id===id)?'已引用发言':'已引用材料');
    return `<details class="ending-role-review" id="ending-review-${h(actor)}"><summary>${h(p.name)} · ${heading} · ${h(status)}</summary><p><strong>主要目标${p.primary?'达成':'未达成'}：</strong>${h(process.primary_reason)}</p><p><strong>个人目标${p.personal?'达成':'未达成'}：</strong>${h(process.personal_reason)}</p><h4>实际提交的结论</h4><p>指认：${h(r.suspect?who(r.suspect):'暂未明确指认')}。${r.accusation_correct===null?'':r.accusation_correct?'与固定真相一致。':'与固定真相不符。'}</p>${r.submission.explanation?`<blockquote>${h(r.submission.explanation)}</blockquote>`:'<p class="muted">没有提交最终说明。</p>'}<h4>最终论证判定</h4><p class="tiny muted">分别核对论述与证据覆盖，两者均通过才成立。以下只评估实际提交的内容。</p>${Object.entries(labels).map(([aspect,label])=>{const a=r.aspects[aspect];if(!a.evaluated)return `<article class="ending-aspect"><h4>${label} · 未评估</h4><p>${h(a.reason)}</p></article>`;return `<article class="ending-aspect"><h4>${label} · ${a.established?'成立':'未成立'}</h4><p>论述：${a.semantic_supported?'支持':'未获支持'}；证据覆盖：${a.proof_covered?'完整':'不足'}。</p><p>${h(a.reason)}</p>${a.identity_matches===false?'<p>所指认的人与固定真相不符，人物链不能成立。</p>':''}${a.matched_evidence_ids.length?`<p class="tiny muted">论证中使用的相关材料：${a.matched_evidence_ids.map(id=>h(sourceName(id))).join('、')}。</p>`:''}${a.gaps.length?`<p class="tiny muted">以下是一条可行证据链的缺口；等价材料任选其一即可：</p><ul>${a.gaps.map(g=>`<li>${h(gaps[g.status])}：${g.alternatives.map(s=>h(s.title)).join(' / ')}。</li>`).join('')}</ul>`:''}</article>`;}).join('')}<details id="ending-sources-${h(actor)}"><summary>本次引用的原始材料与发言</summary>${r.sources.map(s=>`<article class="evidence-card"><strong>${h(s.title)}</strong><p>${h(s.observation)}</p><p class="tiny muted">${h(s.source||'')}</p></article>`).join('')}${r.testimony.map(t=>`<p>${h(t.speaker_name||who(t.speaker))}：${h(t.text)}<span class="tiny muted">（听到的发言，未自动当作独立验证）</span></p>`).join('')}${!r.sources.length&&!r.testimony.length?'<p>没有引用材料或发言。</p>':''}</details><h4>过程回顾（不参与结案评分）</h4><p>已掌握 ${process.known_records} 份材料，其中亲自检查或取得 ${process.personally_acquired} 份、由他人交付或出示 ${process.received_records} 份；有 ${process.directed_utterances} 次定向发言。</p><p>记入贡献的关键材料：${process.contributed_records.map(s=>h(s.title)).join('、')||'暂无'}。</p>${process.unvisited_rooms.length?`<p>未亲自到访：${process.unvisited_rooms.map(r=>h(r.name)).join('、')}。这是尚未走过的调查方向，不表示当时已知其中藏有什么，也不会直接扣分。</p>`:''}</details>`;
  }).join('')}</div>`;
}
