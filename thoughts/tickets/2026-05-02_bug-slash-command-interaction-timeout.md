---
type: bug
created: 2026-05-02
audited: 2026-05-03
status: ready-for-implementation
---

# BUG: Async-first slash commands can raise Unknown Interaction (10062)

## Description

Some hybrid commands still do network, database, or Discord API work before they send
their first slash response. For slash invocations, Discord expects an initial response
within roughly 3 seconds. If that window expires, later `ctx.send()` calls can fail
with `discord.errors.NotFound: 404 Not Found (error code 10062): Unknown interaction`.

The current branch already has the correct pattern in `Information.ping`:

```python
if ctx.interaction and not ctx.interaction.response.is_done():
    await ctx.defer()
```

This ticket is the repo-wide follow-through: audit every hybrid command, add the guard
where async work happens before the first response, and keep prefix behaviour intact.

## Audit Correction

The original bug write-up called out `/help` as the known broken example. That is no
longer accurate on the current branch: `help_command` is sync-first and should not need
defer. The known-risk surface is now commands like `botstats`, `redisget`, the DB-backed
admin commands, scheduled-event lookups, music/Spotify playback commands, and several
utility lookups.

Two commands also have a separate slash-compatibility bug that should be fixed while we
are here:

- `Information.invite` uses `ctx.message.add_reaction(...)`
- `Utility.poll` uses `ctx.message.delete()`

Both rely on prefix-message state that does not exist for slash invocations.

## Observed Error

```python
discord.errors.NotFound: 404 Not Found (error code: 10062): Unknown interaction
```

## In Scope

- Audit every `@commands.hybrid_command` and `@commands.hybrid_group` subcommand in
  `bot/cogs/`
- Add the interaction defer guard to every async-first command that does work before
  its first response
- Preserve existing prefix (`!`) behaviour
- Fix the two slash-incompatible `ctx.message` call sites discovered during audit
  (`invite`, `poll`)
- Add targeted regression tests for slash vs prefix defer behaviour

## Out of Scope

- Broad command refactors unrelated to the interaction-timeout bug
- Reworking the ChatGPT command to the modern async OpenAI client
- Changing central error-handling architecture in `bot/core/events.py`
- Adding defer to commands that already send a first response before long-running work
  such as `manual_bgg_update` and `remind`

## Acceptance Criteria

- Slash invocations of async-first commands no longer fail with `10062`
- Prefix invocations still work unchanged
- Commands that already respond immediately are left alone
- `invite` and `poll` no longer assume `ctx.message` exists under slash
- Tests cover both slash and prefix code paths for at least one representative command

## Current State

- `bot/cogs/Information.py` has the guard only in `ping`
- The current branch has no shared defer helper and no slash-context test fixture
- The command inventory in the original research needs updating to match the current
  branch
- `thoughts/questions/` and `thoughts/research/` existed, but no matching
  `thoughts/structures/` or `thoughts/plans/` doc existed for this bug before the
  2026-05-03 audit

## Desired State

Every async-first hybrid command defers safely before doing slow work, slash-only
failure paths are removed, and the repo has a concrete structure/plan artifact that is
accurate for the live branch.
