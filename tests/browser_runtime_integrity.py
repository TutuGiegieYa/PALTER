"""Synthetic human final submissions through real local HTTP and rendered UI."""
from copy import deepcopy
import json
from pathlib import Path
import threading
from palter import ensemble_world as w
from palter.server import Server
from tests.test_runtime_integrity import RuntimeIntegrityTests,VERSION


def main():
    from playwright.sync_api import sync_playwright,expect
    root=Path('.local/verification/runtime-integrity-20261108/browser');root.mkdir(parents=True,exist_ok=True)
    f=RuntimeIntegrityTests();f.setUp();app=f.app;app.gateway.current_version=VERSION;app.start_background=lambda:None
    server=Server(('127.0.0.1',0),app);threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}';report={'passed':False,'checks':[],'page_errors':[]}
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel='msedge',headless=True,chromium_sandbox=True)
            for width in (1440,390):
                f.prepare();f.actor='A';f.acquire(['c1','c2','c4','c7','c9'])
                event=w.speak(f.s,'B','我听到了公共区域的声音，但没见到说话的人。')
                sid=next(o['id'] for o in f.s['observations']['A'] if o['event_id']==event['id'])
                owner=app.store.session()['id']
                def factory(gid):
                    s=deepcopy(f.s);s.pop('watch');s.update(id=gid,humans=list('ABCD'),joined=list('ABCD'),ready=list('ABCD'),agenda=[])
                    return s
                s=app.store.create_game(owner,{'command_id':'browser_fixture','expected_game_id':None},factory)
                with app.store.transaction() as con:
                    con.execute('INSERT INTO game_members VALUES (?,?,?)',(s['id'],owner,'A'))
                    con.execute('UPDATE sessions SET active_game=? WHERE id=?',(s['id'],owner))
                context=browser.new_context(viewport={'width':width,'height':950},locale='zh-CN')
                context.add_cookies([{'name':'palter_session','value':owner,'url':base}]);page=context.new_page()
                page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
                page.on('dialog',lambda d:d.accept())
                page.goto(base);page.wait_for_function('()=>view?.phase==="active"&&!busy')
                page.locator('#en-final > summary').click()
                expect(page.locator('#en-final fieldset')).to_have_count(3)
                page.locator('#en-suspect').select_option('B')
                values={'identity':['c9','c7'],'time':['c1','c2'],'method':['c4','c7']}
                for aspect,ids in values.items():
                    page.locator('#en-final-'+aspect).fill('我依据取得的记录说明'+aspect)
                    page.locator('#en-gap-'+aspect).fill('仍有待核实的地方。')
                    page.locator('#en-final-sources-'+aspect+' > summary').click()
                    for cid in ids:page.locator(f'[data-final-aspect="{aspect}"][data-final-source="evidence_ids"][value="{cid}"]').check()
                page.locator('#en-final-heard-time > summary').click()
                page.locator(f'[data-final-aspect="time"][data-final-source="testimony_ids"][value="{sid}"]').check()
                page.evaluate('render()')
                expect(page.locator('#en-final-time')).to_have_value('我依据取得的记录说明time')
                expect(page.locator(f'[data-final-aspect="time"][value="{sid}"]')).to_be_checked()
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                page.locator('#en-final-time').scroll_into_view_if_needed()
                page.screenshot(path=str(root/f'final-{width}.png'))
                page.locator('[data-en="submit"]').click()
                page.wait_for_function('()=>view?.submitted===true&&!busy')
                saved=app.store.state(owner,s['id'])['submissions']['A']
                assert len(saved['aspects'])==3 and set(saved['evidence_ids'])=={'c1','c2','c4','c7','c9'}
                assert saved['testimony_ids']==[sid] and saved['suspect']=='B'
                report['checks'].append({'width':width,'three_aspects':True,'draft_survives_render':True,
                                        'no_horizontal_overflow':True,'submitted_citations_exact':True})
                context.close()
            browser.close()
        assert not report['page_errors'];report['passed']=True
    finally:
        server.shutdown();server.server_close();f.doCleanups()
        (root/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
