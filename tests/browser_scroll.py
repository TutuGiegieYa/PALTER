"""Browser regression for scroll retention across polls and full view updates.
All stories and API payloads are isolated provider-double fixtures; no paid calls.
"""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading

from palter.deepseek import DeepSeek,Settings,ROOT
from palter.ensemble import EnsembleApplication
from palter.investigation import InvestigationApplication
from palter.ai_runtime import AIApplication
from palter.server import Application,Server
from palter import ensemble_world
from tests.test_ensemble import EnsembleProvider
from tests.test_investigation import CaseProvider
from tests.test_ai import ProviderDouble


def fixture(directory,kind):
    cls,provider={'ensemble':(EnsembleApplication,EnsembleProvider),'investigation':(InvestigationApplication,CaseProvider),'legacy':(AIApplication,ProviderDouble)}[kind]
    app=cls(directory/(kind+'.sqlite3'),DeepSeek(Settings(api_key='fixture'),provider()))
    owner=app.store.session()['id'];state=app.create_game(owner,{'command_id':'create_scroll_001','expected_game_id':None,'category':'mystery'})
    for command in ('confirm','ready'):
        state,_=app.command(owner,state['id'],{'command_id':'scroll_'+command+'_001','expected_revision':state['revision'],'kind':command})
    state['observations']['A']=[{'id':f'A-scroll-{i}','event_id':f'scroll-{i}','beat':i,'kind':'testimony','speaker':'B',
        'speaker_name':'测试角色','channel':'public','text':f'第 {i} 条记录。'+('核对自己看到的记录，保留尚未证实的判断。'*12)} for i in range(36)]
    if kind=='ensemble':
        for c in state['case']['clues']:ensemble_world.acquire(state,'A',c['id'],{'id':'fixture-inspect'},'测试中取得')
        state['notes']['A']['text']='一行个人笔记，继续核对记录。\n'*90
        for i,actor,words,cue in ((34,'A','我当时只看了记录。','嘴角绷了一瞬，又恢复了原来的神情。'),
                                   (35,'B','你能再说清楚时间吗？','说到最后几个字时，语速放慢了一点。')):
            state['observations']['A'][i].update(speaker=actor,text=words)
            event=ensemble_world.emit(state,'cue',actor,source=f'scroll-{i}',call_id='fixture')
            ensemble_world.note(state,'A',event,cue,'cue')
    elif kind=='investigation':
        state['known']['A']=[c['id'] for c in state['case']['clues']]
        state['notebook']['text']='一行个人笔记，继续核对记录。\n'*90
    view=app.view(owner,state)
    call={'task':'ensemble_dm' if kind=='ensemble' else 'case_dm' if kind=='investigation' else 'dm',
        'model':'deepseek-flash','status':'completed','actor':'B','usage':{'prompt_tokens':100,'completion_tokens':30,'prompt_cache_hit_tokens':40,'prompt_cache_miss_tokens':60}}
    view['ai_trace']['calls']=[{'id':'fixture-call-'+str(i),**deepcopy(call)} for i in range(40)]
    return view


