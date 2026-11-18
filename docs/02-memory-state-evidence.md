# Memory State and Evidence

Status: Scoped acquired snapshots, separate object condition/custody, traces and sourced memory compaction implemented.

Last updated: 2026-11-11.

## Summary Capacity Reserve: 2026-11-10 (v122)

Status: implemented, regression-verified and deployed; three bounded real Flash trials pass.

Standalone consolidation must return at most six entries, leaving at least six
slots below the unchanged twelve-entry active-memory limit. Six is a validated
summary limit, not merely an advisory writing target. Keep the existing trigger,
below-1024 summary text requirement, 2048-token output cap, source permissions,
checkpoint rules, bounded retries and immutable originals. The model reorganizes
compatible topics and preserves epistemic distinctions; engineering never cuts
entries or silently drops citations. Align the task instruction, request limits,
validator and correction receipt. Entry overflow requires a full regrouped
snapshot, even when the text already fits; text-only repair cannot reduce entries.

New operations use v122. Preserve all paid historical requests and accepted
results. A pinned failed role stage with an active-memory capacity error and no
paid role/tool response may run one separately recorded six-entry consolidation
before a fresh role attempt. Reuse that maintenance stage on restart; its paid
presence preserves the recovery path even after the role completes. Never inject
changed memory before an already paid role/tool request. This repair waits for
the user's explicit retry, uses ordinary call/spending limits and does not reset
the role's retry allowance. Stored production games remain untouched during tests.

After the separate consolidation, locally revalidate previous failed role outputs
against the current memory to construct fresh correction feedback. Remove an old
capacity failure only if the relevant checks now pass; retain actual permission,
source and other failures. Do not forward stale entry counts from the old full
summary or auto-accept a previously failed decision. A fresh model reply still
must pass the complete validator. Already paid role/tool requests retain their
saved feedback and exact hashes.

Verification artifacts: `.local/verification/memory-headroom-v122-20261110/`.
Eight focused tests cover the six/seven boundary, six available growth slots,
full-snapshot retries, text-only repair, source permissions, version isolation,
retry admission, and recovery/restart reuse without repurchasing paid stages.
The latest failed operation's five stored request hashes match local replay;
its accepted twelve-entry summary remains historical, and an explicit retry
reaches the separately recorded `memory_headroom_B_91` request with a six-entry
limit. No production records were edited or sent to the provider during testing.

Three synthetic twelve-entry memories containing 401, 689 and 977 text characters
were consolidated through the real Flash gateway. Each succeeded on its first
attempt with six entries; results contained 346, 400 and 389 text characters and
used 391, 437 and 416 completion tokens. Total logged upper cost was USD 0.003360552
within a twelve-call / USD 0.10 verification allowance. All requests kept thinking
disabled and max_tokens=2048. Source/checkpoint validators passed and original
records remained unchanged. These are bounded compaction checks, not whole-game
or exhaustive semantic-accuracy acceptance.

Final full regression: all 667 tests passed in 176.790 seconds, with local socket
access for the HTTP tests. The 142-artifact publication gate passes and all 141
previous artifact hashes are unchanged. Initial results are retained: the first
full run had five sandbox socket denials and one test-fixture checkpoint error;
the fixture was corrected to supply all pending observations, without weakening
the checkpoint guard. Focused memory/recovery checks and the final full run pass.

Deployment: `palter.service` restarted from PID 798760 to 819724 at 23:18:33 CST
on 2026-11-10 using the project Conda interpreter. The unit is active/running;
the homepage and three scripts return HTTP 200. Before/after hashes match all
44 games, 5,330 AI calls, 2,499 operations and two legacy model calls. No requests
were pending; the latest game stays paused at revision 115 / step 85 with its
existing retryable error. The user can explicitly resume the failed step; the
restart did not advance any game or launch production model calls.

## Role-Owned Dialogue Focus: 2026-11-10 (v117)

Status: implemented; regression and targeted real-model verification complete.
Fresh whole-game acceptance failed; not deployed (module 11). Repetitive
questioning remains observable in longer play, despite the targeted changes.

The user approved addressing successive characters paraphrasing the same speech,
including accidentally taking over another speaker's duties. New role guidance
should select speech by the character's own communication purpose, goals and
position. Shared agreement does not require repeating the previous argument or
procedure; brief acknowledgment or permitted silence is valid. Do not manufacture
disagreement, new facts or fixed dialogue roles to create variety. Distinguish
another character's experience, promise and responsibility from the speaker's own.

An opt-in `dialogue_focus` identifies `reply_as` and indexes at most two of the
role's own latest testimony observations and three actually received peer
utterances, with their original speakers/channels. It contains received observation IDs,
never global event IDs or another role's private records. Existing source bodies
are reused; older omitted bodies remain available through authorized source lookup.
The index does not imply the current audience heard an earlier utterance. It does
not change memory checkpoints or classify semantic novelty, truth or usefulness.

Use the existing model call and output schema. Preserve raw speech, the rolling
wait policy and all published historical requests. No additional self-review,
similarity rejection, prose filter or forced action is permitted. Verify source
isolation, references without body duplication, old-prefix replay, native-tool
continuations and multi-turn real-model dialogue. Compare against v113 on synthetic
fixtures only; production transcripts stay local. Narrative behavior and complete
game acceptance must be reported separately from contract checks.

The index appears at the end of the new version's dynamic context. It carries no
copied transcript text and no engineering-generated communication objective.
Profile, personal objectives and existing private interpretation remain the
authority for the role's own position. V114 retains its original own-only index
and original request ordering for paid replay. Its experiment still produced a
copied utterance and duty transfer; its published artifact is retained unchanged.

V115 clarifies that communication motives do not add output fields, and the role
returns only the interpretation field belonging to its current perspective. A
wrong-perspective update now gets structured field-permission feedback before
its nested patch is expanded. This preserves the prior rejection boundary while
making the actual error repairable; it does not rewrite or discard model output.

The longer v115 game still contains successive paraphrased questions and repeated
plans despite improved short probes. V116 retains the same index and permissions,
but puts a more concise turn-taking contract at the end of the role instruction:
one current contribution, usually one sentence, with longer explanations allowed
when needed. Another role's unanswered question need not be repeated; established
duties need not be re-announced. This is guidance, not a length cap or scheduler
change. Neither version establishes that repetition has been eliminated.

V117 moves only already supplied bodies for the indexed utterances from top-level
`sources` into trailing `dialogue_focus.sources`. Both pools resolve the same
source IDs; no body is duplicated, newly disclosed or fetched just to populate
the index. Omitted historical bodies still require authorized lookup. Speaker,
channel and occurrence identity remain unchanged. Fit the budget against this
final layout, including its small structural overhead. V114/V115/V116 layouts
stay pinned. Repeated waiting announcements are explicitly unnecessary, while
the existing wait allowance and ordinary actions remain unchanged.

## Accumulated Reasoning References: 2026-11-09 (v107)

