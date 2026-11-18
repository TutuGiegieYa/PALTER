# Time Reading and Background Activity

Status: Participant pause/reading, background recovery and separate all-AI spectator scheduling implemented.

Last updated: 2026-11-11.

## Distinct Scheduling Terms: 2026-11-11 (v125)

Status: implemented, verified and deployed on 2026-11-11.

Separate consecutive-wait eligibility from message-only subscription admission
without changing either rule. V125 renders `passes_consecutive_wait_check` for
the frequency check and `message_only_subscription_allowed` for the independent
message-only guard. A true frequency result does not grant overall wait permission.
Use `event_candidates`, `supported_modes`, `frequency_blocked_event_ids` and
`empty_subscription_allowed` to make each list or boolean's scope explicit.
Both role perspectives, listener-tool parameter descriptions, dynamic decisions
and retry feedback use the same names. Concrete mixed OR subscriptions retain
their existing exception to the message-only guard, but not to the frequency rule.

`scheduling_terms.py` projects only model-facing input at the gateway, after
retry reconstruction and tool-context refresh and before byte-budget fitting.
The scheduler, validator, state, outputs, native tool receipts and stored raw
errors remain unchanged. Published historical prefixes and paid requests retain
their exact inputs. New operations use v125; pinned old operations keep their
original terminology. Verification artifacts belong to
`.local/verification/scheduling-terms-v125-20261111/`.

Eight new tests cover all four combinations of frequency/admission conditions,
mixed OR and empty subscriptions, unchanged validation, both perspectives,
native-listener continuations, correction feedback and restart reuse. Together
with scheduling/recovery coverage, 48 focused tests pass. Four synthetic real
Flash decisions (investigation/concealment, with/without a previous observation
wait) pass on their first call, costing USD 0.004583976. They do not establish
long-game behavior or complete-game acceptance. Fourteen paid calls across the
actual v123/v124 failed/recovered operations retain exact request hashes and
validation outcomes in offline replay; all 144 prior prefix artifacts are intact.
No production transcript was sent to a provider or game advanced by verification.

The first discovery run used the wrong package root and could not import the
five HTTP tests. Its other failure was a historical dialogue test comparing the
listener description literally. Update that check to preserve the entire schema
while permitting this one intentionally renamed input reference; the new prefix
test independently checks the description. Preserve the initial failed log and
rerun with `unittest discover -s tests -t .`.

Final regression: all 712 tests pass in 185.102 seconds, including the five HTTP
tests. The 145-artifact publication gate passes. Output schemas, model settings,
token limits, event IDs and scheduler checks are unchanged; only new model input
names, their descriptions and generic correction references differ.

Deployment: the idle service restarted at 2026-11-11 01:54:38 CST, PID 852473 to
864011. There were no pending calls/operations or active spectator games. Before
and after hashes match for all 45 games, 5,779 AI calls, 2,725 AI operations and
two legacy model calls. The service is active/running; the homepage and three
application scripts return HTTP 200. No production game was resumed or advanced.

## Last Available Role and Bounded Wait Recovery: 2026-11-10 (v123)

Status: implemented, verified and deployed on 2026-11-11; complete-game acceptance remains open.

Do not let the last available role enter a pure message wait when all other
unfinished participants are waiting. Cover next_observation, its message-only
listener aliases and an empty target list (direct contact). Prevent an empty
stationary continuation from becoming an equivalent idle loop. Real action,
invitation, conversation and other authorized event subscriptions remain valid;
mixed OR subscriptions with a concrete target are not message-only waits.
Keep the existing consecutive-next_observation rule independently. Show only
the role's current action permissions, never other participants' hidden wait
states, private purposes, locations or event IDs. Rebuild after tools and check
again at commit; per-game execution is serialized.
Final submissions do not create a new wait and remain valid for the last role.
Departure is likewise terminal only before a final submission is required.
The dynamic menu explicitly distinguishes continuing with an action/response
from waiting on at least one concrete event. Consecutive-observation exclusions
remain separate: a permitted mixed OR target must not be falsely marked forbidden
by the message-only guard.

For all-AI spectator runs, retain normal progression of running work, queued
dialogue, due world events and genuine fixed deadlines. When no role is ready
and no autonomous work can advance, finish pending scoped DM reviews first,
then interrupt only one subscription so its owner can reconsider. Do not mark
its target event complete, create facts, choose movement or force speech. Prefer
the longest-waiting eligible role, with stable fair ties. In one no-progress
episode, reconsider each role at most once; if all have reconsidered without
actual progress, pause visibly. Use existing grounded progress accounting to
reset the episode, not new prose or repeated waiting. Ordinary manual pauses,
retries and clock advancement do not reset it; explicit resume after this
specific stalled pause starts a fresh bounded round. Human input, error pauses,
spending limits and legacy pinned operations keep their existing behavior.

Implementation uses `wait_progress.py`, version-gated role scheduling, refreshed
native-tool contexts and spectator control. A running activity's next tick is
considered before a later wait timeout. Recovery resolves only the selected
subscription as cancelled, with a private receipt and one queued reconsideration;
it never records the watched event as successful. The Web pause reason explains
the exhausted reconsideration round and retains the explicit Continue control.

