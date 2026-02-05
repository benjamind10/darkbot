# Moderation Logging (ModLog)

The ModLog system logs moderation actions and server events to a designated channel, with a case-based audit trail stored in PostgreSQL.

## Setup

### 1. Apply Database Schema

```bash
docker-compose exec db psql -U postgres -d darkbot < modlog_schema.sql
```

### 2. Configure in Discord

```
/modlog setchannel #mod-log
```

### 3. Verify

```
/modlog status
```

## What Gets Logged

### Message Events

| Event | Embed Color | Details |
|-------|-------------|---------|
| Message Deleted | Red | Author, channel, content, attachments |
| Message Edited | Gold | Before/after content, jump link |

### Member Events

| Event | Embed Color | Details |
|-------|-------------|---------|
| Member Joined | Green | User info, account age, member count |
| Member Left | Gray | User info, member count |
| Member Kicked | Orange | User, moderator (detected via audit log) |

### Moderation Actions

| Event | Embed Color | Details |
|-------|-------------|---------|
| Member Banned | Red | User, moderator, reason (from audit log) |
| Member Unbanned | Green | User, moderator (from audit log) |

## Commands

### Admin Commands (requires Administrator)

| Command | Description |
|---------|-------------|
| `/modlog setchannel <channel>` | Set the modlog channel |
| `/modlog disable` | Turn off modlog |
| `/modlog status` | View current configuration |

### Moderator Commands (requires Manage Messages)

| Command | Description |
|---------|-------------|
| `/cases [member]` | View last 10 moderation cases |

## Database

### Tables

- **`guild_config`** - Per-guild settings (modlog channel, prefix, future: welcome channel, auto-role)
- **`moderation_logs`** - Case-based audit trail (action type, moderator, target, reason)
- **`message_cache`** - Deleted/edited message storage (for future snipe commands)

### Functions

- `get_or_create_guild_config(guild_id)` - Auto-creates config on first use
- `log_moderation_action(...)` - Creates a case with auto-incrementing ID
- `get_next_case_id(guild_id)` - Gets next available case number

Schema file: `modlog_schema.sql`

## Permissions

- **Bot requires:** `View Audit Log`, `Send Messages`, `Embed Links` in the modlog channel
- **Admin setup:** Only users with `Administrator` can configure modlog
- **Case viewing:** Users with `Manage Messages` can view cases
- **Graceful degradation:** If the modlog channel is deleted or inaccessible, events are silently skipped

## Code Structure

- **`bot/cogs/ModLog.py`** - Configuration commands and helper methods
- **`bot/core/events.py`** - Event handlers that build and send modlog embeds
