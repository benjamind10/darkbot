# Testing Guide

## Automated Tests

```bash
pytest                              # all tests
pytest tests/test_boardgames.py     # single file
pytest -v                           # verbose output
pytest --collect-only               # inspect test and fixture discovery
```

Tests use pytest with pytest-asyncio and `asyncio_mode = "auto"` from `pyproject.toml`.
HTTP mocking uses aioresponses. Test files live in `tests/`.

## Test Fixtures

Reusable fixtures live in `tests/conftest.py`:

- `bot` provides a lightweight bot stub with `config`, `db_pool`, `http_session`, `redis`,
  `redis_manager`, `logger`, and `embed_color`.
- `mock_db_pool` provides async context-manager shaped `connection()` and `cursor()` mocks.
- `mock_redis` provides async `get`, `set`, `ping`, and `close` mocks.
- `mock_http_session` provides an aiohttp session plus an aioresponses registry.
- `caplog` is pytest's standard logging capture fixture.

Example HTTP test pattern:

```python
@pytest.mark.asyncio
async def test_fetch_card_returns_first_card(bot, mock_http_session):
    mock_http_session.mocked.get(
        "https://api.magicthegathering.io/v1/cards?name=Lightning+Bolt",
        payload={"cards": [{"name": "Lightning Bolt"}]},
    )

    card = await Mtg(bot).fetch_card("Lightning Bolt")

    assert card is not None
    assert card["name"] == "Lightning Bolt"
```

## Type Checking

```bash
pyright
```

Configured via `pyproject.toml`.

## Discord.py Upgrade Verification

Run these checks after changing the discord.py version or before deploying the upgraded bot:

```bash
python -m pip show discord.py
pytest
pyright
```

Expected package version: `discord.py 2.6.4`.

Live guild checklist:

1. Start the bot and confirm `Loaded cog: ...`, `Synced XX slash command(s) to Discord`, and `DarkBot setup complete` appear in logs.
2. Run `/info` and confirm the embed reports `discord.py` version `2.6.4`.
3. Run `/botstats`, `/ping`, `/poll`, and `/play`, then repeat representative commands with `!` prefix.
4. Delete and edit a message with modlog configured and confirm embeds are delivered.
5. Create/update/delete a scheduled Discord event and confirm listener logs are emitted.
6. Run `/play`, `/queue`, `/skip`, and `/stop` in a voice channel with Lavalink running.

## Manual Testing

### Startup Verification

After starting the bot, check logs for:

```
INFO | DarkBot setup complete
INFO | Synced XX slash command(s) to Discord
INFO | Loaded cog: cogs.ModLog
```

### Slash Commands

1. Type `/` in any channel - DarkBot's commands should appear in autocomplete
2. Test a few commands:

```
/ping
/play <song>
/events
/modlog status
```

### Prefix Commands

All slash commands also work with the `!` prefix:

```
!ping
!play <song>
!events
!modlog status
```

### ModLog Testing

See [modlog.md](modlog.md) for setup, then test:

1. **Message delete** - Send and delete a message, check modlog channel
2. **Message edit** - Edit a message, check modlog channel
3. **Member events** - Have someone join/leave, check modlog channel
4. **Ban/unban** - Use `/ban` and `/unban`, check modlog channel
5. **Cases** - Run `/cases` to see logged moderation actions

### Events Testing

See [events.md](events.md) for setup, then test:

```
/createevent "Test Event" 12/31/2026 "8:00 PM" Test description
/events
/rsvp 1 going
/cancelevent 1
```

### Music Testing

Join a voice channel, then:

```
/play Never Gonna Give You Up
/queue
/nowplaying
/skip
/stop
```

## Database Verification

```bash
docker-compose exec db psql -U postgres -d darkbot
```

```sql
-- Check tables exist
\dt

-- Check guild config
SELECT * FROM guild_config;

-- Check moderation logs
SELECT * FROM moderation_logs LIMIT 5;

-- Check events
SELECT * FROM events LIMIT 5;
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Slash commands not appearing | Wait up to 1 hour for global sync, or restart bot for guild sync. Check `applications.commands` OAuth2 scope. |
| ModLog not logging | Run `/modlog status`, verify channel is set. Check bot has Send Messages + Embed Links + View Audit Log. |
| Music commands unavailable | Expected in the default Docker stack because music is disabled. Re-enable `MUSIC_ENABLED` and `LAVALINK_ENABLED` if you want playback testing. |
| Database errors | Verify schemas are applied (`\dt` in psql). Check `.env` credentials. |
