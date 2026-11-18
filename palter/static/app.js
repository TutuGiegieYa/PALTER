"use strict";
let view = null, csrf = "", activeGame = null, busy = false;
let selectedAction = "move", selectedTarget = "";
let runtimeMode="offline", runtimeGameplay=null, controlBusy=false, speechDraft="", thoughtDraft="", intentDraft="", addressee="";
let privateInputOpen=false, traceOpen=false, inviteTarget="B";
let renderedGame=null;
const app = document.querySelector("#app"), notice = document.querySelector("#notice");
const symbols = {move:"↗", inspect:"⌕", take:"◇", place:"▣", follow:"↝", wait:"◷"};
const names = {hall:"大厅", study:"书房", courtyard:"庭院"};
const escapeHTML = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const id = () => typeof crypto.randomUUID==='function'?crypto.randomUUID():Array.from(crypto.getRandomValues(new Uint8Array(16)),n=>n.toString(16).padStart(2,'0')).join('');
function tell(text, error=false){ notice.textContent=text; notice.classList.toggle("error",error); }
function processingStatus(text, active){
  // Keep the exact wrapped text in layout even between calls; display:none
  // would move every panel below this message on each polling transition.
  return `<p class="processing-status${active?'':' is-idle'}" role="status"${active?'':' aria-hidden="true"'}>${escapeHTML(text)}</p>`;
}
async function request(path, body){
  // Setup can need four provider attempts; polling still reports live progress.
  const timeout=body?600000:180000;
  const controller = new AbortController(), timer = setTimeout(()=>controller.abort(), timeout);
  try {
    const result = await fetch(path,{method:body?"POST":"GET",headers:body?{"Content-Type":"application/json","X-Palter-CSRF":csrf}:{},body:body?JSON.stringify(body):undefined,signal:controller.signal});
    const data = await result.json();
    if(!result.ok){ const error=new Error(data.error?.message||"请求未完成"); error.status=result.status; throw error; }
    return data;
  } finally { clearTimeout(timer); }
}
function apply(next){
  if(view && next.id===view.id && next.revision<view.revision) return;
  // Busy/call status can change without a revision; compare the complete view.
  // Multiplayer reading still renders its wall-clock countdown.
  if(view && next.phase!=="reading" && JSON.stringify(next)===JSON.stringify(view))return;
  view=next; if(view.mode==="ai")document.title="PALTER · "+view.title; render();
}
function hasPending(){return !!localStorage.getItem("palter.pending");}
function updateBusy(){
  const blocked=busy||hasPending();
  document.querySelector("#new-game").disabled=blocked;
  document.querySelector("#history").disabled=blocked;
  document.querySelector("#recovery").hidden=!hasPending();
  document.querySelector("#retry").disabled=busy;
  document.querySelector("#discard").hidden=runtimeMode!=="ai";
  document.querySelector("#discard").disabled=busy;
  document.querySelector("#category").hidden=runtimeMode!=="ai";
  document.querySelector(".category-label").hidden=runtimeMode!=="ai";
}
async function post(path, body){
  if(busy) return;
  if(hasPending()){
    try {
      const pending=JSON.parse(localStorage.getItem("palter.pending"));
      const recovery=view?.gameplay==='ensemble' && view.background_error && path===`/api/games/${view.id}/commands` &&
        ['retry_ai','cancel_pending','watch_resume','watch_step'].includes(body?.kind);
      if(!recovery && (pending.path!==path || JSON.stringify(pending.body)!==JSON.stringify(body))){
        tell("请先恢复上一项操作，确认它是否已保存。",true);return;
      }
    } catch { tell("待恢复的操作记录无法读取，请先确认当前游戏状态。",true);return; }
  }
  busy=true; localStorage.setItem("palter.pending", JSON.stringify({path,body})); render();
  const poll=runtimeMode==="ai"?setInterval(async()=>{try{const s=await request("/api/session");csrf=s.csrf;activeGame=s.active_game;if(s.view)apply(s.view);}catch{}},1200):null;
  try {
    const result=await request(path,body);
    if(!result.receipt?.pending)localStorage.removeItem("palter.pending");
    if(result.view) apply(result.view);
    tell(result.receipt?.message || result.message || "已保存。", result.receipt?.accepted===false || (result.status && !["completed","pending"].includes(result.status)));
    await refreshHistory();
    return result;
  } catch(error){
    if(error.status && error.status<500) localStorage.removeItem("palter.pending");
    tell(error.name==="AbortError" ? "响应尚未确认，可以恢复同一项操作。" : error.message, true);
    if(error.status===409){
      try{const session=await request("/api/session");csrf=session.csrf;activeGame=session.active_game;if(session.view)apply(session.view);await refreshHistory();}catch{}
    }else{ try { const session=await request('/api/session');csrf=session.csrf;activeGame=session.active_game;if(session.view)apply(session.view); } catch {} }
  } finally { if(poll!==null)clearInterval(poll);busy=false; render(); }
}
async function refreshHistory(){
  const session=await request("/api/session"); csrf=session.csrf; activeGame=session.active_game;
  document.querySelector("#history").innerHTML='<option value="">游戏记录</option>'+session.games.map((g,i)=>`<option value="${g.id}" ${view?.id===g.id?"selected":""}>${i===0?"最近一局":"已保存"} · ${g.beat}${g.archived?" · 只读":""}</option>`).join("");
}
function command(kind, extra={}){return post(`/api/games/${view.id}/commands`,{command_id:id(), expected_revision:view.revision, kind, ...extra});}
function heading(){return `<div class="case-heading"><div><div class="eyebrow">PALTER / YOUR STORY</div><h1>${escapeHTML(view.title||"失踪的交接信")}</h1><p>${escapeHTML(view.player_name?"你扮演 "+view.player_name+" · "+view.goal:"你扮演周砚 · 找到交接信，并带回大厅")}</p></div><div><div class="progress"><span class="beat-label">行动节拍</span>${Array.from({length:view.deadline||6},(_,i)=>`<span class="beat ${i<view.beat?"done":""} ${i===view.beat-1?"active":""}">${i+1}</span>`).join("")}</div></div></div>`;}
function observations(){return view.observations.length ? [...view.observations].reverse().map(o=>`<article class="observation"><time>第 ${o.beat} 节拍</time><p>${escapeHTML(o.text)}</p></article>`).join("") : '<p class="muted tiny">你亲眼见到的经历会记录在这里。</p>';}
function reviewPanel(){
  const review=view.review, usage=review.reported_usage;
  const enabled=!view.archived && ["active","ended"].includes(view.phase) && review.configured && !review.pending && (review.calls<review.limit || review.records.length);
  const count=value=>value===null?"未报告":value;
  return `<section class="panel"><h2><span class="section-number">04</span>线索回顾</h2><p class="muted tiny">整理你已经获得的观察，原始经历始终保留。</p><div class="review-actions"><button class="button small quiet" id="review" ${!enabled||busy?"disabled":""}>${review.pending?"正在整理…":"整理已知线索"}</button><span class="muted tiny">${review.calls} / ${review.limit} 次</span></div>${review.records.map(o=>`<div class="review-record"><span class="eyebrow">第 ${o.beat} 节拍</span><p>${escapeHTML(o.text)}</p></div>`).join("")}${!review.configured?'<p class="tiny muted">暂未连接线索整理，原始记录可正常查看。</p>':""}<details class="usage"><summary>模型用量记录</summary><dl><dt>模型</dt><dd>${escapeHTML(review.model)}</dd><dt>已发起调用</dt><dd>${review.calls}</dd><dt>输入 / 输出 token</dt><dd>${count(usage.prompt_tokens)} / ${count(usage.completion_tokens)}</dd><dt>缓存命中 token</dt><dd>${count(usage.prompt_cache_hit_tokens)}</dd><dt>费用上限估算（USD）</dt><dd>${review.estimated_upper_usd===null?"待确认":review.estimated_upper_usd.toFixed(6)}</dd></dl><p>按已报告用量及峰时价格估算；未报告用量保留为未知。</p></details></section>`;
}
function render(){
  const sameGame=renderedGame===view?.id;
  const scrollKey=node=>node.dataset.scrollKey||'input:'+node.id;
  const positions=new Map(sameGame?[...app.querySelectorAll('[data-scroll-key], textarea[id]')].map(node=>[
    scrollKey(node),{top:node.scrollTop,left:node.scrollLeft,
      followEnd:node.hasAttribute('data-scroll-follow')&&node.scrollHeight>node.clientHeight&&node.scrollHeight-node.clientHeight-node.scrollTop<8}
  ]):[]);
  const pagePosition=sameGame?{top:window.scrollY,left:window.scrollX}:{top:0,left:0};
  if(runtimeMode==="offline")document.querySelector("footer span:last-child").textContent="离线脚本验收模式 · 角色行为不调用模型";
  else if(view?.mode==="offline")document.querySelector("footer span:last-child").textContent="历史脚本记录 · 开始新局启用真实 AI";
  const focused=document.activeElement,focusId=focused?.id,start=focused?.selectionStart,end=focused?.selectionEnd;
  renderContent(busy||hasPending());enhanceAI();
  if(view?.mode==="ai"&&["speech","thought","intent"].includes(focusId)){
    const field=app.querySelector("#"+focusId);field?.focus({preventScroll:true});
    if(typeof start==="number"&&field?.setSelectionRange)field.setSelectionRange(start,end);
  }
  // Restore after details and focus; both can otherwise move a nested viewport.
  for(const node of app.querySelectorAll('[data-scroll-key], textarea[id]')){
    const saved=positions.get(scrollKey(node));if(!saved)continue;
    node.scrollTop=saved.followEnd?node.scrollHeight-node.clientHeight:saved.top;
    node.scrollLeft=saved.left;
  }
  window.scrollTo({...pagePosition,behavior:'instant'});
  renderedGame=view?.id;
}
function renderContent(busy){
  updateBusy();
  if(view?.spectator && typeof renderSpectator==="function"){renderSpectator(busy);return;}
  if(view?.gameplay==="ensemble" && typeof renderEnsemble==="function"){renderEnsemble(busy);return;}
  if(view?.gameplay==="investigation" && typeof renderInvestigation==="function"){renderInvestigation(busy);return;}
  if(!view){app.innerHTML='<section class="phase-card panel"><div class="eyebrow">A NEW STORY</div><h1>打开第一份档案</h1><p>从相同的起点，走出自己的经历。</p><button class="button" data-new '+(busy?"disabled":"")+'>开始新局 ↗</button></section>';return;}
  const archived=view.archived?'<div class="archive-banner">这是一局已保存的记录。你可以回顾当时的经历，或开始新局。</div>':"";
  if(view.phase==="introduction"){
    app.innerHTML=archived+`<section class="hero"><div><div class="eyebrow">档案 / 故事开始之前</div><h1>${escapeHTML(view.title||"失踪的交接信")}</h1><p>${escapeHTML(view.introduction)}</p><button class="button" data-command="confirm" ${busy||view.archived?"disabled":""}>确认故事，阅读角色资料 <span>↗</span></button><small>3 个地点 · 6 个行动节拍 · 由你的选择推进</small></div><div class="archive-art" aria-hidden="true"><div class="envelope"><div class="seal"></div></div><span class="art-caption">PALTER / 001</span></div></section>`;return;
  }
  if(["reading","paused"].includes(view.phase)){
    app.innerHTML=archived+heading()+`<section class="phase-card panel briefing"><div class="eyebrow">${view.phase==="reading"?"CHARACTER BRIEF / 初始阅读":"PAUSED / 阅读暂停"}</div><h1>${escapeHTML(view.player_name||"周砚")}，你的起点</h1><ol>${view.briefing.map(t=>`<li>${escapeHTML(t)}</li>`).join("")}</ol><p class="tiny muted">阅读不限时，期间故事不会推进。</p><div class="phase-buttons"><button class="button" data-command="${view.phase==="reading"?"ready":"resume"}" ${busy||view.archived?"disabled":""}>${view.phase==="reading"?"阅读完成，开始行动":"继续游玩"} ↗</button></div></section>${view.phase==="paused"?`<section class="phase-card panel"><h2>已获得的观察</h2>${observations()}</section>`:""}`;return;
  }
  const scene=view.scene;
  const routes=view.map.filter(r=>r.neighbors).map(r=>`${escapeHTML(r.name)} → ${r.neighbors.map(n=>escapeHTML(view.map.find(p=>p.id===n)?.name||n)).join("、")}`).join("<br>");
  let choice=view.options.find(o=>o.action===selectedAction) || view.options[0];
  if(choice){selectedAction=choice.action;if(!choice.targets.some(t=>t.id===selectedTarget)) selectedTarget=choice.targets[0]?.id||"";}
  app.innerHTML=archived+heading()+`<div class="workspace"><aside class="sidebar"><section class="panel"><h2><span class="section-number">01</span>已知地图</h2>${view.map.map(r=>`<div class="room ${r.id===scene.id?"current":""}"><span>${escapeHTML(r.name)}</span><span>${r.id===scene.id?"你在这里":""}</span></div>`).join("")}<p class="route-note">${routes||"大厅 ↔ 书房<br>大厅 ↔ 庭院"}</p></section><section class="panel"><h2>你的任务</h2><p class="task">${escapeHTML(view.goal||"找到带蓝色封口的交接信，并在会议前带回大厅。")}</p><div class="inventory"><span class="muted tiny">随身物品</span>${view.inventory.length?view.inventory.map(i=>`<p>${escapeHTML(i.name)}<br><span class="tiny muted">${escapeHTML(i.description)}</span></p>`).join(""):'<p class="muted">暂未携带相关物品</p>'}</div></section></aside><div><section class="panel scene"><div class="scene-kicker"><span>你此刻实际看到的场景</span>${view.phase==="active"&&!view.archived?`<button class="button small quiet" data-command="pause" ${busy?"disabled":""}>暂停查看资料</button>`:'<span>经历已存档</span>'}</div><h2>${escapeHTML(scene.name)}</h2><p class="scene-description">${escapeHTML(scene.description)}</p><div class="scene-people">${scene.people.length?scene.people.map(p=>`<span class="chip">${escapeHTML(p.name)}在场</span>`).join(""):`<span class="chip">${view.chat?'你正在与 '+escapeHTML(view.chat.partner)+' 私聊':'你暂时独自在这里'}</span>`}</div><p class="tiny muted">可见：${scene.objects.map(escapeHTML).join("、")}</p>${scene.last_seen.length?`<div class="last-seen">${scene.last_seen.map(p=>`${escapeHTML(p.name)} · 第 ${p.beat} 节拍最后见到：${escapeHTML(view.map.find(r=>r.id===p.location)?.name||names[p.location])}`).join("<br>")}<br>以上为当时的观察，不代表对方当前的位置。</div>`:""}</section>${view.outcome?`<section class="panel outcome"><div class="eyebrow">STORY ENDING / 故事暂告一段落</div><h2>${escapeHTML(view.outcome.title)}</h2><p>${escapeHTML(view.outcome.text)}</p><button class="button quiet" data-new ${busy?"disabled":""}>开始新故事 ↗</button></section>`:choice?`<section class="panel"><div class="actions-title"><span>选择这一次的行动</span><span class="muted tiny">提交后推进 1 节拍</span></div><div class="actions">${view.options.map(o=>`<button class="action ${o.action===selectedAction?"selected":""}" data-action="${o.action}" aria-pressed="${o.action===selectedAction}" ${busy?"disabled":""}><span class="action-symbol" aria-hidden="true">${symbols[o.action]}</span>${o.label}</button>`).join("")}</div><form id="action-form"><div class="target-row"><select id="target" aria-label="行动目标" ${busy||!choice.targets.length?"disabled":""}>${choice.targets.length?choice.targets.map(t=>`<option value="${t.id}" ${t.id===selectedTarget?"selected":""}>${escapeHTML(t.label)}</option>`).join(""):'<option>当前没有已知的可用目标</option>'}</select><button class="button" type="submit" ${busy||!choice.targets.length?"disabled":""}>${busy?"正在保存…":"提交行动"} ↗</button></div></form><p class="cost">${choice.targets.length?"本次消耗 1 个行动节拍。选择目标或阅读记录不会推进时间。":escapeHTML(choice.reason)}</p></section>`:""}</div><aside class="records-column"><section class="panel"><h2><span class="section-number">03</span>你的观察记录</h2><div class="timeline" data-scroll-key="observations">${observations()}</div></section>${reviewPanel()}</aside></div>`;
}
async function newGame(){
  const body={command_id:id(),expected_game_id:activeGame};
  if(runtimeMode==="ai")body.category=document.querySelector("#category").value||"mystery";
  if(runtimeGameplay==="ensemble"){
    body.humans=Number(document.querySelector('#human-count').value||1);
    body.opening=document.querySelector('#opening-mode').value||'after';
  }
  return post("/api/games",body);
}
app.addEventListener("click",event=>{
  const target=event.target.closest("button");if(!target)return;
  if(view?.mode==="ai" && ["pause","resume"].includes(target.dataset.command))return void aiControl(target.dataset.command);
  if(busy)return;
  if(target.hasAttribute("data-new")) return void newGame();
  if(target.dataset.command) return void command(target.dataset.command);
  if(target.dataset.action){selectedAction=target.dataset.action;selectedTarget="";render();}
  if(target.id==="review") void post(`/api/games/${view.id}/review`,{command_id:id(),expected_revision:view.revision});
});
app.addEventListener("change",event=>{if(event.target.id==="target")selectedTarget=event.target.value;});
app.addEventListener("submit",event=>{if(event.target.id==="action-form"){event.preventDefault();if(!busy){const extra={action:selectedAction,target:selectedTarget};if(view.mode==="ai"){extra.speech=speechDraft;extra.question_to=addressee||null;extra.channel=view.chat?.id||"public";}void command("action",extra);}}});
document.querySelector("#new-game").addEventListener("click",()=>void newGame());
document.querySelector("#history").addEventListener("change",async event=>{if(!event.target.value||busy)return;busy=true;try{apply((await request(`/api/games/${event.target.value}`)).view);tell("已打开这局记录。");}catch(error){tell(error.message,true);}finally{busy=false;render();}});
document.querySelector("#retry").addEventListener("click",()=>{try{
  if(view?.gameplay==='ensemble'&&view.background_error){
    if(view.background_error.retryable===false)return tell('请先处理当前错误或取消该步骤。',true);
    return void command(view.spectator&&view.phase==='paused'?'watch_resume':'retry_ai');
  }
  const pending=JSON.parse(localStorage.getItem("palter.pending"));if(pending)void post(pending.path,pending.body);
}catch{tell("无法读取待恢复的操作，请刷新查看当前记录。",true);}});
(async()=>{busy=true;updateBusy();try{const session=await request("/api/session");csrf=session.csrf;activeGame=session.active_game;runtimeMode=session.runtime_mode||"offline";runtimeGameplay=session.gameplay||null;if(session.view)apply(session.view);else render();await refreshHistory();busy=false;render();if(hasPending())tell("有一项操作的响应待确认，可恢复同一项操作。",true);}catch(error){tell(error.message,true);app.innerHTML='<div class="loading">连接暂未完成，请刷新页面重试。</div>';}})();

