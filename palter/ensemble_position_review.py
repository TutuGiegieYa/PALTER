"""Post-game outward-position assessment; objective scoring stays in the engine."""
from copy import deepcopy

from . import ensemble_context as context, ensemble_review
from .ai_runtime import references, text


class PositionReviewError(ValueError):
    def __init__(self, message):
        super().__init__(message)
        self.feedback = {'code': 'position_review_contract', 'detail': message,
            'instruction': 'Return position_summary and evidence_checks only. Each check has statement, '
            'status (consistent, contradicted, unresolved), reason and source_ids. Quote an exact '
            'substring of the submitted explanation. Cite only supplied final_evidence or '
            'cited_testimony IDs; consistent/contradicted checks need original evidence. '
            'Do not return grades, winners or identity/time/method claims.'}


def validate(out, explanation, originals, testimony):
    try:
        if set(out) != {'position_summary', 'evidence_checks'}:
            raise ValueError('position review fields')
        text(out['position_summary'], 500)
        checks = out['evidence_checks']
        if not isinstance(checks, list) or len(checks) > 6:
            raise ValueError('at most six selected evidence checks')
        for check in checks:
            if set(check) != {'statement', 'status', 'reason', 'source_ids'}:
                raise ValueError('evidence check fields')
            text(check['statement'], 240); text(check['reason'], 300)
            if check['statement'] not in explanation:
                raise ValueError('statement must quote the actual submitted explanation')
            if check['status'] not in ('consistent', 'contradicted', 'unresolved'):
                raise ValueError('evidence check status')
            references(check['source_ids'], originals | testimony, maximum=None)
            if check['status'] != 'unresolved' and not originals.intersection(check['source_ids']):
                raise ValueError('factual support or contradiction requires supplied original evidence')
    except (ValueError, KeyError, TypeError) as exc:
        raise PositionReviewError(str(exc)) from None


def evaluate(state, actor, call, evaluations):
    # The locked structured choice selects admission. Never infer it from private
    # self-knowledge or rewrite an ambiguous outward explanation into a confession.
    submission = deepcopy(state['submissions'].get(actor) or {})
    if submission.get('suspect') == actor:
        result = ensemble_review.evaluate(state, actor, call, review_mode='admission')
        result.update(review_version=2, assessment_type='admission')
        return result

    from .ensemble_world import name
    known = state['known'][actor]
    cited = list(dict.fromkeys(cid for cid in submission.get('evidence_ids', []) if cid in known))
    testimony = context.testimony(state, actor, submission.get('testimony_ids', []))
    own_sources = [deepcopy(known[cid]) for cid in cited]
    # These are end-of-game evaluator inputs, never added to the role's knowledge.
    # Include other submissions' actually used originals, not their entire holdings.
    records = {r['id']: deepcopy(r) for r in own_sources}
    findings = []
    for other, review in evaluations.items():
        used = set(review.get('argument_sources', []))
        for record in review.get('sources', []):
            if record['id'] in used:records.setdefault(record['id'], deepcopy(record))
        for aspect, assessment in review.get('aspects', {}).items():
            if assessment['established']:
                findings.append({'actor': other, 'name': name(state, other), 'aspect': aspect,
                    'reason': assessment['reason'], 'source_ids': assessment['matched_evidence_ids']})
    explanation = submission.get('explanation', '')
    out = None
    if explanation.strip():
        from . import temporal_facts
        data = {'review_mode': 'concealment', 'review_version': 2,
            'subject': {'id': actor, 'name': name(state, actor)},
            'characters': {a: name(state, a) for a in state['case']['roles']},
            'submitted_suspect': submission.get('suspect'), 'explanation': explanation,
            'cited_evidence_ids': cited, 'cited_testimony': testimony,
            'final_evidence': list(records.values()), 'established_findings': findings,
            'case_established_by_others': any(r.get('result') == 'established' for r in evaluations.values()),
            'temporal_facts': temporal_facts.project(list(records.values()))}
        if 'aspects' in submission:data['submitted_aspects'] = deepcopy(submission['aspects'])
        out, _ = call('theory_' + actor, 'ensemble_theory', None, data,
            lambda response: validate(response, explanation, set(records), {t['id'] for t in testimony}), actor)
    return {'review_version': 2, 'perspective': 'concealment', 'assessment_type': 'position',
        'result': 'position_recorded' if submission else 'unresolved', 'established': [],
        'suspect': submission.get('suspect'), 'submission': submission,
        'sources': own_sources, 'testimony': testimony, 'argument_sources': [],
        'position_assessment': deepcopy(out), 'comparison_sources': list(records.values())}
