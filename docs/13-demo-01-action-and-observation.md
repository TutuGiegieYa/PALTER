# Demo 01: Bounded Actions and Observations

Status: Historical scripted regression fixture, available only with explicit --offline; superseded as production scope by the AI runtime.

Last updated: 2026-11-04.

References: [Conventions](../AGENT.md), [Events and actions](04-world-events-and-actions.md), [Memory and evidence](02-memory-state-evidence.md), [Reading and pauses](08-time-reading-and-background-activity.md), [System DM](10-system-dm-and-deception.md), [Prefixes and cost](11-prefix-cache-and-cost-control.md), [Custom runtime](12-lightweight-runtime-architecture.md), [Theft scenario](scenarios/02-theft-and-deception.md).


The user rejected the scripted production scope after inspecting the first implementation. This document now records the historical offline fixture only. The default application uses real AI according to [AI runtime integration](15-ai-runtime.md). The old schedules and historical verification below do not describe production AI behavior.

## Purpose and Decision Status

The user wants a demo design before application development, followed by incremental expansion. The user has identified open-ended actions, following other characters, changing DM delivery, and randomness as sources of complexity.

This document proposes a small action-and-observation slice. Verify that a supported action changes one shared world and gives each character only its actual observations. Do not attempt a complete story generator, unrestricted physical simulation, or open-ended DM in the first slice.

The user authorized implementation on 2026-11-04 and selected DeepSeek with DEEPSEEK_API_KEY from .env. The fixture, cast, action limits, interface, and timing below are the demo implementation baseline; they do not replace shared product rules or establish permanent limits. The later provider instruction adds the bounded review feature in [DeepSeek integration](14-deepseek-integration.md), while preserving deterministic action resolution and scripted characters.

## First-Slice Scope

- One human controls character A. Characters B and C use authored deterministic scripts, explicitly identified as scripted characters rather than live AI.
- One authored investigation fixture, three connected locations, one relevant letter, and six discrete action beats.
- Five actions: move, inspect, take, follow one movement, and wait.
- No chance-based success, random detection, random cues, or runtime generation of new action rules.
- One authoritative history and separate observations for A, B, and C. Normal player responses contain only A's authorized view.
- Authored descriptions and observation templates for all actual events. The explicit DeepSeek review control selects from A's existing observations; it cannot create facts or change action results. Calls, usage, cache hits, and dated cost estimates are recorded.
- A small local browser interface is the proposed delivery surface. The broader product interface and deployment remain open.

The purpose is to test the event and perception mechanism with one bounded real-provider integration. Generative dialogue and a model-driven DM are later milestones. This slice must not be presented as the completed AI game.

## Fixture: The Handover Letter

Public introduction: a handover meeting is about to begin, and A needs to locate and bring an important letter to the hall. Other characters have their own activities. The introduction does not disclose the letter's hidden custody or future movements.

| Element | Initial actual state | A's starting information |
| --- | --- | --- |
| A | In the hall; not carrying the letter | Knows its own task and starting location |
| B | In the hall, with the letter concealed in a bag | Sees B in the hall, but does not know the bag's contents or B's plan |
| C | In the courtyard | Knows C was assigned courtyard duties; receives no live position feed |
| Locations | Hall connects to study and courtyard; no direct study-courtyard route | Knows the map and ordinary room descriptions |
| Study | Desk with an accessible closed drawer | Can learn about the desk and drawer on entering the study |
| Letter | In B's bag | Identity and appearance of the sought letter are known; its current location is not |

The drawer does not initially contain the letter. B has no automatic knowledge of A's private action selection or thoughts. C's location does not permit observing study or hall activity in this fixture.

### Authored Character Schedule

| Beat | B's supported action | C's supported action |
| --- | --- | --- |
| 1 | Move from hall to study | Remain in the courtyard |
| 2 | Place the letter in the study drawer if still present there and still holding it | Remain in the courtyard |
| 3 | Return from study to hall if still in the study | Remain in the courtyard |
| 4-6 | Remain in the hall | Remain in the courtyard |

C receives only its own local observations. If a scripted action becomes impossible, record a no-op or supported failure rather than inventing a new strategy. This schedule is internal fixture data, not a preview or player-visible walkthrough.

