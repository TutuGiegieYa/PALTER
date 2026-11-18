/* Case UI: acquired records, attributed testimony and private reasoning stay distinct. */
let caseDraft={game:null,speech:"",target:"",notes:"",selected:[],suspect:"",argument:"",intent:"",thought:"",tab:"evidence",sort:false};
const caseEscape=escapeHTML;
function caseButton(label,attrs,disabled=false,quiet=true){return `<button class="button ${quiet?'quiet':''}" ${attrs} ${disabled?'disabled':''}>${label}</button>`;}
function caseCallNames(task){return ({ensemble_preview:"故事预览",ensemble_setup:"角色与场景",ensemble_opening:"开场选择",ensemble_role:"角色回应与行动",ensemble_address:"交谈对象识别",ensemble_action:"行动理解",ensemble_memory:"个人记忆",ensemble_dm:"谈话裁定",ensemble_world:"世界事件",ensemble_ending:"结局复盘",ensemble_theory:"结案论证核验",case_introduction:"案件预览",case_setup:"完整剧本",case_character:"角色回应与行动",case_dm:"场景裁定",case_memory:"个人记忆",case_action:"行动理解",case_theory:"推理核验",case_ending:"结案复盘"})[task]||task;}
function caseTraceMarkup(trace){
  const h=caseEscape, count=n=>Number.isInteger(n)&&n>=0?n.toLocaleString('zh-CN'):'未报告';
  const cache=u=>u&&['prompt_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens'].every(k=>Number.isInteger(u[k])&&u[k]>=0)&&u.prompt_tokens===u.prompt_cache_hit_tokens+u.prompt_cache_miss_tokens?u:null;
  const rate=u=>u&&u.prompt_tokens>0?(100*u.prompt_cache_hit_tokens/u.prompt_tokens).toFixed(1)+'%':'—';
  const reported=trace.calls.map(c=>cache(c.usage)).filter(Boolean);
  const totals=reported.reduce((sum,u)=>({prompt_tokens:sum.prompt_tokens+u.prompt_tokens,prompt_cache_hit_tokens:sum.prompt_cache_hit_tokens+u.prompt_cache_hit_tokens,prompt_cache_miss_tokens:sum.prompt_cache_miss_tokens+u.prompt_cache_miss_tokens}),{prompt_tokens:0,prompt_cache_hit_tokens:0,prompt_cache_miss_tokens:0});
  const summary=reported.length?`缓存命中 <strong>${count(totals.prompt_cache_hit_tokens)}</strong> / 未命中 <strong>${count(totals.prompt_cache_miss_tokens)}</strong> tokens · 输入命中率 <strong>${rate(totals)}</strong>`:'缓存用量尚未报告。';
  return `<details id="case-trace" class="panel case-trace"><summary>AI 运行记录 · ${trace.calls.length} 次调用</summary><p>${summary}</p><p class="tiny muted">缓存统计已报告 ${reported.length} / ${trace.calls.length} 次调用，未报告的用量不计为零。只显示任务与用量，不展示角色秘密。</p><div class="trace-table" data-scroll-key="ai-calls"><table><thead><tr><th>任务</th><th>模型</th><th>状态</th><th>输入 / 输出</th><th>缓存命中</th><th>缓存未命中</th><th>输入命中率</th></tr></thead><tbody>${trace.calls.map(c=>`<tr><td>${h(caseCallNames(c.task))}</td><td>${h(c.model||trace.model)}</td><td>${h(c.status)}</td><td>${count(c.usage?.prompt_tokens)} / ${count(c.usage?.completion_tokens)}</td><td>${count(c.usage?.prompt_cache_hit_tokens)}</td><td>${count(c.usage?.prompt_cache_miss_tokens)}</td><td>${rate(cache(c.usage))}</td></tr>`).join('')}</tbody></table></div></details>`;
}
function renderInvestigation(locked){
  const expanded=[...app.querySelectorAll('details[open]')].map(d=>d.id).filter(Boolean);
  const focus=document.activeElement, focusId=focus?.id, start=focus?.selectionStart,end=focus?.selectionEnd;
  if(caseDraft.game!==view.id)caseDraft={game:view.id,speech:"",target:"",notes:view.notebook?.text||"",selected:[...(view.notebook?.evidence_ids||[])],suspect:"",argument:"",intent:"",thought:"",tab:"evidence",sort:false};
  document.querySelector('footer span:last-child').textContent="调查由你的选择推进 · 阅读和整理笔记不会推进剧情";
  const h=caseEscape, readonly=view.archived, active=view.phase==="active"&&!readonly, off=locked||!active;
  const banner=readonly?'<div class="archive-banner">已保存的案件记录 · 只读回顾</div>':"";
  const header=`<div class="case-heading"><div><div class="eyebrow">PALTER / CASE FILE</div><h1>${h(view.title)}</h1><p>${view.player_name?'你扮演 '+h(view.player_name)+' · ':''}每个人，都只知道故事的一部分。</p></div><div>${active?caseButton("暂停阅读",'data-case-control="pause"',controlBusy):""}</div></div>`;
  if(view.phase==="introduction"){
    app.innerHTML=banner+`<section class="hero"><div><div class="eyebrow">一桩等待你还原的案件</div><h1>${h(view.title)}</h1><p>${h(view.introduction)}</p>${caseButton(locked?"正在准备完整案件…":"确认案件，生成完整剧本 ↗",'data-case-command="confirm"',locked||readonly,false)}<small>4 位参与者 · 独立角色剧本 · 自由调查，没有固定幕数</small><p class="tiny muted">开局一次性准备完整案件和个人剧本，可能需要数分钟。调查中检查现场和整理笔记会立即完成。</p></div><div class="archive-art" aria-hidden="true"><div class="envelope"><div class="seal"></div></div><span class="art-caption">PALTER / CASE</span></div></section>`;
    return;
  }
  if(["reading","paused"].includes(view.phase)){
    app.innerHTML=banner+header+`<section class="panel phase-card"><div class="eyebrow">${view.phase==="reading"?'你的角色剧本':'调查已暂停'}</div><h1>${h(view.player_name)}的起点</h1>${view.briefing.map(p=>`<p>${h(p)}</p>`).join("")}<p class="muted tiny">阅读不限时。你知道的事和其他人的说法，未必是同一回事。</p>${view.phase==="reading"?caseButton("阅读完成，开始调查 ↗",'data-case-command="ready"',locked||readonly,false):caseButton("继续调查 ↗",'data-case-control="resume"',controlBusy||readonly,false)}</section>`;
    if(view.phase==="paused")app.insertAdjacentHTML('beforeend',`<section class="panel phase-card"><h2>已获得的线索</h2>${view.evidence.map(c=>`<h3>${h(c.title)}</h3><p>${h(c.observation)}</p>`).join("")||'<p class="muted">尚无线索。</p>'}</section>`);
    return;
  }
  const actors=view.cast.filter(c=>c.id!=="A"&&(!view.chat||view.chat.participants.includes(c.id)));
  if(caseDraft.target&&!actors.some(c=>c.id===caseDraft.target))caseDraft.target="";
  const moves=view.options.filter(c=>c.id.startsWith('move:')),inspect=view.options.filter(c=>c.id.startsWith('inspect:'));
  const statements=view.observations.filter(o=>["testimony","gesture"].includes(o.kind));
  const history=view.observations.filter(o=>!['testimony','gesture','evidence'].includes(o.kind));
  const evidence=caseDraft.sort?[...view.evidence].sort((a,b)=>a.time.localeCompare(b.time,'zh-CN')):view.evidence;
  const selected=view.evidence.filter(c=>caseDraft.selected.includes(c.id));
  const options=actors.map(c=>`<option value="${h(c.id)}" ${caseDraft.target===c.id?'selected':''}>询问 ${h(c.name)}</option>`).join('');
  const chat=view.chat?`<p class="required">正在与 ${h(view.chat.partner)} 私聊 · 外部谈话不会自动补入你的记录</p>${caseButton('结束私聊','data-case-choice="end_private"',off)}`:`<div class="dialogue-row">${view.options.filter(c=>c.id.startsWith('invite:')).map(c=>caseButton(h(c.label),`data-case-choice="${h(c.id)}"`,off)).join('')}</div>`;
  const invitations=view.invitations.map(i=>`<p class="invitation">${h(view.cast.find(c=>c.id===i.from)?.name)}邀请你私聊 ${caseButton('同意',`data-case-choice="accept:${h(i.id)}"`,off)} ${caseButton('拒绝',`data-case-choice="decline:${h(i.id)}"`,off)}</p>`).join('');
  const scene=`<section class="panel"><div class="eyebrow">当前现场</div><h2>${h(view.scene.name)}</h2><p>${h(view.scene.description)}</p><div class="dialogue-row">${moves.map(c=>caseButton(h(c.label),`data-case-choice="${h(c.id)}"`,off)).join('')}</div><h3>可以检查</h3><div class="case-targets">${inspect.map(c=>caseButton(h(c.label),`data-case-choice="${h(c.id)}"`,off)).join('')||'<p class="muted tiny">当前可检查的材料已记入笔记，或你正在私聊。</p>'}</div></section>`;
  const recentTalk=statements.slice(-4).map(o=>`<article class="case-utterance"><strong>${h(o.speaker_name)}</strong><span class="tiny muted"> · ${o.channel==='public'?'公开':'私聊'}</span><p>${h(o.text)}</p></article>`).join('');
  const dialogue=`<section class="panel"><h2>${view.chat?'私下追问':'交流与质证'}</h2>${chat}${invitations}<div class="recent-talk" data-scroll-key="dialogue" data-scroll-follow aria-live="polite">${recentTalk}</div>${view.must_respond?'<p class="required">有人向你提问，你可以用话语或动作回应。</p>':''}<label for="case-target">交谈对象</label><select id="case-target"><option value="">向当前听众发言</option>${options}</select><label for="case-speech">你想问什么？</label><textarea id="case-speech" maxlength="1600" placeholder="追问某段经历，或指出两份记录之间的矛盾…" ${off?'disabled':''}>${h(caseDraft.speech)}</textarea><div class="dialogue-row">${caseButton('发送追问','data-case-send="say"',off,false)}${caseButton('出示选中的线索'+(selected.length?'（'+selected.length+'）':''),'data-case-send="present"',off||!selected.length)}${caseButton('点头回应','data-case-gesture="点头"',off)}${caseButton('留意其他人的行动','data-case-choice="wait"',off)}</div><p class="tiny muted">在笔记中选择证据，再向当前听众出示。私聊中的证据只交给双方。</p><details><summary>我的想法与尝试</summary><label for="case-thought">不告诉其他人的想法</label><textarea id="case-thought" placeholder="用“我”写下自己的想法，无需填写自己的角色名。" maxlength="2000">${h(caseDraft.thought)}</textarea>${caseButton('记录想法','data-case-send="thought"',off)}<label for="case-intent">想尝试的行动</label><textarea id="case-intent" placeholder="例如：我现在检查这份材料。" maxlength="1200">${h(caseDraft.intent)}</textarea>${caseButton('尝试这个行动','data-case-send="intent"',off)}</details></section>`;
  let notebook='';
  if(caseDraft.tab==='evidence')notebook=`<p class="tiny muted">已掌握 ${view.evidence.length} 条材料。勾选后可出示，或用于最终推理。</p>${caseButton(caseDraft.sort?'按发现顺序':'按记录时间排列','data-case-sort',false)}<div class="evidence-list">${evidence.map(c=>`<article class="evidence-card"><label><input type="checkbox" data-case-evidence="${h(c.id)}" ${caseDraft.selected.includes(c.id)?'checked':''}> <strong>${h(c.title)}</strong></label><div class="tiny muted">${h(c.time)} · ${h(c.source)}</div><p>${h(c.observation)}</p></article>`).join('')||'<p class="muted">先检查现场，或请其他人出示他们发现的材料。</p>'}</div>`;
  if(caseDraft.tab==='statements')notebook=`<p class="tiny muted">以下是实际说过的话，内容仍可能不准确。</p><div class="case-statements" data-scroll-key="statements">${[...statements].reverse().map(o=>`<article class="evidence-card"><strong>${h(o.speaker_name)}</strong><span class="tiny muted"> · ${o.channel==='public'?'公开':'私聊'}</span><p>${h(o.text)}</p>${o.speaker!=='A'?caseButton('追问这句话',`data-case-followup="${h(o.id)}"`,off):''}</article>`).join('')||'<p class="muted">还没有交谈记录。</p>'}</div>`;
  if(caseDraft.tab==='notes')notebook=`<p class="tiny muted">写下自己的解释和疑点。保存笔记不会告诉你答案，也不会告诉其他人。</p><label for="case-notes">我的假设与线索关联</label><textarea id="case-notes" placeholder="用“我”记录判断、依据和疑点。" maxlength="4000" class="long-notes">${h(caseDraft.notes)}</textarea><p class="tiny muted">当前关联：${selected.map(c=>h(c.title)).join('、')||'还未选择线索'}</p>${caseButton('保存笔记','data-case-send="notebook"',off)}`;
  const finalForm=`<section class="panel"><details id="case-final"><summary>形成结论，准备结案</summary><p>你可以继续自由调查。提交最终指认会结束本局，并展开真相复盘。</p><label for="case-suspect">你指认谁？</label><select id="case-suspect"><option value="">选择角色</option>${view.cast.filter(c=>c.id!=='A').map(c=>`<option value="${c.id}" ${caseDraft.suspect===c.id?'selected':''}>${h(c.name)}</option>`).join('')}</select><label for="case-argument">发生了什么？你凭什么这样判断？</label><textarea id="case-argument" maxlength="4000" placeholder="用“我”说明判断，结合时间、人物行动和选中的材料给出依据。">${h(caseDraft.argument)}</textarea><p>引用材料：${selected.map(c=>h(c.title)).join('、')||'尚未选择，仍可以提交自己的判断'}</p><div class="dialogue-row">${caseButton('提交最终指认','data-case-send="accuse"',off,false)}${caseButton('暂未查明，就此结案','data-case-send="close_case"',off)}</div></details></section>`;
  let resolution='';
  if(view.ending){const r=view.resolution;const labels={established:'证据支持的还原',unproven:'指认正确，论证尚不充分',incorrect:'指认有误',unresolved:'暂未查明'};resolution=`<section class="panel outcome"><div class="eyebrow">${h(labels[view.outcome])}</div><h2>${h(view.ending.title)}</h2><p>${h(view.ending.narrative)}</p><details open><summary>真相与证据复盘</summary><p><strong>实际凶手：</strong>${h(r.killer)}<br><strong>作案时间：</strong>${h(r.time)}</p><p>${h(r.reconstruction)}</p><ol>${r.history.map(e=>`<li><strong>${h(e.time)}</strong> ${h(e.text)}</li>`).join('')}</ol>${Object.entries(r.proofs).map(([key,sets])=>`<p><strong>${h({identity:'人物与机会',time:'时间判断',method:'作案与误导'}[key])}：</strong>${sets.map(ids=>ids.map(id=>h(r.all_evidence.find(c=>c.id===id)?.title||'材料')).join(' + ')).join('；或 ')}</p>`).join('')}<p>本次公开出示材料 ${r.social.disclosures} 次。</p>${r.social.beliefs.map(b=>`<p>${h(b.name)}最后怀疑：${h(b.suspect)}</p>`).join('')}</details>${caseButton('开始新案件 ↗','data-new',locked)}</section>`;}
  const traceHTML=caseTraceMarkup(view.ai_trace);
  app.innerHTML=banner+header+resolution+`<div class="investigation-layout"><div>${scene}${active?dialogue+finalForm:''}<section class="panel"><details><summary>现场动态</summary>${[...history].reverse().slice(0,18).map(o=>`<p class="tiny">${h(o.text)}</p>`).join('')}</details></section></div><aside class="panel case-notebook" data-scroll-key="notebook:${h(caseDraft.tab)}"><h2>调查笔记</h2><div class="case-tabs">${[['evidence','现场材料'],['statements','各人说法'],['notes','我的推理']].map(([tab,label])=>`<button class="action ${caseDraft.tab===tab?'selected':''}" data-case-tab="${tab}">${label}</button>`).join('')}</div>${notebook}</aside></div>`+traceHTML;
  for(const key of expanded){const detail=document.getElementById(key);if(detail)detail.open=true;}
  if(focusId?.startsWith('case-')){const field=document.getElementById(focusId);field?.focus({preventScroll:true});if(typeof start==='number'&&field?.setSelectionRange)field.setSelectionRange(start,end);}
}
app.addEventListener('input',e=>{
  const fields={'case-speech':'speech','case-notes':'notes','case-argument':'argument','case-intent':'intent','case-thought':'thought'};
  if(fields[e.target.id])caseDraft[fields[e.target.id]]=e.target.value;
});
app.addEventListener('change',e=>{
  if(e.target.id==='case-target')caseDraft.target=e.target.value;
  if(e.target.id==='case-suspect')caseDraft.suspect=e.target.value;
  if(e.target.dataset.caseEvidence){const key=e.target.dataset.caseEvidence;caseDraft.selected=e.target.checked?[...new Set([...caseDraft.selected,key])]:caseDraft.selected.filter(x=>x!==key);render();}
});
app.addEventListener('click',async e=>{
  if(view?.gameplay!=='investigation')return;
  const button=e.target.closest('button');if(!button)return;const d=button.dataset;
  if(d.caseTab){caseDraft.tab=d.caseTab;render();return;}
  if('caseSort' in d){caseDraft.sort=!caseDraft.sort;render();return;}
  if(d.caseFollowup){const o=view.observations.find(o=>o.id===d.caseFollowup);caseDraft.speech='你刚才说“'+o.text+'”。能解释一下依据和当时的情况吗？';caseDraft.target=o.speaker;render();document.getElementById('case-speech')?.focus();return;}
  if(d.caseControl)return void aiControl(d.caseControl);
  if(busy||hasPending())return;
  if(d.caseCommand)return void command(d.caseCommand);
  const channel=view.chat?.id||'public';
  if(d.caseChoice)return void command('act',{choice:d.caseChoice,channel});
  if(d.caseGesture)return void command('gesture',{gesture:d.caseGesture,channel});
  const kind=d.caseSend;if(!kind)return;
  let extra={channel};
  if(['say','present'].includes(kind)){extra.text=caseDraft.speech;if(caseDraft.target)extra.target=caseDraft.target;}
  if(['present','notebook','accuse'].includes(kind))extra.evidence_ids=caseDraft.selected;
  if(kind==='notebook')extra.text=caseDraft.notes;
  if(kind==='thought')extra.text=caseDraft.thought;
  if(kind==='intent')extra.text=caseDraft.intent;
  if(kind==='accuse'){
    if(!caseDraft.suspect||!caseDraft.argument.trim())return tell('请先选择指认对象，并写下你的推理。',true);
    if(!confirm('提交后将结束本次调查并揭晓真相。确定提交最终指认吗？'))return;
    extra.suspect=caseDraft.suspect;extra.text=caseDraft.argument;
  }
  if(kind==='close_case'&&!confirm('确定以“暂未查明”结束调查并查看复盘吗？'))return;
  const result=await command(kind,extra);
  if(result?.receipt?.accepted&&['say','present','thought','intent'].includes(kind)){caseDraft.speech='';caseDraft.thought='';caseDraft.intent='';render();}
});
if(view?.gameplay==='investigation')render();
