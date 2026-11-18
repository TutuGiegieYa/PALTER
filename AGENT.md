# PALTER Project Conventions and Boundaries

## Development and Documentation Rules

1. **Read the project context first.** Read root AGENT.md, GLOSSARY.md, and the relevant module documents before design or development work.
2. **Write project documentation in English.** This covers conventions, terminology, designs, and development records. Product interface language is a separate decision.
3. **Respect document locations.** Root AGENT.md contains conventions and shared boundaries. GLOSSARY.md contains domain definitions. docs/ contains module records; docs/scenarios/ contains scenario module designs.
4. **Maintain one document per module.** Record status, date, scope, requirements, proposals, examples, and open questions. Add actual implementation and verification records as development proceeds. Register new modules below.
5. **Preserve the scope of examples.** Many user statements illustrate particular scenarios. Derive reusable mechanisms and retain concrete policies in their corresponding scenario modules. Murder, nighttime actions, and daily evidence limits are examples, not universal requirements.
6. **Develop additional scenario modules proactively.** The user has assigned Codex responsibility for expanding these examples into different scenario modules, including settings, goals, events, actions, constraints, and possible endings. Create concrete proposals using judgment and label their status. The user is not required to invent every scenario or mechanic.
7. **Capture decisions promptly.** Apply the user's latest explicit direction and synchronize affected documents. Distinguish shared requirements, scenario-specific agreements, design proposals, and examples. Correct superseded descriptions.
8. **Progress within the agreed scope.** Resolve routine details using project context. Record material assumptions and unresolved questions, and continue work that does not depend on them.
9. **Verify the actual change.** Check documentation scope, terminology, examples, and links. Run implementation checks relevant to changes. Verify information boundaries and causal consistency where affected.
10. **Keep the glossary focused.** Maintain canonical domain definitions; put implementation decisions in module documents.
11. **Design for prefix reuse and measured cost first.** Before expanding agent execution, define immutable prefix versions, authorized context boundaries, dynamic input placement, and call/token budgets. Validate provider-reported usage rather than treating a reusable template as proof of a cache hit or cost saving.
12. **Build a small PALTER runtime directly.** The user has chosen custom implementation instead of existing frameworks to avoid unnecessary complexity. Do not introduce an agent orchestration framework or a broad application framework into the initial design. Prefer ordinary modules, explicit records, and the standard library. Evaluate any small protocol, provider, or storage dependency separately; do not turn PALTER into a general-purpose framework.
13. **Define the demo before implementing it.** Record its supported actions, timing, interaction rules, observation boundaries, and explicit omissions in a module document before application development. Expand capabilities incrementally. Demo limitations do not replace the broader product requirements.
14. **Use a dedicated Conda environment.** The user requires Conda, not venv, and no dependency installation or application execution in base. Use the project's .conda-env interpreter for development, tests, and the server; environment.yml records its dependencies.
15. **Use real AI for AI responsibilities.** The user's latest correction supersedes the scripted production-demo scope. Introduction/setup generation, role decisions and speech, DM interpretation and cue assessment, private DMs, memory/relationship interpretation, world-event selection, and ending narration must use real DeepSeek calls where applicable. Ordinary code enforces permissions, timing, supported effects, and authoritative history. Keep scripted controllers only in explicitly labeled offline/test mode; never silently substitute them when an AI call fails. Verify real feature execution and attributable call traces, not merely API connectivity.

16. **Guide player-visible prose through context.** The user requires skills or versioned Agent context to reduce internal IDs, placeholders, and implementation annotations in text shown to players. Prefer concise natural-language guidance using in-world names and reserve IDs for structured control fields. Do not add self-review steps, extra review calls, regex removal, keyword filtering, or rule-based prose rejection for this. Internal-only data need not follow this display convention. Keep shared wording guidance independent of story-specific setting or location examples, which can anchor later generation. Preserve human speech and recorded history.

Documents must state their status and last update date. A design proposal is not an implemented capability. Shared mechanisms must support multiple scenario types without inheriting every rule from the first example.

## Product Goal

PALTER is an AI role-playing and interactive storytelling project. The same setting, cast, personas, relationships, and initial memories can develop into different stories through participant choices, event order, and interactions.

The name expands to Persona Agents for Live Theater, Evidence and Reasoning. Many causally grounded endings are a product goal; specific goals and ending rules belong to individual scenario modules.

### Current Playable Priority

- V125 distinguishes model-facing scheduling terms: frequency eligibility uses
  `passes_consecutive_wait_check`, while the independent message-only guard uses
  `message_only_subscription_allowed`. Candidate events, supported modes and
  frequency-only exclusions must not imply unconditional wait permission.
  Render consistent names in both role perspectives, listener descriptions,
  refreshed tool contexts and retry feedback. This is an input projection only;
  preserve scheduler decisions, mixed OR rules, state, output schemas, native
  receipts and all historical paid inputs. Module 08 records verification.

