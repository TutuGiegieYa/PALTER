# Demo 02: Progressive Murder Deduction

Status: Implemented legacy investigation runtime, retained for existing saves. New games use the ensemble runtime in module 17.

Last updated: 2026-11-05.

References: [Conventions](../AGENT.md), [Glossary](../GLOSSARY.md), [Evidence](02-memory-state-evidence.md), [Endings](06-goals-and-endings.md), [DM boundaries](10-system-dm-and-deception.md), [Current runtime](15-ai-runtime.md), [Murder scenario](scenarios/01-murder-investigation.md).

New games and current acceptance are documented in [the complete runtime](17-complete-playable-runtime.md). This module preserves the earlier four-character investigation and its historical verification; it is not the new-game feature list.

## Confirmed Experience

The user authorized implementation of the six improvements and explicitly
rejected a prescribed number of acts. A game fixes its case and private scripts
before play, then allows human and AI decisions to produce different outcomes.
The implementation combines a rule-defined physical mystery with generated
settings, social conflict and character profiles. Culprit assignment and clock
values vary; future choices remain open. The first family uses camera-clock
calibration and continuous records. It does not yet generate arbitrary murder
mechanisms. An independent authored fixture is retained for regression.

### Concrete Execution Contract

New games use one human A, AI roles B/C/D, three locations and nine
inspectable evidence records. A generated case contains a fixed history, scoped
initial role knowledge, evidence provenance, a solution and alternative sufficient
evidence combinations for identity, time and method. The case is hashed and is
immutable after initialization. Structural validation cannot by itself establish
perfect narrative logic; real generated cases need inspection and play testing.

Inspection, movement, notebook edits and reading are immediate local operations.
Addressed questions and presented evidence trigger the relevant AI role; a public
untargeted contribution or an explicit wait offers one bounded role opportunity.
AI roles can investigate, move, share discovered evidence, speak and invite or
answer private conversations. Their decision call also updates their scoped
memory and attitude, avoiding a separate memory call for every scene click.
Private conversations require consent and are bounded at eight utterances and
300 active seconds; these caps do not end the case or define acts.

The notebook keeps acquired evidence separate from attributed statements and
private hypotheses. Saving it never asks a model to judge the hidden answer.
A final accusation explicitly closes the attempt: an interpretation task maps
the player's actual quoted explanation to identity/time/method claims and cited
acquired records; code checks the named suspect and sufficient evidence sets.
Correct unsupported guesses, supported reconstructions, wrong accusations and
voluntary unresolved closure have different outcomes. NPC beliefs and disclosure
history are retained as additional social outcome dimensions. There is no
pre-final correctness oracle and no automatic six-step ending.

The existing transaction, command-identity, prefix-version, pause and recovery
mechanisms remain shared. Old item-recovery saves continue through their original
runtime; the new default creates investigation games. No game is upgraded by
rewriting its already-established history.

The user explicitly chose progressively deducing the truth as PALTER's primary
appeal, consistent with its murder-mystery role-playing premise. Investigation,
contradictions and reconstruction take priority over negotiation, betrayal as an
end in itself, or further expansion of introduction categories.

The historical recoverable-item runtime did not provide this experience. Its
ending depends on custody and location, and its observations do not implement a
case proof. Varied introductions and successful model calls do not establish a
fun or solvable mystery.

The playable investigation aims to let the player form a plausible early theory,
encounter a fact that changes that theory, ask a more precise question, and
finally explain what happened using acquired evidence. These are possible
discoveries, not a mandatory sequence of scenes or preassigned player beliefs.

## Bounded Scope and Earlier Proposal

- One human character and three AI suspects, plus one deceased victim outside
  the active cast. The human has a personal connection, partial memories and a
  separate private concern; the role is not an omniscient detective.
- A bounded generated case with a fixed opportunity/evidence contract. The
  earlier authored-case proposal remains an illustrative fixture below. Real AI
  supplies introductions, story content, character decisions and speech, DM
  interpretation, memory, relationships and ending narration.
- Three investigation locations and approximately eight to ten meaningful
  evidence records. No target playtime is claimed before observation with players.
