"""Isolated four-seat UI acceptance with an explicit provider double."""
from concurrent.futures import ThreadPoolExecutor
import json
import secrets
import threading

from palter.deepseek import DeepSeek,Settings,ROOT
from palter.ensemble import EnsembleApplication
from palter.server import Server
from tests.test_ensemble import EnsembleProvider


def main():
    from playwright.sync_api import sync_playwright,expect
    directory=ROOT/'.local/verification/browser-ensemble';directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    database=directory/('run-'+secrets.token_hex(4)+'.sqlite3');provider=EnsembleProvider()
    app=EnsembleApplication(database,DeepSeek(Settings(api_key='fixture'),provider))
    # Deterministic scheduling; the pause test explicitly runs a real pump thread.
    app.start_background=lambda:None
    server=Server(('127.0.0.1',0),app);threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}';report={'completed':False,'database':str(database),'page_errors':[],'checks':[],'provider':'explicit provider double'}
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel='msedge',headless=True,chromium_sandbox=True)
            pages=[browser.new_context(viewport={'width':1440,'height':1000},locale='zh-CN').new_page() for _ in range(2)]
            room={'code':''}
            for p in pages:
                p.set_default_timeout(15000);p.on('pageerror',lambda e:report['page_errors'].append(str(e)))
                p.on('dialog',lambda d:d.accept(room['code']) if d.type=='prompt' else d.accept())
                p.goto(base);expect(p.locator('#new-game')).to_be_enabled()
            a,b=pages
            def current(p):return p.request.get(base+'/api/session').json()['view']
            def refresh(p):
                v=current(p);p.wait_for_function('(revision)=>view&&view.revision>=revision',arg=v['revision']);return v
            def settled(p):
                p.wait_for_function('()=>!busy');assert not p.evaluate('hasPending()'),p.locator('#notice').inner_text()
                assert not report['page_errors'],report['page_errors'];assert p.locator('#notice.error').count()==0,p.locator('#notice').inner_text();return current(p)
            def click(p,selector):p.locator(selector).click();return settled(p)
            def act(p,choice):
                refresh(p);p.locator('#en-choice').select_option(choice);return click(p,'[data-en="act"]')
            a.locator('#human-count').select_option('2');intro=click(a,'#new-game');room['code']=intro['join_code']
            joined=click(b,'#join-game');assert joined['actor']=='B';refresh(a)
            reading=click(a,'[data-en="confirm"]');assert reading['phase']=='reading';refresh(b)
            assert 'B_PRIVATE_SECRET_CANARY' not in json.dumps(reading,ensure_ascii=False)
            assert 'A_PRIVATE_SECRET_CANARY' not in json.dumps(current(b),ensure_ascii=False)
            click(a,'[data-en="ready"]');refresh(b);click(b,'[data-en="ready"]');refresh(a)
            report['checks'].append('two independent browser sessions join separate private seats and synchronize reading')
            a.locator('#en-target').select_option('B');a.locator('#en-text').fill('请说明你亲眼看到的情况。');click(a,'[data-en="say"]');refresh(b)
            assert current(b)['must_respond'];click(b,'[data-en="nod"]');refresh(a)
            act(a,'invite:B');refresh(b);choice=next(c['id'] for c in current(b)['options'] if c['id'].startswith('accept:'));act(b,choice);refresh(a)
            assert current(a)['chat'];a.locator('#en-text').fill('这条私聊只交给你。');click(a,'[data-en="say"]');refresh(b)
            b.locator('#en-text').fill('我听到了，会核实原件。');click(b,'[data-en="say"]');refresh(a)
            assert current(a)['must_respond'];expect(a.locator('[data-en="end_private"]')).to_be_enabled()
            before=len(provider.calls);click(a,'[data-en="end_private"]')
            assert current(a)['chat'] is None;assert not current(a)['must_respond'];assert len(provider.calls)==before
            report['checks'].append('addressed human response, consented private exchange and immediate unilateral exit despite unanswered private reply, without a DM call')
            act(a,'inspect:c1');a.locator('[data-en-evidence="c1"]').check()
            a.locator('#en-notes summary').click();a.locator('#en-notes-text').fill('我需要用两条独立记录确认时间边界。');click(a,'[data-en="notebook"]')
            a.reload();settled(a);a.locator('#en-notes summary').click();expect(a.locator('#en-notes-text')).to_have_value('我需要用两条独立记录确认时间边界。')
            a.locator('.case-trace summary').click();expect(a.locator('.case-trace')).to_contain_text('缓存命中')
            a.screenshot(path=str(directory/'desktop.png'),full_page=True)
            a.set_viewport_size({'width':390,'height':844});assert a.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),a.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth,wide:[...document.querySelectorAll("body *")].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,id:e.id,classes:e.className,width:e.getBoundingClientRect().width}))})')
            a.screenshot(path=str(directory/'mobile.png'),full_page=True);a.set_viewport_size({'width':1440,'height':1000})
            report['checks'].append('persisted personal notebook, cache usage display and 390px layout')
            a.locator('#en-final > summary').click();a.locator('#en-testimony > summary').click()
            heard=next(o['id'] for o in current(a)['observations'] if o.get('text')=='我听到了，会核实原件。')
            a.locator(f'[data-en-testimony="{heard}"]').check();a.wait_for_timeout(1700)
            expect(a.locator(f'[data-en-testimony="{heard}"]')).to_be_checked()
            a.locator('#en-argument').fill('目前无法完成全部论证。');click(a,'[data-en="submit"]');refresh(b)
            with app.store.transaction(False) as con:
                stored=json.loads(con.execute('SELECT state FROM games WHERE id=?',(current(a)['id'],)).fetchone()['state'])
            assert stored['submissions']['A']['testimony_ids']==[heard]
            report['checks'].append('optional heard-testimony citation survives polling and is persisted with the independent conclusion')
            assert current(a)['ending'] is None and current(a)['submitted']
            b.locator('#en-final > summary').click();b.locator('#en-argument').fill('保留未查明的结论。');ended=click(b,'[data-en="submit"]');refresh(a)
            assert ended['phase']=='ended';a.screenshot(path=str(directory/'ending.png'),full_page=True)
            report['checks'].append('all-human submission barrier and independent goal results')
            a.locator('#human-count').select_option('1');click(a,'#new-game');click(a,'[data-en="confirm"]');click(a,'[data-en="ready"]')
            provider.block='ensemble_role';provider.release.clear();provider.entered.clear()
            with ThreadPoolExecutor(1) as pool:
                work=pool.submit(app.pump,current(a)['id'],True);assert provider.entered.wait(2)
                a.wait_for_function('()=>view.ai_busy');a.locator('#en-script summary').click()
                expect(a.locator('[data-en="pause"]')).to_be_enabled();click(a,'[data-en="pause"]')
                provider.release.set();work.result(5)
            assert current(a)['phase']=='paused';click(a,'[data-en="resume"]');provider.block=None
            assert app.pump(current(a)['id'],force=True);refresh(a)
            report['checks'].append('single-player pause during an in-flight role call and buffered recovery')
            assert not report['page_errors'];report['completed']=True;browser.close()
    except Exception as exc:
        import traceback
        report['error']={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    finally:
        provider.release.set();server.shutdown();server.server_close()
        path=database.with_suffix('.json');path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');path.chmod(0o600)
        print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    if not report['completed']:raise SystemExit(1)


if __name__=='__main__':main()
