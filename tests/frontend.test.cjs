// Pure JavaScript checks with a minimal document double. This is not visual QA.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {randomUUID}=require('node:crypto');
const code=fs.readFileSync('palter/static/app.js','utf8');

function fixture(phase='active'){
  return {id:'0123456789abcdef01234567',revision:2,phase,archived:false,beat:0,deadline:6,
    introduction:'公开介绍',briefing:['角色初始记忆'],map:[{id:'hall',name:'大厅',neighbors:['study']}],
    observations:[{id:'A-o0001',event_id:'e0001',beat:0,text:'你只知道眼前的事。'}],
    scene:{id:'hall',name:'大厅',description:'座钟正在走动。',people:[{id:'B',name:'林舟'}],objects:['长桌'],last_seen:[]},
    inventory:[],options:[{action:'move',label:'移动',targets:[{id:'study',label:'书房'}]},
      {action:'inspect',label:'查看',targets:[{id:'hall',label:'当前地点'}]},
      {action:'take',label:'拿取',targets:[],reason:'先发现物品。'},
      {action:'follow',label:'跟随',targets:[{id:'B',label:'林舟'}]},
      {action:'wait',label:'等待',targets:[{id:'',label:'留在原地'}]}],outcome:null,
    review:{calls:0,limit:3,pending:false,configured:true,model:'deepseek-flash',records:[],estimated_upper_usd:null,
      reported_usage:{prompt_tokens:null,completion_tokens:null,prompt_cache_hit_tokens:null}}};
}

async function harness(initial=fixture()){
  const elements=new Map(), storage=new Map(), calls=[];
  const element=selector=>{if(!elements.has(selector))elements.set(selector,{innerHTML:'',textContent:'',hidden:false,disabled:false,classList:{toggle(){}},querySelectorAll:()=>[],addEventListener(){}});return elements.get(selector);};
  let handler=async(path,options)=>{
    if(path==='/api/session')return {csrf:'csrf',active_game:initial.id,games:[],view:initial};
    return {view:initial,receipt:{accepted:true,message:'已保存'}};
  };
  const context=vm.createContext({window:{scrollX:0,scrollY:0,scrollTo(){}},document:{querySelector:element},localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)},
    crypto:{randomUUID},AbortController,setTimeout:()=>1,clearTimeout(){},
    fetch:async(path,options)=>{calls.push({path,options});const data=await handler(path,options);return {ok:true,status:200,json:async()=>data};}});
  vm.runInContext(code,context);
  await new Promise(setImmediate);
  return {context,elements,storage,calls,element,setHandler:next=>handler=next,
    run:source=>vm.runInContext(source,context),setView:next=>{context.nextView=next;vm.runInContext('apply(nextView)',context);}};
}

test('reading and paused views have no action submission form',async()=>{
  const h=await harness(fixture('reading'));
  assert.match(h.element('#app').innerHTML,/阅读完成，开始行动/);
  assert.doesNotMatch(h.element('#app').innerHTML,/id="action-form"/);
  h.setView({...fixture('paused'),revision:3});
  assert.match(h.element('#app').innerHTML,/继续游玩/);
  assert.doesNotMatch(h.element('#app').innerHTML,/id="review"/);
});

test('active view exposes the five bounded controls and explicit submission',async()=>{
  const h=await harness();
  const html=h.element('#app').innerHTML;
  for(const action of ['move','inspect','take','follow','wait'])assert.match(html,new RegExp(`data-action="${action}"`));
  assert.match(html,/提交后推进 1 节拍/);
  assert.match(html,/id="action-form"/);
  assert.match(html,/token/);
  assert.match(html,/未报告/);
});

test('observation text is escaped and an older response cannot rewind the page',async()=>{
  const h=await harness();
  const newer=fixture();newer.revision=4;newer.beat=2;newer.observations[0].text='<script>unsafe()</script>';
  h.setView(newer);
  assert.match(h.element('#app').innerHTML,/&lt;script&gt;/);
  assert.doesNotMatch(h.element('#app').innerHTML,/<script>unsafe/);
  h.setView(fixture());
  assert.equal(h.run('view.revision'),4);
});

test('a lost response locks new submissions and retries the original identity',async()=>{
  const h=await harness();
  const body={command_id:'pending_0001',expected_revision:2,kind:'action',action:'wait',target:''};
  let fail=true, attempts=[];
  h.setHandler(async(path,options)=>{
    if(options.method==='POST'){
      attempts.push(JSON.parse(options.body));
      if(fail)throw new TypeError('Simulated lost response');
      return {receipt:{accepted:true,message:'已保存'},view:fixture()};
    }
    if(path==='/api/session')return {csrf:'csrf',active_game:fixture().id,games:[],view:fixture()};
    return {view:fixture()};
  });
  h.context.body=body;
  const path=`/api/games/${fixture().id}/commands`;
  h.context.path=path;
  await h.run('post(path,body)');
  assert.ok(h.storage.has('palter.pending'));
  assert.equal(h.element('#new-game').disabled,true);
  assert.match(h.element('#app').innerHTML,/type="submit" disabled/);
  await h.run('post(path,{...body,command_id:"different_0001"})');
  assert.equal(attempts.length,1);
  fail=false;
  await h.run('post(path,body)');
  assert.equal(attempts.length,2);
  assert.equal(attempts[0].command_id,attempts[1].command_id);
  assert.equal(h.storage.has('palter.pending'),false);
});

test('ended and archived games do not offer another action',async()=>{
  const h=await harness();
  for(const outcome of ['delivered','incomplete','not_found']){
    const ended=fixture('ended');ended.revision=10;ended.beat=6;ended.outcome={id:outcome,title:outcome,text:'按实际经历结算。'};
    h.setView(ended);
    assert.match(h.element('#app').innerHTML,new RegExp(outcome));
    assert.doesNotMatch(h.element('#app').innerHTML,/id="action-form"/);
  }
  const archived=fixture();archived.revision=11;archived.archived=true;archived.options=[];
  h.setView(archived);
  assert.match(h.element('#app').innerHTML,/已保存的记录/);
  assert.doesNotMatch(h.element('#app').innerHTML,/id="action-form"/);
});

test('a stale new-game tab refreshes the active game pointer',async()=>{
  const h=await harness();
  const newer=fixture();newer.id='abcdef0123456789abcdef01';
  h.setHandler(async(path,options)=>{
    if(options.method==='POST'){const error=new Error('Stale tab');error.status=409;throw error;}
    return {csrf:'csrf',active_game:newer.id,games:[],view:newer};
  });
  await h.run('newGame()');
  assert.equal(h.run('activeGame'),newer.id);
  assert.equal(h.run('view.id'),newer.id);
  assert.equal(h.storage.has('palter.pending'),false);
});