- V124 adds a positive `exploration.no_new_evidence` assertion only for a role
  that actually completed a search and acquired every currently discoverable
  material in that area, with no remaining intact hidden record there. Discovery
  is not reading; unseen/private/carried materials never become known through
  this flag. Keep current checks local, freeze remote assertions in personal
  snapshots, suppress stale results after received opening notices, and leave
  unconfirmed states without the field. Preserve old paid projections and all
  actions. Both role perspectives explain the field and avoid repeated unchanged
  searches; the shared player/spectator display distinguishes current results
  from historical ones. Verification and deployment are recorded in module 02.

- V123 prevents the last unfinished available role from entering a pure message
  wait while its peers are waiting. Cover next_observation, eligible pure-message
  aliases and empty-target direct-contact waits, without guessing custom event
  meanings. Preserve concrete OR targets, real work and final submissions. Supply
  scoped permissions after tools and recheck at commit. In spectator runs, let
  actual work/deadlines and due DM reviews proceed before interrupting one stalled
  subscription. Reconsider each eligible role once per grounded no-progress
  episode, then pause with waiting_stalled. Never complete its underlying event,
  disclose peer state, force an action or reset the allowance on ordinary retries.
  Preserve old paid prefixes and request bytes. Module 08 records verification;
  a bounded budget pause is not whole-game acceptance.

- V122 reserves summary capacity: standalone memory consolidation has a hard
  six-entry limit, while active memory retains twelve entries. Keep the existing
  2048-token / below-1024-text-character summary budgets, source permissions and
  compaction triggers. Synchronize prompt, payload, validator and retry feedback;
  never truncate entries or citations. A failed pinned role without any paid role
  or tool reply may use a separate bounded maintenance stage after explicit retry.
  Preserve that stage on replay and revalidate old feedback against the new
  memory, without promoting failed outputs or changing historical request bytes.
  Verification and deployment records are in module 02.

- V121 binds `own_activity` to the exact event returned by this decision's action.
  An immediate result queues one continuation after its receipt; ongoing work
  waits for its own actual terminal result. Never bind an earlier task or create
  a completion event for an empty stationary wait. Preserve interruption, OR
  subscriptions, deadlines and historical paid inputs. New role guidance and
  menus use the unified contract; pinned failed immediate-action replies can be
  validated compatibly on explicit retry. The spectator global timeline renders
  one attributed row per actual event, with original materials and recipient
  receipts in collapsed details. Keep distinct actions, speech, gestures and
  personal histories exact; no prose rewriting or model calls for this display.
  Verification and deployment receipts are in modules 08 and 18.

- V120 gives ensemble DM tasks, including private scopes, independent 512,000-byte
  dynamic and 1,000,000-byte total request limits. Role/memory limits, completion
  tokens, thinking, retry and cost admission policies remain unchanged. Normalize
  historical gesture snapshots alongside current speech; share exact source bodies,
  actor-bound snapshots and component values without unioning knowledge across
  roles or time. Consecutive citation IDs may use reversible ranges preserving
  prefixes, zero padding, gaps and order. Compare complete request sizes and retain
  the smallest representation. Preserve raw records, model output citation IDs,
  feedback and all paid/published versions. Offline replay and bounded synthetic
  model probes are separate from whole-game acceptance. V120 was deployed at the
  user's explicit restart request on 2026-11-10; preservation receipts are in module
  11. Older pinned DM retries use the higher admission guard with unchanged input
  bytes; new-format sharing is version-gated. Keep the paused game for user recovery.

- V119 supersedes the broad wait frequency policy for new operations. Only
  `next_observation` cannot occur in two consecutive committed replies by one
  role, including listener aliases and mixed subscriptions containing it. Other
  eligible event waits may repeat and restore access to this target. Registering
  listeners, retries, tools, other roles, timeout and cancellation do not advance
  accounting. Keep one dedicated per-role flag and scoped target restrictions
  after tools. Do not reinterpret legacy all-wait flags; v112-v118 requests keep
  their historical policy and bytes. Preserve event authority, response obligations
  and deadlines. V119 was deployed at the user's explicit restart request on
  2026-11-10. Deployment does not clear the preceding combined candidate's
  incomplete whole-game acceptance; keep that limitation distinct from service health.

- V118 reorders context keys for cache reuse only. Scoped constants and stable
  guidance precede source bodies; current messages, state and correction feedback
  follow. Current speech bodies are not initial-fact bodies merely because they
  contain only text. Preserve every value, selected source, chronological array,
  request byte size, fixed model prefix and historical layout. Do not enable
  unrelated context-economy features for memory tasks. Offline equivalence and
  bounded real cache measurements pass; these do not clear the preceding
  combined candidate's incomplete whole-game acceptance. V119 includes this change.

