"""Browser acceptance of a fresh investigation. --live explicitly uses DeepSeek."""

import argparse
from collections import Counter
import json
from pathlib import Path
import secrets
import threading

from palter.investigation import InvestigationApplication
from palter.deepseek import DeepSeek,Settings,ROOT
from palter.server import Server
from tests.test_investigation import CaseProvider
from tests.case_acceptance import argument


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true');args=parser.parse_args()
    directory=ROOT/'.local/verification'/('browser-investigation-live' if args.live else 'browser-investigation')
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    database=directory/('run-'+secrets.token_hex(4)+'.sqlite3')
    provider=CaseProvider()
    app=InvestigationApplication(database,None if args.live else DeepSeek(Settings(api_key='browser-fixture'),provider))
    server=Server(('127.0.0.1',0),app);threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    report={'provider':'DeepSeek' if args.live else 'explicit provider double','completed':False,'page_errors':[],'checks':[],
            'database':str(database),'prefix_version':app.gateway.current_version,
            'scope':'Fresh test game; outcome assertion uses the test-runner solution oracle.'}
    from playwright.sync_api import sync_playwright,expect
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(channel='msedge',headless=True,chromium_sandbox=True)
            page=browser.new_page(viewport={'width':1440,'height':1000},locale='zh-CN')
            page.set_default_timeout(90000 if args.live else 12000)
            page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
            page.on('dialog',lambda d:d.accept())
            def current():return page.request.get(base+'/api/session').json()['view']
            def settled():
                page.wait_for_function('()=>!busy',timeout=600000 if args.live else 15000)
                assert page.evaluate('!localStorage.getItem("palter.pending")'),page.locator('#notice').inner_text()
                assert not report['page_errors'],report['page_errors']
                return current()
            def click(selector):page.locator(selector).click();return settled()
            page.goto(base);expect(page.locator('#new-game')).to_be_enabled()
            intro=click('#new-game');assert intro['gameplay']=='investigation'
            assert '6 个行动节拍' not in page.locator('#app').inner_text()
            reading=click('[data-case-command="confirm"]');assert reading['phase']=='reading'
            assert all(k not in reading for k in ('case','solution','proofs','case_hash'))
            initial_calls=len(reading['ai_trace']['calls']);page.reload();settled()
            assert len(current()['ai_trace']['calls'])==initial_calls
            click('[data-case-command="ready"]')
            page.locator('#case-target').select_option('B');page.locator('#case-speech').fill('请说说案发时你亲眼经历了什么？')
            click('[data-case-send="say"]');report['checks'].append('real interface question and attributed reply')
            for room in current()['rooms']:
                if current()['scene']['id']!=room['id']:click('[data-case-choice="move:'+room['id']+'"]')
                for choice in list(current()['options']):
                    if choice['id'].startswith('inspect:'):click('[data-case-choice="'+choice['id']+'"]')
            assert current()['phase']=='active' and current()['beat']>6
            assert len(current()['evidence'])>=8
            report['checks'].append('all evidence inspectable; no fixed-act ending')
            page.locator('[data-case-evidence]').first.check()
            page.locator('#case-speech').fill('请结合这份材料说明你的说法。')
            click('[data-case-send="present"]')
            click('[data-case-tab="notes"]');page.locator('#case-notes').fill('时间和不在场证明需要分别核对。')
            count=len(current()['ai_trace']['calls']);click('[data-case-send="notebook"]')
            assert len(current()['ai_trace']['calls'])==count
            page.reload();settled();click('[data-case-tab="notes"]')
            expect(page.locator('#case-notes')).to_have_value('时间和不在场证明需要分别核对。')
            click('[data-case-control="pause"]');count=len(current()['ai_trace']['calls'])
            page.reload();settled();assert current()['phase']=='paused'
            assert len(current()['ai_trace']['calls'])==count
            click('[data-case-control="resume"]')
            report['checks'].append('private notebook/reload and pause without extra model calls')
            click('[data-case-tab="statements"]')
            page.locator('[data-case-followup]').first.click()
            expect(page.locator('#case-speech')).not_to_have_value('')
            click('[data-case-choice="invite:C"]')
            chat=current()['chat']
            if chat:
                page.locator('#case-target').select_option('C');page.locator('#case-speech').fill('这段谈话只在我们之间，请说说你的亲历。')
                click('[data-case-send="say"]')
                report['checks'].append('consented private chat with scoped DM')
                if current()['chat']:click('[data-case-choice="end_private"]')
            click('[data-case-tab="evidence"]')
            page.screenshot(path=str(directory/'desktop-investigation.png'),full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.screenshot(path=str(directory/'mobile-investigation.png'),full_page=True)
            page.set_viewport_size({'width':1440,'height':1000})
            for clue in current()['evidence']:page.locator('[data-case-evidence="'+clue['id']+'"]').check()
            with app.store.transaction(False) as con:
                row=con.execute('SELECT state FROM games WHERE id=?',(current()['id'],)).fetchone()
                state=json.loads(row['state'])
            solution=state['case']['solution']
            explanation=argument(state['case'])
            page.locator('#case-final summary').click();page.locator('#case-suspect').select_option(solution['killer'])
            page.locator('#case-argument').fill(explanation[:4000]);ended=click('[data-case-send="accuse"]')
            assert ended['outcome']=='established',ended['resolution']['evaluation']
            assert ended['phase']=='ended'
            page.screenshot(path=str(directory/'ending.png'),full_page=True)
            page.reload();settled();assert current()['outcome']=='established'
            report['checks'].append('evidence-backed final accusation, full reveal and persisted ending')
            report.update(completed=True,tasks=dict(Counter(c['task'] for c in ended['ai_trace']['calls'])),calls=len(ended['ai_trace']['calls']),cost_upper_usd=ended['ai_trace']['cost_upper_usd'])
            report['setup_seconds']=next(c['latency_ms']/1000 for c in ended['ai_trace']['calls'] if c['task']=='case_setup')
            browser.close()
    except Exception as exc:report['error']={'type':type(exc).__name__,'message':str(exc)}
    finally:
        server.shutdown();server.server_close()
        path=directory/'report.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');path.chmod(0o600)
        archived_report=database.with_suffix('.json');archived_report.write_text(path.read_text());archived_report.chmod(0o600)
        print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    if not report['completed']:raise SystemExit(1)


if __name__=='__main__':main()
