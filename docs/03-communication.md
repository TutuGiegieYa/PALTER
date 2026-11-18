# Public and Private Communication

Status: Area-local public/private communication, optional travel speech and autonomous AI-to-AI private turns implemented.

Last updated: 2026-11-10.

## Attributed Spectator Receipts: 2026-11-10 (v121)

Status: implemented and verified with deterministic tests and a headless browser.

The spectator-only global projection extends movement attribution to structured
actions and event results. Render each actual event once. Keep recipient-specific
receipts in attributed, collapsed details, merging identical copies only within
that event. Different inspections of the same material remain distinct named
actions. Spoken and gesture text, including direct address, remains exact. A
role's own observation list retains its original second-person receipts and
information scope. This projection neither edits stored history nor supplies
model context. See [global timeline verification](18-spectator-mode.md#event-based-global-timeline-2026-11-10).

## Arrival Presence and Observer Wording: 2026-11-08

Status: implemented and verified with v78; deployment recorded below.

V78 includes a frozen presence snapshot in each mover/follower's arrival
receipt: other visibly co-located characters, who can be addressed in the
current channel, and who is privately occupied. Empty rooms are stated explicitly.
Presence is distinct from permission to hear a conversation. Arrivals can see a
private pair without receiving its transcript, thoughts, prior actions or missed
messages; the privately occupied participants still receive no outside arrival
notification. Followers receive the snapshot from their own perspective.

The next normal role decision also receives a versioned current presence view.
Public perception covers the current area; private perception remains limited to
the private participants and is explicitly incomplete for the surrounding area.
Neither view reveals remote people, destinations or hidden inventories. Historical
arrival snapshots never update from later movement or conversation changes.

The spectator's global timeline renders each structured movement once, in third
person, including explicit followers when recorded. Personal perspectives retain
their original scoped receipts. This display projection does not rewrite saved
events/observations or transmit omniscient information to role models. Older
pinned operations preserve their request and movement contracts. No extra model
call or wake-up is added to perform receipt formatting or presence projection.

Verification: nine dedicated tests cover empty/occupied rooms, private isolation,
followers, frozen historical lookup, current scoped perception, v77 compatibility,
global deduplication and unchanged model-call count. Desktop (1440px) and mobile
(390px) browser checks passed with no page errors or horizontal overflow; the
screenshots were inspected. A synthetic real Flash role decision received three
visible people but only one eligible listener; the private transcript stayed out
of its payload. No whole-game behavior claim follows from this bounded check.
Artifacts: `.local/verification/arrival-presence-20261108/`.

Deployment: the 347-test regression passed, and v78 was loaded at 17:45:07 CST
on 2026-11-08 after an idle-work check and SQLite backup. HTTP returned 200 and
all saved game/call/operation data retained identical existing-column hashes.
New operations receive the richer arrival contract; old observations and the
currently failed v77 operation keep their historical receipts. The spectator
display projection also applies to stored movements without modifying history.

## Local Conversation and Voluntary Travel Speech: 2026-11-08

Status: Implemented and verified with isolated regression/browser tests and synthetic real Flash decisions.

Public speech, gestures, evidence presentation, addressed questions and private
invitations reach only participants in the same area who are not privately
occupied. Accepted private conversations require co-location; moving apart
invalidates a pending invitation. Mechanical world/closure announcements remain
system notices, not remote character speech. Receipt never backfills a missed
conversation after arrival.

A role may choose a move and optional speech in the same decision. Deliver that
exact speech to the departure audience before moving, without adding another
model call. It may state the destination, remain vague, mislead, or be empty.
The engine does not disclose the destination to people left behind: they see
departure; people at the destination see arrival without the previous location.
The mover and a previously chosen, successful follower know their actual route.
Scope structured action feedback and source lookup as well as visible prose.
Keep authoritative movement history and already acquired memories intact.

The human interface supports the same optional departure line and lists only
current local listeners. Version the rule/prompt changes for new operations;
older pinned recovery retains its contract. No forced dispersal, extra planning
round, prose filter, or mandatory destination announcement is introduced.

Implementation uses `communication_version=1` selected by the immutable v74 role
contract. `ensemble_world.audience` applies co-location to speech, gestures,
presentations, invitations and applicable social actions. Pending invitations
expire on separation; impossible legacy remote private sessions close on the
next new operation without rewriting already delivered history. Fixed global
world/closure notices remain available. Speaking alone does not earn received
public-disclosure credit, and an empty area does not create a periodic duty to
talk to oneself. Existing directed response obligations remain in force.

The existing compact response expresses travel as
`{"action":{"kind":"move","args":["r3"]},"speech":"..."}`; an empty speech
string means silent movement when no response is owed. Runtime delivers speech
before applying the move. There is no additional movement-specific model round
or new native tool family. Human `act` commands accept the same optional line in
`text`; the Web departure field sends both in one atomic command. Technical
retries preserve a single speech event and a single movement result.

Authoritative movement events retain the actual origin, destination and
followers. `movement_views` stores each observer's permitted receipt. Departure
witnesses get no destination in either text or action-feedback arguments;
arrival witnesses get no origin. They also do not receive the other area's
recipient list. Personal source lookup returns the original scoped observation,
not the global movement event. A role's voluntary statement remains a claim even
when it gives a different destination from the actual action. Public speech does
not reach an absent addressee, create their response obligation, or wake them.

Spectator waiting text now says "pending memory records" rather than implying
progress toward waking. The count is observations after the memory checkpoint;
it can include the role's own action receipts and records from before it began
waiting. `next_observation` instead uses the wait's observation cursor and a new
received event from someone else. A later local arrival can satisfy it; speech
from a different area cannot. Waiting does not poll the role model.

Verification artifacts: `.local/verification/local-communication-20261108/`.

- Nineteen dedicated tests cover local receipt/obligations, evidence transfer,
  movement metadata/source lookup, truthful/vague/misleading/silent travel,
  human atomic commands, invalid movement, private consent and separation,
  explicit followers, wait delivery, memory counters, migration, public credit,
  idempotency and v73 compatibility. The complete suite passes 302 tests.
- Real HTTP/browser checks at 1440 and 390 pixels verify optional travel speech,
  silence without a model call, independent departure/arrival recipient views,
  current local addressees/invitations, draft retention and layout. No page errors.
- Three synthetic real Flash decisions used normal action menus: silent travel,
  explicitly announcing the destination, and a culprit's vague departure. All
  chose the intended movement and obeyed delivery boundaries. Five calls (three
  role decisions and two existing speech-DM calls) completed without retries;
  reported usage cost USD 0.00359868. No production story was exported. This
  verifies the bounded communication behavior, not a guarantee that characters
  will always choose different rooms or a complete-game balance result.

Deployment: after an idle check and local SQLite backup, the service restarted
with v74. Root and both changed JavaScript assets returned HTTP 200 and matched
disk. All 30 saved game-state hashes, 1,464 model-call rows and 724 operation rows
were unchanged. Browser verification also rendered a real scoped-wait fixture
with three pending memory records and the explanatory label; waiting remained
active until an eligible new observation. Deployment receipts are in the same
artifact directory. Existing saved knowledge is not retroactively erased.

## Immediate Private Exit and Event Notifications: 2026-11-06

Either participant can end an accepted private conversation immediately, even
while an unanswered question, explanation obligation or periodic speech request
is pending. Neither the other participant nor the DM can require them to stay.
The frontend exit control and server command permit this; AI roles can choose
`end_private` without generating an answer. Eight utterances/300 active seconds
are maximums, not required lengths.

Closing preserves the original transcript and acquired memories, removes queued
turns for that private channel and retires only its pending response obligations.
It does not move a private question into public discussion or erase evidence of
silence. The fixed close transition and notifications require no DM call. The
private DM still evaluates actual new utterances when present; separate custom
tracking conditions may need interpretation. Actually informed outside roles
subscribed to the conversation's end wake together without receiving its content.
See [event scheduling](08-time-reading-and-background-activity.md).

## Current Runtime: 2026-11-05

Public invitations require acceptance. Accepted private sessions have frozen participant baselines, eight-utterance/300-active-second caps, scoped history and a continuing AI agenda. Public events do not backfill absent participants. Addressed recipients must respond; three received dialogue opportunities require actual words. Model role turns, human replies and gestures use the same delivery mechanism.

Implementation: [complete playable runtime](17-complete-playable-runtime.md). Verification uses `tests/test_ensemble.py`, the multiplayer browser walkthrough and fresh provider receipts listed there. The design alternatives below retain their proposal scope; older implementation sections describe legacy saves.


References: [Conventions](../AGENT.md), [Glossary](../GLOSSARY.md), [Memory state and evidence](02-memory-state-evidence.md).

## Purpose and Scope

Support public discussion and agreed private conversations. Communication spreads accounts, clues, experiences, and beliefs that affect subsequent choices.

The invitation is public; conversation content is delivered to its two participants. This applies across categories and action settings.

## Confirmed Rules

- Speech is not required every round. A question addressed to and received by a character requires a verbal or nonverbal response.
- A configurable interval of several rounds requires actual speech; pure gestures do not fulfill it. Events that create an explanation obligation also require speech.
- Provide selectable nonverbal reactions. Optional private thoughts and plans remain a separate button and input path, described in [Speech thoughts and action input](09-speech-thoughts-and-action-input.md).
- Characters may hold private conversations.
- The initiator first requests a conversation with the intended partner in the public channel.
- The recipient must agree before the private conversation starts.
- After agreement, create a dedicated private-conversation DM and use it through the end of that conversation.
- Refusal or no response does not establish agreement.
- Public speech and invitations are available through the public channel, with actual receipt depending on participation. Private content goes to its participants.
- Characters currently in private conversation do not automatically receive or learn about concurrent outside events or conversations. They may ask others about them after returning.
- AI characters can initiate speech and agreed AI-to-AI private conversations in the background during permitted active play.
- Background AI conversations require a maximum duration and a maximum number of exchanges; concrete values and counting semantics remain open.

## Conversation Flow

1. A publicly asks to speak privately with B.
2. Wait for B to express agreement or refusal.
3. After agreement, create a dedicated private-conversation DM and start the two-person conversation.
4. Use that DM for the conversation's successive exchanges, observations, and permitted in-scene handling.
5. Participants form memories and judgments from messages and behavior they actually perceive.
6. When the conversation ends, close its dedicated DM session while preserving actual history and the participants' respective acquired memories.

Interaction controls, the public display of acceptance, termination, and invitation expiry remain open. Silence must not be treated as acceptance.

## Dedicated Private DM Lifetime

The user's reference to the current private-chat round means the accepted conversation through its end. It does not require recreating the DM for each utterance or exchange.

The private DM handles participants' speech, optional private input under its proper scope, applicable response requirements, deception assessment, and actual accompanying behavior. Each participant receives its own perception; one participant's private thoughts are not exposed to the other.

The dedicated context is a session and information boundary, not a requirement for a particular process, model, or worker implementation.

Prefix isolation and cost control are prerequisites for this design. Reuse the authorized private-DM instruction baseline while keeping participants, private history, and new events in scoped session data. A new private conversation must not require resending the entire game history as uncached context. See [Immutable prefixes and cost control](11-prefix-cache-and-cost-control.md) for the design and measurement requirements.

All actual events still belong to one shared world. Permitted physical actions, object changes, and recorded behavior must use the game's authoritative rules and history. A private DM cannot create an independent version of custody, time, or already-resolved events. How such actions are routed through the main coordinator remains an architecture decision.

The DM may consult authoritative information needed for internal checks without teaching participants unobserved outside events. Continue enforcing the private participants' lack of automatic awareness of concurrent activity.

On ending, stop scheduling conversation turns for that session. Preserve the actual exchange and role-specific learning, with private access boundaries intact. Do not distribute a complete transcript or automatic outside recap to the public group. Release the temporary DM context after the required records are retained; exact storage and in-flight-result handling remain open.

Background AI conversations close under the applicable duration or exchange cap. Manual ending controls and the applicability of identical caps to human-only conversations remain to be designed.

## Message Scope and Knowledge

| Information | Recipients | Effect |
| --- | --- | --- |
| Public speech | Public channel participants receiving the message | Recipients know what was said; privately occupied characters do not automatically learn it |
| A's invitation to B | Public channel, subject to actual participation | The invitation is public; actual awareness follows receipt |
| Pending invitation | A conversation has not started | Recipient agreement is still required |
| Private content after agreement | The two participants | Personal conversational experiences |

Receiving an account establishes knowledge of what the speaker said. Truth, belief, and independent verification remain distinct.

The delivered description represents the recipient's actual experience of the other character's speech and visible or audible behavior. The DM is outside the story and does not appear as an extra person relaying or commenting on the exchange. Each recipient receives its own permitted view of the same actual occurrence.

## Response and Speech Obligations

A recipient must respond to a question they actually receive. The player may answer with words or choose a meaningful reaction, such as nodding, shaking the head, shrugging, or signaling someone to continue. An intentional nonverbal response is distinct from leaving the input unanswered.

At the configured periodic speech interval, actual words are required. When a received event creates an explanation requirement, the affected character must also speak. A pure gesture cannot substitute for either spoken-response obligation. Exact intervals, deadlines, eligibility, and relevant-content rules remain open.

Required response does not require truthfulness or disclosure of a secret. Characters may evade, mislead, refuse verbally, or respond nonverbally where permitted. Only actual speech satisfies an active spoken-response requirement.

An unanswered question outside a character's private conversation does not create secret knowledge or an immediate obligation for that absent character. Apply obligations only after actual receipt under the established information boundaries.

A response to an invitation is not automatically agreement to private chat. The invitation still needs recipient agreement; which explicit choices or unambiguous gestures can communicate agreement remains to be defined.

Private thoughts or plans submitted through the additional input control are not messages to a conversation partner. Even in an agreed private conversation, each character's optional private input remains separate from the utterance its partner receives.

Speech itself can cause social consequences, such as changed beliefs, invitations, promises, or scenario-defined agreements. Saying an object was moved does not by itself move it or establish that the claimed event occurred.

AI characters use received public messages and conversations they joined. A public invitation can inform relationship judgments without exposing the private exchange.

Speech can have system-generated accompanying behavior under the [behavioral-cue design](09-speech-thoughts-and-action-input.md). Deliver only observable behavior to eligible recipients; a private DM assessment of whether the speaker may be lying is not part of the relayed message.

## Background AI Conversations and Limits

During ordinary active play, AI characters may decide what to say or do and may invite one another into private conversation. The invitation and recipient agreement rules still apply. Initial reading and single-human reading pauses override permission to start new AI activity, as specified in [Time reading and background activity](08-time-reading-and-background-activity.md).

Configure a maximum conversation duration and a maximum exchange count. The intended bounded-dialogue behavior is to stop the background conversation when either cap is reached. Exact limits, whether duration means wall time or game time, and whether an exchange means a message or a pair of turns remain open.

Cooldowns, repeated invitations, and simultaneous conversations also require design so that immediately reopening a conversation does not defeat its limits. Applying identical caps to human-only conversations has not been decided.

## Outside Activity and Returning

The wider game can continue while characters converse privately, subject to the session's running or paused state. Private participants know their conversation, not the concurrent actions, public claims, or discoveries outside it.

On return, they may choose to ask what happened. The respondent answers from its own information and motives, so a response may be incomplete, mistaken, withheld, or deceptive. Returning alone does not supply an authoritative recap or all missed public messages.

For example, A and B talk privately while C discovers a missing object and discusses it with D. After returning, A and B do not automatically know about the discovery or discussion. If A asks D, A learns D's account, with that source and later learning time preserved.

Current visible changes can be observed normally after return. Historical causes still need supported information. Exceptions for events perceptible inside the private setting, and explicit access to missed public history, remain open.

## Evidence Sharing Example

A individually discovers a letter and publicly invites B. After B agrees, A describes its contents privately. Other characters who received the invitation know it occurred, not the letter's contents. B has received A's account, which is distinct from A's observation.

Presentation of original objects, excerpts, verified displays, and conversation records remains to be designed.

## Scene Action Boundaries

The same invitation procedure applies during gatherings, travel, emergencies, exploration, nighttime scenes, and other action opportunities. Secretly moving or inspecting an object does not itself create a private conversation with another character.

Seeing a figure, hearing steps, or noticing a missing object is an observation. The system's complete action record is not automatically delivered as a public message. See [World events and scene actions](04-world-events-and-actions.md).

## Boundary Cases

- An unanswered or refused invitation cannot directly become private chat.
- An invited AI character must also agree; its decision can reflect its goals and knowledge.
- Public information a character already received remains part of its knowledge after a private conversation begins.
- Retelling a private conversation gives listeners an account, not automatic access to the original exchange.

## Open Questions

- Recognizing recipients, agreement, and refusal.
- Public display of accepted invitations and conversation start/end.
- Leaving, cancellation, expiry, simultaneous conversations, and larger groups.
- Exceptions for directly perceptible outside events, public-history review after return, and acting elsewhere while chatting.
- AI invitation decisions and evidence-sharing controls.
- Duration and exchange limits, counting units, cooldowns, and applicability to human conversations.
- Speech-round order, periodic speech interval and scope, response deadlines, and behavior for absent, paused, or privately occupied characters.
- Selectable nonverbal reactions, their visibility, and which signals can communicate invitation agreement.
- Event explanation triggers and when a combined response satisfies overlapping obligations.
- Private DM creation, safe closure, in-flight results, and handoff of actual events and individual memories.
- Shared-world coordination for physical actions permitted during private conversation.

## Legacy Demo 01 Implementation and Verification

The AI interface supports public speech, addressed questions, nonverbal replies, public private-chat invitations, explicit acceptance/refusal, and exit. Each accepted conversation has an immutable participant baseline and dedicated private-DM call path. Limits are 90 active seconds and four utterances; pauses extend the timer. Outside records are not delivered to private participants. A stale private-channel submission is rejected before model work, preventing unintended public rebroadcast. AI-to-AI invitations use the same consent rules at bounded interaction opportunities. Group chat and multiplayer remain designs.


## Legacy Demo 02 Implementation: 2026-11-05

The investigation slice preserves public invitation/consent and private participant isolation. It permits eight utterances and 300 active seconds per accepted conversation, independently of investigation length. A relevant role responds to questions or presented evidence; bounded outside-role opportunities during private exchanges can create events the participants miss. See [Demo 02](16-demo-02-deduction.md).
