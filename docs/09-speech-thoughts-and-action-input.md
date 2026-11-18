# Speech Thoughts and Action Input

Status: Human/AI response, periodic speech and observed-event explanation obligations implemented.

Last updated: 2026-11-06.

## Current Runtime: 2026-11-05

Direct questions require words or a supported gesture; every three received dialogue opportunities and explicit evidence challenges require words. An observed hide/destroy completion also creates an explanation obligation for its actor. Unobserved handling does not do so. Private absence accrues no missed public obligations. Personal notes remain editable without a model call; optional thoughts are private and explicit action requests select one presently supported effect or a clarification.

### First-person Authoring: 2026-11-06

Task version 42 guides role-authored speech, thoughts, memory, private reasoning
and relationship reasons to use 我 for self-reference. This covers ensemble,
investigation and legacy role/memory tasks. Action/addressee interpretation maps
我 to the speaking/acting character in its authorized view. Thought, notebook,
reason and conclusion inputs now offer first-person examples. No text replacement,
prose rejection, review call or retrospective history edit was added. Published
versions through 41 and already pinned requests remain unchanged.

Four real DeepSeek Flash role/memory calls on a fresh, explicitly synthetic
two-role fixture all completed. Both roles spoke/recalled in first person while
retaining other people's names and source attribution. Cost estimate from reported
usage: USD 0.002994168. Receipt:
`.local/verification/first-person-20261106/probe-65760cc7.json`.
This is a small output sample, not a guarantee that every future sentence complies.
138 Python regressions, six frontend checks, JavaScript syntax and thirteen
browser scroll/input checks passed. User-written text remains exact.

Implementation: [complete playable runtime](17-complete-playable-runtime.md). Verification uses `tests/test_ensemble.py`, the multiplayer browser walkthrough and fresh provider receipts listed there. The design alternatives below retain their proposal scope; older implementation sections describe legacy saves.


References: [Conventions](../AGENT.md), [Glossary](../GLOSSARY.md), [Communication](03-communication.md), [Scene actions](04-world-events-and-actions.md), [Time and reading](08-time-reading-and-background-activity.md).

## Purpose and Scope

Provide outward communication through words or observable reactions, alongside optional private character thoughts and plans. Responses, private intentions, and actual scene actions can influence the story through distinct information and causal pathways.

This is a shared interaction mechanism across scenario categories. It does not select a final interface language or a complete world-clock model.

## Confirmed Direction

- In text written from a character's own perspective, use first-person Chinese
  (我, or natural subject omission), rather than referring to oneself by the role's
  proper name. This applies to speech, thoughts/plans, memory summaries, private
  deductions and personal relationship reasons. Other characters retain their
  names. Interpret first-person human input as the authenticated participant's
  character. Guide new generation through versioned context and input hints;
  preserve quoted records, historical text and the human's exact chosen words.
- Speech is not required every round.
- A character who actually receives a question addressed to them must respond, using words or a selectable body-language reaction.
- Actual speech is required at a configurable interval of several dialogue rounds; pure actions or gestures do not satisfy that interval.
- A received event that creates a need for the character to explain also requires a spoken response.
- Thoughts and intended actions are optional; they do not have to be supplied every round.
- An additional button opens the optional input path.
- When a character lies, the system can randomly attach observable behavior associated with the delivery. This is separate from deliberate nonverbal reply choices.

The private-input interpretation is that these thoughts and plans are supplied for the player's own character and game handling, rather than spoken to other characters. Input labeling, ordering, and exact execution timing remain to be designed.

## Two Input Paths

| Path | Requirement | Information scope | Effect |
| --- | --- | --- | --- |
| Outward communication | Triggered by received questions, periodic speech rules, event explanation requirements, or voluntary participation | Permitted recipients in the current public or agreed private conversation | Words or observable reactions can affect beliefs, relationships, and conversational rules |
| Thoughts and plans | Optional through an additional button | The submitting character and game handling | Records a private perspective or proposes an action, without directly disclosing it to other characters |

A candidate button label is Thoughts and Plans. The actual user-facing label and presentation remain open.

The optional input is not another private-chat channel. Its contents are not automatically shown to a conversation partner, including a partner already talking privately with the player.

## When a Response Is Required

