# AI Runtime Integration

Status: Implemented legacy item-recovery runtime; retained for existing saves. New games use the ensemble runtime in module 17.

Last updated: 2026-11-05.

References: [Conventions](../AGENT.md), [Initialization](01-game-initialization.md), [Communication](03-communication.md), [Relationships](05-character-relationships.md), [Introductions](07-category-selection-and-introduction.md), [DM](10-system-dm-and-deception.md), [Prefix and cost](11-prefix-cache-and-cost-control.md), [Earlier offline fixture](13-demo-01-action-and-observation.md).

New-game behavior and its separate verification are recorded in
[the complete playable runtime](17-complete-playable-runtime.md). The records below apply
to the historical item-recovery runtime and must not be read as evidence that
a generated investigation case is solvable or enjoyable.

## Corrected Requirement

The first implementation used a fixed character schedule and called DeepSeek only
for observation review. The user explicitly identified this as insufficient and
requires all designed AI responsibilities to use actual model calls. The following
matrix is the production implementation checklist. The old deterministic fixture
remains an explicitly selected offline/test mode; it cannot be an automatic fallback.

| Responsibility | Model input boundary | Required use of output |
| --- | --- | --- |
| Public introduction | Selected category and public engine capabilities only | Generated public candidate shown before confirmation; no play progression |
| Initial setup | Confirmed introduction and supported world schema | Initial personas, memories, directional relationships, private objectives, and actual starting facts |
| Character decisions and speech | That character's immutable initial baseline, acquired observations, memories, relationships, and currently permitted choices | Selected supported action and generated speech actually executed/delivered |
| Human free-form action interpretation | Human's input and authorized view, plus supported operations | Clarification or a validated action request; no inferred human strategy change |
| Main DM | Actual events, utterances, and relevant speaker knowledge | Grounded claim assessment and actual observable cues; preserve original words |
| Private DM | One accepted conversation, its participants, exchanges, and relevant adjudication facts | Dedicated per-conversation handling without exposing private content or missed outside events |
| Memory and relationships | Each character's acquired experiences and prior interpretation | Updated private memory summary and relationship experiences with source references |
| World-event selection | Actual current conditions and explicitly supported event effects | A validated event choice that changes the world when eligible |
| Ending | Actual resolution and the recipient's allowed experience | Generated personal ending/recap grounded in recorded sources |
| Observation review | Acquired observations only | Existing record selection, as already implemented |

## Runtime Boundaries

- Preserve one authoritative world, ordinary Python modules, the project Conda
  environment, and explicit supported effects. Model outputs are proposals, not
  permission to execute code, rewrite history, or change the human's decisions.
- Use independently fingerprinted task and role baselines. Freeze initial persona,
  memories, and relationships; dynamic observations and evolving interpretations
  follow the baseline. Private-DM baselines are separate conversation artifacts.
- No role receives another role's private thoughts, hidden state, or global event
  log. Main/private DMs can use internal facts without exposing their assessment.
- Public invitation and explicit agreement precede private chat. Retain a dedicated
  DM until the conversation closes. Limit private exchanges and duration. Occupied
  participants receive no automatic outside history and can ask after returning.
- Use bounded event-driven opportunities for AI activity, not continuous idle
  polling. Initial reading blocks autonomous decisions. Pausing prevents new calls;
  an already-running call can finish and its result is buffered for validated resume.
- Persist an operation identity before billable work. Cache completed stage results
  for safe recovery; retries cannot reroll a committed action or duplicate a charge.
  Keep database transactions short and outside network calls.
- Preserve required responses and periodic speech as explicit obligations. An
  uncertain factual claim is not proven deception, and a cue is not a truth badge.
- Store task, actor/scope, prefix/request fingerprints, provider usage, latency,
  status, and resulting event linkage. Normal player traces expose call metadata,
  not secret prompts or private decisions. A provider failure is visible and never
  replaced with a hidden scripted action.

## Concrete First AI Implementation

Keep one human and two AI roles, a small supported map/action vocabulary, and
bounded scene/action opportunities. Generate the story's public presentation,
personas, initial memories, relationships, goals, and initial object custody from
the selected category. The old per-beat B/C schedule must not run in AI mode.

Each human interaction can trigger eligible role decisions, supported effects,
DM handling, and private memory interpretation. World-event selection is bounded
by action opportunities. Public and private utterances preserve actual speaker
wording. NPC speech is generated by its role controller, not templated dialogue.

Expose natural-language speech, optional private thoughts, explicit action attempts,
private invitations/consent, and conversation exit in the interface. Keep ordinary
action buttons as an accessible alternative to natural-language requests.

Generated content must stay within supported mechanics; category flavor does not
authorize unsupported physical capabilities. The full murder-opening and other
scenario-specific mechanics still require their own explicit execution rules.
This does not justify substituting scripts for the AI responsibilities above.

## Verification Required Before Completion

- Actual DeepSeek requests for each applicable task kind, not fake-provider tests alone.
- Different valid model decisions must cause corresponding different actual actions;
  no fixed beat schedule can override them.
