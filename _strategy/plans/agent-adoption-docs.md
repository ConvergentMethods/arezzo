# Plan: Agent Adoption Docs
**Status:** Planned
**Created:** 2026-03-28
**Depends on:** Live testing program (for verified tool surface)
**Model:** Sonnet · medium
**Imported from:** Boyce `_strategy/plans/agent-adoption-docs-sync.md`

## Goal

Ensure all public-facing agent docs reflect the current Arezzo tool surface and
behavioral design framework. When an agent reads the README or any discovery
surface, it should receive the same behavioral hooks deployed in tool descriptions:
loss aversion framing, clear workflow directives, and complete operation lists.

**Hard requirement:** Every piece of public copy must follow the Behavioral Design
Framework. Arezzo inherits this from Boyce's MASTER.md. Read that section before
writing anything.

---

## Context

Arezzo's behavioral advertising framework (in server.py) already implements:
- Two-register tool descriptions (uncertain model + confident model)
- Loss aversion framing ("you cannot safely construct batchUpdate yourself")
- Workflow directives ("call read_document before edit_document")
- Response guidance (next_step, present_to_user, document_reality)

The public docs (README, future llms.txt, product page) need to match this tone.

---

## Files to Create/Modify

### 1. README.md — Dual-Optimized (exists, needs audit)

Verify:
- [ ] Tool descriptions match server.py exactly (after Opus review changes)
- [ ] All 23 operation types listed (not "etc.")
- [ ] Address modes documented with examples
- [ ] Loss aversion framing in the opening
- [ ] Response format documented (next_step, present_to_user, document_reality)

### 2. llms.txt — Agent-Readable Overview (TO CREATE)

- ~50 lines maximum
- Loss aversion framing: what agents are missing without Arezzo
- Current tool surface with operation list
- Address mode reference
- "Response Format" section: behavioral guidance fields
- Deploy at: product page /llms.txt (when site exists), or in repo root

### 3. llms-full.txt — Complete Agent Reference (TO CREATE)

- ~300 lines
- Full operation catalog with parameter schemas
- All address modes with examples
- Error taxonomy (what errors mean, what to do about each)
- Response format with all behavioral fields
- Architecture overview for agents that want to understand the compilation model

---

## Acceptance Criteria

- [ ] README verified against current server.py tool descriptions
- [ ] llms.txt created, under 60 lines
- [ ] llms-full.txt created, complete operation reference
- [ ] All three surfaces use loss aversion framing consistently
- [ ] Operation type list is complete (23 types) in all surfaces
- [ ] No "etc.", "and more", or open-ended lists anywhere
