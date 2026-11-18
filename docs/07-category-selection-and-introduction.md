# Category Selection and Story Introduction

Status: Seven distinct selectable scenario mechanics and generated public previews implemented.

Last updated: 2026-11-06.

## Current Runtime: 2026-11-06

The selector maps to murder, theft, family, council, rescue, house and archive. Each has distinct effects and outcome predicates, documented in its scenario module. A real model produces three independent preview candidates in one request; the selected premise and cast are persisted. No previous player story is supplied for diversity, and no setting blacklist or prose filter is used.

### Model-authored names: v60

Earlier previews shuffled a fixed list of 30 names and required the model to use
the supplied roster. This caused repeated casts. The user requested free naming;
new ensemble and investigation previews now author each candidate's four names
and its separate designated story person together with its premise. No roster,
name dictionary or concrete example name is supplied. Context guidance asks for
names appropriate to the era, culture, setting and people, varied across the three
candidates. The extra person is a dead victim only in murder scenarios.

The selected cast is saved exactly as returned and passed unchanged into setup,
authoritative history and subsequent role contexts. Structural validation requires
four participant IDs, nonempty bounded names and five distinct people; it does not
rewrite generated prose or score naming style. Names need not be globally unique
across independent games. The same preview call supplies the names, with no extra
naming or review call. Its output cap is 1,800 tokens for all three candidates.

The old fixed roster remains only for operations pinned to pre-v60 versions, so
their request hashes and recovery stay reproducible. Existing games keep their
original names. Tests cover generated-name preservation through setup and duplicate
creation, distinct entity identity, and the older roster request contract.

Verification: 207 Python regression tests pass. Six ensemble browser checks pass
with no page errors. An independent real Flash probe generates previews for
murder, family and council, and confirms the murder setup. All four calls complete
for USD 0.003940152; no request contains a supplied roster. The nine candidates
contain 45 distinct names in this sample, and the selected murder names survive
setup unchanged. This supports free generation, not guaranteed uniqueness across
future games. Receipts: `.local/verification/generated-names-20261106/live-f8ad5e09.json`,
`tests.log` and `browser-ensemble.json` in that directory.

V60 is deployed to the local service (PID 640853). The page, four static assets and
session API return HTTP 200; all 26 saved-game hashes remain unchanged against
`pre-generated-names-20261106-212922.sqlite3`. See the same directory's deployment
receipt. New games use generated names; existing games are not renamed.

Implementation: [complete playable runtime](17-complete-playable-runtime.md). Verification uses `tests/test_ensemble.py`, the multiplayer browser walkthrough and fresh provider receipts listed there. The design alternatives below retain their proposal scope; older implementation sections describe legacy saves.


References: [Conventions](../AGENT.md), [Initialization](01-game-initialization.md), [Scenario catalog](scenarios/README.md), [Goals and endings](06-goals-and-endings.md).

## Confirmed Direction

- Provide multiple broad story categories.
- The user chooses a category and receives a generated story introduction.
- The user reviews and confirms the selection before starting.
- The introduction must not interfere with later gameplay.

The current design interprets the final requirement as a spoiler-free public preview that does not run gameplay or preselect future decisions and outcomes. Exact presentation and generation mechanics remain proposals.

## Proposed Category Catalog

| Category | Main experience | Initial scenario proposals |
| --- | --- | --- |
| Mystery and Investigation | Compare accounts, find clues, reconstruct events | [Murder investigation](scenarios/01-murder-investigation.md), [Theft and deception](scenarios/02-theft-and-deception.md) |
| Relationships and Drama | Secrets, loyalties, trust, difficult choices | [Reunion and family secrets](scenarios/03-reunion-and-family-secrets.md) |
| Factions and Negotiation | Alliances, competing interests, agreements | [Council and succession](scenarios/04-council-and-succession.md) |
| Adventure and Survival | Exploration, cooperation, limited resources | [Isolation and rescue](scenarios/05-isolation-and-rescue.md) |
| Horror and the Uncanny | Uncertainty, tension, consistent hidden explanations | [The changing house](scenarios/06-the-changing-house.md) |
| Puzzles and Exploration | Combine partial knowledge and investigate mechanisms | [The sealed archive](scenarios/07-the-sealed-archive.md) |

This is a proposed taxonomy, not an asserted exhaustive classification. Tone, period, difficulty, and emphasis may be separate tags. A humorous or historical style need not become a separate primary category.

Codex creates and expands the corresponding modules from the user's examples. Category names and module scope can evolve during design.

## Selection Flow Proposal

1. Choose a category.
2. Prepare a candidate premise and its public introduction.
3. Review the introduction.
4. Confirm to begin, request another candidate, or return to category selection.
5. On confirmation, enter initialization and the mode-specific initial reading phase.
6. Begin interactive play after the reading start condition is met, as specified in [Time reading and background activity](08-time-reading-and-background-activity.md).

Detailed controls, participant configuration, and whether multiple candidates appear together remain open. Preparing a candidate may prepare public setup data, but it must not execute the session's future actions.

