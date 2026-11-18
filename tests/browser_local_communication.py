"""Real local HTTP commands, independent player views, desktop and mobile."""
from copy import deepcopy
import json
import threading
from palter.deepseek import ROOT
from palter.server import Server
from palter import ensemble_world as w, spectator, role_schedule
from tests import test_local_communication as fixture


def main():
    from playwright.sync_api import sync_playwright, expect
    folder=ROOT/'.local/verification/local-communication-20261108/browser';folder.mkdir(parents=True,exist_ok=True)
    f=fixture.LocalCommunicationTests();f.setUp();app=f.app;app.gateway.current_version=fixture.VERSION;app.start_background=lambda:None
    server=Server(('127.0.0.1',0),app);threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}';report={'completed':False,'checks':[],'page_errors':[]}
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel='msedge',headless=True,chromium_sandbox=True)
            for width in (1440,390):
                sessions={a:app.store.session() for a in 'ABCD'}
                def factory(gid):
                    s=deepcopy(f.s);s.pop('watch');s.update(id=gid,humans=list('ABCD'),joined=list('ABCD'),ready=list('ABCD'),agenda=[])
                    return s
                s=app.store.create_game(sessions['A']['id'],{'command_id':'browser_fixture','expected_game_id':None},factory)
                with app.store.transaction() as con:
                    for actor,session in sessions.items():
                        con.execute('INSERT INTO game_members VALUES (?,?,?)',(s['id'],session['id'],actor))
                        con.execute('UPDATE sessions SET active_game=? WHERE id=?',(s['id'],session['id']))
                pages={};posts=[]
                for actor in 'ABC':
                    context=browser.new_context(viewport={'width':width,'height':950},locale='zh-CN')
                    context.add_cookies([{'name':'palter_session','value':sessions[actor]['id'],'url':base}])
                    p=context.new_page();p.on('pageerror',lambda e:report['page_errors'].append(str(e)))
                    p.on('request',lambda r:posts.append(r.post_data_json) if r.method=='POST' else None)
                    p.goto(base);p.wait_for_function('()=>view?.phase==="active"&&!busy');pages[actor]=p
                a,b,c=(pages[x] for x in 'ABC')
                expect(a.locator('#en-target option[value="B"]')).to_have_count(1)
                expect(a.locator('#en-target option[value="C"]')).to_have_count(0)
                expect(a.locator('#en-choice option[value="invite:C"]')).to_have_count(0)
                a.locator('#en-travel-speech').fill('我去工作室看看。')
                a.evaluate('render()');expect(a.locator('#en-travel-speech')).to_have_value('我去工作室看看。')
                a.locator('[data-en-choice="move:r3"]').click();a.wait_for_function('()=>view.scene?.id==="r3"&&!busy')
                expect(a.locator('#en-travel-speech')).to_have_value('')
                expect(a.locator('#en-target option[value="B"]')).to_have_count(0)
                expect(a.locator('#en-target option[value="C"]')).to_have_count(1)
                b.wait_for_function('()=>view.observations.some(o=>o.text==="甲离开了这里。")')
                c.wait_for_function('()=>view.observations.some(o=>o.text==="甲来到了这里。")')
                assert b.evaluate('view.observations.some(o=>o.text==="我去工作室看看。")')
                assert not c.evaluate('view.observations.some(o=>o.text==="我去工作室看看。")')
                assert not b.evaluate('view.observations.some(o=>o.text.includes("甲前往档案间"))')
                assert posts[-1]['kind']=='act' and posts[-1]['choice']=='move:r3' and posts[-1]['text']=='我去工作室看看。'
                before=len(f.f.provider.calls)
                a.locator('[data-en-choice="move:r2"]').click();a.wait_for_function('()=>view.scene?.id==="r2"&&!busy')
                assert len(f.f.provider.calls)==before,'Silent move must not add a model round'
                expect(a.locator('#en-target option[value="D"]')).to_have_count(1)
                assert posts[-1]['text']==''
                assert a.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                a.evaluate('window.scrollTo(0,0)');a.screenshot(path=str(folder/f'local-{width}.png'),full_page=True)
                report['checks'].append({'width':width,'speech_then_move':True,'silent_move_no_call':True,'separate_recipients':True,'draft_retained':True})
                for p in pages.values():p.context.close()
            # Three own records awaiting memory processing need not end a wait.
            f.s['memory']['D']['checkpoint']=len(f.s['observations']['D'])
            for _ in range(3):w.note(f.s,'D',w.emit(f.s,'observation','D'),'我保留刚才自己的行动记录。')
            role_schedule.commit(f.s,'D',{'mode':'wait','events':['next_observation']},role_schedule.context(f.s,'D'))
            watch=spectator.view(f.s);watch.update(ai_busy=False,ai_trace=app.gateway.trace(sessions['A']['id'],s['id']))
            p=browser.new_page(viewport={'width':1440,'height':950})
            p.on('pageerror',lambda e:report['page_errors'].append(str(e)))
            p.route('**/api/**',lambda route:route.fulfill(json={'csrf':'fixture','active_game':watch['id'],'games':[],'runtime_mode':'ai','gameplay':'ensemble','view':watch}))
            p.goto(base);p.wait_for_function('()=>view?.spectator&&!busy')
            expect(p.locator('.watch-role-grid')).to_contain_text('待整理进记忆 3 条记录')
            expect(p.locator('.watch-role-grid')).to_contain_text('不表示等待条件已满足')
            expect(p.locator('.watch-role-grid')).not_to_contain_text('累积 3 条新记录')
            p.locator('.watch-role-grid').screenshot(path=str(folder/'wait-memory.png'))
            report['checks'].append({'wait_memory_count':3,'waiting':True,'explanation_visible':True});p.close()
            browser.close();assert not report['page_errors'];report['completed']=True
    finally:
        server.shutdown();server.server_close();f.doCleanups()
        (folder/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
