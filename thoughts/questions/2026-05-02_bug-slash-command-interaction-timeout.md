---
date: 2026-05-02
audited: 2026-05-03
status: resolved
---

# Questions: Slash Command Interaction Timeout (10062)

## Context

The original questions pass was useful, but the live branch has moved enough that the
important implementation choices should now be treated as resolved. This file records
the final decisions that make the bug ready to implement.

## Resolved Decisions

### Q1: Inline guard or shared helper?

**Decision:** Use the existing inline pattern:

```python
if ctx.interaction and not ctx.interaction.response.is_done():
    await ctx.defer()
```

**Why:** The ticket explicitly scopes this as a targeted bug fix rather than a broader
refactor. Reusing the exact `ping` pattern keeps blast radius low and avoids adding a
new utility abstraction just for this pass.

### Q2: Which commands should get defer?

**Decision:** Only async-first hybrid commands that do work before their first user
response.

**Why:** Commands that already respond immediately should keep their current UX.
Examples to skip include `help_command`, `robot_commands`, `manual_bgg_update`,
`remind`, `queue`, `nowplaying`, `clear`, and `shuffle`.

### Q3: What about `ephemeral=True`?

**Decision:** Use plain `await ctx.defer()` everywhere in this bug fix.

**Why:** The current audit of `bot/cogs/*.py` found no `ephemeral=True` usage in first
responses, so there is no ephemerality mismatch to preserve here.

### Q4: Do hybrid-group subcommands need their own guard?

**Decision:** Yes. Guard each affected subcommand individually.

**Why:** Group root callbacks only protect the root invocation. They do not cover
`modlog setchannel`, `word random`, or other subcommands.

### Q5: Should slash-incompatible `ctx.message` usage be fixed in this ticket?

**Decision:** Yes, for the two cases found during audit: `Information.invite` and
`Utility.poll`.

**Why:** Leaving those broken would produce a half-fix where timeout-related slash
errors are reduced but those commands still fail under slash for a different reason.

### Q6: What is the right test shape?

**Decision:** Add targeted inline mocks for slash and prefix contexts instead of
introducing a large new fixture layer.

**Why:** `tests/conftest.py` currently provides bot/db/http primitives, but not a
ready-made `ctx` fixture. Inline `MagicMock` / `AsyncMock` setup is the smallest,
clearest way to verify defer behaviour.

### Q7: Does the ChatGPT command belong in scope even though it blocks?

**Decision:** Yes, but only for the defer guard.

**Why:** `askgpt` is still vulnerable to the interaction timeout and should defer. The
legacy synchronous OpenAI call is a separate correctness/performance issue and should
be tracked independently.

## Outcome

No open research questions remain for this bug. The work is ready to move through the
implementation plan.
