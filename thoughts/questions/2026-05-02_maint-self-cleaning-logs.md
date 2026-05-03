---
date: 2026-05-02
---

# Questions: Self-Cleaning Log System with Time-Based Rotation

## Context
The current `bot/utils/logger.py` has two unbounded `FileHandler`s (`darkbot.log`, `darkbot_errors.log`) and an optional size-based `RotatingFileHandler` that is off by default. The task replaces these with `TimedRotatingFileHandler`s (daily, gzip-compressed, bounded retention), removes the size-based path, adds a startup orphan sweep, and wires new settings through `LoggingConfig` and env vars.

## Technical Unknowns

### Q1: What is the current signature of `setup_logging()`?
**Unknown:** We know the public signature must remain unchanged, but we don't know its current parameters (e.g., does it accept a `Config` object, a `LoggingConfig`, a level string, or nothing?).
**Why it matters:** Any new settings (retention days, rotation cadence, compression flag) must be threaded through whatever the existing call path already accepts — or loaded internally — without changing the signature.
**Research needed:** Read `bot/utils/logger.py` lines around `setup_logging` definition and all call sites in `bot/main.py` and `bot/core/bot.py`.

---

### Q2: How does `get_default_logging_config()` interact with `LoggingConfig`?
**Unknown:** The ticket says `get_default_logging_config()` lives in `bot/utils/logger.py`, but the locator found no top-level `def`/`class` (grep artifact — functions exist but may be nested or the grep pattern failed). We don't know whether this function constructs and returns a `LoggingConfig`, a plain dict, or something else.
**Why it matters:** New fields (`log_retention_days`, `log_error_retention_days`, `log_rotation_when`, `log_compress_rotated`) need to be added to this function's return value and to `LoggingConfig`. We need to match the existing return type exactly.
**Research needed:** Read `bot/utils/logger.py` full file; read `LoggingConfig` in `bot/config/config.py`.

---

### Q3: What is the env-var → `config.py` → `logger.py` wiring pattern?
**Unknown:** The existing `LoggingConfig` fields (`level`, `file`, `max_bytes`, `backup_count`) are sourced from somewhere. We don't know if env vars are read directly inside `config.py`, read in `settings.py` as constants and imported, or handled by a generic loader function.
**Why it matters:** The four new env vars (`LOG_RETENTION_DAYS`, `LOG_ERROR_RETENTION_DAYS`, `LOG_ROTATION_WHEN`, `LOG_COMPRESS_ROTATED`) must follow the same pattern. Getting this wrong means the three-level fallback (env → JSON → default) won't work for the new knobs.
**Research needed:** Read `bot/config/config.py` (full `LoggingConfig` section and its loader); read `bot/config/settings.py` (LOG_* constants block).

---

### Q4: What existing fields in `LoggingConfig` are being removed, and are they referenced outside `logger.py`?
**Unknown:** `LoggingConfig` currently has `max_bytes` and `backup_count` (size-based rotation fields). The ticket removes the size-based handler. We don't know if these fields are used anywhere beyond `logger.py` (e.g., imported directly in tests or docs).
**Why it matters:** Removing fields from a dataclass is a breaking change if other code reads `config.logging.max_bytes`. We need to know whether to remove them cleanly or keep them as deprecated no-ops.
**Research needed:** Grep for `max_bytes` and `backup_count` across the whole repo; check `test_config.py` for references.

---

### Q5: Where in the startup sequence should the orphan sweep run?
**Unknown:** The sweep deletes `*.log*` files in `logs/` older than max retention on startup. We don't know where in the boot flow to call it — before or after `setup_logging()` is called, and whether it should run inside `setup_logging()` itself or be called explicitly by `BotRunner`/`DarkBot.setup_hook()`.
**Why it matters:** Running the sweep before handlers are initialized avoids deleting the current log file accidentally. Running it inside `setup_logging()` keeps log management self-contained. The wrong placement could delete files still in use or run before the `logs/` directory is created.
**Research needed:** Read `bot/main.py` and `bot/core/bot.py` for the boot sequence; confirm where `setup_logging()` is currently called relative to the `logs/` directory creation.

