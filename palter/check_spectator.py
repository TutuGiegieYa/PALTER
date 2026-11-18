"""Paid acceptance: fresh all-AI games, with explicit budgets and no story hints."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import json
from pathlib import Path
import secrets
import threading
import time
from .ensemble import EnsembleApplication
from .deepseek import ROOT


def acceptance(state, error=None, pending_calls=0):
    """A finished runner is not evidence of a complete game."""
    missing=[]
    if not state:return {'passed':False,'status':'failed','missing':['game creation']}
    if state.get('phase')!='ended':missing.append('ended phase')
    submissions=state.get('submissions',{})
    if set(submissions)!=set('ABCD') or any(not submissions.get(a) for a in 'ABCD'):missing.append('four final submissions')
    if set((state.get('results') or {}).get('participants',{}))!=set('ABCD'):missing.append('four participant evaluations')
    if state.get('scenario')=='murder' and any(not (state.get('results') or {}).get('participants',{}).get(a,{}).get('reasoning',{}).get('result') for a in 'ABCD'):missing.append('four theory reviews')
    if not (state.get('ending') or {}).get('narrative'):missing.append('ending narration')
    if pending_calls:missing.append('no pending calls')
    if error or state.get('background_error'):missing.append('no unresolved error')
    passed=not missing
    return {'passed':passed,'status':'passed' if passed else 'paused' if state.get('phase')=='paused' else 'failed','missing':missing}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--count',type=int,default=10);parser.add_argument('--parallel',type=int,default=2)
    parser.add_argument('--category',choices=('murder','theft','family','council','rescue','house','archive'))
    parser.add_argument('--budget-usd',type=float,default=.10)
    parser.add_argument('--call-limit',type=int,default=128)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if not 1<=args.count<=10 or not 1<=args.parallel<=2:parser.error('count 1..10, parallel 1..2')
    if not .10<=args.budget_usd<=2 or abs(args.budget_usd*20-round(args.budget_usd*20))>1e-8:parser.error('budget-usd .10..2 in .05 increments')
    if not 128<=args.call_limit<=512 or (args.call_limit-128)%64:parser.error('call-limit 128..512 in 64-call increments')
    folder=(args.output or ROOT/'.local/verification/spectator').resolve()
    if not folder.is_relative_to((ROOT/'.local/verification').resolve()):parser.error('output must be under .local/verification')
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    database=folder/('live-'+secrets.token_hex(4)+'.sqlite3');app=EnsembleApplication(database)
    report={'completed':False,'runner_finished':False,'acceptance_passed':False,'database':str(database),'prefix':app.gateway.current_version,
            'scope':'Fresh test-owned zero-human cases. No hints, solution oracle, forced votes or resume of operational pauses. Existing bounded stage retries remain active. Operational pauses are not endings.',
            'budget_usd_per_game':args.budget_usd,'call_limit_per_game':args.call_limit,'cases':[]}
    lock=threading.Lock();path=database.with_suffix('.json')
    def save():
        temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');temporary.replace(path);path.chmod(0o600)
    save();print(json.dumps({'report':str(path),'database':str(database),'count':args.count}),flush=True)
    categories=['murder','theft','family','council','rescue','house','archive','murder','murder','murder']
    if args.category:categories=[args.category]*args.count
    def run(index):
        owner=app.store.session()['id'];state=None;start=time.monotonic();case={'index':index+1,'scenario':categories[index]}
        try:
            state=app.create_game(owner,{'command_id':'watch_live_create','expected_game_id':None,'category':categories[index],'humans':0,'opening':'interactive' if index==9 else 'after'})
            gid=state['id'];case['id']=gid
            for n in range(round((args.budget_usd-.10)/.05)):
                state,_=app.command(owner,gid,{'command_id':f'live_budget_{n}','expected_revision':state['revision'],'kind':'watch_add_budget'})
            for n in range((args.call_limit-128)//64):
                state,_=app.command(owner,gid,{'command_id':f'live_calls_{n}','expected_revision':state['revision'],'kind':'watch_add_calls'})
            for kind in ('confirm','watch_resume'):
                state,_=app.command(owner,gid,{'command_id':'live_'+kind,'expected_revision':state['revision'],'kind':kind})
            for step in range(512):
                if state['phase']!='active':break
                app.pump(gid,force=True);state=app.store.state(owner,gid)
                if step%10==0:
                    trace=app.gateway.trace(owner,gid)
                    print(json.dumps({'case':index+1,'scenario':categories[index],'step':state['watch']['steps'],'calls':len(trace['calls']),'cost':round(trace['cost_upper_usd'],5),'phase':state['phase']},ensure_ascii=False),flush=True)
            else:raise RuntimeError('Fixture exceeded its bounded scheduling limit')
            case.update(phase=state['phase'],pause_reason=state['watch']['pause_reason'],steps=state['watch']['steps'],turns=state['watch']['turns'],
                        closure=state['closure'],known_counts={a:len(v) for a,v in state['known'].items()},
                        outcome=state['outcome'],shared_success=(state.get('results') or {}).get('shared_success'),error=state['background_error'])
        except Exception as exc:
            case['error']={'type':type(exc).__name__,'message':str(exc)}
            if state:case['phase']=app.store.state(owner,state['id'])['phase']
        finally:
            pending=0
            if state:
                state=app.store.state(owner,state['id'])
                trace=app.gateway.trace(owner,state['id']);case['calls']=len(trace['calls']);case['cost_upper_usd']=trace['cost_upper_usd']
                pending=sum(c['status']=='pending' for c in trace['calls'])
                case['failed_calls']=[{'task':c['task'],'error':c['error']} for c in trace['calls'] if c['status']!='completed']
                case['models']=sorted({c['model'] for c in trace['calls']})
                case['cache_hit_tokens']=sum((c['usage'] or {}).get('prompt_cache_hit_tokens') or 0 for c in trace['calls'])
                case['cache_miss_tokens']=sum((c['usage'] or {}).get('prompt_cache_miss_tokens') or 0 for c in trace['calls'])
            case['acceptance']=acceptance(state,case.get('error'),pending)
            case['manual_recoveries']=0
            case['recovered_failed_attempts']=len(case.get('failed_calls',[])) if case['acceptance']['passed'] else 0
            case['elapsed_seconds']=round(time.monotonic()-start,2)
            with lock:report['cases'].append(case);save()
            print(json.dumps({'finished':case},ensure_ascii=False),flush=True)
        return case
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        jobs=[pool.submit(run,i) for i in range(args.count)]
        for job in as_completed(jobs):job.result()
    report['cases'].sort(key=lambda c:c['index']);report['runner_finished']=True
    report['acceptance_passed']=len(report['cases'])==args.count and all(c['acceptance']['passed'] for c in report['cases'])
    report['completed']=report['acceptance_passed']
    report['summary']={'ended':sum(c.get('phase')=='ended' for c in report['cases']),
                       'paused':sum(c.get('phase')=='paused' for c in report['cases']),
                       'passed':sum(c['acceptance']['passed'] for c in report['cases']),
                       'failed':sum(c['acceptance']['status']=='failed' for c in report['cases']),
                       'calls':sum(c.get('calls',0) for c in report['cases']),
                       'cost_upper_usd':sum(c.get('cost_upper_usd',0) for c in report['cases'])}
    save();print(json.dumps({'summary':report['summary'],'report':str(path)},ensure_ascii=False),flush=True)
    return 0 if report['acceptance_passed'] else 1


if __name__=='__main__':raise SystemExit(main())
