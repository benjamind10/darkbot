# Events System Guide

## Setup

### 1. Add Database Tables

Run the SQL schema on your database:

```bash
# On your Digital Ocean droplet
docker-compose exec db psql -U postgres -d darkbot < events_schema.sql
```

Or manually copy/paste from `events_schema.sql` into your database.

### 2. Reload the Bot

The Events cog is already loaded. Just restart the bot:

```bash
docker-compose restart python-app
```

## Commands

### For Users

#### `!events` or `!upcoming`
List upcoming events in the server.
```
!events
!events 20  # Show up to 20 events
```

#### `!event <id>`
View detailed information about a specific event.
```
!event 5
```

#### `!createevent <title> <date> <time> [description]`
Create a new event.
```
!createevent "Board Game Night" 12/15/2025 "7:00 PM" Bring your favorite games!
!createevent "Alphabet Soup" 12/20/2025 "18:00" Open game night
```

#### `!rsvp <event_id> [going|maybe|decline]`
RSVP to an event.
```
!rsvp 5 going
!rsvp 5 maybe
!rsvp 5 decline  # Removes your RSVP
```

### For Admins/Event Creators

#### `!editevent <event_id> <field> <value>`
Edit event details (requires Manage Events permission or event creator).
```
!editevent 5 location "15819 Primrose Tarry Drive, Moseley, VA 23120"
!editevent 5 max_attendees 20
!editevent 5 description "Updated description here"
```

#### `!cancelevent <event_id>`
Cancel an event (creator or admin only).
```
!cancelevent 5
```

## Features

✅ **Create Events** - Users can create events with title, date, time, and description  
✅ **RSVP System** - Track who's going, maybe, or declined  
✅ **Capacity Limits** - Set max attendees to control event size  
✅ **Location Info** - Add physical or virtual locations  
✅ **Upcoming List** - View all future events sorted by date  
✅ **Event Details** - See full info including all RSVPs  
✅ **Cancel Events** - Event creators and admins can cancel  
✅ **Auto Cleanup** - Past events automatically hidden from lists  

## Database Tables

### `events`
Stores event information including title, description, date, location, and creator.

### `event_rsvps`
Tracks user RSVPs with status (going/maybe/declined).

## Examples

### Creating a Meetup Event
```
!createevent "The Kallax Meetup" 01/15/2026 "6:00 PM" Monthly board game meetup at the usual spot
```

### Setting Event Details
```
!editevent 1 location "15819 Primrose Tarry Drive, Moseley, VA 23120"
!editevent 1 max_attendees 25
```

### Users RSVP'ing
```
!rsvp 1 going
!rsvp 1 maybe
```

### Viewing Events
```
!events          # List all upcoming
!event 1         # See full details with RSVP list
```

## Notes

- Event dates must be in the future
- RSVP status automatically updates if you RSVP multiple times
- Declined RSVPs are removed from the database
- Events are guild-specific (each Discord server has its own events)
- Past events are automatically hidden but remain in the database
