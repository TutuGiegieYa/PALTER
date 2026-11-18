# World Events and Scene Actions

Status: Shared timed activities, physical evidence handling, following and eligible AI-selected world effects implemented.

Last updated: 2026-11-08.

## Wait Review Contract Recovery: 2026-11-08 (v89 implemented)

The newly created tea-house spectator case paused at operation watch_99355136_40.
The paid role action inspected a record, then registered next_observation with a
purpose mentioning that inspection. The receipt already existed when waiting
started. Four DM responses called the wait completed; the validity-only review
accepted active/cancelled and rejected all four identically. Across this game,
11 failures had that same diagnosis. The schema error was not returned in retry
context. This is a wait-review contract gap, not a missing inspection result.

Keep fixed completion engineering-owned. A sourced completed answer for a
validity-only wait under the v87+ structured-basis contract can be accepted as
legacy shorthand for ending an unnecessary subscription: record it as cancelled
with resolution_kind purpose_satisfied and retain the reported status and source
IDs. It must not complete a tracker, activity, invitation or conversation. Older
pre-basis behavior remains pinned. The ordinary future contract still requests
active or cancelled and distinguishes cancellation of waiting from event failure.

V89 supplies per-record allowed_statuses and the wait's registration boundary,
and aligns the DM task instruction with the shared event protocol. Generic event
schema failures get bounded, scoped correction feedback on the existing retry
path; no extra review call, arbitrary text filter, forced role action or automatic
resume is introduced. Preserve old request bytes and paid stages. Verify the
failed step locally with its original records, new independent synthetic provider
calls, retry/recovery and fixed-event isolation. Leave the production game paused
for the user's retry, without modifying its outcome or consumed call records.

Mixed-batch handling also preserves event order when a completed tracker wakes
its owner before a queued validity review for that owner's wait. The obsolete
review is ignored by its exact pre-batch wait ID rather than being looked up as a
custom tracker. It cannot create a second wake or affect another subscription.
The regression covers both decision orders and fixed private-conversation waits.

Read-only replay of the new game matches 65 historical request hashes across 25
completed background operations plus the failed step, and all four original
failed DM outputs now pass the scoped compatibility checks. The failed step
retains the acquired inspection result, queues its actor once and leaves the
frozen case unchanged. No production result was rewritten or sent to a provider.

Three v89 independent synthetic provider probes pass on their first attempts:
end an already satisfied wait, retain a useful future-information wait, and
complete a custom tracker plus end its wait in one batch. The immutable v88
control returned active (runtime success but missed the immediate-end semantic
expectation); its existing timeout still bounds that wait. This control's failure
is retained in live-report.json, not silently relabeled as a semantic pass.
Final acceptance uses the three v89 probes and the separate exact v88 production
response replay. The probes used Flash with thinking disabled. Artifacts and
final regression/deployment evidence are in module 11 and
`.local/verification/wait-review-20261108/`.

Verification completed: 75 targeted and 419 full tests passed. V89 is deployed locally; the affected game remains paused for explicit user retry.

## Authoritative Workflow Events: 2026-11-08 (v88 implemented)

The runtime exposes investigation versus conclusion versus ended as actual
workflow state. A proposal or one assent does not transition the phase. Visible
assents remain scoped; a global conclusion transition is already announced to all.
A phase:conclusion subscription is completed by the engine only after quorum.
Custom listeners may bind optional end_on fixed event IDs for early cancellation;
those terminal receipts are matched mechanically. Semantic early-end conditions
remain DM-owned, with current workflow facts supplied. Explicit cancellation,
normal completion and timeout retain their separate meanings. No idle polling,
forced movement, disclosure or automatic player conclusions are introduced.