- V117 selects speech by the role's own communication purpose and distinguishes
  the current speaker, up to two own utterances and three actually received peer
  utterances through source references. Do not treat others' speech as a writing
  template or transfer their duties/experiences into first person. Brief agreement,
  gestures and permitted silence remain valid; no fabricated novelty is required.
  Preserve the output schema, wait policy, raw prose and historical paid requests.
  Prefer one conversational contribution, usually one sentence; expanded answers
  and arguments remain allowed. Keep turn-taking guidance at the instruction end.
  Move only already supplied recent speech bodies into the trailing focus source
  pool, resolving IDs across both pools without copying text or expanding recall.
  Measure the final layout during budget fitting; preserve old request layouts.
  V114/V115/V116 are retained, undeployed experiments; short probes did not establish
  reliable behavior in longer conversations.
  Check interpretation-field permissions before parsing an inapplicable patch;
  report actual/expected fields with the shared receipt, never silently accept it.
  V119 now includes this change at the user's explicit restart request. Regression
  passes, but the latest fresh trial stops at the existing DM context-budget
  boundary without reaching closure.
  Long-game repetitive questioning remains an observed limitation, not a solved
  behavior. Preserve the failed trials and distinguish code checks from acceptance.

- Shared reference/text failures return generic structured validation receipts:
  exact paths, rejected values or measurements, expected constraints and reasons.
  Derive source kinds only from the recipient's acquired/received information;
  unknown and foreign IDs remain indistinguishable. Keep patch commit status
  explicit and diagnostic samples bounded without capping accepted citations.
  Do not embed story-specific repair instructions, rewrite replies, grant new
  sources, add review calls or expand retries. Failed-attempt receipts are dynamic;
  published prefixes and paid request feedback/settings remain unchanged.

- V113 supplies explicit per-reply scheduling modes and preserves unresolved
  role corrections across syntax failures and manual retry/restart. Clear only
  validation groups actually checked successfully; never replay a growing error
  conversation or increase the four-attempt allowance. Equivalent interpretation
  patch envelopes may merge only known nonconflicting fields, with full source
  validation and untouched raw receipts. Malformed final JSON selects persisted
  JSON output with tool_choice=none on remaining retries; existing tool results
  remain available. Tool argument failures retain native tool mode. Unpaid v112
  retries may adopt the fix; completed historical requests stay byte-equivalent.

- Historical v112-v118 enforce at most one wait in any three committed replies per role.
  Two non-wait replies must follow a wait; silent stationary continuations also
  consume the allowance. Spoken or gesture-only stationary continuations remain
  non-wait replies. Store only two wait flags per role; cancellation, timeout,
  tool rounds and retries never advance or reset them. Include the allowance in
  scoped context after tools, use bounded field feedback on violation, and keep
  old pinned requests unchanged. Never substitute a forced action or invented fact.

- V111 adds permanent no-restatement dialogue guidance to both investigation and
  concealment roles, based on v109. Permit brief agreement, attributed short
  quotations and silence when obligations allow; never demand invented novelty.
  Preserve raw speech and old paid prefixes. This is guidance, not a similarity
  rejection/filter or an additional review call. V110 remains an unactivated
  repeated-wait experiment, not the base for new production instructions.

- V109 synchronizes setup/tool limits through model_contracts and checks the
  current published prefix at startup. Preserve uncapped authorized citations
  for human and AI inputs. Active-memory repair uses upsert/archive, standalone
  repair uses a snapshot. Scoped old event receipts may be restored as background
  on an unpaid retry, never as new arrivals or global destination disclosures.
  Run the offline contract gate plus fresh real-game acceptance; a finished or
  paused runner is not a passed chain. Preserve historical paid request bytes.

- V108 supplies per-utterance disclosure sources from the speaker's knowledge
  snapshot, before that turn's action. Later acquisitions and event-review source
  visibility must not retroactively authorize a disclosure. Give exact scoped
  correction feedback; preserve speech and actual presentation receipts. HTTP 402
  must explain insufficient provider balance, stop automatic requests and allow
  an explicit retry after top-up while reusing successful stages.
  Memory repair must distinguish entry-count overflow from text overflow: do not
  allocate one text edit per rejected entry when the count itself is invalid.
  Request a newly grouped snapshot while preserving attribution and sources;
  retain the 12-entry, below-1024-character and 2048-token summary limits.
- V107 fixes cumulative citation drift: a valid 12-to-13 testimony delta must
  not fail an ordinary action. Ensemble reasoning, final submissions and reviews
  have no arbitrary citation-count cap; preserve source authority, text/token
  budgets and original histories. Keep legacy request bytes and successful paid
  stages stable. Return field-specific validation feedback within bounded retries.
  Acceptance for reliability changes must include a fresh real-model game reaching
  actual submissions, evaluation and ending. Pauses or short probes are not an
  end-to-end pass. Record test budgets, any manual recovery and all failed trials.
- V106 supplies bounded creator-known background separately from new event
  receipts. Background may support validity judgments but never counts as a
  post-wait arrival or advances a review cursor. Keep source permissions aligned
  with supplied creator context and expose actionable, scoped source feedback.
  Failed v105 operations receive a persisted correction only on a new retry;
  paid requests retain their original bytes and successful stages are reused.
  Keep the current game paused for the user's retry, with no production test call.