Status: implemented; whole-game acceptance is recorded in
[spectator mode](18-spectator-mode.md#whole-game-acceptance-and-accumulating-references-2026-11-09-v107).

The production v106 failure was a belief delta, not standalone memory compression. Twelve
prior testimony IDs plus one new authorized ID hit a leftover twelve-ID cap.
The rejection had no validation feedback, so all four attempts repeated a valid
increment that the old validator disallowed. The same audit found a default
thirty-ID helper limit on strategy/progress/relationship sources and final review.
Remove these citation-count limits across the ensemble chain, including human
submissions and per-aspect normalization. The legacy general runtime keeps its
separate contract. Invalid or unreceived IDs still fail authorization.

New instructions permit explicit removal of obsolete reasoning sources when a
model revises its interpretation. Engineering neither selects which real source
to discard nor truncates source arrays. Fixed memory-entry structure, the 1,024
text-character consolidation trigger, below-1,024 summary and 2,048-token summary
budget remain unchanged. Input envelopes and scoped on-demand originals still
bound actual context; unbounded citation count is not an unlimited request size.

Numeric text feedback names the affected field, maximum and actual length;
invalid-reference feedback identifies the relevant field and rejected positions.
Remaining schema errors get task-scoped correction through existing automatic
retries. Output is revalidated atomically, never patched into apparent success.
Paid historical results and full source histories remain unchanged.

Whole-game verification also exposed a separate snapshot repair bug: a complete
13-entry draft with only 856 text characters failed the 12-entry structure, but
feedback assigned thirteen individual shortening targets. Correction version 6
requests regrouping compatible topics, without per-entry text targets or a
text-only repair contract. Dropped old entries are archived as usual; originals,
source authority and attribution remain intact. Text-only shortening remains
available only for a draft whose entry structure and other fields already pass.
The 12-entry, below-1024-character and 2048-token limits are unchanged. See the
whole-game receipts linked above for real recovery, regression and deployment.

## Field Deltas and Scoped Working Views: 2026-11-09 (v105)

Status: implemented; verification and deployment receipts are maintained in
[cost control](11-prefix-cache-and-cost-control.md#scoped-context-economy-2026-11-09-v105).

For an existing memory entry, a role can send only its id and changed fields.
Omitted kind/text/sources retain their previous values. Source arrays allow full
replacement or explicit sources_add/sources_remove, never both in one patch.
New entries still require all defined fields. Belief and concealment strategy
updates support a patch object with the same preservation semantics. Expansion
uses the operation's original state before the existing atomic source, type and
checkpoint validators; raw provider deltas remain in call receipts. Unused entry
annotations remain ignored, including sources_note:null.

An acknowledgment-only memory_update contains processed_through and no content
changes; it cannot advance over observations that were not supplied. A null
update does not silently advance the checkpoint. The model decides whether a
new statement changes a topic; engineering does not classify semantic novelty.
Nine short entries no longer cause entry-count-only consolidation. The new
count trigger is twelve, with unchanged 1,024-character text trigger, standalone
summary below 1,024 characters, 2,048 output tokens and chronological/pressure
protections. Historical pinned operations keep their previous scheduling.

Request-local metadata indexes are smaller and duplicate evidence catalogs are
merged. Known original documents precede optional recalled snippets, with a
6,000-byte optional body allowance during ordinary role decisions and 12,000 at
final submission, still subject to the whole request budget. Current received
observations and native tool receipts stay exact. Every omitted body remains
queryable through scoped source tools: unloaded is not unknown or nonexistent.
Memory citations and persistent source history retain no arbitrary count cap.

## Whole-Memory Rewriting: 2026-11-09 (v103)

Status: implemented, verified and deployed.

The latest v99 game stopped at memory_C_122 after four 2,048-token length stops.
Its input held nine entries with 1,723 text characters, 67 citation occurrences
and eight pending observations. The first attempt copied seven old entry texts
verbatim before appending new material. Its 28,595-byte dynamic input was within
budget. The output ceiling worked; the model failed to reorganize the summary.

The user's subsequent requirement adds a 1,024-character consolidation trigger
and requires each completed summary to have strictly fewer than 1,024 characters
across all entry.text values. Count Unicode characters including spaces and
punctuation, excluding JSON keys, source IDs and other fields. Incremental role
patches may cross the threshold; consolidate before the next role decision,
without waiting for the usual entry-pressure cooldown. Do not reject an ordinary
role action merely because its memory patch crossed that threshold. Other history,
entry and input-pressure triggers remain. A smaller unchanged summary stays idle.

Keep 2,048 as the hard cap on every attempt, including all three retries. V103
changes standalone consolidation guidance to rewrite a compact working memory
by topic, retaining supported conclusions, unresolved contradictions, attribution,
obligations and next checks. Do not reproduce fixed baseline facts, full acquired
documents or every repeated utterance. These originals remain available; preserve
the citations and distinctions needed by each retained claim. Use a soft total
output target below the API ceiling, including JSON and source IDs. Aim for
600-850 text characters as advisory headroom; the hard summary maximum is 1,023.
No per-entry character limit, prose cutting/filter, source-count cap or extra
review call is introduced. A complete but oversized summary receives numeric
capacity feedback and bounded retries; never silently truncate or save it.

Initial v100 long-input trials and a v101 prompt-only trial still produced
oversized summaries. Keep their receipts as failed experiments, not acceptance.
On a text-capacity failure, include only the latest complete rejected entries in
the next retry's feedback so the model can shorten that actual draft instead of
starting from the much longer old memory each time. Mark it unaccepted editing
material, never source evidence. Revalidate all sources, kinds and checkpoints.
Do not accumulate drafts or add a separate review call. Published experimental
prefixes are also immutable; v103 uses a shorter Chinese consolidation contract
and a focused working view. Keep old entries, complete new observation bodies,
thoughts and authorized initial facts. Separately stored beliefs, strategy,
exploration state, old recalled transcript bodies and optional old evidence
bodies are omitted from this request, not from storage or normal role decisions.
Known originals remain available through scoped source tools.

Prompt changes and general draft retries alone remained unreliable in repeated
long-input trials. The final retry contract narrows the task further: only after
a complete candidate passes source, kind, identity and checkpoint checks may a
text-capacity failure select the immutable memory-text-repair-v2 contract. Supply
only its texts, fixed kinds and advisory per-entry writing allocations. The model
returns text_replacements; engineering preserves the validated IDs, kinds, source
lists and processed_through, then validates the complete reconstructed snapshot.
This is an existing retry, not an extra review call. It uses the same 2,048-token
ceiling and cannot query sources or change progress. Invalid-source drafts are
ineligible. Incomplete/unknown/duplicate replacement IDs are rejected. Store raw
responses and the canonical reconstructed result separately for exact replay.
Previously paid v1 repair requests remain reconstructable as originally sent.

Final real acceptance uses five long-input replays from the latest production
game in a separate database. All five pass both size requirements; four need one
bounded automatic retry, while the current paused v99 operation succeeds in one
new call after its copied failed receipts. The final texts contain respectively
967, 817, 714, 766 and 553 characters; successful response usages are 792, 687,
940, 627 and 502 tokens. All nine calls stay below 2,048 tokens, cost
USD 0.012970092 total, preserve sources and checkpoints, and cause no unchanged
idle consolidation. These are local replay results, not a production resume or
a guarantee of lossless summaries. Manual inspection confirms retention of the
main time bounds, observed-versus-claimed evidence distinction, unresolved
identity question and outstanding promise in the supplied samples.
Final acceptance receipts: `.local/verification/memory-rewrite-20261109/acceptance-repair-v2/`.

Final verification passes all 526 regression tests (152.879 seconds), including
57 focused memory/context checks. Read-only historical reconstruction matches
1,086 request hashes across 457 operations and preserves all 110 pre-change
prefix artifacts. The current manifest validates all 116 artifacts, including
the immutable experimental versions and text-repair contracts.

Service restart completed at 14:19:00 CST (PID 541538), with HTTP 200 and no
pending work. Full before/after hashes match for 39 games, 3,161 AI calls,
1,466 operations and two legacy model calls. The latest game remains paused
at revision 92 with its original error and explicit retry available. Deployment
made no production model calls and did not resume play. Verification and
deployment receipts are in `.local/verification/memory-rewrite-20261109/`.

Truncation feedback must change the failed rewrite strategy, with progressively
more concise advisory output targets on repeated length stops. Apply the updated
feedback to new unpaid retries of token-budget memory tasks, including the paused
v99 operation, whose new retry must meet the explicit character requirement;
reconstruct paid requests with their persisted feedback unchanged.
Never apply partial JSON or advance its checkpoint. Validation, original history,
archives, source authorization and retry/cost limits remain intact. Verify using
the actual failed input and longer real-game snapshots in isolated databases;
do not automatically resume the production game.

## Standalone Memory Output Cap: 2026-11-09 (v99)

Status: implemented, verified and deployed.

The user selected max_tokens=2048 for standalone ensemble memory consolidation.
V99 changes only ensemble_memory's completion cap and the matching instruction;
ordinary role decisions retain 6,144 tokens for action, speech and incremental
memory together. All other task settings and instructions remain unchanged.
There are still no memory character limits. The existing three retries retain
the 2,048-token allowance and concise-rewrite feedback; never apply a response
stopped by the provider's length limit. Earlier operations retain their pinned
versions and allowances, and paid request receipts remain unchanged.

Before this change, 98 memory calls with usage in the latest three games ranged
from 446 to 1,475 completion tokens, including retries. Those historical calls
mostly used earlier character guidance, so they do not establish a universal
upper bound or prove long-game summary quality at the new allowance.
Verification receipts: `.local/verification/memory-2048-20261109/`.

The 59-test targeted regression passes, including truncation rejection, three
automatic retries at the unchanged 2,048-token cap, source/checkpoint checks and
paid-stage replay. Read-only reconstruction matches 903 request hashes across
381 operations and preserves all 109 historical prefix artifacts. Two real Flash
consolidations for separate synthetic investigator/culprit fixtures pass without
retries or idle repeat calls, costing USD 0.003230832 in total. These probes verify
execution, not lossless long-game memory quality.

Service restart completed at 12:50:15 CST (PID 520236) with HTTP 200 and no pending
work. Full before/after hashes match for 38 games, 2,972 AI calls, 1,387 operations
and two legacy model calls. The latest game's ended state and revision 153 are
unchanged; deployment made no production model calls.

## Token-Budgeted Memory: 2026-11-09 (v98)

Status: implemented, verified and deployed.

The user replaced memory character limits with the model output token budget.
V98 kept the existing 6,144-token completion cap; v99 subsequently reduces only
standalone consolidation to 2,048 tokens. Remove the 950-character total, 400-character per-entry and
derived 1,000-character role-summary rejection. A complete, otherwise valid memory
must not fail merely for its text length, including explicitly retried older
operations. Retain the 12-entry structural limit, nonempty text, source authority,
source uniqueness, types, checkpoints, archives and original model receipts.

New v98 contexts and instructions omit character targets and ceilings. A memory
snapshot's entire JSON, including citations, shares max_tokens=6144. An ordinary
role decision shares its existing completion cap with its incremental memory
patch. Neither cap is a target to fill. Preserve concise theme-based consolidation
and first-person attribution, without code truncation or extra self-review calls.
For a response stopped by the provider's length limit, never save partial JSON:
use the existing three retries with explicit concise-rewrite feedback and the
same completion cap, then leave further retries to the user.

New compaction scheduling uses pending chronological history, entry pressure and
the actual request envelope pressure already checked by the runtime. Remove the
850/900-character triggers and character-based success targets for v98. Retain
cooldowns and suppress unchanged idle memory rewrites. max_tokens bounds one
response, not accumulated history; the independent 51,200/90,000-byte request
admission guards remain in force. No approximate character/token conversion is
introduced. Earlier pinned scheduling and paid request metadata remain exactly
reconstructable; only new unpaid retry feedback retires obsolete text limits.

Verification: 90 focused tests pass, including nine new token-budget cases.
All eight saved text-capacity failures from `memory_C_128` now pass their original
local validators, as do the five earlier extra-field failures. Historical replay
matches 895 paid hashes across 378 operations and all 108 pre-v98 artifacts.
Three independent synthetic memory probes and one subsequent role decision pass
through real Flash with thinking disabled and max_tokens=6144. Their initial
1,047-character memories become 287, 317 and 274 characters, without enforcing
those lengths or making idle consolidation calls. All four calls total
USD 0.007343256. This verifies execution, not long-game quality or losslessness.
Receipts: `.local/verification/memory-token-budget-20261109/`.

Full regression passes 514 tests in 149.326 seconds. After a consistent SQLite
backup and zero pending-work check, service restart completed at 12:31:45 CST
(PID 517340) with HTTP 200. Complete before/after row hashes match for 38 games,
2,964 AI calls, 1,385 operations and two legacy model calls. The latest game
remains paused at revision 147 for insufficient spectator budget; no game was
resumed, paid call repeated or saved history rewritten during deployment.

## Ignoring Unused Memory Fields: 2026-11-09

Status: implemented, verified and deployed.

The user authorized ignoring extra memory output fields. In two saved operations,
five otherwise valid snapshots added `sources_note: null` to entry m0. The exact
paid requests reconstruct with matching hashes and contain no such field in the
instructions, examples, baseline, current memory, dynamic data or tools. The
example requires id, kind, text and sources only. The four failed attempts in the
later operation reused the same request without validation feedback. This proves
the strict extra-key check caused the rejection, but does not establish why the
model invented the field. No prompt change is justified by this evidence alone.
The recorded native-tool request uses text final content with a JSON instruction
and example, not a provider-enforced final-response schema. The model can therefore
emit syntactically valid JSON with extra keys even though the example is correct.

For snapshots, incremental memory envelopes, patches and individual entries,
require the documented fields and consume only those fields. Ignore unknown keys
whether null or non-null. Do not infer missing fields, replace null required
values, execute extra controls or merge annotations into memory text. Preserve
all existing kind, identity, source authorization, uniqueness, text capacity and
chronological checkpoint checks. Project working copies without mutating raw
model responses or paid receipts; ignored metadata cannot enter active memory,
archives or later contexts. Preserve retained field order for exact historical
request reconstruction. This is a compatible parser fix for current and pinned
operations; it does not change prompts, resume games or rewrite saved outcomes.

Verification: 68 focused tests pass, including seven new tests for null/non-null
extras, required fields, source/capacity/checkpoint guards, archive behavior,
complete role decisions, raw persisted receipts and idempotent operation replay.
All five saved extra-field failures now pass their original local validators.
Read-only replay reproduces 853 paid request hashes across 359 completed operations
and preserves all 108 published prefix artifacts. No additional provider call is
made. Receipts are under `.local/verification/memory-extra-fields-20261109/`.
The final full regression passes 505 tests. The idle service was restarted at
03:11:22 CST (PID 506263), and HTTP returned 200. Full before/after table hashes
match for 38 games, 2,929 AI calls, 1,366 operations and two legacy model calls;
the current game's existing pause and revision 126 remain unchanged.

## Memory Targets and Recompaction: 2026-11-09 (v94)

Status: historical; v98 supersedes character ceilings, targets and triggers.

The latest long game repeatedly rejected 714-763-character memory snapshots
against the former 699-character snapshot ceiling. One retry reached 694, then
ordinary updates reached 710 and immediately triggered another consolidation.
Most older topic texts were retained verbatim. This was an output-capacity error,
not an input-envelope failure: the latest memory request used 22,496 dynamic and
38,931 total bytes.

Separate the advisory rewrite target (roughly six topics, preferably 400-550
characters; shorter valid summaries need no padding) from the existing storage
hard limits (12 entries, 950 text characters, 400 per entry). Accept a valid
snapshot above the target without buying retries merely to enforce the target.
Keep authorized nonempty unique source lists, kinds, checkpoints and archives.
Never truncate prose or citations in code. Apply the relaxed snapshot validation
also to explicit recovery of pinned older operations; leave their paid inputs
and published prefix artifacts unchanged. Update obsolete capacity feedback only
for a new unpaid attempt.

New v94 operations trigger capacity consolidation at 850 characters or nine
entries. After successful consolidation, require new information or capacity
growth, and normally at least eight new received observations or four further
decisions by that role before another soft-pressure consolidation. Growth to
900 characters or eleven entries bypasses the cooldown. Unchanged high memory
does not trigger polling. Pending chronological chunks above 24 observations
remain processable regardless of cooldown. Do not immediately reconsolidate a
just-processed snapshot merely because it exceeds the advisory target.

Provide exact per-entry and total lengths for whole-topic rewriting, together
with previous consolidation size and progress. A role request approaching its
actual byte envelope can request one additional consolidation of new/grown
memory, then rebuild context once. Required-data overflow and genuine hard-limit
violations still fail explicitly; source authority never becomes a soft rule.
Only attempt the extra rewrite when memory or the pending recent window can
shrink. A short summary with at most twelve pending records cannot reduce a large
fixed baseline. A just-consolidated, unchanged summary also retains its cooldown
unless capacity grows or more than twelve pending observations can be summarized.

Verification: 471 full regression tests and a final 66-test focused suite pass;
the latter includes one additional no-benefit pressure case. All eight stored
outputs from the latest failed operation now pass local snapshot validation,
including source authorization and checkpoint checks. Historical replay preserves
588 paid request hashes across 250 operations and 104 prefix artifacts. Four
independent synthetic Flash calls pass: three 910-character memories become
270, 259 and 255 characters, followed by no idle v94 consolidation. These probes
cost USD 0.007410516 and do not constitute a complete long-game acceptance run.
See [cost and deployment receipts](11-prefix-cache-and-cost-control.md#memory-targets-and-recompaction-2026-11-09-v94).

## Budgeted Working Views: 2026-11-09 (v93)

Role and memory requests now retain recent supplied observations and their exact
source bodies, while older originals are selected by current citations, location
and acquisition recency. Selection is not a truth or importance verdict. Scoped
list_sources searches/pages acquired records and actually received history;
read_sources returns exact character-ranged originals with origin, acquisition,
presentation and available numeric metadata. Partial indexes explicitly report
their totals and do not change permission to cite a previously acquired source.
Full observations, known records, memory citation lists and archives are intact.

Memory consolidation can use two read-only tool batches before its complete
snapshot. Retrieved older records never advance the processing checkpoint; only
the final supplied chronological observation can do so. Role source tools share
the existing two-round allowance with event tools. Tools neither inspect an unread
object nor create a new acquisition, sharing event or private-memory fact.
Engineering limits serialized request views and paginated tool responses, not
stored citation counts. See module 11 for implementation and measured verification.

## Unread Targets and Memory Sources: 2026-11-08 (v92)

Status: implemented, verified and deployed; receipts are recorded in module 11.

The latest continuation cited an unread document ID in an unresolved memory while
choosing to inspect it. The earlier native lookup returned unavailable, and the
inspection would execute only after decision validation. All four continuations
retained that unread ID. Source-count limits were already removed; authorization
correctly rejected the reference, but generic feedback did not identify it.

Source-error feedback now identifies the entry and invalid positions. If the ID
already appears in the role's inspect menu, it is returned as visible_but_unread,
with action_target_only permission. Unknown or foreign IDs are never disclosed.
At most twelve diagnostic entries are returned, with the complete error count;
this bounds feedback size and is not a limit on stored memory citations.

V92 distinguishes pre-action memory from a chosen future inspection and a heard
mention from the original document. A role can retain an unresolved lead by citing
the observation through which it learned the claim, and can still choose the
inspection. After successful execution, the acquired original is citable normally.
No citation is automatically replaced, action forced, prose filtered or hidden
document promoted into knowledge. Pinned paid tool stages remain reusable.

An old failed operation may have only generic source feedback. Before purchasing
its explicitly authorized retry, revalidate that stored failed result locally
with the pure role/memory validator to derive the current scoped details. Do this
only for unpaid attempts with generic memory_entry_sources feedback; leave both
historical rows and completed requests untouched. No model call or gameplay action
is needed to identify the already-visible offending target.

## Memory References without Count Caps: 2026-11-08 (v91)

Status: implemented, verified and deployed; receipts are recorded in module 11.

The user explicitly removed source-ID count limits. The former per-entry eight,
active-memory thirty and snapshot twenty caps were rough cost proxies; short IDs
are not source bodies. Updates and snapshots now preserve all necessary authorized
IDs without these count checks, including recovery of older pinned operations.
V91 removes numeric source limits from prompts and dynamic capacity metadata and
does not trigger compaction solely from source count. Text/entry compaction and
chronological pending-observation processing remain intact.

Source lists must still be nonempty, distinct and authorized for this role.
Initial facts, acquired originals, original observations and archived summaries
remain stored; no automatic citation truncation or semantic filtering is added.
Historical-body recall retains its separate 6,000-byte / 12-record budget; native
lookup retains its body budget. Requests now allow 51,200 dynamic / 90,000 total
bytes, following the separately approved increase from 40,000 dynamic bytes.
Many IDs do not automatically load every referenced body.

Published prefixes and the metadata used by completed requests remain immutable.
Historical source-pressure scheduling is retained only for pinned operations so
their paid stages reconstruct identically. New retries strip obsolete source-count
correction demands; completed calls replay their exact recorded feedback. The
current paused game is not resumed or rewritten by deploying this policy.

Real synthetic validation also exposed an empty-chunk checkpoint mistake: with
no pending observations, the model selected the last recalled historical record
as processed_through, rewinding progress. Checkpoint failures now supply scoped
allowed_processed_through values on bounded retries. An empty chunk recommends
null; a pending full snapshot requires the chunk's final supplied record. The
engine still rejects rewinds and skipped observations without altering memory.
Completed responses replay their original feedback exactly.

## Per-entry Source Recovery: 2026-11-08 (v90, historical)

Status: previously deployed; v91 supersedes the count limits described below.

The latest failure occurred during an ordinary role decision, not compaction.
An existing entry had seven citations; the model retained all seven and appended
three, producing ten in each of four attempts. All ten were authorized sources,
but the entry limit is eight even when total active memory has spare capacity.
This guard previously raised a generic error, so retries received no correction.

Entry-source failures now return the valid memory entry ID, source count, limit
and specific problems: invalid list, empty list, overflow, duplicates or unavailable
sources. No unknown source ID or source body is echoed. Persist the feedback under
the existing source-capacity version gate and replay each paid request's recorded
feedback verbatim. Older pins without this capability retain their old payloads.
An already-exhausted operation still requires an explicit user retry; historical
failed calls without feedback remain intact, and any new failed attempt receives
the correction before the next automatic retry.

V90 guides both role perspectives and compaction to use representative citations.
An upsert replaces text and citations rather than accumulating every repeated
occurrence. The model may separate independent topics within the existing total
limits or omit a lower-priority claim together with its citation. It must preserve
important contradictions and attribution and cannot retain unsupported claims by
dropping necessary citations. Engineering neither selects memories nor truncates
sources. All original observations, evidence and archived entry versions remain.

## Source and Temporal Integrity: 2026-11-08 (v88 implemented)

Source provenance is derived from immutable acquired records, initial facts and
received observations. A remembered interpretation never edits those originals.
Role and compaction contexts identify the origin of retained sources; a statement
about a document is still an attributed claim even when that document is also
cited. An unmentioned field does not establish an empty field. Free-form wording
is guided, not rewritten, filtered or reviewed by extra model calls.

New rule-version 5 cases retain numeric timestamps at compilation. Points carry
no duration. Intervals carry start/end, a clock basis, and engine-computed minutes.
Derived death bounds require both acquired endpoints; intersections are separate
from interval duration and containment. Only comparable clock bases are combined.
Roles receive only initial or acquired facts; the evaluator receives cited facts;
ending reconstruction may receive the complete frozen history. Legacy cases are
not parsed, backfilled or regraded. Spoken times remain claims.

Version 5 also records the subject of survival/death/voice timestamps and makes
the recording culprit's self-alibi explicit in frozen history, so victim survival
and playback of the culprit's voice have different subjects. The compact payload
retains the scoped origin index and temporal facts through memory snapshots;
known record copies keep their numeric metadata. Native source lookup still
returns only acquired originals. These fields do not disclose a hidden crime
time to investigators, and acquiring a time point does not invent its other
endpoint. General model interpretation is still fallible.

## Source-count Retry Correction: 2026-11-08

Status: implemented, verified and deployed on 2026-11-11.

The latest library spectator game stopped at `watch_1eec4920_74`,
`memory_A_94`: all four attempts produced six entries with 21 distinct sources,
over the snapshot limit of 20. Numeric feedback reached each retry, but the
model shortened text while retaining the same source set. No rejected memory
was committed and the game paused with its prior progress intact.

New capacity retries describe the specific exceeded dimension and required
reduction. Source pressure calls for fewer supported topics/citations, not just
shorter text; engineering never chooses or deletes a role's memories. V78 also
guides sparse snapshots toward 1-3 citations per entry, keeping 6 entries within
18 distinct sources; the existing hard limit remains 20. Fixed personal facts,
acquired records and original history remain separately available.

Persist each new call's exact `request_feedback`. Completed historical calls
without this field retain their original reconstruction, and new completed
retries replay their stored correction verbatim. Thus an existing failed v77
operation receives actionable feedback on explicit retry without altering its
immutable prefix, paid stages, attempt limit or original error receipts.

Verification: source-capacity and movement tests passed (43 tests together),
including new correction replay after restart, old paid-request reconstruction
without `request_feedback`, and an exhausted v77 operation that remains blocked
until explicit retry. A read-only replay of 66 operations in the affected game
matched all 133 recorded request hashes and reproduced its four final 21-source
failures (plus one earlier recovered 22-source rejection). A synthetic Flash
test with v77 and explicit fixture feedback succeeded in one call with 12 sources;
v78 produced 9 sources and then a valid role decision. Those three calls cost
USD 0.004733076 in total. No production transcript was sent by these probes.
Artifacts: `.local/verification/arrival-presence-20261108/`.

Deployment: all 347 regression tests passed in 125.384 seconds. After confirming
no in-flight work, the local service was backed up and restarted at 17:45:07 CST
on 2026-11-08 with v78. HTTP returned 200. Existing-column hashes for all 32 games,
1,600 calls and 793 operations were unchanged; `request_feedback` was added as
a nullable column without fabricating historical inputs. The affected game stays
paused for the user's explicit retry; its saved state and original v77 operation
remain intact. No claim is made that its next real retry has already succeeded.

## Conditional Investigation Reminder: 2026-11-08

Status: implemented, verified and deployed with v77.

V76 adds an optional reminder to the next normal role decision after two
completed decisions without new acquired material, a first visit/check or a
completed personal search. A newly received closure proposal can also trigger
one reminder. The third decision is early enough to precede the spectator's
twelve-step stagnation pause. Facts come only from that role's acquired records,
own exploration and received closure votes, never omniscient progress keys.
Speech, memory wording and another character's private actions cannot mark a
room explored. The counters describe investigation activity, not dialogue value.

The reminder names personally unvisited and visited-but-unchecked rooms, with
movement availability from the existing legal menu. It reveals no unseen
inventory, critical evidence, other characters' movements or proof-route gaps.
Ordinary roles compare further checking with continuing dialogue or closure;
concealment roles retain their own goals and response strategy. All legal choices
remain legal, including waiting and closure. There is no forced movement,
map-completion requirement, new DM call, self-review or automatic wake-up.

Suppress reminders during private conversations, running personal activities and
final submission. Repeat the same area reminder no more than once per four own
completed decisions; a changed area set or newly received closure proposal can
be highlighted sooner. No remaining areas means no reminder. Reminder delivery
and counters commit atomically with the role decision; failed attempts, technical
retries, tool continuations and idle polls do not consume or multiply reminders.
Older pinned operations retain their previous payloads and behavior. On upgrade,
new counters start with that role's first successful v76 decision.

`investigation_reminders.py` owns the pure preview and the atomic post-action
counter update. Received material resets the streak without marking its source
room personally explored. Identical re-deliveries and revisiting known areas do
not manufacture new investigation; an actual first personal check or completed
search does. The optional notice is the last dynamic role-context field. Both
role perspectives receive it, with distinct investigation/concealment guidance.

An initial synthetic v76 Flash trial exposed a follow-through gap: two roles
chose an unvisited area, but both then subscribed to waiting instead of continuing
their own investigation. In one bounded continuation, the character remained at
the new scene without examining its records. V77 therefore also explains that
movement does not inspect a room, own immediate action receipts do not wake a
subsequent wait, and a concrete self-directed next action uses `continue`.
Deliberate waiting remains legal; no engineering wake-up or forced action is
added. V76 stays immutable for its recorded calls.

Read-only replay of the latest completed v73 game matched all 173 original
request hashes before closure. Projecting the new counters onto its 82 historical
role decisions produced eight notices: all investigators received a pre-closure
reminder, and the second/third voters received another after a heard proposal.
This is evidence of trigger timing and information scope, not a prediction of
changed model behavior. No historical save or outcome was changed.

The final v77 real Flash trial used three paired synthetic investigator decisions
against v75, with identical dynamic input except for the reminder. One role chose
to move to the unvisited scene instead of waiting, and selected `continue` after
arrival. A five-step normal fair-scheduling continuation reached that role's next
turn; it inspected and acquired the missing original discovery record. Other
roles still chose document inspection or presentation, so the reminder is not a
guarantee of immediate movement or a measured improvement in full-game win rate.

The final trial used 21 Flash calls without failures/retries, 171,288 input tokens
(113,019 cache hits), 5,428 output tokens and USD 0.024672414. The earlier v76 trial
is also retained: 44 calls / USD 0.065056590, including one malformed action that
recovered through the existing bounded retry, and no scene-record acquisition
within its 16-step continuation. Total real validation cost was USD 0.089729004.
All prompts used wholly synthetic fixtures; production content was replayed only
locally without provider calls. Artifacts:
`.local/verification/investigation-reminders-20261108/`, with the final trial in
`v77/`. Case generation and evidence-grading files are byte-identical to their
pre-change versions.

Final acceptance: 336 Python tests passed in 126.302 seconds, including 21 new
reminder tests covering the third-decision trigger, four-decision cooldown,
received/unheard proposals, private activity, knowledge provenance, running work,
voluntary waiting/closure, unchanged menus, first-check/reset behavior, no idle
wake-ups, native-tool continuation and durable retry/restart replay. Under normal
fair scheduling the first notice appears at step 9, before the existing step-12
stagnation pause. All 81 previously published prefix artifacts remain unchanged.

After an idle-work check and SQLite backup, the local service restarted at
17:19:47 CST on 2026-11-08 with v77. HTTP returned 200; hashes of all 30 game
states, 1,464 call records and 724 operation records were unchanged. No production
game was resumed or regraded. Existing pinned operations retain their versions;
new operations use the reminder and continuation guidance.

## Context Optimization: 2026-11-08 (Implemented)

The [cost optimization design](11-prefix-cache-and-cost-control.md#approved-cost-optimization-design-2026-11-07)
owns the user-approved plan for request-local source deduplication, bounded
historical lookup and incremental memory/reasoning updates. Keep immutable
acquired snapshots, attributed testimony and interpretations distinct; deduplicate
source bodies without merging their acquisition histories. An unchanged summary
must not advance past unprocessed observations. All originals remain stored and
role-scoped. The current runtime uses authorized observation IDs introduced in v64 in source tables and native
`read_sources` with one batch / 8 IDs / 8 KiB of body text per decision. As of
v69, an omitted character offset defaults to zero; unknown or unacquired IDs
still return unavailable. The handler also supports omitted offsets in already
pinned requests without rewriting their tool definitions. Memory
updates use sourced entries and explicit upsert/archive/checkpoint fields;
replaced entries are retained in `memory_archive`. Null preserves both entries
and the checkpoint. Own spoken accounts use `self_claim`, distinct from another
speaker's `heard_claim` and from observed facts. Accepting an own claim preserves
its text and source; it cannot create acquired evidence or an action receipt.
At 9 entries or 700 characters, v66 and later run the existing
compaction path to merge topics into at most 6 entries / 699 characters; this is
separate from incremental turn patches. Belief/strategy updates are separate from memory and accept
an explicit clear operation without erasing fixed knowledge. The linked cost
module owns exact limits, compatibility and verification evidence.

The 2026-11-08 memory-contract fix aligns the accepted kinds with existing
`self_claim` observation provenance. It also accepts complete snapshots up to 699
text characters, below the 700-character pressure trigger, without truncating
model text. V70 explicitly documents all five kinds and raises the memory task's
output allowance from 700 to 1,400 tokens for entries, citations and JSON. The
writing target remains 150–250 characters. Older pinned prefixes remain unchanged;
their complete responses benefit from the runtime compatibility fix.

V75 also checks distinct-source pressure: at 24 active sources, consolidate to
at most 20, below the 30-source active limit. Both role perspectives see source
usage, remaining capacity and the existing 8-source limit per entry. The memory
task receives explicit snapshot limits. Capacity failures return persisted,
numeric correction feedback on the next bounded retry; rejected patches never
advance the checkpoint or mutate memory. Original observations, evidence, fixed
knowledge and replaced entry versions remain stored. Older pinned operations
keep their previous payloads and trigger behavior. See the
[source-pressure fix and verification](11-prefix-cache-and-cost-control.md#memory-source-pressure-fix-2026-11-08).

V83 retains these triggers, snapshot limits and source guards. After thinking
was enabled, real v82 memory calls exhausted their 2,424-token completion budget
on reasoning before returning a snapshot. New memory tasks allow 6,144 total
completion tokens, and genuinely truncated thinking retries can grow their
recorded allowance up to 8,192. This does not increase the 699-character active
snapshot limit, delete originals or advance a failed checkpoint. Completed calls
retain their actual request settings; the paused old-version step can recover
only after the user's explicit retry. See
[thinking truncation recovery](11-prefix-cache-and-cost-control.md#thinking-truncation-recovery-2026-11-08)
for deterministic, real synthetic and deployment evidence.

## Confirmed Area Evidence Exhaustion: 2026-11-11 (v124)

Status: implemented and verified; deployment recorded below.

Add `no_new_evidence: true` to a role's area entry only after that role completed
a successful search there, no intact hidden material remains there, and the role
has acquired every intact material currently in that area. Revealing material is
not reading it. Cancelled/failed work, oral reports, another role's search and
empty visible lists alone cannot certify completion. Carried private materials
are outside a room search, and destroyed/removed materials are not promised to
be recoverable. An actually searched empty room may be certified. This is a
positive assertion; omission means unconfirmed, not hidden-material existence.

For the current area, evaluate the actual local inventory and personal acquired
record set; new unread or hidden material withdraws the assertion. Do not remove
actions, force movement/closure, discard originals or rewrite speech. Explain the
field in both role perspectives: a repeated search cannot create a new document
or validate an unsupported spoken detail. Re-reading known originals uses the
existing source tools. The role may still investigate changed conditions.

Freeze a confirmed result in the existing personal area snapshot on actual
observation. Away from the area, expose only that last-observed assertion, with
the existing `snapshot_current=false` distinction; do not update it from unseen
remote changes. A received material-opening notice suppresses a stale assertion.
Legacy remote snapshots without this proof remain unconfirmed until observed;
old current-area searches can be recognized from their actual completed tasks.
Current/last-observed wording must match in role context and the shared player /
spectator exploration display. No hidden IDs or counts are added to context.

Version only the new role projection and instruction; preserve historical paid
requests, immutable prefixes and the memory task's input contract. The feature
adds no model calls. Tests must cover reading after discovery, actor isolation,
new/hidden/carried/removed materials, stale remote snapshots and old requests.

Verification artifacts: `.local/verification/area-evidence-v124-20261111/`.
Sixteen new backend tests pass; 61 focused checks and the full 704-test regression
suite pass. Three new JavaScript tests cover current, historical and absent
markers. Headless Microsoft Edge at 1440 and 390 pixels confirms both status
wordings in the real spectator role view, expanded-panel preservation, no page
errors and no horizontal overflow. The test DOM fixture initially lacked browser
globals; fixing the fixture required no production renderer change.

The new role payload includes the marker even after context packing/budget
selection. Historical role projections omit it even if a save contains a new
personal snapshot; legacy memory-task inputs remain unchanged. Ten completed
v123 historical requests replay locally with matching hashes and validation.
All 143 preceding prefix manifest entries remain unchanged, and the 144-artifact
contract gate passes. No production transcript is sent to a model.

Two bounded synthetic Flash probes, one investigation and one concealment role,
receive a fully searched/read current-area marker and both independently choose
movement rather than another search. Both outputs validate, with two calls total,
no retry and USD 0.005149584 reported usage. This verifies marker delivery and two
actual decisions, not a guarantee of useful behavior across a complete game.
No model call is added to ordinary gameplay by this feature.

The latest paused v123 operation's four failed requests also replay with unchanged
hashes and validation results. Its existing source-kind and message-wait contract
failures remain preserved; this feature does not silently rewrite the paid input,
clear the error or automatically retry it. New role steps receive the v124 field.

Deployment: `palter.service` restarted at 2026-11-11 01:15:28 CST, PID 839536 to
852473, after checking that the current game was paused and no call/operation was
in flight. Before/after read-only hashes match for 44 games, 5,732 AI calls, 2,703
AI operations and two legacy model-call records. The latest game remains paused
at step 288, revision 340, with its prior error intact. Root and three JavaScript
assets return HTTP 200; the served exploration renderer contains the new marker.

## Exploration and Acquisition Sources: 2026-11-06 (Implemented and Verified)

Maintain a per-role investigation map derived from actual movement, personal
checks and completed searches. Distinguish unvisited, visited without checking,
partly investigated and currently visible materials acquired. The last state
does not establish that no hidden evidence remains. Initial script experiences
are not gameplay exploration; receiving a record from another room does not
mark that room visited. Current visible records are scoped to the role's current
location; remote views use only last personally observed snapshots, never live
hidden world state. A received notice about newly available records can flag a
revisit without exposing undiscovered contents. Cancelled searches do not count.

Evidence acquisition is projected from the recipient's event-linked observations:
personal inspection, collection/copy, physical receipt, presentation by another
role or self-authored document. Legacy copied `via`/`acquired_event` values must
not mislabel received presentations as personal inspection. Preserve original
content and historical saves. Heard claims stay attributed in observations and
sourced memory summaries, optionally cited as testimony; no speech promotes a
document into acquired evidence or completes exploration.

V62 role and memory contexts include this map and acquisition metadata;
older pinned operations retain their original context. Model guidance distinguishes
local exhaustion from an exhausted investigation while retaining voluntary
closure. Also summarize presentations personally witnessed reaching other roles
to avoid repeatedly sharing records with the same audience. No hidden holdings,
new review calls, prose filters, forced exploration or altered win rules.

`exploration.for_role` projects `unvisited`, `visited`, `partial` and
`visible_acquired`, personally checked materials, completed-search count, latest
action/observation time and locally visible unread records. Action-time snapshots
retain last-seen inventories for other locations. Unknown legacy inventories stay
unknown. Structured follow-arrival receipts count actual movement; unsupported
legacy follow inference remains conservative. Visible acquired records never
mean all hidden records have been discovered. The former ambiguous
`available_unread_records` field becomes `currently_accessible_unread_records`
only for v62. Role and memory prefixes explain the distinction and preserve
voluntary closure rather than enforcing a full-map checklist.

`evidence.acquisition` uses the recipient's original evidence observation to
identify source method, presenter and usable observation reference. V62 projections
omit the contradictory legacy `via` and `acquired_event` fields; stored old
snapshots remain intact. New presentation acquisitions also persist the correct
receiving event and presenter. Initial personal memories remain legitimate and
separate from investigation visits; testimony remains in attributed dialogue and
sourced summaries, optionally usable in conclusions. `witnessed_receivers` lists
only deliveries this role actually witnessed, including other presenters.

Verification: 11 new exploration/source tests and all 226 Python tests pass, as
do 6 frontend checks and 6 new browser checks for exploration, provenance,
disclosure, scoped views, retained expansion and mobile layout. Local read-only
projection of the latest ended game correctly leaves the crime scene unvisited
for every role and identifies the culprit's playback document as received from
another character; the saved state is unchanged.

Three actual Flash requests on one independent synthetic fixture completed for
USD 0.006857172. Despite another role's claim that the scene had been searched,
the investigator selected `move:r2`, then `inspect:c2`, acquiring the missing
discovery record. A subsequent memory compaction retained the other role's claim
as attributed testimony and distinguished unexamined traces from personal checks.
Summaries remain lossy; this targeted receipt is not a full-game completion or
win-rate claim. Artifacts: `.local/verification/exploration-20261106/`.

Deployment: v62 loaded by local `palter.service` at 23:26 CST on 2026-11-06
(PID 665563). A consistent backup was saved as
`.local/backups/pre-exploration-20261106-232601.sqlite3`; all 28 game-state hashes
remain unchanged. Live homepage/API/assets returned HTTP 200 and asset hashes
match the workspace. The authenticated ended-game view returns the expected
unvisited crime scene and actual presentation provenance. The six existing
ensemble browser checks also pass. Refresh to see progress and sources in old
saves; future unpinned decisions use v62 while old endings remain unchanged.

## Evidence Sharing Receipts: 2026-11-06 (Implemented and Verified)

Separate acquired evidence, spoken disclosure, actual presentation and its
recipients. New presentation events record channel and recipients at execution;
the presenter does not acquire social credit merely by receiving a copy. Public
presentation excludes participants currently in private conversations and does
not backfill when they return. Repeating a presentation can reach new recipients.
Contribution credit remains separate from delivery and never supplies an
`already_shared` flag. Neither delivery nor a speech claim establishes truth.

Role context and player material cards summarize only presentations/disclosures
the role actually observed, including whom that role has personally shown the
record. A person not shown a record may have obtained it independently. Only the
spectator truth panel may combine all roles' actual acquired records. Legacy
saves derive delivery from existing event-linked observations without mutation;
missing channel metadata stays unknown unless a recorded private-chat interval
establishes it. New context is versioned so pinned operations keep old payloads.

`evidence_sharing.ledger` derives separate presentation and disclosure receipts.
`for_role` exposes `spoken_by_me`, `shown_by_me`, `shown_to`, `not_shown_to`,
`recipient_history_complete` and the observed presentation count for acquired
records only. The omniscient projection additionally exposes actual `known_by`
and individual receipts. New share events persist `facts.channel` and
`facts.recipients`. Missing legacy receipts remain explicitly incomplete.
Version 61 changes `focus.already_shared` to actual self-presentations and adds
the scoped status map. Pinned v60 and earlier model contexts retain their old
shape/semantics for recovery; historic prefixes remain unchanged.

Verification: 8 targeted boundary/compatibility tests; all 215 Python tests and
6 frontend tests pass. Four new browser checks cover both player and spectator
cards, actual recipients, disclosure-only status, retained expansion and mobile
layout; the existing six ensemble browser checks also pass. Two real Flash
decisions on independent synthetic cases both chose actual presentation: one
after oral disclosure only, one repeating delivery for a returned private-chat
participant. Both intended recipients acquired the record. Two requests cost
USD 0.001950936; this is a feature probe, not evidence of improved game win rates.
The latest production replay was inspected locally/read-only: playback record
was disclosed but not presented; end-face photos reached only A and B. Its hash
was unchanged. Receipts: `.local/verification/evidence-sharing-20261106/`.

Deployment: local `palter.service` restarted with v61 on 2026-11-06 at 22:09 CST
(PID 652963). Homepage, session API and served assets returned HTTP 200; asset
hashes match the workspace. All 27 game-state hashes match the consistent backup
`.local/backups/pre-evidence-sharing-20261106-220913.sqlite3`. Refreshing the page
shows the receipt status for existing saves; ended games keep their old results.

## Current Runtime: 2026-11-05

Each role acquires its own immutable evidence snapshots. Objects separately track custody, hiding, protection and destruction; later handling cannot erase what was observed. Actual handling can leave independently discoverable traces. Before a long history leaves recent context, ensemble_memory processes every unsummarized observation in chronological chunks of at most 32, with the prior sourced summary. Authoritative records and frozen role baselines are retained. Summaries are lossy interpretations, not replacements for evidence.

Implementation: [complete playable runtime](17-complete-playable-runtime.md). Verification uses `tests/test_ensemble.py`, the multiplayer browser walkthrough and fresh provider receipts listed there. The design alternatives below retain their proposal scope; older implementation sections describe legacy saves.


References: [Conventions](../AGENT.md), [Glossary](../GLOSSARY.md), [Relationships](05-character-relationships.md).

## Purpose and Scope

Represent actual history and current world state separately from what each character remembers, knows, believes, and can discover. Scene actions create evidence or affect its condition, location, custody, and accessibility.

These mechanisms support multiple scenarios. Bodies, bloodstains, and incriminating documents are investigation examples; other stories use relevant objects, observations, resources, or secrets.

## Shared Concepts

| Concept | Meaning | Investigation example |
| --- | --- | --- |
| Initial memory | Experiences and understanding present at the start | Remembering an earlier threat |
| Event memory | Experiences or information acquired during play | Entering a room and finding a body |
| Relationship memory | Initial connections, current attitudes, experiences of change | Beginning to doubt a trusted friend |
| World state | What actually exists now | A stained sleeve and a button on the floor |
| Knowledge and beliefs | Individual information and interpretation | Noticing the stain but not the lost button |
| Visibility | Conditions for acquiring information | An inspection could reveal a trace |

Existence, discoverability, and recognition are distinct. Relationship experiences can refer to an event memory while recording its effect on attitudes.

The [system DM](10-system-dm-and-deception.md) presents each recipient's actual perceptions. Record the underlying occurrence consistently, then derive what each character heard or saw under its visibility conditions. Event memory is based on that character's acquired view and sources, while interpretation remains a separate belief.

A character can truthfully remember hearing an inaccurate statement. The act of speaking and its observable delivery really occurred; the statement's asserted content need not be true.

## Evidence Sources and Handling

Evidence can occur in locations, on characters, in carried objects, or in observations and accounts. Missing, moved, or damaged objects can provide information.

| Illustrative action | Possible consequence |
| --- | --- |
| Inspecting or moving a body | A stained sleeve or changed body position |
| Knocking over a cup | Fragments or effects on nearby objects |
| Catching clothing on an obstacle | A detached button or torn cloth |
| Taking a private letter | Changed custody and an empty original location |

Creators may be unaware of traces. Known evidence may be handleable or restricted by scenario conditions. Awareness does not establish access, permission, or success.

Handling can genuinely remove or change evidence. Actual results, remaining traces, and the actor's beliefs are separate questions. Removal does not rewrite history or erase earlier observations.

## Discovery Scope Proposals

| Scope | Recipients | Developments |
| --- | --- | --- |
| Public discovery | Observable content is made public; actual awareness follows participation and receipt | Shared discussion, different interpretations, or later questions from absent characters |
| Individual discovery | Initially only the discoverer | Concealment, disclosure, or targeted sharing |

Scope does not determine custody or handling rights. Characters may independently discover the same object at different times.

Participants in private conversation do not automatically learn about concurrent outside discoveries. Returning does not silently append missed public events to their memories. They may ask someone what happened and then acquire that person's account. Whether explicit public-history review is available remains open.

A public report of a button in the study does not reveal its owner or complete origin. A spoken account, independent inspection, and verification remain distinct. Private sharing follows the [invitation and agreement procedure](03-communication.md).

## Logical Clues and Undiscovered Information

Logical clues arise from timing, incompatible statements, custody, and other relationships among facts. A character can possess component facts without recognizing their significance.

Distinguish evidence that was removed, evidence still present but unobserved, acquired observations whose connection remains unrecognized, and conclusions characters suspect or have explained.

An unrecognized inference has not been physically destroyed. Sound deductions should be possible from available facts without requiring a predefined answer item. Recording and validating deductions remain design questions.

## Scenario Handling Budget Example

The user proposed attempts to disrupt at most one evidence category per day in an investigation scenario. This is a candidate scenario budget, not a universal game limit.

The actor scope, category definitions, affected item count, retries, and whether a failed attempt spends the allowance remain open. One category must not silently become one individual clue.

## Events and Publication

Evidence may change during an expedition, gathering, emergency, journey, nighttime window, or other relevant opportunity. See [World events and scene actions](04-world-events-and-actions.md).

Existing knowledge records what was observed at that time. Later changes require new observations or communication. A public inspection may reveal a missing letter or damaged cabinet while leaving its actor unknown.

A returning character can observe the current scene under normal visibility conditions without thereby learning the unobserved sequence that produced it. Newly hearing about an earlier event creates a later learning experience; it does not turn the character into an original witness.

## Illustrative Sequence

1. B notices a stained sleeve but misses a lost button.
2. B attempts permitted evidence handling; conditions determine results and feedback.
3. C finds the button and learns its observable properties, with ownership still to investigate.
4. Earlier witnesses retain their experiences. New discoveries can change interpretations without rewriting history.

## Open Questions

- Automatic observations versus deliberate inspection and recognition.
- Discovery scopes and later sharing for each clue.
- Handling requirements, retries, costs, residual effects, and feedback.
- Incidental effects of broad actions on unknown traces.
- Scenario budgets and restricted evidence.
- Deduction validation and private understanding versus demonstrated conclusions.
- Publication and interactions among protection, movement, and disruption.

## Legacy Demo 01 Implementation and Verification

palter/ai_world.py and palter/storage.py preserve actual effects and acquired observations with event IDs. AI memory interpretation uses only that recipient's acquired records and initial baseline, separately from frozen initial memory. Private participants miss outside events, and ending a chat does not backfill history. General evidence destruction, trace physics, and logical-proof validation remain designs. See [AI runtime](15-ai-runtime.md) for actual verification.

The confirmed next priority is progressive deduction. [Demo 02](16-demo-02-deduction.md)
proposes case-backed clues, stable attributed testimony and player-authored
hypotheses. A clue's observation must not silently include its solution, and a
role's later summary must not erase its earlier false statement. Sufficient
evidence combinations and alternate valid proof paths must be checked before
claiming that a case is solvable. These remain design work.


## Legacy Demo 02 Implementation: 2026-11-05

New investigation games now implement acquired case records, stable attributed statements, private hypotheses and bounded proof-route validation in [Demo 02](16-demo-02-deduction.md). Hidden author provenance is not delivered as an observed source. General physical evidence destruction and unrestricted proof reasoning remain outside this slice.


## Sourced Active Context: 2026-11-06

New ensemble operations use v47 projections with explicit self-claim/heard-claim
provenance, selected original-source recall, visible object state and actual own
action receipts. The previous summary is an interpretation, not authority. Three
recent relationship experiences per counterpart (within 2,400 bytes), twelve
recalled observations (within 6,000 bytes), and a recent window retaining every
uncompacted observation bound repeated history. Full acquired snapshots, original
observations and relationship histories remain stored. Evidence referenced by an
observation is not duplicated in prompt text. This is lossy active-context
selection, not deletion, unlimited semantic retrieval or a fixed total token cap.
See the completed-game fixes and verification in [Spectator mode](18-spectator-mode.md).


## Culprit Self-knowledge and Strategy: 2026-11-06

New ensemble role decisions use a private goal/knowledge-specific instruction
variant. A role with the fixed avoidance goal and knowledge of its own crime
stores `strategies[actor]` (situation, plan, acquired sources), not a private suspect
hypothesis. Its script and memory retain factual self-knowledge, while an outward
lie remains an attributed claim. The variant does not receive other characters'
private evidence, thoughts or missed conversations. Investigator beliefs remain
separate. Spectator panels show strategy and memory explicitly; old generated
beliefs are labelled historical output instead of reinterpreted as strategy.