- Public preview has no gameplay effects; initial reading starts no role turns.
- Private baseline isolation, consent, bounded exchanges, missed-event isolation,
  and memory/relationship updates tied to each recipient's own observations.
- Pause/resume and duplicate/in-flight operation recovery without repeated calls or
  stale world commits; failures remain visible and attributable.
- Real browser walkthrough of a generated game, actual AI dialogue/decisions,
  private chat, input interpretation, and generated ending.
- Current runtime/code/UI traces and updated module records identifying actual
  coverage and any remaining unsupported scenario mechanics.

## Implemented Timing and Limits

The local demo uses one human and two AI roles, three connected rooms, one
recoverable item, and an initial six-beat deadline. Code implements move, inspect,
take, place in the study drawer, one visible movement of following, and wait.
An explicit natural-language attempt is a separate real model task that selects
one permitted operation or asks for clarification. Initial setup chooses actual
item custody; no per-beat character schedule runs in AI mode.

Each eligible human interaction increments a dialogue round. Physical actions
and private exchanges also advance a beat. Public dialogue does not automatically
advance the physical clock. B/C receive independent decision opportunities and
may initiate invitations with each other. Maximum provider concurrency is two;
there is no idle polling loop making paid decisions.

Addressed questions require a word/nonverbal response. After three interaction
rounds, a spoken contribution is required; a gesture does not reset it. General
event-specific explanation obligations remain a further module. Private sessions
have a 90-active-second duration and four-utterance cap, checked on interactions
and state reads. Pausing extends their expiry. Missed public history is not
backfilled when the participants return.

World choices are none, courtyard route closure/reopening, and one deadline
extension to seven beats. They are supported current changes, not surprise clues
or altered past facts. All categories use this bounded mechanical vocabulary;
they do not yet implement the complete murder opening, arbitrary evidence
cleanup, multiplayer, or every physical scenario in the catalog.

## Persistence, Prefixes, and Recovery

The default CLI instantiates AIApplication. The old Application and scripted
engine are available only through --offline; legacy saves are read-only in AI
mode. The regular local service retains .local/palter.sqlite3.

ai_operations stores command identity/content, original world, pinned task-prefix
version, status, and receipt before billable work. Completed stage results are
reused only when their request hash matches. Pending network work can finish
during a pause but does not commit; resume reuses completed stages. Cancellation
prevents late commit and retains actual usage. Requests execute outside database
transactions; the final world commit checks the original history and observations.

Core/task artifacts remain immutable. Current defaults are ai-core-v1.txt and
ai-tasks-v11.json, with source hashes verified at startup. Older published task
versions remain available for pinned operations. Private-DM baselines remain
separate per accepted conversation. Public-DM adjudication omits other channels'
utterance bodies; private-DM facts and claim source IDs are limited to its
provided relevant records. Ordinary player payloads contain no global truth,
other-role thoughts, prompts, or DM verdicts.

Limits are 128 requests per game, two explicit attempts per stage, three reviews,
60,000 request bytes, and per-task output caps. New requests stop at the USD 0.25
cumulative estimate threshold, with conservative reservations for unknown usage.
This is not a provider invoice ceiling. Memory generation has a 1,200-token cap
and concise-summary instructions; the initial 550-token cap proved insufficient
in real play. Equivalent relationship maps are normalized to validated updates;
no authored decisions or generated replacement facts are supplied by this code.

## Actual Verification Record: 2026-11-04

The Python suite passed 35 tests, including real-model task orchestration with
explicit doubles, scoped private canaries, model-choice effects, addressed-response
requirements, stale private-message rejection, duplicate commands, in-flight
pause/recovery, HTTP ownership/CSRF, and the historical fixture. Six JavaScript
checks passed. The pause-recovery test switches the deployed default task version
before recovery and confirms that the pinned original stages are reused.

Actual DeepSeek execution, separately from fake-provider regression evidence:

| Evidence | Successful task kinds | Total paid requests including failures | Input tokens | Output tokens | Reported cache-hit tokens | Peak-price estimate USD |
| --- | --- | --- | --- | --- | --- | --- |
| Direct full feature matrix | All ten | 64 | 159,042 | 10,231 | 41,467 | 0.047798502 |
| Headless Edge full game | All ten | 70 | 181,850 | 10,987 | 55,296 | 0.051482376 |

The direct feature matrix recorded 32 actual events linked to model character
decisions, one accepted private conversation with two private exchanges, and a
generated personal ending. Task counts: introduction 1, setup 1, character 16,
action 1, main DM 8, private DM 1, memory 25, world event 6, review 1, ending 1.
Three failed outputs are retained: two initial JSON-structure failures and one
ending missing a required source field. New immutable task versions addressed
these failures, and explicit recovery reused completed stages.

The real browser game covered generated introduction/setup, no autonomous work
while reading/paused, public model speech, voluntary private agreement, dedicated
private-DM execution, recipient isolation, private thoughts, interpreted actions,
review, desktop/mobile layouts, generated ending, and reload persistence. It
reported no page script errors and no horizontal overflow at 390 by 844. A memory
output exceeded the former cap twice; the report retains both charges. After
correcting the budget/summary constraint, the same saved game was restored after
server/browser restart, its failed round was visibly cancelled, and subsequent
AI rounds completed the story. This was not a fresh uninterrupted success claim.

