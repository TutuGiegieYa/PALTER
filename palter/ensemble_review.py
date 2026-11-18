"""Versioned final-argument grading and a separate, factual process review.

Equivalence is a property of a fixed proof premise, never a rewrite of a record,
acquisition or testimony. These helpers do not alter objective/win rules.
"""
from copy import deepcopy

from . import ensemble_context as context, exploration

ASPECTS = ('identity', 'time', 'method')


def premise(case, source):
    equivalents = case.get('evidence_equivalents', {})
    seen = set()
    while source in equivalents:
        if source in seen:
            return min(seen)
        seen.add(source)
        source = equivalents[source]
    return source


def premises(case, sources):
    return {premise(case, source) for source in sources}


def available_routes(case, sources):
    # Supply the evaluator with the IDs actually cited, including mixed copies.
    actual = {}
    for source in sources:
        actual.setdefault(premise(case, source), source)
    return {aspect: [list(dict.fromkeys(actual[premise(case, cid)] for cid in route))
                     for route in routes if premises(case, route) <= actual.keys()]
            for aspect, routes in case['proofs'].items()}


def validate_response(out, allowed):
    from .ai_runtime import references, text
    claims = out['claims']
    if not isinstance(claims, list) or len(claims) != 3:
        raise ValueError('three aspect reviews required')
    if {c['aspect'] for c in claims} != set(ASPECTS):
        raise ValueError('one review per aspect required')
    for claim in claims:
        if type(claim['supported']) is not bool:
            raise ValueError('claim supported')
        text(claim['reason'], 240)
        references(claim['evidence_ids'], allowed, maximum=None)
    references(out['argument_sources'], allowed, maximum=None)


def evaluate(state, actor, call, review_mode=None):
    from .ensemble_world import perspective
    case = state['case']; known = state['known'][actor]
    # Even an investigator's private belief must not replace a final submission.
    submission = deepcopy(state['submissions'].get(actor) or {})
    suspect = submission.get('suspect'); explanation = submission.get('explanation', '')
    cited = list(dict.fromkeys(cid for cid in submission.get('evidence_ids', []) if cid in known))
    testimony = context.testimony(state, actor, submission.get('testimony_ids', []))
    allowed = set(cited) | {t['id'] for t in testimony}
    focus = perspective(state, actor)
    out = {'claims': [], 'argument_sources': []}
    evaluated = bool(suspect and explanation)
    if evaluated:
        data = {'review_version': 1, 'perspective': focus,
                'submitted_suspect': suspect, 'explanation': explanation,
                'cited_evidence': [deepcopy(known[cid]) for cid in cited],
                'cited_testimony': testimony, 'solution': case['solution'],
                'proof_routes': available_routes(case, cited)}
        if review_mode:
            data['review_mode']=review_mode
        if state.get('structured_conclusion_version'):
            from . import temporal_facts
            if 'aspects' in submission:data['submitted_aspects']=deepcopy(submission['aspects'])
            data['temporal_facts']=temporal_facts.project([known[cid] for cid in cited])
        out, _ = call('theory_' + actor, 'ensemble_theory', None, data,
                      lambda response: validate_response(response, allowed), actor)

    # Heard claims stay useful semantic sources, but do not become documents.
    used = set(out['argument_sources']) & set(cited)
    used_facts = premises(case, used); cited_facts = premises(case, cited)
    known_facts = premises(case, known)
    definitions = {c['id']: c for c in case['clues']}
    aspect_reviews = {}; established = []
    claims = {c['aspect']: c for c in out['claims']}
    for aspect in ASPECTS:
        claim = claims.get(aspect, {})
        routes = case['proofs'].get(aspect, [])
        covered = any(premises(case, route) <= used_facts for route in routes)
        supported = bool(claim.get('supported'))
        identity_matches = suspect == case['solution']['killer'] if aspect == 'identity' and suspect else None
        passed = supported and covered and identity_matches is not False
        if passed:
            established.append(aspect)
        # Show one nearest valid route, not every alternative as a requirement.
        route = min(routes, key=lambda r: (len(premises(case, r) - used_facts),
                                           len(premises(case, r) - known_facts)), default=[])
        gaps = []
        for fact in dict.fromkeys(premise(case, cid) for cid in route):
            if fact in used_facts:
                continue
            choices = [cid for cid in definitions if premise(case, cid) == fact]
            held = [cid for cid in choices if cid in known]
            status = 'not_used' if fact in cited_facts else 'not_cited' if fact in known_facts else 'not_acquired'
            gaps.append({'status': status, 'alternatives': [
                {'id': cid, 'title': definitions[cid]['title']} for cid in (held or choices)]})
        aspect_reviews[aspect] = {
            'evaluated': evaluated, 'established': passed,
            'identity_matches': identity_matches,
            'semantic_supported': supported if evaluated else None,
            'proof_covered': covered if evaluated else None,
            'reason': claim.get('reason') or ('未作明确指认，本项未评估。' if not suspect else '没有提交最终说明，本项未评估。'),
            'evidence_ids': claim.get('evidence_ids', []), 'gaps': gaps if evaluated else [],
            'matched_evidence_ids': [cid for cid in cited if cid in used and premise(case, cid) in premises(case, route)],
        }
    result = ('unresolved' if not suspect else 'incorrect' if suspect != case['solution']['killer']
              else 'established' if len(established) == 3 else 'unproven')
    return {'result': result, 'established': established, 'suspect': suspect,
            'review_version': 1, 'perspective': focus,
            'accusation_correct': None if not suspect else suspect == case['solution']['killer'],
            'submission': submission, 'aspects': aspect_reviews,
            'sources': [deepcopy(known[cid]) for cid in cited], 'testimony': testimony,
            'argument_sources': out['argument_sources']}


