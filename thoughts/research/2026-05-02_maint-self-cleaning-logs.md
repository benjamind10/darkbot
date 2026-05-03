---
date: 2026-05-02
git_commit: eb66e02
branch: main
---

# Research: Self-Cleaning Log System with Time-Based Rotation

## Summary

The repository currently has two separate logging setup paths. The runtime entrypoint in `bot/main.py` uses `init_logging(cfg: Config)` with `logging.basicConfig(..., force=True)` and a plain `FileHandler`, while `bot/utils/logger.py` exposes a module-level `setup_logging(config: Optional[Dict[str, Any]] = None)` that builds named `darkbot` and `discord` loggers from a plain dict. `LoggingConfig` is a dataclass populated through the standard env -> JSON -> default helpers in `Config`, but it is not passed into `bot/utils/logger.py` today. The existing size-rotation fields are limited to `config.py`, `settings.py`, and `logger.py`; there is no direct logger test file at present.

## Findings by Question

### Q1: What is the current signature of `setup_logging()`?

**Answer:** There are two different `setup_logging` names. The module-level public utility signature is `setup_logging(config: Optional[Dict[str, Any]] = None) -> logging.Logger`. The bot class has its own instance method `setup_logging(self)` that only assigns `self.logger`.

**Evidence:**
- `bot/utils/logger.py:181` - module-level `setup_logging` accepts an optional plain dict and returns a `logging.Logger`.
- `bot/core/bot.py:79` - `DarkBot.__init__` calls `self.setup_logging()`.
- `bot/core/bot.py:95` - `DarkBot.setup_logging(self)` has no parameters beyond `self`.
- `bot/core/bot.py:97` - the instance method only sets `self.logger = logging.getLogger("darkbot")`.
- `bot/main.py:17` - the active main entrypoint defines `init_logging(cfg: Config) -> logging.Logger` instead of calling the utility function.
- `bot/main.py:44` - `BotRunner.__init__` calls `init_logging(self.config)`.

### Q2: How does `get_default_logging_config()` interact with `LoggingConfig`?

**Answer:** `get_default_logging_config()` does not construct or consume `LoggingConfig`. It returns a standalone `Dict[str, Any]` used only when `bot/utils/logger.py:setup_logging()` is called without a config argument.

**Evidence:**
- `bot/utils/logger.py:194` - `setup_logging()` replaces `None` config with `get_default_logging_config()`.
- `bot/utils/logger.py:225` - `get_default_logging_config()` is declared as returning `Dict[str, Any]`.
- `bot/utils/logger.py:232` - the default config is a dict literal.
- `bot/config/config.py:130` - `LoggingConfig` is a separate dataclass in `config.py`.
- `bot/config/config.py:415` - `Config` constructs `LoggingConfig` through `_initialize_logging_config()`, separate from `get_default_logging_config()`.

### Q3: What is the env-var -> `config.py` -> `logger.py` wiring pattern?

**Answer:** `Config` loads dotenv data, then constructs section dataclasses using helper methods. Existing logging fields use `_get_config()` or `_get_int_config()` with env keys, nested JSON keys, and hard-coded defaults. The active `bot/main.py` logging path reads `cfg.logging.level`, `cfg.logging.format`, and `cfg.logging.file`; `bot/utils/logger.py` expects plain dict keys instead.

**Evidence:**
- `bot/config/config.py:151` - `Config.__init__` loads environment variables from `PROJECT_ROOT / ".env"`.
- `bot/config/config.py:259` - `_initialize_config()` assigns `self.logging = self._initialize_logging_config()`.
- `bot/config/config.py:418` - logging level is read from `LOG_LEVEL`, `logging.level`, default `"INFO"`.
- `bot/config/config.py:427` - `file_path` is read from `LOG_FILE`, `logging.file_path`, and a default root log path.
- `bot/config/config.py:449` - `_get_config()` checks env first, then flat file key, then nested file key, then default.
- `bot/config/config.py:484` - `_get_int_config()` wraps `_get_config()` and coerces to `int`.
- `bot/main.py:24` - runtime logging uses `cfg.logging.level`, `cfg.logging.format`, and `cfg.logging.file` in `logging.basicConfig`.
- `bot/utils/logger.py:53` - `DarkBotLogger` receives a `Dict[str, Any]`, not a `LoggingConfig` instance.