- Investigation starts after the death. The earlier voluntary-killing and
  randomized-arrival opening remains a separate scenario proposal.
- Inspect an explicit target, ask a character about a topic, present acquired
  evidence, compare records privately, and submit a reasoned accusation.
- The current six-action retrieval deadline is not inherited. Reading,
  reconsidering evidence and composing a theory do not spend an action budget.
  A budget limit pauses generation visibly; it does not declare the case solved.
- Continue to support voluntary private conversations and scoped knowledge.
  A recorded statement remains a statement, even when it is false.

The bounded implementation now uses these cast and action choices in a separate
investigation runtime. The earlier A/B/C item-recovery saves retain their original
behavior and are not silently migrated.

## Case Before Dialogue

Freeze a case truth record before the first investigation input: participants,
actual killer, victim, relevant historical events, locations, access conditions,
time anchors, traces, and each role's initial experiences. Separate the public
briefing from the full truth and from individual private briefings.

Every discoverable record has an origin and an acquisition condition. Each major
conclusion has a sufficient combination of records and explicit assumptions.
The developer can inspect this solution structure; role controllers and ordinary
player views cannot. The narrator must not select a culprit after seeing the
player's guess or invent a new witness, forensic result or access route to make
an accusation work.

Evidence relationships can support different investigation orders. A player who
finds a strong combination early may progress immediately; do not withhold it
until enough dialogue rounds have elapsed. At least one complete route must
remain solvable if the culprit refuses to confess or an innocent withholds a
private embarrassment.

The same fixed truth can produce different conversations, discovery orders,
interpretations and accusation outcomes. Changing the culprit for a replay
requires another coherent case version with regenerated dependent facts, not
shuffling a name underneath unchanged evidence.

## Proposed Case Brief: After the Screening

Working Chinese title: 闭馆后的放映室. This is a developer design example, not a
shared generation template or a verified finished script.

A film archive director is found dead after an internal screening. The human
restorer heard one suspect's voice over the sound system and initially treats
that as evidence of the suspect's location. The other roles include a projection
technician, a project manager and an accountant. Each has a reason to conceal
something; concealing a visit or arguing with the director does not establish
murder. Playable places are the screening room, projection booth and office.

The central proposed mechanism is a mistaken inference from a recorded voice to
physical presence. An innocent's later visit creates suspicious traces. The
player must distinguish the fatal encounter from that later visit and establish
positive evidence of the actual offender's opportunity. The complete timeline,
names, exact clues and sufficient-proof combinations must be authored and checked
before this example is treated as an executable case.

| Investigative question | Acquirable material to design | Required reasoning boundary |
| --- | --- | --- |
| Who appears suspicious initially? | A witnessed argument, an inconsistent visit account and a trace associated with that visitor | Motive, a lie or presence alone is insufficient |
| When did the fatal encounter occur? | Independently grounded last-alive and first-death observations, with explainable timestamps | Do not infer an exact death time from a single unverified account |
| Does the suspicious trace belong to the killing? | Entry/exit records plus the time bounds and the visitor's later actions | A trace left after death can explain suspicion without proving innocence for unrelated reasons |
| Does hearing a voice establish an alibi? | The human's actual memory, playback records and an inspectable matching recording | Hearing a recording does not locate its speaker; a broken alibi is still not proof of guilt |
| Who had the relevant opportunity? | Positive presence/access evidence, the established window and independently supported alternatives | Avoid concluding guilt solely because others look less suspicious |
| Why did it happen and how was it concealed? | A grounded dispute, the actual event order and evidence of the alibi construction | The explanation must account for the facts without new hidden mechanisms |

The draft must be revised if these records fail to distinguish a viable alternate
offender or require specialized real-world knowledge absent from the case.
Material mechanics and access limitations must be discoverable in the fiction.

## Player Interaction and Feedback

An inspection yields a concrete observation, such as the contents and provenance
of a playback record. It does not automatically append "therefore this person
is lying" or reveal the relevant solution step.

