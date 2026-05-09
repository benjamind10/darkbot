---
type: feat
created: 2026-05-02
---

# FEAT: Complete Modlog Feature Implementation

## Description
Modlog infrastructure (schema, event logging, config commands) is in place but several features are partially implemented or stubbed. Complete the remaining work to make modlog fully functional.

## In Scope
1. Wire moderation commands (`ban`, `kick`, `warn` in Moderation.py) to insert case records into `moderation_logs` table
2. Implement message cache writes in `on_message_delete` and `on_message_edit` event handlers
3. Add commands to configure welcome/goodbye messages and auto-role per-guild
4. Implement `on_guild_join` and `on_guild_remove` handlers to auto-create/delete guild config

## Out of Scope
- Snipe commands (future use of message cache)
- Welcome/goodbye/auto-role **handlers** (config only; handlers deferred)
- Schema changes or migrations
- Performance optimization

## Acceptance Criteria
- [ ] `/ban`, `/kick`, `/warn` commands insert into `moderation_logs`; `/cases` shows entries
- [ ] Deleted/edited messages are cached in `message_cache` table
- [ ] `/modlog setwelcome`, `/modlog setgoodbye`, `/modlog setautorole` commands exist and persist to DB
- [ ] Guild config auto-created on guild join; cleaned up on leave
- [ ] All commands use `@commands.hybrid_command` syntax

## Current State
- Event logging: ✅ working (joins, leaves, kicks, bans, message edits/deletes)
- Moderation case logging: ❌ commands exist but don't persist
- Message cache: ❌ schema exists, handlers have TODOs, never written
- Welcome/goodbye/auto-role: ❌ columns exist, no setters, no handlers
- Guild lifecycle: ❌ handlers stubbed with TODOs

## Desired State
- All moderation actions logged to `moderation_logs`; `/cases` shows complete history
- Deleted/edited messages cached for future snipe commands
- Guild-configurable welcome/goodbye/auto-role settings
- Guild config automatically created and cleaned up on join/leave