- V105 reduces repeated role/DM context with versioned field deltas, exact
  source-body reuse and per-event dirty checks. Permanent contracts stay in the
  immutable prefix; phase-specific guidance enters the dynamic suffix only
  while applicable, and retry feedback remains until a successful attempt.
  Event review consumes pending receipts chronologically and commits only the
  reviewed cursor. A missing independent DM judgment can be repaired separately
  only after every retained field validates. Keep source permissions, full
  originals, fixed-event ownership and atomic application intact. Prioritize
  acquired originals in role views, allow more at final submission, and make
  omitted bodies explicitly retrievable instead of implying missing evidence.
  Short nine-entry memories alone no longer cause early consolidation; the
  1,024-character trigger, below-1,024 summary and 2,048-token cap still apply.
  Preserve the existing stagnation pause, player agency and all paid artifacts.
  Real acceptance uses synthetic fixtures; inspect production transcripts only
  locally unless their external reuse is explicitly authorized.
- V103 follows the user's revised memory policy: consolidate when combined
  entry.text reaches 1,024 characters and require standalone summaries below
  1,024 characters, with max_tokens=2048 for the entire JSON. Count punctuation
  and whitespace in text, excluding source IDs and JSON fields. Ordinary role
  updates can cross the trigger; do not reject their actions for this threshold.
  Recompose concise sourced topics, never slice prose or cap citation counts.
  A failed summary stays unapplied. A bounded retry may use the last rejected
  draft as untrusted editing material; it grants no knowledge or source access.
  Preserve paid requests and old prefixes. Keep the production game paused until
  the user's explicit retry; verify long real inputs in an isolated store.
- V99 limits standalone ensemble memory consolidation to 2,048 output tokens.
  Ordinary role decisions retain 6,144 tokens, including incremental memory.
  Keep the same cap on retries, never save truncated output, and preserve older
  pinned operations and published prefix artifacts.
- V98 uses the existing request max_tokens budget for memory output, with no
  total, per-entry or derived-summary character ceiling. Remove character-based
  compaction targets/triggers from new requests. Keep complete JSON, nonempty
  text, source authority, chronological checkpoints, the 12-entry structure,
  original receipts and bounded retries. Never save a length-truncated response.
  Preserve old paid request bytes and pinned scheduling during recovery.
- V97 isolates final culprit admissions from non-culprit assessments and objective
  results. Investigator cooperation requires investigator-established truth;
  confession cannot unlock their victory or rewrite their individual commentary.
  Overall case closure and culprit avoidance can still reflect a supported
  admission. Preserve historical scores and pinned pre-v97 behavior.
- V96 separates concealment-position assessment from investigation grading.
  Assess denial/redirection/withheld judgment against actual final evidence;
  never penalize a culprit for failing to solve their own case or infer another
  role believed a lie. Only explicit structured self-identification selects
  admission proof review. Engineering retains objective/shared-outcome rules.
  Keep task traces generic, sources scoped, old receipts pinned, and saved
  outcomes unchanged when adapting historical page display.
- Historical V94 treated roughly six topics / 400-550 characters as advisory
  memory targets. V98 supersedes its text ceilings and character triggers.
  Keep source authority, kinds, chronological checkpoints and archived originals
  strict. Version new compaction scheduling and length metadata; suppress idle
  rewrites and preserve paid historical requests during explicit recovery.
- V93 budgets role and memory working views against serialized bytes. Preserve
  supplied recent receipts, complete stored originals and uncapped memory
  citations. Old evidence bodies and historical indexes can load through scoped
  list_sources/read_sources tools; partial request indexes never define citation
  authorization. Keep native receipts exact and historical paid requests pinned.
- V88 preserves source origins alongside acquired originals and memory. Source kinds
  identify acquisition, testimony and private initial facts; never promote a spoken
  document description into an original document field or rewrite player prose.
- Murder final submissions name every supplied grading dimension with explanation,
  evidence IDs, testimony IDs and gaps. Code derives the combined citation list.
  Frozen rules and old submissions are not retroactively changed. Rule-version 5
  cases retain numeric temporal facts and source subjects; code computes intervals
  and intersections only from authorized originals, never arbitrary speech.
- Fixed workflow transitions and custom listener end_on targets belong to the
  engine. DM event decisions declare a structured basis; claimed workflow changes
  are validated against the actual scoped state with persisted retry feedback.
  A vote is not a phase transition. Semantic feasibility remains DM-owned.
- V89 distinguishes validity reviews of a wait subscription from custom event
  completion. A supported legacy completed-purpose reply ends only that wait,
  retains its reported status/sources, and never completes shared work. Per-record
  status contracts and schema retry feedback stay scoped and versioned. Preserve
  already-paid requests and leave errored spectator games paused for user retry.