## Reading, Time, and Resolution Order

After the introduction is confirmed, show A's initial briefing. No script or gameplay action runs during reading. Reading has no deadline; Reading Complete starts the action slice.

One accepted human action advances one beat. Inspecting the briefing, reviewing acquired information, or submitting invalid input does not advance time. A reading pause freezes progression. There are no autonomous model turns; the optional review cannot start during a pause. Already-running review results can complete and are withheld during the pause. Broader autonomous in-flight-result handling remains untested.

Each accepted action uses this fixture-specific sequence:

1. Validate against current state and A's acquired view. Register an eligible one-step following request before the target's next movement.
2. Advance the beat and apply the authored character action due at that beat. Record only its actual effects under its preconditions and derive observations at occurrence time.
3. Resolve A's move or eligible following movement, then any inspection or taking action due for A. Recheck relevant preconditions after earlier changes. One human submission authorizes only one of these actions.
4. Append new recipient observations and evaluate the deadline after beat 6. Reading the output does not trigger another beat.

This ordering is an explicit fixture rule, not a universal priority for AI, humans, or scripted actors. Model latency and network completion order cannot choose it. Fixed phases allow a concrete implementation without an arbitrary concurrency solver.

## Supported Actions

| Action | Preconditions | Deterministic effect |
| --- | --- | --- |
| Move | Adjacent known location through the fixture's available route | Change A's location; derive departure and arrival observations for actual viewers |
| Inspect | A is in the location; the chosen fixture target is available there | In the study, open and inspect the drawer, learning its current observable contents; elsewhere receive the location's authored inspection result |
| Take | A has acquired the item's current accessible location, is present, and the item remains available | Transfer the letter to A; others perceive only supported local effects |
| Follow | Target is currently visible and in the same location, with no incompatible activity | Attempt to accompany the target's next adjacent movement within this beat; expire after that opportunity |
| Wait | Game is active and before its deadline | Stay in place while the next authored beat resolves |

Only the fixture's supported targets and transitions are executable. Requests rejected before acceptance do not create a successful event or advance time. If a validly accepted action becomes impossible after an earlier scripted effect, record its supported failure without the intended effect; the accepted beat is still spent. Normal feedback must not reveal hidden item custody merely because an invalid request guessed an internal ID.

The fixed interface avoids natural-language action interpretation in this slice. Unsupported actions remain visibly unavailable as capabilities rather than being improvised by a model.

## Following and Observation Rules

Following is a bounded observation-and-movement action. It does not subscribe to the target's thoughts, private plan, inventory, or all future actions.

- A can follow B from the hall at beat 1 because B is currently visible there.
- On that movement, A observes B leave and accompanies the known route. A receives the destination's visible scene after arrival, not B's bag contents.
- At beat 2, an observer already in the study can see B handle the drawer, but the handling view alone does not identify the letter. Inspecting the drawer establishes its observable contents at inspection time.
- B can observe A's visible arrival when present. There is no perfect stealth or hidden detection roll; B does not automatically learn that A selected a following action.
- If the target does not make an eligible visible movement within the beat, the following opportunity expires with feedback limited to what A can observe. It does not become a permanent tracking ability.
- A request submitted after B has left cannot retroactively establish that A followed. A can move along a known route or inspect later without acquiring unseen history.
- Only A can submit a following action in this fixture. Chains of followers, pursuit, evasion, blocking, and arbitrary simultaneous conflicts are deferred.

This small rule set deliberately bounds interactions. It does not assert that incremental delivery alone makes every possible action combination easy.

### Example Recipient Views

When B moves into the study, A in the hall can observe departure along that route. If A follows, A later observes the study scene. C in the courtyard receives no report of that movement. B may observe A arrive without learning A's private purpose.

When B handles the drawer, an observer present in the study receives the visible handling description. A still in the hall receives nothing. A later inspection can discover the letter without turning A into a witness to its earlier placement.

Resolve each occurrence once. Compute recipient observations from actual location and the fixture's visibility rule, then append them. Do not regenerate previous speech, rewrite acquired memories, or give a late observer a full hidden event record.

## Outcomes