### Q4: What existing fields in `LoggingConfig` are being removed, and are they referenced outside `logger.py`?

**Answer:** The size-rotation fields are `max_bytes` and `backup_count`. They are defined and initialized in `bot/config/config.py`, constants with related names exist in `bot/config/settings.py`, and `backup_count` is also used by the optional rotating handler in `bot/utils/logger.py`. Repository search found no direct uses in tests, docs, README, Docker Compose, or env examples beyond those code locations and planning artifacts.

**Evidence:**
- `bot/config/config.py:137` - `LoggingConfig.max_bytes` default is `10 * 1024 * 1024`.
- `bot/config/config.py:138` - `LoggingConfig.backup_count` default is `5`.
- `bot/config/config.py:432` - `max_bytes` is initialized from `LOG_MAX_BYTES` / `logging.max_bytes`.
- `bot/config/config.py:435` - `backup_count` is initialized from `LOG_BACKUP_COUNT` / `logging.backup_count`.
- `bot/config/settings.py:63` - `LOG_MAX_BYTES` constant exists in the settings logging block.
- `bot/config/settings.py:64` - `LOG_BACKUP_COUNT` constant exists in the settings logging block.
- `bot/utils/logger.py:138` - the optional size-based handler is a `RotatingFileHandler`.
- `bot/utils/logger.py:141` - that handler reads `backup_count` from the dict config.
- `docs/configuration.md:78` - docs list config dataclass sections.
- `docs/configuration.md:85` - docs mention `LoggingConfig` but do not enumerate its fields.

### Q5: Where in the startup sequence should the orphan sweep run?

**Answer:** Current startup order is: `BotRunner` constructs `Config`, immediately initializes logging through `init_logging(self.config)`, then later creates `DarkBot`. The module-level `bot/utils/logger.py:setup_logging()` is not part of that boot path. In the active path, `init_logging()` creates the parent directory for `cfg.logging.file` before installing handlers.

**Evidence:**
- `bot/main.py:39` - `BotRunner.__init__` begins runtime construction.
- `bot/main.py:41` - `Config()` is loaded first.
- `bot/main.py:44` - logging is initialized immediately after config load.
- `bot/main.py:22` - `init_logging()` creates the parent directory for `cfg.logging.file`.
- `bot/main.py:24` - `logging.basicConfig(..., force=True)` installs stream and file handlers.
- `bot/main.py:52` - bot object creation happens later in `setup_bot()`.
- `bot/main.py:57` - `DarkBot(config=self.config)` is instantiated after runner logging exists.
- `bot/core/bot.py:79` - `DarkBot.__init__` then calls its local `setup_logging()`, which only retrieves the named logger.

### Q6: Does `logs/` get created by `logger.py` or by something else?

**Answer:** Multiple current paths can create a logs directory. `settings.py` creates `PROJECT_ROOT / "logs"` at import time. `bot/main.py:init_logging()` creates the parent directory of `cfg.logging.file`. `bot/utils/logger.py` creates its configured `log_directory` in validation and again in each file-handler helper. Docker Compose does not mount `./logs` into the Python app service; only the `bot` directory is mounted there, and `./logs` is mounted for Lavalink.

**Evidence:**
- `bot/config/settings.py:16` - `LOGS_DIR` is `PROJECT_ROOT / "logs"`.
- `bot/config/settings.py:20` - `LOGS_DIR.mkdir(exist_ok=True)` runs at settings import time.
- `bot/main.py:22` - `init_logging()` creates `Path(cfg.logging.file).parent`.
- `bot/utils/logger.py:112` - `_add_file_handler()` uses the configured `log_directory`.
- `bot/utils/logger.py:113` - `_add_file_handler()` creates that directory.
- `bot/utils/logger.py:158` - `_add_error_file_handler()` uses the configured `log_directory`.
- `bot/utils/logger.py:159` - `_add_error_file_handler()` creates that directory.
- `bot/utils/logger.py:277` - `_validate_logging_config()` converts `log_directory` to a `Path`.
- `bot/utils/logger.py:279` - validation creates the directory.
- `docker-compose.yml:6` - the Python service mounts `./bot` into `/usr/local/share/bot`.
- `docker-compose.yml:31` - the Lavalink service has its own volume block.
- `docker-compose.yml:33` - `./logs` is mounted to `/opt/Lavalink/logs` for Lavalink.