## Public Preview Content

A candidate introduction may contain:
- Title, category, tone, and public setting.
- The situation that brings the characters together.
- Public stakes and the general kinds of interaction involved.
- Participant requirements and other already-defined public constraints.
- Enough atmosphere to decide whether to start.

Estimated duration should appear only when supported by design or testing. Hidden roles, private relationships, initial secrets, clue answers, planned surprises, and future endings are excluded.

### Illustrative Introduction

At a remote mountain relay station, a worsening storm interrupts the final supply journey. A small group must decide what to preserve, whom to trust, and how to use the station's remaining routes and resources before contact can be restored.

This introduces setting and experience without revealing private motives, a successful escape route, specific future events, or who will cooperate.

## Preview and Gameplay Boundary

Treat the introduction as a public view of a candidate premise:
- Browsing or regenerating wording does not advance game time, consume actions, alter relationships, or trigger world events.
- Generating a preview does not execute an opening procedure or participant decision, nor assign a future outcome. Scenario background facts may be prepared as setup; later choices follow their actual gameplay rules.
- The selected public premise must match the game that starts.
- Rewording an introduction for the same candidate preserves its underlying public setup.
- Replacing the candidate is an explicit selection operation, distinct from rewriting its introduction.
- Confirmation begins initialization and initial reading; it does not bypass the reading gate. Previewing alone starts neither gameplay nor autonomous AI activity.

The current local interface is Chinese and SQLite retains game state; broader deployment remains undecided. English documentation does not require an English product interface.

## Open Questions

- Adopted categories, tags, and how users select them.
- Which cast and public constraints are chosen before preview.
- One candidate or several, and replacement controls.
- Generation and validation of a consistent public premise.
- Treatment of private starting information after confirmation.
- Exact meaning of any additional restrictions the user intends for non-interfering previews.

## Legacy Demo 01 Implementation and Verification

The Chinese interface offers six provisional categories: mystery, relationships, negotiation, survival, uncanny, and exploration. A real introduction call receives only the category and supported public mechanics. Confirmation generates private setup; ready starts play. Preview browsing and reading do not run characters. All six categories currently share the small recoverable-item map and bounded deadline, with generated presentation and character motivations; this is not six complete physical scenario engines. The murder module and other catalog mechanics still need explicit implementations.

## Agent Prose Direction: 2026-11-04

Player-facing introductions use natural in-world names, such as the waiting hall,
luggage office, and tea stall. Internal location keys and variable annotations
belong only in structured control data, not in the introduction or character prose.

The user explicitly requires skill/context guidance, scoped to text shown to
players, to reduce this behavior. The current implementation uses concise task
instructions in immutable ai-tasks-v6.json: use natural language and in-world
names in player-visible prose, and retain IDs in structured control fields.
The ambiguous former instruction asking for public location IDs was removed in
the new version. Other published prefixes remain unchanged. There is no Agent
self-review step, extra review call, text filter, or prose-matching rejection.
Internal-only state and private machine data keep their existing representation.
Already-recorded story text is not rewritten by this instruction update.

### Avoiding Example Anchoring

The earlier v8 introduction context contains no named-location example. It
requests fresh, category-appropriate premises with freedom in setting, era,
atmosphere, central conflict, and target object. Introduction temperature is 0.9.
This is contextual creative guidance, not an output blacklist or a self-review
stage. No earlier user introductions are included in the generation request.
Specific language examples must not become shared scenario templates.

### Independent Candidate Batch: 2026-11-04

The user continued to receive harbor-centered stories after the v8/v9 context
changes. Removing the named example and adding a numeric creativity seed did not
establish sufficient variety in actual samples. The current v11 introduction
task generates three independent public premises in one call, explicitly varying
era, social environment, activity, conflict and object across the alternatives.
No predefined settings or previous player stories are supplied. Chinese is the
presentation language, not a prescribed era or geographical setting.

The game identifier selects one candidate before initialization. Its selection
is stable across retries, and the completed model stage is reused. The player
and initial-setup task receive only the selected premise; alternatives cannot
leak into the chosen game's history. Earlier operations pinned to a single
candidate task version retain their original response shape. No output scoring,
blacklist, prose rewriting, reroll or additional model call is introduced.
The introduction uses temperature 0.9 and a 1,800-token cap for all three
candidates together; the per-game call and cost guards are unchanged.

Nine real new-game calls completed, including four mystery games and one of
each other category. Selected settings included a community utility dispute,
theater troupe, farm, archive, factory, border negotiation and polar station.
One coastal story remained; the implementation permits coastal settings.
This sample supports improved variation, not guaranteed uniqueness or complete
semantic adherence to every scenario constraint. The local report is
.local/verification/ai-tasks-v11-variety-03d2673b.json.


## Legacy Demo 02 Implementation: 2026-11-05

New games now prioritize mystery: one real call supplies three independent murder premises, one is selected, and confirmation generates the complete fixed case before reading/play. Other category-specific engines remain future work. The investigation flow and latest task contract are in [Demo 02](16-demo-02-deduction.md).
