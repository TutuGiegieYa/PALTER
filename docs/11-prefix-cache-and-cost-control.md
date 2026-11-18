# Immutable Prefixes and Cost Control

Status: V120 was deployed at the user's explicit restart request on 2026-11-10, including independent DM budgets and lossless snapshot/citation sharing. Regression, scoped real-model probes, service health and state-preservation checks pass. The earlier whole-game acceptance remains incomplete; this deployment does not establish full narrative acceptance.

Last updated: 2026-11-10.

## Shared DM Knowledge Snapshots: 2026-11-10

Status: v120 implemented and deployed; regression, read-only replay, two synthetic
real DM probes and restart/state-preservation checks pass.

The user's subsequent approval replaces the old shared DM budget with **512,000
dynamic bytes and 1,000,000 total request bytes**, measured on the final serialized
request. Other tasks retain 51,200/90,000 bytes. Completion caps, disabled thinking,
call/retry policies and conservative per-game cost admission remain unchanged.
The v120 task flag gates the new wire format. The larger DM admission limits also
apply to older pinned operations, so a stalled v119 DM stage can retry without
changing its prompt or replaying already completed paid stages. Stored/published
request layouts remain unchanged. All 138 existing artifacts are intact.

`dm_context.py` compares inline, normalized historical snapshots, pooled exact
snapshots/components and reversible citation-range variants using complete request
sizes. Only a smaller representation replaces an inline one. Parsing instructions
live in the new immutable DM prefix, not repeated dynamic explanations. Snapshot
pool keys include actor identity; event occurrence metadata remains on each event.
The source-body pool retains identity/version distinctions. Reference expansion
preserves the normalized information view exactly. ID ranges never sort lists,
invent missing members, remove duplicates, merge different actor prefixes or
rewrite player prose/validation feedback. Output IDs and stored originals stay
unchanged. No extra runtime model call or semantic summarization is introduced.

Actual gateway verification receipts: `.local/verification/dm-snapshot-v120-20261110/`.
Read-only reconstruction matches 27 historical paid request hashes, including the
completed role stages preceding two failing DM requests. The historical DM measures
44,307 dynamic bytes versus 55,509 before (11,202 bytes / 20.18% less), and 66,924
total bytes versus 77,041. The normalized source view with citation ranges is
smaller than wrapping these two distinct snapshots in additional references, so
the final request keeps them inline. It preserves both occurrence-time views.
Thirteen recent DM requests average 12,704 versus 12,721 dynamic bytes; none grows.
Non-DM v119 requests remain exactly identical. Synthetic batches of 1/4/20 snapshot
occurrences measure 4,763/7,538/12,001 dynamic bytes versus 5,523/10,578/102,155;
the twenty-occurrence fixture intentionally shares substantial content and is not
a prediction of production savings.

Two synthetic DeepSeek Flash calls pass the ordinary DM validators and assess
every new utterance: a public four-role batch uses eight snapshot definitions,
eight shared components and four range groups; a private two-role batch uses
four snapshots, four components and two range groups. Both finish without retries
or truncated output. Recorded upper cost is USD 0.003823332 within a USD 0.10 /
four-call cap. These scoped probes do not establish whole-game acceptance or a
provider-token/billing reduction against the old prompt. No production transcript
was sent and no production game was advanced by verification.

The latest paused production operation `watch_ea788383_327` has a completed role
stage and no paid DM attempt. Its reconstructed v119 DM is 56,483 dynamic / 77,871
total bytes, admitted unchanged under the larger runtime guard. V120 projection
of that same input is 51,175 / 73,648 bytes. Its completed role request hash matches;
the recovery replay makes no new provider call and changes no game state.

Verification passes 639 non-HTTP regression cases plus five HTTP cases (644 total),
the frontend test, and 75 targeted recovery/admission cases after the final legacy
DM-guard adjustment. The initial discovery command had a package-relative import
error for the HTTP module; those five tests were rerun successfully through
`python -m unittest tests.test_http` with an isolated local server. All 139
published artifacts pass the contract gate; 138 prior file hashes are unchanged.

The authorized restart completed at **2026-11-10 20:50:38 CST**. The user service
is active/running, with PID 779586 replacing 739168 and the project Conda interpreter.
The homepage and three JavaScript assets return HTTP 200. Before/after hashes match
for all 43 games, 5,138 AI calls, 2,411 operations and two legacy model calls. No
pending calls were interrupted, no provider request was made by deployment, and
the latest game remains paused at step 271/revision 330 for the user's retry.

### Earlier exploratory measurement

Normalize both current speech and historical gesture snapshots through the same
source-body projection. Each event keeps its actor, time, audience and a reference
to its occurrence-time knowledge snapshot. Identical snapshots of the same actor
may share an ID; identical component values may share storage across snapshots.
Sharing bodies never unions knowledge, changes source authority or moves later
knowledge into earlier events. Distinct source versions and occurrence IDs remain
distinct. Preserve stored originals, chronological arrays and published request
versions. No semantic summarization, provider call or source truncation is added.
The initial experiment retained the old 51,200/90,000-byte limits while measuring
a locally reconstructed failed request and multi-actor batches. The subsequent
v120 approval above supersedes those DM limits.
Byte savings are not measured provider-token or billing savings.

The local candidate in `.local/verification/dm-snapshot-20261110/compare.py`
reconstructs the historical failing DM input and thirteen recent paid DM requests
using read-only databases and stored outputs. Historical paid request hashes are
checked before projection. Reference expansion restores the normalized snapshot
view exactly, preserving actor binding and list order. No provider is invoked.

For the historical failure, final dynamic bytes fall from 55,509 to 45,191
(10,318 bytes / 18.59%), including the reference-format explanation. Two distinct
occurrence-time snapshots remain; their whole memory/belief/evidence-list values
are not identical. Savings come from shared source bodies and projecting the raw
historical snapshot's redundant memory representation, not from unioning knowledge.
Exact ID-range encoding further reduces it to 45,119 bytes, a net 72 bytes after
its format explanation. It preserves prefixes, numeric padding, gaps, duplicates
and list order, and is verified by expansion. Individual output IDs stay unchanged.

Thirteen recent requests average 12,721 dynamic bytes before, 12,759 with snapshot
references and 12,764 with additional range support. Thus unconditional reference
wrapping is not beneficial for ordinary small/single-snapshot inputs. A runtime
implementation should measure candidate representations and use a smaller one;
these local measurements do not justify claiming universal savings or a guaranteed
bound. Keep the existing hard guard. The candidate is not a production fix or
an end-to-end model-behavior acceptance result.

## Cache-Oriented Context Ordering: 2026-11-10 (v118)

Status: implemented; offline equivalence, historical replay, regression and a
bounded real cache comparison pass. Initially withheld because the preceding
dialogue/generic receipt candidate has incomplete whole-game acceptance; later
included in v119 at the user's explicit restart request. The cache verification
itself did not advance, pause or restart a production game. Receipts:
`.local/verification/cache-order-20261110/`.

The user requested improving cache reuse by rearranging context. V118 opts role,
DM and memory inputs into `context_order_version=2`. It changes dictionary-key
order only: format, actor/perspective, rooms, objectives, source-access rules,
snapshot limits, conclusion contract and stable conditional guidance come first;
sources then precede the remaining changing state. Validation feedback,
investigation reminders and the existing dialogue focus remain at the end.
Guidance puts recurring scheduling/speech rules ahead of conditional event/final
rules. A current utterance referenced by `text_ref` is sorted with changing bodies,
not with initial facts just because its body contains only `text`.

The implementation preserves every selected field/value, source ID/body and array
order. It neither freezes source-pool membership nor changes memory compression,
source selection, permissions, input limits, model settings or output schemas.
Memory tasks use the ordering helper without enabling the separate context-economy
protocol. Static system/baseline messages and their cache fingerprints remain
identical to v117; only dynamic JSON key placement changes. All 136 previously
published artifacts remain intact. Versions through v117 retain their layouts.

Read-only replay of the running v113 production case at step 153 matches 297 paid
request hashes across 153 completed operations. Applying the candidate order to
those reconstructed bodies preserves parsed JSON and exact byte lengths. Median
consecutive matching dynamic-prefix bytes, grouped by task/actor/fixed fingerprint:

| Task | Previous order | Candidate order |
| --- | ---: | ---: |
| Role | 296 | 3,083 |
| DM | 937 | 1,816 |
| Memory | 34 | 245 |

These are byte-prefix diagnostics, not provider cache-hit measurements. The live
test uses authored synthetic role/DM snapshots only, five rounds for each task and
layout, with alternating arm order and separate stable run markers. Both layouts
receive equivalent snapshots and unchanged generation settings. The first two
rounds per arm are warm-up; the last three give these provider-reported ratios:

| Task | v117 order | v118 order |
| --- | ---: | ---: |
| Role | 53.76% | 58.96% |
| DM | 71.65% | 78.15% |

All twenty requests return complete cache-usage accounting. Total estimated cost
is USD 0.017562516, within the USD 0.10 / twenty-call test cap. Fifteen responses
also pass the ordinary decision validator; five role responses fail memory-source
validation (three old-order, two new-order). No retries are purchased and no outputs
are applied to later snapshots. Raw requests, responses and failures are retained.
This is a cache experiment, not a claim of complete-game reliability, guaranteed
production hit rates, reduced retry cost or measured memory-task cache gains.

Full regression passes 625 tests in 167.653 seconds. Seven new checks cover role,
DM and memory value/size equivalence, unchanged fixed prefixes/settings, native
tool messages, correction feedback, current-speech classification, unknown-field
retention and published-version isolation. Existing privacy, source authorization,
input-budget and chronological-history tests also pass. No additional runtime
model call or cache-prewarming activity is introduced.

## Live Cache Diagnosis: 2026-11-10

Status: diagnosed read-only; no cache-layout implementation, model request,
service restart or production game mutation in this audit. Receipts:
`.local/verification/cache-audit-20261110/`.

The latest running production case is `ea788383f5cebd7562a5dbba`, using v113
throughout. At step 117, 223 calls with complete provider usage report 46.2% input
cache hits; the latest fifty report 43.8%. Role decisions report 42.1%, DM 53.8%
and memory 37.9% (only four memory calls). The first fifty requests average 7,435
input tokens and 3,901 cached tokens, versus 9,937 and 4,355 for the latest fifty.
The growing uncached suffix is a major contributor to the declining fraction;
this production case is not being repeatedly switched between test prefixes.

An earlier consistent snapshot at step 98 reconstructs 178 paid request hashes
across 98 completed operations without any provider call. Role requests have four
fixed fingerprints, one per role; DM has eight. Of 98 comparable role requests,
90 first differ in source-pool membership/order. Median identical dynamic-prefix
length is only 858 bytes for roles and 589 bytes for DM. Source selection varies
with authorized recent observations, acquired material, current reasoning and
the optional-body budget. The source pool precedes actor/rooms/objectives, so an
early pool change also limits reuse of later unchanged fields. These are byte
comparisons, not measurements of provider tokenizer boundaries or cache retention.

