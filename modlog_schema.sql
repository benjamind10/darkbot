-- Modlog Schema for DarkBot
-- This schema adds guild configuration and moderation logging capabilities

-- Guild configuration table
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id BIGINT PRIMARY KEY,
    modlog_channel_id BIGINT,
    welcome_channel_id BIGINT,
    welcome_message TEXT,
    goodbye_message TEXT,
    auto_role_id BIGINT,
    prefix VARCHAR(10) DEFAULT '!',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Moderation action logs table
CREATE TABLE IF NOT EXISTS moderation_logs (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    case_id INTEGER NOT NULL,
    action_type VARCHAR(50) NOT NULL, -- ban, kick, warn, unban, mute, etc.
    moderator_id BIGINT NOT NULL,
    target_id BIGINT NOT NULL,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, case_id)
);

-- Message deletion/edit cache for snipe commands
CREATE TABLE IF NOT EXISTS message_cache (
    id SERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    content TEXT,
    action_type VARCHAR(20) NOT NULL, -- 'delete' or 'edit'
    before_content TEXT, -- For edits
    after_content TEXT, -- For edits
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_message_cache_channel ON message_cache(channel_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_message_cache_guild ON message_cache(guild_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_moderation_logs_guild ON moderation_logs(guild_id, case_id DESC);

-- Auto-update timestamp trigger for guild_config
CREATE OR REPLACE FUNCTION update_guild_config_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_guild_config_timestamp
    BEFORE UPDATE ON guild_config
    FOR EACH ROW
    EXECUTE FUNCTION update_guild_config_timestamp();

-- Helper function to get next case ID for a guild
CREATE OR REPLACE FUNCTION get_next_case_id(p_guild_id BIGINT)
RETURNS INTEGER AS $$
DECLARE
    next_id INTEGER;
BEGIN
    SELECT COALESCE(MAX(case_id), 0) + 1 INTO next_id
    FROM moderation_logs
    WHERE guild_id = p_guild_id;
    RETURN next_id;
END;
$$ LANGUAGE plpgsql;

-- Function to log a moderation action
CREATE OR REPLACE FUNCTION log_moderation_action(
    p_guild_id BIGINT,
    p_action_type VARCHAR(50),
    p_moderator_id BIGINT,
    p_target_id BIGINT,
    p_reason TEXT
)
RETURNS INTEGER AS $$
DECLARE
    new_case_id INTEGER;
BEGIN
    new_case_id := get_next_case_id(p_guild_id);

    INSERT INTO moderation_logs (guild_id, case_id, action_type, moderator_id, target_id, reason)
    VALUES (p_guild_id, new_case_id, p_action_type, p_moderator_id, p_target_id, p_reason);

    RETURN new_case_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get or create guild config
CREATE OR REPLACE FUNCTION get_or_create_guild_config(p_guild_id BIGINT)
RETURNS TABLE (
    guild_id BIGINT,
    modlog_channel_id BIGINT,
    welcome_channel_id BIGINT,
    welcome_message TEXT,
    goodbye_message TEXT,
    auto_role_id BIGINT,
    prefix VARCHAR(10)
) AS $$
#variable_conflict use_column
BEGIN
    -- Insert if not exists
    INSERT INTO guild_config (guild_id)
    VALUES (p_guild_id)
    ON CONFLICT (guild_id) DO NOTHING;

    -- Return the config
    RETURN QUERY
    SELECT gc.guild_id, gc.modlog_channel_id, gc.welcome_channel_id,
           gc.welcome_message, gc.goodbye_message, gc.auto_role_id, gc.prefix
    FROM guild_config gc
    WHERE gc.guild_id = p_guild_id;
END;
$$ LANGUAGE plpgsql;
