# Events System

The Events cog lets users create, manage, and RSVP to server events.

## Setup

Apply the events schema to your database:

```bash
docker-compose exec db psql -U postgres -d darkbot < events_schema.sql
```

The Events cog loads automatically on bot startup.

## Commands

All commands support both prefix (`!`) and slash (`/`) syntax.

### User Commands

| Command | Description |
|---------|-------------|
| `events [limit]` | List upcoming events (default 10) |
| `event <id>` | View details for a specific event |
| `createevent <title> <date> <time> [description]` | Create a new event |
| `rsvp <event_id> <going\|maybe\|decline>` | RSVP to an event |

### Admin Commands

Requires `Manage Events` permission or event creator.

| Command | Description |
|---------|-------------|
| `editevent <id> <field> <value>` | Edit event details |
| `cancelevent <id>` | Cancel an event |

### Examples

```
/createevent "Board Game Night" 01/15/2026 "7:00 PM" Bring your favorite games!
/editevent 1 location "123 Main St"
/editevent 1 max_attendees 20
/rsvp 1 going
/events
```

## Database Tables

- **`events`** - Event data (title, description, date, location, creator, capacity)
- **`event_rsvps`** - User RSVPs with status (going/maybe/declined)

Schema file: `events_schema.sql`

## Behavior

- Event dates must be in the future
- RSVP updates replace previous status for that user
- Declining removes the RSVP from the database
- Past events are hidden from listings but kept in the database
- Events are guild-specific
