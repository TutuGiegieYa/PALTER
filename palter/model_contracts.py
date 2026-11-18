"""Shared authoring/tool bounds, projected into each new immutable task version."""
from copy import deepcopy

CURRENT_PREFIX = 'ai-tasks-v125.json'
EVENT_TEXT = {'description':160, 'completion_condition':400, 'early_end_condition':240}
LISTENER_TARGETS = 4
SOURCE_ID_LENGTH = 200
STORY_TEXT = {'title':1200, 'briefing':1200, 'rooms.*.name':60,
              'rooms.*.description':500, 'roles.*.persona':700,
              'roles.*.secret':700, 'roles.*.secret_record':700,
              'roles.*.relationships[*]':250}
RELATIONSHIPS = 3


class ContractError(ValueError):
    def __init__(self, field, requirement, **details):
        super().__init__(field+': '+requirement)
        self.feedback = {'code':'field_contract', 'field':field, **details,
            'instruction':requirement+' Correct this field in the complete response required by the current task. '
            'Preserve the requested response shape, authorized sources and all other valid decisions.'}


def text(value, field, maximum, empty=False):
    if not isinstance(value,str) or len(value)>maximum or (not empty and not value.strip()):
        raise ContractError(field, f'Use a string of at most {maximum} characters'+
            ('; empty is permitted.' if empty else ' with nonempty text.'),
            maximum_characters=maximum, actual_characters=len(value) if isinstance(value,str) else None)


def setup_guidance():
    return (' Authoring field limits (characters, including punctuation and whitespace): '+
        '; '.join(f'{field} <= {limit}' for field,limit in STORY_TEXT.items())+
        f'. All these texts must be nonempty. Each roles.*.relationships array has exactly {RELATIONSHIPS} entries.')


def synchronize_tools(specs):
    for spec in specs.values():
        for tool in spec.get('tools',[]):
            function=tool['function']; properties=function['parameters']['properties']
            if function['name']=='create_event_listener':
                for field,limit in EVENT_TEXT.items():properties[field]['maxLength']=limit
                for field in ('event_ids','end_on'):
                    properties[field].update(maxItems=LISTENER_TARGETS,uniqueItems=True)
            elif function['name']=='read_sources':
                properties['requests']['items']['properties']['id']['maxLength']=SOURCE_ID_LENGTH
                function['description']=function['description'].replace('One batch per decision, ', 'At most one batch per tool round, ')
            elif function['name']=='list_sources':properties['query']['maxLength']=SOURCE_ID_LENGTH


def check_published(specs):
    expected=deepcopy(specs);synchronize_tools(expected);issues=[]
    for task,spec in specs.items():
        if spec.get('tools')!=expected[task].get('tools'):issues.append(task+': tool schema differs from handler contract')
    if setup_guidance() not in specs['ensemble_setup']['instruction']:issues.append('ensemble_setup: missing current authoring bounds')
    for perspective,spec in [('investigation',specs['ensemble_role']),*specs['ensemble_role'].get('perspectives',{}).items()]:
        if 'testimony_ids最多12个' in spec.get('instruction',''):issues.append(perspective+': obsolete citation cap')
    if specs['ensemble_memory']['tokens']!=2048 or specs['ensemble_role']['tokens']!=6144:issues.append('memory/role token contract')
    if specs['ensemble_role'].get('memory_character_budget')!=1024:issues.append('memory character trigger contract')
    if any(s.get('thinking',{}).get('type')!='disabled' for s in specs.values()):issues.append('thinking must remain disabled')
    return issues
