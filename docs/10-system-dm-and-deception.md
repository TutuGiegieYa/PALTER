# System DM and Deception Assessment

Status: Utterance-time knowledge and dedicated scoped main/private DM adjudication implemented.

Last updated: 2026-11-10.

## Shared Occurrence-Time Knowledge: 2026-11-10 (v120)

Status: implemented; targeted checks, historical replay and two bounded synthetic
provider probes pass. Deployment and regression receipts are in module 11.

Current speech and historical gestures use the same source-body projection. An
event may keep inline `speaker_knowledge` or use `speaker_knowledge_ref` to an
actor-bound entry in `knowledge_snapshots`. Identical snapshot components may use
`part_ref` into `knowledge_parts`. Sources remain resolved through the existing
body pool. This only shares storage: each event retains its actor, recipients,
time and exact occurrence-time knowledge. Later discoveries cannot authorize an
earlier statement, and another actor's evidence cannot become the speaker's own.
Different evidence versions and distinct received occurrences remain separate.

Citation lists may use `id_ranges`, with inclusive full-ID endpoints, only when
actual adjacent IDs form a consecutive run. Prefixes, zero padding, gaps, order
and repeated occurrences remain recoverable. Model outputs still cite original
individual IDs. No range expansion grants knowledge; validation uses unchanged
stored authority. Feedback and player prose are not rewritten. Small requests
can retain inline snapshots/lists when reference wrappers would cost more.

Ensemble DM alone receives a 512,000-byte dynamic and 1,000,000-byte total guard.
The main and private DM use the same mechanism. Existing output caps, cost/call
admission, event selection and atomic result application remain unchanged. These
larger guards are application limits, not a claim about provider context capacity.

## Contextual Microexpressions: 2026-11-06

The user requested that the DM consider truth, speaker knowledge and surrounding
context when accompanying dialogue with microexpressions. Version 36 uses the
existing channel DM call to assess claims and optionally author one short Chinese
observable detail per utterance. Persona, received challenges, prior words and
pressure inform the choice. Known deception, mistaken belief and uncertainty
remain distinct; truthful stress and composed deception are permitted. A cue is
not a truth badge, forced confession, new evidence or a consequential action.
The DM may omit a cue on an ordinary line. There is no extra review call or prose
filter, and the player's original words remain unchanged.

Cues declare audible or visible delivery. Only the original listeners receive
audible details, and only listeners at the speaker's utterance-time location
receive visible details. The rendered view associates a recipient's existing cue
observations with their source utterance; it never reconstructs unseen cues from
the omniscient event stream. This also associates older saved pause/gaze records
without modifying history. Recent dialogue and the complete transcript show the
detail beside the original words, without duplicating it in recent scene changes.
Operations pinned to versions 35 and earlier retain their original enum contract.

## Shared Adjudication Context

Each utterance captures the speaker's acquired evidence, memory, belief and recent perceptions before later actions. The DM receives this snapshot plus frozen truth and scoped actual events. It distinguishes support, known contradiction, mistake and uncertainty; internal verdicts are never delivered. Observable microexpressions and vocal details retain actual recipients and location limits. Explicit disclosure of acquired records or initial known secrets can affect goals, without converting a spoken claim into a physical event.

Implementation: [complete playable runtime](17-complete-playable-runtime.md). Verification uses `tests/test_ensemble.py`, the multiplayer browser walkthrough and fresh provider receipts listed there. The design alternatives below retain their proposal scope; older implementation sections describe legacy saves.


References: [Conventions](../AGENT.md), [Glossary](../GLOSSARY.md), [Memory and evidence](02-memory-state-evidence.md), [Communication](03-communication.md), [Actions](04-world-events-and-actions.md), [Input and cues](09-speech-thoughts-and-action-input.md), [Time boundaries](08-time-reading-and-background-activity.md).

## Purpose and Status

The system DM is responsible for coordinating character inputs, resolving actual events and actions under scenario rules, and presenting what each recipient actually perceives. It operates outside the fiction and is not included in the cast or story.

Lies can probabilistically carry observable accompanying behavior. Once resolved as occurring, such behavior is part of actual game history. Claim assessment and internal implementation remain design proposals.

## DM Responsibilities

