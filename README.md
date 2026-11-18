# PALTER

A local AI role-playing game centered on progressive murder deduction. New games
have four characters: one to four humans, with real AI filling the remaining seats,
or zero human seats in the separate all-AI spectator mode (观海).
Each case fixes its past, evidence and private scripts before play. Actions and
speech determine subsequent events and individual outcomes, without a fixed act
count. Seven scenario types have distinct playable mechanisms.

Current deployment: v125, restarted on 2026-11-11. Scheduling input is clearer
without changing the rules.
`passes_consecutive_wait_check` covers only consecutive observation waits;
`message_only_subscription_allowed` independently controls pure message waits.
Candidate events and supported modes are not blanket permissions. Both role
perspectives, listener descriptions and retry feedback use the same terminology.
All 712 regression tests and four synthetic real Flash decisions pass. Fourteen
historical calls retain exact request hashes and validation results.
See [scheduling terms](docs/08-time-reading-and-background-activity.md#distinct-scheduling-terms-2026-11-11-v125).

V124 role exploration entries can
include `no_new_evidence: true` after a successful personal search and acquisition
of all currently discoverable area materials, including revealed hidden records.
Discovery without reading does not qualify. Current-area checks withdraw the
marker for new unread/hidden materials; remote snapshots remain explicitly
historical. Both role guidance and the shared player/spectator display explain
the distinction. All 704 regression tests, 61 focused checks, frontend and
desktop/mobile headless checks pass. Two bounded real Flash decisions receive
the marker and choose movement without another search; complete-game behavior
remains unproven. Existing game/call records are preserved across restart.
See [area evidence completion](docs/02-memory-state-evidence.md#confirmed-area-evidence-exhaustion-2026-11-11-v124).

V123's last unfinished available
role cannot enter a pure message wait while all its peers wait. Concrete event
waits remain available. If an existing all-waiting spectator state cannot advance,
interrupt one subscription for reconsideration; after one opportunity per role
without actual progress, pause visibly instead of repeatedly calling models.
Keep underlying events, private information, final submissions and paid historical
requests intact. All 688 regression tests pass, with 52 focused checks of the final
scheduling changes and headless desktop/mobile checks. Bounded real probes pass
with correction still occasionally required; the fresh USD 0.10 test run paused
for budget after 22 steps, so complete-game acceptance remains unproven.
See [wait recovery](docs/08-time-reading-and-background-activity.md#last-available-role-and-bounded-wait-recovery-2026-11-10-v123).

V122 standalone memory summaries
now have a hard six-entry limit, leaving six slots under the unchanged twelve-entry
active-memory cap. Prompts, request metadata, validation and correction feedback
use the same limit. Eligible pinned capacity failures receive one separately
recorded consolidation after explicit retry; paid requests remain immutable.
All 667 regression tests and three bounded real Flash compactions pass.
See [summary capacity reserve](docs/02-memory-state-evidence.md#summary-capacity-reserve-2026-11-10-v122).

V121's `own_activity` follows the
current action's actual result: immediate actions queue one continuation after
their receipt, while ongoing work waits for completion, failure or cancellation.
Spectator global rows now identify each actual action, with attributed original
materials/receipts in collapsed details; personal histories and speech stay exact.
Regression, two bounded real Flash probes and desktop/mobile headless checks pass.
The paused game and all saved call records were preserved across restart.
See [action completion](docs/08-time-reading-and-background-activity.md#current-action-completion-2026-11-10-v121)
and [spectator presentation](docs/18-spectator-mode.md#event-based-global-timeline-2026-11-10).
Ensemble DM retains independent 512 KB dynamic / 1 MB total request limits,
including retries of pinned older operations. New DM requests share exact
snapshot/source content and encode consecutive citation IDs only when the complete
request becomes smaller. Other task budgets and model settings are unchanged.
Whole-game acceptance remains incomplete and is not established by this deployment.
Setup/tool bounds are shared with backend validation;
startup checks the published schema, and paid historical prefixes remain pinned.
Both role perspectives include guidance against copying another speaker's turn.
V119 permits consecutive waits for other eligible events. One committed reply
without waiting for `next_observation` restores that target; listener aliases count
as the same target. Retries and DM calls do not reset this restriction. Pinned
v112-v118 operations retain the historical three-reply rule.
See [wait policy](docs/08-time-reading-and-background-activity.md).
Role retries retain unresolved corrections across JSON failures; final-format
repair uses JSON output while preserving already received tool results.
Shared reference/text errors provide structured expected constraints, invalid
values or measurements and field paths. Source diagnostics use only the role's
own knowledge; generic patch guidance leaves the correction to the model.
Role dialogue highlights the current speaker and bounded references to their own
and heard utterances; supplied recent speech bodies move to that trailing source
pool without duplication. Communication purpose and attribution guide speech without
filtering repeats, changing the output schema or adding review calls.
See [current fixes and acceptance](docs/11-prefix-cache-and-cost-control.md).
The v118 layout places scoped constants and stable guidance before changing
sources/state, preserving all selected content, request sizes and old request bytes.
Before release, run `.conda-env/bin/python -m palter.check_contracts` and the test
suite. Real spectator acceptance must exit zero with `acceptance_passed=true`;
a pause or a finished runner alone does not establish a complete game.

## Run

Use the dedicated project Conda environment, never base:

```bash
cd ~/my_proj/PALTER
.conda-env/bin/python -m palter
```

Open [PALTER](http://127.0.0.1:8765). The server loads `DEEPSEEK_API_KEY` from the
project `.env` or process environment; credentials stay server-side. Python's
standard library, SQLite and vanilla browser code supply the runtime. Reproduce
the environment with `conda env create --prefix .conda-env --file environment.yml`.
Use `--port 8766` or `--database /path/to/game.sqlite3` for a separate instance.

On Linux with a user systemd manager, run independently of a terminal or coding
session from the project directory:

```bash
systemd-run --user --unit=palter --service-type=exec \
  --working-directory="$PWD" --property=Restart=on-failure \
  --property=RestartSec=3 --property=UMask=0077 \
  "$PWD/.conda-env/bin/python" -m palter
systemctl --user status palter.service
```

Use `systemctl --user restart palter.service` to load code changes,
`systemctl --user stop palter.service` to stop it, and
`journalctl --user -u palter.service -n 50 --no-pager` for logs. This transient
service survives the launching terminal; it is not configured to start at boot.
After a reboot, run the launch command again. Run only one instance per database.

## Play

Choose a category, human count and (for murder) opening style before starting.
The public preview precedes confirmation. A multiplayer host shares the room code;
each participant opens an independent browser session and selects Join Room.
For devices on the same trusted LAN, explicitly bind the server's LAN interface,
for example `--host 192.168.1.20`, and open that exact address and port. The default
remains loopback. Room codes assign seats server-side; players cannot select
another character through API fields or see that character's private script.
This is a local room system, without hosted accounts or public Internet deployment.

Single-human initial reading is unlimited. Multiplayer reading lasts 120 seconds
or ends when every human is ready. During play, single-human reading can pause
new AI work and buffer in-flight responses; multiplayer rereading never pauses
other participants. The optional murder opening collects willingness and scene
handling, gives willing humans priority, and assigns a fallback if nobody volunteers.
Exactly one killing and all initial facts are fixed before investigation begins.

Select **参与方式 → 观海 · 全 AI**, create and confirm a new story, then click
**开始 / 继续** or **单步推进**. The observer can inspect fixed truth, all actual
dialogue and individual role perspectives, but cannot act or speak for a role.
AI roles retain their own knowledge boundaries and are not told an observer is
present. Heard statements are optional information: roles may use, doubt or
ignore them, and receiving a statement does not establish its truth.
Three closure votes open independent conclusions; all four must submit to end.
Pausing, leaving for sixty seconds, stagnation or spending limits preserve the
game rather than inventing an ending. Existing participant games cannot switch
into this mode. See [spectator behavior and acceptance](docs/18-spectator-mode.md).

Investigate locations, question accounts, inspect evidence and take private notes.
Acquired snapshots survive later hiding or destruction of originals. Take, give,
copy, protect, hide, search, destroy and follow have actual supported effects.
Timed activities share the same clock, can be interrupted, and retain incurred
costs. An explicit natural-language action selects a currently supported effect;
unsupported intentions do not become narrated successes.

Public invitations need acceptance. Private conversations have independent
contexts, eight-utterance and 300-active-second caps; participants miss outside
activity. AI-only private conversations continue through an event-driven agenda.
Directed questions require a reply, while evidence challenges, observed evidence
handling and periodic participation can require actual words. All twelve directed
relationships retain trust, affinity and sourced experiences. Private thoughts
and attitude changes remain private.
New role speech, thoughts, memories and private reasoning use first-person
self-reference (我); input hints follow the same convention. Other characters
keep their names, and human words and historical records retain their authorship.

The channel DM can accompany a line with a short contextual microexpression or
vocal detail, displayed beside that exact line. Truth, knowledge and conversational
pressure inform these details, but they are not lie indicators. Only actual
listeners and eligible visual observers receive them; ordinary lines can have none.

Each role has a primary and a personal goal. Complete victory requires both;
innocence alone is insufficient. Final accusation is separate from confrontation.
Every human submits their own conclusion before the truth and all results appear.
A supported murder reconstruction, unsupported correct guess, incorrect account
and unresolved closure remain distinct. Model interpretation has limitations;
code independently checks suspects, cited evidence and frozen proof routes.

| Category | Actual mechanism |
| --- | --- |
| Murder | Three causal families, combined evidence, alternative proof routes, optional voluntary opening |
| Theft | Separate ownership/custody and actual return of the object |
| Family | Disclosures and bilateral commitments that can be withdrawn |
| Council | Four votes, a three-vote coalition, resource pledges and actual transfers |
| Rescue | Shared supplies, timed repair/route clearance and individual evacuation |
| Changing house | Fixed switch conditions, real exit access and personal keepsakes |
| Sealed archive | Fixed dial combination, cabinet access and separately recovered records |

These are bounded rule-supported mechanisms, not arbitrary physical simulation.
The setting, personas, secrets, decisions, interpretation and narration use real
models. Three murder families improve variety but do not establish unlimited
replayability or guarantee that every generated story is narratively strong.

## Models, cost and recovery

New versioned tasks inherit `DEEPSEEK_MODEL` (default `deepseek-flash`) with
thinking disabled and no `reasoning_effort` setting. Current prompts are in
`palter/prefixes/ai-tasks-v108.json`: instructions, JSON contracts, completion
caps and optional task routing. Historical thinking-enabled operations keep
their original settings; their reasoning and final output share the cap. These files
are model task configurations, not game scripts or saves. `manifest.json` verifies
published artifacts; pending operations retain their pinned version.
Thinking responses truncated by the output cap receive bounded extra headroom
on permitted retries. Each call stores its actual settings; completed stages
reuse those settings exactly, without changing old prefix files or receipts.
Investigator arguments and voluntary admissions use 8,192 completion tokens;
ordinary concealment positions use a separate 4,096-token assessment of actual
statements and final evidence, without investigator grades. Investigator outcomes
and cooperation credit are isolated from the culprit's final confession; supported
admission can affect case closure and the culprit's own result. Ending narration
starts with 4,096. These are
maximum allowances, not output targets or guarantees against truncation.
Game data and tool results share a 51.2 KB (51,200-byte) dynamic limit. Native tool reasoning
remains intact under the 90 KB full-request limit and normal cost accounting.
Role and memory requests use budgeted working views: recent receipts stay intact,
older originals load on demand, and partial indexes expose counts and scoped
`list_sources` / `read_sources` pagination. Exact request sizes include tool
continuations and validation feedback. Source lookup is read-only; it never
grants access to unread evidence or other roles' private history.

Every request records its actual model, latency, reported usage, cache hit/miss
and conservative cost estimate. The UI displays an input-weighted cache ratio;
missing usage remains unknown. Role and DM baselines are scoped and immutable.
Long histories are compacted through chronological, sourced role-memory chunks,
while original observations and evidence remain stored.
Memory snapshots and incremental updates ignore extra JSON annotations while
requiring their defined fields and validating their values. Ignored metadata is
kept in raw call receipts, never copied into stored memory or its archives.
The current memory policy uses a 2,048-token completion ceiling for a complete standalone memory JSON
response; a role's incremental patch shares its 6,144-token full-response budget.
Combined entry.text reaching 1,024 characters triggers consolidation before the
next role decision. A completed summary must contain fewer than 1,024 text
characters; punctuation and spaces count, JSON fields and source IDs do not.
Aim for 600-800 characters as advisory headroom, with roughly six sourced topics.
Ordinary incremental patches can cross the trigger without rejecting the action;
no per-entry or hidden derived-summary limit applies. History, entry and actual
request-pressure protections remain, without source-count triggers or caps.
Length stops and oversized complete summaries get bounded corrective retries.
When a complete draft passes source, type and progress checks but exceeds the
text budget, the next retry asks only for shorter texts; engineering preserves
its validated IDs, kinds, citations and checkpoint. The draft remains unaccepted
and grants no source access. Never cut prose, save partial JSON,
raise the output cap or add review calls. Unchanged small memory stays idle.
Historical paid requests and scheduling remain pinned.
V107 removes the leftover 12-testimony and 30-source count limits from ensemble
reasoning and final submission/review paths. Authorization and actual request
budgets remain strict; source lists are never silently truncated. Field-specific
text/reference errors and other contract failures carry corrective feedback in
the existing retry loop, with no extra review model. Legacy thinking length stops
retain their original headroom recovery. Connection errors record a safe error
category/errno instead of hiding every cause behind one generic diagnostic.
V108 gives DM disclosure checks each utterance's pre-action source list; a later
inspection cannot authorize an earlier disclosure. Entry-count memory repairs
request a regrouped snapshot instead of one shortening target per invalid entry.
Provider HTTP 402 stops automatic calls and offers a clear balance message with
an explicit retry after top-up. Complete-game and recovered-run receipts are in
[spectator mode](docs/18-spectator-mode.md#whole-game-acceptance-and-accumulating-references-2026-11-09-v107).
V105 permits field-level memory, belief and strategy patches: unchanged fields
are preserved and source arrays support explicit add/remove operations. An
acknowledgment-only memory update must still name its processed observation.
Short nine-entry memories no longer trigger early consolidation by count alone;
the text, history, twelve-entry structure and actual request-pressure guards remain.
DM context reuses exact source bodies without widening recipient permissions.
V106 separates bounded creator-known background from newly reviewed records,
so a newly registered wait can cite prior speech without treating it as a new
message. Source errors identify invalid references and the creator's allowed
scope. Failed v105 operations can receive this correction on retry while keeping
their already-paid stages and historical request hashes intact.
Only changed custom events are reviewed, in chronological receipt chunks with
atomic cursors. Missing independent event judgments can be repaired without
regenerating already validated judgments. Permanent instructions stay in the
immutable prefix; temporary private-chat, final-submission and event-review
guidance appears in the dynamic suffix only while relevant. Correction guidance
survives failed retries and disappears after success. Stable evidence bodies
precede changing context; final submission allows more originals, and all
omitted originals remain available through scoped source tools.
Conditional investigation reminders highlight personally unchecked areas during
normal role decisions, with a cooldown and no additional reminder call or forced
movement. Roles can continue their own investigation or deliberately wait.

Games start with 128 requests and allow one initial attempt plus three automatic
retries per stage, with two provider slots. After exhaustion, an explicit Web
retry starts another bounded round and reuses completed stages. Every actual
attempt counts toward the call and money budgets. Spectators can manually extend their request allowance
by 64 at a time, including in existing games paused at the limit. Ordinary games retain a USD 0.25 cumulative conservative
admission estimate. Spectator games start at USD 0.10, warn at 80%, and reserve
uncached input plus maximum output before each new call. Unknown usage retains
its reserve. Separate controls add USD 0.05 or 64 requests; neither changes the
other allowance or resumes play automatically. These are application guards, not invoice-enforced ceilings.
Automatic retry progress and all attempt usage stay visible; there is no scripted
substitution. Exhausted retries stop the agenda until explicit recovery or cancellation.
Role contexts deduplicate acquired source bodies and use exact action argument
tuples. Sourced memory entries update incrementally and consolidate when pending
observations or active memory reach their bounds. Full originals remain stored,
with bounded authorized lookup. See [cost optimization and acceptance](docs/11-prefix-cache-and-cost-control.md).

Progress is stored in `.local/palter.sqlite3` and associated with browser sessions.
Refresh/restart restores committed state; operation recovery reuses completed
matching stages. Starting a new game does not archive a multiplayer room still
used by other participants. Existing investigation/item-recovery saves keep their
original frozen facts and runtime; start a new game for the ensemble features.
`--offline` selects the explicitly scripted historical regression fixture.

See [current implementation and acceptance](docs/17-complete-playable-runtime.md),
[scenario modules](docs/scenarios/README.md), and [project conventions](AGENT.md).

## Verify

```bash
.conda-env/bin/python -m unittest discover -v
node --check palter/static/app.js
node --check palter/static/investigation.js
node --check palter/static/ensemble.js
node --check palter/static/spectator.js
node tests/frontend.test.cjs
.conda-env/bin/python -m tests.browser_ensemble
.conda-env/bin/python -m tests.browser_spectator
```

Unit/browser checks use isolated databases and explicit provider doubles. HTTP
and browser checks need loopback permission; browser checks use Edge and the
project's `requirements-dev.txt` in the Conda environment.

The separately paid acceptance runner is
`.conda-env/bin/python -m palter.check_spectator --count 10 --parallel 2`.
It creates only fresh test-owned cases, uses each game's default budget, and
records operational pauses separately from actual endings.
For explicit extended murder-chain acceptance, use `--category murder
--budget-usd 1.50 --call-limit 512 --output .local/verification/<run>`.
These test allowances do not change production defaults. The runner never
forces votes, provides truth hints or resumes a paused/error case to claim success.

Explicit paid integration checks:

```bash
.conda-env/bin/python -m palter.check_ensemble
```

This creates fresh test-owned cases, exercises every scenario and AI task, and
writes attributable receipts in `.local/verification`. It never exports existing
player transcripts. A solution oracle is used for deterministic final assertions;
that is execution evidence, not a human playtest or proof of narrative quality.
