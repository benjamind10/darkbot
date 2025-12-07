-- Events Management Schema
-- Add this to your darkbot database

-- Events table
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    creator_id BIGINT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    event_date TIMESTAMP NOT NULL,
    location VARCHAR(500),
    max_attendees INTEGER,
    is_cancelled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Event RSVPs table
CREATE TABLE IF NOT EXISTS event_rsvps (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    username VARCHAR(100),
    status VARCHAR(20) DEFAULT 'going', -- 'going', 'maybe', 'declined'
    rsvp_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_event_user UNIQUE (event_id, user_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_events_guild_id ON events(guild_id);
CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date);
CREATE INDEX IF NOT EXISTS idx_event_rsvps_event_id ON event_rsvps(event_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_event_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at
CREATE TRIGGER trigger_update_event_modtime
    BEFORE UPDATE ON events
    FOR EACH ROW
    EXECUTE PROCEDURE update_event_modified_column();

-- Function to get upcoming events
CREATE OR REPLACE FUNCTION get_upcoming_events(p_guild_id BIGINT, p_limit INTEGER DEFAULT 10)
RETURNS TABLE(
    id INTEGER,
    title VARCHAR,
    description TEXT,
    event_date TIMESTAMP,
    location VARCHAR,
    max_attendees INTEGER,
    creator_id BIGINT,
    going_count BIGINT,
    maybe_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.id,
        e.title,
        e.description,
        e.event_date,
        e.location,
        e.max_attendees,
        e.creator_id,
        COUNT(r.id) FILTER (WHERE r.status = 'going') AS going_count,
        COUNT(r.id) FILTER (WHERE r.status = 'maybe') AS maybe_count
    FROM events e
    LEFT JOIN event_rsvps r ON e.id = r.event_id
    WHERE e.guild_id = p_guild_id
        AND e.event_date > NOW()
        AND e.is_cancelled = FALSE
    GROUP BY e.id, e.title, e.description, e.event_date, e.location, e.max_attendees, e.creator_id
    ORDER BY e.event_date ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to get event RSVPs
CREATE OR REPLACE FUNCTION get_event_rsvps(p_event_id INTEGER)
RETURNS TABLE(
    user_id BIGINT,
    username VARCHAR,
    status VARCHAR,
    rsvp_date TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT r.user_id, r.username, r.status, r.rsvp_date
    FROM event_rsvps r
    WHERE r.event_id = p_event_id
    ORDER BY r.rsvp_date ASC;
END;
$$ LANGUAGE plpgsql;