- The user removed arbitrary memory source-ID count limits on 2026-11-08.
  V91 uses entry/text and actual request-body budgets; the old 8/20/30 ID caps
  no longer reject updates, including pinned recovery. New operations do not
  compact merely because the reference count grows. Keep authorization, unique
  nonempty source lists, checkpoints, original records and archived versions.
  Preserve historical prefixes and paid request bytes; never truncate citations.
- V92 source feedback identifies an unread target only if its ID is already in
  that role's action menu. Memory updates precede chosen action execution; cite
  received observations for heard claims or unresolved leads until the original
  is actually acquired. Do not grant source access from an unavailable lookup.

The user authorized implementing the deduction improvements and clarified that
each game's truth and initial character scripts must be fixed at the start.
Subsequent human and AI actions and speech determine developments and endings.
Do not prescribe an act count or end an investigation after a fixed number of
interactions. Case creation fixes past facts, not future choices or an ending.

The user confirmed on 2026-11-04 that the primary appeal should be progressively
deducing the truth in a murder mystery. Prioritize a coherent case, grounded
clues, conflicting testimony and an evidence-supported reconstruction. Social
relationships and deception serve investigation. New setting variety and model
task coverage alone do not satisfy this goal. The next bounded design is
[Demo 02: progressive deduction](docs/16-demo-02-deduction.md); its concrete case
and runtime changes are implemented for new games, with verification recorded in that module. Seven distinct bounded scenario categories now use the complete runtime in module 17.

## Confirmed Shared Requirements

On 2026-11-05 the user authorized completing all missing and partial requirements
from the audit, including multiplayer, scenario mechanics, the original murder
opening and the social/physical consequences. The execution contract and current
acceptance status are in [Complete playable runtime](docs/17-complete-playable-runtime.md).

On 2026-11-06 the user authorized full fresh playthroughs and improvements to
causal variety, role interaction, difficulty and recovery. The findings and
versioned implementation are recorded in module 17; human difficulty and
narrative quality must not be inferred from contract tests alone.

### Spectator Mode

On 2026-11-06 the user approved a separate all-AI spectator mode (观海). A spectator
occupies no character seat and can inspect the whole story, but cannot alter truth,
speak as a role or supply hidden hints. Role contexts do not identify controller
types, human counts, spectator presence, speed or spending controls. Use the same
role and DM logic. Shared closure requires three of four characters to agree,
followed by independent final conclusions; operational limits pause rather than
end a story. Default budget is USD 0.10, warning at 80%, with an initial 128 calls
including failures/retries. The observer can separately add USD 0.05 or 64 calls;
neither addition automatically resumes play. The user explicitly replaced the
fixed call ceiling with manual extensions on 2026-11-06. Pause after twelve decisions
without meaningful progress once each role has had at least two opportunities.
See [Spectator mode](docs/18-spectator-mode.md) for the execution contract.

### Category Selection and Story Introduction

- Users select a story category and receive a generated introduction before confirming a game.
- The introduction is a preview that must not interfere with subsequent play. The current design interprets this as a spoiler-free public overview and a preview phase with no gameplay progression.
- New previews generate three independent public candidates in one model call and select one durably. Only the selected candidate enters initialization. Use no prior player stories, fixed setting catalogue, output blacklist, or extra self-review call to obtain variation.
- New previews generate their own character names together with the premise, fitting each story's setting and people. Do not supply a fixed name pool. Freeze the selected names for setup and play; preserve older saved names and version-pinned recovery.
- Codex is responsible for proposing categories and expanding their scenario modules from the user's examples. Seven current categories and their supported effects are specified in module 17; broader variants remain proposals.

### Characters and Relationships

- A game supplies a setting, premise, participant count, personas, relationships, and individual memories.
- Characters may have different memories of the same or related events.
- Support four seats with one to four humans; real AI fills the remaining seats, including an all-human mode. Separate spectator games have zero human seats.
- Relationship memory has an initial relationship file and can evolve during play.

### Memory State and Information

- Memory output consumes required schema fields and ignores extra annotations.
  Preserve raw model receipts; unused fields must not enter stored memories or
  archives. Required values, source permissions, output budgets and chronological
  checkpoints remain strict, including recovery of historical pinned operations.
- Characters require initial memory, event memory, relationship memory, and state information.
- Actual world state, discoverable information, and individual knowledge are distinct.
- Arrival receipts preserve the visible occupants at arrival, separately from who can hear the current channel. Private conversations remain isolated from outside activity. The spectator's third-person movement projection never enters role knowledge or rewrites original receipts.
- Traces may exist without their creator noticing them. Some known evidence is handleable; other evidence is restricted by scenario conditions.
- Evidence existence, knowledge, interpretation, ownership, and handling permissions are distinct.
- Track each role's investigation visits, actual checks and completed searches separately from testimony. Receiving a presented record does not mark its source area explored. Spoken reports remain attributed dialogue/memory, not acquired document records or completed personal actions. Exploration context must not reveal hidden contents of unvisited areas.
- Conditional investigation reminders may highlight personally unchecked areas during normal role decisions, based on actual own investigation and received information. Keep them optional, scoped and rate-limited; do not force movement, require full-map completion, wake waiting roles or add reminder-specific model calls. See the memory module for thresholds and verification.
- A character who knows they committed the crime assesses exposure and plans responses from their own information; do not ask them to rediscover the culprit. Keep their factual self-knowledge, private strategy and chosen outward position separate. Investigators continue to build evidence-based deductions.
- Public and individual discovery are candidate information scopes; exact policies remain scenario decisions.