| Situation | Obligation | Are pure gestures sufficient? |
| --- | --- | --- |
| No current response or speech requirement | The character may choose whether to contribute | No response is automatically required |
| A received question addressed to the character | Give an outward response | Yes, unless another spoken-response rule also applies |
| Periodic speech interval becomes due | Give an actual spoken contribution | No |
| A received event or challenge requires explanation | Give a spoken response to that requirement | No |

A private thought does not satisfy an outward response requirement, because the other character has not received it.

### Selectable Nonverbal Responses

Provide deliberate reactions with communicative purpose, such as nodding, shaking the head, shrugging, or signaling someone to continue. An intentionally selected reaction is an outward response; the player simply not answering is a different situation.

These choices describe observable behavior. They do not reveal the character's private reasoning or certify a factual interpretation. Observers may interpret the same gesture differently.

A gesture response must not become a way to bypass scene-action rules. Moving an object or claiming that a major action succeeded still requires the appropriate action request and resolution.

### System-Generated Behavioral Cues

The user clarified that behavior such as looking away can accompany a lie probabilistically, rather than being a default button asking the player to choose an incriminating appearance. Possible details include a brief pause, changed delivery, restless fingers, or a shifting gaze.

Record the player's chosen words and the generated accompanying behavior separately. The cue must not replace those words, invent a confession, or choose a new substantive action for the human.

Lie assessment is a separate problem. The [system DM](10-system-dm-and-deception.md) consults actual history and the speaker's own information; the proposed assessment approach distinguishes clear contradictions, mistaken beliefs, and uncertain claims. This does not establish access to the real human's mental intention.

Observers receive only behavior they can actually perceive. They do not receive a hidden label saying that the statement is false or that its speaker is lying. Private conversation and missed-event boundaries remain applicable.

Once a generated behavior is resolved as occurring, it is an actual event. The DM derives each observer's perception from that same occurrence, rather than independently inventing gestures for different viewers. The DM does not become a fictional narrator-character or participant in the exchange.

As a design proposal, overlapping cues can also arise from sincere stress or other character conditions. This would preserve uncertainty rather than turn one gesture into a mechanically definitive lie signal. Exact triggers, probabilities, and character factors remain open.

Voluntary response gestures and generated cues have different origins. A cue accompanying speech does not independently satisfy a pending response obligation, invite someone to private chat, or require an explanation unless actual interaction or scenario rules create that requirement.

### Periodic Actual Speech

Use a configurable interval N of dialogue rounds to require actual spoken participation. N is not yet chosen. Pure body-language responses do not fulfill the requirement or reset the count of actual spoken participation.

Who is eligible in a counted round, whether private speech counts toward public participation, counter behavior during pauses or absence, and what content qualifies remain open. This is not a requirement to speak in every round.

### Event Explanation Requirements

A scenario event can require a particular character to speak when there is an explanation demand supported by information that character receives. Examples include a challenged account, an observed broken promise, or a public resource discrepancy that the character is asked to explain.

The response must use words, but it is not required to disclose the truth or a hidden motive. Evasion, deception, or verbal refusal remain possible within scenario rules; exact relevance criteria remain open.

Hidden events do not automatically impose a response obligation on an uninformed character. Private-chat information isolation and the initial-reading and pause gates still apply.

### Overlapping Requirements

When a received question also requires an event explanation, a gesture alone is insufficient. The stronger spoken-response requirement applies. As a design proposal, one relevant spoken response can satisfy multiple active obligations when their audience and timing are compatible.

An answer to a private-chat invitation remains distinct from accepting it. Invitation agreement must still be established; the supported consent signals are a separate interaction decision.

## Thought Intention and Action Request

Separate private input that expresses a belief or concern from a request to attempt an action.

| Illustrative input | Interpretation |
| --- | --- |
| I suspect B, but I still want to protect them | A private belief and motivation |
| I am considering moving the letter, but have not decided | A tentative intention, not execution |
| I now try to retrieve the letter from the cabinet | An action request subject to actual scene conditions |

This distinction preserves the user's rule that humans decide whether to act. The handling of unclear or mixed input remains an open interaction question; a tentative concern must not silently become an executed action.

Leaving the optional input empty means no new private input was supplied. It does not require the system to invent a thought or an action for the human. Persistence or cancellation of previously declared plans and ongoing authorized actions needs a separate rule.

### Proposed Action Submission Interaction

The [action-policy proposal](04-world-events-and-actions.md) recommends natural-language action requests grounded in supported scenario effects. This is a proposal, not a confirmed interface change.

