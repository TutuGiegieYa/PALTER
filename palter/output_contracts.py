"""Actionable validation feedback; never rewrite an accepted or rejected reply."""
from .delta_updates import ContractError


def _actual(value,include_text=True):
    """Bound diagnostics, not accepted values or citation lists."""
    kind=('null' if value is None else 'boolean' if isinstance(value,bool) else
          'string' if isinstance(value,str) else 'array' if isinstance(value,list) else
          'object' if isinstance(value,dict) else 'number')
    result={'type':kind}
    if isinstance(value,str):
        result['characters']=len(value)
        if include_text:
            if len(value)<=160:result['value']=value
            else:result.update(preview=value[:160],truncated=True)
    elif isinstance(value,(list,dict)):result['size']=len(value)
    else:result['value']=value
    return result


def _receipt(error,expected,violations):
    """One task-independent shape generated from the failed constraint."""
    error.feedback['validation_receipt']={
        'version':1,'value_basis':'expanded_value','rejected_update_applied':False,
        'expected':expected,'violations':violations[:8],
        'violation_count':len(violations),'omitted_violations':max(0,len(violations)-8)}
    error.feedback['instruction']=(
        'Correct the reported violations using the expected constraints and authorized context; '
        'return the complete response required by the task. Do not invent replacement values. '
        'The rejected update was not saved. Paths and indices refer to the expanded value. '
        'For a patch, omitted fields retain saved values: omit an invalid new addition from the '
        'rejected draft, and use a remove operation only for a member of the saved list. '
        'A permitted alternative field does not require moving the value there. '
        'Only diagnostics are sampled; omitted violations still need correction.')
    return error


def text(value,field,maximum,empty=False):
    if not isinstance(value,str) or len(value)>maximum or (not empty and not value.strip()):
        error=ContractError(field,f'Use a string of at most {maximum} characters'+(' (empty is permitted).' if empty else ' with nonempty text.'))
        error.feedback.update(maximum_characters=maximum,actual_characters=len(value) if isinstance(value,str) else None)
        reason=('type_mismatch' if not isinstance(value,str) else
                'text_too_long' if len(value)>maximum else 'nonblank_required')
        raise _receipt(error,{'type':'string','max_characters':maximum,'allow_blank':empty},
            [{'path':field,'reason':reason,'actual':_actual(value,include_text=False)}])


def object_fields(value,allowed,field,required=()):
    """Report object permissions before interpreting disallowed nested values."""
    violations=[]
    if not isinstance(value,dict):
        violations.append({'path':field,'reason':'type_mismatch','actual':_actual(value)})
    else:
        for key in sorted(set(value)-set(allowed)):
            violations.append({'path':field+'.'+key,'reason':'field_not_allowed','actual':_actual(value[key])})
        for key in sorted(set(required)-set(value)):
            violations.append({'path':field+'.'+key,'reason':'required_field_missing'})
    if violations:
        error=ContractError(field,'Use only fields allowed for this response.')
        raise _receipt(error,{'type':'object','allowed_fields':sorted(allowed),'required_fields':sorted(required)},violations)


def references(value,known,field,other_fields=None,*,source_kinds=None,expected_kinds=None):
    if not isinstance(value,list) or any(not isinstance(i,str) or i not in known for i in value):
        error=ContractError(field,'Use an array of source IDs actually authorized for this field; there is no citation-count cap. Do not use unread targets or another role\'s observation IDs.')
        expected={'type':'array','items':{'type':'string','source_scope':'authorized_for_field'}}
        if expected_kinds is not None:expected['items']['source_kinds']=list(expected_kinds)
        violations=[]
        if isinstance(value,list):
            error.feedback['invalid_source_indexes']=[n for n,i in enumerate(value) if not isinstance(i,str) or i not in known]
            for n in error.feedback['invalid_source_indexes']:
                identity=value[n];actual=_actual(identity)
                reason='type_mismatch' if not isinstance(identity,str) else 'source_not_authorized_for_field'
                if isinstance(identity,str) and source_kinds is not None:
                    actual['source_kind']=source_kinds.get(identity,'unavailable')
                    if identity in source_kinds and expected_kinds is not None and source_kinds[identity] not in expected_kinds:
                        reason='source_kind_mismatch'
                alternatives=[target for target,ids in (other_fields or {}).items()
                              if isinstance(identity,str) and identity in ids]
                violations.append({'path':f'{field}[{n}]','actual':actual,'reason':reason,
                                   'permitted_fields':alternatives})
            if other_fields:
                error.feedback['misplaced_sources']=[{'index':n,'id':identity,'permitted_field':target}
                    for n,identity in enumerate(value) if isinstance(identity,str) and identity not in known
                    for target,ids in other_fields.items() if identity in ids]
        else:violations=[{'path':field,'reason':'type_mismatch','actual':_actual(value)}]
        raise _receipt(error,expected,violations)


def disclosure_sources(state, speeches):
    """Authorization at the instant of speech, before the following action."""
    return {speech['id']: sorted({c['id'] for c in speech['facts']['speaker_knowledge']['evidence']}
            | set(state['case']['roles'][speech['actor']]['knows'])) for speech in speeches}


class DisclosureError(ValueError):
    def __init__(self,index,event_id,allowed):
        super().__init__('disclosure source: use the speaker knowledge snapshot at speech time')
        self.feedback={'code':'disclosure_source','field':f'disclosures[{index}].evidence_id',
            'event_id':event_id,'allowed_evidence_ids':allowed,
            'instruction':'Return the complete DM response. For this disclosure, cite only a listed source '
            'whose content the utterance actually discloses, or omit this disclosure. Speech happens before '
            'the accompanying inspect/share/move action. A document learned by that later action is not '
            'authorized retroactively. Sources visible in event-recipient contexts or the shared source pool '
            'do not extend this utterance snapshot. A spoken intention to inspect/show is not an actual '
            'presentation. Preserve the separate event_decisions source rules and do not rewrite speech.'}


def feedback(task,error):
    """Fallback for still-unstructured contract failures in an existing retry."""
    detail=str(error) if isinstance(error,ValueError) else type(error).__name__
    result={'code':'output_contract','task':task,'validation_error':detail[:240],
        'instruction':'The previous output failed validation; nothing from this attempt was applied. '
        'Correct the indicated contract problem and return the complete coherent response required by this task. '
        'Preserve source permissions and do not invent facts or perform self-review.'}
    if task=='ensemble_role':
        result['instruction']+=' For an existing belief/strategy patch, omitted fields retain their prior values. '
        result['instruction']+='Citation lists have no count cap; retain only references supporting the current reasoning and remove obsolete ones explicitly. '
        result['instruction']+='Choose an exact available action tuple. A final conclusion must cover every supplied dimension once.'
    return result
