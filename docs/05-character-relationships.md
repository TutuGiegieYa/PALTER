# Character Relationships and Relationship Memory

Status: All twelve directed relationships, trust/affinity and sourced experiences implemented.

Last updated: 2026-11-05.

## Current Runtime: 2026-11-05

Every ordered character pair has a private initial relationship, trust, affinity and experience records. AI updates require cited acquired sources and bounded deltas. Humans use their own private reason and choose trust or affinity changes. Role decisions receive their current directed relationships and objectives; no omniscient relationship updates are injected.

Implementation: [complete playable runtime](17-complete-playable-runtime.md). Verification uses `tests/test_ensemble.py`, the multiplayer browser walkthrough and fresh provider receipts listed there. The design alternatives below retain their proposal scope; older implementation sections describe legacy saves.


References: [Conventions](../AGENT.md), [Glossary](../GLOSSARY.md), [State and memory](02-memory-state-evidence.md), [Events and actions](04-world-events-and-actions.md).

## Purpose and Scope

Supply initial interpersonal information and retain how relationships evolve during play. Relationships affect judgment and intentions; new experiences can produce protection, suspicion, cooperation, estrangement, or reconciliation.

Fields, file formats, numerical scales, and update mechanics remain open.

## Confirmed Requirements

- Manage relationships as relationship memory.
- Provide an initial relationship file.
- Allow relationships to change as the story develops.
- Relationships can motivate choices under incomplete information.
- Humans decide their own characters' subsequent discretionary actions.

Protecting an unknown killer is one investigation example. The same mechanism can support family loyalties, faction alliances, debts, dependencies, or shared survival obligations.

## Initial Setup and Per-Game Evolution Proposal

| Part | Purpose | Example |
| --- | --- | --- |
| Initial relationship file | Starting connections, attitudes, and background | A trusts B because of earlier help |
| Current relationship state | Attitudes and connections now | A still cares about B but doubts an account |
| Relationship experiences | Reasons for formation and change | A learned that B's explanation contradicted an observation |

Preserve the scenario's starting setup and derive each game's current state and experiences from it. Paths, schemas, and actual starting data will be chosen during scenario and module development.

Retain reasons for change, not just a final label, so later information can clarify misunderstandings and explain revised behavior.

## Candidate Relationship Dimensions

| Dimension | Possible content |
| --- | --- |
| Connections | Family, friendship, cooperation, competition, and who knows the connection |
| Affection | Care, attachment, distance, resentment |
| Trust | Willingness to believe an account or share a discovery |
| Commitments and interests | Debts, promises, secrecy, aligned or conflicting goals |
| Fear and dependency | Reasons to hesitate, protect, comply, or withdraw |

Dimensions can coexist. A can care about B while distrusting B. A shift in trust does not erase kinship or historical experiences; alliances and promises change through relevant events.

## Direction and Information Boundaries

Track A's attitude toward B separately from B's attitude toward A as a design proposal. Protection can be one-sided or unknown to its recipient.

AI characters use their own relationship information and acquired experiences. The system's hidden attitudes and unobserved actions are not automatically available to them.

Updates should reflect what the character actually experienced or learned. A false account may change beliefs; later evidence may lead to reinterpretation.

An observed behavioral cue may contribute to suspicion under the character's interpretation. The system's private deception assessment is not automatically known to observers and must not become an unexplained relationship update or a memory asserting that a lie was proven.

## Connection to Actions

A candidate progression is:

Initial relationship, acquired information, personal interpretation, updated attitude, action intention, decision, and new experience.

Relationships may affect accepting private-chat invitations, sharing information, investigating together, or protecting someone. Private conversation still requires public invitation and recipient agreement.

How humans express or revise their characters' attitudes remains open. A relationship label alone does not execute a human's discretionary action.

## Investigation Example

1. A starts as B's trusting friend.
2. A finds a letter that seems damaging to B, without knowing B's hidden role.
3. A considers handling it; the human decides whether to act.
4. A later learns B lied, potentially reducing trust while affection remains.
5. Further information can clarify the misunderstanding and change the relationship again.

If A secretly helps B and B does not learn about it, the system must not automatically make B grateful. B can react after acquiring relevant information.

## Module Connections

Event memory records what was experienced; relationship experiences explain effects on attitudes. Evidence and communication supply new information. Scene actions create new shared experiences, cooperation, and conflict.

These mechanisms apply across the [scenario catalog](scenarios/README.md) and retain individual information boundaries.

## Open Questions

- Initial file format, fields, connections, attitudes, and background.
- Natural-language, tag, numerical, or combined representations.
- Direction, dimensions, and visibility.
- Update eligibility, scale, persistence, and supporting event references.
- Human expression of attitudes and presentation of relationship experiences.
- Misunderstanding, broken commitments, repair, and reconciliation.

## Legacy Demo 01 Implementation and Verification

Initial setup supplies each character's directional relationship descriptions. Dynamic trust and sourced experiences are separate from the immutable initial profile. Per-character memory calls can propose a trust delta within [-0.2, 0.2], citing that character's acquired observation IDs; code clamps accumulated trust to [-1, 1]. An equivalent role-keyed response is normalized to the validated list schema without generating content. Unsourced zero changes are ignored. Other roles never receive these private interpretations. Human interpretation does not authorize an automatic human action.


## Legacy Demo 02 Implementation: 2026-11-05

In the investigation runtime, each role has an initial relationship description and its own evolving memory. Applicable role decisions update trust toward the human by a bounded amount and record a private suspect belief; an NPC may suspect the human without changing the true culprit. Final social outcomes reflect those actual beliefs and disclosures. Richer pairwise relationship mechanics remain proposals.
