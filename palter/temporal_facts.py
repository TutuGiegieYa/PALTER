"""Exact compiled timing, independent of player speech and model arithmetic."""
from copy import deepcopy
from itertools import combinations


def point(label, minute, basis='master_clock'):
    if type(minute) is not int or minute < 0:raise ValueError('absolute clock minute')
    return {'kind':'point','label':label,'clock_basis':basis,'minute':minute}


def interval(label, start, end, basis='master_clock'):
    if any(type(n) is not int or n < 0 for n in (start,end)) or end < start:
        raise ValueError('ordered absolute minutes required; include day offset across midnight')
    return {'kind':'interval','label':label,'clock_basis':basis,
            'start_minute':start,'end_minute':end,'duration_minutes':end-start}


def compile_case(case, lower, crime, upper, offset):
    """Called only while compiling new immutable cases, from original numbers."""
    h={r['id']:r for r in case['history']};c={r['id']:r for r in case['clues']}
    for key,label,n in [('alive','last_verified_alive',lower),('crime','actual_crime',crime),
                        ('dead','first_confirmed_dead',upper),('late','later_arrival',upper+3)]:
        h[key]['temporal']=[point(label,n)]
    c['c1']['temporal']=[point('last_verified_alive',lower)]
    c['c2']['temporal']=[point('first_confirmed_dead',upper)]
    for index,actor in enumerate(a for a in case['arrival'] if a!=case['solution']['killer']):
        value=[point('post_discovery_visit',upper+index*3)]
        h['visit_'+actor]['temporal']=deepcopy(value)
        c['c'+str((5,6,13)[index])]['temporal']=deepcopy(value)
    family=case['family']
    if family=='clock':
        c['c3']['temporal']=[point('entry_overlay',crime+offset,'entrance_overlay')]
        c['c4']['clock_calibration']={'from':'entrance_overlay','to':'master_clock','subtract_minutes':offset}
        c['c10']['temporal']=[point('recorded_entry',crime)]
    else:
        label='playback' if family=='recording' else 'cup_exchange'
        c['c3']['temporal']=[point('public_voice' if family=='recording' else label,crime)]
        c['c4' if family=='recording' else 'c10']['temporal']=[point(label,crime)]
        custody=interval('tool_custody' if family=='recording' else 'badge_custody',lower-9,lower+9)
        for record in (h['handover'],c['c9'],c['c14']):record['temporal']=[deepcopy(custody)]
        if family=='recording':
            c['c10']['temporal']=[point('intact_at_loan',lower-9),point('notched_at_return',lower+9)]

    if case.get('rules_version',0)>=5:
        # Time refers to a specific person/event, never to an unnamed voice.
        for key in ('alive','dead'):
            h[key]['temporal'][0]['subject']=case['victim']
        h['crime']['temporal'][0]['subject']=case['solution']['killer']
        c['c1']['temporal'][0]['subject']=case['victim'];c['c2']['temporal'][0]['subject']=case['victim']
        if family=='recording':
            for key in ('c3','c4'):c[key]['temporal'][0]['subject']=case['solution']['killer']


def project(records):
    """Derive only from explicitly supplied originals; never parse their prose."""
    facts=[];calibrations=[]
    for record in records:
        for value in record.get('temporal',[]):
            fact={**deepcopy(value),'source_ids':[record['id']]}
            prior=next((f for f in facts if {k:v for k,v in f.items() if k!='source_ids'}==value),None)
            if prior:
                if record['id'] not in prior['source_ids']:prior['source_ids'].append(record['id'])
            else:facts.append(fact)
        if 'clock_calibration' in record:
            calibrations.append({**deepcopy(record['clock_calibration']),'source_ids':[record['id']]})
    for fact in list(facts):
        for calibration in calibrations:
            if fact['kind']=='point' and fact['clock_basis']==calibration['from']:
                corrected=point(fact['label']+'_calibrated',fact['minute']-calibration['subtract_minutes'],calibration['to'])
                facts.append({**corrected,'source_ids':fact['source_ids']+calibration['source_ids']})
    alive=next((f for f in facts if f['label']=='last_verified_alive'),None)
    dead=next((f for f in facts if f['label']=='first_confirmed_dead'),None)
    if alive and dead and alive['clock_basis']==dead['clock_basis'] and alive['minute']<=dead['minute']:
        facts.append({**interval('death_bounds_not_exact_death',alive['minute'],dead['minute'],alive['clock_basis']),
                      'start_inclusive':False,'end_inclusive':True,
                      'source_ids':list(dict.fromkeys(alive['source_ids']+dead['source_ids']))})
    comparisons=[]
    for a,b in combinations([f for f in facts if f['kind']=='interval'],2):
        if a['clock_basis']!=b['clock_basis']:continue
        start=max(a['start_minute'],b['start_minute']);end=min(a['end_minute'],b['end_minute'])
        comparisons.append({'left':a['label'],'right':b['label'],'clock_basis':a['clock_basis'],
            'source_ids':list(dict.fromkeys(a['source_ids']+b['source_ids'])),
            'left_contains_right':a['start_minute']<=b['start_minute'] and a['end_minute']>=b['end_minute'],
            'right_contains_left':b['start_minute']<=a['start_minute'] and b['end_minute']>=a['end_minute'],
            'overlap':interval('overlap_only',start,end,a['clock_basis']) if start<=end else None})
    return {'facts':facts,'comparisons':comparisons,'calibrations':calibrations}


def for_role(state,actor):
    known=state['case']['roles'][actor]['knows']
    return project([f for f in state['case']['history'] if f['id'] in known]+list(state['known'][actor].values()))