Characters retain their own earlier statements. Presenting an acquired record
lets the player ask about a specific discrepancy. An innocent may explain a
separate secret; a culprit may evade or propose an alternative. AI decides its
response from authorized memory and the presented information. The actual
response becomes history, but its claims do not overwrite the case facts.
Record selection and memory must preserve the original testimony so a later
summary cannot erase a contradiction.

The evidence notebook distinguishes observed material, attributed testimony and
the player's hypotheses. A small timeline and links between selected records
support comparison. No automatic culprit ranking, lie badge or solution graph
is shown. A private draft can contain the player's own uncertainty without
broadcasting it or making it an executed accusation.

Natural-language reasoning may be interpreted into a proposed conclusion and
selected supporting records. Show that interpretation for the player's explicit
submission. The model may not silently add missing evidence or strengthen the
player's argument. Alternative sound wording and equivalent evidence sets must
work; keyword matching is not a proof standard.

Optional help must be requested. Begin by pointing to a relevant already-acquired
record or unanswered question, without exposing the answer. Never make repeated
model questioning the only way to discover a critical fact.

## Accusation and Resolution

The player submits the accused person and an explanation of the relevant time
window, opportunity or method, and supporting evidence. Motive and the reason
for a misleading account contribute to reconstruction quality, but a missing
confession or uncertain motive cannot invalidate otherwise sufficient proof.

Evaluate the submission against the frozen case and what the player actually
acquired. A language model can map the argument into structured claims; ordinary
validation checks referenced records, supported relations and the case's proof
conditions. Satisfying one particular checklist is not required when another
valid proof establishes the same conclusion.

- **Established:** the culprit and supported causal reconstruction are correct.
- **Correct suspect, incomplete explanation:** the name is right but the player's
  evidence does not establish it; report this distinction at final resolution.
- **Incorrect reconstruction:** show where the submitted account conflicts with
  the actual chronology during the final review.
- **Unresolved:** the player chooses to close without a supported conclusion.

Drafting and ordinary discussion are not scored as hidden answers. To avoid a
guessing oracle, do not announce whether the suspect is right during play. A
final accusation clearly closes the attempt. Post-game review may then reveal
the fixed truth, connect it to the evidence and explain innocent characters'
misleading behavior under this case's explicit disclosure policy. A personal
ending is narrated from that adjudicated result, not from item possession.

## Implementation Sequence and Acceptance

1. Author one complete case asset and audit its timeline, knowledge boundaries,
   clue provenance and sufficient evidence combinations. Verify that a viable
   alternative explanation is not being dismissed by fiat.
2. Implement case-backed inspections, a visible evidence notebook and persistent
   attributed statements. Adapt the roster explicitly and keep runtime state
   separate from the hidden solution.
3. Connect real character responses to questions and presented evidence. Ground
   new factual admissions in the role's frozen experiences, not invented history.
4. Add private theory drafting, explicit final accusation, proof evaluation and
   a post-game reconstruction. Retain pause, recovery and call accounting.
5. Run a complete real-provider/browser investigation and observe a human play.

Required acceptance includes:

- Several valid investigation orders lead to sufficient evidence without a
  predetermined character script or a required confession.
- A named culprit without evidence is distinct from an established case; a
  persuasive but false argument cannot rewrite the hidden truth.
- The innocent visitor's suspicious trace has an actual, discoverable cause.
- No ordinary response reveals another role's private knowledge or labels a
  supported behavioral cue as proof of lying.
- A player can cite acquired evidence for a changed belief and explain the key
  contradiction at the end. Ask what led to that change; observing a completed
  API flow alone cannot establish that the deduction experience worked.
- Recovery preserves discoveries, statements and the pending submission rather
  than rerolling facts or issuing another accusation.

The proposed example above is not the production script. New games use a generated
case under the bounded contract; the earlier runtime in module 15 remains for
existing saves. Verification records below distinguish model and browser checks
from human play testing.

## Implementation Record: 2026-11-05

