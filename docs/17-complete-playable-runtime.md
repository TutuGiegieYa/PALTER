# Complete Playable Runtime

Status: Implemented and verified for the explicit four-seat, seven-scenario contract below. Broader design illustrations retain their proposal scope.

Last updated: 2026-11-09.

## Speech Non-Repetition Guidance: 2026-11-09 (v111)

Status: Guidance implemented, verified with scoped probes, and deployed at
2026-11-09 19:03:28 CST (service PID 615876).
The user explicitly requested a no-restatement instruction after the diagnosis
below. V111 derives from active v109, not the unactivated v110 waiting experiment.
It adds the same permanent dialogue paragraph to investigation and concealment
instructions, including private conversations that use the same role task.

Roles must not copy another speaker's entire turn, or reissue it with changed
names, wording or personal experiences. Agreement can be brief. Necessary short
quotations for challenge/comparison retain attribution and lead to the role's own
judgment or question. With no additional contribution or conversational purpose,
choose silence, a brief acknowledgment or waiting as the speech obligation allows;
a mandatory utterance can state the role's position briefly. Do not invent facts
to manufacture novelty. This changes instructions only, with no similarity-based
rejection, rewriting, extra self-review, altered actions or automatic gameplay
resume. Earlier paid prefixes and speech records remain untouched.

Validation: all 129 earlier published artifacts retain their hashes; the only task
changes versus v109 are the two dialogue paragraphs. Rendered requests include
the paragraph for both perspectives. All 27 related contract/context regressions
pass. Three synthetic real-model probes each completed with one provider call. The
investigation and concealment roles chose silence when allowed; the mandatory
speech sample gave one short original sentence. None copied the preceding
synthetic utterance. Estimated upper cost: USD 0.003572364. This is a small scoped
sample, not whole-game acceptance or a guarantee against all future repetition.
Receipts are under `.local/verification/speech-echo-20261109/`. Service HTTP is 200;
pre/post hashes of games, operations and provider-call ledgers match. The current
production game remains paused at revision 242 / step 199 for the user's own
continue action. New operations use v111; historical utterances stay unchanged.

## Cross-Character Speech Echo: 2026-11-09 (original diagnosis)

Read-only inspection of game `0632efa6fcd3cca63e08cdc9` found near-verbatim
echoing between A's `e000282` and D's `e000283`. D retained the opening, argument
structure and closing question while changing the personal alibi and names.
Character-sequence similarity is approximately 93.4%; these are not byte-identical
utterances. Both stored event texts match their respective raw provider responses.

The completed role calls `0f3e0773e53c2cbf3a05ddb3` (A) and
`3db5d8ed23ed505d5cfe204d` (D) have distinct request and prefix hashes. Local
reconstruction matches both paid request hashes. Each request supplies its own
correct actor/profile. D received A's preceding speech as `D-o000131`, explicitly
attributed to A, and its complete text is present in D's request. Both decisions
had `must_speak=false` and `must_respond=false`; silence was available. This is
model-generated dialogue imitation, not duplicate rendering or reuse of one
role's saved response for another. The earlier cost-focused anti-repetition
guidance does not adequately prevent this outward-speech failure.

The initial candidate direction, now implemented as guidance in v111 above, was to
guide roles to contribute their own
stance or purpose, acknowledge agreement briefly, and choose silence/waiting when
appropriate. Preserve intentional quotations and their speaker attribution. Do
not require novel facts, rewrite stored speech, filter near-duplicate prose or add
model self-review. No production writes, provider calls or gameplay resumes were
performed during this diagnosis.

## Accumulated Final Sources: 2026-11-09 (v107)