function enhanceAI(){
  if(view?.mode!=="ai" || ["investigation","ensemble"].includes(view?.gameplay))return;
  const trace=view.ai_trace||{calls:[],limit:128}, locked=busy||hasPending();
  document.querySelector("footer span:last-child").textContent="角色决策、DM、私聊、记忆与事件由 DeepSeek 实际运行";
  const taskNames={introduction:"故事介绍",initial_setup:"初始剧本",character:"角色决策与发言",action:"行动理解",dm:"主 DM",private_dm:"私聊 DM",memory:"记忆与关系",world_event:"全局事件",ending:"结局生成",review:"线索整理"};
  const traceHTML=`<section class="panel ai-trace-panel"><h2>AI 运行记录 <span class="muted tiny">${trace.calls.length} / ${trace.limit} 次调用</span></h2><p class="muted tiny">${trace.operation_status==="pending"?"DeepSeek 正在处理本轮，请稍候。":trace.operation_status==="buffered"?"已暂停，已完成的步骤保留，恢复后继续。":"下列记录来自实际模型调用。这里只展示元数据，不公开角色的私有决定。"}</p><details id="ai-trace-details" ${traceOpen?"open":""}><summary>查看任务、用量和状态</summary><div class="trace-table" data-scroll-key="ai-calls"><table><thead><tr><th>任务</th><th>角色</th><th>状态</th><th>输入 / 输出</th><th>缓存命中</th></tr></thead><tbody>${trace.calls.map(c=>`<tr><td>${escapeHTML(taskNames[c.task]||c.task)}</td><td>${escapeHTML(view.cast?.find(p=>p.id===c.actor)?.name||"系统")}</td><td>${escapeHTML(c.status)}${c.error?" · "+escapeHTML(c.error):""}</td><td>${c.usage?.prompt_tokens??"—"} / ${c.usage?.completion_tokens??"—"}</td><td>${c.usage?.prompt_cache_hit_tokens??"—"}</td></tr>`).join("")}</tbody></table></div></details></section>`;
  let html="";
  if(view.phase==="active"&&!view.archived){
    const partner=view.chat?`与 ${escapeHTML(view.chat.partner)} 私聊中（${view.chat.turns.length}/${view.chat.limit} 条）`:"公共讨论";
    html+=`<section class="panel ai-interaction"><h2>${partner}</h2>${view.must_speak?'<p class="required">已连续几轮没有发言，这一轮需要说一句话。</p>':view.must_respond?'<p class="required">有人向你提问，请用话语或动作回应。</p>':""}<label for="speech">你想说的话${view.chat?"（仅私聊对方能收到）":""}</label><textarea id="speech" maxlength="1000" placeholder="角色会根据自己的信息和目标作出真实的模型回应。">${escapeHTML(speechDraft)}</textarea><div class="dialogue-row"><select id="addressee" aria-label="发言对象"><option value="">对当前听众说</option>${(view.cast||[]).filter(p=>p.id!=="A"&&(!view.chat||p.id===view.chat.partner_id)).map(p=>`<option value="${p.id}" ${addressee===p.id?"selected":""}>对 ${escapeHTML(p.name)} 说</option>`).join("")}</select><button class="button" data-ai-kind="say" ${locked?"disabled":""}>发送发言</button><button class="button quiet" data-ai-gesture="点了点头" ${locked?"disabled":""}>点头回应</button><button class="button quiet" data-ai-gesture="摇了摇头" ${locked?"disabled":""}>摇头回应</button></div>`;
    if(view.chat)html+=`<p class="muted tiny">私聊期间不接收外部事件；结束后可询问其他人。</p><button class="button quiet" data-ai-kind="end_private" ${locked?"disabled":""}>结束私聊，回到公共讨论</button>`;
    else html+=`<div class="dialogue-row"><select id="invite-target" aria-label="私聊邀请对象">${(view.cast||[]).filter(p=>view.invite_targets?.includes(p.id)).map(p=>`<option value="${p.id}" ${inviteTarget===p.id?"selected":""}>${escapeHTML(p.name)}</option>`).join("")}</select><button class="button quiet" data-ai-kind="invite" ${locked||!view.invite_targets?.length?"disabled":""}>公开邀请私聊</button></div>`;
    for(const i of view.invitations||[])html+=`<div class="invitation">${escapeHTML(i.name)} 公开邀请你私聊。<button class="button small" data-ai-answer="accept" data-invitation="${i.id}" ${locked?"disabled":""}>同意</button> <button class="button small quiet" data-ai-answer="decline" data-invitation="${i.id}" ${locked?"disabled":""}>拒绝</button></div>`;
    html+=`<details class="private-input" ${privateInputOpen?"open":""}><summary>我的想法与打算（不向其他角色公开）</summary><label for="thought">只记录想法</label><textarea id="thought" placeholder="用“我”写下自己的想法，无需填写自己的角色名。" maxlength="1000">${escapeHTML(thoughtDraft)}</textarea><button class="button quiet" data-ai-kind="thought" ${locked?"disabled":""}>记录想法，不执行动作</button><label for="intent">现在要尝试的行动</label><textarea id="intent" maxlength="1200" placeholder="例如：我现在去书房查看抽屉。">${escapeHTML(intentDraft)}</textarea><button class="button" data-ai-kind="intent" ${locked?"disabled":""}>交给 DM 理解并尝试执行</button></details></section>`;
    app.querySelector(".scene")?.insertAdjacentHTML("afterend",html);
    html=`<section class="panel personal-memory"><h2>我的事件记忆与关系</h2><p>${escapeHTML(view.memory?.summary||"暂未形成新记忆。")}</p>${Object.entries(view.relationships||{}).map(([c,r])=>`<p><strong>${escapeHTML(view.cast?.find(p=>p.id===c)?.name||c)}</strong> · ${escapeHTML(r.description)}<br><span class="muted tiny">${escapeHTML(r.experiences?.at(-1)?.reason||"初始关系")}</span></p>`).join("")}</section>`;
    app.querySelector(".sidebar")?.insertAdjacentHTML("beforeend",html);
  }
  app.insertAdjacentHTML("beforeend",`<div class="ai-extras">${traceHTML}</div>`);
  for(const kind of ["pause","resume"]){const button=app.querySelector(`[data-command="${kind}"]`);if(button)button.disabled=controlBusy||view.archived;}
}
async function aiControl(kind){
  if(controlBusy)return;controlBusy=true;
  try{const result=await request(`/api/games/${view.id}/commands`,{command_id:id(),expected_revision:view.revision,kind});apply(result.view);tell(result.receipt.message);
    if(kind==="resume"&&hasPending()&&!busy){const pending=JSON.parse(localStorage.getItem("palter.pending"));void post(pending.path,pending.body);}
  }catch(error){tell(error.message,true);}finally{controlBusy=false;render();}
}
app.addEventListener("input",event=>{if(event.target.id==="speech")speechDraft=event.target.value;if(event.target.id==="thought")thoughtDraft=event.target.value;if(event.target.id==="intent")intentDraft=event.target.value;});
app.addEventListener("change",event=>{if(event.target.id==="addressee")addressee=event.target.value;if(event.target.id==="invite-target")inviteTarget=event.target.value;});
app.addEventListener("click",event=>{
  const button=event.target.closest("button");if(!button||busy||view?.mode!=="ai")return;
  const kind=button.dataset.aiKind,gesture=button.dataset.aiGesture,answer=button.dataset.aiAnswer;
  if(!kind&&!gesture&&!answer)return;
  let extra={channel:view.chat?.id||"public"};
  if(kind==="say"){if(!speechDraft.trim())return tell("请先输入要说的话。",true);extra={...extra,text:speechDraft,question_to:addressee||null};}
  if(kind==="thought")extra.text=thoughtDraft;
  if(kind==="intent"){extra.text=intentDraft;extra.speech=speechDraft;extra.question_to=addressee||null;}
  if(kind==="invite")extra.target=document.querySelector("#invite-target").value;
  if(gesture){extra.text=gesture;extra.question_to=addressee||null;}
  if(answer)extra.target=button.dataset.invitation;
  void command(answer||(gesture?"gesture":kind),extra).then(result=>{if(result?.receipt?.accepted){speechDraft="";thoughtDraft="";intentDraft="";render();}});
});
document.querySelector("#discard").addEventListener("click",async()=>{
  if(busy||!view||runtimeMode!=="ai")return;
  try{const operation=view.ai_trace?.operation_id;if(operation)await request(`/api/games/${view.id}/commands`,{command_id:id(),expected_revision:view.revision,kind:"cancel_pending",operation_id:operation});localStorage.removeItem("palter.pending");apply((await request(`/api/games/${view.id}`)).view);tell("已确认当前状态。已发生的调用用量保留。");}catch(error){tell(error.message,true);}
});

app.addEventListener("toggle",event=>{if(event.target.classList.contains("private-input"))privateInputOpen=event.target.open;if(event.target.id==="ai-trace-details")traceOpen=event.target.open;},true);