Verification artifacts: `.local/verification/message-wait-v123-20261110/`.
Twenty-one focused tests cover admission, empty waits/continuations, aliases,
mixed OR targets, real actions, final submissions, scoped context, native tools,
stale permission checks, paid retry reuse, normal deadlines, one-role wakeup,
bounded cycling, progress reset, manual resume and old contracts. Initial full
regression exposed the final-submission exception; it was corrected before
deployment. Headless Edge checks at 1440 and 390 pixels confirm the new pause
message, enabled Continue control, no horizontal overflow and no page errors.
Historical v121/v122 production requests are replayed read-only; no production
transcript is sent to a model and no production game is advanced by verification.

Two bounded synthetic Flash probes passed: both investigation and concealment
roles chose actual inspections under the restriction. A separate fresh test-owned
game ran 22 steps / 50 calls and paused at the USD 0.10 admission budget
(USD 0.0811878 reported usage). It had nine recovered role-validation failures,
including repeated message-only waits; it did not reach closure. The clearer
dynamic permission was then rechecked against one troublesome synthetic state:
two calls, one corrected rejection, an actual outward response and continuation.
This confirms bounded correction, not elimination of model mistakes or whole-game
acceptance. Across these probes and the fresh run, reported cost was USD 0.08580018;
no budget extension or automatic resume was used. Preserve all failed receipts.

Final regression: 688 tests pass; 52 focused tests cover the final scheduling and
terminal-action changes. Both frontend tests and the 143-artifact contract gate
pass. All 142 historical prefix manifest entries are unchanged. Five v121 paid
requests and four v122 paid requests retain their request hashes and validation
results in offline replay. The earlier v121 operation had since been recovered
by the user; its initial failed round and separate capacity-maintenance stage
are checked independently, rather than misrepresenting its later paid reply as
part of the original failed round.

Deployment: `palter.service` restarted at 2026-11-11 00:29:16 CST, PID 819724 to
839536. The user resumed their game during verification; it later paused naturally
for existing stagnation at step 272, revision 316, with no error and no in-flight
call. The deployment pause check sent no command because it was already paused.
Only then was the service restarted. Before/after read-only hashes match for all
44 games, 5,683 AI calls, 2,685 AI operations and two legacy model-call records.
The latest game remains paused with the same state. Root and three JavaScript
assets return HTTP 200; the served spectator asset includes the new pause reason.

## Current-Action Completion: 2026-11-10 (v121)

Status: implemented; regression, bounded real-model probes and paused-operation replay verified.

`own_activity` means completion of this decision's actual action, not only work
that happens to take time. Bind it to the exact event returned by the action
executor. If that event starts an ongoing activity, retain its existing terminal
subscription. Otherwise its synchronous result is already recorded: enqueue one
next decision, without manufacturing a task, wait receipt, DM review or recursive
model call. Speech/gesture-only replies may bind their actual outward event; an
empty stationary wait has no completion event and cannot wake itself. Other wait
targets retain OR semantics, visibility, interruption and deadline rules. Failure
and cancellation remain distinguishable from success. No earlier activity can
satisfy a new action's subscription.

New contexts explain the unified contract. Historical paid request bytes stay
unchanged; a pinned failed reply using an immediate action with own_activity may
validate under the compatible runtime behavior on explicit retry. Raw failed
outputs are never promoted automatically. Invalid targets receive scoped field,
actual-action and allowed-target information instead of an unqualified error.

Verification artifacts: `.local/verification/own-action-v121-20261110/`.
The 87 focused tests pass. Full discovery ran 659 tests: 654 passed, and the five
HTTP tests passed separately with local socket access; the original full run's
five sandbox socket denials are retained. Frontend checks and the 141-artifact
publication gate pass. The four original failed outputs from
`watch_a732ede7_34` all validate locally, with all four paid request hashes
preserved. Applying the last output only to an isolated in-memory copy acquires
the inspected document and queues exactly one continuation. The production
failure and paused game are untouched; retry still requires the user's action.

Two synthetic real Flash calls with thinking disabled selected `own_activity`
for inspection and search respectively. The inspection queued one continuation
after acquisition; search waited for its real completion. Both passed the actual
validator and executor, at a total logged upper cost of USD 0.00140676 within a
two-call / USD 0.10 limit. No production game data was sent to the provider.
These bounded semantic checks do not establish whole-game reliability.

Deployment: `palter.service` restarted at 21:54:12 CST on 2026-11-10 from PID
779586 to 798760 using the project Conda interpreter. The service is active/running
and the homepage plus three application scripts return HTTP 200. Before/after
hashes match all 44 games, 5,157 AI calls, 2,421 operations and two legacy model
calls. There were no pending calls. The latest game remains paused at revision 35
/ step 7 with the existing retryable failure; no game was advanced or retry sent.
The bounded semantic probes and service restart do not establish complete-game
acceptance. New operations use v121; older operations keep their pinned prefixes.

## Consecutive Observation Waits: 2026-11-10 (v119)

Status: implemented, regression-verified and deployed at the user's explicit restart request.

The user replaced the broad rolling wait limit with one event-specific rule:
a role cannot wait for `next_observation` in two consecutive committed replies.
Only that target is restricted. Waiting for an authorized activity, invitation,
private conversation, custom event or phase transition may occur consecutively.
One committed reply without a `next_observation` subscription restores access,
even when it waits for a different event. Merely registering a listener does not
count; entering a wait through a listener that includes `next_observation` does.
Mixed target lists follow the same rule. Other event permissions, deadlines,
response obligations and DM validity checks remain unchanged.