### Q7: What test coverage currently exists for `logger.py`, and what new tests are expected?

**Answer:** There is no `tests/test_logger.py` or `tests/test_config.py` in the current tree. The only source test file found is `tests/test_boardgames.py`, which demonstrates pytest-asyncio, `aioresponses`, and `caplog` for logging assertions. The repository testing docs describe pytest and pyright, but no logger-specific tests exist today.

**Evidence:**
- `tests/test_boardgames.py:1` - the test file imports `asyncio`.
- `tests/test_boardgames.py:4` - tests use `pytest`.
- `tests/test_boardgames.py:5` - HTTP mocking uses `aioresponses`.
- `tests/test_boardgames.py:10` - async tests use `@pytest.mark.asyncio`.
- `tests/test_boardgames.py:12` - logging assertions use `caplog.set_level(logging.DEBUG)`.
- `tests/test_boardgames.py:19` - the helper under test is called directly.
- `tests/test_boardgames.py:20` - a logger is injected with `logging.getLogger("test")`.
- `tests/test_boardgames.py:24` - the test asserts against `caplog.records`.
- `docs/testing.md:5` - docs list `pytest` as the all-tests command.
- `docs/testing.md:11` - docs state tests use pytest, pytest-asyncio, and aioresponses.

### Q8: How are `handler.rotator` and `handler.namer` typed by `TimedRotatingFileHandler`?

**Answer:** The repo's pyright configuration has type checking off, but docs still name `pyright` as the type-checking command. Local Pylance/typeshed defines `BaseRotatingHandler.namer` as `Callable[[str], str] | None` and `rotator` as `Callable[[str, str], None] | None`, matching Python runtime behavior.

**Evidence:**
- `pyrightconfig.json:1` - pyright uses `typeCheckingMode: "off"` and the local `venv`.
- `docs/testing.md:13` - testing docs include a type-checking section.
- `docs/testing.md:16` - the documented type-checking command is `pyright`.
- `/home/shiva/.vscode/extensions/ms-python.vscode-pylance-2026.2.1/dist/typeshed-fallback/stdlib/logging/handlers.pyi:33` - `BaseRotatingHandler` is the parent class defining these attributes.
- `/home/shiva/.vscode/extensions/ms-python.vscode-pylance-2026.2.1/dist/typeshed-fallback/stdlib/logging/handlers.pyi:34` - `namer` is typed as `Callable[[str], str] | None`.
- `/home/shiva/.vscode/extensions/ms-python.vscode-pylance-2026.2.1/dist/typeshed-fallback/stdlib/logging/handlers.pyi:35` - `rotator` is typed as `Callable[[str, str], None] | None`.
- `/usr/lib/python3.14/logging/handlers.py:85` - runtime `rotation_filename()` accepts `default_name`.
- `/usr/lib/python3.14/logging/handlers.py:101` - runtime calls `self.namer(default_name)`.
- `/usr/lib/python3.14/logging/handlers.py:104` - runtime `rotate()` accepts `source` and `dest`.
- `/usr/lib/python3.14/logging/handlers.py:123` - runtime calls `self.rotator(source, dest)`.

## Discovered Unknowns

- The active runtime path and the utility logging path are separate: `bot/main.py:init_logging()` installs root handlers, while `bot/utils/logger.py:setup_logging()` builds named loggers from a dict. The questions document anticipated `setup_logging()` call sites in `bot/main.py` and `bot/core/bot.py`, but `bot/main.py` currently uses `init_logging()` and `bot/core/bot.py` only uses the instance method.
- `LoggingConfig` has both `file_path` and `file` fields. `Config._initialize_logging_config()` populates `file_path`, while `bot/main.py:init_logging()` reads `cfg.logging.file`.
- `bot/config/settings.py` defines `LOG_MAX_BYTES` and `LOG_BACKUP_COUNT`, but `bot/config/config.py` does not import those constants in its settings import block.

## Open Questions

- None from the research pass. All eight listed questions were answerable from the current codebase and local type stubs.