| Input or condition | DM responsibility |
| --- | --- |
| Outward speech or a chosen response | Preserve the contribution, determine actual recipients, and record the communication event |
| Optional thoughts and plans | Keep the character's private scope; distinguish reflection from a present action request |
| Action request | Check actual position, access, custody, time, abilities, and scenario rules; record the resolved result |
| World event | Check trigger conditions and actual effects; derive observable consequences |
| Private-chat invitation | Apply public invitation and recipient agreement, then create a dedicated DM for the accepted conversation and enforce applicable limits |
| Question or explanation demand | Create the relevant response obligation after actual receipt |
| Reading or pause state | Respect initial-reading gates, pauses, and already-running-work boundaries |

The DM has access to authoritative records needed for management. Ordinary AI characters receive their own allowed context, rather than the DM's complete view.

The DM role can combine language understanding and narration with explicit records and scenario rules. The implementation need not be one model call or a single freely improvising narrator. Facts should be checked against records rather than established solely because generated narration states them.

Independent immutable prefixes and cost control are prerequisites. A DM is a logical responsibility, not a requirement to invoke a separate large-model call for every routing, counter, or validation step. Define reusable context boundaries, dynamic increments, and execution budgets using [Immutable prefixes and cost control](11-prefix-cache-and-cost-control.md) before implementing expanded agent activity.

The user has chosen custom implementation instead of an existing framework. The [lightweight runtime proposal](12-lightweight-runtime-architecture.md) describes an application-owned scheduler and a single authoritative commit path shared by main and private DMs. Its language, storage, and detailed execution choices remain proposals.

## Outside the Fiction

The DM has no fictional body, persona, location, faction, vote, relationship, or personal objective. It is not an eligible witness, suspect, target, or private-chat partner. Characters interact with one another and the scenario world; private input addressed to game handling does not create an in-story conversation with the DM.

Present an event or perception directly, such as the lights going out or a character pausing before answering. Do not create a fictional DM who enters the location or announces information. Any actual in-world announcer would need to be a separately defined scenario entity.

## Dedicated Private Conversation DMs

Each accepted private conversation creates a dedicated DM context, used until that conversation ends. The DM serves the conversation's successive exchanges rather than being recreated for every message.

A possible responsibility split is a main coordinator for shared-world activity and a dedicated DM for each accepted private conversation. The dedicated DM interprets that conversation's inputs, performs or requests supported checks, records actual accompanying behavior, and produces the two participants' respective perceptions. The exact execution and storage architecture remains open.

Every instance operates on the same authoritative history. A proposed action during private conversation, if permitted by the scenario, must be resolved against actual current state. This prevents a private DM and the main coordinator from independently moving the same object or inventing incompatible events.

Administrative access to records does not make those records known to characters. Internal claim checking may use relevant authoritative facts, while delivered views still exclude unobserved outside events, hidden motives, and the other participant's private input.

When the conversation ends, retain its actual events and each participant's acquired memories before releasing the temporary context. The main system can retain these records for consistent management without granting other characters access to the private exchange. Participants return without an automatic account of missed outside activity and may choose to ask others what happened.

The dedicated DM remains outside the story throughout its lifetime. It has no fictional presence, and it inherits applicable pause gates, response rules, and conversation caps. Exact closure and late-result handling remain implementation decisions.

Creating or closing a private DM must not mutate the main DM's or another character's frozen prefix. Share only authorized stable segments, maintain private conversation increments separately, and request relevant authoritative facts rather than copying the entire world's hidden context into each session. Session release and provider-cache expiration are separate lifecycle concerns.

## Actual Events and Recipient Perception

The DM's outward output is the recipient character's actual sensory experience. Resolve the underlying speech, action, event, or cue once, retain its occurrence in game history, and derive each recipient view from it.

| Recipient conditions | Example view of the same interaction |
| --- | --- |
| Nearby with a clear view | Hears the spoken denial and notices a brief gaze shift |
| Able to hear from farther away, without a detailed view | Hears the denial and pause but receives no unseen facial detail |
| Occupied in an unrelated private conversation | Receives no automatic knowledge of the outside interaction |

These are visibility examples, not finalized distance or perception rules. An omitted detail is not an assertion that its opposite happened. Views can differ in completeness while sharing one actual history.

The recipient may interpret a cue as suspicious; that interpretation belongs to the recipient's beliefs. The displayed cue itself is something that actually occurred. A false spoken claim can be genuinely heard without its content becoming true.

Speaker awareness of an involuntary cue is a separate observation question. Do not assume a character automatically knows every detail other characters noticed about its expression.

### Proposed Bounded Routing for Demo 01

The [demo design](13-demo-01-action-and-observation.md) narrows the first slice to supported actions and incremental recipient observations. A following request is an action candidate with a start time and observation preconditions. It does not reveal the target's intended plan, create a separate world, or retroactively add observations to completed history.