Keep one per-role observation-wait flag, separate from legacy all-wait history.
Retries, tools, other roles, cancellation and timeout do not advance it. New
accounting starts with the first v119 committed reply; do not infer the previous
target from legacy boolean flags. Surface the restricted targets in scoped context
and preserve them after tools. Preserve published prefixes and pinned operations;
v112-v118 retain their historical three-reply rule. Do not add any other frequency
limit, forced action or prose rewrite.

Verification artifacts: `.local/verification/observation-wait-20261110/`.
The 86 focused tests pass, covering direct and aliased waits, mixed targets,
other-event repetition, per-role persistence, timeout, tool continuations,
bounded retry and paid-stage reuse, and legacy policy isolation. The publication
gate passes all 138 artifacts. Initial failures were confined to legacy test
fixtures: one silent continuation intentionally remains invalid under the old
rule, and a restarted legacy test needed to retain its old default version for
the next operation. Their original output is retained. No real-provider calls,
production writes or service restart were performed for this change. The prior
combined candidate's incomplete whole-game acceptance remains outstanding.

Final verification covers all 634 discovered tests: 629 passed in the full run,
and the five HTTP tests passed separately in 3.135 seconds with local socket
access. The full run's five errors were sandbox socket denials, not assertions;
its original output is retained. An earlier invocation omitted the test package
root and is also retained. The 64 legacy request comparisons preserve complete
payloads and hashes across histories, roles and context options. All 137 prior
published artifact hashes remain unchanged. These are deterministic regression
checks, not real-model whole-game acceptance or deployment.

Deployment: the user explicitly requested restart after the verification report.
At 17:39:26 CST on 2026-11-10, `palter.service` restarted from PID 651146 to
739168 using the project Conda interpreter and v119. The unit is active/running;
the homepage and three application scripts return HTTP 200. Before/after hashes
match all 43 games, 5,110 AI calls, 2,396 operations and two legacy model calls.
There were no pending requests; the latest game remains paused at revision 309 /
step 257 with its existing stagnation reason. No game was advanced and no model
request was sent. Receipts: `.local/verification/restart-v119-20261110/`.
This user-authorized deployment does not mark the prior whole-game acceptance
as passed. Pinned operations continue using their historical versions.

