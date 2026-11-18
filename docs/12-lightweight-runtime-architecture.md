# Lightweight Custom Runtime Architecture

Status: EnsembleApplication is the default; legacy saves keep their original runtime.

Last updated: 2026-11-06.

## Local Service Lifetime: 2026-11-06

The earlier foreground launch was verified during its tool session but was no
longer present when the user next visited: host port 8765 had no listener, and
the original execution session was unavailable. The local service now runs as
the transient user systemd unit `palter.service`, with the project Conda Python,
project working directory, loopback binding, journal logs and restart-on-failure.
Its cgroup belongs to the user service manager, independently of the launching
tool session. No boot autostart or network exposure was added. README contains
launch, restart, stop and log commands.

Separate host checks confirmed active/running state, zero restarts, a real
127.0.0.1:8765 listener, and HTTP 200 for the page, frontend assets and session
endpoint. These are service/HTTP checks, not new model-execution acceptance.

## Current Runtime: 2026-11-05

The default stack is EnsembleApplication -> InvestigationApplication -> AIApplication over the existing durable SQLite operation/call records. scenario_cases compiles frozen assets; ensemble_world owns state/effects/projections; ensemble owns membership, scheduling and scoped model calls; ensemble.js renders per-seat views. Existing investigation and item-recovery saves route through their original implementation. No framework was introduced. The server binds loopback by default; an explicit local IPv4 --host supports invited LAN multiplayer, retaining exact Host, same-origin, session and CSRF checks.

Implementation: [complete playable runtime](17-complete-playable-runtime.md). Verification uses `tests/test_ensemble.py`, the multiplayer browser walkthrough and fresh provider receipts listed there. The design alternatives below retain their proposal scope; older implementation sections describe legacy saves.


References: [Conventions](../AGENT.md), [Glossary](../GLOSSARY.md), [World events and actions](04-world-events-and-actions.md), [Time and background activity](08-time-reading-and-background-activity.md), [Input obligations](09-speech-thoughts-and-action-input.md), [System DM](10-system-dm-and-deception.md), [Prefixes and cost](11-prefix-cache-and-cost-control.md).

## Confirmed Direction and Scope

The user wants a custom, lightweight implementation instead of existing frameworks. PALTER should own its scheduling, state transitions, DM coordination, role context construction, and cost controls. Do not introduce an agent orchestration framework or a broad application framework into the initial design.

This document proposes the broader internal architecture. Demo 01 now uses Python 3.12 in a dedicated Conda environment, ordinary modules, SQLite, a standard-library HTTP transport, and a plain browser interface. The user authorized DeepSeek on 2026-11-04; its bounded review integration uses urllib rather than a provider SDK. No application or agent framework is introduced.

Build the modules PALTER needs. Avoid a generic graph language, plugin platform, service registry, or framework intended for unrelated applications.

The current production scope is [AI runtime integration](15-ai-runtime.md), with real role, DM, memory, event, and ending calls. [Demo 01](13-demo-01-action-and-observation.md) remains a historical deterministic regression fixture selected explicitly with --offline. Bounded thread pools support concurrent character/memory work; continuous idle role loops are not used.

## Proposed Deployment Shape

Start with one application process, ordinary modules, one durable store, and bounded asynchronous model calls. A character and a dedicated private DM are logical contexts with separate permissions and lifecycle state, not necessarily processes or services.

Use one authoritative update path per game. Model calls may run concurrently within a configured limit, while changes to shared history are validated and committed in order. Model completion order must not silently determine fictional arrival order, action priority, or elapsed game time.

Do not start with a message broker, distributed workers, a vector database, or separate services for each character. Add infrastructure only when an observed requirement justifies it.

## Proposed Starting Stack

| Area | Initial proposal | Boundary |
| --- | --- | --- |
| Core language | Python 3.12 with explicit records and ordinary functions, implemented in the project Conda environment | No application execution or dependency installation in base or venv |
| Concurrent work | Bounded standard-library HTTP workers for the demo; asyncio remains a future scheduling option | Application-owned rules; model calls run outside database write transactions |
| Durable data | SQLite through sqlite3; explicit SQL and short transactions, implemented for the demo | Deployment scale and storage ownership remain open |
| Scenario assets | Versioned JSON records and text instructions | Validate references and initial consistency before starting gameplay |
| Model access | A thin application-owned provider adapter | Exact provider, HTTP library or SDK, models, and pricing are undecided |
| First verification interface | A local command runner for controlled sessions | A development aid; it does not settle the player-facing interface |
| Player interface | Plain HTML, CSS, and JavaScript over local HTTP, implemented for Demo 01 | Broader deployment remains open; browser acceptance is recorded in the demo module |

