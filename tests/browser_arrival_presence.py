"""Desktop/mobile rendering of structured movement and personal arrival receipts."""
from copy import deepcopy
import json
import threading
from pathlib import Path
from palter import ensemble_world as w, spectator
from palter.server import Server
from tests import test_arrival_presence as fixture


def main():
    from playwright.sync_api import sync_playwright, expect
    root=Path('.local/verification/arrival-presence-20261108/browser');root.mkdir(parents=True,exist_ok=True)
    f=fixture.ArrivalPresenceTests();f.setUp();app=f.app;app.start_background=lambda:None
    f.s['locations'].update(B='r3',C='r3',D='r3');f.private_pair()
    event=w.apply_choice(f.s,'A','move:r3')
    owner=app.store.session()['id']
    saved=app.store.create_game(owner,{'command_id':'browser_fixture','expected_game_id':None},lambda gid:dict(deepcopy(f.s),id=gid))
    watch=spectator.view(saved);watch.update(ai_busy=False,ai_trace=app.gateway.trace(owner,saved['id']))
    server=Server(('127.0.0.1',0),app);threading.Thread(target=server.serve_forever,daemon=True).start()
    report={'checks':[],'page_errors':[]}
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel='msedge',headless=True,chromium_sandbox=True)
            for width in (1440,390):
                p=browser.new_page(viewport={'width':width,'height':950},locale='zh-CN')
                p.on('pageerror',lambda e:report['page_errors'].append(str(e)))
                p.route('**/api/**',lambda route:route.fulfill(json={'csrf':'fixture','active_game':watch['id'],
                    'games':[],'runtime_mode':'ai','gameplay':'ensemble','view':watch}))
                p.goto(f'http://127.0.0.1:{server.server_port}');p.wait_for_function('()=>view?.spectator&&!busy')
                expect(p.locator('.watch-timeline article').filter(has_text='甲来到档案间。')).to_have_count(1)
                expect(p.locator('.watch-timeline article').filter(has_text='你来到')).to_have_count(0)
                p.locator('.watch-timeline').scroll_into_view_if_needed()
                p.screenshot(path=str(root/f'global-{width}.png'))
                p.locator('nav [data-watch-pane="A"]').click()
                arrival=p.locator('.watch-timeline article').filter(has_text='你来到档案间。')
                expect(arrival).to_have_count(1)
                expect(arrival).to_contain_text('丁也在这里，可以直接交流。')
                expect(arrival).to_contain_text('乙、丙也在这里，正在私聊')
                expect(p.locator('.watch-timeline')).not_to_contain_text('PRIVATE_ARRIVAL_CANARY')
                arrival.scroll_into_view_if_needed();p.screenshot(path=str(root/f'personal-{width}.png'))
                assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                report['checks'].append({'width':width,'one_third_person_movement':True,'personal_presence':True,'no_private_backfill':True,'no_horizontal_overflow':True})
                p.close()
            browser.close()
        assert not report['page_errors'];report['completed']=True
    finally:
        server.shutdown();server.server_close();f.doCleanups()
        (root/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
