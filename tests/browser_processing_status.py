"""Measure content geometry while real polling alternates provider status.
Isolated local browser/API fixtures only; no external model calls.
"""
from copy import deepcopy
import json,tempfile,threading
from pathlib import Path
from palter.deepseek import DeepSeek,Settings,ROOT
from palter.ensemble import EnsembleApplication
from palter.server import Application,Server
from tests.test_ensemble import EnsembleProvider
from tests.browser_scroll import fixture


def spectator_fixture(folder):
    app=EnsembleApplication(folder/'spectator.sqlite3',DeepSeek(Settings(api_key='fixture'),EnsembleProvider()))
    owner=app.store.session()['id']
    state=app.create_game(owner,{'command_id':'create_status_fixture','expected_game_id':None,'category':'murder','humans':0})
    for command in ('confirm','watch_resume'):
        state,_=app.command(owner,state['id'],{'command_id':'status_'+command,'expected_revision':state['revision'],'kind':command})
    data=app.view(owner,state)
    data['timeline']=[{'id':f'status-{i}','event_id':f'status-{i}','kind':'testimony','speaker_name':'测试角色',
        'channel':'public','text':f'第 {i} 条收到的信息。'+('继续核对已获得的材料。'*8),'cues':[]} for i in range(24)]
    return data


def main():
    from playwright.sync_api import sync_playwright
    output=ROOT/'.local/verification/processing-status-20261106';output.mkdir(parents=True,exist_ok=True)
    report={'completed':False,'page_errors':[],'checks':[]}
    with tempfile.TemporaryDirectory(prefix='palter-status-') as temp:
        folder=Path(temp);server=Server(('127.0.0.1',0),Application(folder/'http.sqlite3',DeepSeek(Settings(api_key='fixture'))))
        threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as pw:
                browser=pw.chromium.launch(channel='msedge',headless=True,chromium_sandbox=True)
                for kind in ('spectator','ensemble'):
                    original=spectator_fixture(folder) if kind=='spectator' else fixture(folder,'ensemble')
                    for width in (1440,390):
                        data=deepcopy(original);data['ai_busy']=False;data['ai_trace']['reserved_cost_usd']=0
                        page=browser.new_page(viewport={'width':width,'height':844});page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
                        def route(request):
                            request.fulfill(json={'csrf':'fixture','active_game':data['id'],'games':[],'runtime_mode':'ai','gameplay':'ensemble','view':data})
                        page.route('**/api/**',route);page.goto(base);page.wait_for_function('()=>view?.phase==="active"&&!busy')
                        anchor='.watch-tabs' if kind=='spectator' else '.investigation-layout'
                        timeline='.watch-timeline' if kind=='spectator' else '.recent-talk'
                        def sample():
                            return page.evaluate('''({anchor,timeline})=>{const a=document.querySelector(anchor),t=document.querySelector(timeline);return {pageY:scrollY,contentY:a.getBoundingClientRect().top,timelineY:t.getBoundingClientRect().top,innerY:t.scrollTop,pageHeight:document.documentElement.scrollHeight}}''',{'anchor':anchor,'timeline':timeline})
                        page.locator(timeline).evaluate('(n)=>n.scrollTop=(n.scrollHeight-n.clientHeight)*.55')
                        page.evaluate('window.scrollTo(0,600)');before=sample();samples=[]
                        for active in (True,False,True,False):
                            data['ai_busy']=active
                            if kind=='spectator':data['ai_trace']['reserved_cost_usd']=.0123 if active else 0
                            page.wait_for_function('(active)=>view.ai_busy===active',arg=active)
                            # Observe a painted frame, not just the assigned view variable.
                            page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
                            after=sample();samples.append(after)
                            for key in before:assert abs(after[key]-before[key])<2,(kind,width,key,before,after)
                            status=page.locator('.processing-status')
                            assert status.is_visible()==active
                            if kind=='spectator':assert page.locator('[data-watch="watch_pause"]').is_enabled()
                            else:assert page.locator('[data-en="say"]').is_disabled()==active
                        page.screenshot(path=str(output/(kind+'-'+str(width)+'.png')),full_page=True)
                        report['checks'].append({'runtime':kind,'width':width,'status_transitions':4,'baseline':before,'max_content_shift_px':max(abs(s['contentY']-before['contentY']) for s in samples)})
                        assert not report['page_errors'];page.close()
                browser.close();report['completed']=True
        except Exception as exc:
            report['error']={'type':type(exc).__name__,'message':str(exc)}
        finally:
            server.shutdown();server.server_close();(output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps(report,ensure_ascii=False,indent=2))
    if not report['completed']:raise SystemExit(1)

if __name__=='__main__':main()
