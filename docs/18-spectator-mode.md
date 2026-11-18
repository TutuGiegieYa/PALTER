# Spectator Mode

Status: Implemented and contract/browser verified. Real-Flash samples confirm autonomous play and operational pauses; reliable natural closure within the default budget remains unproven.

Last updated: 2026-11-11.

## Bounded Wait Recovery: 2026-11-11 (v123)

Status: implemented and covered by scoped scheduling and headless display tests.

The last available role cannot enter a pure message wait while the other
unfinished participants wait. Concrete events and normal work retain their
completion/timeout semantics. If an existing all-waiting state has no autonomous
work, finish due event reviews and interrupt one subscription at a time. Its role
chooses the response; its custom/fixed event is not marked complete. Reconsider
each eligible role once per no-progress episode, then pause with `waiting_stalled`
and a visible explanation. Explicit continuation after this pause permits another
bounded round; ordinary pause/retry does not reset it. Roles receive only their
own scheduling permission and private cancellation receipt. The engine never
discloses other roles' private waits or chooses a story action on their behalf.

See [scheduling and verification](08-time-reading-and-background-activity.md#last-available-role-and-bounded-wait-recovery-2026-11-10-v123).
The fresh bounded playtest paused for budget without reaching an ending; the
focused tests and real probes do not establish complete-game reliability.

## Event-Based Global Timeline: 2026-11-10

Status: implemented; recipient-boundary tests and desktop/mobile headless checks pass.

The global timeline renders one row per actual event, with explicit actors and
third-person descriptions for structured actions. Separate inspections remain
separate actions, but acquired document bodies move into collapsed material and
receipt details rather than appearing as repeated unattributed scene messages.
Merge recipient copies only inside their shared event; never merge distinct
occurrences just because their text is identical. Keep distinct perceptions with
their recipient attribution in details. Personal perspective histories and all
spoken/gesture text remain exact. Unknown receipt types retain their original
text in attributed details rather than guessing a third-person rewrite. No regex
replacement, model paraphrase, saved-history mutation or role-context change is
used for this display projection.

Verification artifacts: `.local/verification/own-action-v121-20261110/`.
Six timeline tests cover action attribution, same-event recipient grouping,
distinct repeated speech, private scope and unchanged personal observations.
Two frontend tests cover collapsed details, stable IDs, escaping and original
role text. Read-only projection of the latest three games preserves all personal
observations and stored state; each timeline has unique event IDs and no
second-person action summaries. Microsoft Edge headless checks pass at 1440 and
390 pixels: four separate named inspections, exact speech, original role receipts,
details initially collapsed and still expanded after refresh, no horizontal
overflow and no browser errors. Desktop/mobile global and role screenshots were
generated from synthetic fixtures using the actual renderer and stylesheet.
The fixture required a missing application-state helper before the final pass;
this was not a production renderer error.

After the v121 restart, read-only headless checks also pass against the actual
paused latest game at both widths. Its seven committed inspections appear as
seven named actions, expanded receipt details survive automatic polling, and
the recovery button is enabled. There are no page errors or horizontal overflow;
all browser requests were GETs, with non-GET requests blocked by the test harness.
The game was not resumed. Live screenshots and `headless-live-report.json` are
stored alongside the synthetic checks. Restart preservation is recorded in
[action completion deployment](08-time-reading-and-background-activity.md#current-action-completion-2026-11-10-v121).

The current [observation wait policy](08-time-reading-and-background-activity.md#consecutive-observation-waits-2026-11-10-v119)
prohibits only consecutive `next_observation` waits by the same role. Other
eligible events may be awaited consecutively. Historical v112-v118 operations
retain their rolling one-wait-in-three-replies policy. Spectator timer jumps,
DM cancellation and pauses do not reset accounting. The role still chooses its
next action; existing no-progress and spending pauses remain active.

## Whole-Game Acceptance and Accumulating References: 2026-11-09 (v107)

Status: implemented and deployed; a real game completed through evaluation and ending after
explicit error/balance recovery. Uninterrupted reliability is not established.

The production v106 run progressed beyond the repaired event review and stopped
at role_A with a different contract drift: twelve existing belief testimony IDs
plus a valid one-ID delta exceeded an old twelve-reference validator. All four
attempts failed with testimony cap and no actionable request feedback. Small
isolated probes had not exercised this long-running accumulation boundary.

Remove citation-count caps from ensemble private reasoning, progress,
relationship-source arrays, final submissions and final evidence review while
keeping actual source authority, JSON types, text/output/input budgets and
atomic application. Do not truncate citations, silently accept unknown records
or convert spoken claims into original evidence. New role guidance asks for
explicit removal of obsolete references when reasoning changes. Role errors
carry field-specific numeric/source diagnostics; remaining unstructured model
contract failures receive correction feedback within the existing three retries.
Published prefixes and paid requests remain immutable.

Acceptance now includes complete fresh all-AI murder games through individual
submissions, reviews and final narration. The runner may set an explicit test
budget/call allowance using ordinary spectator controls, recorded separately
from the production default. No truth hints, forced exploration, forced votes,
scripted role decisions or automatic resumption of a stagnation/error pause may
be counted as an autonomous ending. Production saves remain read-only during
diagnosis and are never sent to the provider as test inputs.

The long real runs exposed another boundary: a role's speech precedes its inspect
action, but event review also sees the resulting acquisition. A DM repeatedly
assigned that later document to the earlier utterance. V108 adds per-utterance
`disclosure_sources`, scoped to the speech snapshot and initial knowledge, plus
precise allowed-source retry feedback. Event-review visibility does not grant
retroactive disclosure authority. Speech remains untouched and spoken intentions
never substitute for actual presentation receipts. Historical v107 requests keep
their original fields; only a new retry receives correction feedback.

The provider subsequently returned HTTP 402 during final-phase testing. This
means insufficient provider balance, distinct from the spectator's configured
game budget. It stops automatic calls, explains the condition and permits a
manual retry after top-up. The user confirmed top-up; detached test copies are
explicitly resumed and reported as recovered runs, never clean uninterrupted runs.
Reference: [DeepSeek error codes](https://api-docs.deepseek.com/quick_start/error_codes/).

After top-up, final-phase consolidation exposed a contradictory repair: a
13-entry, 856-character draft met the text limit but exceeded 12 entries. The
old feedback still assigned thirteen per-entry shortening targets and described
text overflow. Correction version 6 distinguishes entry overflow, removes these
targets and any text-only repair contract, and asks the model to regroup a full
snapshot by compatible topics. It keeps provenance kinds, source permissions,
the checkpoint, 12-entry structure, below-1024 summary and 2048-token cap. No
engineering truncation or automatic semantic merge is used. Paid retry inputs
remain pinned; only new attempts use the correction.

Real acceptance uses Flash with thinking disabled and an explicit USD 1.50 /
512-attempt allowance per fresh case; production defaults are unchanged.

- Case `796909bc76cb96048d2d1ff3` autonomously voted to close and reached final
  submissions. Balance stopped it at step 167. After top-up, the entry-count
  repair was reproduced and fixed. Its next memory attempt produced nine
  entries / 787 text characters / 1001 completion tokens from the rejected
  thirteen-entry draft. The detached continuation reached `phase=ended` at step
  169 with all four submissions, four reviews and ending narration, without
  forcing movement, votes or theories. B/C/D established their cases; the
  culprit's outward position was assessed separately and its avoidance failed.
  This is a recovered complete chain, not an uninterrupted pass. The final
  lineage contains 381 provider attempts, 16 completed consolidations and
  estimated logged cost USD 0.841746708.
- Case `8ef394a05b8d40a353505119` stopped before its first action after four
  connection failures. It was not resumed. Independently observed transport
  failures were TLS EOF (`SSLEOFError`, errno 8); transport reliability is not
  claimed fixed by logging diagnostics.
- Case `aca6c6fac899c166e1ed3891` stopped at step 103 on the disclosure boundary.
  An explicit detached retry first encountered HTTP 402. After top-up, the real
  DM retry passed and advanced to step 104 with no error; the requested single
  verification step then paused normally. This is a recovery check, not an ending.
- The fresh v108 case `8f98a64a554dcbc08407db14` stopped at step 1 on HTTP 402.
  It is retained as an incomplete trial, not counted as a full-game success.

Local production-output replay preserves the failed 12-to-13 increment without
external calls or source deletion. Historical reconstruction matched 1280 paid
request hashes across 541 operations and preserved all 123 pre-change artifacts;
the complete manifest now has 126 immutable artifacts. Real synthetic testing
and recovery used 630 distinct provider attempts, with logged estimated cost
USD 1.327731912 (deduplicating copied receipts). These estimates are not an
account billing reconciliation. No production game was advanced by testing.

Receipts: `.local/verification/full-chain-20261109/acceptance.json`,
`conclusion-final/live-recovered.json`, `disclosure-verified/live-recovered.json`,
`recovery-report.json` and `replay-report.json`.

Final regression passed 559 tests in 157.727 seconds, including local HTTP,
legacy thinking recovery, paid-call reuse, source authorization and the new
entry-count regression (`final-tests.txt`). A prior sandbox-only run could not
bind the five HTTP fixtures; the final permitted run executed them successfully.

Deployed v108 at 16:56 CST on 2026-11-09, service PID 584824, with the local page
returning HTTP 200. Before/after hashes matched all 40 games, 3358 ensemble calls,
1552 operations and two legacy model calls. No pending calls were interrupted.
The production game `0632efa6fcd3cca63e08cdc9` remains paused at revision 62,
step 42, ready for the user's explicit retry. No production model call was made.
Deployment receipt: `deployment.json` in the same verification folder.

## Scoped Repetition Context: 2026-11-09 (v105)

Status: implemented; acceptance and deployment are recorded in
[cost control](11-prefix-cache-and-cost-control.md#scoped-context-economy-2026-11-09-v105).

The latest reviewed production game reached the existing stagnation pause at
revision 142: twelve unproductive decisions, three opportunities per role.
This is a working termination boundary, not an infinite background loop. Keep
the paused game intact and require the user's normal resume action.

When at least three of a role's last four own choices are wait, its ordinary
decision receives a small scoped reminder with those choices, recent actually
received statement IDs/speakers and its own last wait result. No global pause
counters, other characters' private actions or observer/controller identity enter
the role context. The model determines whether more discussion, a different
action or deliberate waiting is useful; no semantic duplicate classifier,
forced movement, forced conclusion or additional reminder call is added.

## Individual Exploration View: 2026-11-06

Each role panel now includes its own investigation progress and material
acquisition labels. Actually presented documents identify the presenter rather
than inheriting that person's inspection label. Receipt does not mark the source
room explored. Progress distinguishes visits, personal checks, completed searches
and last visible inventory; undiscovered offsite contents remain absent even in
an individual spectator panel. The separate truth panel retains its omniscient
scope. Ordinary player cards use the same projection and received speech remains
in dialogue/sourced memory. Details retain their expanded state across polling.
Verification and real-model limits are recorded in module 02.

## Evidence Sharing Visibility: 2026-11-06

The truth panel now lists who actually acquired each material, separate counts
and expandable receipts for oral disclosures and real presentations, and the
actual recipients/channel of each occurrence. Individual role panels and ordinary
player material cards show only that role's own disclosure/presentation status
and recipients. They never derive other roles' private holdings from the truth
panel. Legacy saves render this information without migration or replay; missing
channel/recipient metadata is labelled incomplete rather than guessed. Expanded
receipts survive polling. New v61 role decisions use the corresponding scoped
receipt summary, documented and verified in module 02.

The v59 event-driven scheduler and native listener tools are implemented and
verified. Ordinary received dialogue accumulates while roles wait; fixed outcomes
wake subscribers in code, and scoped DM passes assess custom conditions. If all
roles wait with no runnable event, the observer sees a waiting pause. Both private
participants can leave immediately. The detailed contract, real-provider receipts,
test counts and deployment record are in
[Time and background activity](08-time-reading-and-background-activity.md).

Processing and in-flight cost notices retain stable layout space between calls.
Desktop/mobile polling checks confirm that busy/idle changes do not move the
content below the controls; see module 17's processing-status verification.

## Scope and Information

Create a separate four-character game with zero human seats. The authenticated
owner is a spectator, never character A. Existing participant games cannot switch
to an omniscient view. All seven existing scenario rule sets remain available.
The public introduction is confirmed before preparing fixed truth and scripts;
the spectator explicitly starts play after inspecting the prepared game.

The spectator can inspect fixed truth, all actual dialogue including private
conversations, each role's acquired records, current interpretation, objectives,
relationships and actions. This view is never reused as model input. All roles
use the ordinary role/DM tasks and recipient contexts; no human counts, controller
types, spectator flag, speed or cost metadata enter those tasks. The spectator
cannot speak, move, choose a role's action, submit a theory or rewrite history.

Actually heard speech is optional usable information, including public speech
and private exchanges received by that role. A role may cite, trust, doubt or
ignore it. Its receipt does not establish its truth. Older acquired observations
remain valid after leaving the recent-message window. The runtime checks actual
receipt; it does not force a role to cite testimony or accept a claim.

## Progress and Closure

Provide an initial decision opportunity, then schedule explicit continuations and
event-triggered wakeups while balancing queued opportunities across roles. Do not
poll a waiting role merely because the response agenda drains. The observer can
inspect each role's waiting state, selected events and private tracking conditions.
Roles can investigate, converse, consent to private chats, act or remain silent.
Running activities and world opportunities retain their real supported effects.
The scheduling clock advances by two active seconds per committed step. Normal
and fast playback differ only in wall-clock dispatch delay, not fictional timing.
When all roles wait, a runnable activity or known timer can advance directly to
its next transition without role calls. With no runnable event, pause visibly;
do not invent a narrative ending or repeatedly check models. See
[event-driven scheduling](08-time-reading-and-background-activity.md) for custom
conditions, scoped DM judgments, cancellation and direct-contact interruptions.
Another role gets an opportunity to react before newly started timed work ticks.
V79 gives every role wait an active-time deadline, so all-waiting playback can
advance to that deadline without polling the roles. Generic DM validity review
uses only the owner's perceived circumstances; fixed outcomes remain mechanical.
The cards show remaining active time and the most recent termination reason.
Repeated timeout-and-wait cycles with no progress still reach the stagnation
pause. See the [bounded wait contract](08-time-reading-and-background-activity.md#bounded-waiting-and-contextual-validity-2026-11-08).
Versioned context supplies recent actual choices and available unread records;
speech and a concrete action can occur in the same turn. Historical actions are
labels, while executable choices come exclusively from the current action menu.

Shared role choices include proposing/agreeing to closure and withdrawing assent.
Three of four votes open final submission; each role then independently locks its
own conclusion from acquired information. Only after all four lock does the same
existing outcome evaluator and ending narrator run. The culprit cannot veto the
other three. Ordinary human games retain explicit human submission as their final
barrier. Public closure information is available to both ordinary and all-AI roles.
There is no fixed act count, hidden solution-based auto-ending or invented clue.

## Observer Controls and Recovery

Start, pause, resume, single-step and normal/fast playback are out-of-fiction
controls. One step commits one queued decision or world/activity transition;
multi-call decisions commit atomically. A step pauses again afterwards. In-flight
work can finish during pause but stays buffered until explicitly resumed. Steps
and requests are idempotent, and concurrent clicks cannot execute duplicate turns.
No observer heartbeat for sixty seconds pauses the game. Returning to the page
does not silently resume it. Provider errors pause with explicit recovery; no
scripted substitute or automatic paid retry loop is allowed.

## Budget and Stagnation

Default USD 0.10 includes preparation, play, final evaluation and narration.
Show provider-reported token/cache usage, estimated consumed cost, reservations,
remaining admission budget and an 80% warning. Admit a request only when a
conservative uncached-input/output-cap estimate fits the unreserved remainder.
Unknown usage retains its reservation. All attempts count toward an initial
128-request allowance. The observer can explicitly add USD 0.05 or 64 requests
with separate idempotent controls. Neither addition automatically resumes play
or changes the other allowance. On 2026-11-06 the user replaced the fixed request
ceiling with this manually extensible limit. Old spectator saves default to 128
and can add requests without restarting the story. Count-paused operations keep
their completed stages and recover after an explicit addition and resume.
Per-stage retry limits remain separate. Cost and count stops preserve the game.

After twelve completed role decisions without meaningful progress, and at least
two opportunities per active role, pause for stagnation. Material discoveries,
first disclosures, new evidence-backed interpretations, sourced answers and real
objective/action changes count. Rewording the same claim, repeating a search or
moving back and forth does not repeatedly reset the counter. Waiting for an
ongoing activity is excluded. Resuming acknowledges stagnation and starts a fresh
observation window; it does not invent story progress.

## Verification

Verify zero-seat ownership and normal-game isolation, role context parity,
private-channel boundaries, all-AI opening, fair ongoing scheduling, collective
closure, single-step/pause/in-flight recovery, disconnect, conservative admission,
unknown charges, count ceilings, budget additions and substantive-progress rules.
Use isolated providers for contracts and browser checks. Run ten fresh real-Flash
spectator games under the agreed budgets; report ended versus operationally paused
outcomes and actual costs separately. Never export existing player transcripts.

Implementation: `palter/spectator.py`, `palter/static/spectator.js`, shared ensemble
role/DM logic and gateway reservations. Published artifacts through version 36
remain unchanged. Versions 37-41 record successive contract/context corrections;
the initial spectator acceptance used version 41. Current version 42 adds
first-person role/memory wording; older operations retain their pinned input.

Contract and browser evidence on 2026-11-06:

- 136 Python tests pass, including twenty spectator tests. Cases cover all seven
  closure paths, heard versus unheard sources, old received observations,
  recipient context parity, fairness/stagnation, disconnect, reservations,
  unknown usage, count limits, topups, concurrent controls and buffered recovery.
- Six frontend checks and JavaScript syntax pass. Seven spectator browser checks,
  thirteen ordinary scroll/control checks and five multiplayer-flow checks pass
  without page errors. Desktop and 390px spectator screenshots were inspected.
  Receipts: `.local/verification/browser-spectator/run-09fb9242.json`,
  `.local/verification/browser-scroll/report.json` and
  `.local/verification/browser-ensemble/run-dce1c3c8.json`.
- Twelve unchanged real outputs previously rejected for source references pass
  offline validation against their original role-acquired records after the fix.
  No transport or original receipt mutation occurred. Receipt:
  `.local/verification/spectator/heard-source-revalidation.json`.

Real-model evidence uses fresh test-owned cases, DeepSeek Flash, no truth oracle,
no automatic retries and no added budget. Operational pauses are not endings:

| Receipt under `.local/verification/spectator/` | Version | Cases | Calls | Usage-based cost USD | Outcome |
| --- | --- | ---: | ---: | ---: | --- |
| `live-8a8a998c.json` | 37 | 10 | 158 | 0.135392928 | Source validation exposed legitimate heard-message references; the original report also retains a reporting exception later corrected |
| `live-6ce427bb.json` | 38 | 1 | 34 | 0.034058256 | DM included an older utterance in the new assessment; version 39 adds explicit new-utterance scope |
| `live-af04d6ea.json` | 39 | 10 | 718 | 0.763635876 | Six budget pauses; four visible model-output/source errors; no endings |
| `live-787a54b6.json` | 40 | 1 | 59 | 0.064835124 | More investigation, then a repeated historical inspect choice; version 41 separates historical labels from the executable menu |
| `live-28d45288.json` | 41 | 2 | 109 | 0.113620068 | Murder: forty decisions, seven/nine/three/three acquired records, budget pause without failed calls. Theft: visible relationship-field schema error after twelve decisions. No endings |

The version 41 murder sample made concrete discoveries; it does not establish
general narrative quality, reliable closure or complete games within USD 0.10.
Structured model-output errors can still require explicit recovery. Collective
closure and final evaluation are verified with isolated test controllers across
all categories, not yet by a naturally completed all-AI real-model sample.
Keep the agreed default and manual controls; do not force closure, auto-topup or
silently substitute a script to improve these numbers. Raw receipts stay local.

## Local Deployment

The existing user systemd service was restarted after confirming zero in-flight
calls/operations and making a consistent backup at
`.local/backups/pre-spectator-20261106-151040.sqlite3`. All nineteen existing
game-state hashes matched after startup. Homepage, updated assets and session
API returned HTTP 200; reservation accounting schema is present. Receipt:
`.local/verification/spectator/deployment.json`. No existing game was converted
or used for testing. Refresh the local page and create a new zero-human game.

## Manual Call Extensions: 2026-11-06

The later user correction makes the call allowance manually extensible. The
observer's separate “增加 64 次调用” button persists a per-game limit, defaults
missing older-save fields to 128, and keeps money and count allowances independent.
Adding calls unlocks a count-paused operation for explicit recovery, preserving
its operation ID and completed stages. It does not erase a different failure or
increase the per-stage retry allowance. Updates made during an in-flight step
survive its atomic state commit, and repeated command IDs add calls only once.

138 Python tests pass, including twenty-two spectator tests. A boundary test
starts from an old save without the new field, lets the role consume call 128,
stops before its DM, adds calls, reloads the application and completes the same
operation with call 129 without paying for the role again. Budget independence,
retry-exhaustion independence and in-flight additions are also checked. Eight
spectator browser checks pass without page errors, including the disabled resume
button at the limit, addition, refresh persistence and single-step recovery.
Receipt: `.local/verification/browser-spectator/run-b9d861dc.json`.
This control change uses isolated provider doubles and needs no paid gameplay run.

Deployment of call extensions and first-person context version 42 used the backup
`.local/backups/pre-call-limit-first-person-20261106-153636.sqlite3`. No calls or
operations were in flight. All twenty-one existing game-state hashes matched
after the user service restart; six page/asset requests and the session API
returned HTTP 200. Receipt:
`.local/verification/call-limit-first-person-20261106/deployment.json`.

## Completed User-game Review: 2026-11-06

The user requested review of the completed spectator game
`b884f79ef06e58a9918e2934` (recording-family murder). This was read-only: no new
provider requests, production state changes, automatic recovery or regrading.
The review inspected the full 109-utterance sequence, actual actions, submissions,
grading and receipts. It replayed all 111 background operations using their
original outputs and pinned versions 41/42; all 222 post-setup request hashes
matched, and the final events, observations, submissions and results reproduced
exactly. Public/private utterance recipients matched the stored observations.
Metrics and reproducible read-only audit:
`.local/verification/spectator-review-20261106/audit.json` and `audit.py`.
These artifacts contain metrics and event references, not an exported transcript.

The game ended after 111 steps and 224 successful Flash calls, with no failed
calls. Role opportunities were 28/27/27/27. Three closure votes were followed by
four independently locked submissions and ending narration. Estimated usage cost
was USD 0.33562002; the observer had explicitly raised the monetary allowance to
USD 0.50 and request allowance to 384. The measured input cache-hit fraction was
45.30%. This establishes a natural all-AI closure after manual extensions; it does
not establish a solved mystery or completion under the default USD 0.10 budget.

Findings, in priority order:

1. **Conclusion assembly loses available support.** Role C possessed evidence
   satisfying all three compiled proof dimensions and selected the correct
   suspect, but submitted only five records, omitting c1/c2/c3. None of its
   submitted sets satisfied a complete proof route, so no dimension passed the
   runtime guard even though the model grader marked its claims supported.
   Role B also possessed a full proof route but retained a null suspect throughout
   play and final submission. The incomplete conclusions should be addressed at
   role decision/submission time, without silently supplying uncited material or
   weakening the evidence checks. `lock_conclusion` currently copies the role's
   ordinary belief fields directly. The grading input also carries selected
   evidence snapshots, but no independently attributable heard-testimony source
   collection; acquired testimony needs an explicit final-use contract.
2. **Invented and merely claimed history enters personal memory.** The frozen
   setup/case contains no spare-key handover or receipt. Role B introduced that
   account (e000065) and recorded it as its own remembered experience; the DM
   marked the speech uncertain. Role C claimed a private record had been secured
   (e000071) and retained that claim in memory while its executed action was wait.
   Outward deception is allowed, but own memory must still distinguish actual
   execution, claimed conduct and unsupported inventions. The world ledger did
   not create a key receipt or perform that claimed protection.
3. **Temporal mistakes become repeated premises.** The defensible death interval
   from c1/c2 is 18:26–18:38. The 18:32 audio concerns role A rather than the victim.
   Dialogue instead fixated on a six-minute gap and later explicitly described
   18:17–18:35 as six minutes (e000250, e000258 and e000271). Some DM assessments
   still marked these lines supported. Valid JSON and valid source IDs do not
   establish semantic correctness of the inference or its memory summary.
4. **Repetition and redundant actions consume turns.** 49 of 109 decisions chose
   wait, including eighteen consecutive decisions. One speech occurred verbatim
   three times (e000073/e000081/e000089). Five of six protect choices targeted
   already-protected objects, because those options remain offered. The existing
   stagnation guard correctly paused at step 37, but later answer-source novelty
   can reset progress during substantially repetitive discussion. Review action
   eligibility and progress signals rather than rewriting generated prose.
5. **Long-game context grows outside the rolling summary.** Every role decision
   updated a summary, and no separate ensemble_memory call was needed in this
   regularly scheduled game. Nevertheless, 152 relationship-experience entries
   and all acquired evidence remained in input. The first role request used 3,899
   input tokens/18,114 serialized bytes; the largest used 11,282 tokens/45,906
   bytes, including 7,993 bytes of relationship history and 6,355 bytes of evidence.
   It stayed below the 60,000-byte guard, but a short summary alone does not bound
   total context. Preserve raw records while bounding active relationship context
   and retrieving relevant acquired sources on demand.
6. **Delivery lacks silence and cue variation.** All 109 speeches received a
   microexpression cue. The three-received-utterance speech interval made speech
   mandatory in 83 of 109 role opportunities, which often requires words on every
   rotation of a four-role public conversation. Frequent repeated musical phrasing
   spread beyond the character whose persona introduced it. This warrants pacing
   and contextual guidance work; it is not a transport or privacy failure.

No runtime fixes were made as part of this review. First priorities are explicit
final conclusion assembly, grounded personal memory, and eliminating redundant
action opportunities; long-context bounds and dialogue pacing follow. Keep the
world/knowledge distinction, optional use of heard claims, independent endings,
and the prohibition on prose filters or extra prose-review calls.

## Review Fix Implementation: 2026-11-06

Authorized scope: repair the completed-game findings above. New operations will
pin v47; v41/v42 payloads and recorded histories remain replayable. No additional
prose-review calls or generated-text filters are introduced.

- Assemble a private final argument in the existing role decision, using an
  identity/time/method checklist and explicit acquired citations. Heard testimony
  has its own optional citations and attribution; it does not silently become
  an inspected record or bypass fixed proof routes.
- Rehydrate selected memory sources from the recipient's acquired records, label
  speech as testimony (including self-authored claims), and distinguish actual
  actions from proposed actions. Keep only three recent relationship experiences
  per counterpart in active context; retain complete histories in storage.
- Remove already-protected and already-copied actions; count progress sources
  individually rather than permitting endlessly recombined citation sets.
- Count periodic speech across participant-sized dialogue rotations, while
  preserving immediate response/explanation obligations. Give the existing DM
  scoped recent delivery context and make ordinary cue-free speech the default.
- Validate structure, privacy, pinned recovery, the original recorded replay and
  focused real Flash decisions separately. A model-guidance improvement is not a
  guarantee that every future deduction is correct or that every game is solved.


Implemented in `ensemble_context.py`, `ensemble.py`, `ensemble_world.py`,
`spectator.py` and the ensemble UI. Versioned context activates the new interaction
rules on new operations; older pinned operations retain their original payloads.
Published v43–v46 artifacts are retained as intermediate verification versions.

Final submission now has its own `final_conclusion`, separate from private belief.
A culprit may knowingly submit an unresolved or misleading position without
corrupting its private memory or automatically confessing. `ensemble_theory`
assesses the actual submitted text directly; it no longer asks the model to copy
long exact quotations, which produced an invalid ellipsis quote in an intermediate
probe. It returns per-aspect support and `argument_sources` for sources actually
used across the whole argument. Runtime still checks acquisition, explicit
submission, culprit and the original proof routes. Unsupported aspects and missing
sources still fail. Heard testimony is optional, separately attributed and
selectable by human players; it does not replace independent proof anchors.

Role context carries self/heard-claim provenance, acquired source recall, actual
own-action receipts and currently visible protection state. It contains neither
spectator metadata nor unavailable private conversations. At most three recent
relationship experiences per counterpart, with a 2,400-byte allowance, enter a
request; recall is limited to twelve records and 6,000 bytes. Context retains at
least twelve recent observations plus every observation since the memory
checkpoint (after normal chronological compaction), and refers to acquired evidence
by ID instead of duplicating its text. Full source histories remain unchanged.
This bounds active relationship/recall history, not every possible game's total
request size; acquired evidence and heard-statement ID indexes still grow, and
the 60,000-byte admission guard remains.

Periodic speech now allows three participant-sized dialogue rotations (nine
received contributions in a four-person conversation, three in a private pair).
Immediate question and explanation obligations remain. Already-protected objects
cannot be protected again under the new rules; each role can retain a copy once.
Progress credits individual sources rather than their arbitrary combinations.
The existing DM can omit ordinary delivery cues and receives scoped recent cues
to avoid habitual embellishment. No player text is transformed.

Verification:

- 148 Python tests passed; six frontend tests and JavaScript syntax checks passed.
- Original v41/v42 user-game replay: 222 completed calls matched their original
  request hashes and reproduced the recorded events/results, with zero replay
  errors and unchanged production state.
- Local projection comparison over 109 original role contexts: relationship
  history maximum fell from 9,027 to 2,507 bytes. Full request maximum was 45,822
  versus 45,401 bytes, mean 32,949 versus 32,268. These are serialized context
  comparisons, not measured provider-token savings or new game outcomes.
- Final v47 synthetic Flash probes: ten completed calls, USD 0.00843198. Both
  final-assembly/grading operations completed; one established all dimensions,
  the other remained unproven (time only), preserving evidence standards. The
  invented-deed and false-completion probes retained claims as claims; the
  arithmetic-error DM did not endorse the statement; ordinary speech received
  no cue. A separate culprit-choice probe tests private belief versus submission.
- Fresh intermediate v45 game: 43 steps, 86 calls, zero failed calls, budget pause
  at USD 0.089529576. Fresh v46 game: 25 steps, 52 calls, zero failed calls,
  stagnation pause at USD 0.043433844. Neither reached an ending; no automatic
  allowance extension or retry was used. These runs validate pauses and reveal
  remaining role passivity, not reliable autonomous completion or universal fun.
- Browser coverage includes optional testimony selection/persistence, desktop and
  mobile layout, spectator controls/recovery, and all existing scroll cases with
  the new testimony list included.

Artifacts: `.local/verification/review-fixes-20261106/` (synthetic probes, context
comparison and deployment receipt); `browser-ensemble/run-fb2a3ae1.json`, the
latest browser spectator/scroll reports, and spectator `live-6e6fe30a.json` and
`live-fb2bd97e.json`. Original player data was used only for local replay/context
measurement. Automatic approval rejected an attempted external model probe using
that save; it was replaced with independent synthetic fixtures.


Deployment completed with v47 on the local palter.service (PID 581361). The page,
four changed/relevant assets and session API returned HTTP 200; served asset bytes
matched the workspace. All 21 saved-game hashes matched the pre-restart SQLite
backup `pre-spectator-review-fixes-20261106-164044.sqlite3`. Final browser results:
six ensemble checks, eight spectator checks and thirteen scroll/input checks,
with no page errors. The source replay remains unchanged.

The separate real culprit probe completed for USD 0.002079084, but the model still
chose to accuse itself. The code now permits a different submitted position and
preserves that separation in deterministic tests; this probe does not demonstrate
reliable strategic deception. Autonomous initiative, consistent full citation and
strategic play remain model-quality limitations, not guarantees established by
this fix. No old game was replayed forward or regraded in production.

## Culprit Perspective Correction: 2026-11-06 (Implemented)

The user explicitly requested replacing the culprit's detective-style deduction
with situation assessment and response planning. The runtime implements a role-scoped private
instruction/output variant, chosen only from that character's own fixed goal and
known participation in the crime. The outward task name remains generic in usage
traces so other players cannot identify the culprit through diagnostics.

The culprit keeps factual self-knowledge in its script/memory and assesses only
received evidence, questions and exposure risks. Situation/plan are stored separately
from detective beliefs, without a private suspect-identification field. Final
submission remains the character's independently chosen outward position. In the
spectator UI, situation/response and personal memory are separate; historical
detective output is explicitly labelled as legacy output. Other murder roles retain
deduction and non-murder roles retain their scenario objectives. Existing pinned
requests, recorded utterances and human choices remain unchanged. Once characters
agree to conclude, only their independent final submission is offered; old private
self-accusations are never substituted for an unsubmitted culprit conclusion.

Verification: nine focused role-contract tests plus the complete regression suite
and browser perspective checks. The v49 synthetic Flash probe completed six of
seven calls (USD 0.008560524 reported usage); one ordinary decision failed output
validation with unknown usage retained. All three final culprit probes actually
locked their submissions: one blamed another role, two declined to name anyone.
The innocent control independently named the culprit. These are targeted synthetic
samples, not a guarantee that every culprit will always choose strategic deception.
Artifacts: `.local/verification/culprit-perspective-20261106/live-87e2dd19.*`.


## Separate Final Submission Guidance: 2026-11-08

Status: Implemented and verified with contract tests and bounded real Flash probes.

Review of the completed production game `348ccb14187f2107a6b40670` found that
its culprit voluntarily submitted a self-accusation. The existing private variant
already replaced detective belief with strategy, but still copied the common
final-submission paragraph asking for correct identity, time and mechanism. It
also copied the investigator's criterion for agreeing to end the investigation.
This is a conflicting instruction, not a fallback that substituted private truth
into the final submission. The user requested separate closing guidance.

V71 keeps the existing role-scoped perspective selection and generic external
task label. Investigators assemble their evidence-grounded argument. The culprit
receives a separate role purpose, exposure assessment, closure decision and
final-submission instruction. The culprit's fixed objectives continue through
submission: knowing the true act, acknowledging a local fact, being accused, or
agreeing to conclude does not oblige a self-accusation. A final position can deny,
contest the causal argument, decline to identify anyone, or choose another
outward accusation. Private memory remains factual; sources and available actions
remain strictly authorized. Deliberate admission remains a character choice.
There is no output filtering, self-ID ban, extra review call or rewriting of human
speech. The shared final JSON shape is unchanged.

The culprit memory instructions also inherit the current five-kind contract,
including `self_claim`, so they no longer lag behind the investigator's V70
memory guidance. Native tools, output token budgets, timing and win rules are
unchanged. Each private prefix remains stable and independently cacheable; old
pinned operations use their immutable original instructions. The change applies
to new operations and does not replay or regrade a completed game.

Verification: 269 Python tests passed. Five new tests inspect the actual selected
model request, not just the default instruction file: role-specific final/closure
routing, authorized baseline separation, matching memory/tool contracts, unchanged
outward choices (including voluntary admission), stable prefix reuse and V70
compatibility. Four real Flash calls used isolated synthetic final-stage fixtures
with received accusations and acquired documents. All completed on the first
attempt. The three culprit cases (clock, recording and substitution) submitted
`suspect:null` with contested outward accounts; the innocent recording control
named the actual culprit. Estimated total cost was USD 0.010531872. These samples
confirm the chosen role behavior in those fixtures, not guaranteed deception,
flawless arguments or whole-game narrative quality. Artifacts:
`.local/verification/final-perspectives-20261108/`.


## Investigation Guidance-Only Trial: 2026-11-08

Status: Implemented; bounded real Flash reproduction completed.

The user limited this change to guidance for overlooked unvisited areas and
repetitive discussion. Evidence grading, including the previously identified
mixed-equivalent-source defect, is explicitly deferred. No forced itinerary,
mandatory room completion, persisted investigation-plan state machine or automatic
movement is added.

V72 changes only `ensemble_role.instruction`. Ordinary roles are guided to compare
available ways to resolve consequential uncertainty rather than equating an
exhausted conversation or locally exhausted materials with an exhausted
investigation. Unvisited rooms and unknown inventories remain unknown; a room can
be worth checking without knowing in advance what it contains. Speech about a
check or presentation does not execute it. Repetition, waiting, conversation and
voluntary closure remain legal choices. The culprit's complete V71 perspective,
all task examples, tools, models, output caps, action menus and grading code are
unchanged. Existing pinned requests keep their old version.

A proposed historical-snapshot network replay was rejected by automatic approval
because authorization to send the stored story was not sufficiently explicit.
That script did not execute. The completed alternative uses a wholly synthetic
fixture built from test data and the scenario compiler, with no production-save
reads or original dialogue/persona reuse in the model probe. Its structural setup
has three investigators, repeated public discussion, acquired local documents,
a spoken death-time upper bound and an unvisited workroom. Exact original-game
behavior therefore remains unverified.

For each of the three investigators, V71 and V72 received identical baseline,
dynamic context, action menu, model settings and tools; only the role system
instruction differed. Assertions verified that the workroom was `unvisited`, its
inventory was unknown, movement was available and its unretrieved source `c2`
was absent from the model's source map and visible targets. In these three paired
single-step samples, V71 chose two closure votes and one presentation; V72 chose
three presentations, with no immediate movement. All selected actions executed.

The first pair was then continued through normal fair scheduling, bounded at
12 further steps or closure/scene inspection. V71 received its remaining two
closure votes within two steps, without visiting the workroom. V72 continued;
on continuation step 9, investigator A independently chose `move:r2`, saying the
workroom had not been personally checked and could help test the timeline. The
movement committed. On that role's next scheduled opportunity (one additional
step after the 12-step window), it chose `inspect:c2` and actually acquired the
original discovery record. The probe then stopped, without invoking grading or
ending generation. It did not receive an external instruction naming the target
room or its hidden source.

This demonstrates an autonomous visit and inspection in one continued synthetic
case. It does not establish immediate exploration, a full-game success rate,
reliable absence of repeated dialogue, or a cost improvement. Intermediate
presentations, waiting and other actions still occurred. The complete regression
suite passed 269 tests. All 43 real Flash calls completed, estimated total cost
USD 0.060134832, including two retained baseline calls before a reporting-harness
error was corrected. The scoring implementation SHA256 remained unchanged.
Artifacts: `.local/verification/investigation-guidance-20261108/`.
## Explained Conclusion Reviews: 2026-11-08

Status: Implemented for new v73 conclusion operations. Historical outcomes remain
unchanged; old pinned operations use their original evaluation contract.

The shared play/spectator ending view now separates the submitted argument's
score from a factual process retrospective. It displays semantic reasons and
runtime proof gaps for identity, time and method, supports declared equivalent
original/copy combinations, and treats heard statements separately from acquired
documents. Culprit commentary describes outward stance and actual objective
outcomes, allowing voluntary admission without labeling it an error. See
[Goals and endings](06-goals-and-endings.md#evidence-matching-and-explained-reviews-2026-11-08)
for scope, fixtures, real-model results and browser evidence. This completes the
grading/commentary work separately authorized after the v72 guidance trial; it
does not introduce forced movement, prescribed acts, or extra review calls.
