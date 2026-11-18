# Goals and Endings

Status: Separate primary/personal victories and actual outcomes for seven scenarios implemented; versioned murder argument reviews implemented.

Last updated: 2026-11-09.

## Admission Isolation: 2026-11-09 (v97)

Status: implemented, verified and deployed.

The user's correction makes the culprit's final voluntary admission independent
of non-culprit assessment and objective results. The v96 evaluation order already
kept each investigator's submitted argument and evidence separate, but the shared
case flag could still unlock a cooperation victory after a supported confession.
That indirect score dependency must be removed.

New conclusion operations distinguish investigator-established truth from a
supported culprit admission. An investigator's own argument, cooperation credit,
primary/personal outcomes and individual commentary depend only on investigator
assessments and the unchanged gameplay record. Changing only the culprit's final
submission must leave the complete investigator participant results unchanged.
Cooperation between non-culprit investigators remains supported by the existing
requirements. A valid confession can still establish the overall case and affect
the culprit's avoidance objective. Unsupported confession supplies no proof.

This is a versioned engineering scoring change, with no altered model prompt,
new review pass or paid repair call. Pinned v96 and earlier conclusions retain
their original results; saved games are not regraded. The post-game header will
distinguish confession-established closure from investigator success.

`results.scoring_version=2` records separate `investigation_success` and
`admission_established` facts. The former supplies investigator cooperation and
individual process commentary; overall `shared_success` still describes case
closure. The new prefix sets only an engine metadata flag: model instructions,
request bodies, token limits, source access and retry contracts are unchanged.
Final-confession isolation does not erase or change testimony actually received
and explicitly cited during play; it prevents the subsequent closing evaluation
from retroactively improving another role's submission or result.

The focused suite passes 40 tests, including a 96-combination scoring matrix and
complete-flow comparisons of denial, unsupported admission and supported admission.
These comparisons preserve every non-culprit participant result, including
individual commentary. Tests retain investigator cooperation and legacy v96
scoring, and execute the shared JavaScript header renderer without changing saves.
Nine previously paid real Flash requests from four independent synthetic v96
closures replay byte-identically under v97; all recorded outputs validate and
close successfully. No new model call is needed for this engineering change.
Artifacts: `.local/verification/admission-isolation-20261109/`.

Historical read-only replay matches 607 paid request hashes across 255 completed
operations and preserves all 107 pre-change prefix artifacts. The production game
is not resumed, and saved ending results are not recomputed.
The final full regression passes 498 tests; no additional provider call was made.
Service restart and unchanged saved-row hashes are recorded in module 11.

## Role-Specific Conclusion Assessment: 2026-11-09 (v96)

Status: implemented, verified and deployed.

Investigators retain identity/time/method argument grading. A concealment role's
ordinary outward position receives a separate assessment of the submitted stance
and its relationship to evidence actually used in final submissions. Denial,
redirection and withholding judgment are legitimate choices, not failed deduction.
Do not demand missing proof of the role's own crime, score acting quality, or infer
that another role believed a lie. Quote only actual submitted text when assessing
a conflict; unresolved evidence is not a contradiction. Omitted private beliefs,
unsubmitted known records and hidden case details cannot supply supporting proof.

An explicit structured self-identification selects voluntary-admission review.
Keep semantic support plus actual acquired/cited proof coverage; an admission
alone cannot establish the case. Preserve the exact final submission even if its
text is incomplete or ambiguous. Narrative wording alone does not change the
locked accused person. All objective and shared-outcome rules remain unchanged.

Version private assessment instructions and output contracts within the existing
generic ensemble_theory task. Assess investigators first so the concealment
review can see their actual evidence findings; no new whole-history or self-review
pass. A written stance without an accused person now receives one assessment;
an empty submission needs none. Outcome and objective explanations are attached
by engineering after scoring and cannot be supplied by the model.

New reviews distinguish outward-position assessment, admission assessment and
investigation assessment. The shared player/spectator page displays the appropriate
review. Historical culprit panels may hide irrelevant investigation grades while
retaining their exact submission/outcomes and identifying unavailable new-style
commentary. Never regrade saved games, alter published prefixes or buy new calls
for historical display. Pinned operations retain their former contracts.

