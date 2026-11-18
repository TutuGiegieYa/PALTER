"""Rendered investigation progress and actual acquisition sources on a synthetic game."""
from copy import deepcopy
import json
import threading
import time

from palter import ensemble_world as w
from palter.deepseek import ROOT
from palter.server import Server
from tests.test_evidence_sharing import EvidenceSharingTests


def main():
    from playwright.sync_api import sync_playwright,expect
    folder=ROOT/'.local/verification/exploration-20261106';folder.mkdir(parents=True,exist_ok=True)
    fixture=EvidenceSharingTests();fixture.setUp();app=fixture.app;app.start_background=lambda:None
    s=fixture.state;s['exploration_version']=1
    w.apply_choice(s,'A','inspect:c1');w.apply_choice(s,'A','move:r3')
    w.apply_choice(s,'A','search');w.advance(s)
    w.apply_choice(s,'A','inspect:c4');w.apply_choice(s,'A','inspect:c9');fixture.disclose('A','c9')
    w.apply_choice(s,'C','move:r2');w.apply_choice(s,'C','inspect:c2')
    fixture.private('C','D');w.apply_choice(s,'A','share:c4')
    w.apply_choice(s,'C','share:c2');s['phase']='paused'
    owner=app.store.session()['id']
    with app.store.transaction() as con:
        con.execute('INSERT INTO games VALUES (?,?,?,?)',(s['id'],owner,json.dumps(s),time.time()))
    server=Server(('127.0.0.1',0),app);threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}';report={'checks':[],'page_errors':[],'provider':'explicit test double; synthetic fixture'}
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel='msedge',headless=True,chromium_sandbox=True)
            page=browser.new_page(viewport={'width':1440,'height':1050},locale='zh-CN')
            page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
            page.goto(base);page.wait_for_function('()=>Boolean(csrf)')
            from palter import spectator
            watch=spectator.view(s);watch['ai_trace']=app.gateway.trace(owner,s['id'])
            # Deterministic rendered fixture: polling is held to this same view.
            page.route('**/api/session',lambda route:route.fulfill(json={'csrf':'fixture','games':[],'active_game':s['id'],'view':watch}))
            page.evaluate('(v)=>apply(v)',watch)
            page.locator('[data-watch-pane="truth"]').click();page.locator('#watch-truth-evidence summary').first.click()
            card=lambda cid:page.locator('#watch-truth-evidence .evidence-card').filter(has=page.locator('strong',has_text=next(c['title'] for c in s['case']['clues'] if c['id']==cid)))
            expect(card('c4')).to_contain_text('已掌握：甲、乙')
            expect(card('c4')).to_contain_text('实际出示 1 次 · 口头披露 0 次')
            expect(card('c9')).to_contain_text('实际出示 0 次 · 口头披露 1 次')
            page.locator('#watch-evidence-sharing-c4 summary').click()
            expect(page.locator('#watch-evidence-sharing-c4')).to_contain_text('甲出示 · 公开 · 接收：乙')
            page.evaluate('(v)=>apply({...v,revision:v.revision+1})',watch)
            assert page.locator('#watch-evidence-sharing-c4').get_attribute('open') is not None
            page.locator('#watch-evidence-sharing-c2 summary').click()
            expect(page.locator('#watch-evidence-sharing-c2')).to_contain_text('丙出示 · 私聊 · 接收：丁')
            page.screenshot(path=str(folder/'truth-desktop.png'),full_page=True)
            report['checks'].append('truth separates knowledge, speech and presentation; public/private recipients and expanded state survive rerender')
            page.locator('[data-watch-pane="B"]').first.click()
            expect(page.locator('aside .evidence-origin')).to_have_text('由甲向我出示')
            page.locator('#watch-exploration-B summary').click()
            room=page.locator('#watch-exploration-B .evidence-card').filter(has=page.locator('strong',has_text=s['case']['rooms']['r3']['name']))
            expect(room).to_contain_text('本轮尚未调查')
            assert 'c4' not in json.dumps(watch['roles']['B']['exploration'],ensure_ascii=False)
            page.locator('#watch-exploration-B').screenshot(path=str(folder/'received-is-not-explored.png'))
            report['checks'].append('received document shows actual presenter and leaves its source area unvisited')
            page.locator('[data-watch-pane="A"]').first.click()
            expect(page.locator('aside')).to_contain_text('我已出示给：乙')
            expect(page.locator('aside')).to_contain_text('我尚未出示给：丙、丁')
            expect(page.locator('aside')).to_contain_text('我已口头提及 · 我尚未实际出示')
            assert not page.locator('aside').get_by_text(next(c['title'] for c in s['case']['clues'] if c['id']=='c2'),exact=True).count()
            expect(page.locator('aside .evidence-origin')).to_have_text(['我亲自检查所得','我亲自检查所得','我亲自检查所得'])
            page.locator('#watch-exploration-A summary').click()
            room=page.locator('#watch-exploration-A .evidence-card').filter(has=page.locator('strong',has_text=s['case']['rooms']['r2']['name']))
            expect(room).to_contain_text('本轮尚未调查')
            room=page.locator('#watch-exploration-A .evidence-card').filter(has=page.locator('strong',has_text=s['case']['rooms']['r3']['name']))
            expect(room).to_contain_text('完成搜查 1 次')
            watch['revision']+=2;page.evaluate('(v)=>apply(v)',watch)
            assert page.locator('#watch-exploration-A').get_attribute('open') is not None
            report['checks'].append('personal checks and completed searches render separately from unvisited areas and survive rerender')
            report['checks'].append('individual spectator panel shows personal receipts without hidden private evidence')
            page.set_viewport_size({'width':390,'height':844})
            page.locator('aside').scroll_into_view_if_needed();page.locator('aside').screenshot(path=str(folder/'role-mobile.png'))
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1')
            report['checks'].append('mobile material cards fit the viewport')
            player=deepcopy(s);player.pop('watch');player['phase']='active';player['humans']=['A'];player['joined']=['A']
            player_view=w.view(player,'A',True);player_view['revision']=watch['revision']+2
            page.unroute('**/api/session')
            page.route('**/api/session',lambda route:route.fulfill(json={'csrf':'fixture','games':[],'active_game':s['id'],'view':player_view}))
            page.evaluate('(v)=>apply(v)',player_view)
            expect(page.locator('.case-notebook')).to_contain_text('我已口头提及 · 我尚未实际出示')
            expect(page.locator('.case-notebook')).to_contain_text('我尚未出示给：丙、丁')
            page.locator('#en-exploration summary').click()
            expect(page.locator('#en-exploration')).to_contain_text('本轮尚未调查')
            page.locator('.case-notebook').screenshot(path=str(folder/'player-mobile.png'))
            report['checks'].append('normal player material cards use the same scoped delivery status')
            assert not report['page_errors'],report['page_errors'];browser.close()
        report['completed']=True
    finally:
        server.shutdown();server.server_close();fixture.doCleanups()
        (folder/'browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
