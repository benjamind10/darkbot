---
type: maint
created: 2026-05-02
---

# MAINT: Self-cleaning log system with time-based rotation

## Description

The current logging system in [bot/utils/logger.py](bot/utils/logger.py) has unbounded growth on its two primary file handlers: `darkbot.log` (everything) and `darkbot_errors.log` (errors only). Only the optional `darkbot_rotating.log` has any cleanup (size-based, off by default). In long-running deployments these files grow forever and require manual cleanup.

Replace the unbounded `FileHandler`s with `TimedRotatingFileHandler`s, gzip compress rotated files, and add a startup orphan sweep so pre-existing files past retention also get cleaned.

## In Scope

- Replace main/error `FileHandler` with `TimedRotatingFileHandler` in [bot/utils/logger.py](bot/utils/logger.py)
  - Daily rotation at midnight, UTC
  - Default retention: 14 days for `darkbot.log`, 30 days for `darkbot_errors.log`
- Gzip compression of rotated files via `handler.rotator` / `handler.namer` override
- Startup orphan sweep — delete `*.log*` files in `logs/` older than max retention
- Remove the now-redundant size-based `RotatingFileHandler` code path
- Wire new settings through `LoggingConfig` in [bot/config/config.py](bot/config/config.py) and defaults in `get_default_logging_config()` in [bot/utils/logger.py](bot/utils/logger.py)
- Update [docs/configuration.md](docs/configuration.md) with new env vars

## Out of Scope

- Structured/JSON logging
- Per-cog log files
- External log shipping (Loki, Grafana, ELK)
- Discord-side log commands (e.g., `/logs tail`)
- Console handler changes
- Decorator/`LogContext` behavior changes

## Acceptance Criteria

- `darkbot.log` and `darkbot_errors.log` rotate daily; rotated files are gzipped
- Files older than retention are deleted automatically by the rotation handler
- Orphan `*.log*` files in `logs/` older than max retention are deleted on startup
- Retention, cadence, and compression configurable via env vars:
  - `LOG_RETENTION_DAYS` (default 14)
  - `LOG_ERROR_RETENTION_DAYS` (default 30)
  - `LOG_ROTATION_WHEN` (default `midnight`)
  - `LOG_COMPRESS_ROTATED` (default `true`)
- `setup_logging()` public signature unchanged
- Existing tests still pass; `pyright` clean

## Current State

- [bot/utils/logger.py](bot/utils/logger.py)
  - `_add_file_handler()` (line 110) — plain `FileHandler`, no rotation
  - `_add_error_file_handler()` (line 156) — plain `FileHandler`, no rotation
  - `_add_rotating_file_handler()` (line 131) — size-based `RotatingFileHandler`, off by default
- [bot/config/config.py](bot/config/config.py) — `LoggingConfig` does not yet expose retention/rotation knobs
- Logs directory: `logs/` (created via `Path.mkdir(exist_ok=True)`)

## Desired State

- Main and error log files use `TimedRotatingFileHandler` with daily rotation, gzip-compressed backups, and bounded retention
- Old/orphan files in `logs/` are cleaned on bot startup
- Size-based rotation handler removed
- All retention/cadence settings configurable via env or JSON config; sensible defaults match best practices
- Documentation reflects new behavior