Implementation uses private `ensemble_theory` variants selected by `review_mode`.
`ensemble_position_review.py` produces `assessment_type=position` with a short
stance summary and selected source-backed statement checks; it produces no
investigator aspect grades or accusation-correctness verdict. The existing
objective scorer sees no established case from a non-self accusation. Admission
uses `assessment_type=admission` and the existing acquired/cited proof contract.
The engine attaches actual case-establishing submitters and objective reasons
after scoring. Only actual final evidence is supplied to the comparison; neither
other roles' private beliefs nor all their acquired holdings enter the request.
Comparison evidence never enters the subject's stored knowledge.

Statement checks quote exact submitted text, cite supplied source IDs, and require
an original for a factual support/contradiction verdict. A heard claim alone stays
unresolved. New structured feedback survives automatic retries, restart and an
explicit manual retry without buying completed investigator assessments again.
The ordinary position task has a 4,096-token cap; investigator and admission caps
remain 8,192. Flash and thinking-disabled settings remain unchanged.

V95 is retained as an immutable intermediate probe version. Its first real probe
treated a factual denial of the act as an inherently subjective statement despite
an established causal case. V96 adds generic factual-proposition guidance:
indirect causal evidence can contradict a denial without an eyewitness, while
genuine evidentiary gaps remain unresolved. This is prompt guidance, not a phrase
filter or an engineered semantic verdict. Missing natural names in admission
reasons use a generic role reference instead of exposing actor IDs.

Verification artifacts: `.local/verification/role-reviews-20261109/`. Four synthetic
cases cover denial against submitted evidence, withholding an accusation, supported
admission and admission without proof. V95 and v96 each complete nine real Flash
calls (including ending narration); the v96 repeat additionally checks that the
denial of the act is assessed against the connected evidence. No production story
is exported or resumed. These probes do not establish a full-game quality rate.
The first deterministic recovery test exposed a missing feedback-persistence
hook; the hook was added and the restart/manual-retry test now passes.

The browser access host was unavailable. Executed JavaScript-renderer checks
cover distinct sections, admission display, historical results, escaping and
stable unique detail IDs. Desktop/mobile visual acceptance is not claimed.

Final verification passes 489 full regression tests and 46 focused tests.
Read-only historical replay matches 607 request hashes across 255 operations,
preserving all 105 pre-change prefix artifacts. The scorer file is byte unchanged.
The two real-probe rounds total 18 calls and USD 0.009345888; all calls completed
without retries. Deployment and preservation receipts are recorded in module 11.

## Evidence Matching and Explained Reviews: 2026-11-08

Status: Implemented with contract, browser, and bounded synthetic Flash verification.

New versioned murder reviews match case-declared equivalent records only
for proof coverage. Original records, acquisition, testimony, and history remain
separate. Mixed originals and copies can establish the same fixed fact; a spoken
reference to an unacquired document cannot supply that document.

The existing final-argument evaluation call returns short reasons for each
of identity, time, and method. Runtime combines semantic support with actual
submitted/acquired source coverage and expose the resulting decision and gaps.
Only an actual final submission is graded. Process statistics and missed known
opportunities are a separate retrospective, never additional scoring evidence.
Investigators receive deduction/contribution feedback; culprits receive chosen
outward-position, exposure, and objective feedback. Voluntary admission is valid
agency, not automatically a behavioral error. Existing objective/closure rules
remain unchanged. No dedicated commentary call or whole-history review is added.

Published prefixes and pinned operations retain their original contract. Saved
outcomes are not regraded. Historical Web views identify missing detailed reviews
without inventing explanations. Acceptance covers equivalent/missing sources,
semantic failure, role boundaries, actual submissions, historical compatibility,
desktop/mobile views, and bounded synthetic Flash receipts.

Implementation: `palter/ensemble_review.py` owns proof-premise matching and the
persisted review. `conclude_ensemble` selects it only for the v73 review contract;
older versions retain their previous request/response and grading behavior.
`ensemble_theory` v73 adds three concise reasons within the existing 1,600-token
cap. All other task definitions are byte-equivalent as parsed JSON to v72. Runtime
matches only actually used, cited, acquired documents; testimony remains a separate
source type. A wrong suspect cannot establish identity even if the model approves
that aspect. No suspect or no explanation is displayed as unassessed, without a
new evaluation call or an invented claim that selected evidence was unused.

Each persisted `results.participants[actor].reasoning` retains the original
`result`, `established`, and `suspect` fields and adds `review_version`, role
perspective, submitted text, cited source snapshots, and three aspect reviews.
An aspect stores semantic support/reason, engineering coverage, final established
status, actual matching IDs, and one nearest proof route's remaining gaps. Gaps
distinguish unacquired, acquired but uncited, and cited but unused records. The
display explains that alternate equivalent materials are choices, not additional
requirements. These gap titles are post-game truth comparisons, not claims about
what a player knew. Extra private notes in a transfer stub remain part of that
record; equivalence does not transfer those notes into another document.

