const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function render(rows,key='all'){
  const context=vm.createContext({rows,key,app:{addEventListener(){}},escapeHTML:s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),enCues:()=>''});
  vm.runInContext(fs.readFileSync('palter/static/spectator.js','utf8'),context);
  return vm.runInContext("watchTranscript(rows,key,a=>({A:'甲',B:'乙'}[a]||a))",context);
}

test('global receipts are closed details with stable IDs and explicit recipients',()=>{
  const html=render([{event_id:'e1',speaker_name:'行动记录',text:'甲查看了《材料》。',details:[{title:'材料',recipients:['A','B'],text:'你看到 <script> 的原文。'}]}]);
  assert.match(html,/<details id="watch-receipts-e1">/);assert.doesNotMatch(html,/<details[^>]*\bopen/);
  assert.match(html,/甲、乙收到的原文/);assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>/);
  assert.match(html,/data-scroll-key="watch-talk-all"/);
});

test('role receipts and dialogue retain their exact second person content',()=>{
  const html=render([{event_id:'e2',text:'你开始搜查当前区域。'}],'A');
  assert.match(html,/你开始搜查当前区域。/);assert.doesNotMatch(html,/<details/);
  const speech=render([{event_id:'e3',speaker_name:'甲',channel:'public',text:'你有疑问吗？'}]);
  assert.match(speech,/你有疑问吗？/);assert.doesNotMatch(speech,/<details/);
});
