# Game Initialization

Status: Four-seat mixed/all-human initialization and optional murder opening implemented.

Last updated: 2026-11-06.

## Current Runtime: 2026-11-05

New games assign one to four human seats through server-owned room membership. Other seats use real AI. The public three-candidate preview precedes setup. Murder optionally collects willingness and arrival handling, applies willing-human priority and no-volunteer fallback, and freezes exactly one killing before private reading. Scene facts and role scripts remain immutable thereafter.

From v60, the preview model creates its own names rather than receiving a fixed
name pool. The selected cast and designated story person are fixed before setup,
then reused without renaming throughout play. Existing saved names and pinned
preview operations retain their original identities; see module 07.

Implementation: [complete playable runtime](17-complete-playable-runtime.md). Verification uses `tests/test_ensemble.py`, the multiplayer browser walkthrough and fresh provider receipts listed there. The design alternatives below retain their proposal scope; older implementation sections describe legacy saves.


References: [Conventions](../AGENT.md), [Glossary](../GLOSSARY.md), [Category selection](07-category-selection-and-introduction.md).

## Purpose and Scope

Create an initial world, cast, memories, and relationships from the selected scenario. The same setup can develop into different histories through subsequent choices and events.

Initialization is shared across categories. The murder arrival sequence is one scenario-specific opening; other stories define their own conflicts and procedures.

## Initial Setup

| Component | Information |
| --- | --- |
| Setting | Location, time, environment, accessible areas |
| Premise | Public situation, background events, conflicts, constraints |
| Cast | Character count and human/AI assignments |
| Personas and relationships | Identities, traits, connections, private attitudes |
| Memories | What each character experienced, observed, heard, or misunderstood |
| Scenario rules | Actions, event conditions, budgets, goals, stopping conditions |

Exact schemas and generation order remain open. Hidden background facts must be consistent with the public introduction and each character's initial information.

## Entry into Play

1. Select a category and review a spoiler-free candidate introduction.
2. Confirm a candidate to start.
3. Prepare world state, cast, memories, and initial relationships.
4. Enter the initial reading phase. Provide the script and private starting information while holding autonomous gameplay.
5. Release the reading gate under the [single-human or multiplayer readiness policy](08-time-reading-and-background-activity.md).
6. Apply the selected scenario's interactive opening procedures and participant decisions.
7. Resolve actual events and derive personal experiences, state changes, and traces.
8. Continue into the scenario's interaction, investigation, action, or other progression model.

Previewing a candidate has no gameplay effects. Session creation, data loading, and how much candidate setup is prepared in advance remain implementation decisions.

Initial single-human reading has no deadline. Multiplayer reading has a deadline and can finish early when all human readers select Reading Complete. Reading time is distinct from active gameplay; AI characters cannot use this phase to act, talk, or privately negotiate ahead of the humans.

## Murder Opening Example

The user's concrete opening is preserved in the [murder investigation module](scenarios/01-murder-investigation.md). Participants choose whether to kill the target; arrival order, human priority, and fallback assignment produce one actual killer. Later arrivals encounter a victim who is already dead.

Characters may inspect or touch the scene, leave traces, and conceal visits for personal reasons. Finding a body does not establish witnessing the killing or knowing the killer.

| Illustrative order | Experience | Consequence |
| --- | --- | --- |
| A first | Kills the target and leaves while a cup remains on the table | A remembers its own actions and departure scene |
| B later | Finds the body, stains a sleeve while inspecting, and knocks over the cup | B has a different experience; the scene now contains fragments |
| C last | Finds the body and fragments, accidentally losing a button | C observes the changed scene and may not notice the lost button |

A and C can truthfully remember different cup positions. Exact objects and timing are examples, not required content.

## Module Boundaries

Actual events inform [state and evidence](02-memory-state-evidence.md). Individual experiences determine what each character learns. Interpersonal information is covered by [relationships](05-character-relationships.md).

## Open Questions

- Initial data schemas and generation order across categories.
- Cast assignment and delivery of private starting information.
- Presentation of opening choices and scenario-specific fallback assignments.
- Transition into the chosen time and action model.
- Consistency checks between introduction, background, memories, and relationships.

## Legacy Demo 01 Implementation and Verification

palter/ai_runtime.py generates a public preview and, after confirmation, calls DeepSeek for a validated setup with three personas, private initial memories/goals, directional relationships, room descriptions, and actual item custody. Initial reading launches no role turns. Initial profiles remain frozen while acquired memory evolves separately. Cast size is currently one human plus two AI roles; the full murder-opening procedure and additional physical scenario modules remain unimplemented. See [AI runtime](15-ai-runtime.md).


## Legacy Demo 02 Implementation: 2026-11-05

New investigations bind four living participants and a separate victim in the preview. Confirmation generates the complete case once under a fixed causal contract. Past truth, evidence, initial personal knowledge and proof dependencies are locked before reading begins; subsequent choices and the ending remain open. See [Demo 02](16-demo-02-deduction.md).