palter/case_authoring.py fixes the culprit, clock bounds, nine evidence roles
and their knowledge/proof dependencies before content generation. The preview
binds four distinct living names and a separate victim. Code constructs physical
events and their observable records from the same clock/cast values, then derives
initial knowledge and proof dependencies. The model authors social conflict, its
documentary evidence, personal profiles and an innocent secret. The physical
family is explicit: a direct cord killing, a camera clock ahead or behind the
master clock, continuous alibis and a complete entrance record. This is a bounded
case grammar, not a general mystery solver or a failure fallback.

palter/case_world.py validates and locks the case, resolves movement/inspection,
tracks acquired evidence and attributed speech, and builds recipient views.
palter/investigation.py reuses durable operations and prefix-pinned recovery,
coordinates relevant real AI decisions and DM handling, and adjudicates a final
submission. New games have four living roles; existing saves route through the
legacy runtime. The browser has a scene panel, immediate dialogue, evidence and
testimony tabs, private notes, and an explicit final-submission control.

The setup contract includes an objective last-alive and first-death record,
clock bounds matching the solution window, a crime event within that window,
positive-presence/exclusion records, and supported method records. The killer
must know the crime event; other roles cannot receive that complete fact in their
initial knowledge. Hidden author provenance is excluded from evidence views;
player provenance identifies the inspected object. Runtime claims still require
semantic model judgment; these structural checks are not a general proof solver.

The current task version is ai-tasks-v23.json. Following the user's Flash
preference, all tasks inherit the configured model (default deepseek-flash)
without thinking. The one-time social story retains its 3,200-output-token cap.
V22 used Pro for setup and remains immutable for pinned recovery. Model selection is included
in request fingerprints and actual-model cost accounting. No extra prose
self-review call or output blacklist is introduced.

Early live attempts remain recorded as failures. V12 exposed an overly narrow
memory-reference validator. V13-v16 failed case generation or reasoning-budget
checks. V17 exposed cast confusion and an invalid restriction on NPCs suspecting
the human. V18/v19 completed actions but failed the supported-reconstruction
acceptance; manual inspection found weak or contradictory physical evidence.
V19 setup alone took 410.9 seconds and did not fix those semantic problems. These
results motivated the explicit physical case grammar above, rather than further
prompt-only retries or a weaker acceptance standard. V20 exposed a relationship
key error and a too-narrow proof-route check. V21 uses ordered relationships and
recognizes the complete-entry-record identity route; one real browser game passed,
but a separate preview confused the victim with a living role. V22 assigns distinct
entity names before preview generation and asks the model to author their setting
and story, avoiding another independent roster copy. Earlier logs are retained.

The final argument parser quotes the player's own submitted words. Supported
claims for one aspect may span multiple sentences; their evidence is combined.
Physical identity has both an alibi-supported route and a complete-entry-record
route. Time and method must still be established for a supported reconstruction.
Memory sources accept only the role's observations, acquired records or scoped
initial facts. Final checks below are execution acceptance, not a human fun test.


## Verification: 2026-11-05

- 61 Python tests and six frontend tests passed. Coverage includes immutable case
  truth, scoped initial knowledge, effective NPC inspection/sharing, private
  outside events without backfill, supported and unsupported conclusions, all
  four outcome branches, failure atomicity, idempotency and pause/recovery.
- Real-model CLI acceptance passed on a fresh v22 case, “录音棚静默”. All 18 calls
  completed, every identity/time/method aspect was established, inspection made
  zero model calls and the case hash stayed unchanged. Setup took 13.635 seconds;
  reported-usage cost estimate was USD 0.019229636. Record:
  [.local report](../.local/verification/investigation-live-450a08ec.json).
- Real-model headless Edge acceptance passed on a separate fresh v22 case,
  “客栈夜话”: 18 calls, no page errors, no mobile horizontal overflow, successful
  questioning/presentation, consensual private chat, notes/reload, pause/resume,
  supported final accusation and persisted reveal. Setup took 13.287 seconds;
  usage-based estimate was USD 0.018293468. Record:
  [browser report](../.local/verification/browser-investigation-live/run-9263fa76.json).
  Desktop and 390px mobile captures were visually inspected.
- Manual inspection checked the CLI case's fixed name bindings, 19:42–19:54
  window, camera display 19:32 plus a 16-minute correction yielding 19:48, the
  continuous alibis and the record that excludes other entrants before discovery.
