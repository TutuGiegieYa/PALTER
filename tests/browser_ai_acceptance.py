"""Headless AI-runtime acceptance; --live explicitly permits real paid calls."""

import argparse
from collections import Counter
import json
from pathlib import Path
import secrets
import threading

from palter.ai_runtime import AIApplication
from palter.deepseek import DeepSeek, Settings, ROOT
from palter.server import Server
from tests.test_ai import ProviderDouble
from palter.check_ai import REQUIRED


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--database',type=Path,help='Continue a protected prior acceptance database')
    parser.add_argument('--continue-game',action='store_true',help='Restore the original browser-owned game and cancel its failed operation visibly')
    args=parser.parse_args()
    if args.continue_game and (not args.live or not args.database or not args.database.exists()):
        parser.error("--continue-game requires --live and an existing --database")
    output=args.output or ROOT/'.local/verification'/('browser-ai-live' if args.live else 'browser-ai')
    output.mkdir(parents=True,exist_ok=True,mode=0o700)
    report={'browser':'Edge headless','provider':'DeepSeek' if args.live else 'explicit provider double','completed':False,'cases':[],'page_errors':[]}
    if args.continue_game and (output/'report.json').exists():
        prior=json.loads((output/'report.json').read_text())
        report['cases']=prior.get('cases',[])
        report['explicit_recoveries']=prior.get('explicit_recoveries',[])
    provider=ProviderDouble()
    def policy(actor,data):
        invitation=next((i for i in data['invitations'] if i['to']==actor),None)
        if invitation:return 'accept:'+invitation['id']
        return 'wait'
    provider.policy=policy
    app=AIApplication(args.database or output/('run-'+secrets.token_hex(6)+'.sqlite3'),None if args.live else DeepSeek(Settings(api_key='browser-double'),provider))
    server=Server(('127.0.0.1',0),app)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    from playwright.sync_api import sync_playwright,expect
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True,chromium_sandbox=True)
            context=browser.new_context(viewport={'width':1440,'height':1000},locale='zh-CN')
            if args.continue_game:
                with app.store.transaction(False) as con:
                    session=con.execute('SELECT * FROM sessions WHERE active_game IS NOT NULL ORDER BY rowid DESC LIMIT 1').fetchone()
                    operation=con.execute("SELECT command FROM ai_operations WHERE game_id=? AND status='failed' ORDER BY started DESC LIMIT 1",(session['active_game'],)).fetchone()
                context.add_cookies([{'name':'palter_session','value':session['id'],'url':base,'httpOnly':True,'sameSite':'Strict'}])
            page=context.new_page();page.set_default_timeout(180000)
            page.on('pageerror',lambda error:report['page_errors'].append(str(error)))
            def current():
                data=page.request.get(base+'/api/session').json()
                assert data['runtime_mode']=='ai'
                view=data['view']
                if view:
                    for key in ('events','knowledge','locations','profiles','thoughts','letter_custody','dm_assessments'):
                        assert key not in view,key
                return view
            def settled():
                # A visible failure must fail acceptance, not silently reroll the story.
                page.wait_for_function('()=>!busy',timeout=180000)
                if not page.evaluate('!localStorage.getItem("palter.pending")'):
                    message=page.locator('#notice').inner_text()
                    report.setdefault('explicit_recoveries',[]).append(message)
                    # Exercise the visible recovery control with the same operation ID.
                    page.locator('#retry').click()
                    page.wait_for_function('()=>!busy',timeout=180000)
                    assert page.evaluate('!localStorage.getItem("palter.pending")'),page.locator('#notice').inner_text()
                return current()
            def click(selector):
                page.locator(selector).click();return settled()
            def speech(words):page.locator('#speech').fill(words)
            def end_chat():
                if current()['chat']:
                    speech('我们先聊到这里。')
                    click('[data-ai-kind="end_private"]')
            page.goto(base);expect(page.locator('#new-game')).to_be_enabled()
            if args.continue_game:
                if operation:
                    pending={'path':f"/api/games/{current()['id']}/commands",'body':json.loads(operation['command'])}
                    page.evaluate('(data)=>localStorage.setItem("palter.pending",JSON.stringify(data))',pending)
                    page.reload();expect(page.locator('#discard')).to_be_visible()
                    click('#discard')
                    report['cases'].append('visible cancellation of failed operation after server/browser restart; committed history retained')
            else:
                page.locator('#category').select_option('mystery')
                intro=click('#new-game')
                assert intro['phase']=='introduction' and len(intro['ai_trace']['calls'])==1
                assert intro['ai_trace']['calls'][0]['task']=='introduction'
                report['cases'].append('generated category introduction without role activity')
                reading=click('[data-command="confirm"]')
                assert reading['phase']=='reading'
                assert not any(c['task']=='character' for c in reading['ai_trace']['calls'])
                page.reload();expect(page.locator('[data-command="ready"]')).to_be_visible()
                assert current()['briefing']==reading['briefing']
                click('[data-command="ready"]')
                before=current();click('[data-command="pause"]');page.reload()
                expect(page.locator('[data-command="resume"]')).to_be_visible()
                assert len(current()['ai_trace']['calls'])==len(before['ai_trace']['calls'])
                click('[data-command="resume"]')
                report['cases'].append('reading, reload and pause gate start no role calls')
                page.locator('.private-input summary').click()
                page.locator('#thought').fill('BROWSER_PRIVATE_THOUGHT：这是我自己的担忧。')
                click('[data-ai-kind="thought"]')
                assert current()['beat']==0
                report['cases'].append('optional private thought updates only personal interpretation')
                speech('我想听听你们各自的看法。我们先互相介绍一下？')
                click('[data-ai-kind="say"]')
                assert any(c['task']=='character' and c['status']=='completed' for c in current()['ai_trace']['calls'])
                report['cases'].append('actual role-generated speech delivered with model-call trace')
                private_seen=False
                for target in 'BC':
                    view=current()
                    if view['chat']:
                        private_seen=True;break
                    if target not in view['invite_targets']:continue
                    page.locator('#invite-target').select_option(target)
                    click('[data-ai-kind="invite"]')
                    if current()['chat']:
                        private_seen=True;break
                if not private_seen and current()['invitations']:
                    click('[data-ai-answer="accept"]')
                    private_seen=bool(current()['chat'])
                assert private_seen,'No accepted private conversation; do not bypass consent'
                chat=current()['chat']['id']
                speech('这句话只在我们之间讨论。你亲眼看到了什么？')
                click('[data-ai-kind="say"]')
                assert any(c['task']=='private_dm' and c['status']=='completed' for c in current()['ai_trace']['calls'])
                with app.store.transaction(False) as con:
                    owner=con.execute('SELECT id FROM sessions WHERE active_game=?',(current()['id'],)).fetchone()[0]
                actual=app.store.state(owner,current()['id'])
                outsiders=set('ABC')-set(actual['chats'][chat]['participants'])
                assert all('这句话只在我们之间讨论' not in json.dumps(actual['observations'][c],ensure_ascii=False) for c in outsiders)
                report['cases'].append('public invitation, model consent, dedicated private DM and recipient isolation')
                end_chat()
                if not page.locator('.private-input').evaluate('(e)=>e.open'):page.locator('.private-input summary').click()
                page.locator('#intent').fill('我现在留在原地等待，不移动。')
                speech('我先留在原地，继续听听大家的说法。')
                click('[data-ai-kind="intent"]')
                click('#review')
                report['cases'].append('free-form action interpretation and acquired-record review')
            page.locator('#ai-trace-details summary').click()
            page.screenshot(path=str(output/'desktop-active.png'),full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            page.screenshot(path=str(output/'mobile-active.png'),full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'), 'Mobile horizontal overflow'
            page.set_viewport_size({'width':1440,'height':1000})
            report['cases'].append('desktop and mobile layout without horizontal overflow')
            while current()['phase']=='active':
                end_chat()
                speech('我继续留意当前发生的事。')
                page.locator('[data-action="wait"]').click()
                click('#action-form button[type="submit"]')
            ended=current()
            assert ended['phase']=='ended' and ended['outcome']['text']
            counts=Counter(c['task'] for c in ended['ai_trace']['calls'] if c['status']=='completed')
            assert REQUIRED<=set(counts),REQUIRED-set(counts)
            report['cases'].append('generated personal ending and all ten AI task kinds executed')
            page.screenshot(path=str(output/'desktop-ending.png'),full_page=True)
            page.reload();expect(page.locator('.outcome')).to_be_visible()
            assert current()['outcome']==ended['outcome']
            report['cases'].append('completed story and call receipts survive reload')
            report.update(completed=not report['page_errors'],tasks=dict(counts),calls=len(ended['ai_trace']['calls']),cost_upper_usd=ended['ai_trace']['cost_upper_usd'],
                          usage={k:sum((c['usage'] or {}).get(k) or 0 for c in ended['ai_trace']['calls']) for k in ('prompt_tokens','completion_tokens','prompt_cache_hit_tokens')})
            browser.close()
    except Exception as exc:
        report['error']={'type':type(exc).__name__,'message':str(exc)}
        raise
    finally:
        server.shutdown();server.server_close()
        (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(report,ensure_ascii=False,indent=2))
    assert report['completed']


if __name__=='__main__':main()
