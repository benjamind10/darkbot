---
date: 2026-05-03
---

# Structure: Slash Command Interaction Timeout (10062)

## Approach

Ship this as one focused bug-fix pass with three implementation slices:

1. Add defer guards to straightforward async-first hybrid commands.
2. Fix the two slash-incompatible `ctx.message` call sites discovered during audit.
3. Add a small regression test layer that proves slash and prefix behaviour diverge
   correctly.

This stays intentionally narrow: no helper abstraction, no OpenAI client migration, no
error-system refactor.

## Resolved Decisions

### D1: Keep the `ping` inline pattern

**Decision:** Copy the exact inline guard from `Information.ping`.

**Rationale:** The repo already has an accepted pattern, and the ticket is explicitly a
targeted bug fix. Repeating the small guard is lower risk than introducing a new shared
helper across many cogs.

### D2: Fix `invite` and `poll` in the same PR

**Decision:** Treat slash-incompatible `ctx.message` usage as part of this bug.

**Rationale:** Those commands would remain broken under slash even after defer lands, so
excluding them would leave the slash audit incomplete.

### D3: Surgical defer, not blanket defer

**Decision:** Only add guards to async-first commands.

**Rationale:** Commands that already respond immediately should keep their current
interaction UX and do not need a loading state.

### D4: Minimal tests with inline mocks

**Decision:** Use focused per-test context mocks instead of building a large shared
fixture system.

**Rationale:** `tests/conftest.py` already covers bot/db/http dependencies. The missing
piece is just slash-vs-prefix command context, and inline mocks are the smallest fit.

## Vertical Slices

### Slice 1: Straightforward Defer Pass

**Goal:** Guard every async-first hybrid command whose first meaningful work happens
before the first response.

**Files:**
- [bot/cogs/Information.py](/home/shiva/Documents/code/darkbot/bot/cogs/Information.py:34)
- [bot/cogs/BoardGames.py](/home/shiva/Documents/code/darkbot/bot/cogs/BoardGames.py:63)
- [bot/cogs/Chatgpt.py](/home/shiva/Documents/code/darkbot/bot/cogs/Chatgpt.py:33)
- [bot/cogs/Mtg.py](/home/shiva/Documents/code/darkbot/bot/cogs/Mtg.py:42)
- [bot/cogs/Database.py](/home/shiva/Documents/code/darkbot/bot/cogs/Database.py:17)
- [bot/cogs/ModLog.py](/home/shiva/Documents/code/darkbot/bot/cogs/ModLog.py:68)
- [bot/cogs/Events.py](/home/shiva/Documents/code/darkbot/bot/cogs/Events.py:53)
- [bot/cogs/Moderation.py](/home/shiva/Documents/code/darkbot/bot/cogs/Moderation.py:27)
- [bot/cogs/Music.py](/home/shiva/Documents/code/darkbot/bot/cogs/Music.py:95)
- [bot/cogs/Owner.py](/home/shiva/Documents/code/darkbot/bot/cogs/Owner.py:19)
- [bot/cogs/Spotify.py](/home/shiva/Documents/code/darkbot/bot/cogs/Spotify.py:113)
- [bot/cogs/Utility.py](/home/shiva/Documents/code/darkbot/bot/cogs/Utility.py:70)

**Checkpoint:** Each affected command defers only when `ctx.interaction` exists and the
interaction has not already been responded to.

### Slice 2: Slash-Safe Command Fixes

**Goal:** Remove prefix-only assumptions from the two known broken commands.

**Files:**
- [bot/cogs/Information.py](/home/shiva/Documents/code/darkbot/bot/cogs/Information.py:207)
- [bot/cogs/Utility.py](/home/shiva/Documents/code/darkbot/bot/cogs/Utility.py:350)

**Checkpoint:** Slash invocations no longer touch `ctx.message`; prefix behaviour stays
recognizable.

### Slice 3: Regression Tests

**Goal:** Lock in the slash-vs-prefix defer behaviour and cover the two special cases.

**Files:**
- [tests/conftest.py](/home/shiva/Documents/code/darkbot/tests/conftest.py:1) if a tiny
  helper is useful, otherwise leave untouched
- New targeted test file(s) under `tests/`

**Checkpoint:** Tests prove:
- slash path awaits `ctx.defer()`
- prefix path does not
- `invite` and/or `poll` no longer assume `ctx.message` exists for slash

## Not Doing

- Adding a shared `maybe_defer(ctx)` helper
- Migrating ChatGPT to the async OpenAI client
- Refactoring command bodies beyond what is needed for defer placement or slash safety
- Touching commands that already respond immediately

## Rollback

This is one bug-fix PR. If needed, revert the PR as a unit; the change surface is
limited to command-entry guards, two slash-safety fixes, and targeted tests.