After objective scoring, a deterministic process view records acquired source
origins, directed speech count, credited key records, and the actor's own
unvisited areas. No private belief is substituted for an actual submission, and
these process facts never enter the argument evaluation or change the score.
Culprit reviews display chosen stance and whether the collective case succeeded;
they do not criticize a role for failing to investigate itself. The existing
primary/personal rules, cooperation thresholds, closure and available actions are
unchanged. Process counts are factual feedback, not an AI assessment of acting or
dialogue quality.

Both play and spectator pages render the same merged verdict, exact submission,
per-aspect reasons and proof gaps, source details, objective reasons and separate
process section. Stable detail IDs preserve expansion and scroll across polling.
Historical outcomes show their saved verdict and explicitly state that detailed
reviews were not recorded. Detailed reviews appear in normal player views only
after the game has ended.

Verification artifacts: `.local/verification/conclusion-review-20261108/`.

- 14 new targeted regression tests cover both mixed-copy families, missing
  sources, unused versus uncited records, semantic failure despite full coverage,
  heard claims, invalid model references, culprit admission/abstention, actual
  submissions, scoped process observations, disclosure timing, and v72 recovery.
- The full suite passes 283 tests. Two legacy test-double responses were updated
  to the new three-reason contract; old-version fixtures still use their original
  response shape. No production response is silently repaired.
- Browser verification covers play and spectator pages at 1440 and 390 pixels,
  original-source display, old results, expanded details/scroll retention, no
  horizontal overflow and escaped untrusted text. No page errors were recorded.
- Four real Flash synthetic cases passed: mixed originals/copies established;
  wrong time unproven; missing original unproven despite model semantic approval;
  voluntary culprit admission established. Eight calls completed without retries,
  costing USD 0.005096028 in reported usage estimates. Every call reported cache
  usage; no production story was exported or regraded. This is bounded acceptance,
  not a complete-game balance or universal semantic-quality guarantee.

Local deployment: the service was restarted after confirming no pending
operations/calls and creating `predeploy.sqlite3`. Root and updated JavaScript
assets returned HTTP 200 and matched disk. All 29 saved game-state hashes, 1,270
call rows and 635 operation rows remained unchanged. `deployment.json` records
the restart and state-preservation checks. No historical result was recomputed.

## Current Runtime: 2026-11-05

Every role has two executable objectives. Complete victory requires both. Innocence alone earns no victory: murder investigators must submit a supported reconstruction or contribute at least two key records to an established case. Disclosure can defeat another objective even when deduction succeeds. Other scenarios evaluate actual custody, bilateral commitments, votes, fulfilled resource pledges, evacuation, mechanisms and recovered records. Every human submits independently; truth stays hidden until the final human submits. Model narration receives already computed outcomes.

Implementation: [complete playable runtime](17-complete-playable-runtime.md). Verification uses `tests/test_ensemble.py`, the multiplayer browser walkthrough and fresh provider receipts listed there. The design alternatives below retain their proposal scope; older implementation sections describe legacy saves.


References: [Conventions](../AGENT.md), [Evidence](02-memory-state-evidence.md), [Relationships](05-character-relationships.md), [Scenario catalog](scenarios/README.md).

## Purpose and Design Responsibility

Define scenario-specific goals, stopping conditions, and possible outcomes. Codex is responsible for expanding the user's examples into additional scenario designs and ending possibilities.

The discussed evidence-suppression outcome is an investigation example. Other categories can focus on rescue, reconciliation, negotiation, exploration, or different objectives.

## Candidate Outcome Dimensions

An ending can combine the actual world outcome, public understanding, individual objectives, and relationship results. These dimensions need not reduce to a single shared win or loss.

A character may protect a friend while losing trust, recover an object while concealing its history, or reveal the truth while failing a personal objective.

## Possible Ending Families