At the end of beat 6, evaluate actual custody, A's location, and A's acquired information:

| Condition | Demo outcome |
| --- | --- |
| A holds the letter and is in the hall | Letter delivered for the meeting |
| A knows the letter's location or holds it elsewhere, but has not delivered it | Location established or letter recovered, with delivery incomplete |
| Neither condition holds | Letter not located before the meeting |

The outcome does not identify guilt, force a confession, or imply that A knows B's unseen actions. Different outcomes arise from player choices and observations rather than rerolling success. Do not create a new clue to rescue a missed objective.

## Minimal Records and Interface

Reuse the shared event model with only fields required by this fixture: stable identity and definition version, beat, actor and target, lifecycle, supported effects, and causal links. Store actual events separately from pending requests. Keep acquired observations and their source event IDs per character.

The proposed player screen contains the introduction and briefing, current beat and location, visible people and objects, supported action controls, acquired observations, and the outcome. Display last-seen information as such; do not show hidden live locations or internal custody in a map or action picker.

A separate development inspection surface may compare truth with A/B/C views under explicit development access. It is outside the fiction and must not share the full hidden record through the ordinary player payload. Tests can inspect authoritative state directly without granting A that knowledge.

The proposed implementation uses ordinary Python modules and a small local transport, without an agent orchestration framework. Use the interaction and persistence defaults below for this demo; final package layout remains an implementation detail. Preserve one state-update path, command deduplication, and recipient isolation. Repeated delivery of a command must not spend another beat or repeat an effect.

## Interaction Defaults for the Demo

These are Codex-proposed implementation defaults to make the first slice concrete. They are scoped to this demo and do not settle the full product interface or deployment.

### Screen and Phase Flow

| Phase | Player experience | Permitted progression |
| --- | --- | --- |
| Introduction | Public premise and the objective to bring the letter to the hall | Confirm to receive A's briefing; no script runs |
| Reading | A's starting material and map | Reading Complete starts active play at beat 0 |
| Active play | Current scene, action controls, and acquired observations | An accepted action resolves the next beat |
| Reading pause | Original briefing and already acquired information | Resume returns to the same beat; no catch-up progression |
| Ended | The outcome and A's acquired timeline | Read-only review or a new game |

Use a compact Chinese text interface for the demo: beat and current location at the top, the currently visible scene and people, five action controls with relevant targets, and a separate acquired-observation list with event times. Show A's own carried items with only their known observable properties. A sealed letter's possession does not grant knowledge of its contents.

The map shows known routes. People appear at their currently observed locations or as explicitly labeled last-seen information; the map must not reveal B's unobserved current position. Action targets and disabled-control explanations derive from A's authorized view, not a hidden schedule or secret inventory. A take target can remain a plausible known location until an actual attempt or observation establishes otherwise.

### Submission and Feedback

- Selecting an action or target does not advance time. A Submit Action control sends the selected action once. Show the known cost of one beat before submission.
- During an unresolved submission, disable further action submission. Reading acquired information remains available. Pause and new-game controls wait for that submission to settle, avoiding a race with its commit.
- An accepted receipt shows what A actually perceives, the new beat, and any newly acquired observation. It does not announce hidden facts merely to explain the internal resolution.
- A request rejected before acceptance shows a knowable reason and spends no beat. An accepted action that becomes impossible during the documented resolution sequence spends its beat and returns supported failure feedback.
- Closing the briefing, hovering a target, refreshing the page, or reading an observation never submits an action. There is no extra automatic Continue turn after a receipt.

Human-readable controls should describe available mechanics without recommending a secret solution or disclosing that B is scheduled to move on the next beat.

## Session and Recovery Defaults

Use one local human session per active game for this demo. Bind A on the server side; the client cannot request B's or C's player view by changing a role identifier. This is a local development scope, not a production multiplayer or account system.

Propose SQLite as the demo's local persistence, using the ordinary Python sqlite3 interface and short transactions. This is a demo implementation choice, not a permanent product storage commitment. Store the initial fixture version, phase, beat, current state, actual events, per-character observations, and command receipts. Save each accepted command and its related effects, observations, and outcome atomically. Do not persist hidden world records in browser storage.