The independent provider-double browser run covers the same interface paths
without paid requests. It is regression evidence only. Screenshots were inspected
for readable controls and layout; provider cost numbers above are reported-usage
estimates using the dated peak rate card, not reconciled invoices.

Local artifacts (excluded from Git):

- .local/verification/ai-runtime-live.json: full real task matrix and usage.
- .local/verification/browser-ai-live-final/report.json: real browser record.
- .local/verification/browser-ai-live-final/desktop-active.png,
  mobile-active.png, desktop-ending.png: current real-game screenshots.
- .local/verification/browser-ai/report.json: explicit-double browser regression.
- Protected SQLite databases alongside reports retain private diagnostic data;
  never publish them or expose their responses as ordinary player traces.

These checks prove bounded feature execution and recovery. They do not establish
perfect model factual judgment, guaranteed provider caching, unbounded narrative
mechanics, production load behavior, or multiplayer support.

## Agent Prose Context Update: 2026-11-04

The user reported location variables in the introduction and chose context
instruction to reduce them only in text shown to players. New operations pin
ai-tasks-v6.json. Concise task instructions request natural Chinese and in-world
names in introductions, labels, briefings, dialogue, human clarification,
A's displayed memories/relationship reasons, and personal endings. Structured
IDs and internal-only state retain their existing roles. The misleading request
for public location IDs was removed from introduction guidance.

The user explicitly excluded self-review and programmatic prose matching/removal.
No extra review call, self-check stage, text filter, or prose-rejection rule is
installed. Human words, recorded history, and earlier published prefix artifacts
remain unchanged. Guidance reduces the chance of variable leakage; it is not a
hard guarantee about every model output.

A real DeepSeek introduction generation using the reported paragraph and v6
context returned the three Chinese place names directly, with no parenthesized
location codes. This used one ordinary generation call (593 input tokens, 139
output tokens, 128 reported cache-hit tokens); there was no self-review call or
programmatic prose transformation. The public result and usage are retained in
.local/verification/prose-context-live.json. Ten AI-runtime regression tests
passed. The local service was restarted with the new default task context.

## Story Variation Context Correction: 2026-11-04

A specific ferry-terminal location example in the v6 introduction guidance
anchored repeated premises in a similar harbor setting across categories. The
current v8 task context replaces this with setting-neutral language guidance,
requests an independently imagined premise suited to the selected category,
and allows the era, social situation, atmosphere, locations, object, and central
conflict to vary. The deadline is described generically rather than as a
meeting/departure template. Introduction sampling temperature is 0.9; other
tasks retain their existing settings. Older pinned operations retain their
original instructions and sampling settings.

The generator uses no setting blacklist, output filter, self-review step, or
mandatory setting catalogue. The historical-story context path considered during
development was removed. No previous user story is sent as variation context.
The normal candidate generation input remains the selected category and the
supported public mechanics. The gameplay mechanics remain bounded independently
of the generated fictional setting.

## Preview Diversity and Take Recovery: 2026-11-04

The v9 variety report still clustered around harbors, fog and tides. A subsequent
v10 single-premise experiment varied the social conflicts but remained clustered
around old towns and recorded one malformed JSON response in eight attempts.
The final v11 preview contract generates three independent public alternatives
in one call, then selects one deterministically from the random game identifier.
Only that selected premise is sent to setup. It uses no previous player stories,
fixed setting list, content filter or self-review call. Nine real new-game calls
completed with varied selected settings; see
.local/verification/ai-tasks-v11-variety-03d2673b.json and the category module.

The player's failed `take:letter` commands were pinned to v6. Three stored DM
responses used `true` or `truthful` where the validator required `supported`.
The prompt had not enumerated the four legal verdicts. New main/private DM
contexts now define the complete enum and reference contracts. Gateway
normalization accepts those two affirmative aliases even for pinned old
operations, leaving request fingerprints and completed stages unchanged.
Unknown verdicts and invalid references still reject the entire world commit.

All three original failures were replayed locally against their original base
states and saved role/DM results: raw validation failed, normalized validation
passed, and the take resolved in memory. No provider call or player-save write
was made by that replay. .local/verification/take-local-replay.json records this
scope. A separate regression exercises failed-command recovery, completed-role
reuse, atomic rejection and duplicate submission. This is distinct from claiming
that the player's current game has already advanced or completed a live retry.

A separate, freshly constructed fictional fixture made two real main-DM calls
and one private-DM call with v11. All completed; both nonempty assessments used
`supported`. No existing player save was read or sent in that check. Its report
is .local/verification/dm-contract-live-55b50742.json. Final verification passed
39 Python tests, six frontend tests, and the explicit-provider-double Edge
walkthrough (.local/verification/browser-ai-v11/report.json). The local service
was started with the v11 default; no player command was executed as part of
deployment. The remaining failed take can be retried through the normal recovery
control, retaining its original operation identity and pinned task version.