Within the existing optional private-input panel, distinguish recording a thought from submitting an action. An explicit submission authorizes its stated scope; ordinary mechanical substeps do not each need an additional confirmation. If the input is ambiguous or the system proposes a substantive alternative strategy, obtain a clear choice before executing that alternative. Exact labels and layout remain open.

Suggestions may show actions grounded in the character's acquired information without exposing hidden opportunities. A preview or interpretation may describe knowable time estimates and resource requirements, but not hidden observers, undiscovered evidence, or guaranteed outcomes. A submitted multi-step plan does not authorize controlling another participant's choices or inventing new actions for the human when a step becomes impossible.

Preparation and feedback must remain within the character's private scope. The world effects of actual execution are delivered according to observation rules, which may expose some activity or aftermath to others without disclosing the original private plan.

## Speech and World Effects

Speech is a real communication event. Recipients can believe, doubt, repeat, or react to it. Invitations and other scenario-defined speech acts can have their specified effects.

A claim about a physical action or past event is checked against actual history rather than accepted as a world-state update. For example, saying that a letter was taken can be true, false, mistaken, or deliberately misleading. Actually attempting to take it is handled through action resolution.

Likewise, a private intention does not establish success. Location, access, custody, time, abilities, and scenario rules determine what actually occurs. Other characters acquire any effects through supported observations and communication, not access to the private input.

## Illustrative Interaction

1. B asks A a question that A receives. A chooses a shrug as the response.
2. A later becomes due for periodic actual speech and says: I stayed in the hall. The earlier shrug does not satisfy this spoken-participation requirement.
3. A separately and optionally submits a private input: I want to protect B. I now try to retrieve the letter from the study.
4. The game resolves the attempted action. A receives appropriate feedback; others obtain only information they actually observe or receive.
5. If a later received event creates an explanation requirement for A, A must respond with words. A can still decide how much to reveal.

If A provides no private input, no new private intention or physical action is inferred from that omission. A character can also decline to contribute in an ordinary round where no response or speech obligation is active.

These are illustrative interactions. Exact round order and speech/action resolution timing are not yet fixed.

## AI and Background Activity

AI characters also distinguish concise in-character intentions from outward speech. An AI's hidden plans are not included in messages sent to other characters. During permitted background activity, its actual action requests use the same scenario-resolution framework.

Initial reading, single-human pauses, public invitation and recipient agreement for private conversation, and background conversation caps remain applicable. Optional intentions do not create an extra public speaking turn or automatically start private chat.

## Open Questions

- What counts as a dialogue round, eligibility, order, and the interval N for actual speech.
- Public versus private speech counting, counter behavior during pause or absence, and minimum relevance of speech.
- Response deadlines and handling of missing, withdrawn, or disconnected responses.
- Event explanation triggers, combined obligations, and supported nonverbal responses.
- Whether optional input is submitted before speech, alongside it, or at another permitted point.
- How to distinguish thoughts, tentative plans, and present action requests in free-form input.
- Action resolution timing and conflicts between speech, movement, and other concurrent actions.
- Whether to suggest actions and how the player can inspect or revise a submitted plan.
- Persistence, duration, and cancellation of ongoing plans and previously authorized actions.
- How private input appears to its owner without leaking through other characters' messages or memories.
- How in-character deception is assessed, how uncertainty is handled, and which cues observers can perceive.
- Cue probabilities, pacing, overlap with sincere behavior, and whether deliberate misleading gestures also qualify.

## Legacy Demo 01 Implementation and Verification

The interface exposes words, addressed responses, nod/shake responses, an optional personal-thought control, explicit natural-language action attempts, and ordinary action buttons. An unanswered addressed question requires a verbal or nonverbal response; every three interaction rounds requires actual speech. Private thoughts update only A's interpretation and execute no action. Natural-language execution selects one supported operation or asks for clarification. Main/private DM outputs can create actual bounded cues without displaying internal truth judgments. General event-specific mandatory explanation triggers remain a design boundary rather than an advertised implemented feature.


## Legacy Demo 02 Implementation: 2026-11-05

The investigation interface supports addressed questions, revisiting attributed statements, presenting selected acquired records, private reflection and explicit supported-action interpretation. Private notebook drafts are local saves with no model call or answer judgment. Final submission requires a suspect, the player's own explanation and chosen evidence; it explicitly closes the case. See [Demo 02](16-demo-02-deduction.md).