| Family | Investigation example | Other scenario applications |
| --- | --- | --- |
| Resolved outcome | Actual events are established and accepted | A mechanism is solved or disputed ownership established |
| Known but unproven | Someone understands the truth but cannot demonstrate it | An agreement is understood privately but lacks public support |
| Mistaken resolution | The group settles on an incorrect account | A council chooses on false information or explorers misinterpret a discovery |
| Concealed outcome | Relevant people intentionally preserve a secret | A family protects a private history or factions hide a bargain |
| Unresolved outcome | A deadline arrives with competing explanations | Negotiations end in deadlock or an expedition leaves questions open |
| Negotiated settlement | Characters trade disclosure or cooperation | Power sharing, return of property, or an agreed separation |
| Costly success | A goal succeeds while a relationship or other objective fails | Rescue with losses, recovery at the expense of trust |
| Partial success | Some goals or questions are resolved | Some participants are evacuated or only part of an archive is recovered |
| Collective success | Shared goals and compatible personal objectives succeed | Everyone escapes or parties reach a durable agreement |
| Breakdown | Coordination or an agreement fails under actual events | Failed evacuation, coalition collapse, or a reunion ending in estrangement |

These are composable proposals, not a fixed menu of endings or adopted victory rules.

## Evidence Suppression Example

The user proposed a possible murder-scenario development in which removable evidence is eliminated, or logical connections remain unrecognized. An example handling budget permits attempts against at most one evidence category per day.

Distinguish:
- Evidence actually destroyed or made inaccessible.
- Evidence still present but not discovered.
- Facts known individually without their logical connection being recognized.
- A correct private conclusion that has not been shared or demonstrated.

Existing testimony and memory remain part of history. A sound deduction can still arise from available facts even after a physical clue is gone.

Evidence condition alone does not automatically end a game. The scenario must specify when investigation ends, whether further meaningful actions remain, and how current understanding contributes to the ending. Budget scope and category definitions remain open.

## Candidate Stopping Conditions

Scenarios may use a deadline, departure, completed objective, agreed resolution, exhausted permitted phase, or a decisive world event. Each selected condition must be explicit and causally supported.

Do not invent an extra clue or rewrite the past solely to force a preferred resolution. The ending should explain what actually happened and what participants achieved, within the selected post-game disclosure policy.

## Open Questions

- Shared victory, individual success, narrative outcomes, or a combination.
- Objective changes during play and conflicts between objectives.
- Formal accusations, evidence standards, and private deductions where relevant.
- Scenario-specific stopping conditions and continued play after partial success.
- How much hidden truth to disclose after play, especially for replay.
- Which proposed ending families to adopt in the first scenario modules.

## Legacy Demo 01 Implementation and Verification

The bounded AI runtime evaluates actual item custody, A's location, acquired information, and the deadline to obtain delivered, incomplete, or not_found. DeepSeek then generates A's personal ending from that actual outcome and A's legitimate experiences, with source IDs. It cannot change the evaluated outcome or reveal an omniscient solution. Individual AI goals influence decisions but do not yet have separate formal victory scorers. Formal accusations, comprehensive scenario-specific endings, and full-truth post-game disclosure remain designs.

## Historical Priority: Deduction (superseded by the current runtime)

The user selected progressively reconstructing the truth as the core experience.
[Demo 02](16-demo-02-deduction.md) proposes evaluating a submitted explanation
against fixed history and acquired evidence, distinguishing an established case
from a correct guess, an incorrect account and an unresolved investigation.
The proposed final review explains the evidence and misleading accounts after
the attempt closes. This differs from the implemented custody/location outcome
and requires new accusation and proof handling; it is not active in the current
runtime.


## Legacy Demo 02 Implementation: 2026-11-05

New investigation games now resolve established, unproven, incorrect or unresolved from the actual final submission and fixed proof routes. The final review can reveal the frozen truth only after explicit closure. Recorded AI beliefs, attitudes and disclosures supply additional social outcomes. See [Demo 02](16-demo-02-deduction.md); item custody continues to govern legacy saves only.


## Goal-specific Culprit Decisions: 2026-11-06

A culprit's avoidance objective guides situation assessment, tactical speech and
final positioning. Their true personal memory is not itself a submitted
accusation. Only an explicitly chosen culprit submission is graded; an old private
self-identification cannot silently supply one. Context permits deception without
changing world facts or rewriting private knowledge. There is no programmatic
confession filter: a role may still make an intentional sacrifice or bad choice.

After collective closure opens submission, new AI decisions can choose only
lock_conclusion. This closes the investigation phase rather than imposing a
fixed act/round count, and leaves the content of the final position to the role.
Older pinned operations retain their original choices. See [Spectator mode](18-spectator-mode.md)
for the version and validation evidence.