def attach_process(state):
    """Run after objective scoring; no effect on the score or the model request."""
    from .ensemble_world import public_disclosure
    result = state['results']
    for actor, participant in result['participants'].items():
        review = participant['reasoning']
        if review.get('review_version') not in (1, 2):
            continue
        known = state['known'][actor]; case = state['case']
        key_records = set().union(*(set(route) for route in case['proofs']['identity']))
        contributions = [cid for cid in state['contributions'][actor] if cid in key_records]
        sources = list(dict.fromkeys(contributions))
        profile = case['roles'][actor]; objective = profile['objectives'][0]['kind']
        active = bool(state['contributions'][actor])
        isolated_investigator = result.get('scoring_version') == 2 and actor != case['solution']['killer']
        if objective == 'avoid':
            primary_reason = ('有人提交了被证据支持的完整结论，避免定案的目标未达成。' if result['shared_success'] else
                              '尚无完整结论被证据支持，且有实际参与贡献，避免定案的目标达成。' if active else
                              '尚无完整结论被证据支持，但没有实际参与贡献，主要目标未达成。')
        elif review['result'] == 'established':
            primary_reason = '自己的最终指认、时间与作案方式均有论述和证据支持。'
        elif participant['primary']:
            primary_reason = ('非凶手玩家已完成定案；自己的关键材料贡献和最终论证符合协作达成条件。' if isolated_investigator else
                              '集体已完成定案；自己的关键材料贡献和最终论证符合协作达成条件。')
        else:
            primary_reason = ('自己的最终论证尚未完整成立，也未满足非凶手玩家之间的协作达成条件。' if isolated_investigator else
                              '自己的最终论证尚未完整成立，也未同时满足集体定案与协作贡献条件。')
        secondary = profile['objectives'][1]
        exposed = set(state['public_evidence']) | {d['evidence_id'] for d in state['disclosures'] if public_disclosure(d)}
        target = 's' + secondary['target']
        if secondary['kind'] == 'protect':
            personal_reason = ('要保护的秘密已公开。' if target in exposed else
                               '要保护的秘密未公开，且有实际参与贡献。' if active else
                               '要保护的秘密未公开，但没有实际参与贡献。')
        else:
            personal_reason = ('已完成目标要求的秘密披露。' if participant['personal'] else '未完成目标要求的秘密披露。')
        own_speeches = [e for e in state['events'] if e['kind'] == 'testimony' and e['actor'] == actor]
        origins = exploration.acquisitions(state, actor)
        review['process'] = {
            'known_records': len(known),
            'personally_acquired': sum(o['method'] in ('personal_inspection', 'personal_collection', 'personal_copy') for o in origins.values()),
            'received_records': sum(o['method'] in ('presentation', 'physical_receipt') for o in origins.values()),
            'directed_utterances': sum(bool(e['target']) for e in own_speeches),
            'contributed_records': [{'id': cid, 'title': known[cid]['title']} for cid in sources if cid in known],
            'unvisited_rooms': [{'id': r['room_id'], 'name': r['name']} for r in exploration.for_role(state, actor) if r['status'] == 'unvisited'],
            'primary_reason': primary_reason, 'personal_reason': personal_reason,
            'truth_established': result['investigation_success'] if isolated_investigator else result['shared_success'],
        }
        if review.get('review_version') == 2 and review.get('perspective') == 'concealment':
            review['exposure'] = {
                'established': result['shared_success'],
                'established_by': [{'actor': a, 'name': p['name'], 'self_submission': a == actor}
                                   for a, p in result['participants'].items()
                                   if p['reasoning'].get('result') == 'established'],
            }
