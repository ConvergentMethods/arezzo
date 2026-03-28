# Plan: Distribution & Community Launch
**Status:** Planned
**Created:** 2026-03-28
**Depends on:** Live testing program, agent adoption docs
**Model:** Varies by step
**Imported from:** Boyce Phase 3 (Distribution & Community Launch), Block 4 (Ecosystem & Adoption)

## Goal

Take Arezzo from "published on PyPI" to "discovered and adopted by agents and
developers." This plan sequences the distribution activities that turn a shipped
package into a used product.

---

## Distribution Surfaces

Imported from Boyce's distribution stack. Arezzo targets the same registries
and channels.

### Tier 1 — Registry Presence (agent discovery)
- [ ] MCP directory submissions: Smithery, PulseMCP, mcp.so, Glama
  (see `_strategy/mcp-directory-submissions.md`)
- [ ] GitHub repo public with proper metadata (topics, description, URL)
- [ ] PyPI metadata complete and rendering correctly (DONE)

### Tier 2 — Content & SEO (human discovery)
- [ ] llms.txt + llms-full.txt deployed (agent docs plan)
- [ ] Product page (convergentmethods.com/arezzo/ or dedicated domain)
- [ ] Technical essay: "Why UTF-16 Index Arithmetic Breaks Every Agent"
  (the Arezzo equivalent of Boyce's Null Trap essay)

### Tier 3 — Community Engagement (adoption)
- [ ] Hacker News Show HN post
- [ ] Reddit r/MachineLearning, r/googlecloud, r/mcp
- [ ] AI agent community posts (Anthropic Discord, OpenAI community)
- [ ] MCP community channels
- [ ] Direct outreach to Google Docs automation tool authors

---

## Sequencing

1. **Registry submissions** — Do immediately after live testing passes.
   Pre-drafted content in `_strategy/mcp-directory-submissions.md`.
2. **GitHub repo public** — Before registry submissions (registries link to GitHub).
3. **Agent docs** — Before community posts (visitors need good docs to convert).
4. **Technical essay** — Before community posts (the "hook" content).
5. **Community posts** — Last. These drive traffic; everything else must be ready.

---

## Technical Essay: "Why UTF-16 Index Arithmetic Breaks Every Agent"

Arezzo's Null Trap equivalent. The essay that demonstrates why the product exists.

**Thesis:** Every agent that edits Google Docs via batchUpdate is silently
corrupting documents. Here's exactly how, here's the math, and here's what
to do about it.

**Structure:**
1. The Google Docs API uses UTF-16 code units, not characters
2. Why Python's `len()` gives wrong offsets (surrogate pairs)
3. Cascading index shifts in batched mutations (worked example)
4. The invisible corruption: no error, wrong output
5. The fix: deterministic compilation (Arezzo's approach)
6. Interactive demo or reproducible example

**Target:** convergentmethods.com/arezzo/utf16-trap/ (or equivalent)

---

## Content Calendar (Will controls timing)

| Week | Action | Owner |
|------|--------|-------|
| Week 0 | Live testing program complete | CC (Sonnet) |
| Week 0 | Agent docs (README audit, llms.txt) | CC (Sonnet) |
| Week 1 | GitHub repo public, registry submissions | Will + CC |
| Week 1 | Product page deployed | CC (Sonnet) |
| Week 2 | UTF-16 essay drafted | CC (Sonnet) + Will review |
| Week 2-3 | Community posts | Will |

---

## Acceptance Criteria

- [ ] All 4 MCP registries submitted
- [ ] GitHub repo public and discoverable
- [ ] Agent docs deployed (llms.txt, llms-full.txt)
- [ ] Technical essay published
- [ ] At least 3 community posts made
- [ ] At least 1 external agent project references Arezzo

---

## Lessons from Boyce Launch

1. **Registry submissions are low-effort, high-signal.** Do them immediately.
2. **llms.txt is the agent discovery surface.** Agents read it before humans read the README.
3. **The technical essay is the human discovery surface.** Hacker News cares about the problem, not the product.
4. **Don't cold-outreach until you have external validation.** Let registry indexing and organic traffic establish credibility first.
5. **The behavioral advertising framework works.** Arezzo already has it in server.py — make sure public docs match.