Resolve an actual occurrence once, apply the demo's explicit visibility rules, and append only newly acquired perceptions to each eligible recipient. Present existing facts with deterministic text templates initially. A different observer can acquire another view of an event without requiring a full transcript rewrite or a new model call for every observer. If an observer's action changes actual conditions, resolve that effect as a subsequent supported occurrence.

This bounds narration work, but does not solve arbitrary action interaction automatically. Unsupported combinations remain outside the demo; simultaneous conflicts beyond its explicit fixture need a later rule design. The current bounded model-driven implementation is recorded below; arbitrary interactions remain outside its supported effects.

## Internal Truth and Outward Delivery

The user's clarification concerns preventing disclosure of hidden truth. It does not require a new speech-paraphrasing feature. The DM consults true events internally, preserves the speaker's chosen communication, and supplies only accompanying behavior that the recipient can perceive.

| Internal DM information | Allowed outward content |
| --- | --- |
| What actually happened | Only facts the speaking character chose to express, or information independently available to the recipient under game rules |
| What the speaker knows or believes | The speaker's actual statement and observable delivery; no unsolicited exposure of private knowledge |
| A deception or uncertainty assessment | No truth badge or internal verdict; only an eligible observable cue under the cue policy |
| A private thought or motive | Kept private unless the character communicates it or a supported game event makes it knowable |

If a player denies an action that the DM knows occurred, preserve the denial. The DM must not rewrite it into an admission or add an explanation exposing the hidden action. If a player intentionally tells the truth, the chosen disclosure is conveyed normally.

A visible hesitation is permitted when generated under the cue policy. Narrating that the speaker hesitated because they feared exposure for taking a letter would disclose a hidden motive and action; the recipient should receive only what it can actually observe.

These responsibilities can be separated into fact-and-knowledge assessment, cue selection, and recipient-specific delivery. A delivery step needs the permitted utterance and observable details, not an unrestricted explanation of the case's hidden truth.

## Information Used for Claim Assessment

For a factual claim, consider its subject, time, location, scope, and source. Consult:

- Actual events and relevant current state.
- Information the speaker had acquired before speaking, including private memories and observed outcomes.
- Whether the speaker is quoting someone, expressing a suspicion, or asserting a fact.
- Any explicit in-character intention the player supplied, treated as supporting context rather than a substitute for actual history.

Missing information is not evidence of falsehood. The system must not invent unrecorded history in order to judge a statement. Subjective preferences, uncertain time ranges, and vague wording may not support a factual verdict.

## Candidate Assessment Outcomes

The implemented main/private DM wire values are `supported`,
`known_contradiction`, `mistaken`, and `uncertain`. The v11 task context explicitly
defines each value and requires speech/speaker references from the supplied
utterances and source references from the supplied actual events. Earlier task
versions omitted the complete enum and sometimes returned `true` or `truthful`,
aborting otherwise valid actions. The gateway accepts those two affirmative
machine-field aliases as `supported` for legacy recovery. Ambiguous negative
labels such as `false` or `lying` remain invalid; they cannot establish whether
a speaker was mistaken or knowingly contradicting facts. This compatibility
step does not rewrite prose, modify world facts, or expose an internal verdict.

| Situation | Assessment | Example |
| --- | --- | --- |
| A statement agrees with established records | Supported within the checked scope | A states a visit that actually occurred |
| It contradicts a fact the character clearly knows | Candidate in-character deception or known-fact contradiction | A personally took a letter and denies having taken it |
| It is false in the world but consistent with the speaker's belief | Mistake or mistaken belief | A repeats a report it trusts, while hidden records show the report was wrong |
| Facts, timing, interpretation, or knowledge are insufficient | Uncertain or unverifiable | A makes a broad claim about an unrecorded period |
| It expresses an opinion, suspicion, or preference | Not a simple factual lie verdict | A says it suspects B |

The DM can compare game records and a role's known information. It cannot directly know a real human's mental intention. A player forgetting an assigned memory, a role misunderstanding evidence, and deliberate misrepresentation must not all be described as proven psychological dishonesty.

A practical first design can assess clear in-character contradictions and retain uncertainty elsewhere. It should retain its internal basis for assessment. The exact policy for cue eligibility when intent is uncertain remains open.

## Behavioral Cue Generation and Delivery

1. Receive the outward contribution without replacing its words.
2. Assess only claims supported by relevant game records and character knowledge.
3. Under the selected cue policy, resolve any accompanying behavior as an actual occurrence and record it once.
4. Present the contribution and each recipient's actually perceived behavior from that occurrence.
5. Preserve assessment reasons privately; observers form their own interpretations.

