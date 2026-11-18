"""Explicit paid integration check on a fresh case, never an existing player save."""

from collections import Counter
import json
from pathlib import Path
import secrets

from .investigation import InvestigationApplication
from .deepseek import ROOT
from . import case_world as w
from tests.case_acceptance import argument


def main():
    directory=ROOT/'.local/verification';directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    database=directory/('investigation-live-'+secrets.token_hex(4)+'.sqlite3')
    app=InvestigationApplication(database);owner=app.store.session()['id'];state=None
    report={'provider':'DeepSeek','completed':False,'database':str(database),
            'prefix_version':app.gateway.current_version,
            'scope':'Fresh generated case; test runner uses solution as outcome oracle, not a human playtest.'}
    try:
        state=app.create_game(owner,{'command_id':secrets.token_hex(12),'expected_game_id':None,'category':'mystery'})
        print('Preview:',state['title'],flush=True)
        def command(kind,**extra):
            nonlocal state
            state,receipt=app.command(owner,state['id'],{'command_id':secrets.token_hex(12),'expected_revision':state['revision'],'kind':kind,**extra})
            assert receipt['accepted'],receipt
            print('Completed:',kind,flush=True)
        command('confirm');fixed=state['case_hash']
        report['title']=state['title'];report['evidence_count']=len(state['case']['clues'])
        command('ready')
        command('say',target='B',text='请说说你在案发前后亲眼经历了什么，你的时间依据是什么？')
        before=len(app.gateway.trace(owner,state['id'])['calls'])
        for room in state['case']['rooms']:
            if state['locations']['A']!=room:command('act',choice='move:'+room)
            for clue in state['case']['clues']:
                if clue['location']==room and clue['id'] not in state['known']['A']:command('act',choice='inspect:'+clue['id'])
        report['inspection_model_calls']=len(app.gateway.trace(owner,state['id'])['calls'])-before
        assert report['inspection_model_calls']==0 and state['phase']=='active'
        command('notebook',text='声音和人在场可能是两件事，需要结合原始记录。',evidence_ids=state['known']['A'][:2])
        command('present',target='B',text='请结合这两份材料，解释你刚才的说法。',evidence_ids=state['known']['A'][:2])
        command('act',choice='invite:C')
        chat=w.chat_for(state,'A')
        if chat:
            command('say',target='C',text='关于你不愿公开的那段经历，你愿意说明亲眼看到的部分吗？',channel=chat['id'])
            report['private_chat']=True
            if w.chat_for(state,'A'):command('act',choice='end_private',channel=chat['id'])
        else:report['private_chat']=False
        solution=state['case']['solution']
        explanation=argument(state['case'])
        command('accuse',suspect=solution['killer'],text=explanation[:4000],evidence_ids=state['known']['A'])
        assert state['case_hash']==fixed and state['phase']=='ended'
        trace=app.gateway.trace(owner,state['id'])
        report.update(completed=state['outcome']=='established',outcome=state['outcome'],established=state['evaluation']['established'],
                      case_unchanged=True,tasks=dict(Counter(c['task'] for c in trace['calls'])),calls=len(trace['calls']),
                      failures=[{'task':c['task'],'error':c['error']} for c in trace['calls'] if c['status']!='completed'],cost_upper_usd=trace['cost_upper_usd'])
        report['setup_seconds']=next(c['latency_ms']/1000 for c in trace['calls'] if c['task']=='case_setup')
    except Exception as exc:report['error']={'type':type(exc).__name__,'message':str(exc)}
    finally:
        path=database.with_suffix('.json');path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');path.chmod(0o600)
        print(json.dumps(report,ensure_ascii=False,indent=2),flush=True);print('Report:',path,flush=True)
    if not report['completed']:raise SystemExit(1)


if __name__=='__main__':main()