def main():
    from playwright.sync_api import sync_playwright
    report={'completed':False,'page_errors':[],'checks':[]}
    directory=ROOT/'.local/verification/browser-scroll';directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    with tempfile.TemporaryDirectory(prefix='palter-scroll-') as temp:
        folder=Path(temp);server=Server(('127.0.0.1',0),Application(folder/'http.sqlite3',DeepSeek(Settings(api_key='fixture'))))
        threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True,chromium_sandbox=True)
                for kind in ('ensemble','investigation','legacy'):
                    data=fixture(folder,kind);page=browser.new_page(viewport={'width':1440,'height':1000})
                    page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
                    def route(request):
                        body={'csrf':'fixture','active_game':data['id'],'games':[],'runtime_mode':'ai','gameplay':data.get('gameplay'),'view':data} if request.request.url.endswith('/api/session') else {'view':data}
                        request.fulfill(json=body)
                    page.route('**/api/**',route);page.goto(base);page.wait_for_function('()=>view&&view.phase==="active"&&!busy')
                    trace='#case-trace' if kind!='legacy' else '#ai-trace-details'
                    page.locator(trace+' summary').click()
                    if kind=='ensemble':
                        for i,needle in ((34,'嘴角绷了一瞬'),(35,'语速放慢了一点')):
                            row=page.locator(f'.recent-talk [data-utterance="scroll-{i}"]')
                            assert needle in row.locator('.utterance-cue').inner_text()
                        assert page.locator('.recent-talk .utterance-cue').count()==2
                        assert page.locator('#en-history .utterance-cue').count()==2
                        scene=page.locator('section').filter(has=page.locator('h3',has_text='最近现场变化'))
                        assert '嘴角绷了一瞬' not in scene.inner_text()
                        page.locator('.recent-talk').evaluate('(n)=>n.scrollTop=n.scrollHeight')
                        page.locator('.recent-talk').screenshot(path=str(directory/'dialogue-cues-desktop.png'))
                        page.locator('#en-final > summary').click();page.locator('#en-testimony > summary').click()
                        report['checks'].append({'runtime':kind,'case':'human and AI cues attach to their own utterances and full history without standalone scene duplicates'})
                    selector='[data-scroll-key], textarea[id]'
                    def sample():
                        return page.evaluate('''selector=>Object.fromEntries([...document.querySelectorAll(selector)].filter(n=>n.clientHeight>0&&(n.scrollHeight>n.clientHeight+4||n.scrollWidth>n.clientWidth+4)).map(n=>[n.dataset.scrollKey||'input:'+n.id,{top:n.scrollTop,left:n.scrollLeft,max:n.scrollHeight-n.clientHeight}]))''',selector)
                    def position(bottom=False):
                        page.evaluate('''({selector,bottom})=>{for(const n of document.querySelectorAll(selector)){if(!n.clientHeight)continue;n.scrollTop=(n.scrollHeight-n.clientHeight)*(bottom?1:.55);n.scrollLeft=n.scrollWidth-n.clientWidth;}window.scrollTo(0,650);}''',{'selector':selector,'bottom':bottom})
                        return sample(),page.evaluate('scrollY')
                    def update():
                        data['revision']+=1
                        if kind=='ensemble':page.wait_for_function('(r)=>view.revision===r',arg=data['revision'])
                        else:page.evaluate('next=>apply(next)',data)
                    def check_positions(before,y):
                        after=sample()
                        for key,saved in before.items():
                            assert key in after,(kind,key,after)
                            assert abs(saved['top']-after[key]['top'])<2,(kind,key,'vertical',saved,after[key])
                            assert abs(saved['left']-after[key]['left'])<2,(kind,key,'horizontal',saved,after[key])
                        assert abs(page.evaluate('scrollY')-y)<2,(kind,'page moved')
                    for bottom in (False,True):
                        before,y=position(bottom);assert before,(kind,'no scrollable fixtures');update();check_positions(before,y)
                    report['checks'].append({'runtime':kind,'case':'desktop middle/bottom survives changed view','containers':list(before)})
                    if kind=='ensemble':
                        page.evaluate('document.querySelector(".recent-talk").scrollMarker=true')
                        page.wait_for_timeout(3200)
                        assert page.evaluate('document.querySelector(".recent-talk").scrollMarker===true'),'unchanged polls replaced the DOM'
                        check_positions(before,y)
                        # Call status can change before the game revision commits.
                        data['ai_busy']=True
                        page.wait_for_function('()=>view.ai_busy')
                        assert page.locator('[data-en="say"]').is_disabled()
                        check_positions(before,y)
                        data['ai_busy']=False
                        page.wait_for_function('()=>!view.ai_busy')
                        assert page.locator('[data-en="say"]').is_enabled()
                        check_positions(before,y)
                        report['checks'].append({'runtime':kind,'case':'same-revision AI status updates controls without moving scroll'})
                        # A longer new message follows the bottom only when already there.
                        observation={**next(o for o in reversed(data['observations']) if o['kind']=='testimony'),'id':'new-scroll-message','event_id':'new-scroll-event','cues':[],'speaker':'B','speaker_name':'测试角色','channel':'public','text':'新发言。'*150}
                        data['observations'].append(observation);update()
                        assert page.locator('.recent-talk').evaluate('(n)=>Math.abs(n.scrollHeight-n.clientHeight-n.scrollTop)<2')
                        report['checks'].append({'runtime':kind,'case':'unchanged polling keeps DOM; new message follows bottom'})
                        # Required speech must agree with the server's action gate.
                        original={key:deepcopy(data[key]) for key in ('must_speak','must_respond','must_explain','options')}
                        data.update(must_speak=True,must_respond=False,must_explain=False);update()
                        for action in ('act','intent','forge','nod','shake'):
                            assert page.locator('[data-en="'+action+'"]').is_disabled(),action
                        assert page.locator('[data-en-choice]:enabled').count()==0
                        assert page.locator('[data-en="say"]').is_enabled()
                        assert page.locator('[data-en="notebook"]').is_enabled()
                        assert page.locator('[data-en="thought"]').is_enabled()
                        assert '连续几次交流没有发言' in page.locator('#app').inner_text()
                        data['options'].append({'id':'accept:fixture-invitation','label':'同意私聊'});update()
                        assert page.locator('[data-en="act"]').is_enabled()
                        assert page.locator('#en-choice option').all_text_contents()==['同意私聊']
                        data.update(must_explain=True,must_respond=True);update()
                        assert page.locator('[data-en="act"]').is_disabled()
                        assert '用话语解释质疑' in page.locator('#app').inner_text()
                        data.update(must_speak=False,must_explain=False);update()
                        assert page.locator('[data-en="nod"]').is_enabled()
                        assert page.locator('[data-en="intent"]').is_disabled()
                        data.update(original);update()
                        report['checks'].append({'runtime':kind,'case':'periodic speech, explanation and response controls match allowed actions'})
                        data['background_error']={'message':'测试中的连接中断，已有进展保留。','operation_id':'fixture','retryable':False};update()
                        assert page.locator('[data-en="retry_ai"]').is_disabled()
                        assert page.locator('[data-en="cancel_ai"]').is_enabled()
                        data['background_error']['retryable']=True;update()
                        assert page.locator('[data-en="retry_ai"]').is_enabled()
                        data['background_error']=None;update()
                        report['checks'].append({'runtime':kind,'case':'retry exhaustion disables recovery but leaves explicit cancellation available'})
                    if kind=='investigation':
                        page.locator('[data-case-tab="statements"]').click()
                        before,y=position();assert 'statements' in before;update();check_positions(before,y)
                        page.locator('[data-case-tab="notes"]').click();field='#case-notes'
                    elif kind=='ensemble':
                        page.locator('#en-notes summary').click();field='#en-notes-text'
                    else:field=None
                    if field:
                        page.locator(field).evaluate('(n)=>{n.focus({preventScroll:true});n.setSelectionRange(20,25);n.scrollTop=110;}')
                        before,y=position();update();check_positions(before,y)
                        assert page.evaluate('document.activeElement.id')==field[1:]
                        assert page.locator(field).evaluate('n=>[n.selectionStart,n.selectionEnd]')==[20,25]
                        report['checks'].append({'runtime':kind,'case':'notes focus, selection and scroll retained'})
                    page.set_viewport_size({'width':390,'height':844});before,y=position(True);update();check_positions(before,y)
                    if kind=='ensemble':
                        page.locator('[data-utterance="scroll-35"]').scroll_into_view_if_needed()
                        page.locator('.recent-talk').screenshot(path=str(directory/'dialogue-cues-mobile.png'))
                    if kind!='legacy':assert before['ai-calls']['left']>0,'mobile table did not overflow'
                    report['checks'].append({'runtime':kind,'case':'mobile log horizontal/vertical position retained'})
                    assert not report['page_errors'],report['page_errors'];page.close()
                browser.close();report['completed']=True
        except Exception as exc:
            import traceback
            report['error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
        finally:
            server.shutdown();server.server_close()
            path=directory/'report.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');path.chmod(0o600)
            print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    if not report['completed']:raise SystemExit(1)


if __name__=='__main__':main()
