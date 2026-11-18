# DeepSeek Integration and Usage Verification

Status: Current ensemble runtime implemented; historical legacy measurements retained below.

Last updated: 2026-11-10.

References: [Conventions](../AGENT.md), [AI runtime and current verification](15-ai-runtime.md), [Prefix/cost requirements](11-prefix-cache-and-cost-control.md), [Launch](../README.md).

## Current Scope

The active ensemble runtime uses real provider calls for introduction, setup,
role decisions, scoped DM interpretation, memory consolidation, reviews and ending.
The current prefix contains 29 task definitions, including retained legacy tasks;
this is not a claim that every game invokes all 29. The earlier ten-task demo
is historical; its verification remains in module 15. The playable ensemble and
current acceptance records are in modules 17 and 11. Offline fixtures are explicit
test adapters, never a provider-failure fallback.

## Provider Contract

- Use https://api.deepseek.com/chat/completions through standard-library urllib.
  Credentials are loaded server-side from DEEPSEEK_API_KEY. Dotenv assignments are
  parsed as data, never executed. Redirects are blocked.
- Default model: deepseek-flash; configurable alternative: deepseek-v4-pro.
- Rechecked on 2026-11-05: the official pricing page maps deepseek-flash to
  DeepSeek-V4.1-Flash-1017. The old deepseek-v4-flash aliases route to the same
  current model. Current PALTER tasks inherit the configured model, including
  case setup, following the user's preference for Flash. Older pinned operations
  retain their original routing. This is a project choice, not a cross-provider
  quality ranking. [Official models and pricing](https://api-docs.deepseek.com/quick_start/pricing/).
- Require a JSON object for final content, disable thinking, and validate both
  schema and referenced IDs before committing effects. Native role calls normally
  use text response mode with tools. V113 switches malformed-final-JSON retries
  to json_object and tool_choice=none, retaining received native tool messages;
  ordinary successful decisions do not gain an extra model call. Empty/truncated
  output still fails. Other JSON tasks retain their existing settings.
  Current task output caps range from 1,204 to 8,192 tokens. Ordinary role
  decisions use 6,144; standalone memory summaries use 2,048. Dynamic input is
  capped at 51,200 bytes and the full serialized request at 90,000 bytes.
  Memory consolidation starts at 1,024 combined text characters (or structural
  pressure); summaries must contain fewer than 1,024 text characters and at most
  12 entries. Source IDs remain authorized and uncapped by citation count.
- A syntactically valid but semantically equivalent relationship map can be
  normalized to the expected list. This carries the original model values; it
  does not invent a decision or substitute authored content. Malformed JSON,
  unknown references, and unsupported effects fail visibly.
- Preserve protected raw responses/results for diagnostics. Player traces contain
  metadata only. Failed output still retains its actual reported usage.
  Shared reference/text failures attach a versioned validation receipt with
  expected constraints, actual invalid values or measurements and expanded field
  paths. Source types are recipient-scoped; unknown IDs reveal no hidden origin.
  The generic correction is dynamic, does not add a provider call or change
  prefix bytes, and is persisted with each paid request for exact replay.
- Spectator games start with 128 provider requests and USD 0.10 of estimated
  budget. Users may add 64 calls or USD 0.05 at a time. Each retry round allows
  an initial attempt plus three automatic retries, then pauses for explicit user
  retry. HTTP 402 stops automatic retries immediately and permits manual retry
  after top-up. Two concurrent provider calls remain the shared concurrency cap.
  The retained legacy review adapter has its own three-review limit. Calls happen outside SQLite
  transactions. A retry reuses completed stage results with the same request hash.
- Reading starts no role work. Pause blocks new calls and buffers running results;
  resume applies them only against the original unchanged world. Bounded automatic
  retries reuse successful stages; there is no silent scripted fallback or idle
  prewarming loop. Reading or adding budget alone does not resume a paused game.

These provider API details were checked against the official documentation on
2026-11-04: [API](https://api-docs.deepseek.com/),
[JSON output](https://api-docs.deepseek.com/guides/json_mode/),
[thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/), and
[chat-completion contract](https://api-docs.deepseek.com/api/create-chat-completion/).

## Prefixes and Ledger

Published files are checked against palter/prefixes/manifest.json. Production
uses ai-core-v2.txt for ensemble tasks. The current code selects ai-tasks-v119.json;
its event-specific wait policy is recorded in module 08, and combined deployment
acceptance is recorded in module 11. The default
version is defined in model_contracts.CURRENT_PREFIX; startup and
`python -m palter.check_contracts` validate current schema/guidance bounds. Earlier task versions remain untouched
for diagnostic provenance; review-v1.txt remains the historical review adapter's
baseline. A new version is published when instructions change.

Each operation pins its task-prefix version, so a later deployment does not change an in-flight operation's instructions. Each request has a fresh independent messages list. Stable system/task material
and the authorized frozen character/private-session baseline precede dynamic
observations and interpretations. The prefix fingerprint includes the model,
settings, and baseline. The final-request hash includes all actual dynamic input.

SQLite ai_operations persists identity, input command, original world snapshot,
status, and receipt. ai_calls persists task, actor, operation/stage, prefix/request
hashes, timing, attempts, reported usage, cost estimate, result, and protected
response/diagnostic data. Actual role effects carry decision call IDs; cues,
world events, memories, relationships, and endings have their own originating
call IDs. Duplicate committed operations cause no new request or world effect.

Application prefix integrity cannot guarantee provider cache residency. Cache
reuse is established only by reported usage. See the official
[cache guidance](https://api-docs.deepseek.com/guides/kv_cache/).

## Dated Cost Assumptions

The deepseek-usd-2026-11-04-peak-upper rate card uses USD per million tokens:

| Model | Cached input | Uncached input | Output |
| --- | --- | --- | --- |
| deepseek-flash | 0.006 | 0.30 | 1.20 |
| deepseek-v4-pro | 0.044 | 1.32 | 3.96 |

Source: [official pricing](https://api-docs.deepseek.com/quick_start/pricing/).
Actual time-dependent rates can be lower. Estimates use reported cache hits,
misses, and output tokens, not prompt size guesses. Missing usage remains unknown.
Unknown usage reserves USD 0.015 per call. Spectator admission uses that game's
current adjustable budget; the older non-spectator adapter retains its separate
USD 0.25 ceiling. A request already admitted can exceed
that threshold, and unknown usage is not an invoice, so this is no hard monetary
ceiling. The interface labels costs as estimates.

## Current Verification

The 2026-11-09 synchronization fixes and local/real acceptance receipts are recorded
in [module 11](11-prefix-cache-and-cost-control.md). The acceptance runner now
returns nonzero for creation failures, pauses, missing submissions/evaluations or
missing ending narration. Runner completion alone is not a full-chain pass.

### Historical 2026-11-04 Verification

The full real-task matrix completed on 2026-11-04, including private-DM execution,
actual model-selected role events, personal memory/relationship changes, world
event selection, and a generated ending. Details, task counts, costs, failures,
explicit recovery, and browser coverage are recorded in [AI runtime](15-ai-runtime.md).
Fake-provider tests are separate regression evidence, not proof of real-model
execution. Memory compaction has since been implemented and separately verified in module 11.
Cache-expiry, multi-provider and production-load benchmarks remain open.

## Historical Review-Only Measurement

Before the user's scope correction, three actual review requests reported:

| Call | Input | Cache hit | Cache miss | Output | Latency ms | Peak estimate USD |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 553 | 0 | 553 | 16 | 835 | 0.000185100 |
| 2 | 670 | 512 | 158 | 26 | 727 | 0.000081672 |
| 3 | 751 | 512 | 239 | 26 | 779 | 0.000105972 |

All retained the same review prefix and changed no authoritative world state.
The total estimate was USD 0.000372744. The historical headless review button
reported 751 input, 512 cache-hit, 239 cache-miss, and 26 output tokens. These
records verify only that former bounded feature, not the later AI runtime.
