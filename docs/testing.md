# Testing Guide

## Automated Tests

```bash
pytest                              # all tests
pytest tests/test_boardgames.py     # single file
pytest -v                           # verbose output
```

Tests use pytest with pytest-asyncio. HTTP mocking uses aioresponses. Test files live in `tests/`.

## Type Checking

```bash
pyright
```

Configured via `pyrightconfig.json`.

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
| Music not playing | Check Lavalink is running: `docker-compose logs lavalink`. Verify bot has voice permissions. |
| Database errors | Verify schemas are applied (`\dt` in psql). Check `.env` credentials. |
