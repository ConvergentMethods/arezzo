# MCP Directory Submissions — Arezzo

Pre-drafted content for all four MCP/AI tool registries. Copy-paste when Will
gives the go. Adapted from Boyce's submission template.

**Prerequisite:** PyPI publish complete (DONE — https://pypi.org/project/arezzo/)
**Prerequisite:** Live testing program passes (see `plans/live-testing-program.md`)

---

## Canonical Content (source of truth for all submissions)

### Name
```
Arezzo
```

### Tagline (<= 80 chars)
```
Deterministic compiler for Google Docs API operations — correct index arithmetic for agents
```

### Short description (<= 160 chars)
```
Compile semantic document edits into correct Google Docs batchUpdate requests. UTF-16 arithmetic, cascading index shifts, OT-compatible ordering. MIT licensed.
```

### Long description (Markdown, ~300 words)

```markdown
Arezzo is an MCP server that compiles semantic editing operations into correct
Google Docs API `batchUpdate` request sequences — deterministically.

**The problem:** AI agents editing Google Docs via the batchUpdate API must
calculate UTF-16 code unit offsets for every mutation. Insert 10 characters at
position 50, and every subsequent index in the batch is wrong. A single
miscalculation silently corrupts the document with no error message. The agent
cannot detect or recover from this.

**What Arezzo does:**

- **Deterministic Compiler** — Semantic intent → correct batchUpdate requests.
  Same inputs, same output, every time. Zero reasoning in the compilation path.
- **UTF-16 Index Arithmetic** — Proper surrogate pair handling for emoji, CJK
  supplementary characters, and all non-BMP Unicode.
- **Address Resolution** — Target locations by heading name, named range,
  bookmark, document start/end, or absolute index. No manual offset calculation.
- **Two-Phase Compilation** — Content mutations in reverse index order, then
  format mutations. OT-compatible request sequencing.

**3 MCP tools:**

- `read_document(document_id)` — Structural map: headings, named ranges,
  tables, bookmarks, section boundaries. Call before editing.
- `edit_document(document_id, operations)` — Compile + execute. 23 operation
  types: text, formatting, tables, lists, images, headers/footers, footnotes,
  named ranges.
- `validate_operations(document_id, operations)` — Dry-run compilation.
  Inspect the exact API calls before they execute.

**Zero configuration beyond OAuth:** `pip install arezzo && arezzo init` walks
through Google OAuth setup and writes platform config files.

Named for [Guido d'Arezzo](https://en.wikipedia.org/wiki/Guido_of_Arezzo)
(~991-1033), the monk who standardized music notation — turning vague melodic
intent into precise, portable notation. MIT licensed.
```

### Install command
```
pip install arezzo
```

### GitHub URL
```
https://github.com/ConvergentMethods/arezzo
```

### PyPI URL
```
https://pypi.org/project/arezzo/
```

### Product page
```
https://pypi.org/project/arezzo/
```

### Category / Tags
```
Categories: Productivity, Document Editing, Developer Tools, Automation
Tags: mcp, google-docs, compiler, utf-16, document-editing, agents, llm, automation
```

### Tool count
```
3
```

### Language / Runtime
```
Python 3.12+
```

### License
```
MIT
```

---

## Registry-Specific Submission Notes

### Smithery — https://smithery.ai

- Submit at: https://smithery.ai/submit (or search for "submit server")
- Smithery indexes from GitHub — may auto-discover or require PR to registry
- Use long description; Smithery renders Markdown

### PulseMCP — https://pulsemcp.com

- Submit at: https://pulsemcp.com/submit
- Requires: name, description, GitHub URL, category
- Check for JSON manifest requirement

### mcp.so

- Submit at: https://mcp.so
- Use short description + tags

### Glama — https://glama.ai

- Submit at: https://glama.ai/mcp/servers
- Glama indexes MCP servers; may pull from GitHub automatically
- Adjust to their character limits

---

## Pre-Submission Checklist

- [x] PyPI publish complete — `pip install arezzo` works in a clean env
- [ ] GitHub repo is public (ConvergentMethods/arezzo)
- [ ] README is publish-ready (reviewed, correct version, no stale content)
- [ ] Live testing program complete (Tier 2 + Tier 3)
- [ ] Version number consistent across: PyPI, README, docs
- [ ] All 4 MCP platforms tested end-to-end

---

## Post-Submission

After submitting to each registry:
- Note submission date in this file
- Check indexing within 24-48h
- If registry requires changes, update canonical content above and re-submit
- Add registry URLs to ASSETS.md once listed

---

*Draft prepared 2026-03-28. Adapted from Boyce's mcp-directory-submissions.md.*