Current ensemble final submissions and their reviews no longer impose arbitrary
twelve/thirty source-ID caps. Actual acquisition/hearing, required argument
dimensions, text/output budgets and individual evaluation remain authoritative.
The engine still derives the combined citation union from submitted dimensions.
Historical outcomes are not regraded. Whole-game evidence and remaining limits
are recorded in [spectator mode](18-spectator-mode.md#whole-game-acceptance-and-accumulating-references-2026-11-09-v107).

## Structured Final Arguments: 2026-11-08 (v88 implemented)

Murder final submissions use one entry per supplied grading dimension, each with
explanation, acquired evidence IDs, heard testimony IDs and acknowledged gaps.
The engine validates sources and derives the union and legacy display text; there
is no separately model-maintained overall citation list. Missing support may be
submitted explicitly. A culprit still chooses an outward position, including no
accusation or voluntary admission. Human forms provide the same aspect structure;
legacy flat commands and already pinned requests remain readable.

Review sees the exact submitted aspects and deterministic temporal facts; correct
arithmetic in context must not silently repair an incorrect submitted argument.
New recording cases permit the explicitly verified playback comparison to support
the same premise without separately requiring its redundant raw audio precursor.
Acquisition, actual argument use, semantic validity and identity are still checked.
Existing frozen proof routes and completed outcomes are unchanged.

Acceptance and deployment evidence: [module 11](11-prefix-cache-and-cost-control.md#source-conclusion-and-workflow-integrity-2026-11-08-v88).

## Latest Spectator Audit: 2026-11-08

Status: historical read-only findings. The authorized fixes are implemented in
v88, described above and in modules 02, 04 and 11. Withholding an acquired record
and independent actors inspecting the same record remain deliberate mechanics.
No historical outcome is rewritten.

Audited game `5951ade7cdfaad7cfecd0ee8` (night-school case), frozen recording
family, ended at revision 128 with no background error. There were 98 role
decisions and 223 provider attempts: 219 completed, four failed and subsequently
recovered (preview/memory/theory length truncation and one invalid reference).
Logged estimated cost was USD 0.752277864; reasoning accounted for 286,966 of
360,023 completion tokens (79.7%). These are historical v84 measurements, not
a prediction of savings from v85.

All four roles visited all three rooms. No actor inspected the same evidence ID
twice. Different actors acquiring the same record, or finding overlapping content
in distinct records, is normal investigation and is not classified as a defect.
The custom search tracker completed against an actual completed search with no
new discovery; no idle event loop was found in that sequence.

Observed issues and their evidence:

1. **An unsupported spoken detail becomes an asserted personal observation.**
   At `e000063`, culprit A says the playback document has an unsigned operator
   field. No frozen evidence contains that field or an assertion it is empty.
   D repeats this at `e000068`, then at `e000110` explicitly claims to have seen
   it during inspection. D's `m5` update calls it a property of the calibration
   record while citing both `c4` and heard statements. A is allowed to lie;
   the defect is D attributing an acquired claim to personal inspection and
   preserving it as a document property. This originates in role generation/
   incremental memory, not merely later compaction. Preserve attribution and
   actual source content without filtering human speech or adding self-review.
2. **A critical record is withheld rather than lost from storage.** D inspected
   `c4` (playback task/audio verification) at `e000049`; A collected it at
   `e000054` and retained it intact. B and C never acquired it. C later searched
   its former room and found no new hidden record. D still knew `c4` and could
   present it under the existing known-record share action, but never did.
   Only three formal presentations occurred among 81 spoken turns, and none
   presented `c4`. Missing acquisition, oral disclosure and physical custody
   must remain distinct; this is not evidence of an unvisited-room regression.
3. **Final source selection defeats otherwise supported reasoning.** B, C and D
   all accused A. B/C failed proof coverage without acquired `c4`. D possessed
   both `c3` and `c4` but selected only `c4`; every semantic aspect was marked
   supported, while fixed identity/method routes required the omitted `c3`.
   Its gap is correctly stored as `not_cited`, not `not_acquired`. Consequently
   shared success was false and A achieved the avoidance objective. This matches
   current source/route rules; whether the original audio record must remain
   indispensable alongside an explicit track comparison is a design question.
   Do not silently add uncited sources or retroactively award success.
4. **Early termination uses an inaccurate phase explanation.** D's first yes
   vote at `e000195` prompted cancellation of C's tracker at `e000196` on the
   stated basis that final conclusions had begun. The actual third yes vote
   and shared closure occur only at `e000217`/`e000218`; C investigated in the
   intervening period. The audited v84 DM circumstances contained presence
   and own activity, but no authoritative closure-stage field. Distinguish a
   proposal/vote from a completed phase transition in future event guidance.
5. **Temporal and review wording still drifts.** Later speech calls
   18:10–18:28 nine minutes (for example `e000188`, `e000199`), although only
   its intersection with the death window, 18:19–18:28, lasts nine minutes.
   D's submission swaps upper/lower labels for 18:19 and 18:31. D's review
   incorrectly describes the whole custody interval as contained in the death
   interval. The ending repeats the nine-minute wording. Review source-grounded
   time reasoning separately from the mechanical citation-coverage failure.

Evidence snapshot and read-only replay artifacts are in
`.local/verification/thinking-disabled-20261108/`. Prioritize source attribution
and final-assessment fidelity; preserve normal independent investigation and
the culprit's freedom to conceal information.

## Investigation Progress and Sources: 2026-11-06

V62 adds an engineering-maintained, role-scoped investigation map to decisions
and memory compaction. Unvisited rooms expose no hidden evidence; offsite areas
retain only personally observed snapshots. Visiting, checking, finishing a search
and receiving another person's document are separate outcomes. Acquired records
carry actual recipient-specific provenance, while spoken reports remain attributed
testimony/memory. New context distinguishes a local empty inspection menu from
exhausted investigation and includes witnessed deliveries by other presenters.
Player and spectator role views show the same progress/source distinctions.
Existing case truth, win criteria, human closure and pinned recovery remain intact.
Boundary tests, browser checks and the three-request real-Flash feature sample
are recorded in module 02 under Exploration and Acquisition Sources.

## Evidence Delivery Correction: 2026-11-06

V61 separates oral disclosure, presentation receipts and recipients from social
contribution credit. `already_shared` no longer labels a spoken disclosure as a
completed presentation, nor omits a real presentation because another role earned
first-disclosure credit. Current roles receive only their scoped acquired-record
status, with explicit recipients and remaining people they have not shown it to.
Players and spectators can inspect that status on material cards. Public delivery
does not include absent private-chat participants; repeating a share is available.
No forced sharing, altered win criteria, automatic proof, hidden evidence hints
or retroactive regrading is introduced. Existing saves render from their receipt
history; only new operations use v61. Pinned recovery retains older context.
Implementation and deterministic/browser/live-model evidence are recorded in
[Memory state and evidence](02-memory-state-evidence.md#evidence-sharing-receipts-2026-11-06-implemented-and-verified).

## Playability Work: 2026-11-06 (Implemented and Verified)

The user authorized a complete fresh playthrough followed by changes grounded in
its findings: distinct deduction structures, useful role interaction, meaningful
individual victory and recoverable operation feedback. Start with a test-owned
case and make player decisions using only that seat's view. Record the point at
which a hypothesis becomes supported, changed testimony, failures and closure.
This is an agent-operated playthrough, not a human difficulty study. Do not export
existing player transcripts or inspect the test case's solution before closure.

Retain frozen initial truth, explicit human closure, Flash routing, scoped memory
and immutable prefixes. New causal structures apply only to newly created cases;
older saves and pinned recovery contexts must remain valid. Design evidence and
proof routes together, provide discoverable counterevidence to misleading leads,
and test both correct reasoning and plausible but unsupported accusations. Role
context improvements may expose only acquired questions, actions and evidence,
never a hidden solution or another participant's private history. Final evidence
must distinguish runtime contracts, live model behavior and actual playability.

The user authorized completing every missing or partial capability identified in
the requirements audit. Existing saves retain their frozen case and original
runtime. New games use a four-seat ensemble with one to four human participants;
remaining seats are real DeepSeek-controlled characters. All current model tasks
inherit the configured Flash model. No scripted failure fallback, prose filter,
self-review call, or framework is introduced.

## Play and Information Contract

- A generated public preview precedes a lobby and initial setup. Joining requires
  a private room code and assigns a server-owned seat, never a client-selected role.
  Single-human reading is unlimited. Multiplayer reading lasts 120 seconds or
  ends when every human is ready. Reviewing a script does not pause multiplayer.
- The optional murder opening collects each human's willingness and scene-handling
  choice, asks AI roles for their own choices, randomizes arrival, prioritizes
  willing humans, and falls back to an AI or a random human if nobody volunteers.
  Exactly one killing occurs. The resulting past and personal scripts are fixed
  before investigation. The standard after-death opening remains selectable.
- Role knowledge, evidence existence, evidence custody/condition, beliefs and
  relationships are separate. Inspections acquire snapshots; later hiding,
  destruction or forgery cannot erase a prior observation or rewrite truth.
- Public invitations require consent. Private conversations have independent
  baselines, an eight-utterance cap and 300 active seconds. An event-driven agenda
  continues AI-only conversations, with bounded response chains and no idle paid
  polling. Pauses prevent new calls and buffer already running results.
- Addressed questions require speech or a meaningful gesture. Presented challenges
  and every three received dialogue opportunities require words. Private absence
  does not accrue public obligations. Reading and private notes remain available.
- DM inputs include utterance-time acquired evidence, memories, beliefs, recent
  perceived events and scoped conversation history, alongside authoritative facts.
  Only actual observable cues are delivered; verdicts stay internal.
- Every directed relationship has its own trust, affinity and sourced experiences.
  Role decisions update only relationships grounded in their acquired records.
  Humans express their own attitudes and make their own actions.
- Commands remain pending until accepted; timed actions use shared running/completed/cancelled/failed records. Timed work
  shares one game clock; cancellation preserves already incurred effects. Local
  inspection, notes and script review do not require AI interpretation.
- Supported object actions include take, transfer, hide, search, protect, copy,
  destroy and create an attributed forged document. Following observes only a
  subsequent visible movement. Murder evidence disruption is limited to one
  evidence category per actor per game day; previous knowledge remains intact.
- World choices are real AI selections from eligible scenario effects, on bounded
  event opportunities. Physical effects and initial facts are code-validated.
- Each role has a primary and a conflicting personal objective with executable
  evaluation. An innocent's success requires an active contribution; being
  exonerated alone is insufficient. Progress exposes only knowable facts.
- Confrontation is separate from final closure. Humans can hear and question
  changed accounts before committing. Multiplayer closure waits for every human's
  submission. No correctness feedback is provided before closure.

## Scenario Contracts

Murder supplies three causal families (clock displacement, recorded alibi and
object substitution), partial suspect accounts, independently combinable records,
and alternative proof routes. Initial evidence placement agrees with generated
room descriptions. Generic prose cannot add unperformed laboratory analysis.

Theft tracks actual object custody, ownership records, transfer and recovery.
Reunion tracks voluntary mutual commitments and disclosure of historical secrets.
Council tracks votes, resource pledges and whether a coalition honors commitments.
Rescue tracks shared supplies, repair, route conditions and individual evacuation.
The changing house has a fixed switch/route mechanism and recoverable keepsakes.
The sealed archive has a fixed dial mechanism and separately recoverable records.
Each scenario has its own executable outcome and role objectives; category names
are not merely different prose around a murder or item-recovery engine.

## Verification Gate

Verify the four audit counterexamples, all role/scope boundaries, every scenario's
distinct effects and outcomes, all-human and mixed-human opening/reading/closure,
timed interruption, evidence snapshots, goal failures and successes, model-choice
effects, transaction recovery, cache/prefix stability and scoped compaction.
Use fresh test-owned cases for paid provider tests and browser walkthroughs.
Existing player transcripts must not be exported for testing. Test doubles prove
execution contracts; real-model receipts prove provider execution; browser
inspection proves interface behavior. None alone establishes narrative quality.

## Implementation Map

| Audit gap | Current implementation and evidence |
| --- | --- |
| AI-to-AI private chats stop after acceptance | `ensemble_world.enqueue/speak`, `ensemble.pump/turn`, bounded private-session test and real private-DM receipt |
| Missing periodic speech and human reply constraints | Shared recipient counters/obligations; addressed response, gesture rejection, challenge and observed-handling tests |
| DM lacks acquired knowledge | Immutable utterance-time snapshots; acquired-versus-future knowledge and private-canary tests |
| Incomplete relationships | Twelve directed trust/affinity states and sourced experience updates; own-attitude UI and directionality test |
| Flavor-only personal goals and passive innocent wins | Separate executable primary/personal predicates; inactive-innocent failure, disclosure failure and independent ending rows |
| Missing evidence conditions and consequences | Separate objects/known snapshots, custody/handling, new traces, interruption and preserved-history tests |
| Missing active world events | Real eligible `ensemble_world` selections, shared effects, bounded opportunities and route recovery tests |
| Single easy physical murder family | Three causal families, alternate proof routes and no perfect-window innocent alibis; frozen-family contract tests |
| Missing voluntary opening | Real AI intentions, human priority, fallback and recorded leave/inspect/touch choices; mixed/all-human tests |
| Missing multiplayer | Server-owned membership, independent sessions, room join, 120-second/all-ready barrier, submission barrier and two-browser acceptance |
| Other categories only change prose | Seven effect sets and outcome predicates; deterministic scenario tests plus seven real generated/ended cases |
| Missing long-history handling | Chronological scoped memory chunks, persisted checkpoints, retained evidence and untouched baselines; coverage and canary test |
| Cache-hit UI regression | Per-call hit/miss and weighted totals; browser trace panel verified at desktop and 390px width |

## Operational Limits

The active game clock advances on physical effects and timed work; one unit is
one scenario minute for the murder daily allowance. World opportunities occur
at six-unit intervals, at most four per game. Timed work needs two units and can
advance in the background at two-second scheduling intervals while a participant
is present. The worker is event driven: it does not make paid calls merely
because the browser polls. A sixty-second presence window stops unattended
background processing. Human obligations do not have an automatic penalty timer.

Four seats, three physical locations, the stated action vocabulary and three
murder families are explicit current bounds. General construction, arbitrarily
composed plans, larger casts and hosted identity are broader product extensions.
The original scenario illustrations are retained as proposals where they exceed
these bounds. They are not advertised as completed arbitrary world simulation.

## Acceptance: 2026-11-05

- Full Python regression: 95 tests, including 33 ensemble tests. Six frontend
  regression checks and JavaScript syntax checks also pass.
- Browser receipt: `.local/verification/browser-ensemble/run-9237eda6.json`.
  Two independent sessions joined distinct seats, exchanged a consented private
  conversation, retained notes after reload, respected the shared ending barrier,
  and displayed independent results. A single-human pause during a real in-flight
  test-provider operation buffered and resumed correctly. No page errors.
  Desktop and 390px screenshots were inspected; mobile overflow was fixed.
- Paid provider receipt: `.local/verification/ensemble-live-9d0b72db.json`.
  All seven scenario outcomes and all eleven relevant task types were exercised.
  Across development verification there were 62 DeepSeek Flash requests, 59
  completed and three retained structural failures, with USD 0.054194664 reported
  peak-rate estimate. Reported cache hit/miss inputs were 44,544/88,414 tokens
  (33.5% input-weighted hit rate). Eleven setup calls took 7.87–12.72 seconds.
- The three real failures exposed an omitted relationship source list, an invalid
  gesture enum, and a descriptive DM cue instead of its enum. Immutable prompt
  versions clarified those exact contracts. The failed steps committed no story
  events. Version 28 successfully executed the restored private-role opportunity
  and private DM under a new operation; prior calls, costs and cancelled operation
  records remain intact. There is no prose filtering or scripted fallback.

The real test uses only newly generated test-owned stories; multiplayer case
endings use a solution oracle, and one AI-only private conversation is explicitly
arranged by the test fixture. This proves execution, boundaries and attributable
provider use, not spontaneous social quality or human deduction difficulty.
Generated settings varied, but harbor/fog motifs still appeared in two of the
seven category samples; this does not establish complete elimination of a model's
setting bias. No output blacklist was added. Narrative quality and long-term
replayability still require actual playtesting.

- Additional current-version receipt: `.local/verification/ensemble-v28-agenda.json`.
  Seven further Flash calls successfully activated all three AI roles and their
  DMs after the contract fixes, at USD 0.005393688 reported estimate. Together
  the receipts contain 69 requests, 66 completions and the three retained earlier
  failures (USD 0.059588352 total). All nine version-28 calls completed.

Legacy compatibility additionally verifies replay of original creation requests, reading and closure under EnsembleApplication for both older runtime families. A method-name collision in legacy conclusion dispatch was corrected before service rollout.

## Local Delivery

The verified service was restarted on `http://127.0.0.1:8765` with real AI and
`deepseek-flash`. A consistent SQLite backup was created before restart at
`.local/backups/pre-ensemble-20261105-134525.sqlite3`. Deployment verification
compared all sixteen existing game states against that backup: all were unchanged.
The session endpoint reports `gameplay: ensemble`, and the served ensemble asset
matches the verified local file. Receipt: `.local/verification/ensemble-deployment.json`.
Existing games keep their prior rules; refresh and create a new game to use this
runtime. No existing player transcript was sent to the provider during acceptance.

## Scroll Retention Fix: 2026-11-05

Polling previously reapplied the whole view through `app.innerHTML`, replacing
scroll containers and resetting their positions even when nothing changed.
`apply` now skips identical non-reading views while still applying same-revision
AI/call-status changes and updating multiplayer reading countdowns. Shared render
handling restores stable-keyed vertical/horizontal list positions, textarea
positions, focus/selection and the page viewport after DOM replacement. Dialogue
follows a new message when the reader was already at the bottom; other reading
positions stay put. Changing games does not reuse another game's offsets.

The fix covers ensemble, investigation and legacy observation views: dialogue,
evidence/notebooks, statements, observation timelines, call tables and textareas.
Six frontend regressions and all JavaScript syntax checks pass. Headless Edge
checks in `tests/browser_scroll.py` verify unchanged real polling, changed views,
same-revision busy controls, middle/bottom positions, notes focus and selection,
and narrow-screen table scrolling across all three runtimes. Receipt:
`.local/verification/browser-scroll/report.json` (completed, no page errors).
No provider call is required. Reload the page to load the new assets in the
current game; no new game or backend restart is needed.

### Processing-status layout stability: 2026-11-06

The spectator's processing paragraph was inserted/removed whenever `ai_busy`
changed. The existing scroll restoration preserved scrollY, but content below the
controls still moved; a real-polling browser fixture reproduced a 42.1875 px shift.
The conditional in-flight reservation text could also wrap the cost line on mobile.

Processing messages in spectator and ensemble views now retain their wrapped
layout space and toggle visibility instead of entering/leaving the layout. Idle
messages are hidden from assistive technology. Spectator reservation cost has its
own stable line. Pause, action gates, errors and actual task status remain live.

`tests/browser_processing_status.py` verifies four busy/idle transitions each in
spectator and ensemble views at 1440 px and 390 px widths. All four cases measure
zero content displacement; page height, viewport position and inner dialogue
scroll also stay unchanged. Six frontend checks and all 13 existing browser
scroll/focus/control checks pass with no page errors. Desktop/mobile screenshots
were inspected. Artifacts: `.local/verification/processing-status-20261106/`
(`before.json`, `report.json`, `scroll-regression.json`, screenshots and
`delivery.json`). The live service serves matching asset hashes without a restart;
refresh the current page to receive the fix. No model or stored game changes occur.

## Unheard Addressee Fix: 2026-11-05

Two production role attempts failed with `ValueError: question target`: a public
speaker addressed a known cast member who was in an accepted private conversation.
The earlier role validator rejected that target and rolled back the whole turn.
This is now a valid attempted utterance. Its exact words and intended target stay
in history, only current listeners receive it, and the speaker learns that the
addressee did not hear. The absent character acquires no observation, knowledge,
response obligation or scheduled reply. Unknown/non-cast targets remain invalid.
Human addressee inference follows the same delivery rule; an explicitly selected
target that has left the channel still fails before sending. Private utterances
remain private even when they name someone outside their conversation.

Version 29 supplies current listeners and unavailable cast names to the role and
address tasks. Role guidance prefers a current listener, and address inference
preserves the human's intended target. No prose rewriting or extra model call is
introduced. The operation's pinned prefix also controls these dynamic fields so
older resumable stages retain their request hashes. No historical prompt changed.

Two separate search rejections were periodic speech obligations, rather than an
unanswered direct question. The server now reports the actual reason. The UI
disables unrelated actions while a reply is due, keeps speech and notes available,
permits eligible invitation consent, and distinguishes explanation from ordinary
nonverbal response. This makes the existing obligation visible before submission.

Verification:

- 101 Python tests pass, including six new regressions for unheard AI/human
  addresses, private isolation, invalid identities, pinned context and the actual
  periodic-speech error. JavaScript regressions and syntax checks pass.
- Both original failed outputs pass local replay against copies of their original
  base states. Words, private isolation and frozen case are preserved. No replay
  was applied to the live game or sent to a provider. Receipt:
  `.local/verification/address-fix/replay.json`.
- Eleven browser scroll/control checks and the full five-part multiplayer flow
  pass with no page errors. Receipts: `.local/verification/browser-scroll/report.json`
  and `.local/verification/browser-ensemble/run-9130fd37.json`.
- Four real `deepseek-flash` calls complete on a fresh synthetic fixture: role,
  DM, human addressee inference and DM. The role addressed a current listener;
  inference preserved the absent intended addressee without cross-channel delivery.
  Reported usage supports a USD 0.00198036 upper-bound cost. Receipt:
  `.local/verification/address-fix/live-4737ab8e.json`. This is a bounded feature
  check, not evidence of general narrative quality. No player transcript was sent.

The local service was restarted with v29 after verifying no in-flight calls or
operations. Backup: `.local/backups/pre-address-fix-20261105-151011.sqlite3`.
All seventeen game-state hashes match the backup, and served JavaScript matches
the verified files. Receipt: `.local/verification/address-fix/deployment.json`.
Refresh the current game to load the updated controls; a new game is unnecessary.
The previously cancelled failed operation remains cancelled.

## Full Playthrough Findings and Changes: 2026-11-06

The baseline was a fresh v29 case, operated through the human seat's view, with
no solution read before closure. Twenty-five real Flash calls completed. The
agent investigated records, challenged the same suspect twice, then submitted a
connected explanation with eight acquired records. This is not an unbiased human
playtest: the operator already knows the application's general puzzle families.
The receipt and visible views are in `.local/verification/playability-20261106/`.

Observed issues and bounded implementation:

- The generated public premise described a pre-dawn fall while the fixed physical
  evidence established an evening cup substitution. Version 30 separates setting
  and social stakes from cause, exact time, access and evidentiary facts. Preview
  and setup guidance cannot introduce an independent physical puzzle. This is
  context guidance, not output filtering or an additional review call.
- Role invitations and acceptances generated both model speech and another
  generic utterance, consuming two speech opportunities. Version 30 keeps the
  chosen speech and records the social action once as an observable invitation
  or acceptance, including actual consent and response scheduling.
- The player explained time, identity and method in separate paragraphs, but
  grading demanded time citations again inside the identity paragraph. Connected
  supported arguments now share their actually cited evidence across aspects;
  each aspect still needs a supported exact quote and a sufficient proof route.
  Older pinned operations retain their grading for reproducible recovery.
- The ending text contradicted a successful personal objective in the score
  table. Updated guidance leaves score calculation to the authoritative table
  and asks the narrator for causal and relationship consequences.
- Repeated public sharing could earn the same two key-record credits for everyone.
  New murder cases credit the first public disclosure of each identity-route
  record. Supporting victory additionally requires a correct suspect and a
  supported time or method argument. A complete personal reconstruction remains
  an alternative. Personal disclosure objectives retain their own action semantics.

Version-two new cases keep three families but use distinct proof structures:
clock cases use calibrated opportunity; recording cases combine a false voice
alibi with tool custody, fracture evidence and dated before/after photographs;
substitution cases combine cup identities, an anonymous swap, badge lending and
preserved analysis. The latter two no longer expose a named sole entrant through
an all-solving entrance backup. Initial registration points to an innocent lender
until actual custody is investigated. A participant holds a signed counterfoil
with a private annotation, creating a disclosure tradeoff; an independently
searchable archive supports another route without requiring a confession.
Truth, private experienced facts, evidence and proof requirements are compiled
once. Existing saved cases and pre-v30 setup operations keep version-one assets.

Version 30 role context includes only the recipient's outstanding requests, its
own recent actions, running activity and previously shared material. Private
cumulative reasoning is separate from tactical outward speech; neither another
role's thoughts nor unobserved private conversation is supplied. Roles can remain
silent when no reply is required and choose a useful investigation action.

Cancellation now removes only the original background queue entry, is idempotent,
and never consumes an AI turn when cancelling a failed human command. A late
cancelled response cannot reinstall a background error. Retry exhaustion is shown
before another click; pending processing and connection/model-output failures
have distinct readable feedback. No automatic paid retry loop is added.

The second full playthrough exposed two remaining grading problems: a redundant
initial-registration citation was required even when actual custody was proven,
and the model sometimes classified an opportunity argument as time rather than
identity. Rules version 3 removes that redundant proof premise and treats
original/counterfoil or original/copy pairs as one key contribution. Version 34
makes the existing final-theory call assess each aspect of the whole argument,
with eligible proof routes as a coverage aid; it remains one call, with exact
quotes and acquired citations. Version 35 supplies literal recent public speech
to the epilogue, excludes private dialogue and individual score tables, and
distinguishes admitting object handling from confessing to killing. Versions
29-34 remain immutable for pinned recovery. All current tasks still use Flash.

## Playability Acceptance: 2026-11-06

Receipt: `.local/verification/playability-20261106/report.json`.

- Three complete test-owned, player-view-operated playthroughs reached closure:
  the v29 baseline, a revised recording case and a revised substitution case.
  The operator did not read those cases' solutions before submitting, but already
  knew the application's puzzle families. This is not a blind human study.
- The original incorrectly graded arguments remain unchanged in their original
  ended fixtures. Separate clones using v34 classified both exact arguments as
  established. A v35 counterexample selected all evidence and guessed the correct
  name with no explanation: it remained unproven, with no established aspects.
  Receipts: `regrade-result-v34.txt` and `negative-result.txt` in that directory.
- The final substitution playthrough established all three aspects. Its human
  completed the primary goal but lost the personal protection goal when the
  actual lender chose to publish a counterfoil containing private information.
  A role inspected the counterfoil before sharing it. The outcome followed
  actual choices; no confession or private answer oracle was required.
- 84 real Flash requests: 83 completed and one retained v31 `role choice` failure
  (`share` of an uninspected record). That isolated operation was explicitly
  cancelled, then play continued under updated action-contract guidance. Final
  v35 calls: 10, all completed. Total reported upper-bound cost: USD 0.077743932;
  input-weighted provider cache hit rate: 45.96%. These are sample measurements,
  not a price guarantee or a zero-error claim.
- 114 Python regressions pass, including causal variants, connected reasoning,
  negative argument cases, legacy/pinned recovery, private focus/ending isolation,
  one utterance per invitation, copy-credit deduplication, retry exhaustion and
  cancellation of in-flight work. Six frontend checks and JavaScript syntax pass.
- Twelve browser scroll/control checks and the five-part multiplayer flow pass,
  with no page errors. Receipts: `.local/verification/browser-scroll/report.json`
  and `.local/verification/browser-ensemble/run-ccc71ab1.json`.

The new puzzles remain three bounded compiled families. Population win rates,
long-term variety and consistent prose quality still require more human play.
The recorded examples establish particular fixes and executable tradeoffs; they
do not establish that every generated response will be natural or error-free.

Deployment: the loopback service was started with Flash and v35 after a consistent
backup at `.local/backups/pre-playability-20261106-005647.sqlite3`. All seventeen
game-state hashes matched after startup; served assets matched the verified files.
Receipt: `.local/verification/playability-20261106/deployment.json`. New cases use
the revised structures and objectives; existing games retain their frozen cases.

## Contextual Dialogue Cues: 2026-11-06

The user requested microexpressions informed by truth, knowledge and context,
shown beside each associated utterance. Version 36 extends the existing scoped
DM call from two fixed pause/gaze controls to short model-authored audible or
visible details. Known deception, mistaken belief, sincere stress and uncertainty
inform delivery without exposing verdicts or motives. Ordinary lines may have
no cue; no fixed lie-to-expression rule, extra review call or prose filter was
introduced. Original speech remains exact. See module 10 for the contract.

Recipient views attach only already-received cue observations to source speech,
including older saved records. Recent dialogue and the complete transcript show
the detail together with the original sentence; recent scene changes omit the
duplicate. Visual cues retain utterance-time location restrictions, and private
cues stay inside their conversation. Published versions through 35 are unchanged,
and pinned operations retain their previous contracts.

Verification:

- 57 relevant Python tests pass, covering ensemble play, playability and DM
  contracts, including original-word preservation, scoped attachment of older
  cues, natural cue text and audible/visible recipient differences.
- Six frontend checks and the updated JavaScript syntax check pass. Thirteen
  browser checks pass across the three runtimes with no page errors, including
  human/AI inline cues, complete history, duplicate removal and scroll retention.
  Desktop/mobile cue screenshots were inspected. Receipt and screenshots:
  `.local/verification/browser-scroll/`.
- Three real Flash DM requests on a new synthetic fixture completed. The four
  public claims were assessed as known contradiction, supported, mistaken and
  uncertain; the private statement and cue stayed private. Generated cue text
  described observable delivery and included stress with sincere speech.
  Reported conservative cost: USD 0.002326308. Receipt:
  `.local/verification/microexpressions-20261106/live-result.json`.
  This small feature sample does not establish cue frequency or game balance.
- The systemd service was reloaded after confirming no in-flight operation and
  making a consistent backup. All eighteen game-state hashes were unchanged;
  homepage, assets and session API returned HTTP 200. Deployment receipt:
  `.local/verification/microexpressions-20261106/deployment.json`.

Refresh the page for inline rendering; new operations in existing ensemble games
use the new DM contract. No new game is required.

## All-AI Spectator Mode: 2026-11-06

Separate zero-human games now use an authenticated observer instead of character
A. The omniscient UI includes fixed truth, public/private dialogue and individual
role information. Roles retain ordinary recipient contexts with no observer or
controller metadata. Actually heard speech is optional usable information; it
does not become established truth and cannot expose unheard private exchanges.

The scheduler continues fairly without a human-triggered agenda. Start, pause,
single-step, speed, a sixty-second disconnect pause, stagnation detection and
explicit spending controls operate outside fiction. Three role agreements open
independent conclusions; all four submissions still precede ending evaluation.
New normal-game roles can also use collective closure, while humans retain their
own action choices and explicit submission barrier. Existing frozen facts and
older pinned operation contexts remain intact.

Versions 37-41 add these contracts and targeted context corrections. 136 Python,
six frontend, seven spectator-browser, thirteen scroll/control and five
multiplayer-flow checks pass. Real Flash samples exercised autonomous play and
budget/error pauses; they do not yet demonstrate natural all-AI completion within
the default USD 0.10. Full receipts, measured costs and limits are recorded in
[Spectator mode](18-spectator-mode.md).

The user subsequently made spectator call limits manually extensible in 64-call
increments, independently of the USD 0.05 budget control. Older count-paused
games recover their original operation after an explicit addition and resume.
Version 42 also guides role speech, thoughts, memory, reasoning and relationship
reasons into first-person self-reference; input hints use the same perspective.
See modules 18 and 09 for boundary tests and the four-call real-Flash voice sample.


## Shared Role Review Fixes: 2026-11-06

The completed spectator-game review produced shared role-context, action,
communication and final-grading fixes under v47. Human conclusions can optionally
cite actually heard speech. AI final submissions are selected separately from
private beliefs. Existing proof guards and heard/private information boundaries
remain. Implementation details, real-model limits and verification receipts are
recorded in [Spectator mode](18-spectator-mode.md#review-fix-implementation-2026-11-06).
