# Scenario Module Catalog

Status: Seven distinct bounded scenario runtimes implemented; broader setting variants remain design material.

Last updated: 2026-11-05.

## Design Responsibility and Scope

The user's concrete stories are examples of mechanisms. Codex is responsible for expanding them into scenario modules with their own settings, initial memories, relationships, objectives, actions, event possibilities, constraints, and endings.

All seven categories now have distinct executable state changes, primary/personal
objectives and outcome rules in [the complete runtime](../17-complete-playable-runtime.md).
Murder deduction remains the main product focus. New games support one to four
humans, with AI filling the remaining seats. Older saves retain their original
rules. Each module separates its current implemented policy from broader design
illustrations; the latter are not an assertion of arbitrary simulated physics.

## Modules

| Module | Category proposal | Distinct design focus |
| --- | --- | --- |
| [Murder investigation](01-murder-investigation.md) | Mystery and Investigation | Generated opening, conflicting accounts, evidence handling |
| [Theft and deception](02-theft-and-deception.md) | Mystery and Investigation | Custody, ownership, recovery, hidden exchanges |
| [Reunion and family secrets](03-reunion-and-family-secrets.md) | Relationships and Drama | Memory, private loyalties, disclosure, reconciliation |
| [Council and succession](04-council-and-succession.md) | Factions and Negotiation | Commitments, legitimacy, coalition changes |
| [Isolation and rescue](05-isolation-and-rescue.md) | Adventure and Survival | Shared resources, competing priorities, routes |
| [The changing house](06-the-changing-house.md) | Horror and the Uncanny | Uncertain perception under consistent world rules |
| [The sealed archive](07-the-sealed-archive.md) | Puzzles and Exploration | Partial knowledge, mechanisms, interpretation |

## Shared References

- [Conventions](../../AGENT.md)
- [Initialization](../01-game-initialization.md)
- [Memory state and evidence](../02-memory-state-evidence.md)
- [Communication](../03-communication.md)
- [Events and actions](../04-world-events-and-actions.md)
- [Relationships](../05-character-relationships.md)
- [Goals and endings](../06-goals-and-endings.md)
- [Category selection and preview](../07-category-selection-and-introduction.md)

No module inherits murder, nighttime-only opportunities, mandatory betrayal, or a particular ending merely because another module uses it.