| Situation | Proposed default |
| --- | --- |
| Browser refresh or server restart | Restore the last committed phase, beat, custody, and acquired observations; do not rerun the script to catch up with real time |
| Response is lost after submission | Retrieve the current view and receipt; a retry uses the same command identity rather than creating a new action |
| Same command arrives twice | Reuse its original resolution and return the current authorized view; spend no additional beat |
| Same command identity carries different content | Reject the conflict without altering history |
| Another tab submits an outdated command | Reject its stale revision before acceptance and refresh that tab's authorized view |
| Failure before a commit | Keep the previous committed state; do not expose a partial successful receipt |
| End of beat 6 | Persist the last action and outcome together; reject further gameplay actions |
| New game | Create a fresh game identity from the same fixture and retain the old game as read-only history |

The action boundary needs a command identity, expected state revision, supported action, and target. The response needs an acceptance or rejection receipt and A's authorized current view. Exact endpoint paths and serialization can be chosen during implementation. Check a known command identity before treating its old revision as a new stale request; transport retry and a new action are different situations.

Review and replay show only the observations A actually acquired in that game. An earlier event's display time is its occurrence or learning time as recorded; a later discovery must not be relabeled as an earlier direct observation. Replay does not execute actions, reveal the full truth, or provide an undo feature. Development-only truth comparison remains a separate inspection capability.

## First-Run and Completion Criteria

The implementation provides one documented local launch command and a local player interface. The deterministic fixture requires no API credentials; the optional DeepSeek review reads the server-side key. Launching, reading, and ordinary actions make no provider calls. A fresh game is available after launch without manually editing scenario data.

The first implementation is ready for review when a player can complete all three reference outcomes through the browser, refresh and resume correctly, and inspect the resulting authorized observation history. Automated checks should cover authoritative transitions and isolation; browser verification should cover readable feedback, controls, pauses, and outcomes. Record actual implementation paths, launch instructions, and verification results here when they exist.

## Acceptance Cases

1. Remaining in initial reading causes no movement, item transfer, or autonomous script execution.
2. Replaying the same initial fixture and accepted command sequence produces the same actual events, observations, and outcome.
3. A successful beat-1 following request produces actual movement and limited observations, without exposing B's plan or inventory.
4. A late following request does not backfill an earlier visit or change past observations.
5. C receives no hall or study information merely because an event has shared-world effects.
6. Inspecting after placement discovers the letter but does not disclose its unobserved origin. Taking it changes real custody without erasing earlier observations.
7. Unknown or stale targets, unsupported actions, and duplicate command delivery cannot advance extra beats, bypass access, or repeat an outcome.
8. A supported conflict or failed precondition has the documented result; an unsupported combination cannot be narrated as having succeeded.
9. The same fixture supports delivered, incomplete, and not-located outcomes through different command sequences.
10. Ordinary player payloads exclude hidden plans, full world history, other characters' private records, and development-only truth views.
11. Refreshing or restarting restores the last committed game without extra beats, repeated scripts, or changed observations.
12. A lost response, double click, or identical retry cannot repeat an action. Changed content under the same command identity and genuinely stale new commands are rejected without mutation.
13. A reading pause preserves the current beat and scene; resuming does not apply real-time catch-up events.
14. New Game creates a separate initial state. Reviewing an old game or replaying A's observations cannot modify either game or reveal missed events.
15. Scene panels, inventory, maps, action choices, error messages, and normal network responses all preserve A's information boundary.

Reference command sequences for development verification, not player-facing hints:

| Six accepted actions | Expected outcome |
| --- | --- |
| Follow B; inspect drawer; take letter; move to hall; wait; wait | Letter delivered |
| Wait; wait; wait; move to study; inspect drawer; take letter | Recovery with delivery incomplete |
| Wait six times | Letter not located |

## Deferred Capabilities and Expansion Order

The following remain broader product requirements or proposals, not simulated capabilities of this slice: generated categories and introductions; dynamic scenario generation; live AI decisions and dialogue; speech obligations and deception cues; private-chat invitations and dedicated DMs; multiplayer reading; long-running actions, cleanup, interruption, and free-form action composition; random world events; and production deployment.

