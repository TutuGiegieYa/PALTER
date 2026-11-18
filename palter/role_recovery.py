"""Stage-scoped correction continuity, without changing model decisions or receipts."""
from copy import deepcopy
import json

from . import output_contracts, memory_entries

ERRORS=(ValueError,KeyError,TypeError,IndexError,AttributeError)


def enabled(task,spec):
    # An unpaid v112 retry may adopt the fix; its paid requests remain pinned.
    return task=='ensemble_role' and bool(spec.get('role_recovery_version') or spec.get('wait_frequency_version'))


def validate_steps(steps):
    checked=[];group='decision_shape'
    try:
        iterator=iter(steps)
        group=next(iterator)
        while True:
            following=next(iterator)
            checked.append(group);group=following
    except StopIteration:return
    except ERRORS as exc:
        exc.role_checked=checked;exc.role_group=group
        raise


def failure(error,feedback,previous=None,output=None,response=None):
    previous=previous or {}
    issues={issue['group']:deepcopy(issue) for issue in previous.get('unresolved_issues',[])}
    checked=set(getattr(error,'role_checked',[]))
    if isinstance(output,dict):checked.add('json')
    if 'decision_shape' in checked:checked.update(('output','tool_calls'))
    for group in checked:issues.pop(group,None)
    # Native tool-argument JSON errors have an already decoded tool message.
    # They must retain tool calling instead of switching to a final-only reply.
    malformed=(output is None and isinstance(error,json.JSONDecodeError))
    group='json' if malformed else getattr(error,'role_group','tool_calls' if isinstance(output,dict) and '_tool_message' in output else 'output')
    if malformed:
        feedback={'code':'role_json_syntax','field':'response',
            'instruction':'Return one complete valid JSON object, with all braces and quoted strings closed. '
            'Return the final role decision using the supplied actions and received tool results; do not call more tools.'}
    feedback=deepcopy(feedback or output_contracts.feedback('ensemble_role',error))
    if feedback.get('code') in ('memory_capacity','memory_entry_sources'):
        feedback=memory_entries.correction_feedback(feedback)
    issue={k:deepcopy(v) for k,v in feedback.items() if k not in ('role_recovery_version','unresolved_issues','json_final_only','correction_instruction')}
    issue['group']=group;issues[group]=issue
    feedback.update(role_recovery_version=1,unresolved_issues=list(issues.values()),
        json_final_only=bool(previous.get('json_final_only') or malformed),
        correction_instruction='Correct every unresolved_issues item together in the complete final response. '
            'An earlier semantic error remains unresolved when JSON parsing fails or its check was not reached. '
            'Successful checks remove their prior issues. No failed action, speech or memory was committed. '
            'The current scheduling limits still apply; private reasoning updates are not scene actions.')
    return feedback


def recover(rows,validator,decode,*,revalidate=False):
    """Build only a new unpaid correction; never overwrite historical feedback."""
    feedback=None
    for row in rows:
        saved=json.loads(row['validation_feedback']) if row['validation_feedback'] else None
        if saved and saved.get('role_recovery_version')==1 and not revalidate:
            feedback=saved
            continue
        if not row['response']:continue
        response=json.loads(row['response']);output=None
        try:
            output=decode('ensemble_role',response,tools=True)
            validator(output)
        except ERRORS as error:
            feedback=failure(error,getattr(error,'feedback',None) or (None if revalidate else saved),feedback,output,response)
        else:
            if revalidate:feedback=None
        # Newly compatible old failures are not promoted to successful receipts.
        # A later fresh response must still pass all validators atomically.
    return feedback