- Final scope review removed undiscovered camera/calibration records from every
  initial personal script. The killer still knows their own crime; a participant
  knowing an action does not automatically know every trace it left. A regression
  checks this boundary across all three culprit assignments and both clock
  directions. The human also sees their own initial relationship descriptions.

Both live runners deliberately use the solution as an acceptance oracle to write
an evidence-backed argument. They verify execution, not unaided deduction,
engagement, difficulty or broad generative mystery quality. The bounded physical
family, limited action vocabulary and model-mediated semantic judgment remain
material limits. Existing production saves were preserved; start a new game to
use the investigation rules.

## Played-Game Review: 2026-11-05

Status: Local review findings and next design priorities, not implemented gameplay
changes. The played gallery case was read locally; no player save or transcript
was sent to an external model for this review.

The game completed 23 model calls without a failed call. The human collected all
nine clues, identified the actual culprit, and received an unproven result. Their
final explanation cited motive and entrance footage; the earlier clock-calibration
discussion was not included in the final citations, and the explanation omitted
the method. This does not establish a mistaken proof verdict. It exposes a weak
handoff from investigation notes and discussion to the final submission.

The user's report that innocents win too easily is supported by the design:

- Both innocent AI roles receive independently conclusive continuous alibis for
  the entire murder window. Two inspections effectively remove two suspects.
  All evidence is immediately inspectable without a meaningful disclosure choice.
- Personal goals are descriptive text. There is no evaluated personal success
  condition; NPC beliefs and trust contribute to narration only. Being innocent
  must not become a substitute for accomplishing a personal objective.
- Untargeted response selection uses the action-round counter, which also advances
  on movement and inspection. The culprit did not speak until beat 18. A later
  follow-up intended for the culprit selected an innocent instead.
- During finalization the culprit admitted a previously denied visit, but the
  human could no longer challenge that change. Outcome adjudication runs before
  these final responses, and finalization immediately ends the game.
- A generated secret-clue target named a warehouse object although its assigned
  location was the exhibition room. Its observation also presented fingerprints
  without an available forensic procedure. Authoring must receive explicit
  placement and observable-information constraints.

Priorities for the next gameplay increment are: complementary partial evidence
instead of two ready-made perfect alibis; fixed, actionable personal objectives
whose disclosures can conflict with the investigation; response scheduling based
on addressed challenges and unfulfilled opportunities; and an in-play
confrontation before irreversible closure. Preserve one solvable route despite
withholding, fixed past facts, scoped knowledge, and no prescribed act count.
Final submission should help the human review their own reasoning and linked
evidence without supplying hidden-answer feedback or crediting NPC reasoning as
the human's work. These are design priorities, not claims that difficulty has
already improved.

The cache display defect was separate: all 23 calls retained valid usage in the
database, totaling 21,248 cached and 31,237 uncached input tokens (40.5% hit ratio).
The new investigation UI now shows those columns and the aggregate, distinguishes
unreported usage from zero, and keeps the panel expanded across view refreshes.
Desktop and mobile browser checks passed using numerical usage metadata only.

## Flash Routing Verification: 2026-11-05

62 Python tests and six frontend tests passed. Coverage verifies current Flash
routing and billing, and the old Pro routing/cost of a pinned v22 operation. The
HTTP tests require localhost socket access outside the restricted sandbox.

A fresh, isolated v23 case completed 18 real DeepSeek calls, all recorded as
deepseek-flash, with no failures. Setup took 8.870 seconds. Questioning, evidence
presentation, consensual private conversation and the oracle-assisted final
reconstruction completed; inspections used zero calls and the case hash remained
unchanged. The peak-rate usage estimate was USD 0.015347004. Record:
[Flash acceptance report](../.local/verification/investigation-live-2f92a182.json).

This is one execution sample, not an A/B comparison or proof of stable narrative
quality. Manual inspection confirmed coherent constructed clock/proof values but
also found a generated document target naming the service desk while assigned to
the equipment room. That authoring limitation also occurred in the earlier Pro
player game; the routing change does not claim to fix it or the difficulty issues.