V113 adds explicit allowed scheduling modes and preserves wait corrections
through unrelated JSON errors. The rolling limit and its accounting are unchanged.
See [role correction continuity](11-prefix-cache-and-cost-control.md#role-correction-continuity-2026-11-09-v113)
for compatibility, retry settings and verification.

## Rolling Wait Limit: 2026-11-09 (v112)

Status: implemented, verified and deployed.

The user chose at most one wait in any three consecutive replies by the same
role. Count successfully committed final role decisions, not other roles, DM
calls, source/tool continuations, failed attempts or model retries. After a wait,
two non-wait decisions are required before another wait. Cancellation, timeout,
new messages, pause/resume and restart do not clear that history.

Any `next_decision.mode=wait` consumes the allowance, regardless of the target or
whether the reply also speaks/acts. A completely silent `choice=wait` with
`mode=continue` also counts, so an empty continuation cannot bypass the limit.
Stationary speech or a gesture with `mode=continue` remains a non-wait reply.
No semantic prose filter, forced action, forced movement or invented fact is used.
The role sees the remaining restriction before generation; an invalid response
gets field-specific feedback through the existing bounded retry mechanism.

Keep only the last two committed wait flags per role. Apply this historical rule only to
v112-v118 opted-in operations, including after native tools. Older pinned
requests preserve their original context and validation. Existing subscriptions
continue to resolve normally; counting begins on the first new-version decision
without guessing whether an older stationary action was speech or waiting.
Submission, fixed-event completion, timeout and DM semantic authority are retained.

Verification receipts: `.local/verification/wait-frequency-20261109/`. The 79
focused regressions pass, including per-role rolling boundaries, cancellation,
timeout, persistence, native-tool continuation, scoped validation feedback and
retry/restart accounting. An initial full run found an older minimal tool entry
without scheduling context; the continuation now preserves its optional context
contract. That initial failure is retained in `full-tests.txt`.

Six synthetic real Flash decisions cover investigation and concealment roles
after an explicitly seeded prior wait. Both supplied two non-wait decisions,
then received the restored allowance; no failed attempts or extra review calls
occurred. Their total cost was USD 0.006762408. These probes verify quota handling,
not completion or narrative quality of a whole game. A read-only reconstruction
of the latest game's 141 completed background operations matches all 286 paid
request hashes; all 130 previous prefix artifacts remain unchanged.

Final full regression passes 589 tests in 164.497 seconds. The focused compatibility
recheck passes 19 tests; the publication gate verifies all 131 artifacts. Deployment
at 21:21:04 CST starts PID 637693 with HTTP 200. Before/after hashes match all 41
games, 4,065 AI calls, 1,895 operations and two legacy calls. No request was pending;
the latest production game remains paused at revision 164 / step 141. New-version
reply counting starts when the user continues; no production play or model call
was performed by verification or deployment.

## Repeated Wait/Cancel Loop: 2026-11-09 (pre-v112 diagnosis)

Read-only inspection of `b54c4bb6799179432c18e2f3` found a model/DM scheduling
cycle. Roles expected a fingerprint/contact-trace examination mentioned in speech,
but state contained no running activity, no custom tracker and no private session;
its only recorded search was already completed. A repeatedly chose silent wait
on `next_observation`. Every new generic subscription sets `review_pending=True`,
causing an initial DM validity call even without a new scene fact. The DM cancelled
these waits using previous cancellation receipts and the expectation of no near-term
news. Cancellation records an own `wait_result` and unconditionally enqueues the
owner; the role then creates another wait. This is a cancellation wake/re-arm
cycle, not evidence that another actor's wait receipt triggers `next_observation`.

Operations `watch_b54c4bb6_156` through `_163` contain eight role decisions and
seven DM reviews, costing an estimated USD 0.025268928. One role reply chose
`mode=continue` while its executed action was still `wait`. Other roles retained
60-second observation waits: all-waiting spectator playback can advance directly
to those deadlines, wake the roles and repeat. The latest state was paused by
stagnation protection at step 141 / revision 164, with no background error.

V111 only changes outward speech guidance; it did not prevent this scheduling
cycle. The user subsequently selected the rolling frequency policy above for
v112. Broader semantic distinctions between wait bookkeeping and scene evidence
remain separate from this bounded change. Preserve legitimate timeouts, one real
wake receipt, actual private conversation/activity completion and DM authority
over semantic validity. Do not invent the expected examination, force scene
actions or end the story to escape the loop. No production writes, external model
calls or resume occurred during this diagnosis.

## Event Background and Citation Recovery: 2026-11-09 (v106)

Status: implemented, verified and deployed.

The new v105 game stopped in dm_public after all four attempts rejected a
wait-validity citation. The role had just spoken and inspected a document before
subscribing to next_observation. Its review checkpoint was already at the end of
its observations, so selective review supplied no received_records. The DM still
saw its utterance in the speech-assessment section and cited it. That citation
was absent from the event-specific whitelist. A second attempt cited earlier
received utterances with the same failure. The request used about 10 KB of
dynamic content, so this was a projection/authority mismatch, not budget pressure.

V106 keeps background_records separate from received_records. The former adds
up to six recent pre-review receipts under a 2,000-byte target, plus previously
cited support. Every record remains exact and belongs to that creator. Source
bodies are pooled without merging occurrences. observation_index and the event's
review_range.from_exclusive/through distinguish prior context from this event's
new chronological chunk, including when multiple trackers share a creator view.
Background can explain a waiting purpose or an acquired document; it cannot
trigger a fixed next-observation subscription or advance the review cursor.
The existing timeout, scoped dirty check and engine-owned wake conditions remain.

New source feedback identifies the event and creator, invalid submitted IDs and
that creator's supplied source IDs. It does not expose another creator's records.
Legacy contracts without review ranges retain their earlier feedback shape.
Generic v105 source errors are revalidated locally on a new attempt to construct
an actionable correction. That correction selects the expanded context in both
request assembly and validation. The private upgrade projection never enters an
uncorrected historical request. Stored request feedback is canonicalized before
its first use so restart reconstruction has exactly the same key order and hash.
Once selected, the correction survives subsequent event-judgment retries.

Only the DM task changes in ai-tasks-v106; role/memory instructions, generation
caps, thinking settings and other tasks remain byte-equivalent to v105. The new
economy-guidance-v3 artifact describes the background/new-record distinction;
existing prefix artifacts are unchanged. Failed paid outputs are not silently
promoted or rewritten, and the production game is not automatically resumed.

Receipts: `.local/verification/event-background-20261109/`. Local recovery uses
the saved failed response as an explicit validation stub, without an external
model call or a claim that its original semantic reasoning was correct. Fresh
model acceptance uses only synthetic repository fixtures.

Eight focused regressions pass, including an initial no-new-message wait,
private/outside isolation, chronological backlog coverage, old wire invariance
and old generic-feedback correction followed by restart. Local reproduction of
the actual failed operation preserves its five original call rows, reuses the
successful role stage and needs one explicit local stub result for the corrected
DM. Restart then reuses that corrected result without another call. This is
offline recovery evidence, not a new model evaluation of the production story.

Three real synthetic Flash wait reviews pass on their first attempt: public
initial wait, private initial wait and waiting for someone to return. The first
two legitimately cite earlier own speech and retain the wait for another
person's reply; the third keeps a future-return wait without an invented source.
Their total cost is USD 0.002154360. One additional private probe did not have a
live wait because the fixture had not reconciled its invitation receipt; it is
excluded from wait acceptance. All four provider calls cost USD 0.002557212.
An earlier fixture action error happened before a provider call and was fixed
in the test runner. These small probes are not full-game quality evidence.
See `acceptance-report.json` and `recovery-report.json` for separate scopes.

Full regression passes 548 tests in 155.649 seconds; the subsequently added
private-wait isolation assertion also passes in the eight-test focused module.
Historical reconstruction matches 1,205 paid request hashes across 505 completed
operations without provider calls. All 121 pre-change artifacts are unchanged;
all 123 current artifacts pass manifest verification. The earlier full-suite
failure concerned the legacy feedback shape and is retained in `full-tests.txt`;
the corrected full run is `full-final-tests.txt`.

Deployment at 16:01:21 CST starts PID 567682; the service is running and HTTP
returns 200. Full before/after hashes match for 40 games, 3,284 AI calls, 1,516
operations and two legacy model calls. No request was pending at restart.
The affected game stays paused at revision 24 with its original retryable error,
ready for the user's normal retry. No production game was resumed or model call
made by verification/deployment. `deployment.json` records these checks.

## Selective Event Review: 2026-11-09 (v105)

Status: implemented; verification and deployment are recorded in
[cost control](11-prefix-cache-and-cost-control.md#scoped-context-economy-2026-11-09-v105).

Normal DM speech calls no longer include every unchanged custom tracker. A
tracker becomes reviewable when proposed, cancellation is requested, its creator
receives new observations or its scoped circumstances change. Fixed activities,
invitations, conversations and workflow transitions remain engine-owned. Ordinary
wait-validity reviews retain their existing scoped change checks and timeouts.

Custom trackers consume every pending received record in chronological chunks,
with a 4,000-byte target per tracker and at least one whole record. Existing
cited support remains available. review_range reports the consumed cursor and
remaining count; the DM must keep the event active until all pending chunks
have been reviewed. Only successful atomic application commits the exact
supplied cursor, including when applying another judgment emits new receipts.
No history is skipped by selecting only the newest twenty records.

DM requests pool exact evidence/receipt bodies across creator contexts while
retaining distinct occurrence IDs, document versions and each creator's source
authorization. If the only contract problem is omitted independent event
judgments, a retry asks for those missing IDs. All retained assessments, cues,
disclosures and judgments must validate first. Invalid or duplicate decisions
cannot be frozen into a repair. The merged result is revalidated before any
state changes; raw responses and canonical merged results remain recoverable
without rebuying completed calls. Existing three automatic retries still apply.

Universal event mechanics remain in immutable event-protocol-v9. The longer
judgment contract is supplied dynamically only when tracked events are present;
event instances and scoped review context remain dynamic throughout their life.

## Bounded Waiting and Contextual Validity: 2026-11-08

Status: implemented and verified with v79; deployment recorded below.

Every new role wait has a finite timeout: default 30 active seconds, selectable
from 10 to 300. Spectator time follows its existing logical clock and can jump
to the next deadline when nobody can act. Player pauses suspend timers. Timeout
ends that role's subscription, emits a private receipt and queues one decision;
it does not complete a shared activity, close a conversation or claim that a
custom condition succeeded. Repeated notifications coalesce. Existing no-progress
and spending limits still stop repeated unproductive cycles.

Event validity is interpreted by the DM from conditions, purpose, scoped actual
receipts and current perceptible circumstances. The shared guidance is generic:
it contains no room-specific cancellation rule, keyword classifier or scenario
patch. A change in participants may invalidate one condition and leave another
meaningful. Fixed terminal transitions remain engine-owned. Existing custom
trackers receive current scoped circumstances alongside their acquired records.
Generic observation/direct-contact waits also receive an initial DM validity
review and another only when newly perceived circumstances warrant it. Such a
review may keep or cancel the wait, but cannot invent successful completion.
Specific/compound conditions still use the existing listener tool.

Role output can state `wait_reason` and `timeout_seconds` in `next_decision`;
omitted fields use the known selected targets and default duration. Descriptive
intent does not replace registered conditions. All wait instances and review
checkpoints live in dynamic state; universal guidance stays in the immutable
shared prefix. Reuse normal scoped DM calls where possible; a new condition or
perceived change may require a DM call, but idle checks never call a model.

V79 enables timers and review metadata for existing live waits at the first new
operation, starting their default deadline then rather than fabricating a past
start time. Old pinned operations retain their original payloads and behavior.
The UI shows remaining active time and the latest timeout/cancellation reason.

Implementation uses `wait_lifecycle.py`, ordinary role scheduling, and existing
`event_decisions` in the scoped DM task. `wait_validity` records may remain active
or be cancelled, never claim completion. Current circumstances contain only own
activity and scoped visible presence; private perception remains incomplete for
the surrounding area. Review checkpoints and circumstance fingerprints prevent
unchanged idle DM polling. Deadline receipts are private; early-ending a wait
does not end a shared conversation or change a custom tracker's outcome.

Verification: seventeen dedicated tests cover clock jumps, one-time private
timeouts, unchanged fixed-event handling, semantic review, private isolation,
legacy migration, paused-time accounting, ordinary human-game dispatch, paid
role/DM replay after restart and repeated no-progress cycles. The last case
reaches the existing stagnation pause rather than calling models indefinitely.
Desktop/mobile checks (1440/390px) passed with no page errors or horizontal
overflow; changing the remaining time did not change card height. Screenshots
were inspected.

Six real Flash calls on synthetic fixtures cost USD 0.00440928 with no failures:
the same generic protocol cancelled an ended exchange, retained a future-return
condition, cancelled a condition whose required equipment failed, completed a
condition with an actual receipt, and cancelled an invalid generic wait. The
woken role then chose to inspect a record. These are bounded examples, not proof
that every narrative condition will always be judged correctly.
Artifacts: `.local/verification/wait-lifecycle-20261108/`.

Deployment: the final 369-test regression passed in 128.627 seconds. After a
SQLite backup and confirmation of no in-flight work, v79 was loaded at 18:03:16
CST on 2026-11-08. HTTP returned 200. All 32 game states, 1,630 call records and
808 operation records retained identical hashes across restart. The affected
game remains paused with its progress intact; its authenticated recovery control
is now enabled. Its failed v78 operation keeps that version, and subsequent new
operations activate the bounded-wait contract, including existing waits.

## Event-driven Role Decisions: 2026-11-06 (Implemented and Verified)

The user requested that characters choose whether to continue acting or wait for
an existing event, without polling every role after every occurrence. Recording
an observation and scheduling a model decision are separate operations. The
runtime keeps all actual recipient observations while a role waits; the next
decision receives its accumulated information through existing scoped memory
compression, recent observations and source recall. Waiting does not grant access
to other private conversations or missed public speech.

The current native-tool contract (v59) supersedes JSON-only creation for newly
generated roles. Every role has `create_event_listener` through provider-native
function calling. A call can register known fixed targets or create a personal
free-form proposal for DM review. Its caller identity is runtime-bound; target
permissions never come from model-supplied ownership fields. The returned
`wait_event` activates through the final role decision. Tool receipts include the
provider call ID, native tool-call ID, arguments and result. One batch of at most
two tools is followed by one final role decision; completed stages are reused on
recovery. No generic orchestration framework or unbounded Agent loop is added.

The generic mechanics live in immutable `event-protocol-v2.txt`, shared before
the role/DM-specific instructions. Native tool definitions are also part of the
frozen prefix. Event instances, progress, role-scoped source records, native
assistant/tool-result messages and wake state remain in the dynamic suffix.
Provider cache hits are measured, not guaranteed by an application cache label.
Calling a tool normally adds a model continuation; fixed state checks and idle
waiting still make no provider call. Version-pinned JSON creation from v50-v55
remains recoverable.

The initial bounded contract adds a private `next_decision`: continue, or wait
for any selected event. Available subscriptions cover known running activities,
one's pending invitations, known active conversations ending, and the next
received observation. A role can also start its own activity/invitation and wait
for that result in the same decision. An empty subscription list means wait for
direct contact. Targets come from an authorized menu, not model-invented event
IDs, arbitrary predicates or hidden world state. Completion, cancellation,
failure and invitation expiry are terminal outcomes, not guaranteed success.

Direct received questions/challenges, invitations, private replies, one's work
outcomes and collective conclusion submission interrupt waiting. Ordinary public
speech is recorded without waking an unsubscribed waiting role; periodic speech
counters remain, but are enforced at its next legitimate decision. Multiple
notifications coalesce into one queued turn. Continuing produces a fair queued
opportunity under the same pause, budget and recovery gates. No extra model call
is needed to choose or check the wake condition.

When every role waits, advance executable activities and active conversation or
invitation expiry without role polling. A spectator game with no runnable work
pauses with a visible waiting reason; human games await new participant input.
This is not an ending, a fixed act count or permission to invent progress.
Existing pinned operations keep their original behavior and request hashes.
Verification covers call counts, private boundaries, accumulated context,
terminal outcomes, pause/restart and no-event waiting.

### User-approved free-form conditions and early termination

The user subsequently authorized role-created events with natural-language
completion conditions and optional early-end conditions. The DM decides whether
a proposal is reasonable, whether observed developments satisfy it, and whether
it should end early. These are personal tracking requests, not executable code,
commands to other characters, new evidence, or permission to change world truth.
Private-chat lifecycle remains the main long-running shared event; physical work
uses short, existing two-unit tasks.

The user clarified that fixed event conditions are engine-owned: no DM call is
needed to decide whether a private chat closed, an invitation expired or an
action reached its terminal state. Either private-chat participant may end the
conversation unilaterally at any time; eight utterances/300 active seconds are
fallback ceilings, not minimums. A direct close immediately notifies eligible
subscribers, without partner consent or DM approval. The DM only interprets any
separate free-form condition that uses this actual closure as one of its inputs.

For a new custom proposal plus immediate waiting, the structured dependency must
reference the whole proposed event. Its individual conditions are not separate
OR subscriptions. Creating while continuing is also allowed. No player prose is
rewritten to enforce this control-field contract.

Each role may have at most two pending/active custom trackers. Its proposal,
conditions and interpretation stay private to that role. Shared, actually known
activity/conversation events remain separately subscribable by multiple roles.
Custom tracking uses the creator's actually acquired records and known facts;
the DM's global truth is not grounds for waking a role about unheard events.
The current main/private DM receives only trackers routed to its own scope,
with scoped receipts and prior assessment progress. A tracker can be approved,
rejected, completed or cancelled with a reason; an owner can request cancellation.
Terminal notifications wake the creator and distinguish success from early end.

Fold these judgments into existing DM calls when possible. A proposal or new
relevant non-speech receipt can require a DM call even without dialogue. With no
new information, do not poll the DM or characters. Thus savings concern avoided
role calls, not a promise that DM reasoning or extra input tokens are free.
Persist decision sources, assessed observation checkpoints and outcomes for
recovery and audit. This extends the approved event mechanism without adding a
general task engine, arbitrary physical effects or a provider polling loop.

### Verification record

The final v59 regression run passes 204 Python tests and six frontend checks.
Browser acceptance passes six ensemble checks and ten spectator checks with zero
page errors, including immediate private exit, waiting/event details, mobile
layout, call-budget recovery and unchanged scroll position. A local replay of
222 persisted calls matches every original request hash, with no validation or
recipient mismatch; it performs no provider calls or production writes.

The independent synthetic Flash probe `event-tools-20261106/live-767faf76.json`
completes all nine calls for USD 0.007006776 with no unknown-usage reserve. The role
actually calls `create_event_listener`, receives the matching tool result, and
waits on its returned ID. Its compound condition remains active after the private
conversation closes, and completes only after the public explanation is received.
Separate synthetic proposals verify DM rejection and owner cancellation. The
native creation and continuation have the same frozen prefix hash; provider usage
reports 23,296 cache-hit and 18,442 cache-miss input tokens across the probe.

This is a directed role-intent scenario, not evidence that every autonomous role
will choose the best listener or that a whole game always reaches an ending.
Earlier native probes exposed invented listener IDs and an unregistered spoken
wait. V59 clarifies tool-before-decision behavior and keeps all invalid structured
targets visible as recoverable errors; it does not rewrite player-facing prose.
Fixed event transitions and idle scheduling are independently covered without DM
calls. When a custom compound tracker also depends on a fixed transition, that
tracker's separate judgment can legitimately require the DM.

Artifacts are under `.local/verification/event-tools-20261106/`, browser ensemble
`run-383fa80e.sqlite3` and browser spectator `run-c4c7549f.sqlite3`. Deployment and
saved-game integrity are recorded in `event-tools-20261106/deployment.json`.
The final local deployment runs v59 with `palter.service` active (PID 620320).
The page, four relevant static assets and session endpoint return HTTP 200;
served static bytes match the workspace. All 24 game-state hashes match backup
`pre-event-tools-20261106-183009.sqlite3`; no saved game was advanced or regraded.

## Current Runtime: 2026-11-06

The cast has four seats with one to four humans. Single-human reading is unlimited; multiplayer reading lasts 120 seconds or until all humans are ready. Single-human pause freezes new work and active timers, buffers in-flight work, and resumes the same persisted operation. Multiplayer rereading never pauses others. A lightweight worker advances queued role turns, timed activities and eligible world effects while a participant is present. Public response chains have depth at most three; private turns have their separate cap. No paid idle polling occurs.

Separate zero-human spectator games fairly dispatch queued ready roles; sleeping
roles are not polled when the agenda drains. They explicitly start after preparation and use two active fictional
seconds per committed step. Normal/fast playback affects dispatch delay only.
Starting timed work gives another role an opportunity before the first work tick.
Pause buffers in-flight work; resuming reuses completed calls. A buffered single
step can be resumed continuously. Sixty seconds without an observer heartbeat,
stagnation, errors or budgets pause the game and never imply an ending. See
[Spectator mode](18-spectator-mode.md) for the complete current boundary.

Implementation: [complete playable runtime](17-complete-playable-runtime.md). Verification uses `tests/test_ensemble.py`, the multiplayer browser walkthrough and fresh provider receipts listed there. The design alternatives below retain their proposal scope; older implementation sections describe legacy saves.


References: [Conventions](../AGENT.md), [Initialization](01-game-initialization.md), [Communication](03-communication.md), [World events](04-world-events-and-actions.md), [Category selection](07-category-selection-and-introduction.md).

## Purpose and Scope

Define when gameplay can run, how humans review starting materials, and when AI characters can act in the background. These are shared session rules across categories; they do not select a particular active-play clock or impose a day/night structure.

Single-human play means one human with any supported AI cast. Multiplayer means multiple human participants, optionally alongside AI characters. The reading-completion barrier is interpreted as tracking human readers; AI setup readiness can be checked separately without running autonomous gameplay.

## Confirmed Reading Rules

| Situation | Reading limit | Gameplay and AI behavior |
| --- | --- | --- |
| Single-human initial reading | Unlimited | No autonomous gameplay while the human reviews starting materials |
| Multiplayer initial reading | Timed | No autonomous gameplay; all human readers can finish early |
| Single-human review during play | The human may pause to reread the original briefing | Hold new AI activity; previously running work may finish in the background |
| Multiplayer review during play | Reviewing the script does not pause the session | Other permitted game activity continues |

Provide a Reading Complete control. In multiplayer, start early when all human readers have completed reading; otherwise the configured reading deadline ends the phase. Single-human initial reading ends when that human chooses to proceed.

Completing reading is a readiness indication, not consent to private chat or a future scenario action. In multiplayer, an early finisher waits for the common start condition rather than receiving early gameplay opportunities.

Starting-material delivery and initial data preparation are distinct from autonomous play. Preparing a character's data must not execute role decisions, speech, private negotiation, or other gameplay before the reading gate opens.

## Initial Reading and Live Review Are Different

The category introduction is a public preview before confirmation. Initial reading follows confirmation and may include the participant's private role materials and starting memories. Live review returns to the original materials during an ongoing game.

Access to starting materials retains role visibility: reviewing one's own briefing does not reveal every other character's private memories or the complete hidden scenario.

The exact Reading Complete interaction, multiplayer duration, and whether opening the single-human viewer automatically pauses or requires a separate pause control remain open.

## Single-Human Pause and Already-Running Work

Confirmed boundaries:

- The human may pause during play to review the original briefing without a reading deadline.
- Do not start new AI gameplay activity during that pause.
- AI work already running when the pause begins may finish in the background.

Finishing computation and applying its result to the game are separate decisions. The user has allowed the former; result application and player-visible delivery during a pause are not yet specified.

A proposed policy is to hold completed results until resume, validate them against current state, and prevent their completion from automatically scheduling another AI turn. This proposal also freezes in-game timers during the pause; it is not yet an adopted commit policy.

This applies to an in-progress AI private exchange as well: an already-running response may finish, but it must not automatically start a new turn during the reading pause.

## Ordinary Background AI Activity

During permitted active play, AI characters may decide scene actions and speech in the background. They can initiate AI-to-AI private conversation by publicly inviting a partner and obtaining agreement.

This permission does not apply during initial reading or to new AI activity during a single-human reading pause. Multiplayer script review does not create such a pause.

Background AI conversations require both a maximum duration and a maximum exchange count. See the [communication module](03-communication.md) for limits and knowledge boundaries. Values, units, and turn-count definitions remain open.

Each accepted private conversation has a dedicated DM until that conversation ends. Its turn scheduling follows the same initial-reading and single-human pause boundaries as other AI activity. A temporary private DM does not independently advance the shared world during a pause or restart a closed conversation.

Autonomous activity also needs call and token budgets under [Immutable prefixes and cost control](11-prefix-cache-and-cost-control.md). Permission to act in the background does not require continuous model polling. Cache maintenance must not start forbidden gameplay turns during initial reading or a pause. A provider cache may age in real time while game time is paused; resuming must handle that condition without changing the frozen context baseline.

## Private Conversation and Missed Events

Private participants do not automatically learn about the rest of the game's concurrent activity. The wider session may keep progressing while they talk, provided it is otherwise running.

On return, participants can choose to ask someone what happened. They receive that person's account, not an automatic transfer of all hidden facts or missed public messages. Subsequent scene observations can reveal present conditions without supplying their unseen history.

Any exception for a directly perceptible disturbance, or an optional public-history review feature, needs an explicit design rule.

## Time Concepts to Keep Separate

- Human reading duration in real time.
- Multiplayer initial-reading countdown.
- In-game time and scenario deadlines.
- Model or task execution time.
- Private-conversation duration and exchange count.
- Dialogue rounds, response obligations, periodic speech intervals, and optional private character input.

Active-play time progression is still undecided. A task finishing in real time does not by itself establish how much fictional time has passed.

Character actions use the shared [event data model](04-world-events-and-actions.md). Timing, occupied activities, and interruption behavior belong to event properties and supported scenario rules. An event may be instantaneous or take time; defining its duration does not by itself choose the global clock or require the human to wait that duration in real time. Overlapping events share the world timeline rather than contributing their full durations one after another. The detailed fields and execution lifecycle remain proposals.

Question-triggered responses, periodic speech, event explanation requirements, and optional thoughts or plans are specified in [Speech thoughts and action input](09-speech-thoughts-and-action-input.md). Speech is not required every round. An empty private-input field does not create a new response obligation or block an otherwise valid response.

Dialogue rounds do not establish a mandatory day/night cycle, bypass reading or pause rules, or require private participants to answer public questions they have not received. The interval definition, counter behavior during absence or pause, and response deadlines remain open.

## Boundary Cases and Open Questions

- Multiplayer reading duration and the point at which its countdown starts.
- Players joining late, disconnecting, withdrawing readiness, or failing to read before the deadline.
- Whether mode changes when human participation changes; do not assume a disconnect automatically grants single-human pause behavior.
- Application of completed AI work during pause, result validation, and resume ordering.
- Which in-game deadlines and conversation counters freeze under the proposed pause policy.
- Exact conversation caps, units, counting rules, repeated invitations, and concurrency.
- Human-only conversation limits and direct-perception exceptions during private conversation.
- Active-play time model and limits on autonomous AI activity per opportunity.

## Legacy Demo 01 Implementation and Verification

Initial reading and rereading pauses launch no autonomous role work. Each eligible human interaction gives B/C bounded decision opportunities; role and memory calls can run in the background with at most two provider requests in flight. Already-started work can finish during pause but is buffered; resuming reuses persisted completed stages and validates the original world before commit. Private chat expires after 90 active seconds or four utterances; expiry is checked at session reads/interactions, with no idle model loop. Public dialogue increments a conversation round; physical actions/private exchanges advance a beat. One eligible model event may extend the initial six-beat deadline to seven. Multiplayer readiness and continuous autonomous scheduling remain designs.


## Legacy Demo 02 Implementation: 2026-11-05

The user confirmed that investigation must not prescribe acts. New cases have no six-action deadline or turn-count ending. Reading, inspecting known material and notebook edits do not trigger role polling. Explicit interactions create bounded relevant-role opportunities. Final accusation or voluntary unresolved closure ends the attempt; a provider budget never decides the fictional resolution. See [Demo 02](16-demo-02-deduction.md).