Python's official documentation describes asyncio's concurrent tasks and queues and sqlite3's access to a lightweight database without a separate database server. These capabilities support this proposal; they do not establish PALTER's eventual performance or deployment capacity. [asyncio](https://docs.python.org/3/library/asyncio.html), [sqlite3](https://docs.python.org/3/library/sqlite3.html)

Avoid implementing HTTP parsing, TLS, or a database engine as part of custom game orchestration. If a network interface is selected, evaluate a small protocol implementation separately and keep it outside the game rules.

## Proposed Module Responsibilities

| Module | Owns | Boundary |
| --- | --- | --- |
| Session runtime | Reading, readiness, pause gates, permitted decision opportunities, timers, response obligations, and private-session lifecycle | Does not infer fictional time from network latency |
| World and scenario rules | Current world state, validated action outcomes, scenario event triggers, and ending conditions | Claims and tentative thoughts do not directly alter the world |
| System DM | Language interpretation where needed, supported claim assessment, actual behavioral cues, and recipient perception | Remains outside the fiction and submits effects through the common update path |
| Character controller | A human command or an AI decision from that character's authorized view | Does not obtain global secrets or automatically learn missed events |
| Context builder | Immutable prefix artifacts, scoped retrieval, dynamic suffixes, and private-context isolation | Does not use cache identity as an access-control decision |
| Model gateway | Provider requests, concurrency limits, budget reservations, bounded retries, usage, and attributable cost | All billable work passes through this boundary |
| Storage | Actual events, current-state records, acquired information, session metadata, and request accounting | Persistent truth does not depend on model context or cache residence |

These are responsibilities, not a requirement for seven services or seven extra model calls. Initially they can be a small number of modules in one package, split further only when responsibilities become difficult to maintain.

Character actions and world events share an [event data structure](04-world-events-and-actions.md) carrying execution properties such as timing, prerequisites, compatible activities, interruption, observation, and resolution. The runtime schedules validated instances from those definitions. A pending instance is distinct from committed facts about its actual start, progress, or outcome; model completion alone cannot complete a timed in-world action. Exact fields and lifecycle remain proposals.

## Proposed Input and Resolution Flow

1. Receive an input with an authenticated participant identity, game, communication scope, command identifier, and observed state version. The server derives authority; a supplied role ID does not grant it.
2. Check the session phase, reading or pause gate, channel membership, obligations, and scenario eligibility. Keep thoughts, speech, and action requests distinct.
3. For work requiring language interpretation or an AI decision, build the authorized context and reserve the applicable call budget before sending the request. Perform the model call outside a database write transaction.
4. Treat generated results as candidates. On completion, recheck the current phase, conversation lifecycle, relevant facts, and action preconditions. A result for a closed conversation or changed object must not silently take effect.
5. Create or advance the validated event instance under its timing and execution rules. Resolve only effects that are actually due; record any actual cue or random result once, then commit the occurrence, current-state changes, and authorized perception records consistently.
6. Deliver only the recipient's allowed view. Create obligations after actual receipt; do not deliver missed outside history to a privately occupied character.
7. Schedule bounded follow-up opportunities only if the game phase and remaining budgets allow them. A completed request must not automatically bypass a pause or begin an unlimited AI exchange.

This flow does not settle the open pause-result policy. Under the existing buffering proposal, a completed result waits until resume and is revalidated before application. Other policies require an explicit decision in the time module.

Language interpretation and uncertain action adjudication may need a model. Structural validation and precondition checks still belong to application code. Unsupported actions must receive a defined clarification or adjudication path rather than inventing a successful result.

## Shared History, Conflicts, and Recovery

The main DM and every private DM share one world history. A private DM may retain its own conversation state but cannot independently declare that it owns an object or that an action has succeeded.

For example, if A attempts to destroy a letter while B attempts to take it, the scenario's action-order rule determines what happens. The runtime must not let both report success simply because their model requests ran concurrently. Whether priority uses declared time, an action window, or a random tie-break is a product decision still to be made.

Proposed persistence rules:

- Assign commands stable identifiers so delivery retries do not repeat an in-world action.
- Keep committed actual events append-only; update current-state projections from accepted effects.
- Persist the realized random choices and generated behavior. Restoring a session must not reroll an established killer, cue, or action outcome.
- Commit related event and state updates atomically. Keep database transactions short and do not wait for model responses while holding them.
- Record delivery state separately from public availability, so reconnecting does not accidentally grant private participants knowledge of outside events they missed.
- Reconstruct a session from stored events and snapshots without calling a model to rewrite history. Check that a recovered state matches the last committed state.
- Persist model request status and usage separately from world commits. An uncertain network outcome may still be billable; do not automatically retry forever or assume that an uncommitted action cost nothing.

SQLite permits multiple read transactions but only one simultaneous write transaction. The proposed store therefore serializes short writes; per-game ordering alone does not remove database-wide write contention. Larger deployments require measured storage evaluation. [SQLite transactions](https://www.sqlite.org/lang_transaction.html)

## Scenario Boundary

Represent a scenario with its versioned initial setup, permitted action definitions, event triggers, observation conditions, objectives, and stopping and outcome rules. A small explicit interface between these rules and the runtime is sufficient initially.

The shared runtime must not assume a murder, a mandatory night phase, a single killer, or a daily evidence limit. Keep those policies in their relevant scenario modules. Use at least one contrasting scenario fixture when evaluating whether a supposedly shared mechanism has accidentally embedded murder-specific assumptions.

Generated introductions and initial scenario material also need validation. A preview does not advance the game, and an accepted starting setup must remain causally stable while later actions change current state.

## Prefix and Cost Foundation

Implement the [prefix and cost module](11-prefix-cache-and-cost-control.md) alongside the first runtime slice, before expanding autonomous play:

- Build immutable authorized baselines and inspect the final serialized provider request.
- Keep changing observations, relationships, conversation turns, and current requests after the protected baseline.
- Give each private DM a scoped context, sharing only authorized identical instructions rather than duplicating the full world.
- Reserve budgets centrally so concurrent requests cannot each assume the same remaining allowance. Reconcile reported usage afterward, keeping unknown charges explicit.
- Track calls, input categories, output, retries, latency, and total activity cost. Baseline immutability alone does not demonstrate provider cache hits.
- Use relevant events, pending responses, timers, or permitted action opportunities to schedule work. Do not continuously ask every character whether it wants to act.

An initial fake provider can verify orchestration, permissions, and budget behavior without paid calls. It cannot verify model quality, provider cache behavior, latency, or actual billing savings; those require a later measured integration.

## Proposed First Playable Scope

Use one human plus a small AI cast, one concrete scenario, text interaction, public speech, optional thoughts and action requests, accepted private conversations, bounded world events, and a causally resolved ending. This is a proposed development sequence, not a restriction on the eventual multiplayer product.

Do not begin by generating every category or implementing all scenario modules. Build one complete path while checking shared rules against contrasting fixtures. A murder investigation is a convenient first candidate because its opening already has detailed examples; its release priority is not confirmed.

Suggested implementation order:

1. Define the event, world-state, knowledge, scenario, command, and prefix records; run a local session with a fake provider and a small authored fixture.
2. Establish reading and pause gates, authoritative updates, per-recipient delivery, recovery, and request/budget accounting. Verify conflict handling and information isolation before expanding autonomy.
3. Integrate one selected provider; measure actual prefix reuse, cost, quality, and latency for a complete representative flow before expanding model activity.
4. Add bounded character decisions, public and accepted private conversations, scene actions, and ending evaluation around that foundation; then connect the chosen player interface.

## Decisions to Resolve Next

| Decision | Proposed starting point | Why it matters |
| --- | --- | --- |
| Active-play time and simultaneous actions | Explicit scene action windows plus dialogue opportunities; detail the relation to real-time deadlines | Determines scheduler ordering, interruptions, and conflict resolution |
| First playable mode and cast | One human with a small AI cast | Bounds initial orchestration and cost without changing future multiplayer requirements |
| Human action input | Natural language mapped to explicit supported action requests; ask for clarification when ambiguous | Keeps creative input grounded in actual executable effects |
| Player interface and deployment | Local development first; browser interface as a candidate | Determines transport, delivery, reconnection, and access requirements |
| Provider and budgets | One measured provider integration with per-game and private-session caps | Prevents an unbounded autonomous loop from defining the cost |
| Language and persistence | Python plus asyncio and SQLite | Supplies a concrete lightweight proposal to assess before creating application code |
| Setup generation and stopping rules | Validate one initial scenario and define its outcome triggers explicitly | Avoids improvisation that rewrites the setup or forces a preferred ending |

Use existing modules for the detailed remaining choices, including speech intervals, chat caps, pause-result application, deception cues, and final disclosure. There is no need to reopen already confirmed boundaries.

## Legacy Demo 01 Implementation and Verification

Production defaults to AIApplication, ai_world, and ai_gateway with real DeepSeek task calls. The runtime uses Python 3.12 in .conda-env, standard-library HTTP/urllib, SQLite, explicit per-game operations, bounded thread pools, and vanilla browser source. Network calls execute outside database transactions. Completed stages are persisted for duplicate-safe recovery; world effects commit together only against the original unchanged history. No agent or application framework is introduced. The old Application/engine fixture is available only through explicit --offline mode; saved legacy games are read-only in AI mode. See [AI runtime](15-ai-runtime.md) for the task matrix and evidence.


## Legacy Demo 02 Implementation: 2026-11-05

The server now defaults to InvestigationApplication, which subclasses the durable AI operation runtime and routes older saved games to their original rules. case_world owns frozen case contracts, evidence and scoped views; investigation owns decision opportunities and accusation. The stack remains standard-library Python, SQLite and a local browser; no new framework is introduced.