The first real v86 probe showed that workflow facts alone did not prevent an
incorrect cancellation. V87 therefore requires a structured decision basis:
received_condition, current_circumstances, owner_request or workflow_transition.
Only the last may name a stage, which must already be the actual conclusion or
ended stage; owner_request requires a recorded creator request. Invalid bases
receive a bounded, source-scoped validation receipt through the existing retry
path. Paid retry inputs are persisted and replayed exactly. V88 also updates the
older inline field-list instruction to include basis, resolving the conflicting
format guidance exposed by the first v87 call. This is structural validation,
not text filtering or an extra model-review pass. Semantic claims can still be
wrong; this does not make arbitrary DM prose mechanically provable.

## Local Travel Observations: 2026-11-08

Implemented for v74 operations: a move can include optional actor-authored speech
delivered before departure. The mover chooses whether to disclose its destination.
Departure witnesses learn departure only, arrival witnesses learn local arrival,
and an explicitly chosen successful follower learns their own actual route.
The full event remains authoritative; role-scoped action feedback and source
lookup cannot expose the hidden part of that route. Communication and private
invitations require the same area. See [the communication implementation and
verification](03-communication.md#local-conversation-and-voluntary-travel-speech-2026-11-08).

## Objective Action Feedback: 2026-11-08 (Implemented)

The [cost optimization design](11-prefix-cache-and-cost-control.md#5-objective-action-feedback-and-model-controlled-repetition)
extends objective execution feedback to the supported structured action families.
Code derives receipts and recipient-scoped summaries; roles decide whether to
repeat an action. A new real execution appends occurrences and updates observable
counts, latest status and results without rewriting history. Lifecycle updates,
provider retries and command re-delivery are not independent executions.
Pending, completed, failed and cancelled outcomes must remain distinct where
the handler supports them. Unknown receipt is not proof of non-receipt, and a
spoken claim cannot establish an unexecuted action. Preserve valid repeated
actions, current scenario rules and human control. `action_feedback.py` covers
supported structured action families through observed event receipts. New actions
record execution metadata; old records preserve unknown fields. Prompts include
counts and at most two recent receipts per group within approximately 2 KiB;
required live obligations remain outside that bounded history. Full history is
retained, and arbitrary physical construction remains outside the supported actions.

## Current Runtime: 2026-11-05

New games support move, inspect, take, place, give, copy, protect, hide, search, destroy and one-step following. Humans can create a document containing an explicitly unverified claim. Search/hide/destroy/repair/route clearance run for two shared clock units, with start costs and cancellation; completion rechecks access. World calls select only eligible access, record-release or supply effects every six physical units, capped at four opportunities. Speech cannot establish a physical result. General arbitrary construction and multi-step plan invention remain outside the adopted bounded contract.

Implementation: [complete playable runtime](17-complete-playable-runtime.md). Verification uses `tests/test_ensemble.py`, the multiplayer browser walkthrough and fresh provider receipts listed there. The design alternatives below retain their proposal scope; older implementation sections describe legacy saves.


References: [Conventions](../AGENT.md), [Glossary](../GLOSSARY.md), [State and evidence](02-memory-state-evidence.md), [Communication](03-communication.md), [Action input](09-speech-thoughts-and-action-input.md), [Prefixes and cost](11-prefix-cache-and-cost-control.md), [Scenario catalog](scenarios/README.md).

## Purpose and Scope

World events and character actions change shared conditions, create opportunities, and produce consequences that drive further interaction. This is a general event-and-action mechanism across settings and categories.

Day, night, journeys, ceremonies, investigations, negotiations, and emergencies are possible contexts. A mandatory day/night cycle is not established.

## Confirmed Direction

- Include global random events and actual scene actions alongside conversation.
- Support multiple event types, contexts, and trigger conditions.
- Treat character actions as character-level events. Use a shared event data structure to define duration and other execution properties across character and world events.
- Publish some observable consequences according to actual visibility.
- Characters can form their own intentions from relationships, goals, and incomplete knowledge.
- Humans decide their characters' discretionary actions; acting and declining opportunities both affect the developing story.

Specific events, budgets, schedules, and resolution mechanics below are proposals. Codex is responsible for expanding them into concrete [scenario modules](scenarios/README.md).

## Shared Event Data Model

The user's term user-level event refers here to an in-world character event. Use the same mechanism for human-controlled and AI-controlled characters. Searching, moving an object, cleaning a trace, and repairing equipment can be character events; storms and power failures can be world events. A character event can cause a global consequence.

Propose one common event structure with a type-specific payload. Define execution properties as event data, supported by explicit scenario rules. Avoid a separate scheduler or hard-coded timing path for each kind of action. The exact field names and encoding below remain proposals.

| Field group | Proposed contents | Meaning |
| --- | --- | --- |
| Identity and cause | Event ID, game ID, definition ID and version, originating request or event | Connect an occurrence to its rules and causal history; recognize repeated delivery |
| Kind and source | Character activity, communication, or world change; character or world trigger | Classification does not grant visibility or establish success |
| Participants and targets | Acting characters, affected entities, location, optional conversation | Actor, affected character, and observer are different roles |
| Eligibility | Trigger and required state or permissions | Check before starting and recheck where the outcome depends on changing conditions |
| Timing | Instantaneous, defined duration, or a bounded condition-based end; explicit clock and unit where needed | Whether and how long an event consumes time is an event property |
| Execution state | Pending, running, suspended, or terminal; actual start, progress, and end when applicable | A proposed or scheduled action has not necessarily happened |
| Concurrency and interruption | Occupied resources or activities, compatible actions, cancellation and resumption rules | Determines whether the actor can speak, move, or switch activity during execution |
| Observation | Visibility rules for the activity and its consequences | Compute actual recipient views at the relevant occurrence, not from event kind alone |
| Resolution | Supported effect rules, effect timing, and recorded actual outcome | Effects can occur at start, during progress, or at the end; completion does not guarantee success |

Keep scenario-owned definitions separate from per-game execution values while retaining one shared structure. Definitions supply permitted duration and effect policies; an instance identifies who is acting, where, and its actual progress. A player or generated candidate cannot grant itself a zero duration, remove prerequisites, or choose a guaranteed successful result by supplying different fields.

An illustrative instance, not an implemented schema:

```json
{
  "id": "event_018",
  "game_id": "game_01",
  "definition": {"id": "inspect_location", "version": 1},
  "kind": "character_action",
  "source": {"character_id": "A", "request_id": "request_042"},
  "targets": ["study"],
  "state": "pending",
  "timing": {"mode": "duration", "clock": "game", "unit": "tick", "value": 2},
  "eligibility_rule": "can_inspect_location",
  "execution_rules": {
    "concurrency": "inspection_activities",
    "interruption": "inspection_interruption"
  },
  "observation_rule": "local_inspection_observers",
  "resolution_rule": "inspect_location"
}
```

The rule identifiers stand for application-supported scenario rules, not arbitrary code supplied by a player or model. The study, duration of two game ticks, rule names, and concurrency behavior are examples. This does not select ticks as the universal game clock or determine how they map to real time.

Observation rules and internal resolution fields are system data. Deliver a recipient view rather than exposing the complete event record to every character. Secret intent, actual activity, visible aftermath, and the actor's awareness of leaving a trace can all have different knowledge boundaries.

## Event Lifecycle and Actual History

A possible execution lifecycle is pending to running to completed, with rejection before start, suspension and resumption, cancellation, or failure where supported. Exact states remain a proposal. A completed execution records its resolved outcome, which may be success, failure, or partial progress.

Distinguish execution state from the append-only history of what actually occurred:

- A tentative thought does not automatically create an executable event. An explicit action request can produce a pending candidate after validation.
- Accepting or scheduling a candidate does not establish that its future effects happened.
- Starting an action can itself be observable. Record actual start, intermediate effects, interruption, and resolved outcome when they occur.
- Cancelling an action does not erase time already spent, observations, or effects already committed. Retention or loss of unfinished progress depends on the scenario rule.
- A rejected request need not create an in-world occurrence. If an observable attempt actually occurred, retain that occurrence without inventing a completed action.
- Concurrent events use the same world timeline and resource checks; their durations are not simply added together to advance the clock.

For example, a trace-cleaning event may require access to water, occupy the character's hands, and permit interruption. Someone entering may cause an interruption. The resulting history can include partial cleaning and new water marks without granting either character knowledge of unseen details. Those effects need scenario support; they are not automatic properties of every cleanup.

In a survival scenario, repairing equipment can use the same structure with different materials, timing, interruption rules, and progress effects. A world power failure can be instantaneous while the resulting outage persists as world state until another event changes it. Event duration and the lifetime of its consequences are distinct.

## Runtime Integration

The [custom runtime](12-lightweight-runtime-architecture.md) validates and schedules these event instances, coordinates conflicts, records actual effects through one shared update path, and derives observations. Timing and lifecycle transitions do not each require a model call.

Keep fictional events distinct from initial-reading controls, transport retries, provider requests, and billing records. Those technical activities may schedule or block execution but are not automatically story occurrences. Existing reading and pause gates still apply; this event structure does not settle the open policy for applying model results completed during a pause.

## Proposed Action Policy: Free Proposals and Grounded Execution

The user has asked for a recommendation on action design. The policy in this section is a Codex proposal, not a newly confirmed ruleset. It builds on the confirmed shared event model and human control of discretionary actions.

The user subsequently raised concerns about interaction complexity and randomness. The broad policy below remains a future design proposal. The current [Demo 01 design](13-demo-01-action-and-observation.md) recommends five explicitly supported actions, deterministic outcomes, one-step following, and no runtime invention of new action rules. Develop the bounded slice before considering broader composition.

Allow players to describe an intended action in natural language, including ideas not listed as scenario menu choices. Ground execution in the character's abilities, acquired information, location, available resources, current world state, and scenario rules. Optional suggestions can help discovery without becoming an exhaustive action menu or exposing hidden opportunities.

### Small Composable Action Vocabulary

Use a small set of supported operations rather than enumerating every possible sentence:

| Operation family | Candidate operations | Boundary |
| --- | --- | --- |
| Observation | Look, listen, inspect an area, compare acquired material | An inspection can test a hypothesis without guaranteeing a discovery |
| Movement and access | Travel, approach, enter, open permitted access | Actual routes, travel conditions, barriers, and timing apply |
| Object interaction | Take, transfer, place, conceal, clean, alter, or use an object | Check custody, physical access, materials, and supported effects |
| Operation and construction | Operate equipment, repair, or combine available materials | Character capability and scenario-supported physical effects apply |
| Character interaction | Ask, propose cooperation, assist, obstruct, or communicate | Other participants retain their decisions; private conversation still requires public invitation and agreement |
| Waiting and monitoring | Wait, observe a location, or maintain a permitted activity | The world can progress while the activity occupies the character |

These are proposed families, not a closed final enumeration or an authorization to perform every listed action in every story. A new player idea can become a bounded composition of supported operations. A language model may propose targets, steps, and parameters; it cannot create executable code, install a new rule handler, or grant itself authority to change the world.

If an idea needs an effect the current runtime cannot represent, use a bounded clarification or state the supported limitation. Do not narrate unsupported success. Scenario-specific additions should extend the supported rules explicitly rather than silently changing them for one participant.

### Intent, Submission, and Multi-Step Plans

Distinguish the player's desired outcome from the means they authorize. A request to make another character believe a forged letter contains both a possible physical action and an outcome controlled by another participant. Creating or placing a forged letter does not guarantee that someone reads or believes it.

Propose explicit intent labels within the existing optional private-input panel: recording a thought versus submitting an action. A clearly submitted action is authorization to attempt its stated scope; it does not require a second confirmation for every ordinary step. Clarify ambiguous input or a proposed substantive change in strategy before executing that change. A spoken claim about a past action remains a communication event, not proof that the physical action happened.

Bound multi-step plans and validate each step against current state. Execute only the submitted scope; if a necessary item is absent, do not automatically steal it, attack its holder, or invent a substitute plan for the human. Other characters' cooperation requires their own decisions. Conditional plans, if supported, must specify authorized conditions and use observations actually available to the actor rather than hidden system knowledge.

### Feasibility and Uncertainty

| Situation | Proposed resolution policy |
| --- | --- |
| The action is physically or procedurally impossible under current conditions | Do not grant the intended effect; explain only what the actor can legitimately learn |
| The action is ordinary and its relevant conditions are satisfied | Resolve through supported rules without an unnecessary success roll |
| The outcome has a scenario-supported uncertainty | Use relevant abilities, materials, environment, and time to adjudicate; preserve the actual sampled result |
| Another event competes for the same object, location, or activity | Apply the scenario's ordering and conflict rules against the common world state |
| The request is underspecified or the effect is unsupported | Clarify the material ambiguity or explain the supported boundary without inventing a completed action |

Do not add arbitrary failure rolls to every inspection or fabricate a residual clue whenever concealment succeeds. Failed, partial, and successful actions must all be possible where supported. Repeated delivery of the same command must not reroll the outcome. Any genuinely new attempt is a new event with applicable costs and current conditions; repeatedly inspecting an unchanged fact must not arbitrarily change that fact.

Invalid input rejected before any in-world attempt need not consume game time. An actual attempt may spend time and materials or leave observable effects even when it fails. Distinguish those situations in the event history.

### Separate Action Results and Knowledge

Record distinct dimensions of a resolved action:

- What physically or socially occurred within the supported action scope.
- Time, materials, custody, location, and other actual state changes.
- Whether the process or its aftermath was observable, and what each observer actually acquired.
- Traces or other consequences supported by the scenario.
- What feedback the actor can perceive, including uncertainty about completion or detection.

Action success, being noticed, and leaving traces are separate questions. An actor can succeed without knowing someone observed them, or fail to remove all traces while believing a cleanup was sufficient. These distinctions do not require a separate model call for every dimension.

An action may affect an unknown trace through a supported physical process. For example, washing an entire known garment can alter a trace its wearer never noticed. That does not grant the wearer knowledge of the trace before or after washing. Conversely, an actionable target must have a legitimate location or description; private entity identifiers supplied without an in-world basis do not grant access. Searching an area can test a guess without the system confirming a hidden object's existence in advance.

### Feedback and Cost

Before or during execution, convey the interpretation and constraints the actor can know: the intended action, a supported estimate of time or material use, and perceptible obstacles. Exact presentation is open. Do not reveal hidden observers, unseen traces, secret detection probabilities, or undisclosed reasons for failure through a plan preview.

For familiar actions, use rule-based validation and resolution directly. Use bounded language interpretation or adjudication for genuinely new compositions or ambiguity; no model call is required for every timer update. Once an accepted event starts, advance its recorded lifecycle without repeatedly asking a model to decide whether its already established past happened.

Keep accepted scenario rules and stable instructions versioned. A new action instance or temporary plan belongs in dynamic context and must not rewrite a published prefix. The proposed policy does not select a global clock, exact probabilities, universal action allowances, or any provider budget.

Concrete examples are retained in the [theft scenario](scenarios/02-theft-and-deception.md) and [survival scenario](scenarios/05-isolation-and-rescue.md). They illustrate different uses of the same mechanism rather than imposing forgery or survival rules on every category.

## Event Families and Contexts

| Family | Example | Decisions it creates |
| --- | --- | --- |
| Environmental change | Storm, flooding, reduced visibility, route obstruction | Protect resources, change route, investigate, or stay |
| Infrastructure change | Power failure, restored communications, access-system failure | Restore a facility, guard a location, exploit or investigate changed access |
| Social event | Public hearing, reunion, ceremony, unexpected visitor | Attend, disclose information, negotiate, or pursue another objective |
| Resource pressure | Delayed supplies, changed transport capacity, a deadline | Allocate scarce resources, cooperate, prioritize goals |
| Information arrival | A previously established letter, witness, or record becomes accessible | Inspect, verify, disclose, conceal, or seek corroboration |
| Access change | An archive opens, a route clears, a restricted area becomes available | Explore first, travel together, observe others |
| Character consequence | Missing property, a broken agreement, a protected location disturbed | Inspect, question, repair, pursue, or reassess trust |

Sources can include random selection, schedules, state conditions, and character actions. Each event must fit its actual source and current world state.

## Progression Proposals

One candidate loop is interaction and investigation, followed by action opportunities, event/action resolution, and new observations. A ceremony or journey can create such a window just as a night scene can.

Choosing continuous time, turns, phases, or different active-play models by scenario remains open. Initial reading and single-human review pauses have defined scheduling boundaries in [Time reading and background activity](08-time-reading-and-background-activity.md). Limited time or resources can make guarding, searching, negotiating, and protecting someone meaningful alternatives.

During permitted active play, AI characters may act and speak in the background, including initiating agreed private conversations with other AI characters. Their conversations have duration and exchange caps. Participants privately occupied elsewhere do not automatically know these actions or public results; they can ask about missed activity on return.

## Relationship-Driven Intentions

A character may act to protect another person without knowing that person's hidden role. In an investigation, an innocent character may try to remove a clue implicating a friend. In a negotiation, someone may support an unreliable ally. In survival, someone may prioritize a dependent over a shared objective.

Current [relationships](05-character-relationships.md) and acquired information inform intentions. Humans decide whether their own characters act. Specific scenario opening assignments, such as the murder example's fallback killer, remain scoped to those scenario procedures.

Separate intention, decision, attempt, and actual outcome. Declining an opportunity leaves the relevant world processes and other participants free to continue under the chosen time model.

## Action Possibilities

| Purpose | Candidate actions | Consequences or trade-offs |
| --- | --- | --- |
| Protect a person or secret | Withhold information, move relevant property, intervene | Exposure, conflict, changed access, lost investigation time |
| Preserve a shared resource | Guard, relocate, inspect, recover | Opportunity cost and encounters with competing interests |
| Check an account | Investigate a location, observe a route, seek another source | Partial knowledge, time use, possible discovery |
| Pursue a private goal | Recover an item, keep a promise, secure an agreement | Cooperation or conflict with shared goals |
| Improve conditions | Restore facilities, clear permitted access, organize assistance | Changes to other characters' opportunities |
| Remain or defer | Stay with someone, wait, leave an opportunity unused | New witnesses, missed opportunities, continued world change |

Available actions depend on location, information, abilities, objects, and scenario constraints. Outward responses use words or selectable gestures, while optional private thoughts and intended actions use an additional button. Ordinary speech is not required every round; received questions, periodic speech intervals, and event explanation requirements determine when a response is due. See [Speech thoughts and action input](09-speech-thoughts-and-action-input.md).

A tentative thought can inform the character's current perspective without executing an action. An expressed action attempt is checked against scene conditions before its effects become established. The exact interpretation and feasibility model remain open.

Scenario events may create explanation requirements, for example when a publicly observed discrepancy prompts a particular character to account for it. The character must speak after receiving the relevant information. A hidden event alone must not impose an obligation that leaks information the character has not acquired.

## Conflict Resolution

Resolve competing actions against one actual history: arrival times, locations, custody, obstacles, and observers. Later actors encounter the state produced by earlier actions.

The [system DM](10-system-dm-and-deception.md) is responsible for these resolutions and for presenting each character's actual perceptions. It operates outside the fiction. Character speech describes claims, while rule-grounded resolution establishes actual state changes.

An event or generated action presented as having occurred must be part of the game's actual history. Microexpressions and delivery cues are resolved occurrences as well, not independent stylistic inventions for each recipient. Visibility may limit what is noticed without changing the underlying occurrence.

The murder example's human priority is a local opening rule. It does not establish universal priority in negotiations, resource allocation, movement, or object competition.

## Public Outcomes and Private Observations

| Information | Candidate scope |
| --- | --- |
| A condition actually experienced by a character | Observable information for that character; direct perception during private chat requires an explicit rule |
| Missing property confirmed in a public inspection | Public findings for recipients; private-chat participants are not automatically caught up |
| A figure or conversation fragment observed locally | Actual observers first |
| A character's private purpose | That character's own information |
| Unobserved routes, identities, or motives | Acquired only through supported observations or communication |

A change may remain undiscovered until someone checks. Global effects do not require immediate publication of every detail.

An event's public scope and a character's awareness are separate. Use actual receipt and observation to form memories. A public event occurring during private conversation does not automatically become known to its absent participants.

## Investigation Illustration

A letter is publicly known to be stored in a cabinet. During a relevant access window, A approaches it, B watches a corridor, and C investigates elsewhere. A possible resolved history has A take the letter while B sees only a partial figure.

A later inspection can announce the missing letter. B may disclose observations or publicly invite A to a private conversation and wait for agreement. Alternative histories can have a guard intervene, another character arrive first, or the letter remain protected.

Night and a power failure are optional variants of this example.

## Design Boundaries

- Continue causal history; random selection must not rewrite past actions.
- Check event prerequisites, current custody, access, and previous effects.
- Supply observations with their actual limits, preserving hidden identities and motives.
- Let actions have genuine consequences; backups and residual traces need scenario support.
- Apply public invitation and agreement rules to private conversation in any context.
- Tune event frequency and intensity to support meaningful decisions.
- Treat the proposed daily one-evidence-category limit as a local scenario budget, not the event system's default.

## Open Questions

- Exact shared event fields, definition and instance representation, lifecycle states, and supported rule interfaces.
- Time models, action budgets, simultaneous movement, and intervention.
- Per-event duration, compatible activities, interruption, partial effects, and the lifetime of resulting world conditions.
- Event eligibility, frequency, scheduling, and intensity.
- Observation and detection conditions, including whether an actor notices being observed.
- Public reporting versus inspection-dependent discoveries.
- Interpretation of private action proposals, suggested choices, and ambiguous or tentative thoughts.
- Whether to adopt the proposed free-proposal policy, which operations to support first, how to bound composed plans, and when uncertain outcomes require sampling.
- Waiting, declining an action, and failing to choose.
- How changed situations contribute to scenario endings.

## Legacy Demo 01 Implementation and Verification

The production AI runtime supports move, inspect, take, place, one-step human following, and wait. DeepSeek interprets explicit natural-language attempts into one permitted choice or clarification. Role model decisions select actual effects; the old authored schedule runs only with --offline. The model selects eligible route closure/reopening, one meeting delay, or none. These are explicit current effects; they cannot invent evidence or past facts. Ordinary code validates preconditions and commits history atomically. Arbitrary conflicts, cleanup, variable-duration actions, and composed free-form execution remain designs.


## Legacy Demo 02 Implementation: 2026-11-05

New investigations support explicit movement, inspection, evidence presentation, waiting and consensual private conversation. Physical inspection and movement are local deterministic effects. A role decision can execute the same permitted effects from that role's own acquired information. Arbitrary destruction, combat and evidence fabrication are not implemented. No action count closes the investigation. See [Demo 02](16-demo-02-deduction.md).
