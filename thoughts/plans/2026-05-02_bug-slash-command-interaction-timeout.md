---
date: 2026-05-03
status: implemented
---

# Plan: Slash Command Interaction Timeout (10062)

## Overview

Implement the bug in one focused pass:

1. Add the `ping`-style defer guard to every async-first hybrid command identified in
   research.
2. Fix `invite` and `poll` so slash invocations no longer rely on `ctx.message`.
3. Add targeted tests for slash and prefix behaviour.

See structure doc: [thoughts/structures/2026-05-02_bug-slash-command-interaction-timeout.md](../structures/2026-05-02_bug-slash-command-interaction-timeout.md).

## Current State

- Only `Information.ping` defers today:
  [bot/cogs/Information.py](/home/shiva/Documents/code/darkbot/bot/cogs/Information.py:228)
- Many async-first hybrid commands still await DB/HTTP/Discord work before their first
  response
- `invite` and `poll` contain slash-incompatible `ctx.message` usage
- There is no current test that explicitly asserts defer behaviour for slash vs prefix

## Phase 1: Apply Defer Guards

**Completed:** Added slash-safe defer guards across the phase targets, including the `word` subcommands (`random`, `search`) that implement the planned `word_random` / `word_search` behavior, in `bot/cogs/Information.py`, `bot/cogs/BoardGames.py`, `bot/cogs/Chatgpt.py`, `bot/cogs/Mtg.py`, `bot/cogs/Database.py`, `bot/cogs/ModLog.py`, `bot/cogs/Events.py`, `bot/cogs/Moderation.py`, `bot/cogs/Music.py`, `bot/cogs/Owner.py`, `bot/cogs/Spotify.py`, and `bot/cogs/Utility.py`.

Add:

```python
if ctx.interaction and not ctx.interaction.response.is_done():
    await ctx.defer()
```

as the first meaningful statement in each affected command body.

### Target Files

- `bot/cogs/Information.py`
  - `botstats`
  - `redisget`
  - `invite`
- `bot/cogs/BoardGames.py`
  - `search_boardgame`
  - `boardgame_info`
  - `bgg_collection`
- `bot/cogs/Chatgpt.py`
  - `askgpt`
- `bot/cogs/Mtg.py`
  - `card`
  - `search_cards`
- `bot/cogs/Database.py`
  - `list_users`
  - `add_user`
  - `disable_user`
  - `enable_user`
  - `list_board_games`
  - `execute_sql`
  - `boardgame_count`
- `bot/cogs/ModLog.py`
  - `modlog_setchannel`
  - `modlog_disable`
  - `modlog_status`
  - `cases`
- `bot/cogs/Events.py`
  - `list_events`
  - `event_details`
  - `event_users`
  - `next_event`
- `bot/cogs/Moderation.py`
  - audit each hybrid moderation action and add the guard at the top
- `bot/cogs/Music.py`
  - `play`
  - `pause`
  - `skip`
  - `stop`
  - `volume`
  - `disconnect`
- `bot/cogs/Owner.py`
  - `status`
  - `name`
  - `sync`
  - `playing`
- `bot/cogs/Spotify.py`
  - `spsearch`
  - `spplay`
- `bot/cogs/Utility.py`
  - `bitcoin`
  - `litecoin`
  - `currency`
  - `currency_to_bitcoin`
  - `word_random`
  - `word_search`
  - `ip_lookup`
  - `poll`
  - `translate`
  - `weather`

### Skip List

Do not change commands that already respond immediately, including:

- `Information.help_command`
- `Information.robot_commands`
- `BoardGames.manual_bgg_update`
- `Utility.remind`
- `Music.queue`
- `Music.nowplaying`
- `Music.clear`
- `Music.shuffle`

## Phase 2: Fix Slash-Safe Behaviour

**Completed:** Updated slash-safe `invite` and `poll` handling in `bot/cogs/Information.py` and `bot/cogs/Utility.py`, preserving prefix-only message operations while ensuring slash invocations no longer depend on `ctx.message`.

### `invite`

- Keep the DM embed
- Under prefix, preserve the reaction if desired
- Under slash, do not touch `ctx.message`
- Send an in-channel confirmation or failure message so the slash interaction completes

### `poll`

- Only delete `ctx.message` when a prefix message exists
- Keep the poll-posting flow unchanged otherwise
- Ensure slash invocations can still create the poll after deferring

## Phase 3: Add Targeted Tests

**Completed:** Added focused slash/prefix coverage in `tests/test_hybrid_commands.py` for `Information.botstats`, `Information.invite`, and `Utility.poll`, including slash contexts without `ctx.message`.

Create focused tests that explicitly model slash and prefix contexts.

### Minimum Coverage

- One representative command proves slash path defers and prefix path does not
- `invite` no longer requires `ctx.message` under slash
- `poll` no longer requires `ctx.message` under slash

### Suggested Test Pattern

```python
ctx.interaction = MagicMock()
ctx.interaction.response.is_done.return_value = False
ctx.defer = AsyncMock()
ctx.send = AsyncMock()
```

And for prefix:

```python
ctx.interaction = None
```

## Verification

### Automated

- Run targeted tests for the touched cogs
- Run the broader test suite with `pytest`

### Manual

- Exercise representative slash commands such as `/botstats`, `/events`, `/spsearch`,
  and one moderation command
- Confirm slash `invite` and `poll` no longer fail on missing `ctx.message`
- Confirm representative prefix commands still behave as before

## Risks

- Over-deferring sync-first commands would slightly change UX, so the skip list matters
- `askgpt` still blocks on the legacy synchronous OpenAI call even after defer; that is
  acceptable for this bug fix but should remain visible as follow-up tech debt
- `poll` and `invite` need slightly more than a one-line guard, so those edits deserve
  extra test attention
