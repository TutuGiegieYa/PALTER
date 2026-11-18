"""Show finite waits and their outcomes at desktop and mobile widths."""
from copy import deepcopy
import json
import threading
from pathlib import Path
from palter import spectator,role_schedule
from palter.server import Server
from tests.test_wait_lifecycle import WaitLifecycleTests


def main():
    from playwright.sync_api import sync_playwright,expect
    root=Path('.local/verification/wait-lifecycle-20261108/browser');root.mkdir(parents=True,exist_ok=True)
    f=WaitLifecycleTests();f.setUp();app=f.app;app.start_background=lambda:None
    f.wait(timeout_seconds=30,wait_reason='等待收到与当前事项有关的实际进展。');f.review()
    owner=app.store.session()['id'];saved=app.store.create_game(owner,{'command_id':'browser_fixture','expected_game_id':None},lambda gid:dict(deepcopy(f.s),id=gid))
    waiting=spectator.view(saved);waiting.update(ai_busy=False,ai_trace=app.gateway.trace(owner,saved['id']))
    saved['watch']['clock']=30;role_schedule.reconcile(saved)
    expired=spectator.view(saved);expired.update(ai_busy=False,ai_trace=waiting['ai_trace'])
    report={'checks':[],'page_errors':[]};server=Server(('127.0.0.1',0),app)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel='msedge',headless=True,chromium_sandbox=True)
            for width in (1440,390):
                current=deepcopy(waiting);p=browser.new_page(viewport={'width':width,'height':950},locale='zh-CN')
                p.on('pageerror',lambda e:report['page_errors'].append(str(e)))
                p.route('**/api/**',lambda route:route.fulfill(json={'csrf':'fixture','active_game':current['id'],'games':[],
                    'runtime_mode':'ai','gameplay':'ensemble','view':current}))
                p.goto(f'http://127.0.0.1:{server.server_port}');p.wait_for_function('()=>view?.spectator&&!busy')
                expect(p.locator('.watch-role-grid')).to_contain_text('剩余 30 秒游戏活动时间')
                p.locator('.watch-role-grid').scroll_into_view_if_needed();p.screenshot(path=str(root/f'waiting-{width}.png'))
                rect=p.locator('.watch-role-grid').bounding_box();p.evaluate('view.roles.A.scheduling.remaining_seconds=29;render()')
                assert p.locator('.watch-role-grid').bounding_box()['height']==rect['height']
                current=deepcopy(expired);p.reload();p.wait_for_function('()=>view?.roles.A.scheduling.last_result')
                expect(p.locator('.watch-role-grid')).to_contain_text('上次等待超时')
                p.locator('nav [data-watch-pane="A"]').click()
                expect(p.locator('.watch-timeline')).to_contain_text('等待已超时')
                p.locator('.watch-timeline').scroll_into_view_if_needed();p.screenshot(path=str(root/f'expired-{width}.png'))
                assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                report['checks'].append({'width':width,'remaining_time':True,'countdown_height_stable':True,'timeout_receipt':True,'no_horizontal_overflow':True})
                p.close()
            browser.close()
        assert not report['page_errors'];report['completed']=True
    finally:
        server.shutdown();server.server_close();f.doCleanups()
        (root/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