Proposed expansion after validating the slice:

1. Add one bounded model-controller integration with immutable authorized prefixes, final-request inspection, request accounting, and call/token budgets. Keep scripted controllers as reproducible test doubles. Select a provider and measure actual cache usage and total cost before expanding autonomous activity.
2. Add public dialogue and a small set of model-selected existing actions; models propose actions through the same validation path and cannot create facts or handlers.
3. Add one supported mechanic at a time, such as a two-beat inspection or a consent-based private conversation, with explicit interaction and observation rules.
4. Consider natural-language action composition and scenario-supported randomness only after the earlier behavior remains understandable and verifiable.

## Implementation and Verification Record

Implemented files:

- palter/scenario.py and palter/engine.py: the authored fixture, five actions, deterministic beats, actual events, per-character observations, and three endings.
- palter/storage.py: SQLite snapshots and append-preserving history, command deduplication, ownership, revisions, archives, model-call reservations, and usage.
- palter/server.py and palter/static/: loopback HTTP transport, scoped responses, Chinese interface, action controls, pauses, history, replay, and pending-request recovery.
- palter/deepseek.py and versioned prefix artifacts: credential handling, authorized review, output validation, call limits, and actual usage. See [provider verification](14-deepseek-integration.md).
- environment.yml and README.md: dedicated Conda setup and launch commands. All Python execution and tests use .conda-env/bin/python; no venv or base installation is used.

Launch:

```bash
.conda-env/bin/python -m palter
```

The service is available at http://127.0.0.1:8765. Progress persists in .local/palter.sqlite3.

Verification on 2026-11-04 includes 25 Python engine/storage/HTTP tests, six JavaScript rendering/state-handler tests with a minimal document double, and three actual DeepSeek smoke calls. The HTTP cases exercise all three reference outcomes and server restart through the real transport. Tests use temporary databases and fake model responses unless the explicit live check is selected.

The original browser-control host was unavailable. The user explicitly authorized a headless browser as an alternative. Playwright 1.64.1 was installed only in the project Conda environment and used the installed Microsoft Edge with a fresh temporary profile and Chromium sandbox enabled. No ordinary Edge profile was accessed.

Headless Edge acceptance passed against both the running application with one additional live DeepSeek review and an isolated temporary server with a fake model. Cases covered all three outcomes, reading and active/paused refresh, pause/resume, native double clicking, lost-response retry with the original command identity, readonly archived history, and visible review records. The browser reported no page script errors. A 390 by 844 mobile viewport had no horizontal overflow. Desktop and mobile screenshots were inspected for readable text, controls, and layout.

Evidence artifacts:

- .local/verification/deepseek-live.json: three actual provider calls and fingerprints.
- .local/verification/browser/report.json: the live-server headless walkthrough and actual review usage.
- .local/verification/browser-offline/report.json: repeatable headless acceptance with no paid calls, including the active-refresh and rendered-review assertions.
- .local/verification/browser/ and browser-offline/: introduction, scene, outcome, mobile, and review screenshots as applicable.

### Acceptance Coverage

| Design cases | Evidence |
| --- | --- |
| 1: reading does not run gameplay | Engine reading test; browser reading refresh |
| 2: identical accepted sequence is deterministic | Engine comparison of complete repeated state, events, observations, and outcomes |
| 3-6: following, late requests, isolated observers, and later discovery | Engine observation tests; real browser following and inspection flow |
| 7-8: unsupported requests and preconditions | Engine validation tests; HTTP field, identity, and ownership tests |
| 9: three outcomes | Engine, actual HTTP, and headless Edge reference paths |
| 10 and 15: player information boundary | HTTP scoped payload tests, owner isolation, bounded model-input test, and browser payload checks |
| 11 and 13: recovery and pause | SQLite restore, full HTTP server restart, and browser reading/active/paused reload |
| 12: duplicate, conflict, stale, or lost commands | Concurrent storage tests, JavaScript retry tests, and browser native double click/lost-response cases |
| 14: new game and readonly replay | Storage archive test and headless history selection |

Reproduction commands and optional browser dependencies are in [README.md](../README.md). These checks cover Demo 01, not the deferred full-product capabilities.
