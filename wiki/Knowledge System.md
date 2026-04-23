## Summary
AgentAscend uses an LLM-Wiki style knowledge system that is viewable in Obsidian and organized by strict folder boundaries.

## Components
- `/raw` stores unprocessed notes, scraped text, and incoming source material.
- `/wiki` stores structured knowledge pages that follow `system/schema.md`.
- `/system` stores system-level rules, purpose, and schema definitions.
- `[[wikilinks]]` connect pages into a navigable knowledge graph.
- `.obsidian/` settings make the repository readable as an Obsidian vault.

## Relationships
- Used by [[Hermes Agent]]
- Constrained by [[System Rules]]
- Supports [[Tool System]]
- Part of [[AgentAscend]]

## Notes
- Raw notes must be added to `/raw` first.
- Structured concepts must be created or updated in `/wiki`.
- System instructions must only be kept in `/system`.
- Do not mix these folders; this separation is required for clean Obsidian navigation and safe agent operations.