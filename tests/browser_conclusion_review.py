"""Rendered score explanations on desktop/mobile, both play and watch views."""
from copy import deepcopy
import json
import threading
import time
from palter import ensemble_world as w, spectator
from palter.deepseek import ROOT
from palter.server import Server
from tests import test_conclusion_review as fixture


def main():
    from playwright.sync_api import sync_playwright, expect
    root = ROOT/'.local/verification/conclusion-review-20261108/browser'; root.mkdir(parents=True, exist_ok=True)
    f = fixture.ConclusionReviewTests(); f.setUp(); app = f.app; app.start_background = lambda: None
    s = f.s; ids = ['c1','c2','c3','c4','c9','c10','c11']
    for actor in 'ACD':
        f.acquire(ids, actor); f.submit([c for c in ids if c != 'c2'] if actor == 'A' else ids, actor)
    f.submit([], 'B', suspect=None, explanation='我保留我的立场。')
    def response(task, out, data):
        if task == 'ensemble_theory':
            for c in out['claims']:
                c['reason'] = {'identity':'把保管记录、新断口与致命伤联系起来，人物推断有依据。',
                    'time':'明确区分最后存活与发现死亡的时间边界。','method':'说明了近距离伤害与事先录音制造的不在场假象。'}[c['aspect']]
    f.conclude(response)
    owner = app.store.session()['id']
    with app.store.transaction() as con:con.execute('INSERT INTO games VALUES (?,?,?,?)',(s['id'],owner,json.dumps(s),time.time()))
    trace = app.gateway.trace(owner,s['id'])
    watch = spectator.view(s); ensemble = w.view(s,'A',True); ensemble['humans']=['A']
    for data in (watch,ensemble):data.update(ai_trace=trace,ai_busy=False)
    server = Server(('127.0.0.1',0),app); threading.Thread(target=server.serve_forever,daemon=True).start()
    report = {'checks':[],'page_errors':[],'completed':False}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel='msedge',headless=True,chromium_sandbox=True)
            for kind,original in (('spectator',watch),('ensemble',ensemble)):
                for width in (1440,390):
                    data = deepcopy(original); page = browser.new_page(viewport={'width':width,'height':1000},locale='zh-CN')
                    page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
                    def route(request):
                        request.fulfill(json={'csrf':'fixture','active_game':data['id'],'games':[], 'runtime_mode':'ai','gameplay':'ensemble','view':data})
                    page.route('**/api/**',route); page.goto(f'http://127.0.0.1:{server.server_port}')
                    page.wait_for_function('()=>view?.phase==="ended"&&!busy')
                    a = page.locator('#ending-review-A'); a.locator(':scope > summary').click()
                    expect(a).to_contain_text('指认正确，论证未完整成立')
                    expect(a).to_contain_text('已掌握，但最终没有引用：发现现场的原始记录')
                    expect(a).to_contain_text('过程回顾（不参与结案评分）')
                    page.locator('#ending-sources-A > summary').click()
                    expect(a).to_contain_text('工具断片封存副本')
                    b = page.locator('#ending-review-B'); b.locator(':scope > summary').click()
                    expect(b).to_contain_text('对外立场与目标'); expect(b).to_contain_text('我保留我的立场。')
                    expect(b).not_to_contain_text('未亲自到访')
                    c = page.locator('#ending-review-C'); c.locator(':scope > summary').click()
                    expect(c).to_contain_text('论证成立')
                    # Poll/render retains opened reviews and page position.
                    a.scroll_into_view_if_needed(); page.evaluate('window.scrollBy(0,280)')
                    before = page.evaluate('scrollY'); page.evaluate('render()')
                    page.wait_for_function('()=>document.querySelector("#ending-review-A").open')
                    assert page.locator('#ending-sources-A').evaluate('(n)=>n.open')
                    assert abs(page.evaluate('scrollY')-before)<2
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
                    a.screenshot(path=str(root/f'{kind}-{width}.png'))
                    # Historical result rendering adds no fabricated reasons or new grade.
                    old = deepcopy(data)
                    for p in old['results']['participants'].values():
                        r=p['reasoning'];p['reasoning']={k:r[k] for k in ('result','established','suspect')}
                    page.evaluate('(v)=>apply(v)',old)
                    expect(page.locator('#ending-review-A')).to_contain_text('保留原始结果，不重新评分')
                    # Untrusted explanations/reasons are text, never executable markup.
                    hostile = deepcopy(data)
                    hostile['results']['participants']['A']['reasoning']['aspects']['time']['reason']='<img src=x onerror="window.reviewInjection=true">'
                    page.evaluate('(v)=>apply(v)',hostile)
                    expect(page.locator('#ending-review-A')).to_contain_text('<img src=x')
                    assert page.locator('.conclusion-review img').count()==0
                    assert page.evaluate('window.reviewInjection === undefined')
                    report['checks'].append({'view':kind,'width':width,'historical':True,'scroll_retained':True,'escaped':True})
                    page.close()
            browser.close(); assert not report['page_errors']; report['completed']=True
    finally:
        server.shutdown();server.server_close();f.doCleanups()
        (root/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':main()