### Communication and Player Agency

- Public character communication is local to one area. Private invitations and
  accepted conversations require co-location; an absent character cannot receive
  speech, presented evidence, questions or invitations remotely. A move can carry
  optional actor-authored speech before departure. Observers see local departure
  or arrival, not an engine-supplied remote destination/origin. Preserve these
  boundaries in structured receipts as well as prose and retain historical saves.
- Character-authored speech, thoughts, personal memory, deductions and relationship reasons use first-person self-reference (我), not the character's own proper name. Apply this through versioned generation context and input hints; preserve human words, attributed quotes and authoritative history.
- Speech is not required every round. A character who receives a question addressed to them must respond with words or a selectable nonverbal reaction.
- Require an actual spoken contribution at a configurable interval of several dialogue rounds. Pure gestures do not satisfy this periodic speech requirement.
- An event that creates an explanation requirement for a character requires a spoken response, once that character has received the relevant event or challenge.
- An additional button provides optional private input for the character's thoughts and intended actions. Supplying this input is not required each round.
- Private character input is distinct from private conversation: thoughts and plans are not sent to the player's conversation partners or other characters.
- A spoken claim is a communication event. Physical actions and claimed past results are established by actual action resolution, not by the claim alone.
- Actually heard speech is optional usable information, including older observations outside the recent-message window. Roles may cite, trust, challenge or ignore it. Receipt does not establish truth; unheard speech and another role's private thoughts remain inaccessible.
- When a character lies, the system may probabilistically attach observable behavioral details to the utterance. These are generated cues, distinct from deliberate response choices such as nodding or shaking the head.
- DM microexpressions consider claim truth, speaker knowledge, persona and conversational pressure. They accompany the exact utterance in the dialogue UI. Honest stress and composed deception remain possible; cues must not expose internal verdicts or hidden motives, and ordinary lines can have no cue. Preserve actual listeners and visual-location boundaries.
- Private conversation requires a public invitation to the intended partner and that partner's agreement.
- Refusal or no response does not start a conversation. Its content is delivered to the participants; the invitation is public.
- After agreement, create a dedicated private-conversation DM for that conversation and use it until the conversation ends. Its lifetime spans the conversation, not a single message exchange.
- During a private conversation, its participants do not automatically learn about events or conversations outside it. On returning, they may choose to ask others what happened.
- During ordinary active play, AI characters may decide actions and speech in the background, including inviting other AI characters to private conversations under the same agreement rule.
- Background AI conversations end after eight utterances or 300 active seconds; the agenda counts actual speech and gestures and freezes timers during pause.
- Either participant may end a private conversation immediately, including before answering a private question or challenge. The caps are upper limits, not minimums; no partner consent or DM approval is required to leave. Preserve the dialogue, without transferring unanswered private response obligations to the public channel.
- Role decisions may continue or wait for selected known events. Fixed lifecycle outcomes are checked by code. Natural-language personal event proposals and early-end conditions are evaluated by the scoped DM against the creator's acquired information. Record observations during waiting without polling the role; direct contact can interrupt it. No new information means no DM polling either.
- Role waits have bounded active-time deadlines. A timeout ends a subscription and wakes its owner once, without asserting that the underlying event succeeded. The DM judges contextual validity from generic conditions and permitted current circumstances; do not add scenario-specific or empty-room cancellation heuristics. Pause timers during player pauses and retain pinned historical behavior.
- Characters can develop intentions from relationships, goals, and limited knowledge. Humans decide their own characters' subsequent discretionary actions.
- Acting and declining an opportunity both contribute to later developments. Other characters and events progress under the chosen time model.

### Prefix Isolation and Cost Prerequisite