Possible details include hesitation, a changed delivery, restless fingers, or shifting gaze. None is presented as a truth badge. A character absent in private conversation does not learn a cue from an outside conversation automatically.

As an additional proposal, sincere speakers under stress may show overlapping behavior. Otherwise a behavior generated exclusively for lies could become a definitive game signal even if not every lie produces it. Probabilities, overlap, observation conditions, pacing, and persona factors require scenario design and validation.

## Illustrative Flow

A previously took a letter, received confirmation, and later says: I never took that letter.

The DM can identify a contradiction with A's known game history. It may attach an eligible cue under the configured policy. B receives the utterance and any visible behavior, not the internal contradiction verdict. B may become suspicious and ask a follow-up question, without automatically obtaining proof.

If A instead accuses B because it believed an incorrect witness account, the hidden fact that B is innocent does not by itself establish deliberate deception by A.

If A says it does not know who entered a room, and A never learned that information, the DM knowing the actual visitor does not turn A's ignorance into a lie. Preserve the statement without adding a hidden-truth explanation or automatically presenting it as deceptive behavior.

## Boundaries

- Preserve actual history when interpreting claims or resolving actions.
- Distinguish actual falsehood, the speaker's beliefs, and inferred deceptive intent.
- Preserve uncertainty; avoid treating omitted or unrecorded facts as proven lies.
- Keep private thoughts and assessment records outside other characters' visible context.
- Generated behavior does not change the chosen words, create a confession, or authorize a new substantive action.
- Knowledge used for adjudication must not leak through narration of a gesture's hidden cause or the speaker's unexpressed motives.
- Apply the same scenario policies to human and AI characters.
- Use actual observation to update memories and relationships; an internal assessment is not itself observed evidence.
- Keep the DM outside the fiction and derive recipient views from the same resolved events and behavior.
- Respect initial reading, pause handling, private-chat agreement, conversation caps, and missed-event isolation.

## Open Questions

- Adopted DM architecture and the division between language interpretation, rules, and narration.
- Representation of actual events and character knowledge sufficient for claim checks.
- Contradiction assessment versus explicit deception declarations, including genuine human memory mistakes.
- Ambiguous statements, partial truths, omission, and deliberate nonverbal deception.
- Cue eligibility under uncertainty, probabilities, sincere-behavior overlap, and observer access.
- Feedback to the speaking player and presentation of accompanying behavior.
- Recording generated behavior once and deriving consistent views under different observation conditions.
- The speaker's awareness of involuntary behavior.
- Main and private DM coordination, session lifetime, authoritative action resolution, and memory handoff on closure.
- Validation of correct fact checking and resistance to hidden-information leakage.

## Legacy Demo 01 Implementation and Verification

palter/ai_runtime.py calls a main DM and a separate DM for each accepted private session that has new utterances. Inputs include relevant actual records and speaker-specific knowledge for internal adjudication. Valid output assesses supported/known-contradiction/mistaken/uncertain claims and may select pause/fingers/gaze cues, at most one per speaker. Code records each cue once and derives hearing/visual recipients using utterance-time locations. Exact chosen words remain unchanged. Player views omit verdicts, hidden reasons, prompts, and other roles' thoughts. Claim accuracy is model-mediated and is not a guaranteed human lie detector. Unsupported arbitrary action adjudication remains outside this bounded runtime.


## Legacy Demo 02 Implementation: 2026-11-05

The investigation DM assesses newly recorded statements per public/private channel against the fixed case and speaker knowledge. It may attach bounded pause/gaze cues but cannot rewrite the statement, create a clue or expose its internal verdict. Gaze uses utterance-time co-location; hearing uses actual recipients. Final reasoning interpretation is authorized only after explicit closure; code independently enforces the fixed suspect and proof dependencies.


## Review Follow-up: 2026-11-06

V47 retains the channel DM call and adds only scoped recent delivery context.
Ordinary explanations default to no cue. Claim assessment distinguishes a
fallible memory from an action receipt and checks timed subjects, bounds and
arithmetic; no correction is spoken on behalf of the DM. Synthetic real-Flash
probes no longer endorsed the tested arithmetic error and omitted cues on plain
logistical speech. This is model guidance, not a semantic correctness guarantee.
Final argument assessment uses the separate ensemble_theory task in the existing
final-grading stage, so a generated nonliteral quotation cannot break submission.
Legacy pinned grading retains its original contract.
