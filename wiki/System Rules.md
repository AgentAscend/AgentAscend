## Summary
Defines the operating constraints for AgentAscend, including strict knowledge-folder boundaries for the LLM-Wiki workflow.

## Components
- Knowledge boundary rules (`/raw`, `/wiki`, `/system`)
- Access control and payment enforcement
- Safety and execution guardrails

## Relationships
- Applies to [[Hermes Agent]]
- Enforced by [[Tool System]] and backend routes
- Supports [[Knowledge System]]

## Notes
- Put unprocessed notes in `/raw`.
- Put structured pages in `/wiki`.
- Put system definitions and rules in `/system`.
- These boundaries are mandatory to keep the Obsidian vault clean and auditable.