- Reliable independent prefix caching and cost control are prerequisites for the agent and DM architecture.
- Published stable prefixes are immutable. Main DM, private DM, and character contexts retain separate state and permission boundaries; one conversation cannot mutate another context's prefix or history.
- Reuse identical authorized instruction material where possible, while keeping private memories, hidden facts, and per-role state in their appropriate scopes.
- New events, current relationships, acquired memories, and conversation turns belong after the frozen baseline. Dynamic updates must not rewrite that baseline.
- Dedicated private DMs reuse stable instructions and carry scoped session increments; their creation does not require duplicating the complete game context.
- Cost evaluation includes all relevant model calls, cache reads and writes where applicable, uncached input, generated output, retries, and other applicable charges. The user selected DeepSeek for all implemented AI tasks; whole-game usage and scoped prefixes are recorded in docs/15-ai-runtime.md, with dated price assumptions in docs/14-deepseek-integration.md. Multi-provider routing remains open.
- On 2026-11-05 the user requested Flash wherever practical. Current tasks, including one-time case setup, inherit DEEPSEEK_MODEL (default deepseek-flash). A more expensive task override needs demonstrated benefit for that task; model price alone does not establish case quality. Preserve previously pinned operations and their accounting.
- The user's latest direction on 2026-11-08 disables thinking for new operations, superseding the earlier low-effort preference. V85 and later send thinking disabled and omits reasoning_effort for all versioned tasks while retaining Flash and existing completion caps. Historical operations retain their pinned settings and required native-tool reasoning, without adding it to character memory or player speech. Caps and real verification are recorded in module 11.
- For thinking responses that actually end at the output limit, a permitted retry may use bounded additional completion allowance recorded with that individual call. Preserve the published prefix version and all completed receipts; reconstruct a paid call with its stored settings. Increased allowance still requires cost admission and does not grant extra attempts or resume a paused game.
- Application-side prefix immutability is distinct from the provider cache's lifetime. Preserve reproducible baselines and support rebuilding eligible caches without altering game facts or visibility.

