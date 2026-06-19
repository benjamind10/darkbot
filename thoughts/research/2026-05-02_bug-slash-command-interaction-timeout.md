---
date: 2026-05-02
audited: 2026-05-03
status: ready-for-implementation
---

# Research: Slash Command Interaction Timeout (10062)

## Summary

The bug is real, but the original research snapshot is stale against the current
branch. `Information.ping` is still the only command with a defer guard, but the set of
affected commands and the supporting test/codebase facts have changed:

- `/help` is no longer a good canary; it is sync-first in the live branch
- `tests/conftest.py` no longer defines a `ctx` fixture at all
- `Owner.py`, `Database.py`, `ModLog.py`, `Music.py`, and other cogs have different
  command inventories than the original branch snapshot
- There are two separate slash-compatibility bugs beyond missing defer:
  `Information.invite` and `Utility.poll` both rely on `ctx.message`

This file reflects the current branch and is the source of truth for implementation.

## Current Evidence

- Existing guard: [bot/cogs/Information.py](/home/shiva/Documents/code/darkbot/bot/cogs/Information.py:228)
- No other `ctx.defer(` hits in `bot/`: grep returns only the `ping` call
- `help_command` is sync-first and just delegates to `robot_commands` or builds an
  embed locally: [bot/cogs/Information.py](/home/shiva/Documents/code/darkbot/bot/cogs/Information.py:84)
- `tests/conftest.py` provides `bot`, `mock_db_pool`, `mock_redis`, and
  `mock_http_session`, but no command-context fixture:
  [tests/conftest.py](/home/shiva/Documents/code/darkbot/tests/conftest.py:1)

## Commands That Need a Defer Guard

These commands perform awaited work before their first response and should add the same
guard used by `ping`.

### Information

- `botstats`
- `redisget`
- `invite` also needs a slash-safe replacement for `ctx.message.add_reaction(...)`

### BoardGames

- `bgsearch`
- `bginfo`
- `bggcollection`

Skip `manualbggupdate`: it sends an immediate progress message before the long-running
work starts.

### ChatGPT

- `askgpt`

It still uses the legacy synchronous OpenAI client, but deferring is still required to
avoid the slash timeout.

### MTG

- `card`
- `searchcards`

### Database

- `listusers`
- `adduser`
- `disableuser`
- `enableuser`
- `listboardgames`
- `executesql`
- `boardgame_count`

### ModLog

- `modlog setchannel`
- `modlog disable`
- `modlog status`
- `cases`

The `modlog` group root itself is sync-first and does not need a guard.

### Events

- `events`
- `event`
- `eventusers`
- `nextevent`

### Moderation

The moderation action commands are all async-first and should be audited as a batch.
They perform Discord API work before responding, so they are all good defer candidates.

### Music

- `play`
- `pause`
- `skip`
- `stop`
- `volume`
- `disconnect`

Do not blanket-add guards to sync-first commands such as `queue`, `nowplaying`,
`clear`, and `shuffle`.

### Owner

- `status`
- `name`
- `sync`
- `playing`

### Spotify

- `spsearch`
- `spplay`

### Utility

- `bitcoin`
- `litecoin`
- `currency`
- `currency_to_bitcoin`
- `word random`
- `word search`
- `ip_lookup`
- `poll`
- `translate`
- `weather`

`poll` also needs a slash-safe replacement for `ctx.message.delete()`.

## Commands That Should Not Change

These are good examples of commands that are hybrid but already sync-first or already
respond before long-running work:

- `Information.help_command`
- `Information.robot_commands`
- `Information.ping` (already fixed)
- `BoardGames.manual_bgg_update`
- `Utility.remind`
- `Utility.random_color`
- `Utility.temperature` group and its arithmetic subcommands
- `Music.queue`
- `Music.nowplaying`
- `Music.clear`
- `Music.shuffle`

## Special Cases

### `invite`

`invite` currently does:

- `await ctx.message.add_reaction("🤖")`
- `await ctx.author.send(embed=embed)`

That is prefix-centric. Under slash invocation there is no message object to react to,
so this needs more than just defer. The slash-safe version should respond in-channel
with a confirmation after the DM succeeds or fails.

### `poll`

`poll` currently deletes the invoking message before posting the poll. Slash commands
have no invoking message to delete. The command should skip the delete path under slash
and keep the rest of the behaviour.

### Multi-send Commands

Some commands send more than once (`listboardgames`, `searchcards`, `manual_bgg_update`,
etc.). Deferring is still compatible with that flow because later sends become follow-up
messages under the hood. The important rule is whether a response is sent before the
slow work starts.

## Test Implications

- Use inline `MagicMock` / `AsyncMock` command contexts in targeted tests
- Explicitly set `ctx.interaction = None` for prefix tests
- Explicitly set `ctx.interaction.response.is_done.return_value = False` for slash tests
- Assert `ctx.defer` is awaited for slash and not awaited for prefix

Representative targets:

- `Information.botstats` or `Information.redisget` for a simple defer regression
- `Utility.poll` for the slash-safe `ctx.message` branch
- `Information.invite` for DM confirmation behaviour under slash

## Implementation Readiness

The bug is ready to implement. The remaining work is execution, not more research.