---

### Q6: Does `logs/` get created by `logger.py` or by something else?
**Unknown:** The ticket says `logs/` is created via `Path.mkdir(exist_ok=True)`, but the locator found no actual `logs/` directory in the workspace. We don't know whether that mkdir call is inside `logger.py`, in `main.py`, or only happens at runtime inside Docker.
**Why it matters:** The orphan sweep iterates `logs/` — it must not crash if the directory doesn't exist yet. We need to know whether to guard the sweep with an existence check or if we can rely on the directory always being present before `setup_logging()` runs.
**Research needed:** Read `bot/utils/logger.py` for the `Path.mkdir` call; check `docker-compose.yml` for volume mapping of `logs/`.

---

### Q7: What test coverage currently exists for `logger.py`, and what new tests are expected?
**Unknown:** No `test_logger.py` exists. `test_config.py` has some logging references. The acceptance criteria say "existing tests still pass; pyright clean" but do not explicitly require new tests for the rotation/compression/sweep logic.
**Why it matters:** If we should add tests (e.g., assert rotated files are gzipped, assert orphan sweep deletes old files), we need to understand the existing test patterns (fixtures, mocking style with `aioresponses`, etc.) to write consistent tests.
**Research needed:** Read `test_config.py` (logging-related section); read `test_boardgames.py` for general test structure/fixture patterns.

---

### Q8: How are `handler.rotator` and `handler.namer` typed by `TimedRotatingFileHandler`?
**Unknown:** Overriding `.rotator` and `.namer` on a `TimedRotatingFileHandler` to enable gzip compression requires assigning callables to those attributes. Python's type stubs mark them as `Callable | None` but pyright can be strict about the exact signature.
**Why it matters:** The acceptance criteria requires `pyright` clean. If the override signatures don't match what pyright expects, we'll need an explicit `# type: ignore` or a correctly typed wrapper.
**Research needed:** Check `pyrightconfig.json` for strictness settings; skim Python typeshed stubs for `logging.handlers.TimedRotatingFileHandler` to know the expected callable signatures.

---

## Human Decisions Required

1. **`max_bytes` / `backup_count` in `LoggingConfig`** — Should these be removed outright (clean break) or kept as ignored no-ops for backward compatibility with existing JSON config files that may reference them?
   **Resolved:** Remove outright (clean break).

2. **`LOG_ROTATION_WHEN` valid values** — Should we validate the value (e.g., only allow `midnight`, `D`, `H`, `W0`–`W6`) or pass it through to `TimedRotatingFileHandler` and let Python raise at runtime?
   **Resolved:** Validate the value.

3. **Separate retention for main vs error log** — The ticket specifies two separate env vars. Should a single `LOG_RETENTION_DAYS` set both when `LOG_ERROR_RETENTION_DAYS` is not explicitly set, or are they always independent?
   **Resolved:** Always independent — `LOG_RETENTION_DAYS` and `LOG_ERROR_RETENTION_DAYS` are separate with no fallback relationship.

---

## Research Plan

1. **Read `bot/utils/logger.py` in full** — answers Q1, Q2, Q5 (call order), Q6 (mkdir location), and reveals the exact handler construction we're replacing.
2. **Read `bot/config/config.py` (`LoggingConfig` block) and `bot/config/settings.py` (LOG_* block)** — answers Q3 (wiring pattern) and Q4 (field inventory).
3. **Grep `max_bytes` and `backup_count` repo-wide** — answers Q4 (external references).
4. **Read `bot/main.py` + `bot/core/bot.py` (boot sequence)** — answers Q5 (sweep placement) and confirms `setup_logging()` call site for Q1.
5. **Read `pyrightconfig.json`** — answers Q8 (strictness level).
6. **Read `tests/test_config.py`** — answers Q7 (existing test coverage and patterns).
