const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function render(extra={}){
  const room={room_id:'r2',name:'测试区域',status:'visible_acquired',current:true,personally_checked:[],completed_searches:1,last_observed_beat:2,visible_unread_records:[],snapshot_current:true,revisit_notice:false,...extra};
  const ctx=vm.createContext({room,app:{addEventListener(){}},document:{querySelector:()=>null},setInterval(){},escapeHTML:s=>String(s)});
  vm.runInContext(fs.readFileSync('palter/static/ensemble.js','utf8'),ctx);
  return vm.runInContext("explorationMarkup([room],'test-exploration')",ctx);
}
test('current certification explicitly states that searchable evidence has been read',()=>{
  assert.match(render({no_new_evidence:true}),/当前可发现材料均已读完，暂无新证据可调查/);
});
test('remote certification is explicitly historical',()=>{
  const html=render({no_new_evidence:true,current:false,snapshot_current:false});
  assert.match(html,/上次核查时/);assert.match(html,/当前情况需到场确认/);
  assert.doesNotMatch(html,/暂无新证据可调查/);
});
test('visible acquired alone does not claim evidence exhaustion',()=>{
  assert.doesNotMatch(render(),/暂无新证据可调查|上次核查时/);
});
