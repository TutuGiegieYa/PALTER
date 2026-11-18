"""Paid acceptance on fresh test-owned stories; never loads a player's save."""
import argparse
from pathlib import Path
from collections import Counter
from copy import deepcopy
import json
import secrets

from .deepseek import ROOT
from .ensemble import EnsembleApplication
from . import ensemble_world as w
from .scenario_cases import SCENARIOS
from .storage import fingerprint


def argument(case):
    clues={c['id']:c for c in case['clues']};solution=case['solution']
    def observations(aspect):return '；'.join(clues[c]['title']+'：'+clues[c]['observation'] for c in case['proofs'][aspect][0])
    bridge='完整入口、主时钟与死亡边界合并起来，只留下这一人在该时段的到场机会；其他到访发生在死亡之后。'
    if case.get('rules_version',1)>=2:
        bridge={'clock':bridge,
            'recording':'实际借还和连续保管记录将工具使用区间归于被指认者，借出完整、归还断裂的照片与致命伤内断片吻合；录音是预设播放，不能作为本人在公共区的不在场证明。',
            'substitution':'画面没有脸，不能把工作牌最初领用者当作换杯者；借还时间与换杯时刻对应，确定实际佩戴者。杯底编号把原始席位、交换过程与危险残留对应，证明是被指认者的换杯导致死者饮下危险物质。'}[case['family']]
    return ('我指认'+case['roles'][solution['killer']]['name']+'。身份与机会：'+observations('identity')+
        '。'+bridge+'\n'+
        '时间边界：'+observations('time')+'。这只能把死亡限制在'+solution['time']+'，不能假装知道精确死亡分钟。\n'+
        '方式：'+observations('method')+'。这些相互对应的材料支持'+solution['method']+'；应将目击、时钟或录音的误导和真实致死过程区分。')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--resume',type=Path);args=parser.parse_args()
    directory=ROOT/'.local/verification';directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    database=directory/('ensemble-live-'+secrets.token_hex(4)+'.sqlite3');app=EnsembleApplication(database)
    report={'completed':False,'database':str(database),'prefix_version':app.gateway.current_version,'cases':[],
            'scope':'Fresh test-owned cases. The runner uses fixed solutions as outcome oracles; no human playtest claim. Mixed-role private session explicitly arranged by the fixture.'}
    all_calls=[];prior_call_ids=set();owners={a:app.store.session()['id'] for a in w.ACTORS};state=None
    if args.resume:
        previous=json.loads(args.resume.read_text());existing=Path(previous['database']).resolve()
        if existing.parent!=directory.resolve() or not existing.name.startswith('ensemble-live-'):raise ValueError('Only isolated ensemble acceptance databases may be resumed')
        database=existing;app=EnsembleApplication(database);report=previous;report.pop('error',None);report.pop('last_case_calls',None)
        with app.store.transaction(False) as con:
            first=report['cases'][0]['id'];owners={r['actor']:r['session_id'] for r in con.execute('SELECT * FROM game_members WHERE game_id=?',(first,))}
            rows=con.execute('SELECT id,owner FROM games').fetchall()
        for row in rows:
            trace=app.gateway.trace(row['owner'],row['id']);all_calls.extend(trace['calls'])
        report['prior_attempt_cost_upper_usd']=sum(app.gateway.trace(r['owner'],r['id'])['cost_upper_usd'] for r in rows)
        report['cases_before_resume']=len(report['cases'])
        prior_call_ids={c['id'] for c in all_calls}
    def current():return app.store.state(owners['A'],state['id'])
    def cmd(a,kind,**extra):
        nonlocal state
        state=current();state,receipt=app.command(owners[a],state['id'],{'command_id':secrets.token_hex(12),'expected_revision':state['revision'],'kind':kind,**extra})
        assert receipt.get('accepted'),receipt
        return state
    def act(a,choice):
        if w.must_speak(current(),a) or current()['obligations'][a]['response']:cmd(a,'say',text='我会核对自己看到的记录，再作出决定。',target=next(b for b in w.audience(current(),a) if b!=a),channel=w.channel(current(),a))
        return cmd(a,'act',choice=choice,channel=w.channel(current(),a))
    def create(scenario,humans=4,opening='after'):
        nonlocal state
        session=app.store.require_session(owners['A'])
        state=app.create_game(owners['A'],{'command_id':secrets.token_hex(12),'expected_game_id':session['active_game'],'category':scenario,'humans':humans,'opening':opening})
        for a in w.ACTORS[1:humans]:app.join(owners[a],{'command_id':secrets.token_hex(12),'code':state['join_code']})
        cmd('A','confirm')
        if opening=='interactive':cmd('A','opening',volunteer=False,handling='inspect')
        for a in state['humans']:cmd(a,'ready')
    def inspect_all(a):
        for room in ('r1','r2','r3'):
            if current()['locations'][a]!=room:act(a,'move:'+room)
            act(a,'search');act(a,'wait')
            for choice in list(w.choices(current(),a)):
                if choice['id'].startswith('inspect:'):act(a,choice['id'])
    def close():
        for a in current()['humans']:
            if w.chat_for(current(),a):act(a,'end_private')
            cmd(a,'submit',suspect='',text='按已经发生的实际行动结算。')
    def collect(label):
        trace=app.gateway.trace(owners['A'],state['id']);all_calls.extend(trace['calls'])
        assert fingerprint(current()['case'])==current()['case_hash']
        item={'scenario':label,'id':state['id'],'title':state['title'],'phase':state['phase'],
              'family':state['case']['family'],'calls':len(trace['calls']),'cost_upper_usd':trace['cost_upper_usd'],
              'results':state.get('results'),'case_unchanged':True}
        report['cases'].append(item);print('Verified:',label,'calls',len(trace['calls']),flush=True)
    try:
        for scenario in SCENARIOS:
            if scenario in {case['scenario'] for case in report['cases']}:continue
            print('Creating:',scenario,flush=True);create(scenario)
            if scenario=='murder':
                inspect_all('A');cmd('A','thought',text='我需要比较时间边界、进入现场的机会和造成死亡的方式。')
                cmd('A','intent',text='在当前位置留意现场进展。')
                cmd('A','say',text=state['case']['roles']['B']['name']+'，请说明你亲眼经历了什么。')
                cmd('B','say',target='A',text='我会只说明自己经历过的部分，不替别人证明。')
                act('A','invite:B');inv=current()['invitations'][-1]['id'];act('B','accept:'+inv)
                cmd('A','say',target='B',channel=w.channel(current(),'A'),text='我还在核对时间记录，请把你的亲身经历和听说的事分开。')
                act('A','end_private')
                cmd('A','challenge',target='B',text='请解释你的到访时间与这些原始记录是否一致。',evidence_ids=['c1','c2'])
                cmd('B','say',target='A',text='我需要对照这两份记录，不能只凭自己记住的时间。')
                cmd('A','submit',suspect=current()['case']['solution']['killer'],text=argument(current()['case']),evidence_ids=list(current()['known']['A']))
                for a in 'BCD':cmd(a,'submit',suspect='',text='我尚未形成完整的证据链。')
                assert state['results']['participants']['A']['reasoning']['result']=='established',state['results']
                assert all(not state['results']['participants'][a]['primary'] for a in 'BCD' if a!=state['case']['solution']['killer'])
            elif scenario=='theft':
                owner=state['case']['solution']['owner'];holder=state['items']['artifact']['holder']
                if holder==owner:raise AssertionError('Theft begins already returned')
                act(holder,'transfer:artifact:'+owner);close();assert state['results']['shared_success']
            elif scenario=='family':
                for a in ('A','C'):
                    if 'c1' not in current()['known'][a]:act(a,'inspect:c1')
                    act(a,'share:c1');target='B' if a=='A' else 'D'
                    act(a,'promise:'+target);act(target,'agree:'+current()['commitments'][-1]['id'])
                close();assert state['results']['shared_success']
            elif scenario=='council':
                for a in 'ABCD':act(a,'vote:A')
                act('B','pledge:A');act('B','fund:A');close();assert state['results']['shared_success']
            elif scenario=='rescue':
                act('A','move:r2');act('A','repair');act('A','wait');act('A','move:r3');act('A','clear_route');act('A','wait')
                assert app.pump(state['id'],force=True);state=current();assert not state['background_error']
                for a in 'ABCD':
                    if current()['locations'][a]!='r3':act(a,'move:r3')
                    act(a,'collect:keepsake_'+a);act(a,'leave')
                close();assert state['results']['shared_success']
            elif scenario=='house':
                act('A','move:r2');act('A','switch:0')
                for a in 'ABCD':
                    act(a,'move:r3');act(a,'collect:keepsake_'+a);act(a,'move:r1');act(a,'leave')
                close();assert state['results']['shared_success']
            elif scenario=='archive':
                act('A','move:r3')
                for i,value in enumerate(state['case']['solution']['dials']):act('A',f'dial:{i}:{value}')
                act('A','collect:archive_1');act('A','collect:archive_2');close();assert state['results']['shared_success']
            collect(scenario)
        previous_id=app.store.require_session(owners['A'])['active_game']
        previous=app.store.state(owners['A'],previous_id) if previous_id else None
        if args.resume and previous and previous['opening']=='interactive' and previous['phase']=='active' and previous['background_error']:
            state=previous;queue=deepcopy(state['agenda'])
            cmd('A','cancel_pending',operation_id=state['background_error']['operation_id'])
            # This test fixture restores the uncommitted opportunity under a NEW
            # operation/version. Neither the failed operation nor past facts change.
            with app.store.transaction() as con:
                old=app.store.load(con,owners['A'],state['id']);work=deepcopy(old);work['agenda']=queue
                work['revision']+=1;app.store.save(con,work,old)
            report.setdefault('explicit_fixture_recoveries',[]).append({'game':state['id'],'version':app.gateway.current_version})
        else:
            create('murder',humans=1,opening='interactive')
            # Arrange one consented AI-only private session in this fresh test fixture.
            with app.store.transaction() as con:
                old=app.store.load(con,owners['A'],state['id']);work=deepcopy(old)
                w.apply_choice(work,'B','invite:C');w.apply_choice(work,'C','accept:'+work['invitations'][-1]['id'])
                work['revision']+=1;app.store.save(con,work,old)
        for _ in range(6):
            app.pump(state['id'],force=True);state=current();assert not state['background_error'],state['background_error']
        assert any(c['turns'] for c in state['chats'].values())
        assert not any(o.get('channel','public')!='public' for o in state['observations']['A'])
        collect('mixed opening and private AI activity')
        all_calls=list({c['id']:c for c in all_calls}.values())
        failures=[{'task':c['task'],'error':c['error']} for c in all_calls if c['status']!='completed']
        tasks=dict(Counter(c['task'] for c in all_calls));required={'ensemble_'+s for s in ('preview','setup','opening','role','address','action','memory','dm','world','ending')}|{'case_theory'}
        assert required<=set(tasks),required-set(tasks)
        new_failures=[c for c in app.gateway.trace(owners['A'],state['id'])['calls'] if c['status']!='completed' and c['id'] not in prior_call_ids]
        assert not new_failures,new_failures
        report.update(completed=True,verified_prefix_version=app.gateway.current_version,tasks=tasks,calls=len(all_calls),models=sorted({c['model'] for c in all_calls}),failures=failures,
            cost_upper_usd=sum(c['cost_upper_usd'] or 0 for c in all_calls))
        usage=[c['usage'] for c in all_calls if c['usage']]
        report['usage']={k:sum(u.get(k,0) or 0 for u in usage) for k in ('prompt_tokens','completion_tokens','prompt_cache_hit_tokens','prompt_cache_miss_tokens')}
    except Exception as exc:report['error']={'type':type(exc).__name__,'message':str(exc)}
    finally:
        if state and not any(c['id']==state['id'] for c in report['cases']):
            trace=app.gateway.trace(owners['A'],state['id']);report['last_case_calls']=trace['calls']
        path=database.with_suffix('.json');path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');path.chmod(0o600)
        print('Completed:',report['completed'],'Report:',path,flush=True)
        if 'error' in report:print(report['error'],flush=True)
    if not report['completed']:raise SystemExit(1)


if __name__=='__main__':main()
