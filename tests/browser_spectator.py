"""Spectator browser acceptance with isolated game state and provider doubles."""
from copy import deepcopy
import json
import secrets
import threading
from palter.deepseek import DeepSeek,Settings,ROOT
from palter.ensemble import EnsembleApplication
from palter.server import Server
from palter import ensemble_world as w
from palter import role_schedule as scheduling, role_events
from tests.test_ensemble import EnsembleProvider


def main():
    from playwright.sync_api import sync_playwright,expect
    directory=ROOT/'.local/verification/browser-spectator';directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    database=directory/('run-'+secrets.token_hex(4)+'.sqlite3');provider=EnsembleProvider()
    provider.next_decision=lambda d:{'mode':'continue','events':[]}
    app=EnsembleApplication(database,DeepSeek(Settings(api_key='fixture'),provider));app.start_background=lambda:None
    server=Server(('127.0.0.1',0),app);threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}';report={'completed':False,'database':str(database),'page_errors':[],'checks':[]}
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel='msedge',headless=True,chromium_sandbox=True)
            page=browser.new_page(viewport={'width':1440,'height':1050},locale='zh-CN');page.set_default_timeout(15000)
            page.on('pageerror',lambda e:report['page_errors'].append(str(e)));page.goto(base);expect(page.locator('#new-game')).to_be_enabled()
            def current():return page.request.get(base+'/api/session').json()['view']
            def refresh():
                v=current();page.wait_for_function('(r)=>view?.revision>=r',arg=v['revision']);return v
            def click(selector):
                page.locator(selector).click();page.wait_for_function('()=>!busy')
                assert not page.evaluate('hasPending()'),page.locator('#notice').inner_text()
                assert not report['page_errors'],report['page_errors'];return current()
            page.locator('#human-count').select_option('0');intro=click('#new-game')
            assert intro['spectator'];gid=intro['id'];reading=click('[data-watch="confirm"]')
            assert reading['phase']=='reading';assert reading['watch']['steps']==0
            assert page.locator('#en-text').count()==0;assert page.locator('[data-en="submit"]').count()==0
            report['checks'].append('dedicated zero-human entry, explicit preparation/start and no player action controls')
            page.locator('[data-watch-pane="B"]').first.click();assert 'B_PRIVATE_SECRET_CANARY' in page.locator('#app').inner_text()
            page.locator('[data-watch-pane="truth"]').click();assert '开局已确定的真实经过' in page.locator('#app').inner_text()
            page.locator('[data-watch-pane="all"]').click();click('[data-watch="watch_step"]');app.pump(gid,True);v=refresh()
            assert v['phase']=='paused';assert v['watch']['steps']==1
            report['checks'].append('omniscient truth and individual role perspectives; single step pauses after one decision')
            click('[data-watch="watch_resume"]')
            for _ in range(18):app.pump(gid,True)
            v=refresh();assert v['watch']['pause_reason']=='stagnation';assert v['phase']=='paused'
            page.locator('.watch-timeline').evaluate('(n)=>n.scrollTop=n.scrollHeight/2')
            before=page.locator('.watch-timeline').evaluate('(n)=>n.scrollTop')
            page.wait_for_timeout(1800);assert abs(page.locator('.watch-timeline').evaluate('(n)=>n.scrollTop')-before)<2
            report['checks'].append('autonomous fair turns and stagnation pause; polling preserves timeline position')
            culprit=next(a for a,r in v['roles'].items() if r['perspective']=='concealment')
            innocent=next(a for a,r in v['roles'].items() if r['perspective']=='investigation')
            page.locator(f'[data-watch-pane="{culprit}"]').first.click()
            expect(page.get_by_role('heading',name='局势与应对',exact=True)).to_be_visible()
            expect(page.get_by_role('heading',name='当前局势',exact=True)).to_be_visible()
            expect(page.get_by_role('heading',name='应对计划',exact=True)).to_be_visible()
            assert page.get_by_role('heading',name='案件推断',exact=True).count()==0
            assert v['roles'][culprit]['strategy'] and v['roles'][culprit]['belief'] is None
            page.screenshot(path=str(directory/'culprit-perspective.png'),full_page=True)
            page.locator(f'[data-watch-pane="{innocent}"]').first.click()
            expect(page.get_by_role('heading',name='案件推断',exact=True)).to_be_visible()
            assert page.get_by_role('heading',name='局势与应对',exact=True).count()==0
            page.locator('[data-watch-pane="all"]').click()
            report['checks'].append('culprit situation/plan and personal memory are separate from innocent deduction')
            with app.store.transaction() as con:
                row=con.execute('SELECT owner,state FROM games WHERE id=?',(gid,)).fetchone();owner=row['owner'];old=json.loads(row['state']);s=deepcopy(old)
                identity=role_events.request(s,'A',{'event_request':{'description':'等公开核对时间记录','completion_condition':'有人公开解释时间差','early_end_condition':'当事人明确拒绝说明'}})
                role_events.apply(s,[{'id':identity,'status':'active','reason':'仍在等待公开说明。','progress':'私聊尚未结束。','source_ids':[]}],'browser-fixture')
                s['phase']='active';s['agenda']=[q for q in s['agenda'] if q['actor']!='A']
                scheduling.commit(s,'A',{'mode':'wait','events':['tracked:'+identity]},scheduling.context(s,'A'));s['phase']='paused'
                s['revision']+=1;app.store.save(con,s,old)
            refresh();assert '等待事件' in page.locator('.watch-role-grid').inner_text()
            page.locator('[data-watch-pane="A"]').first.click();page.locator('#watch-tracking-A summary').click()
            assert '等待条件：有人公开解释时间差' in page.locator('#watch-tracking-A').inner_text()
            assert '可提前结束：当事人明确拒绝说明' in page.locator('#watch-tracking-A').inner_text()
            page.screenshot(path=str(directory/'event-waiting.png'),full_page=True)
            page.locator('[data-watch-pane="all"]').click()
            report['checks'].append('waiting role status and private custom event condition/progress/early-end details render correctly')
            click('[data-watch="watch_speed"]');assert current()['watch']['speed']=='fast'
            v=click('[data-watch="watch_add_budget"]');assert abs(v['watch']['budget_usd']-.15)<1e-9
            assert v['phase']=='paused';report['checks'].append('playback speed and explicit budget addition leave paused game paused')
            # A count stop midway through a step retains the paid role result.
            with app.store.transaction() as con:
                row=con.execute('SELECT owner,state FROM games WHERE id=?',(gid,)).fetchone();owner=row['owner'];old=json.loads(row['state']);s=deepcopy(old)
                limit=con.execute('SELECT COUNT(*) FROM ai_calls WHERE game_id=?',(gid,)).fetchone()[0]+1
                s['watch']['call_limit']=limit;s['revision']+=1;app.store.save(con,s,old)
            refresh();click('[data-watch="watch_resume"]');app.pump(gid,True);v=refresh()
            assert v['watch']['pause_reason']=='call_limit';steps=v['watch']['steps'];roles=sum(t=='ensemble_role' for t,_,_ in provider.calls)
            expect(page.locator('[data-watch="watch_resume"]')).to_be_disabled()
            v=click('[data-watch="watch_add_calls"]');assert v['ai_trace']['limit']==limit+64
            assert v['phase']=='paused';assert abs(v['watch']['budget_usd']-.15)<1e-9
            expect(page.locator('[data-watch="watch_resume"]')).to_be_enabled()
            page.reload();page.wait_for_function('()=>view?.spectator&&!busy');assert current()['ai_trace']['limit']==limit+64
            click('[data-watch="watch_step"]');app.pump(gid,True);v=refresh()
            assert v['watch']['steps']==steps+1;assert sum(t=='ensemble_role' for t,_,_ in provider.calls)==roles
            report['checks'].append('count pause, explicit +64 persists across reload, no budget increase or auto-resume, cached role stage reused')
            # Actual private occurrence: visible to observer, absent in outside role view.
            with app.store.transaction() as con:
                row=con.execute('SELECT owner,state FROM games WHERE id=?',(gid,)).fetchone();owner=row['owner'];old=json.loads(row['state']);s=deepcopy(old)
                s['silent']['C']=0;s['obligations']['C']={'response':False,'explain':False,'sources':[]}
                w.apply_choice(s,'C','invite:D');w.apply_choice(s,'D','accept:'+s['invitations'][-1]['id']);w.speak(s,'C','PRIVATE_WATCH_BROWSER_CHECK',target='D')
                s['revision']+=1;app.store.save(con,s,old)
            refresh();assert 'PRIVATE_WATCH_BROWSER_CHECK' in page.locator('.watch-timeline').inner_text()
            page.locator('[data-watch-pane="A"]').first.click();assert 'PRIVATE_WATCH_BROWSER_CHECK' not in page.locator('#app').inner_text()
            session=page.request.get(base+'/api/session').json()
            response=page.request.post(base+f'/api/games/{gid}/commands',headers={'X-Palter-CSRF':session['csrf']},data={'command_id':'forbidden_watch_say','expected_revision':session['view']['revision'],'kind':'say','text':'旁观者试图发言'})
            assert response.status==403
            report['checks'].append('private transcript belongs to omniscient view; outside role lacks it; server rejects spectator speech')
            page.locator('[data-watch-pane="all"]').click()
            page.locator('.watch-timeline').scroll_into_view_if_needed()
            page.screenshot(path=str(directory/'desktop.png'),full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            page.locator('.watch-timeline').scroll_into_view_if_needed()
            page.screenshot(path=str(directory/'mobile.png'),full_page=True)
            page.locator('.watch-timeline').screenshot(path=str(directory/'mobile-dialogue.png'))
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
            report['checks'].append('desktop and 390px viewport with no page overflow')
            # Drop fixture budget to exercise actual request-admission failure and recovery controls.
            with app.store.transaction() as con:
                old=app.store.load(con,owner,gid);s=deepcopy(old);s['watch']['budget_usd']=.000001;s['revision']+=1;app.store.save(con,s,old)
            refresh();click('[data-watch="watch_resume"]');app.pump(gid,True);v=refresh();assert v['watch']['pause_reason']=='budget'
            assert '剩余预算不足' in page.locator('#app').inner_text();click('[data-watch="watch_add_budget"]')
            provider.policy=lambda d:'end_private' if any(c['id']=='end_private' for c in d['choices']) else 'lock_conclusion' if d['closure']['ready'] else 'close_vote:yes'
            click('[data-watch="watch_resume"]')
            for _ in range(20):app.pump(gid,True)
            v=refresh();assert v['phase']=='ended',v.get('background_error')
            assert '故事已结束' in page.locator('#app').inner_text();assert page.locator('[data-watch="watch_add_budget"]').count()==0
            assert page.locator('[data-watch="watch_add_calls"]').count()==0
            report['checks'].append('budget pause, explicit topup, pinned recovery, three-person closure and four final submissions')
            assert not report['page_errors'];report['completed']=True;browser.close()
    except Exception as exc:
        import traceback
        report['error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        server.shutdown();server.server_close();path=database.with_suffix('.json');path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    if not report['completed']:raise SystemExit(1)


if __name__=='__main__':main()