The UI uses the provider's hit/miss counts and the token-weighted ratio, excluding
unreported usage. No display-calculation error was found. DeepSeek's current
documentation describes matching persisted common-prefix units, with best-effort
retention; unchanged text later in a changed request is not by itself a cache hit.
[Official context caching guide](https://api-docs.deepseek.com/guides/kv_cache/).

Proposed next work: move unchanged scoped fields ahead of changing state; keep a
bounded stable evidence-body block with explicit refresh boundaries and put new
receipts/current metadata later; reduce repeated DM event bodies. Preserve source
authorization, original history, paid request bytes and existing input limits.
Validate information equivalence and request sizes offline, then measure provider
cache hits, uncached tokens and total cost with a bounded real probe. Higher cache
hit percentages are not promised before that measurement.

## Dialogue Purpose and Attribution: 2026-11-10 (v117)

Status: implemented; regression and targeted model checks complete. Fresh whole-game
acceptance of v117 failed; it was initially withheld and later included in the
user-requested v119 deployment. That restart does not change the failed acceptance
result. Receipts are in
`.local/verification/dialogue-purpose-20261110/`.

The user approved three changes for cross-role paraphrasing: choose speech by
individual communication purpose, highlight own prior speech without duplicating
bodies, and preserve ownership of duties/experiences/promises. V114 implements an
own-only index and initial guidance, but the controlled real dialogue experiment
still includes an exact copied utterance and a copied duty. It is retained as an
undeployed experiment, not presented as a successful fix.

V115 strengthens the guidance and ends the dynamic input with the current speaker,
two own received speech IDs and three actually heard peer speech IDs. All text
continues to use the existing source pool or authorized historical lookup. No new
output field, model self-review, speech filter, timing policy or semantic novelty
classifier is introduced. Temperature, thinking and completion caps are unchanged.

The initial fresh v114 trial stops at step 8: an investigator emits an inapplicable
strategy patch with invented fields, and all four attempts fail. Existing
perspective rejection ran after patch parsing, so feedback named patch shape
without identifying the actual forbidden field. The permission check now runs
first and uses the generic actual/expected receipt. Its original failure report
is retained. One explicit recovery of this isolated game is used to verify the
repair; its paid v114 stages stay pinned, with new operations using v115. No plot
hints, forced votes, budget extensions or stagnation resumes are permitted.

Regression passes 617 tests in 169.342 seconds. Nine dialogue tests cover speaker
isolation, private channels, exact source reuse, omitted-source lookup, native
continuations, original occurrence retention, old versions and field permissions.
All 132 artifacts published before this task remain unchanged; v114 and v115 are
new immutable artifacts. The previous generic text/reference receipt fix remains
included in the release candidate.

Controlled dialogue tests use authored synthetic histories and a wait-only scene
menu supplied equally to each version. They are dialogue probes, not full-game
playability tests: no provider output is rewritten and waiting roles are skipped
until real scoped input wakes them. Two fixtures with three rounds/four roles yield
24 real role decisions per version. V113, v114 and v115 raw transcripts and paid
receipts are retained. V115 has no exact copied utterance or direct duty takeover
in these samples, but some repeated discussion of plans remains. Offline character
similarity is a diagnostic only; it never controls production output and is not
a semantic-quality guarantee. A longer repetitive-history probe is also retained.

The longer v115 trial disproves a blanket improvement claim: successive roles
still paraphrase questions and plans. It pauses at step 146 after 316 calls and
estimated USD 0.647664180, with no submissions or ending. The final four attempts
alternate a non-testimony source in `belief_update.testimony_ids` and a thirteen-entry
memory delta exceeding the existing twelve-entry limit. Its original paid rows
remain identical. This is a failed whole-chain acceptance, not a passed recovery.

V116 keeps the index/schema and moves a shorter dialogue contract to the end of
the role instruction: one current contribution, usually one sentence, with longer
answers or arguments when necessary. Do not echo an unanswered question or
re-announce settled duties; brief acknowledgment, gestures and permitted silence
remain valid. The same two synthetic scenes yield 24 successful role decisions,
estimated USD 0.033334800; one long similar pair and repeated plan language remain.
The restricted stationary menu limits how well these probes represent gameplay;
they do not prove semantic novelty or successful action execution.

An injected wrong-perspective field followed by one real Flash correction succeeds
with the generic field-permission receipt (USD 0.001093536). Local historical replay
matches 871 paid request hashes across 421 operations, with zero provider calls.
All 132 original artifacts remain unchanged; v114/v115/v116/v117 are new immutable
artifacts. The fresh v116 game stops under the unchanged stagnation guard at step
119: 261 real calls, USD 0.533383926, no final submissions or ending, and no unresolved
error. Fourteen failed attempts recovered within the existing retry allowance,
but complete-chain acceptance is false. No manual recovery was used.
The final v116 regression passes all 617 tests in 169.737 seconds. Its live game
also contains repeated waiting announcements and occasional copied phrasing;
shorter turns and explicit attribution do not guarantee semantic diversity.
No output filter, automatic rewriting, extra review call or changed wait allowance
is used to hide these retained raw results.

V117 retains attribution and concise turn-taking guidance, but moves only the
already supplied recent utterance bodies into `dialogue_focus.sources` at the
end of the dynamic context. Top-level sources plus this small pool resolve the
same IDs and contain each body once. Budget fitting measures the final layout;
no omitted source is reinserted and no old prefix changes layout. This is an
additional layout intervention after the limitations of guidance-only probes.

A paired diagnostic copies that stopped test-owned state into separate v116/v117
branches, each with one explicit diagnostic resume and eight natural scheduled
steps. The original stopped trial is untouched. V116 makes eight stationary
choices; v117 makes six stationary choices, one move and one inspection, and six
utterances. Both branches retain attribution and no exact copied utterance is
observed in this small sample. These branches cost USD 0.045063996 and USD
0.043462704 respectively. This is not complete-chain acceptance or causal proof
of improved gameplay. A failed initial harness invocation lacked an observer
membership and made zero provider calls; its report is preserved.

The source-pool change passes ten dialogue checks including one-body preservation,
omitted-body lookup and unchanged v116 layout. The final full regression passes
618 tests in 167.524 seconds.
An additional read-only replay matches all 259 paid hashes across 119 completed
v116 operations, with no provider calls. Test fixtures resolve both source pools; production source authority
and stored histories are unchanged. The original fixture-adapter errors are retained
alongside the corrected passing tests.

The final fresh v117 trial `dcda603745b40001ed75d50f` stops at step 170 with
`context_budget` in `dm_public`, after 384 real calls and estimated USD 0.851585688.
There are no final submissions, evaluations or ending, so acceptance is false.
No manual recovery, additional budget, forced votes or production game advancement
is used. Its later dialogue still includes repeated questioning: neither shorter
turns nor source placement establishes complete prevention of semantic repetition.

Read-only replay reuses the completed role stage exactly and reproduces the DM
failure under v113, v116 and v117. The DM task contracts are identical. Each
produces 55,509 dynamic bytes and 77,041 total bytes; the dynamic cap is 51,200.
Largest fields: `recent_actual_events` 23,439 bytes, `sources` 12,137 and `utterances`
9,887. This isolates the immediate budget failure from the role-only source-pool
move; it does not show that differing model trajectories have equal growth.
Diagnostic serialization temporarily raises limits only inside an isolated read-only
script, sends no request and changes no application limit. The outstanding DM
context growth and long-game dialogue convergence require further work.

The candidate and all failed trials remain available for review. No service restart
or release is performed; the prior generic-receipt work remains pending the same
complete-chain gate. See `final-report.json`, `budget-diagnosis.json` and
`production-preservation.json` for the consolidated result and preservation checks.

## Generic Validation Receipts: 2026-11-09

Status: implemented; regression, replay and targeted real corrections verified.
Fresh whole-game acceptance remains incomplete. The historical second trial
stopped on provider HTTP 402; after the user reported a top-up, a read-only balance
check confirmed funds and new verification resumed in the dialogue record above.
Not deployed; the running service has not been restarted.

The user requests reusable correction receipts rather than instructions tailored
to a particular incident. Shared text/reference validators will report expected
constraints, actual invalid values or measurements, exact field paths and
machine-derived reasons. Reference kinds come only from the recipient's own
received observations, acquired records and initial facts. Unknown IDs must not
reveal whether another role owns them. A failed patch remains unapplied; correction
guidance explains replacement/add/remove semantics without selecting story actions
or changing the model's reply. Large rejected values and diagnostic samples must
be bounded; this does not cap accepted citations or rewrite stored records.

Only failed attempts receive the dynamic receipt. Keep all published prefixes,
successful-request bytes and retry limits unchanged. Verify shared reference/text
contracts, patch expansion, old received sources, foreign-source isolation,
retry continuity, successful paid-stage reuse, local historical replay and real
synthetic corrections. Whole-game acceptance must be reported separately from
targeted correction tests. Production play is not a test fixture.

The shared `validation_receipt` reports `expected`, `violations` with expanded
paths and actual values/types, `value_basis`, and `rejected_update_applied=false`.
The same correction instructions apply to every supported text/reference field.
Source diagnostics distinguish known kind mismatch from an unavailable reference
without looking up global/private records. Known alternatives are field permissions,
not orders to move a citation. At most eight invalid details and 160 characters per
invalid string are shown, with explicit omitted/truncated counts; complete source
authorization and uncapped accepted citation lists remain unchanged. Text failures
report lengths without echoing the rejected prose. Other existing validator
families retain their established contracts; this is not a replacement of every
validation branch or a guarantee of first-retry success.

Verification receipts: `.local/verification/contract-receipts-20261109/`.
Four synthetic probes inject one failure each: wrong received-source kind,
misplaced known source, unavailable source, and excessive text length. All four
recover in one real Flash role reply each (USD 0.004232376 total). The initial
faults are test doubles, not provider failures; production transcripts were not
sent externally. Read-only local replay matches 782 paid hashes across 379
completed v111/v112/v113 operations and preserves all 132 prefix artifacts. All
seven rejected replies in the reported operation now identify the same invalid
observation ID and kind locally, without changing those historical receipts.

Full regression passes 608 tests in 166.591 seconds. Nine new tests exercise
structured diagnostics, bounded samples, uncapped valid references, patch
non-application, older received sources, unavailable/foreign source isolation,
JSON-error continuity and corrected paid-stage reuse after a later failure and
restart. The first suite run's only failure was an obsolete assertion that no
submitted invalid ID may be echoed; the updated assertion checks that echoing
the model's own invalid value discloses no hidden source kind/body or alternative
permission. Both the initial result and the passing rerun are retained.

The first fresh real murder game pauses under the unchanged stagnation guard
at step 101, after 217 Flash calls (USD 0.432990312). There is no unresolved
model error, but no closure/submissions/ending either: its acceptance result is
false. Do not describe this as a successful chain or resume it with hidden hints.
Seven natural source-kind failures recover under the new receipt; six pass on
the next attempt and one also encounters another validation error before passing
within its four-attempt round. `first-natural-corrections.json` records each
failing/successful attempt. Both trials remain in the final report.

The second fresh case `9dd1be532d7aea935698b42a` stops at step 89 with provider
HTTP 402 (insufficient balance), 163 attempted calls and estimated USD 0.260371344.
Its seven output-validation failures recover, but the provider failure is unresolved;
there are no final submissions or ending. That runner made no further provider
call or automatic resume after the balance error. The user was asked to report a top-up so
the same isolated case can resume with an explicit recovery, preserving the first
non-passing report. Total estimated test cost, including the four probes and both
fresh trials, is USD 0.697594032 (usage/reservation estimates, not an invoice).

The release gate still requires fresh complete-chain acceptance. Code and tests
are ready, but deployment is pending that gate; do not present either paused
trial as success. Production games and paid receipts were inspected read-only,
with no game advancement or service restart by this change.

## Role Correction Continuity: 2026-11-09 (v113)

Status: implemented, verified and deployed. Fresh whole-game acceptance passed
after one explicit test-budget extension; all semantic choices remained model-owned.

The user approved fixing the mixed failure chain in `watch_d1ea4ea1_22`:
misplaced strategy sources, forbidden silent continuation, malformed final JSON,
then the same forbidden continuation. Preserve the rolling wait limit. Supply
explicit current scheduling modes and stationary-action requirements. Normalize
equivalent patch-envelope fields only when known and nonconflicting; source and
effect permissions remain strict and raw receipts remain unchanged.

Correction state is scoped to game, operation, role and provider stage. Keep one
unresolved issue per validation group. A valid check clears that group's prior
issue; checks not reached remain unresolved. Invalid JSON clears no semantic
issues. Persist the compact issue state in existing feedback receipts so retry
rounds and restart retain it without replaying a growing prompt history.

After malformed final JSON, the same stage's remaining retries use JSON output
and disable new tool selection, retaining tools/results already supplied. Empty
or truncated output remains invalid. Do not add a normal extra model call or
increase the existing initial-plus-three retry allowance. Tool argument errors
do not disable tool use. New v113 requests opt in; unfinished v112 role stages
receive the correction only on a new unpaid retry. Completed stages reconstruct
their exact stored feedback/settings and never repurchase successful results.

Verification must cover alternating semantic/syntax errors, conflict and source
rejection, tools followed by JSON correction, manual recovery/restart, exact
historical request hashes and isolated real-model behavior. Production transcripts
stay local and the affected production game remains paused for the user's retry.

Receipts: `.local/verification/role-recovery-20261109/`. Full regression passes
599 tests in 165.870 seconds. Ten added tests cover mixed failures, resolved-field
removal, ambiguous and foreign-source rejection, native continuations, bounded
exhaustion, manual retry/restart and exact reuse of a corrected paid role stage
after a later failure. Existing related tests also pass.

Two hybrid synthetic cases explicitly inject field conflict, forbidden idle and
malformed JSON before a real Flash correction. Investigation and concealment
each recover with one real provider call on the fourth allowed attempt, choosing
an available inspection. Six injected failures are test doubles, not observed
provider failures. The two real calls cost USD 0.001996512. This proves targeted
correction behavior, not a complete game.

Read-only reconstruction matches 376 paid request hashes across 191 completed
v111/v112 background operations and preserves all 131 prior prefix artifacts.
The failed production operation's four original hashes also match. Its next
unpaid correction keeps the unresolved wait issue and selects final JSON mode.
An explicitly edited local stub (the third draft plus its missing final brace)
validates the original available inspection; it is not a provider result and is
never written back to production. The actual production game is not resumed.

A third hybrid probe includes an executed synthetic native listener and its tool
receipt before a malformed reply. One real Flash correction succeeds in JSON mode
with tool_choice=none, retains the receipt exactly once, and chooses an inspection.
Its real cost is USD 0.000658968; injected calls are not counted as provider calls.

The fresh all-AI murder case `4a6f28d46cccd3c5ac4cd41d` reaches `ended` at step
148 with all four final submissions, four participant evaluations/theory reviews
and ending narration. It makes 284 real Flash calls at estimated USD 0.579860472.
Eighteen failed output-validation attempts (16 role, one DM, one theory) recover
within the existing automatic retry allowance; there is no unresolved error or
pending call at completion. This is successful recovery, not error-free generation
or a narrative-quality guarantee. A/B establish their cases, C remains unproven,
and D's concealment position is recorded independently.

The initial USD 0.50 / 256-call test run paused at step 132 for budget admission;
its original non-passing report is preserved. One explicit extension to USD 1.00 /
512 calls and one resume complete the same test-owned story. No hints, forced
votes, manufactured submissions, story edits or stagnation resumes were used.
`continuation-report.json` and `complete-chain-check.json` record final acceptance;
the original `fresh/` report remains the first-run failure receipt. Total real
verification cost, including the three targeted corrections, is USD 0.582515952.

Deployment at 22:13:04 CST starts PID 651146, active/running with HTTP 200.
Before/after full table hashes match for 42 games, 4,082 AI calls, 1,905 operations
and two legacy calls. No request was pending. The affected production game stays
paused at revision 23 / step 7 with its original retryable error, ready for the
user's explicit retry. No production provider call or game advance occurred.

## Contract Synchronization Fixes: 2026-11-09 (v109)

Status: Seven fixes implemented and deployed; contract verification passed; fresh
complete-chain acceptance not achieved. Supersedes the seven
open findings in the dated v108 audit below. Published v108 and earlier artifacts
remain immutable. Production remains paused for the user's explicit retry.

- Shared `model_contracts` limits drive setup validation/guidance and native tool
  schemas. Event and source lookup errors identify the exact field and bound.
  Current-prefix consistency is checked at startup and with the offline
  `python -m palter.check_contracts` release gate; old versions are hash-checked,
  never compared against new semantics.
- Removed the stale twelve-testimony clause from current investigation guidance.
  Human common-input citations also have no arbitrary forty-item cap; source
  permission, type and HTTP/request-body boundaries still apply.
- Active-memory capacity repair retains the role's incremental
  `memory_update.upsert/archive/processed_through` contract. Archive superseded
  stored IDs explicitly; omission does not delete them. Standalone overflow
  still requests a complete regrouped snapshot. No source/text slicing occurs.
- Event reviews supply explicit allowed-source lists. Bounded old receipts
  referenced by current DM context can be restored from the creator's own
  observations, never global event bodies. Unpaid pinned retries can restore up
  to eight old receipts / 4,000 serialized bytes per creator in persisted feedback.
  Their observation positions must precede every relevant review range; they
  neither advance a cursor nor count as new messages or fixed-event completion.
  Unknown or another role's private IDs remain unauthorized.
- `check_spectator` separates `runner_finished` from `acceptance_passed`, exits
  nonzero for incomplete/error/paused games, and requires all four submissions,
  participant evaluations, murder reasoning records and ending narration.
  It does not force closure or automatically resume operational pauses.
- Module 14 now describes the current 29-definition prefix, retry behavior,
  budget extensions, thinking setting and memory policy. Dated prices and older
  runtime measurements retain their historical scope.

Latest production failure: `watch_0632efa6_211` cited departure event `e000252`.
Creator A actually received `A-o000166`, but the bounded background omitted it.
Local reconstruction matches all ten stored paid request hashes in that operation;
restoring only that original scoped receipt makes the rejected source list valid.
This is contract verification, not a new model judgment or a resumed production
operation. Evidence: `.local/verification/contracts-20261109/latest-error.json`.

Verification so far: 571 regression tests pass (`tests-release.log`); 1,569
historical requests across 676 operations retain exact hashes, and all 126 older
prefix artifacts remain unchanged (`replay-report.json`). Twelve new cross-task
contract tests cover boundaries, scoped recovery, restart reuse and acceptance
failure exits. Current-prefix integrity originally included 127 artifacts; 129 now include the
immutable v110 test candidate and its guidance, which are not active in production. A separate local
reconstruction verifies the latest failed production operation without sending
its transcript to a provider. Misplaced authorized testimony now receives
field-specific feedback identifying `testimony_ids` instead of treating a spoken
claim as an original document; failed patches remain unapplied.

A targeted hybrid fixture injected a synthetic 10-to-13 active-memory overflow;
one real model call then returned the correct incremental contract, archived
seven superseded IDs and retained three entries. Estimated real-call cost was
USD 0.001420728 (`active-memory-live.json`). The rejected first draft was a test
injection, not a claimed natural model failure. An earlier harness invocation
used an invalid command ID and stopped before any provider call; its log/database
are retained separately.

Service updated at 2026-11-09 18:15:38 CST (PID 602316), HTTP 200. Pre/post hashes
of all games, provider calls and operation rows match; the latest production game
remains paused at revision 216 / step 177. No production model call or automatic
resume occurred (`deployment.json`).

Fresh trial 1 reached the existing stagnation pause after 200 steps / 430 calls,
with 24 completed memory consolidations and no unresolved provider/validation
error. There were 23 rejected attempts recovered by bounded automatic retries.
Estimated upper cost: USD 1.0651293. It had no submissions or ending, so the runner
correctly exited 1; this is NOT a complete-chain pass. No manual recovery or
forced closure was performed. The configured cap was USD 1.50 / 512 calls.

A second fresh fixture selects the clock-family seed before case creation to
cover a different initial mechanism. All authoring, actions, dialogue and votes
remain real model decisions. Its separate cap was USD 1.00 / 384 calls; no hints,
production transcript reuse, forced actions or automatic resume. It paused on
stagnation at step 65 with 135 successful first-attempt calls, cost USD 0.288332364;
no submissions or ending occurred. The runner correctly exited 1. Receipts: `acceptance.json`, `clock-fixture.json`, and the separate
`fresh/` / `fresh-clock/` ledgers in the verification folder.

### Remaining Acceptance Limitation and Actual Production Recovery

Two explicit continuations of the first synthetic game also stopped on stagnation:
step 212 with unchanged guidance, then step 224 with the v110 test candidate.
That candidate only adds guidance during repeated waiting to distinguish spoken
promises from performed actions. It did not resolve the observed stall and was
NOT activated. Production default remains v109. Both candidates and all paid
receipts remain immutable for provenance. Do not describe these pauses as endings
or claim a full-chain pass. The game can still settle into repeated promises to
investigate unsupported extra details instead of selecting available actions or
closure; this is an open gameplay/reliability finding, not a source-permission
error or authorization to force movement, evidence, admissions or voting.

Across two fresh cases and their preserved continuation snapshots: 618 unique
provider attempts, estimated upper cost USD 1.480311444; the targeted real memory
repair adds USD 0.001420728. All tests have stopped, within their per-game caps.
There were no forced votes or hidden hints. Summary: `verification.json` and
`acceptance.json`. Final submissions, participant review and ending were not
reached by these fresh trials, so complete end-to-end acceptance remains open.

After the service update, the user independently resumed the production game.
Read-only verification confirms `watch_0632efa6_211` completed and its successful
DM request used the restored scoped background. The observed game advanced from
step 177 to 195, active at revision 238 with no background error. This is actual
recovery evidence for the reported failure, not a new production test action.
Receipt: `production-recovery.json`. The deployment preservation receipt describes
only the earlier restart boundary; subsequent user-authorized progress is expected.

## Preventive Contract Synchronization Audit: 2026-11-09 (v108)

Status: audited and reproduced locally; findings below remain open. This audit
does not modify production code, published prefixes, running games or service
configuration. All probes use generated offline fixtures, with zero provider
calls. Evidence: `.local/verification/sync-audit-20261109/report.json` and the
reproducible `probe.py` in the same folder.

| Priority | Unsynchronized boundary | Confirmed consequence / scope |
| --- | --- | --- |
| High | Active role citation instructions | The v108 investigation instruction first says reference counts are unlimited, then still says `testimony_ids` has a twelve-item cap. The validator accepts forty authorized IDs. A prepended override did not remove the contradiction. |
| High | Active-memory overflow versus snapshot repair | A role update growing ten entries to thirteen raises `scope=active_memory`. Correction version 6 requests an `entries` replacement snapshot, but the role requires `memory_update.upsert/archive/processed_through`; the suggested snapshot shape is rejected. Standalone regrouping recovery passed previously, but this role path was not covered. |
| High | Acceptance result versus process exit | With creation deliberately failing, `check_spectator` reports zero ended games and an error but still returns normally and marks the run `completed=true`. The JSON is honest; process success/completed cannot serve as a release gate. |
| Medium | Tool schema versus handler limits | `create_event_listener` omits schema maxima for description/completion/early-end text (160/400/240) and four target IDs. The handler enforces them and text overflow yields only `event tool text`. Source-read IDs also have a handler-only 200-character bound. |
| Medium | Story-authoring instructions versus validation | Room names/descriptions, persona/secret/record and relationship entries have 60/500/700/250-character bounds absent from setup instructions. A 251-character relationship is rejected as `invalid authored text`; generic retry feedback does not identify the path or actual limit. |
| Medium | Common human-input references versus uncapped interpretation/finals | Notebook, challenge and legacy flat submission inputs still cap top-level `evidence_ids` at forty, reporting an acquisition error for forty-one valid IDs. Current structured final UI sends empty top-level IDs and has no such final-source cap. The intended boundary should be stated consistently; this is not a claim that current structured final submission fails. |
| Medium | Current provider documentation versus deployed runtime | Module 14 still describes v8, a 60,000-byte request limit, two explicit attempts and no automatic retries as production behavior. Current code is v108, 51,200 dynamic / 90,000 total bytes and an initial attempt plus three retries. Historical records should remain, but these descriptions need explicit historical scope and a current contract pointer. |

Verified aligned: service PID 584824 runs from this checkout and new production
operations actually pin v108; no runtime source file is newer than its 16:56:05
startup. The latest read showed the user's game active, revision 95 / step 74,
without a background error. This audit did not resume it. All 126 published
prefix hashes match. Current tasks disable thinking, standalone memory/role
budgets are 2048/6144 tokens, the 1024-character trigger works, and current
structured final UI/guidance/validation agree on 1200/400-character fields.
Old published prefixes, legacy-runtime contracts and paid operation pinning are
intentional history, not files to overwrite to make version numbers match.

Proposed prevention, not yet implemented: define shared field/count budgets and
task-specific error contracts once; project them into new immutable prompts,
tool schemas, validators and relevant UI fields. Exercise exact boundaries and
cross-task recovery before release, including role delta versus standalone
snapshot, investigation versus concealment, human versus AI and pinned retries.
Require the acceptance gate to verify ended phase, submissions, evaluations and
ending records, with separate failed/paused/recovered outcomes. A fake-provider
test proves a contract, not natural model closure. Real whole-game receipts must
still identify budgets and manual recovery. Fixing a prompt requires publishing
a new version, never editing v108 or reconstructing paid inputs differently.

## Accumulated Citation Recovery: 2026-11-09 (v107)

Field deltas could legitimately grow a twelve-item belief citation list to
thirteen, but the older expanded-output validator still rejected it. The same
class of count limit remained in current ensemble strategies, progress,
relationships, final arguments and review. V107 removes these arbitrary source
counts while preserving authorization and request/output budgets. Explicit
reference removal remains a model decision, never silent truncation by code.

Validation failures now receive actionable feedback within the existing bounded
retry round, including when recovering pinned v106 operations. Successful paid
requests retain exact reconstruction. Legacy thinking-length recovery retains
its existing token-cap-only behavior. Transport failures record exception class
and errno without raw connection text or credentials; this improves diagnosis
and does not claim to repair provider/TLS availability.

Whole-game acceptance, including failed trials and explicit test allowances, is
recorded in [spectator mode](18-spectator-mode.md#whole-game-acceptance-and-accumulating-references-2026-11-09-v107).
V108 additionally separates pre-action disclosure sources from later event
context and distinguishes entry-count regrouping from text-only memory repair.
Final acceptance is 559 passing tests plus a recovered real 169-step game with
four submissions/reviews and ending. Deployed v108 on 2026-11-09; the linked
record preserves the failed trials, recovery limits and production hash checks.

## Event Context Regression: 2026-11-09 (v106)

V105 over-trimmed the initial review of a newly registered wait: no post-start
messages existed, while prior speech remained visible elsewhere in the DM call.
V106 restores a bounded, separately labeled creator-known background and aligns
citation validation with it. Old messages never become new arrivals. Pinned v105
source failures receive a persisted correction on a fresh retry, with paid-stage
reuse and exact historical request reconstruction. Model/output budgets and
role/memory policies are unchanged. See the [implementation and acceptance](08-time-reading-and-background-activity.md#event-background-and-citation-recovery-2026-11-09-v106).

## Scoped Context Economy: 2026-11-09 (v105)

Status: implemented, verified and deployed.

The user approved request-local DM source deduplication, per-event dirty checks,
field-level memory/reasoning deltas, stable source ordering and bounded indexes,
less premature consolidation, loop visibility, actionable/partial retries and
shorter scoped instructions. Permanent contracts stay in the immutable prefix;
phase guidance stays dynamic only while its condition holds. One-shot correction
survives retries until success. Keep all originals, authority boundaries, cues,
fixed-event ownership, 1024-character summary trigger and 2048-token generation
cap. No semantic filtering, forced movement/closure, source-count cap or review
model is authorized. New contracts are versioned; paid historical requests remain
reconstructable without rebuying calls.

The latest production game reached the existing stagnation pause at revision 142:
12 unproductive decisions, three opportunities per role. Preserve this working
protection; add scoped loop context rather than claiming an infinite scheduler
bug. Event checks must cover every pending receipt, retain prior supporting
records and commit review cursors only after successful atomic validation.
DM repairs may fill missing independent event judgments after other fields and
existing judgments validate; action changes still require a full coherent retry.
Measure deterministic request sizes separately from real provider token/cost/cache
receipts. Real tests use isolated stores, never advance the production game.

Implementation:

- DM projections reuse exact document bodies across speech and creator views,
  retaining distinct occurrence IDs, source versions and recipient authority.
- Unchanged trackers are omitted even during unrelated speech. Pending records
  are reviewed in chronological 4,000-byte chunks, always including one whole
  receipt. Partial review stays active; only a validated result advances its
  recorded cursor. Fixed workflows remain engine-owned.
- Role memory, belief and strategy updates may change individual fields and
  explicitly add/remove source IDs. Checkpoint-only acknowledgments are explicit
  and cannot skip unsupplied records. Nine short entries alone no longer trigger
  consolidation; twelve-entry, history, text and request-pressure guards remain.
- Smaller metadata indexes merge duplicate catalogs. Stable document bodies
  precede changing receipts. Acquired originals take priority over optional old
  snippets, with 6,000 bytes for normal role bodies and 12,000 at final submission,
  subject to the whole-request guard. Current receipts and scoped source tools
  preserve exact content and retrieval access.
- Scoped repeated-wait context supports autonomous decisions within the normal
  role call. It exposes no other role's private actions and adds no forced move,
  closure, semantic duplication filter or separate reminder call.
- Missing independent DM judgments can be filled by an existing bounded retry
  after all retained fields validate. The merged output is revalidated atomically;
  full raw receipts and replayable canonical results are retained. Invalid action
  choices receive the menu/tuple requirement; conflicting deltas receive specific
  correction guidance. The maximum remains three automatic retries.
- Shortened immutable role/DM/event contracts retain permanent boundaries.
  Private-chat, final-submission, timing, repeated-wait and event/speech judgment
  details enter active_guidance only while applicable. Retry feedback persists
  across failed attempts and is absent after successful completion.

The v104 trial passed nine schema/application probes, but content review found
that a 3,000-byte body allowance could omit known key originals and encourage
an incorrect claim of missing evidence. V105 restores evidence priority and
larger phase-specific allowances, explicitly distinguishes unloaded from unknown,
and reinforces complete-claim support for DM verdicts. Both paid experimental
artifacts remain immutable; v105 is the accepted default.

Final real Flash acceptance uses only fictional repository fixtures and authored
synthetic dialogue: nine cases, nine provider calls, no retries, USD 0.016487604.
This includes three old/new paired role/culprit/DM comparisons and three new
private/final-submission cases. The investigator identifies the fixture culprit
with its clock-correction and entry evidence, the culprit submits a concealment
position without forced confession, and the DM keeps an unsupported claim of
having answered as uncertain. Input tokens fall from 14,479 to 9,243 for the
investigator, 14,136 to 9,104 for the culprit and 13,716 to 7,469 for the DM.
Different cache warmth makes these token reductions unsuitable for a direct
percentage claim about billed savings. Small probes do not establish full-game
narrative quality or a universal reliability rate. The earlier v104 experiment
cost USD 0.023122656 and remains outside final acceptance.

Local-only production projections show late request bytes of 76,000 to 43,282,
75,776 to 43,153 and 78,188 to 48,596 for two role and one DM request. Dynamic
sizes are respectively 32,127 to 28,075, 32,807 to 27,739 and 34,382 to 25,649.
Early dynamic suffixes can grow because guidance moves out of the fixed prefix,
while total requests still shrink. These are deterministic serialized request
measurements, not provider usage or invoices. Automatic approval rejected sending
production game inputs to the external provider for this test; no such test ran.
The approved alternative used synthetic provider inputs and local production
size/replay checks only. No production game advanced.

Receipts: `.local/verification/context-economy-20261109/`, including
`acceptance-v105/synthetic-report.json`, `acceptance-v105/size-report.json`,
`replay-report.json` and `full-v105-tests.txt`.

Final regression passes all 541 tests in 156.318 seconds, including fifteen
dedicated economy tests covering authority, chronological checkpoints, partial
repair rejection, paid replay, final proof availability and guidance lifecycle.
Local historical reconstruction matches 1,194 request hashes across 499
operations without provider calls. All 116 pre-change artifacts remain unchanged;
all 121 published artifacts pass manifest verification.

Deployment at 15:21:45 CST on 2026-11-09 starts PID 558250 with HTTP 200. Full
before/after hashes match for all 39 games, 3,265 AI calls, 1,507 operations and
two legacy model calls. No pending work existed at restart. The latest game
remains paused at revision 142 with its stagnation reason intact; no game was
resumed and no production provider call was made. `deployment.json` records
these checks. New operations use v105; saved paid operations retain their pins.

## Bounded Summary Rewriting: 2026-11-09 (v103)

Status: implemented, verified and deployed.

The user revised the policy to trigger memory consolidation at 1,024 text
characters and require completed summaries below that threshold, while keeping
the full response capped at 2,048 tokens. Versioned standalone-summary guidance
and character metadata enforce this without truncating prose or limiting source
counts. The consolidation view omits separately stored reasoning and optional
old originals, keeping new receipts exact and originals available on demand.
Ordinary role calls retain 6,144 tokens; crossing the text trigger in an
incremental patch causes later consolidation rather than action rejection.

Truncation feedback changes the rewrite strategy without raising the token cap.
For a complete but oversized snapshot that passes source/type/progress validation,
the next existing retry receives only its texts and advisory writing allocations
under immutable memory-text-repair-v2. The model rewrites text; engineering keeps
the validated identity, kinds, citations and checkpoint and checks total length.
This is explicitly unaccepted editing material, without new source authority.
Stored paid feedback stays exact; new retries of the paused v99 task use current
correction guidance. No extra self-review call or automatic game resume occurs.
See [memory rewriting](02-memory-state-evidence.md#whole-memory-rewriting-2026-11-09-v103).
Receipts: `.local/verification/memory-rewrite-20261109/`.

The final five real long-input replays all meet the requested character/token
bounds. One passes directly and four need one automatic retry; nine calls cost
USD 0.012970092. Final text lengths are 967/817/714/766/553 and successful output
usages are 792/687/940/627/502 tokens. All original state and copied paid receipts
are preserved. Earlier unsuccessful trials remain recorded, not counted as
acceptance: this is a small regression sample, not a reliability guarantee.

All 526 regression tests pass, including 57 focused memory/context checks.
Historical reconstruction matches 1,086 request hashes across 457 operations;
all 110 pre-change prefix artifacts remain unchanged. Restart at 14:19:00 CST
(PID 541538) returns HTTP 200. Full before/after hashes match for 39 games,
3,161 AI calls, 1,466 operations and two legacy model calls. The current game
remains paused at revision 92; deployment made no production calls or progress.

## Standalone Memory Allowance: 2026-11-09 (v99)

Status: implemented, verified and deployed.

The user approved a 2,048-token cap for standalone ensemble_memory calls. Only
that task's tokens setting and explicit instruction change from v98; role
decisions retain 6,144 tokens and all other tasks are unchanged. Published v98
and earlier artifacts remain immutable, with old operations pinned to their
original allowances. Source tools, input-byte budgets, source/checkpoint checks,
disabled thinking and bounded same-cap truncation recovery are unchanged.
The cap is not an output target or a proportional cost-saving guarantee.
See the [memory module](02-memory-state-evidence.md#standalone-memory-output-cap-2026-11-09-v99).
Verification receipts: `.local/verification/memory-2048-20261109/`.

Verification passes 59 targeted regression tests and two real synthetic Flash
summaries at the new cap (USD 0.003230832 total). Historical replay matches 903
request hashes across 381 operations with 109 historical artifacts unchanged.
Restart at 12:50:15 CST (PID 520236) returns HTTP 200; full before/after table
hashes match for 38 games, 2,972 AI calls, 1,387 operations and two legacy model
calls. The latest completed game remains at revision 153, without production
model calls or rewritten results during deployment.

## Memory Output Token Budget: 2026-11-09 (v98)

Status: implemented, verified and deployed.

The [memory module](02-memory-state-evidence.md#token-budgeted-memory-2026-11-09-v98)
records the user's replacement of character ceilings with the existing 6,144-token
output budget. V99 subsequently reduces standalone consolidation to 2,048 tokens. Only
role/memory instructions and their versioned working metadata change; all other
tasks, provider settings, tools and completion caps are preserved. New contexts
remove stale character guidance and the obsolete source-count text still embedded
in ordinary role memory instructions. Published prefixes remain immutable.

Character length no longer rejects sourced entries, snapshots or the assembled
role summary, including pinned recovery. Source, identity, nonempty text, 12-entry
structure and checkpoint checks remain. New pressure scheduling uses chronological
history, entry pressure and actual request-envelope pressure, with cooldowns and
no unchanged idle rewrite. The independent input-envelope guards still apply.
A provider length stop cannot commit a partial response; the same bounded retries
carry explicit rewrite feedback without raising max_tokens. Completed stages use
their saved feedback/settings and never rebuy a paid call.

90 focused tests pass. Read-only replay accepts all eight recorded text-capacity
failures and matches 895 paid request hashes across 378 operations, preserving
108 historical prefix artifacts. Four real Flash calls against separate synthetic
fixtures pass, including both perspectives and an older pinned correction, costing
USD 0.007343256. No production transcript was sent and no production game advanced.
Receipts: `.local/verification/memory-token-budget-20261109/`.

Full regression passes 514 tests in 149.326 seconds. The service restarted at
12:31:45 CST (PID 517340), returning HTTP 200. Full row hashes match before and
after deployment for all 38 games, 2,964 AI calls, 1,385 operations and two legacy
model calls. No pending work was interrupted. The current game's revision 147
and spectator-budget pause are unchanged; deployment made no production calls.

## Unused Memory Output Fields: 2026-11-09

Status: implemented, verified and deployed.

The [memory module](02-memory-state-evidence.md#ignoring-unused-memory-fields-2026-11-09)
records the compatible parser change: required fields remain validated, unknown
annotations are unused, and complete raw responses remain in call receipts. No
prompt, task setting, model, retry allowance or published prefix was changed;
the current task version remains v97. This avoids purchasing retries merely for
unused fields, including `sources_note: null` in the reported incident.

Read-only reconstruction matched the twelve paid request hashes in both affected
operations. The extra field occurs in five failed outputs and nowhere in the
corresponding request contexts; all five outputs now validate locally. The four
consecutive failures used identical requests without field-error feedback.
The final content was instructed JSON in text mode, without a provider-enforced
output schema. There is no evidence of an input requesting this annotation.

Broader read-only replay matches 853 paid hashes across 359 completed operations,
with all 108 existing prefix artifacts preserved. The focused suite passes 68
tests. No additional model calls were made. Verification and deployment receipts:
`.local/verification/memory-extra-fields-20261109/`.

Full regression passes 505 tests. After a consistent SQLite backup and zero
pending-work check, service restart completed at 03:11:22 CST (PID 506263), with
HTTP 200. Complete before/after row hashes match for all 38 games, 2,929 AI calls,
1,366 operations and two legacy model calls. The current pause, revision, call
history and paid receipts are unchanged; no automatic retry was initiated.

The current game subsequently paused at revision 126 in `memory_C_128` of
`watch_869554a8_121` for a different condition: snapshots exceed the 950-character
text limit (the latest stored attempt has 1,019 characters). Ignoring annotations
does not waive capacity checks or automatically resume this failed operation.

## Admission Isolation: 2026-11-09 (v97)

Status: implemented, verified and deployed.

The [ending module](06-goals-and-endings.md#admission-isolation-2026-11-09-v97)
separates investigator-established truth from a supported culprit confession.
This versioned engineering change prevents confession from unlocking an
investigator's cooperation victory or changing individual assessment commentary.
Overall closure and the culprit's avoidance objective still use actual supported
case outcomes. Existing completed games and pinned v96 operations retain their
original scoring and request behavior.

V97 adds only `admission_isolation` task metadata. Model instructions and examples,
tokens, tools, Flash routing and disabled thinking are byte-equivalent as parsed
configuration. Nine existing real Flash receipts from four synthetic v96 closures
match the complete v97 request hashes and validate successfully, with zero new
provider calls. The 40-test focused suite includes source/role boundaries, a
96-combination score-invariance matrix, unchanged full investigator results and
historical scoring compatibility. Artifacts:
`.local/verification/admission-isolation-20261109/`.

Historical read-only replay matches 607 paid request hashes across 255 completed
operations and preserves all 107 pre-change prefix artifacts. No prior saved
ending is regraded or production game advanced.
The final full regression passes 498 tests, with zero additional provider cost.

Service restart completed at 02:19:18 CST on 2026-11-09 (PID 497433); HTTP returned
200 and the served ending script matches the tested file. Before/after hashes
match for all 37 games, 2,674 AI calls, 1,259 operations and two older model-call
rows. The latest game stays ended at revision 179 with its prior scores intact.
New conclusion operations use v97. Receipts: `predeploy.json` and `deployment.json`
in the verification directory above.

## Role-Specific Conclusion Assessment: 2026-11-09 (v96)

Status: implemented, verified and deployed.

The [ending module](06-goals-and-endings.md#role-specific-conclusion-assessment-2026-11-09-v96)
records separate investigator, concealment-position and voluntary-admission
assessment. Keep the generic `ensemble_theory` trace name while selecting private
instructions and contracts from the versioned prefix. A normal written culprit
position uses one 4,096-token-capped call in place of investigator grading;
investigation and admission keep their 8,192-token caps. A written abstention now
receives one stance assessment where the former no-suspect path made none. Empty
submissions still make no assessment call. No full-history or prose-review pass
is added. All roles retain Flash, disabled thinking and persisted usage/budgets.

The engine derives case-establishing submitters and objective explanations after
the independent assessments. Other final submissions' actually used originals may
support post-game comparison, but never become role knowledge or retroactive
evidence in that role's submission. The objective-scoring implementation is byte
unchanged (SHA256 `829bdd82967f9d142f99dc3f8fe481598db4b954d5ce4bd9e7427d9b18676ff3`).
New structured position-review correction feedback survives restart and manual
retry, reusing the completed investigator call and preserving historical rows.

Artifacts: `.local/verification/role-reviews-20261109/`. V95 remains immutable as
the first synthetic probe; v96 strengthens generic factual-denial reasoning and
natural role references. Each version completed four synthetic closure scenarios
using nine real Flash calls, with no provider failure or retry. V95 cost USD
0.005155488 and v96 USD 0.0041904, total USD 0.009345888 for 18 calls. These are
bounded synthetic checks, not a full-game quality or cost benchmark. No production
transcript was exported and no production game advanced by these probes.

Executed shared-renderer tests cover investigator/culprit separation, confession,
historical fallback, exact saved outcomes, HTML escaping and stable detail IDs.
The latest saved game at revision 179 also renders its historical culprit panel
without investigator grades, with zero provider calls or state mutation. Browser
access was unavailable, so desktop/mobile visual verification remains unperformed.

Final full regression passes 489 tests; the focused suite passes 46. Read-only
historical replay matches 607 request hashes across 255 operations and preserves
105 pre-change prefix artifacts, with zero provider calls. Saved completed
operations retain their original assessment contract and ordered requests.

Service restart completed at 02:12:33 CST on 2026-11-09 (PID 494954); HTTP returned
200 and the served ending JavaScript exactly matches the tested file. Before/after
row hashes match for all 37 games, 2,674 AI calls, 1,259 operations and two older
model-call rows. The latest game remains ended at revision 179 with its original
outcomes. No production call or continuation was purchased by deployment.
New conclusion operations use v96; saved conclusions receive only the historical
display adaptation. See `predeploy.json`, `deployment.json` and
`latest-ending-render.json` in the verification directory above.

## Memory Targets and Recompaction: 2026-11-09 (v94)

Status: implemented, verified and deployed.

The [memory policy](02-memory-state-evidence.md#memory-targets-and-recompaction-2026-11-09-v94)
separates an advisory six-topic / 400-550-character target from the existing
12-entry / 950-character storage limits. This removes the 699-character snapshot
rejection loop without relaxing source authority, kinds or checkpoint validation.
V94 adds whole-topic rewrite guidance and numeric entry lengths, triggers at
850 characters / nine entries, and requires new information or growth before
another capacity consolidation. Unchanged results retain a cooldown, and request
pressure allows at most one additional useful rewrite before rebuilding context.
No extra prose-review call or code-based truncation is introduced. Only role and
memory task instructions/metadata change; model, thinking and tool settings stay
unchanged. Paid historical requests and prefix files remain pinned. New unpaid
retries receive current capacity guidance, including for old operations.

Verification artifacts: `.local/verification/memory-policy-20261109/`.
Full regression passes 471 tests. The final focused suite passes 66 tests,
including one added no-benefit pressure case after full discovery (472 distinct
tests covered). Local validation accepts all eight stored failed snapshots from
the latest operation, originally 714-763 characters; no historical row is altered.
Read-only replay matches 588 request hashes across 250 operations and preserves
104 earlier prefix artifacts, with zero provider calls. Durable manual-retry
coverage reuses a paid native source stage and preserves all prior failed rows.

Four real Flash calls use an independent synthetic fixture, with no production
transcripts: v94 investigator memory shrinks from 910 to 270 characters and makes
a valid subsequent role decision; v94 concealment memory shrinks to 259; a v93
request with seeded current retry feedback shrinks to 255. Both v94 follow-up
capacity checks make zero calls. All four calls succeed, costing USD 0.007410516.
The v93 probe checks model behavior with the new feedback; durable exhausted
operation recovery is verified separately offline. This is not a whole-game
narrative or total-cost acceptance run.

Service restart completed at 01:42:20 CST on 2026-11-09 (PID 488118); HTTP returned
200. Before/after row hashes match for all 37 games, 2,663 AI calls, 1,255
operations and two older model-call rows. The latest game remains paused at
revision 173, with its explicit retry available; deployment purchases no production
call or automatic game continuation. Its failed v93 operation keeps its pinned
inputs and can use relaxed validation/current feedback on the next unpaid retry;
following new operations use v94. Receipts: `predeploy.json` and `deployment.json`
in the verification directory above.

## Bounded Working Context: 2026-11-09 (v93)

Status: implemented, verified and deployed.

Scope: role decisions and private-memory consolidation. Preserve recent supplied
observations, their source bodies, current obligations, exact acquired facts,
memory citations and all stored originals. Select older evidence bodies by actual
references, current location and recency instead of sending every original on
every call. Supply a bounded evidence directory and explicit incomplete-index
markers. Historical testimony IDs and origin indexes are request projections,
never the authorization database. A scoped paginated list_sources tool can find
older acquired records or actually received statements, and read_sources retrieves
their original text and provenance. Neither tool discovers unread documents or
another role's private information. Metadata omission is not absence of evidence.

Assemble against exact serialized bytes, including escaping, tool messages and
retry feedback, within 51,200 dynamic / 90,000 total bytes. Prefer a smaller initial
working context with headroom; reduce optional originals and index pages again on
each continuation. Preserve native call/result pairs and required recent data;
an irreducible oversized request still fails explicitly rather than silently
losing required information. No memory source-count cap or player-prose filter.

Use a new immutable task version and deterministic projections. Historical pinned
operations keep their exact request bytes and tool behavior. New operations of
existing games adopt v93 normally; deploying does not resume a paused game.
Lookup loops remain bounded, costed and durably replayable. Synthetic real-model
validation must use independent fixtures, never exported production transcripts.

Implementation uses a 6,000-byte allowance for optional original bodies, bounded
directory/origin/receipt views and a preferred 36,000 dynamic / 76,000 total byte
working target. The exact final envelope remains subject to the hard limits;
mandatory receipts can exceed the preferred target. Refit optional content after
each native batch and retry-feedback update. Directory responses are at most
4,096 serialized bytes; original reads at most 8,192, with character offsets.
Memory and role lookup each allow at most two native batches before final output.
Relation, plan and temporal-fact semantics are unchanged in this scoped change.

Verification artifacts: `.local/verification/working-context-20261109/`.
The historical failing B-role request projects from 40,342 to 34,022 dynamic
bytes (15.7% smaller); total bytes change from 78,771 to 75,651 because the new
fixed instructions/tools also occupy space. This is a local byte measurement,
not a measured reduction in whole-game provider cost. Retrieval may add calls.
Stress coverage includes 1,000 received statements, 80 acquired originals,
1,000 retained memory references, escaped/multibyte pagination, private-source
isolation, mandatory receipts, native continuations, correction feedback and
independent full-envelope pressure. Read-only replay matches 225 request hashes
across 91 historical operations and preserves 102 earlier prefix artifacts.
The first replay harness incorrectly inserted a null feedback field; correcting
the harness restored the original hashes without changing runtime or saved data.

Full discovery ran 456 tests: 451 passed and five HTTP tests were blocked by the
sandbox's local-port restriction. All five passed when rerun with local ports
available. The final focused suite passes 43 tests, including three additional
new checks, bringing distinct regression coverage to 459 tests. Paid memory-tool
recovery reuses its completed stage after restart and four failed continuations,
then accepts an explicit manual retry under its original pinned version.

Real synthetic Flash probes exercised role retrieval and memory listing/reading
followed by validated updates. The first fixture accidentally left its short
target inline, so its five calls did not establish deferred-source retrieval.
The corrected fixture made six actual calls: investigator and memory probes
retrieved the deferred original and retained its exact test value; the concealment
role chose another legal investigation action without retrieval or fabricated
knowledge. That sample establishes a valid decision, not source-tool use. Both
reports are retained; total probe cost is USD 0.02118756. No production transcript
was exported or production game advanced. These probes are not a whole-game
narrative or total-cost acceptance run.

Service restart completed at 00:18:00 CST on 2026-11-09 (PID 474374); HTTP returned
200. Before/after hashes preserve all 36 game states, 2,290 model-call rows and
1,092 operation rows. The paused game stays at revision 113. Its pending v92
operation retains its existing request and benefits from the earlier 51,200-byte
allowance; following new operations use v93. No production call was purchased.

## Dynamic Context Allowance: 2026-11-08

Status: implemented, verified and deployed.

The user increased the dynamic-context allowance from 40,000 to 51,200 UTF-8
bytes (51.2 decimal KB). This applies to serialized dynamic messages, including
JSON escaping and tool continuations. The full-request allowance remains 90,000
bytes. Both limits and the displayed error use the same gateway constants.
Historical 40,000-byte measurements below describe their original policies.

Admission is outside the immutable prompt artifacts: no new prompt version,
changed request bytes, memory rules or stored-game migration is required.
Previously paused operations can use the larger allowance on explicit retry;
deployment does not resume play or buy model calls. This raises a hard limit,
not an adaptive compaction policy; evidence and other growing context can still
reach it later.

Twenty-two focused admission, native reasoning/recovery and memory-reference
tests pass. Exact serialized dynamic sizes of 51,200 bytes pass and 51,201 fail;
both current and historical pinned task versions use the new allowance.
Read-only reconstruction of `watch_99355136_112` admits the unchanged B-role
request (40,342 dynamic bytes; 78,771 total bytes) without contacting a provider.
The service restarted at 23:51:46 CST and HTTP returned 200. Hash verification
preserved all 36 game states, 2,290 call rows and 1,092 operation rows. No game
was resumed. Receipts: `.local/verification/context-51200-20261108/`.

## Unread Reference Recovery: 2026-11-08 (v92)

Status: implemented, verified and deployed.

The paused operation `watch_99355136_80` completed its native source-lookup stage,
then all four D-role continuations cited unread `c10` in memory while choosing to
inspect it. Lookup returned unavailable; an action target does not grant acquired
source access. Existing correction identified the entry but not the offending ID.

Return precise invalid positions and disclose the exact ID only when it already
appears in this role's visible inspect menu. Retry guidance explains pre-action
memory, heard-observation citations, unavailable lookup results and subsequent
acquisition. Publish v92 role/memory guidance without changing 101 historical
prefix artifacts, count-cap removal, body budgets, model settings or retry counts.
Preserve completed tool-call receipts and leave the production game paused.

Artifacts: `.local/verification/unread-memory-20261108/`.

Old generic source feedback can be enriched by locally revalidating its saved
failed result with the pure role/memory validator before a new paid attempt.
Completed requests always retain their original recorded feedback and hashes.
Forty-eight targeted tests pass, including visible/unread versus hidden targets,
heard-claim citations, post-inspection access, snapshot feedback, bounded diagnostics,
native tool continuation, paid-stage replay after restart, and explicit v91 retry
that reuses its paid tool stage and succeeds with one new continuation call.

Read-only replay matches 155 historical request hashes over 61 completed background
operations plus the failed operation. All four failed continuations still reject
the unacquired source, now identifying c10 precisely without disclosing its body;
101 prior prefix artifacts are unchanged. The production game remains untouched.

Five independent real Flash probes passed on the first actual call: pinned-v91
investigator/concealment continuations with precise feedback, v92 continuations for
both perspectives without feedback, and a v92 memory snapshot. Native unavailable
tool history was seeded locally for those continuation probes, not purchased or
copied from production. All four roles retained supported pre-action memory and
chose to inspect the record, acquiring it only after validation; the snapshot did
not acquire or cite the unread original. Cost: USD 0.007749432, thinking disabled.
An earlier test fixture left the intended visible record hidden, correctly causing
authorization failures; the corrected fixture explicitly exposes its synthetic
record. The initial full-test log is retained separately from final verification.

Final regression: 445 tests passed in 138.921 seconds. After confirming no active
game or in-flight work, the service was backed up and restarted at 23:26:30 CST,
PID 461320, active/running. `/` and `/ensemble.js` returned HTTP 200. All 36 games,
2,220 calls and 1,062 operations retain identical row hashes. The affected game
remains paused with its original retryable operation `watch_99355136_80`; no
automatic retry, document acquisition or narrative change was applied.

## Memory Reference Policy: 2026-11-08 (v91)

Status: implemented, verified and deployed.

The user removed memory source-ID count caps. Runtime validation no longer rejects
more than eight sources per entry, thirty per active summary or twenty per snapshot.
V91 instructions and dynamic metadata expose entry/text limits and informational
source counts, with no source-count maximum. New operations no longer consolidate
solely at 24 citations. Authorization, distinct/nonempty lists, checkpoint validity,
entry/text limits, separately bounded historical-body recall, native lookup body
budgets and actual request byte admission remain enforced.

No extra model step or paid-call replacement is introduced. Old operation pins
retain their prefix, metadata and scheduling for exact recovery; relaxed source
validation also accepts their otherwise valid responses. Only unpaid retries get
refreshed correction feedback that retires obsolete source-count demands. Published
artifacts and stored feedback on completed calls remain untouched.

Verification artifacts: `.local/verification/memory-refs-20261108/`.

Forty-nine targeted tests pass, including a complete role decision retaining
120 source IDs, no count-only compaction, separate bounded historical-body recall,
source authorization, remaining entry/text/request-byte guards, obsolete-feedback
retirement, manual retry and paid-stage replay. The final role validator also
bypasses its shared helper's historical 30-ID ceiling specifically for memory;
legacy memory entrypoints receive the same relaxation. Other action contracts
retain their existing limits.

Read-only replay matches all 107 request hashes over 42 completed background
operations and the failed operation. All four originally rejected ten-source
responses now pass unchanged; 100 previously published prefix artifacts retain
their hashes. Nothing is applied to the production game by this replay.

Synthetic real-model validation exposed an independent checkpoint edge case:
an empty pending chunk was confused with recalled historical source bodies.
Persist exact permitted processing checkpoints on validation failure so retries
can correct the marker; retain the guards against rewinding or skipping records.
The initial failed probe remains recorded separately from the recovery result.

Both real Flash role probes (investigator and concealment) passed on their first
call with 36 references in the input. The snapshot's initial four calls failed
only on a recalled-record checkpoint marker; after the feedback fix, its explicit
retry failed once, received the permitted null marker, then passed. The successful
snapshot retains all 36 source IDs in a single entry; additional entries use
2/2/3/1 references. The original checkpoint and original records are unchanged.
Eight real calls in total cost USD 0.010605888, including the initial failures;
thinking remains disabled. All probes use independent synthetic records, and no
production story was exported. See `live-report.json`, `live-recovery-report.json`
and `live-acceptance.json` for the separate initial and final outcomes.

Final regression: 437 tests passed in 137.617 seconds. After confirming no active
game or in-flight model work, the service was backed up and restarted at 23:11:02
CST, PID 456636, active/running. `/` and `/ensemble.js` returned HTTP 200. All
36 games, 2,172 calls and 1,043 operations retain identical row hashes across the
restart. The affected game remains paused with the same retryable v89 operation
`watch_99355136_59`; no automatic retry or gameplay action was issued.

## Per-entry Memory Source Recovery: 2026-11-08 (v90, historical)

Status: implemented, verified and deployed.

The latest role-stage failure produced ten citations in one entry whose limit
is eight. The whole-memory limit was not the cause. Return scoped entry-local
validation feedback for invalid source lists, overflow, duplicates and unavailable
sources through the existing memory_source_capacity gate. The model corrects its
own memory; do not truncate source lists, raise limits or erase originals.

Publish v90 without changing the previous 99 prefix artifacts. Only role and
memory guidance changes; all task settings, Flash routing, disabled thinking,
completion caps and retry limits remain unchanged. Completed paid stages reuse
their stored request_feedback and request hashes, including after restart.
Existing exhausted operations remain paused for a user-controlled retry.

Artifacts: `.local/verification/memory-entry-20261108/`. Local replay reproduces
all four failures, confirms all cited sources were authorized, and matches 107
historical request hashes over 42 completed background operations plus the failed
operation. Thirty targeted tests pass, including per-entry correction in ordinary
role and snapshot calls, unknown-source protection, four-attempt exhaustion,
manual retry, old-version isolation and completed-stage replay after restart.

Five independent synthetic Flash probes also pass on their first real call:
pinned-v89 investigator and concealment decisions with explicit synthetic
correction feedback; v90 decisions for both perspectives without feedback; and
a v90 snapshot with correction feedback. All process the supplied new records
with one to three citations per resulting entry, no reasoning text, and unchanged
frozen case facts. Cost: USD 0.009116928. The old-prefix probes demonstrate response
to scoped feedback; they do not replay the user's production transcript or claim
that the paused production operation has already resumed successfully.

Full regression: 427 tests passed in 136.838 seconds. With no in-flight work, the
service was backed up and restarted at 22:48:55 CST, PID 450844, active/running;
both `/` and `/ensemble.js` returned HTTP 200. Row hashes were unchanged for all
36 games, 2,172 calls and 1,043 operations. The affected game remains paused at
its retryable operation `watch_99355136_59`, pinned to v89. No retry, game action,
history rewrite or paid-call replacement was issued during deployment.

## Wait Validity Recovery: 2026-11-08 (v89)

Publish v89 and event-protocol-v7 without editing the previous 97 artifacts.
Only role/DM event contracts change; all 29 tasks retain Flash, disabled thinking,
existing output caps, bounded retry counts and request admission limits. New
per-record allowed_statuses and wait registration boundaries are dynamic. V88
pinned recovery retains exactly its prior dynamic fields and request bytes.

EventDecisionError covers count/identity/status/text/source contract failures;
DecisionBasisError retains its existing specialized workflow correction. The
existing event feedback gate persists either bounded correction on failure and
sends it in the next attempt. Successful cached requests use their recorded
request_feedback, so retry after an interruption does not purchase or modify an
already-paid stage. The four-attempt policy and user retry control are unchanged.

Verification: 75 targeted tests pass, including nine new wait-contract tests.
New tests cover legacy compatibility with scoped support, strict pre-basis
behavior, no fixed-event completion by DM, registration boundaries, mixed-batch
ordering, bounded correction feedback and paid-reply recovery. Read-only replay
matches 65 request hashes and proves all four originally rejected DM results can
end just the waiting subscription. Three v89 real synthetic calls pass on the
first attempt, zero reasoning text, USD 0.003014424. A separate immutable v88
control completed without an API/schema error but chose to keep waiting; its
semantic immediate-end expectation failed. Total probe cost including that
control: USD 0.003737568. See live-report.json and live-acceptance.json for the
explicit distinction. No production story was exported, regraded or resumed.

Final full regression: 419 tests passed in 136.017 seconds. The idle local service
was backed up and reloaded at 22:28:26 CST, PID 446796, active/running; `/` and
`/ensemble.js` returned HTTP 200. All 36 games, 2,130 calls and 1,026 operations
retain identical row hashes across reload. The affected game remains paused with
its original retryable error and recovery operation watch_99355136_40. No retry
was issued automatically; the user can use single-step or resume to recover it.
The backup, predeploy hashes and HTTP/service receipt are retained alongside
`deployment.json` under the verification directory.

Artifacts: `.local/verification/wait-review-20261108/`; implementation details
are in [module 04](04-world-events-and-actions.md#wait-review-contract-recovery-2026-11-08-v89-implemented).

## Source, Conclusion and Workflow Integrity: 2026-11-08 (v88)

New operations use `ai-tasks-v88.json`; all 29 tasks still use Flash with thinking
disabled and no reasoning_effort. Existing output caps, 40 KB dynamic / 90 KB
request bounds, four total attempts and user-controlled manual recovery remain.
Generic mechanics live in the immutable prefix and `event-protocol-v6.txt`;
actual events, source origins, phase and computed timing stay in scoped dynamic
content. Version 86 and 87 are retained immutable verification candidates, never
deployed to the local service. No earlier prefix bytes or saved game outcomes
are edited.

The new source index covers retained memory sources and the current received
window. Temporal facts come from fixed numeric case assets, with deduplicated
origins and comparisons only between comparable intervals. No additional model
review call is introduced. Event-basis validation uses the existing retry path;
its correction and successful paid payload are stored for exact recovery.

Verification artifacts are under `.local/verification/runtime-integrity-20261108/`.
The final live report is `v88/live-report.json`; earlier candidate reports are
retained, including the v86 premature cancellation and v87 omitted-basis retry.
Tests cover exact source unions, missing/foreign sources, clock calibration,
point versus interval, 18/12/9-minute arithmetic, scoped knowledge, old cases,
actual-quorum wakeup, early private closure, absent-owner cancellation, paid DM
retry/recovery, Flash configuration and immutable prefix hashes. Human form
acceptance uses real local HTTP at widths 1440 and 390; drafts and selected
sources survive re-render, submitted citation unions are exact and no page
errors or horizontal overflow occurred. Historical read-only replay matches
220 request hashes across 103 background operations, with identical results,
submissions, known evidence and frozen case.

A separate local-only migration admission audit checked the next role/compaction
request in 98 historical decision states against v88: no admission failures,
maximum dynamic content 34,788 bytes and total request 71,209 bytes. This audit
made no provider calls and wrote no production game data; it checks these
representative states, not an unrestricted future-context size guarantee.


Final regression: 410 tests passed in 136.036 seconds; 37 targeted tests also passed.

Final v88 synthetic provider acceptance: five scenarios, seven calls, all completed
on the first attempt, zero reasoning text, estimated USD 0.004441464. Compaction
kept the invented unsigned-field claim attributed to its speaker and distinct
from the original document. A first vote left the custom wait active. A role
submitted all three dimensions with an exact engine-derived citation union.
An acquired verified audio comparison supported the new recording proof route
without its raw-audio precursor; the well-formed, semantically grounded argument
was established. A second argument that called an 18-minute custody interval
nine minutes retained source coverage but failed semantic time support. Both
ending paths executed through the real model. Earlier development probes cost
USD 0.022668780; they are retained as failures/iterations, not reported as final
acceptance. These are bounded feature probes, not a full-play win-rate study or
a guarantee that a model never misattributes or misinterprets a fact.

Deployment: the idle local service was reloaded at 21:51:48 CST on 2026-11-08,
PID 440630, active/running. `/` and `/ensemble.js` returned HTTP 200. A full
SQLite backup precedes reload; row hashes confirm all 35 games, 2,063 AI call
records and 998 operation records are unchanged. The prior latest spectator
case remains ended without a background error. `deployment.json` and
`predeploy.sqlite3` retain the receipt and backup. New cases get numeric temporal
assets and the new proof structure; old frozen cases are not backfilled or
regraded. New operations receive v88 contexts while existing pins remain intact.

## Disable Thinking on User Request: 2026-11-08

Status: v85 implemented, verified and deployed locally.

The user's latest direction disables thinking before auditing the newest
spectator game. Publish v85 with `thinking:{type:"disabled"}` and no
`reasoning_effort` for all 29 tasks. Keep Flash, instructions, tool/response
contracts, completion caps, source boundaries and the four-attempt recovery
policy unchanged. No published version is edited. Existing operation pins and
paid requests remain reconstructable with their original thinking settings;
new operations, including later steps in an existing game, use v85.

The latest game was already ended and there was no in-flight model work at
inspection. Verify non-thinking payloads, native-tool continuation and historical
recovery offline, run bounded synthetic real-provider checks, and restart only
an idle service after backing up and checking stored records. Then audit the
latest saved game's decisions and conclusion without rerunning it.
Artifacts: `.local/verification/thinking-disabled-20261108/`.

Verification: 24 targeted tests and all 393 regression tests passed (full suite
132.937 seconds). All 29 new task payloads, including the concealment role
variant, differ from v84 only by disabling thinking and removing reasoning
effort. Native-tool continuation succeeds; old thinking-enabled paid-stage
recovery retains its pinned contract. Read-only replay matched 220 request
hashes across 103 completed background operations of the latest game, reproduced
its final results exactly, and preserved all 91 prior published prefix artifacts.

Four real Flash requests exercised memory compaction, the following role
decision, final assessment and ending narration. All completed without retries,
with zero reported reasoning tokens and no returned reasoning text. Synthetic
memory retained its originals and advanced checkpoint 40 with four entries,
148 text characters and five sources. Total logged test cost: USD 0.00504288.
These checks establish configuration and protocol behavior, not future gameplay
quality or a controlled cost comparison with the historical thinking run.

After backup, the idle service restarted at 21:02:44 CST on 2026-11-08. HTTP
and the ensemble script returned 200; every stored row and column across 35
games, 2,063 calls and 998 operations remained unchanged. The latest game remains
ended with no background error. Its separate read-only findings are recorded in
[Complete playable runtime](17-complete-playable-runtime.md#latest-spectator-audit-2026-11-08).

## Final Assessment Thinking Allowance: 2026-11-08

Status: v84 implemented, verified and deployed locally.

The latest spectator game completed automatically on v83, but its final
assessment incurred eight length-truncated responses before three successful
reviews. Every truncated response used its whole completion allowance for
reasoning and emitted no final answer. The initial 2,624-token ensemble theory
allowance was not covered by the earlier memory/role adjustment. Two responses
also exhausted the bounded 8,192-token retry cap, so raising the initial cap
alone cannot guarantee successful completion.

Publish v84 without changing prior artifacts or pinned operations. Both
`case_theory` and `ensemble_theory` start at 8,192 tokens and receive concise
guidance to assess the submitted identity/time/method argument against its
supplied sources, report material gaps and contradictions, and finish the
required JSON instead of repeatedly trying hypothetical repairs. Preserve every
existing grading requirement, response schema, source permission, proof-route
check and role perspective. This is guidance, not a hard reasoning-token cap.
The three ending tasks start at 4,096 tokens with their existing narration and
perspective rules; they remain grounded in already adjudicated outcomes.

Keep Flash, thinking enabled at low effort, the 8,192-token retry ceiling,
four attempts per recovery round, all dollar/call admission checks and full
response accounting. Failed thinking is still billable. No disabled-thinking
fallback, fabricated review or extra self-review call is introduced. Existing
completed games and paid receipts remain unchanged; new operations use v84.

Verify new contracts and atomic conclusion recovery offline, reconstruct the
latest completed v83 operation locally with exact historical request hashes,
and use independent synthetic inputs for real-provider grading/narration probes.
Do not export production stories or automatically rerun the completed game.
Artifacts: `.local/verification/conclusion-thinking-20261108/`.

Verification: 27 targeted tests passed, including four new closure-contract,
atomic failure/recovery, old-pin paid-stage reuse and grading-boundary cases.
Full regression passed 391 tests in 129.710 seconds. Local read-only replay
matched all 203 recorded request hashes across 81 completed background operations
and reproduced the final results, ending, submissions, acquired records and case
exactly. All 90 previously published prefix artifacts retained their hashes.

Ten real Flash-low requests completed on their first attempt with no truncation
or schema failure, costing USD 0.032463684. Four synthetic ensemble scenarios
each exercised assessment and ending: mixed originals/copies and supported
voluntary admission established the case; incorrect death timing and missing
evidence remained unproven. Two additional single-player assessment probes
preserved exact submitted quotes and rejected the incorrect time claim. The
largest observed reasoning use was 5,418 tokens; its complete answer used 6,033
completion tokens. These are independent synthetic probes, not a replay of the
production story or a guarantee against stochastic future truncation. An early
case-probe harness run stopped at local command-ID validation before any provider
request; its empty ledger is retained separately from the ten real-call receipts.

After a SQLite backup, the service restarted at 19:53:40 CST on 2026-11-08.
HTTP and the ensemble script returned 200. All rows and columns of 34 games,
1,840 calls and 893 operations remained unchanged. The latest production game
was already ended and remains ended with no background error; deployment did
not make a production model call or rerun its conclusion. New operations use
v84; existing operation pins remain unchanged.

## Thinking Tool Continuation Admission: 2026-11-08

Status: runtime fix implemented, verified and deployed locally; published
prefixes remain unchanged at v83.

The current game stopped before `role_D_continuation_1` in
`watch_536c0967_77`. The paid first role response was a valid native
`create_event_listener` call. Its reasoning adds 14,442 serialized UTF-8 bytes
to the continuation: the dynamic message list totals 42,314 bytes and the
complete request totals 73,048 bytes. The shared 40 KB dynamic check includes
provider-generated reasoning, so it rejects this otherwise bounded continuation
before contacting the model. This is separate from v83 output truncation recovery.

Keep the 40,000-byte bound on dynamic game inputs, assistant content/tool call
arguments and tool result messages. Exclude only the top-level string
`reasoning_content` of native assistant tool-call messages in a thinking-enabled
request from that sub-budget. The complete unchanged request, including every
reasoning byte, remains bounded at 90,000 bytes and subject to cost admission.
User text and tool-result text do not gain an exemption by using similar names.
Preserve the exact request, source permissions, tool limits and published prefix
versions. This is an admission accounting change, not a context rewrite or an
increase in the full-request limit. The existing paid role call must be reused
when the user retries; no role action or listener is committed twice.

Verification artifacts: `.local/verification/tool-reasoning-admission-20261108/`.
Twenty targeted tests passed, including six new boundary/recovery tests. They
cover intact reasoning roundtrip, full-envelope and dollar metering, game/tool
data enforcement, named-field spoofing, unchanged non-thinking behavior, and
pause/restart recovery after a paid native call with exactly one listener.
The local read-only replay matched all 151 recorded request hashes across 62
background operations. The blocked continuation is now admitted with 27,851
dynamic-game bytes, 14,442 reasoning bytes and 73,048 total request bytes; native
assistant/tool messages remain intact. Its cost reservation is USD 0.0294792,
within the then-remaining USD 0.096179368 and 103-call allowance.
No additional paid verification call is needed: serialized provider requests,
prompts and execution semantics are unchanged. Production remains paused until
the user explicitly retries.

Full regression passed 387 tests in 131.561 seconds. After a SQLite backup, the
service restarted at 19:22:22 CST on 2026-11-08. HTTP and the ensemble script
returned 200. All columns and rows of 34 games, 1,788 calls and 874 operations
remained unchanged. The affected game remains paused on `watch_536c0967_77`
with manual retry enabled and no in-flight work; deployment made no production
model call and did not advance gameplay.

## Thinking Truncation Recovery: 2026-11-08

Status: implemented, verified and deployed locally in v83.

The latest v82 spectator run paused at `memory_C_40`: four responses ended with
`finish_reason:length`, all 2,424 completion tokens spent on reasoning and zero
final-answer characters. `memory_B_37` also truncated three times before its
fourth attempt succeeded; two role attempts hit their cap as well. This is an
output-allowance failure introduced by enabling thinking, not malformed memory
citations, lost observations or an input-context overflow.

Publish v83 with 6,144 total completion tokens for the three memory tasks and
the ensemble role task, keeping Flash and low effort. Preserve all prior prefix
bytes and pinned operations. For a genuine length-truncated thinking response,
the next permitted retry doubles the preceding cap up to 8,192 tokens. Persist
the applied override in each call receipt, include it in request/prefix hashes
and cost reservation, and restore it exactly when reusing a completed stage.
Ordinary schema errors and non-thinking calls do not increase the cap. A timeout
after a raised-cap attempt retains that allowance without increasing it again.
Keep four attempts per user-authorized round, the existing dollar/call limits,
atomic memory replacement, source authorization and checkpoint validation.

The affected production game stays paused. Verify historical requests locally
without exporting player data, use independent synthetic data for paid probes,
and let the user initiate the next retry after deployment.

Verification artifacts: `.local/verification/thinking-truncation-20261108/`.
The 27 targeted tests passed, including nine new cases for bounded growth,
non-thinking/schema errors, exact paid-stage recovery, old exhausted operations,
timeout continuation and increased dollar reservation. Read-only replay matched
all 97 requests across 41 completed/failed background steps in the affected game
and preserved all 89 previously published artifacts. Its next authorized retry
retains v82 and identical messages, with a 4,848-token allowance. At the audit,
USD 0.096364964 and 157 calls remained; this retry reserved USD 0.0130281.

Three real synthetic Flash-low calls passed: v83 memory compression, a subsequent
role decision and recovery of an old v82 memory stage. The latter uses four
explicitly synthetic legacy failure receipts, followed by one real model call
at the recovered allowance; it is not a production game replay. Both memory
cases start with 40 observations, checkpoint 36, eight entries, 757 text characters
and 22 sources. They finish at checkpoint 40 with four entries, respectively
124/139 text characters and 6/5 sources. Original observations, evidence and
fixed story remain unchanged. Estimated real-call cost: USD 0.006273744.
These results verify the protocol and recovery; the actual paused step is left
for the user's next explicit retry.

Full regression passed 381 tests in 131.118 seconds, including HTTP and all
historical recovery tests. The service was backed up and restarted at 19:00:31
CST on 2026-11-08. HTTP and the ensemble script returned 200. Existing-column
hashes for all 34 games, 1,734 calls and 853 operations remained unchanged. The
new nullable `request_settings` column is empty for historical calls. The latest
game remains paused on `watch_536c0967_50`, with manual retry enabled and no
in-flight work; no production model call or gameplay step ran during deployment.

## Minimum Thinking Effort: 2026-11-08

Status: implemented, verified and deployed locally in v82.

The user requested the lowest enabled thinking tier while retaining Flash.
The current [official thinking guide](https://api-docs.deepseek.com/guides/thinking_mode/)
documents `low` as the lowest tier (`minimal` maps to the same tier). New v82
task definitions explicitly send `thinking:{type:"enabled"}` and
`reasoning_effort:"low"`. All 29 versioned task definitions inherit the current
Flash model. Existing operations retain their immutable versions; the original
standalone demo review adapter retains its published non-thinking contract.

Thinking and final output share a completion allowance. Ordinary tasks receive
1,024 additional maximum completion tokens above their existing caps. The three
initialization tasks have an 8,192-token total cap after a real 4,024-token probe
exhausted its entire allowance on reasoning without a final answer. This stays
below the provider's much larger thinking default. This is headroom, not a hard
reasoning-only cap or a promise about actual consumption. Existing dollar/call
budgets and full-response accounting remain enforced. The transport allows at
least 90 seconds for enabled thinking; non-thinking timeout behavior is retained.
The provider ignores temperature in thinking mode; stored task temperature values
are not an effective sampling control for these new calls.

Native tool continuations must preserve the returned `reasoning_content` along
with assistant/tool messages. The existing decoder and continuation path already
do so; deterministic and real continuation checks passed. Reasoning remains in server-side
call receipts and necessary same-decision continuations, not player speech,
another role's context or long-term character memory.

Verification artifacts are under `.local/verification/low-thinking-20261108/`:

- The first v80 real probe found that a role appended `next_observation` to a new
  custom listener wait, conflicting with the existing exact-list validator.
  V81 adds generic guidance to both role perspectives: wait for exactly the new
  custom listener receipts, or continue acting while they are tracked. Direct
  contact and timeout still interrupt the wait. No engine wait rule changed.
- V81 passed real short-output, role, tool-continuation and DM checks. Its setup
  exhausted the 4,024-token cap on reasoning on four attempts. V82 raises only
  the three initialization caps to 8,192; previous published artifacts remain
  unchanged, including the unsuccessful verification versions.
- The final v82 synthetic run completed all six calls on the first attempt:
  opening, world, role, native continuation, DM and generated setup. All initial
  calls returned reasoning; the actual tool message's reasoning was carried
  into the continuation. Setup completed in 30.960 seconds; the other calls
  took 1.912–4.832 seconds. Recorded estimated cost was USD 0.008613516. Earlier
  v80/v81 probes cost USD 0.006583764 and USD 0.025699632 including failures;
  these are test costs, not a per-game forecast or a provider invoice.
- Full root-level regression passed 372 tests in 129.807 seconds on the v81
  implementation. The final v82 cap-only revision separately passed all three
  thinking-configuration tests, covering all 29 tasks, both role perspectives,
  old contracts, manifest hashes, reasoning isolation/roundtrip and timeout.
  The earlier sandbox-only run had five HTTP binding permission failures;
  the complete permitted run includes those HTTP tests.

This verifies API and runtime compatibility, not a complete thinking-mode game
or improved deduction quality. Real tests use generated fixtures and a separate
database; no saved player scenario is sent to the provider.

The local service was restarted at 18:22:58 CST on 2026-11-08 after an idle-work
check and SQLite backup. HTTP and the ensemble script returned 200. All 32 game
states, 1,634 call records and 809 operation records retained identical hashes.
The existing paused game remains paused on its prior `context_budget` error;
enabling thinking neither resolves that separate limit nor resumes gameplay.
New operations use v82; recovery of existing operations retains its pinned
version and thinking settings. See `deployment.json` for the service receipt.

## Approved Cost Optimization Design: 2026-11-07

This is the implementation plan confirmed by the user, followed by engineering
boundary recommendations. It is not a report that the changes have shipped.
The user requested documentation before development and subsequently specified
three automatic retries before a Web error offers a manual retry decision.
Keep the existing real Flash role and DM responsibilities, optional use of heard
speech, independent conclusions, and event-driven waiting behavior.

### Evidence and Scope

The local production audit covered four substantial spectator runs: 931 provider
attempts, including failures, and 919 gameplay requests reconstructed with hashes
matching their persisted requests. No provider calls or game writes were needed.

| Story | Status | Calls | Mean role input tokens | Logged estimated USD |
| --- | --- | ---: | ---: | ---: |
| 山寺义庄的未了愿 | Ended | 214 | 10,786 | 0.418241 |
| 空厅里的最后一排 | Ended | 196 | 9,018 | 0.323299 |
| 旧同学会 | Paused reunion | 297 | 6,897 | 0.387347 |
| 合唱团里多出来的人 | Ended | 224 | 7,838 | 0.335620 |

The latest completed run used v61; there was no complete v62 production run in
this audit. These different stories and versions are not a controlled A/B test.
Costs use the recorded `deepseek-usd-2026-11-04-peak-upper` rate card, not a
provider invoice or a newly verified price quote.

In the latest run, role decisions account for 72.74% of estimated cost and DM
calls for 26.00%. Uncached input accounts for 72.76%, output for 25.64%, and cached
input for 1.60%. Role dynamic input averages 22,985 UTF-8 bytes; recalled sources,
recent observations and acquired evidence together account for about 49% of its
field-value bytes. DM dynamic input averages 10,097 bytes and includes full
speaker evidence and recent observation snapshots. These byte proportions are
not separately metered token proportions. Twenty-nine presentations created no
new evidence acquisition; associated operations cost USD 0.122074, but their
speech may still have argumentative value, so that amount is not proven waste.

Local reproducibility artifacts: [audit script](../.local/verification/context-cost-20261107/audit.py)
and [numeric report](../.local/verification/context-cost-20261107/report.json).
These local artifacts may not accompany another checkout; the summary above
retains the audit scope and limitations without publishing private transcripts.

### 1. Deduplicate Authorized Context

Build a request-local source table containing each supplied source body once.
Recent observations, recalled references, memory, reasoning and relationship
experiences refer to those entries instead of embedding the same body again.
Keep evidence content separate from each role's acquisition receipt. Apply the
same normalization to DM speaker snapshots and recent-event packages.

Identity is based on the original record and acquired snapshot, not matching
words. Different speakers, observation times, document versions or provenance
remain distinct even when their text matches. A copied source body may be shared
inside one authorized request while its distinct acquisition metadata remains.
Original speech, documents and chronological history stay stored unchanged.

Initially retain every currently acquired evidence body and the existing recent
and recalled selection. Validate lossless reference resolution before reducing
which older utterances are sent. A subsequent bounded lookup path can retain
source indices and automatically include current obligations and explicitly
cited reasoning sources, with other actually heard originals available on demand.
Do not choose material using the hidden solution or treat summaries as evidence.
Unknown or unauthorized references must not reveal whether hidden data exists.

The DM still needs fixed truth, speaker knowledge at the utterance, relevant
observations, and scoped event conditions. Do not remove these merely because a
speaker omitted a citation or has an empty private deduction. The first change
deduplicates that material rather than using keyword rules to judge relevance.
Deception assessment, semantic event decisions and microexpressions remain DM
responsibilities; no extra relevance-classifier or self-review call is added.

### 2. Compact Action Menus

Put generic action definitions and argument shapes in the stable task prefix.
Dynamic input supplies only currently legal targets, argument combinations,
necessary costs/durations and scoped status. Entity names and document titles
resolve through the authorized entity/source tables, with no repeated prose per
action-target pair. Preserve usable names even for a visible, unread object.

The role returns a supported action and arguments in the same decision response.
Map that response to the existing handlers and revalidate against current world
state at execution and timed completion where required. Do not turn independent
target lists into permission for every Cartesian combination: a transfer must
retain the legal item/recipient pairs. Cover all existing scenario choices,
including cancellation, invitations, event waits and final submission.
Menu compression does not remove otherwise legal actions or change human agency.

### 3. Incremental Memory, Reasoning and Relationship Updates

Allow an explicit unchanged result, such as `memory_update: null`, instead of
requiring a rewritten summary on every decision. Changed summaries and beliefs
carry updated source references; relationships emit only actual updates.
Concealment roles update private strategy rather than a culprit hypothesis.
Use distinct operations for unchanged, replacement and clearing an interpretation;
none can erase fixed personal knowledge, acquired evidence or original history.

Apply updates atomically against the request's state revision. Evidence sources
must belong to that role, and heard claims retain attribution and uncertainty.
Reading a message and retaining it in a summary are separate bookkeeping facts:
an unchanged memory result cannot silently advance the summarization checkpoint
past new unprocessed observations. Preserve outstanding observations until a
bounded memory update has processed them. Reuse the existing compaction path
where necessary and measure whether unchanged outputs increase those calls.
Do not create a new per-turn summarizer or infer a human's private intentions.

### 4. Stable Request Ordering

Use this order in new request versions: generic instructions and action/tool
definitions; immutable authorized baseline; stable acquired source bodies;
current interpretations and relationships; new observations, wake reason and
executable state. Keep stable acquired entries in deterministic append order.
Frequently changing acquisition/display counters must not be embedded inside
otherwise stable source bodies. Acquired sources are still dynamic material
after the frozen baseline, not edits to that baseline.

Define ordering in the new payload assembler without changing global
`storage.canonical`, existing fingerprints or published prefixes. Preserve old
operation versions and exact replay inputs. Include all required material in
each request; a provider cache is neither authorization nor persistent model
memory. Do not share private role material across scopes to increase hit counts.
Cache benefits remain a measurement question, with no guaranteed lifetime or
savings percentage and no extra calls just to keep a cache warm.

### 5. Objective Action Feedback and Model-Controlled Repetition

Extend scoped feedback across the runtime's supported structured actions. Code
records who acted, what target and parameters were used, actual lifecycle and
outcome, and who received which observation. The role model decides whether
repetition is worthwhile from those details; humans retain their own choices.
Do not introduce a repetition ban, a forced alternative action, a forced ending,
or a code-generated judgment that speech is pointless.

Every new real execution appends its occurrences. Derived feedback updates the
observable count, most recent execution, execution status, recipient history and
available outcome details. Old history remains intact. A pending request is not
success, and cancellation does not erase effects already committed. Rejected
requests and network retries do not fabricate in-world actions.

| Supported family | Objective feedback | Interpretation retained by the model |
| --- | --- | --- |
| Inspect and search | Actual checks, activity completion, received discoveries, last observed area state | Whether another search is worthwhile; whether evidence is sufficient |
| Move and follow | Observed start/destination and actual following result | Motive or usefulness of returning |
| Present, give, take, place, copy and protect | Executed operation, observed custody/condition and delivery receipts | Whether a recipient believes or understands the material |
| Timed handling and scenario actions | Start, actual effects, completion, cancellation or failure supported by the handler | Whether another attempt advances the character's goal |
| Speech, questions and private conversations | Utterance identity, actual recipients, directed replies and explicit session lifecycle | Whether an answer resolves a question, or an argument repeats a claim |
| Event listeners and waiting | Registered targets, actual notifications and lifecycle transitions | Custom semantic conditions, interpreted by the scoped DM |
| Closure votes and conclusions | Actual vote/submission receipts under existing rules | Whether to end, accuse, defend or continue investigating |

Use only that role's own actions and received observations. For example, a
presentation observed by A may establish that B received the document, while
B's separate private acquisition cannot be exposed to A. Missing receipt means
unknown, not not-received. Delivery does not establish comprehension or truth.
A statement such as "I showed B the letter" remains testimony until a real
presentation occurrence establishes the action. Arbitrary unsupported physical
actions are not made executable by this feedback feature.

### Automatic Retries and Web Recovery: Additional Confirmed Requirement

The user specified three retry opportunities before asking for a Web decision.
Interpret this as one initial provider attempt plus at most three automatic
retries: four attempts total in the initial recovery round. After a retryable
failure exhausts that allowance, stop automatic work for the affected operation
and show its error in the Web interface. Do not automatically start another round.
The user can request another retry or leave/cancel the pending work under the
existing control permissions. Apply the policy consistently to playable and
spectator flows, including setup, role, DM, memory, tool continuation and ending
stages; do not retry an entire multi-stage operation unnecessarily.

Recommended execution details, to implement and verify with that requirement:

- Retry transport failures, timeouts, transient provider/rate-limit failures and
  invalid model outputs under one bounded gateway policy. Use bounded backoff,
  honoring provider delay guidance within the operation deadline. Do not multiply
  the allowance with an independent adapter retry loop.
- Do not retry pauses, cancellation, exhausted money/call budgets, stale state,
  authorization/configuration errors or a locally oversized context as if they
  were transient model failures. Explain the applicable control or blocker.
- Retry the same pinned stage and authorized base state. Transport retries keep
  the same request hash. V75 memory-capacity corrections may add persisted,
  numeric validation feedback to dynamic input, producing a distinct auditable
  request hash without changing the game context or prefix. Reuse
  completed stages and native-tool receipts, and never repeat their world effects.
  Recheck cancellation, ownership and revision before reserving an attempt or
  committing a result. A changed context requires an explicit new operation.
- Keep each attempt, error, measured/unknown usage and reservation in the ledger.
  Count every actual provider attempt toward the game call and monetary budgets.
  A timeout can be billable; unknown usage must not be treated as zero cost.
- Persist recovery round and attempt progress. Restarting the process or polling
  a page must not reset the allowance. A manual retry is an explicit, idempotent
  user command; recommended behavior starts one new bounded round with the same
  maximum of one requested attempt and three automatic retries, budget permitting.
- During automatic recovery, show stable progress such as "retrying 2/3" without
  a blocking error panel or changing list scroll position. Exhaustion shows a
  user-readable error, attempts made, and an explicit retry control. Detailed
  logs retain all failures; Web messages do not expose credentials or hidden role
  material. Multiplayer recovery uses the existing host/control authority.

Implemented in the shared gateway: four attempts per stage per recovery round,
with persisted round starts and completed-stage reuse. Explicit manual recovery
opens another bounded round; polling and process restart do not renew it.

### Boundary Review and Recommended Defaults

The five directions and the three-retry/Web decision rule above are confirmed.
The following details are engineering recommendations; numerical tuning values
are proposals for measurement, not already agreed or shipped behavior.

| Boundary | Recommended rule |
| --- | --- |
| Source identity | Deduplicate the same acquired source, not identical wording or allegedly equivalent proof. Keep versions, speakers and receipt metadata. |
| Read limits | Begin with at most one historical-source lookup batch per role decision, up to 8 source IDs and 8 KiB of returned source bodies. Oversized originals need explicit ranges and continuation metadata; never represent an excerpt as a complete source. |
| Tool coexistence | Source lookup and event-listener creation share a finite continuation budget. Initial proposal: at most one batch of each, two continuations total, followed by a final decision; no recursive lookup loop. Charge every continuation. |
| Missing context and budget | Prioritize unprocessed observations, direct obligations and explicitly cited sources. Retain existing total context/call/money guards; if necessary context cannot fit, return a clear operational limit rather than silently discard it or fabricate an answer. |
| Retention | Prompt selection never deletes stored history. Completed role summaries may be lossy, but source references and original evidence remain retrievable in the authorized scope. |
| Comparable actions | Group by actor, supported action, target and relevant parameters/scope. Distinguish a repeated target from a new observed state; never label an unseen state change as "changed" or "unchanged" for the role. |
| Counts and idempotency | Count actual executions once. Separate attempts, completed outcomes and failures where recorded. Lifecycle transitions and technical retries do not increase the count of independent executions. |
| Snapshot timing | Assess a speech using the speaker's knowledge when it occurred, not discoveries obtained afterward. Keep cached source bodies separate from evolving custody and delivery state. |
| Dialogue interpretation | Link actual directed replies mechanically, but leave "answered adequately", semantic repetition, truth and usefulness to the model. No keyword or string-similarity classifier replaces that judgment. |
| Input authority | Retrieved statements are quoted game data, not new system instructions. Keeping an original available does not grant its speaker control over another role, DM or runtime tools. |
| Feedback size | Start with counts, latest status and a bounded recent detail window; proposal: at most 3 recent execution receipts per comparable action and 6 KiB total feedback, excluding required current obligations. Do not expand every historical receipt into every menu option. |
| Feedback limits | Keep mandatory active work, pending requests and unread result notifications. Explicitly identify omitted older detail and its scoped references; if required entries exceed the limit, use the operational budget path rather than dropping them. |
| Legacy saves | Derive only what existing receipts establish. Missing audience/status metadata stays unknown. No invented historical results, private-knowledge backfill or rewrite of pinned request inputs. |
| Repeated failures | Manual retry can start another bounded round but cannot bypass permissions, pause/cancel, state consistency, budget admission or an already committed result. No automatic infinite recovery. |

### Delivery Order and Acceptance

Implement and measure in this order: lossless context deduplication, compact
menus, incremental updates, stable ordering, and action feedback. Add historical
lookup only after the lossless stage passes; measure its extra calls separately.
The retry policy is a distinct recovery change and must be validated before
using automatic retries in cost comparisons. Version all request/response shape
changes without rewriting published artifacts or already pinned operations.

| Area | Required verification |
| --- | --- |
| Source integrity | Every included reference resolves; same-text/different-source records stay distinct; unauthorized IDs reveal no hidden content; heard claims never become acquired physical records. |
| Role and DM isolation | Unseen private acquisitions do not change another role's feedback; DM deduplication preserves truth versus speaker belief and utterance-time knowledge. |
| Menu equivalence | All formerly legal action/argument combinations remain representable; unauthorized combinations and stale-state actions still fail; scenario costs, durations and targets survive compression. |
| Incremental updates | Unchanged, replace and clear are distinct; sources remain valid; pending observations survive unchanged summaries; replay does not apply relationship changes twice. |
| Receipts | Repeat execution updates feedback once, while retrying the same command does not; changed audiences, re-visits, cancellations, partial effects and old incomplete receipts retain correct meaning. |
| Retry recovery | Success on the initial or fourth attempt, four failures followed by a Web decision, manual retry success, duplicate clicks, reload/restart, exhausted budget, cancellation during backoff and completed-tool replay all behave as specified. |
| Compatibility | Old pinned request hashes and outcomes are reproducible; new contexts are deterministic for the same snapshot; no new model fallback or prose-filtering path appears. |
| User interface | New retry/progress states remain readable without scroll jumps; controls remain disabled while the same attempt is pending; only authorized users can retry or cancel. |
| Real usage and play | Measure provider hit/miss input, output, retries, lookup calls, latency, compaction frequency and whole-game cost. Compare matched starting cases, inspect missed clues, evidence attribution, repeated actions and final arguments. |

Set performance targets from measured candidates rather than claiming a fixed
saving now. Reduced prompt bytes, stable hashes, synthetic probes and completed
real playthroughs are different evidence levels. A higher cache ratio or shorter
game alone does not establish better cost per meaningful investigation.

Implementation touchpoints: `palter/ensemble_context.py`, `ensemble_world.py`,
`ensemble.py`, `evidence_sharing.py`, `exploration.py`, `event_tools.py`,
`ai_gateway.py`, versioned prefix files, and the playable/spectator Web views.
Implementation and verification records follow. Proposed numerical limits above
are superseded by the measured implementation limits where stated below.

## Current Runtime: 2026-11-08

### Memory source pressure fix: 2026-11-08

Status: implemented, verified and deployed. The latest completed v73
spectator run rejected the same final role patch seven times: 25 active source
IDs became 31, exceeding the existing limit of 30. Entry/text pressure did not
trigger consolidation, source capacity was absent from the role context, and
retries received no capacity feedback.

New v75 operations expose the existing 30-source and 8-per-entry limits,
used/remaining source capacity and explicit snapshot limits. Consolidation also
runs at 24 distinct active sources and must return at most 20, leaving room
for subsequent incremental updates without immediately retriggering compaction.
These thresholds supplement the existing pending-observation, entry and text
checks. The model selects supported representative citations and merges topics;
engineering does not trim prose, invent citations or delete original history.

Capacity-validation errors carry bounded, structured counts and limits for
the same role and stage on subsequent v75 retries. The feedback is persisted so
restart/manual retry and completed-stage replay reconstruct the actual request.
The ledger stores this correction in `ai_calls.validation_feedback`. It contains
counts, limits and an active-memory/snapshot scope, without source text or IDs.
Only dynamic retry input may change; baseline, prefix, authorized game snapshot,
stage effects and the four-attempt recovery policy remain unchanged. Old pinned
requests retain their previous payloads and compaction behavior. No new retry
round, polling task, model fallback or automatic production-game resume is added.

Offline read-only replay reproduced all seven 31-source failures and the eighth
30-source success; the new source trigger catches the original 25-source base
before its role decision. A synthetic real Flash probe consolidated 8 entries /
320 text characters / 25 sources into 5 entries / 10 sources, then completed a
normal role decision with 16 active sources. Its own false account remained a
`self_claim`, contradictions and attribution survived, originals stayed unchanged
and a second idle pressure check made no call. Two calls, no retries, 11,799 input
tokens (1,664 cache hits), 765 output tokens, USD 0.003968484. This bounded probe
does not establish whole-game cost or narrative quality. Evidence is under
`.local/verification/memory-source-capacity-20261108/`.

Verification: all 315 Python tests passed in 124.594 seconds, including 13 new
source-pressure and recovery tests. They cover the 25-to-31 incident shape,
24-source trigger boundary, 20-source snapshot headroom, duplicate citations,
chunk/checkpoint and authorization guards, atomic failures, preserved originals
and archives, version-specific payloads, corrected-stage replay after restart,
four-attempt exhaustion and explicit manual recovery. All 80 previously published
prefix artifacts retain their original bytes. The first test-discovery invocation
used the wrong top-level path and failed to import the HTTP module; the complete
root-level discovery above passed, including HTTP tests.

The local service was restarted at 16:47:47 CST on 2026-11-08 after an idle-work
check and SQLite backup. HTTP returned 200, and all 30 game states, 1,464 call
records and 724 operation records retained identical existing-column hashes.
The new nullable feedback column was added with no historical feedback fabricated.
No production game was resumed or retrospectively regraded.

New operations use ai-tasks-v83.json with shared `event-protocol-v4.txt`.
V83 retains lowest-effort thinking with the completion allowances and retry
recovery recorded above. It inherits the v79
waiting behavior.
V79 adds bounded waits and generic, recipient-scoped contextual validity review
in the existing DM task. Fixed outcomes/timeouts do not call a model. A new
generic wait or newly perceived circumstances can require a DM judgment; there
is no unchanged-state polling. All native tools and output token caps are retained.
See [the waiting contract and verification](08-time-reading-and-background-activity.md#bounded-waiting-and-contextual-validity-2026-11-08).

An accompanying preflight incident exposed the former 60,000-byte envelope cap:
the affected v78 role request was 60,319 bytes with 29,534 bytes of dynamic JSON
content; shared fixed instructions consumed the rest. Admission now separately
bounds serialized dynamic messages (including tool continuations) to 40,000 bytes
and the whole request to 90,000 bytes. This is a byte admission policy, not a token
limit or a cost saving. Existing provider/dollar reservations still count the
whole payload. No history or prefix is rewritten to fit. The failed request now
passes locally unchanged, and explicit manual recovery is allowed; oversized
preflight failures never enter automatic retries because no paid attempt exists.
A read-only replay of 80 operations matched all 163 historical request hashes.
Five admission tests cover the separate limits, tool-result size, manual-only
recovery and preservation of an existing pinned operation.
The final full regression passed all 369 tests. The 18:03:16 CST service reload
preserved all saved states and call/operation receipts; an authenticated read of
the paused affected game verified that manual recovery is available. No real
game retry or story progression was performed during deployment.

V78 adds scoped current/arrival presence and
sparse memory snapshot guidance without new calls, tool families or token caps.
Capacity retries now explain the exceeded dimension and persist the exact
`request_feedback` for reproducible recovery, including explicitly resumed v77
failures. Old completed requests still reconstruct their historical bytes.
See [arrival presence](03-communication.md#arrival-presence-and-observer-wording-2026-11-08)
and [source-count correction](02-memory-state-evidence.md#source-count-retry-correction-2026-11-08).
V76 adds conditional, scoped investigation
reminders; V77 clarifies voluntary continuation after movement instead of waiting
for an own-action receipt that will not wake the role. Only role guidance changes;
all other task definitions, output budgets, proof rules and waiting permissions
remain unchanged. Reminders use existing normal decisions, with no additional
model stage or polling. See the
[reminder contract and verification](02-memory-state-evidence.md#conditional-investigation-reminder-2026-11-08).
V75 implements the memory source-pressure correction above.
V74 versions local communication and
optional pre-movement speech in the existing role response, for both ordinary
and concealment perspectives. It also clarifies DM, address and action guidance;
all token caps and native tool families remain unchanged. Three synthetic real
Flash travel decisions used five calls (three roles, two speech DMs), costing
USD 0.00359868. No planning, movement-specific or polling call was added. See
[the communication record](03-communication.md#local-conversation-and-voluntary-travel-speech-2026-11-08).
V73 adds concise per-aspect reasons to the
existing final-argument call, retaining its 1,600-token cap and all other task
definitions. It gates equivalent-proof matching and explained reviews without
changing pinned historical evaluation. Process feedback is a local projection,
not a new model call or a whole-history prompt. Four synthetic real Flash cases
used eight calls including endings, costing USD 0.005096028. See
[the review record](06-goals-and-endings.md#evidence-matching-and-explained-reviews-2026-11-08).
V72 changes only the ordinary role's
investigation-choice and closure guidance; it adds no planner, forced movement,
new call stage or grading change. See the [bounded reproduction record](18-spectator-mode.md#investigation-guidance-only-trial-2026-11-08).
V71 separates the culprit's closure and
final-position instructions from investigator proof assembly, using the existing
private perspective routing; it adds no model stage or new output budget. See
[the spectator module](18-spectator-mode.md#separate-final-submission-guidance-2026-11-08)
for scope and verification. V63 introduces the compact wire contract;
v64 makes observation source-table keys the authorized observation IDs after a
real Flash probe showed confusion with internal event-derived keys. V63 remains
immutable for its recorded calls. V65 adds visible memory capacity; v66 adds
capacity-triggered consolidation after real play showed that prompting alone did
not reliably stop accumulation. V67 restores the earlier explicit voluntary
closure condition. V68 clarifies that repeated denials need not rewrite a belief
or require a confession before an independently supported conclusion; the role
still decides whether further investigation is useful. V61/v62 introduced presentation receipts and
role-scoped exploration/acquisition. The version history below describes earlier
contracts, which remain immutable and available for pinned recovery. Baselines
remain role/channel scoped; new observations follow them. All tasks inherit
DEEPSEEK_MODEL, default deepseek-flash. The interface displays provider-reported
cache hit/miss tokens and the input-weighted ratio; missing usage remains unknown.
Games initially allow 128 calls. Each stage permits one initial attempt plus
three automatic retries; every actual provider attempt counts against the limit.
Spectators can add 64 calls independently of money; ordinary games retain their
fixed cap and USD 0.25 admission estimate. Spectators default to USD 0.10 with an
80% warning, explicit USD 0.05 additions and conservative per-call reservations.
Unknown usage retains its reserve. A limit pauses play without creating an ending.

V60 changes only new preview naming: the model authors names alongside each
premise instead of receiving the legacy name pool. Both preview tasks allow 1,800
output tokens. The new response contract and dynamic-input shape are versioned;
earlier pinned requests keep their original rosters and hashes. The selected cast
remains the immutable game-specific baseline. No additional naming call is made.

### Source-lookup offset incident: 2026-11-08

A production spectator step pinned to v68 failed eight times across two explicit
recovery rounds with `ValueError: source lookup request`. All eight native
`read_sources` calls supplied source IDs without `offset`. The tool description
said character offsets were optional, while its JSON schema and handler required
that field. Repeating the same request retained this contradiction; retries could
not reliably repair it.

The handler now treats an absent offset as character zero, for both new requests
and already pinned operations. V69 makes the schema and description agree:
`id` is required; `offset` is optional with default zero. Explicit null, boolean,
negative, fractional or string offsets remain invalid. Unknown fields and foreign
actor selection remain invalid. Original tool arguments, failed-call receipts and
published v68 prefixes are preserved.

The affected role had not acquired the requested document IDs. Local replay of
all eight recorded calls now returns the ordinary `unavailable` tool receipts,
without exposing those documents or changing game state. A heard reference to a
document still does not grant access to its original body.

Verification: 257 Python tests passed, including exhausted-v68 recovery through
its original operation, authorization and pagination checks. A two-call real
Flash native-tool probe on a synthetic fixture omitted both offsets, read the
acquired source, returned unavailable for the unacquired source, and completed
its follow-up response. Estimated probe cost: USD 0.0003153. No production story
was sent to the provider for this validation. Artifacts:
`.local/verification/source-lookup-offset-20261108/`.

The production game stays paused at its saved step until the user selects recovery;
service reload does not open another paid retry round.

### Memory-contract incident: 2026-11-08

The same spectator game later paused at step 67 in `memory_B_123`, pinned to v69.
Its four attempts failed for an unaccepted `self_claim` entry, a response truncated
at the 700-token output cap, a complete 645-character snapshot exceeding the
600-character validator, and another `self_claim` entry. Observation projection
already used `self_claim` for a role's own speech; the memory enum omitted it.

The runtime now accepts `self_claim` as its own category, preserving text and
sources rather than converting an account into an observed fact. Authorization,
checkpoint, entry/source count and fixed-knowledge boundaries remain enforced.
The compactor accepts up to 699 total text characters, strictly below its
700-character pressure trigger. Its writing target remains 150–250 characters;
no generated text is cut or rewritten to fit. Pressure and capacity constants
are shared by memory validation and scheduling.

V70 makes the five kinds explicit in both role and memory instructions and raises
only the memory output allowance from 700 to 1,400 tokens for structured entries,
citations and JSON. This is an output ceiling and conservative reservation, not
an automatic doubling of billed output. Previously pinned tasks keep their exact
prefix and output cap; the compatible runtime accepts their complete responses.
Failed calls are not retrospectively marked successful or committed.

Verification: 264 Python tests passed. New coverage includes claim/source
preservation, unacquired-source rejection, 645/699-character acceptance,
700-character rejection, no repeated idle compaction, archival preservation and
an exhausted v69 operation recovered by explicit retry without changing its
pinned version. Read-only local replay accepts all three complete recorded
responses (590, 645 and 498 characters); the truncated response remains invalid.
Original production history and failed receipts remain unchanged.

A synthetic real Flash operation compacted 9 entries / 653 text characters and
9 pending observations (123 total) into 5 entries in one call, with checkpoint
123. Its own false account stayed `self_claim` and explicitly distinct from what
actually happened. Full observations and acquired records remained identical.
Provider usage: 4,087 input tokens (384 cache hits), 347 output tokens; estimated
cost USD 0.001529604. This bounded probe is not a new full-game quality or cost
comparison. Artifacts: `.local/verification/memory-contract-20261108/`.

### Implemented optimization and recovery contract

- `compact_context.py` resolves each acquired evidence body once per source version.
  Evidence, observation, recall and request metadata use column/row tables; source
  bodies retain speaker/occurrence identity. Role references use authorized
  observation IDs in v64. DM inputs retain utterance-time knowledge, fixed truth,
  scoped history and complete acquired evidence; later discoveries cannot enter
  an earlier speech snapshot. Full source bodies remain available on every call.
- `actions` carries exact legal argument tuples. The stable prefix defines action
  meaning, costs and duration. Existing handlers revalidate actions. Human menus
  and scenario rules are unchanged. Visible unread objects retain usable labels.
- `memory_entries.py` applies `memory_update: null` or an explicit
  `{upsert, archive, processed_through}` patch. Each active entry has a stable ID,
  kind (`observed`, `self_claim`, `heard_claim`, `unresolved`, `interpretation`), text and sources.
  The writing target is 3–6 entries / 150–250 Chinese characters; validation allows
  at most 12 entries, 950 total text characters, 8 sources per entry and 30 unique
  sources overall. Replaced/archived entry versions are retained separately.
  Null leaves the processing checkpoint unchanged. Advancing it requires every
  intervening observation to have been supplied. Existing chunk compaction handles
  accumulated observations. In v66, 9 active entries or 700 text characters also
  trigger this path before the next decision. That bounded compactor returns a
  complete replacement of at most 6 entries / 699 text characters, then the role
  resumes incremental patches. V75 additionally triggers at 24 unique sources
  and caps the replacement at 20, exposing source limits and remaining capacity.
  No consolidation call runs solely for an idle poll or when no pressure threshold
  is reached. Its extra cost is measured separately.
  Initial scripts,
  full documents and original observations are never deleted by a memory patch.
- `belief_update` and concealment-only `strategy_update` distinguish null,
  replacement and `{clear: true}`. Empty objects and the wrong role perspective
  are invalid. Empty relationship updates preserve prior relationships. Fixed
  private knowledge cannot be cleared by these interpretation fields.
- `read_sources` offers one batch of up to 8 authorized IDs / 8,192 UTF-8 body
  bytes, with character offsets and explicit excerpt/continuation metadata.
  Unavailable and unauthorized IDs have the same response. Current cited memories,
  beliefs and obligations remain in context; old relationship-only raw recall is
  replaced by source IDs. Read-only retrieval and event listener creation can
  each use one batch, with at most two continuations before a final decision.
- Ordered wire serialization puts stable instructions, authorized baseline and
  acquired source bodies before changing beliefs, receipts and executable state.
  Global canonical JSON, old request fingerprints and published prefix files are
  unchanged. Prefix ordering is not a promise of provider cache retention.
- `action_feedback.py` records new execution metadata and derives only own or
  received occurrences. Counts update on real executions; lifecycle completion,
  failure and cancellation update the original execution. At most two recent
  receipts per comparable group and approximately 2 KiB of group bodies enter
  each prompt; omitted groups/details are identified. Required active work and
  direct obligations remain separately present. The initial 6 KiB candidate
  increased request size in replay, so it was reduced before release. Missing
  recipient history stays unknown. Speech remains a claim, never a physical receipt.
- Gateway retries connection/timeouts, invalid outputs, HTTP 408/409/425/429 and
  5xx failures, with 1/2/4-second backoff and numeric Retry-After bounded to 30s.
  Each attempt is logged and budgeted, including unknown-usage reservations.
  Pause, cancellation, stale state, permission/configuration, context and spending
  limits do not trigger automatic retries. Cancellation is rechecked during backoff
  and before commit. Manual retries are idempotent commands that reuse paid stages
  and tool receipts; failed model operations block unrelated replacement work
  until explicitly recovered or cancelled. Preview/setup failures also have recovery.
- Web views expose automatic retry progress and an explicit retry/cancel decision
  after exhaustion. Non-hosts cannot recover shared background work. Stable space
  is reserved for wrapped status messages on desktop/mobile. Mutation requests
  allow up to ten minutes for multi-stage recovery while polling remains active.

### Acceptance record: 2026-11-08

Artifacts are under `.local/verification/cost-optimization-20261107/`.

- Historical replay reconstructed **919 old request hashes across four games**
  with zero mismatches; saved world-state hashes remained unchanged.
- On the latest completed v61 game, the same historical role snapshots projected
  into the final role wire contract averaged 44,875.6 → 43,086.9 serialized request
  bytes (**4.0% lower**);
  dynamic role content was 22,985.1 → 20,785.3 (**9.6% lower**), including the new
  feedback. DM requests were 39,707.7 → 41,295.4 (**4.0% higher**). This is a byte
  projection, not provider token billing or a matched whole-game cost experiment.
  Earlier versions had different features and smaller prefixes; their aggregate
  request sizes must not be used as a like-for-like savings claim.
- A real v63 probe failed all four role attempts because Flash cited internal
  source-table keys. State was not committed and spectator play paused with a
  retry decision. The failure ledger is retained; v64 fixes the source identity
  ambiguity instead of silently accepting unauthorized references. A fresh v64
  game reached 24 steps before accumulating 12 memory entries. V65 capacity hints
  recovered it but did not reliably prevent another overflow at step 32. V66
  consolidates at 9 entries / 700 characters and validates a compact replacement.
  All version transitions in this synthetic test were explicit cancellations and
  new operations; previously pinned request inputs were never rewritten.
- A separate real Flash compaction processed 30 synthetic observations in one
  call, produced four attributed entries, advanced the checkpoint to 30, and
  preserved original observations. Logged estimated cost: USD 0.001446168.
- **252 Python regression tests passed.** Playable and spectator browser tests
  passed at 1440px and 390px: 16 busy/retry transitions, zero content displacement
  and no page errors. Retry controls also sent the correct recovery command and
  cleared a previously retained foreground request. Browser geometry and full-play
  evidence are recorded
  in `regression.log`, `browser/report.json`, `live-final-report.json` and the isolated
  SQLite ledgers. The long synthetic game reached 107 steps / 239 attempts and
  paused for stagnation without a runtime error, at USD 0.44324682 including the
  earlier-version failures. Remaining cost was dominated by repeated questioning;
  v68 clarifies unchanged updates and independently supported closure. A manual
  test resume retained the fixed case, observations and existing budget.
  The final v68 continuation used 19 attempts with no failures: three roles
  voluntarily agreed to closure, all four submitted independently, and the game
  ended at step 115 with the culprit established. The complete mixed-version
  ledger contains 258 attempts / USD 0.483458412, including development failures
  and capacity consolidation. This is acceptance evidence, not a fresh v68 versus
  v62 cost comparison. Input was 2,383,361 tokens, with 1,252,352 reported cache-hit
  tokens; output was 113,868 tokens. Original dialogue and case truth remained intact.
- New ordered contexts exposed a recovery-order issue: canonically stored output
  could reorder a memory entry before a later DM stage. The gateway now restores
  the raw provider JSON field order after confirming semantic equality with the
  validated stored result. A dedicated pause-after-DM test proves that both paid
  stages are reused without another provider call. All 256 replayable background
  requests in the synthetic game were reconstructed. One pre-fix paused operation
  used the historical canonical-result order; the read-only audit reports that
  alternate representation explicitly. No request hashes or old responses were rewritten.
- A controlled real Flash conclusion fixture, with three prior votes and all
  documents acquired in setup, completed all four independent submissions, four
  theory reviews and ending narration. Three investigators established identity,
  method and time; the concealment role's counter-accusation was rejected.
  It used 14 calls / USD 0.020084232. This verifies the ending contract, not
  autonomous investigation difficulty or a whole-game savings percentage.
- Local service deployment: the previous transient service was absent and HTTP
  was unavailable. A consistent SQLite backup was made, the final v68 service was started with
  systemd, HTTP returned 200, and all 28 existing game-state hashes remained
  identical. `ai_operations.retry_state` was migrated without rewriting saves.

### Shared event protocol and native tools

`event-protocol-v3.txt` holds universal event/listener rules plus the bounded
source-lookup coexistence contract. Earlier task versions retain v2. It precedes
task-specific role/DM instructions and immutable authorized baselines. The stable
`create_event_listener` function schema is part of each role request's frozen
prefix and its fingerprint. Per-game targets, conditions, progress, receipts and
native assistant/tool-result messages stay in the dynamic suffix. Changing an
event instance does not alter that prefix hash; this is tested independently of
the provider's reported cache hits. There is no claim of a separately allocated
provider-side dynamic-cache object.

`ai-core-v2.txt` explicitly permits provided native tools while retaining the ban
on arbitrary code, invented effects and fabricated tool receipts. Earlier versions
retain ai-core-v1.txt and their original request hashes. V56 introduced the native
event tool, and v57 corrected the old core's conflicting blanket tool prohibition.
V58 permits native tool output with the provider's text response mode for role
tasks; their final content still requires parsed, validated JSON. Other tasks and
older pinned versions retain JSON response mode. V59 explicitly requires tool
registration before a new custom wait; merely describing a wait does not create
one. These changes do not assert that JSON mode alone caused the earlier failures.
The runtime follows the provider's [Tool Calls protocol](https://api-docs.deepseek.com/guides/tool_calls/)
using actual assistant tool calls, matching tool_call_id results and a bounded
final decision. Each provider request, including tool continuations and failures,
has its own persisted stage, usage, reservation and raw response.

The v59 real synthetic probe completed nine calls, including native creation and
its continuation with an unchanged prefix hash. Provider-reported input contains
23,296 hit tokens and 18,442 miss tokens (55.82% input-weighted hit ratio), costing
USD 0.007006776 including output. This verifies observed reuse, not cache lifetime
or a whole-game cost-reduction percentage. See the verification record in
[Time and background activity](08-time-reading-and-background-activity.md).

Earlier versions 24-28 add ensemble tasks; v29 adds the current audience;
v30-v35 refine scoped focus, private reasoning, grading and ending context. New
setups use case rules version 3. Their original context shapes remain pinned.

Versions 36-41 add contextual dialogue cues, shared closure and optional grounded
progress, actually heard speech as a valid source, a DM new-utterance allowlist,
and a role's recent actual choices/unread opportunities. Version 41 supplies
historical action labels without executable IDs; current choices remain the only
executable menu. Version 42 adds first-person role/memory wording and resolves
first-person human input to the acting character, without changing schemas or
dynamic input shapes. Role dynamic context version 6 and DM context version 2 are
operation-pinned. No observer controls, human counts, spending metadata or hidden
omniscient view enter role requests. Older artifacts remain unchanged. See
[Spectator mode](18-spectator-mode.md) for measured outcomes and limitations.

Implementation: [complete playable runtime](17-complete-playable-runtime.md). Verification uses `tests/test_ensemble.py`, the multiplayer browser walkthrough and fresh provider receipts listed there. The design alternatives below retain their proposal scope; older implementation sections describe legacy saves.


References: [Conventions](../AGENT.md), [Private conversations](03-communication.md), [Time and background activity](08-time-reading-and-background-activity.md), [System DM](10-system-dm-and-deception.md), [Custom runtime](12-lightweight-runtime-architecture.md).

## Confirmed Requirement

Independent prefix caches that remain protected from unintended changes are a prerequisite for the agent architecture. Cost must be considered when designing main DMs, temporary private DMs, character activity, and other generated content.

The application must preserve immutable, independently scoped prefix artifacts. Provider cache residence and billing are separate concerns and require a provider-specific integration. The user selected DeepSeek on 2026-11-04. The AI runtime now uses versioned scoped baselines, budgets, and whole-game usage attribution; see [AI runtime](15-ai-runtime.md) and the dated provider contract in [DeepSeek integration](14-deepseek-integration.md).

## What Remains Immutable

Publish a versioned baseline for each reusable context. New turns must not rewrite its content, ordering, tools, or serialization. Legitimate instruction changes create a new version rather than modifying a published baseline in place.

A prefix is part of the final request presented to the model, not just the source template. Inspect final assembled messages, tool definitions, and output-format configuration when checking stability. Account for provider-managed context that the application cannot directly inspect through compatible settings and reported usage.

Record a stable fingerprint of the application-controlled serialized baseline and its compatible configuration. Detect unexpected drift before expanded agent flows rely on reuse. Exact identifiers and serialization are implementation decisions.

## Proposed Prefix Layers

| Layer | Possible contents | Reuse and boundary |
| --- | --- | --- |
| Shared public foundation | General game conventions and common stable instructions | Reuse only identical authorized material |
| Role-type instructions | Main DM, private DM, or character-specific responsibilities and stable schemas | Separate compatible baselines by role and version |
| Scenario and session baseline | Relevant initial setup and authorized starting information | Freeze for the appropriate game, role, or conversation scope |
| Dynamic suffix | Current state overlays, new memories, relationship changes, turns, tool results, and current input | Update after the frozen boundary |

These are context-design proposals, not a guarantee that a provider supports a separate cache object for each layer. The final prefix must meet the selected provider's actual reuse conditions.

Each role sees only material appropriate to that role. Character prompts must not inherit a main DM's hidden world knowledge merely to obtain a cache hit. A private DM may obtain relevant internal facts for adjudication while continuing to protect what its participants actually know.

Session IDs and other changing metadata should not be repeatedly inserted ahead of otherwise reusable content. Bind access and identity in application state and in the required role context, placing dynamic metadata after reusable material where the chosen interface permits.

## Isolation and Safe Branching

- Keep parent and sibling baselines immutable when creating a private conversation.
- Reuse a private-DM instruction baseline and create a separate conversation branch with its own participants, turns, and authorized starting view.
- Append new information to the branch without modifying the parent or another role's context.
- Apply current state as an explicit dynamic overlay; freezing an initial relationship does not freeze its later evolution.
- Retain one authoritative world history. Cached prompt text is not the database of truth or the sole copy of game memories.
- Close and archive a private session without invalidating shared application prefix artifacts.
- Enforce permissions separately from cache identity. A cache key or cache hit is not authorization to receive hidden information.

Technical namespaces should identify compatible model configuration, prefix version, authorized scope, and content fingerprint. Their exact relation to a provider routing key or cache handle must be designed after selecting the integration; creating a unique provider key for every message may defeat intended reuse.

## Dynamic Context Growth

Preserve reusable history when economical, and include only relevant new facts and context required for the current task. Do not copy the full world state or every participant's transcript into each private DM.

If growing context needs summarization or a checkpoint, operate after the protected baseline. Preserve authoritative history outside the prompt, maintain information provenance, and rebuild the dynamic portion explicitly. Such changes can affect reuse of the dynamic history even when the baseline remains unchanged.

Compare total cost and quality before and after compaction. Keeping an unnecessarily long history solely to maintain a high hit percentage is not a sufficient cost policy.

## Calling Policy Proposals

| Work | Cost-conscious approach |
| --- | --- |
| Reading gates, counters, permissions, and timers | Use ordinary application rules |
| Straightforward recorded-state checks | Query authoritative records and apply deterministic checks where possible |
| Agent autonomy | Allocate bounded decision opportunities triggered by relevant information or a permitted scene opportunity |
| Private AI exchanges | Enforce duration and turn caps, bounded context, and a parent game budget |
| Natural-language interpretation and narration | Use model calls where needed, combining compatible work when this preserves information isolation and correctness |
| Recipient delivery | Derive views from one resolved event; avoid generating incompatible copies or unnecessary repeated narration |
| Retries and recovery | Bound attempts and include their costs in the originating activity |

No new AI gameplay call is allowed solely to keep a cache warm during a reading pause. Prewarming, if supported and useful, is an optional costed optimization that needs an expected-reuse justification.

Set budgets for a game, an activity type, a character, and a private conversation. Exact limits are open. New private sessions should inherit the remaining parent budget rather than reset the game's allowance. When optional background work reaches its budget, stop or reduce it under a defined policy without fabricating actions, violating required responses, or leaking information.

Model tiers and generation limits should be chosen using quality and latency measurements as well as prices. A routing decision or separate DM responsibility does not automatically require an additional model call.

## Cost Accounting Proposal

For a provider whose billing categories are disjoint, estimate each call as:

    call_cost = (
        uncached_input_tokens * uncached_input_rate
        + cached_read_tokens * cached_read_rate
        + sum(cache_write_tokens_by_class * corresponding_write_rate)
        + billable_output_tokens * output_rate
    ) / 1_000_000 + other_applicable_charges

Rates above are per million tokens. Normalize provider usage into disjoint categories: do not charge the same input as both ordinary input and cache write, or count reasoning twice when it is already included in billable output. Include session creation or prewarming requests, abandoned previews, retries, and any other billed work in the appropriate activity ledger.

Estimate game cost by summing all main-DM, private-DM, character, preview, and supporting calls. A cache miss, expiry, short conversation, or unused prewarm can change the economics. No monetary saving or maximum game price is established before selecting rates and measuring actual usage.

## Measurement and Acceptance

Capture compatible request metadata, activity kind, game and conversation scope, prefix version/fingerprint, reported cached reads, writes where available, uncached input, output, retries, latency, and rate-card version. Keep unknown usage explicitly unknown until reconciled; do not treat missing counts as zero.

Use provider-reported usage and attributable costs to evaluate a complete playable flow. Offline token counts and stable templates are useful diagnostics, not proof of billed savings. Raw prompts containing secrets need separate protected handling; ordinary metrics need not expose their contents.

Evaluate at least cold start, warm continuation, multiple short private conversations, long conversations, pause and resume after cache expiry, a deliberate prefix version change, and dynamic-context compaction. Measure calls and cost per completed activity and per game alongside latency, factual consistency, and role isolation.

Before expanded execution relies on the design, verify:

- Dynamic updates do not mutate the protected serialized baseline.
- Stable tool definitions and message ordering are preserved where required.
- Creating, ending, or compacting one session cannot mutate another.
- Shared segments contain no unauthorized role secrets.
- Provider misses can be handled from the immutable source without changing game facts.
- Usage reporting includes all relevant calls and output rather than only cached input.
- Background work remains bounded and obeys initial-reading and pause gates.

The bounded review path was validated with three actual DeepSeek calls on 2026-11-04; the second and third responses each reported 512 cached input tokens. See [the measured record](14-deepseek-integration.md). These earlier review results establish only that path. Whole-game and private-DM usage is recorded in the AI-runtime module; compaction and expiry benchmarking remain open.

## Provider Reference Boundaries

Official OpenAI documentation, checked on 2026-10-26, describes matching rendered prefixes, finite cache lifetimes, and model-dependent cache-read and cache-write charging. Prompt caching still generates new output. These are implementation-reference facts, not a provider choice for PALTER. [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)

OpenAI's usage guidance evaluates all calls, generated output, retries, and applicable charges; a high cached-input percentage alone does not establish lower total task cost. PALTER's measurements should follow that whole-activity accounting principle. [Observability and usage](https://developers.openai.com/api/docs/guides/agents-api/observability)

Recheck actual provider eligibility, configuration, billing fields, and rates when the integration is selected. Do not hard-code one provider's current thresholds or retention settings as shared game rules.

## Open Questions

- Provider and models, cache eligibility, routing, lifetimes, and billing fields.
- Exact prefix layers, serialization, identities, and permitted reuse scopes.
- Dynamic context retrieval, checkpoints, and compaction thresholds.
- Model-call, token, output, retry, and monetary budgets.
- Whether and when prewarming is economical.
- Budget-exhaustion behavior that preserves gameplay obligations and information boundaries.
- Acceptance thresholds for total cost, latency, consistency, and actual cache reuse.

## Legacy Demo 01 Implementation and Verification

palter/ai_gateway.py verifies published core/task source hashes and builds fresh independent requests. Prefix fingerprints include immutable instructions, role/chat baselines, model, and request settings; acquired records and evolving interpretations are dynamic trailing input. The ledger retains actual request hashes, usage, latency, status, protected raw results/responses, and event linkage. Maximums: 128 calls per game, two explicit attempts per stage, three reviews, 60,000 serialized request bytes, task-specific output caps, and two concurrent provider requests. New calls stop when the accumulated estimate reaches USD 0.25; unknown charges are conservatively reserved, so this is not an invoice-enforced monetary ceiling. No silent fallback or idle prewarming occurs. Real whole-game usage and failure/recovery evidence are in [AI runtime](15-ai-runtime.md). Multi-provider routing, compaction, and cache-expiry benchmarking remain designs.


## Legacy Demo 02 Implementation: 2026-11-05

The user requested Flash wherever practical. Task version ai-tasks-v23.json removes
the earlier one-time Pro setup override: all current tasks inherit DEEPSEEK_MODEL,
which defaults to deepseek-flash, without thinking. Setup retains its 3,200-token
output cap. Older operations retain their pinned version, including any model
override. Each call records its actual requested model; fingerprints and cost
calculations use that model. The existing request, retry, concurrency and
cumulative-cost guards remain. Reading and notebook/inspection operations do not
call a model.


## Investigation Trace Display: 2026-11-05

The investigation UI again shows provider-reported cache-hit and cache-miss input
tokens for each call, plus the input-token hit ratio and an aggregate. Aggregates
include only complete, internally consistent input-usage reports; unavailable
usage stays unknown rather than becoming zero. The expanded trace panel remains
open across view refreshes. This is a display correction, with no prompt, provider
request, cache policy or saved-case change.