On 2026-11-07 the user approved context deduplication, compact action menus,
incremental memory/reasoning updates, stable request ordering and scoped feedback
for supported structured actions. Engineering records actual outcomes; roles
decide whether repetition is worthwhile. New real executions append history and
refresh feedback; technical retries do not count as new character actions. The
user also requires three automatic retries after an initial model-call failure,
then a Web error with a user-controlled retry decision. The
[cost optimization design](docs/11-prefix-cache-and-cost-control.md#approved-cost-optimization-design-2026-11-07)
records confirmed requirements, proposed limits and acceptance criteria.
Implemented on 2026-11-08 with versioned compact contexts, sourced incremental memory,
scoped receipts and four-attempt recovery rounds. Preserve existing guards and
pinned recovery; the cost module distinguishes byte projections, real provider
usage and complete-play acceptance.

### Custom Runtime and Dependencies

- Implement PALTER's game scheduling, state transitions, DM coordination, character contexts, and budget policy directly rather than adopting an existing framework.
- Keep the initial architecture small. A logical character or dedicated private DM does not require an independent service, process, or continuously running model loop.
- The demo uses Python 3.12 in the project's dedicated Conda environment, standard-library modules, SQLite, and a local browser interface. Wider product deployment and dependency choices remain open; see the [runtime module](docs/12-lightweight-runtime-architecture.md).
- Keep scenario rules separate from shared execution so additional scenario modules do not require rewriting the runtime.

### Demo Design Direction

- The user wants a demo design document before starting application development, followed by gradual capability expansion.
- The user has raised concerns about open-ended actions, following other characters, DM routing complexity, and excessive randomness. These are constraints to address in the demo design, not confirmation of every earlier free-action proposal.
- The user authorized implementation on 2026-11-04 and selected DeepSeek using DEEPSEEK_API_KEY from .env. Keep credentials server-side and never print or commit them.
- The first implementation was a scripted rule-verification slice, with DeepSeek used only for clue review. The user rejected that scope as insufficient and explicitly requires every designed AI responsibility to make real calls. [AI runtime integration](docs/15-ai-runtime.md) governs the correction; the earlier scripted fixture is an offline regression mode, not the production AI experience.

### Initial Reading and Review Pauses

- Initial script and memory reading precedes autonomous gameplay. Other agents do not perform gameplay actions during this phase.
- Single-human play means one human participant, even with multiple AI characters. Initial reading has no time limit; during play, that human may pause to reread the original briefing.
- A single-human reading pause stops new AI activity. Work already running may finish in the background; its result remains buffered until resume and state validation.
- With multiple human participants, initial reading is timed. A Reading Complete control allows an early start when all human readers are ready, without waiting for the deadline.
- During multiplayer play, reviewing the script does not pause the game.
- Detailed reading, readiness, pause, and background-activity boundaries are recorded in the [time and reading module](docs/08-time-reading-and-background-activity.md).

### Events and Scene Actions

- Gameplay includes world events and actual scene actions alongside conversation.
- Character actions are character-level events, including actions controlled by humans or AI. Use a shared event data structure to describe timing and other execution properties rather than a separate timing mechanism for every action.
- Specific event fields and lifecycle rules remain design proposals. A pending action is distinct from an event that has actually occurred; event scope is distinct from who observes or learns about it.
- Global events support multiple settings, phases, and event types. Night is one possible context.
- Random, scheduled, conditional, and character-caused events are design options.
- Observable consequences can become public while hidden actors, motives, and unobserved details retain their information boundaries.

## System DM Boundaries

The system DM is responsible for receiving character inputs, consulting actual history and character-specific knowledge, resolving events and actions under scenario rules, and presenting each recipient's actual perception. These responsibilities are agreed design boundaries. The current ensemble runtime implements scoped main/private DM adjudication and seven explicit scenario effect sets; arbitrary physics remains outside the supported contract.

The DM exists outside the fiction. It is not a cast member, witness, suspect, dialogue participant, relationship partner, or eligible target. Its output represents what a character actually hears, sees, or otherwise perceives; it must not introduce the DM as an in-story actor or speaker.

Resolved events, actions, and generated microexpressions are actual occurrences in the game world. Record them consistently before deriving recipient views. Different views may omit details that cannot be perceived, but must not invent incompatible versions of the same occurrence.

Assessing deception requires distinguishing factual contradiction, the speaker's own mistaken beliefs, and information that cannot yet be verified. The DM cannot infer a real human's private mental intention with certainty. Observable cues must not expose an internal truth verdict. Details are in [System DM and deception assessment](docs/10-system-dm-and-deception.md).

The DM's access to truth is for internal adjudication. Outward delivery preserves what the character chose to communicate and any actually observable accompanying behavior. It must not correct an intentional false account into a confession, add hidden motives, or disclose the assessment itself. A character may still voluntarily reveal information through its own speech.

A dedicated private DM handles one accepted conversation. It remains outside the fiction, uses the same authoritative world history and rules, and presents only its participants' actual perceptions. Ending the private DM's session preserves actual events and each participant's acquired memories; it does not expose the private exchange or missed outside events to other characters.

## Scenario-Specific Agreements and Examples

The discussed murder opening uses one actual killer for a designated victim, randomized arrival, human priority among willing killers, and fallback assignment when nobody volunteers. Preserve that example in the [murder investigation scenario](docs/scenarios/01-murder-investigation.md), not as a default for every story.

The new murder runtime limits each actor to one disruption category (document or trace) per 1,440 physical clock units. Repeated attempts in that category still require access and time. This allowance is scoped to murder; other scenarios use their own resources.

Removed evidence and an unrecognized logical inference are different conditions. Neither rewrites history or automatically erases existing memories.

## Shared Design Principles

- **Preserve causal history.** Actions alter current state; previous events and observations remain historically grounded.
- **Respect individual knowledge.** Give AI characters their own memories, beliefs, and actual observations. Update relationships from acquired information.
- **Distinguish public availability from awareness.** A public event can occur while a character is privately occupied. That character learns missed information through later supported observation or communication, rather than automatic memory backfill.
- **Distinguish intention, decision, and outcome.** Resolve attempted actions against actual conditions; a plan alone does not establish success.
- **Make consequences matter.** Object handling, protection, disclosure, and declining opportunities can change later options and outcomes.
- **Scope publication.** Public information communicates observable content, not the system's complete explanation.
- **Separate preview from play.** Browsing an introduction does not execute character decisions, consume game time, or predetermine future outcomes.

## Remaining Product Exploration

The audited missing shared capabilities and seven bounded scenario mechanisms
are implemented in module 17. Its acceptance records distinguish deterministic
contracts, real provider execution, browser behavior and narrative quality.
Open exploration concerns larger casts, hosted accounts, arbitrary multi-step
physical construction, new causal puzzle families, narrative variety and tuning.
Those are broader extensions, not substitutes for the implemented requirements.
Provider cache lifetime remains provider-controlled; measured cache hits do not
guarantee future retention. Existing frameworks remain excluded.

## Document Index

- [Domain glossary](GLOSSARY.md)
- [Game initialization](docs/01-game-initialization.md)
- [Memory state and evidence](docs/02-memory-state-evidence.md)
- [Communication](docs/03-communication.md)
- [World events and scene actions](docs/04-world-events-and-actions.md)
- [Character relationships](docs/05-character-relationships.md)
- [Goals and endings](docs/06-goals-and-endings.md)
- [Category selection and story introduction](docs/07-category-selection-and-introduction.md)
- [Time reading and background activity](docs/08-time-reading-and-background-activity.md)
- [Speech thoughts and action input](docs/09-speech-thoughts-and-action-input.md)
- [System DM and deception assessment](docs/10-system-dm-and-deception.md)
- [Immutable prefixes and cost control](docs/11-prefix-cache-and-cost-control.md)
- [Lightweight custom runtime architecture](docs/12-lightweight-runtime-architecture.md)
- [Demo 01: bounded actions and observations](docs/13-demo-01-action-and-observation.md)
- [DeepSeek integration and usage verification](docs/14-deepseek-integration.md)
- [Full AI runtime integration](docs/15-ai-runtime.md)
- [Demo 02: progressive murder deduction](docs/16-demo-02-deduction.md)
- [Complete playable runtime](docs/17-complete-playable-runtime.md)
- [Spectator mode](docs/18-spectator-mode.md)
- [Scenario catalog](docs/scenarios/README.md)
