---
date: 2026-05-02
git_commit: eb66e02
branch: maint/cleanup
---

# Research: Whole-App Python Best-Practices Sweep

## Summary
DarkBot currently has a split tooling and runtime baseline: Pyright exists but type checking is disabled, Docker runs Python 3.10, and there is no Ruff/pytest/pre-commit configuration in the repo. Dependency state is also split between a UTF-16LE `bot/requirements.txt`, a separate root `requirements.txt`, and extra Docker `pip install` lines. The main async hazards are synchronous MTG HTTP calls and synchronous psycopg2 database work inside async commands and event helpers; Redis is already using `redis.asyncio`. Error handling, logging, and configuration access are mixed across central helpers and per-cog direct patterns. Test coverage in this checkout is one narrow BoardGameGeek utility test with no shared `conftest.py`.

## Findings by Question

### Q1: Tooling baseline
**Answer:** Pyright is present but minimal, Docker targets Python 3.10, and repo-level Ruff/pytest/pre-commit config files were not found. The repo has both `bot/requirements.txt` and a root `requirements.txt`, which affects where tool and project metadata would attach.

**Evidence:**
- `pyrightconfig.json:1` - Pyright points at `./venv`, names `venv`, and sets `"typeCheckingMode": "off"`.
- `Dockerfile:1` - The image comment says Python 3.10 is the base.
- `Dockerfile:2` - The actual base image is `python:3.10`.
- `Dockerfile:17` - Docker copies `./bot/requirements.txt` into the image.
- `requirements.txt:1` - A separate root dependency file exists and starts with `aiohttp==3.9.5`.
- `bot/requirements.txt:1` - The bot-local dependency file exists separately and starts with `aiogoogletrans==3.3.3` when decoded.

### Q2: `bot/requirements.txt` corruption and dependency ground truth
**Answer:** `bot/requirements.txt` is UTF-16LE with a BOM and CRLF line endings, so normal terminal display shows interleaved NUL bytes. Docker treats it as the install manifest, then explicitly installs packages that overlap with entries already present in that manifest. Test-only dependencies are not captured in either visible requirements file.

**Evidence:**
- `bot/requirements.txt:1` - The decoded first entry is `aiogoogletrans==3.3.3`; raw file metadata reports UTF-16 little-endian text.
- `bot/requirements.txt:13` - Runtime dependency `discord.py==2.3.2` is pinned in the bot-local manifest.
- `bot/requirements.txt:30` - Runtime dependency `psycopg2==2.9.1` is pinned in the bot-local manifest.
- `bot/requirements.txt:42` - `redis==5.0.1` is already listed in the bot-local manifest.
- `Dockerfile:20` - Docker installs `-r requirements.txt` after copying `bot/requirements.txt`.
- `Dockerfile:22` - Docker separately installs `redis==5.0.1`.
- `Dockerfile:23` - Docker separately installs `aiogoogletrans asyncurban ipinfo strgen forex-python bitlyshortener`.
- `tests/test_boardgames.py:4` - Tests import `pytest`.
- `tests/test_boardgames.py:5` - Tests import `aioresponses`.

### Q3: Async/sync correctness across cogs
**Answer:** External HTTP is mostly async via `aiohttp`, but MTG uses synchronous `requests` from async command paths. Database access uses synchronous psycopg2 connections/cursors inside async commands and event helpers. Utility commands also call synchronous third-party clients from async handlers. Redis uses the async Redis client.

**Evidence:**
- `bot/cogs/Mtg.py:12` - MTG imports `requests`.
- `bot/cogs/Mtg.py:42` - `fetch_card()` calls `requests.get(..., timeout=10)`.
- `bot/cogs/Mtg.py:65` - Async command `card()` calls the synchronous `fetch_card()`.
- `bot/cogs/Mtg.py:112` - Async command `search_cards()` calls `requests.get(..., timeout=10)` directly.
- `bot/cogs/ModLog.py:27` - Async `get_guild_config()` opens a psycopg2 cursor from `self.bot.db_conn`.
- `bot/cogs/ModLog.py:204` - Async `cases()` opens a psycopg2 cursor for moderation case reads.
- `bot/cogs/Database.py:29` - Async `list_users()` opens a synchronous cursor.
- `bot/cogs/Database.py:267` - Async owner SQL command executes arbitrary SQL through the synchronous cursor.
- `bot/cogs/Utility.py:86` - Async bitcoin command constructs a `BtcConverter`.
- `bot/cogs/Utility.py:87` - That command calls `get_latest_price()` synchronously.
- `bot/cogs/Utility.py:306` - Async IP lookup constructs an ipinfo handler.
- `bot/cogs/Utility.py:307` - The handler calls `getDetails()` synchronously.
- `bot/utils/redis_manager.py:12` - Redis imports `redis.asyncio`.
- `bot/utils/redis_manager.py:66` - Redis connection is tested with `await self.redis.ping()`.

### Q4: Error handling and logging consistency
**Answer:** There is a central command error hook through `DarkBot` and `EventManager`, but individual cogs and utilities also catch broad exceptions and log with mixed styles. Some paths use `logger.exception`, many use stringified `logger.error`, and several bare `except:` blocks suppress best-effort moderation/event logging failures. Custom exceptions exist but are used narrowly.

**Evidence:**
- `bot/core/bot.py:257` - `DarkBot.on_command_error()` delegates command errors to the event manager.
- `bot/core/events.py:169` - `EventManager.on_command_error()` is the central command error handler.
- `bot/core/events.py:196` - Generic command errors are logged with `logger.error(...)`.
- `bot/cogs/Chatgpt.py:65` - ChatGPT catches broad `Exception`.
- `bot/cogs/Database.py:51` - Database command catches broad `Exception`.
- `bot/cogs/BoardGames.py:237` - BoardGames uses `logger.exception(...)` for one BGG collection path.
- `bot/cogs/Information.py:172` - Information uses `logger.exception(...)` for Redis key fetch errors.
- `bot/core/events.py:260` - A bare `except:` suppresses role-add audit logging failures.
- `bot/cogs/Moderation.py:203` - A bare `except:` suppresses a moderation DM failure.
- `bot/core/exceptions.py:11` - `DarkBotException` is defined as the base custom exception.
- `bot/core/exceptions.py:366` - A `handle_errors` decorator exists for custom exception handling.
- `bot/core/bot.py:19` - Core bot imports `DarkBotException` and `ConfigurationError`.
- `bot/utils/logger.py:181` - A separate `setup_logging()` helper exists outside `bot/main.py` logging setup.

### Q5: Test coverage and reliability gaps
**Answer:** In this checkout, the tests directory contains one source test file and one committed pycache artifact. There is no `tests/conftest.py`. The single test exercises one async BGG 401 response path using `pytest.mark.asyncio`, `aioresponses`, and `caplog`.

**Evidence:**
- `tests/test_boardgames.py:4` - The test imports `pytest`.
- `tests/test_boardgames.py:5` - The test imports `aioresponses`.
- `tests/test_boardgames.py:7` - The test imports only `fetch_bgg_collection` and `BASE_URL` from app code.
- `tests/test_boardgames.py:10` - The test uses `@pytest.mark.asyncio`.
- `tests/test_boardgames.py:16` - The test creates an `aioresponses()` mock.
- `tests/test_boardgames.py:19` - The test calls `await fetch_bgg_collection(...)`.
- `tests/test_boardgames.py:23` - The assertions cover a 401 result and log message.

### Q6: Architecture hygiene, import-time side effects, helpers vs utils
**Answer:** Package init files now exist for `bot`, `bot/config`, `bot/core`, and `bot/cogs`, but not for `bot/utils`. Import-time side effects are concentrated in bootstrap/config modules: `main.py` mutates `sys.path`, `settings.py` loads `.env`, creates `logs/`, and snapshots env constants. BoardGames has both cog-level BGG HTTP/XML logic and a `bot/utils/boardgames.py` module with BGG fetch/process/upsert logic; Spotify has helper methods inside the cog rather than a utility module.

**Evidence:**
- `bot/__init__.py:1` - A root package init file exists.
- `bot/core/__init__.py:8` - Core package init imports `DarkBot`.
- `bot/main.py:9` - Main mutates the import path before importing config/core.
- `bot/config/settings.py:11` - Settings calls `load_dotenv()` at import time.
- `bot/config/settings.py:20` - Settings creates the logs directory at import time.
- `bot/config/settings.py:30` - Settings snapshots `REDIS_ENABLED` from the environment.
- `bot/config/settings.py:95` - Settings snapshots `DISCORD_TOKEN` from the environment.
- `bot/config/config.py:151` - `Config.__init__` also loads `.env`.
- `bot/utils/boardgames.py:16` - Utility module owns `fetch_bgg_collection(...)`.
- `bot/utils/boardgames.py:179` - Utility module owns `upsert_boardgame(...)`.
- `bot/utils/boardgames.py:236` - Utility module owns `process_bgg_users(...)`.
- `bot/cogs/BoardGames.py:79` - BoardGames cog still opens its own BGG `ClientSession` for search.
- `bot/cogs/BoardGames.py:127` - BoardGames cog opens its own BGG `ClientSession` for game info.
- `bot/cogs/Spotify.py:42` - Spotify token helper lives inside the cog.
- `bot/cogs/Spotify.py:87` - Spotify voice helper lives inside the cog.

### Q7: Configuration loading and consumption
**Answer:** The central `Config` class implements env/file/default lookup and builds typed-ish config sections, while `settings.py` also reads environment variables at import time. Several cogs and utilities bypass `Config` with direct `os.getenv` calls. Redis is the main utility observed consuming the `Config` object directly.

**Evidence:**
- `bot/config/config.py:142` - `Config` is the main configuration class.
- `bot/config/config.py:223` - `_initialize_config()` builds the runtime config sections.
- `bot/config/config.py:449` - `_get_config()` implements environment, file, then default lookup.
- `bot/config/settings.py:30` - Redis settings are read directly from env at import time.
- `bot/config/settings.py:78` - Lavalink host is read directly from env at import time.
- `bot/config/settings.py:163` - Feature flags are built from env values in `FEATURES`.
- `bot/core/bot.py:181` - Runtime diagnostics directly import/use `os.getenv`.
- `bot/cogs/Chatgpt.py:29` - ChatGPT reads `CHATGPT_SECRET` directly.
- `bot/cogs/Music.py:41` - Music reads `LAVALINK_SERVER` directly.
- `bot/cogs/Spotify.py:36` - Spotify reads `SPOTIFY_CLIENT_ID` directly.
- `bot/cogs/Utility.py:68` - Utility reads `IP_INFO` directly.
- `bot/utils/boardgames.py:33` - Boardgames utility reads BGG cookie env vars directly.
- `bot/utils/redis_manager.py:22` - `RedisManager` receives the central config object.
- `bot/utils/redis_manager.py:29` - Redis checks `self.config.redis.enabled`.

### Q8: Resource lifecycle
**Answer:** Startup initializes Redis, loads cogs, opens a single psycopg2 connection, and syncs slash commands. Shutdown closes Wavelink, the single database connection, Redis, the event manager, and then the parent Discord client. Music also closes Wavelink in `cog_unload`, so Lavalink cleanup ownership exists in two places. `aiohttp` sessions are short-lived context managers rather than bot-level resources.

**Evidence:**
- `bot/core/bot.py:140` - `setup_hook()` is the startup hook.
- `bot/core/bot.py:153` - Startup initializes Redis.
- `bot/core/bot.py:162` - Startup loads cogs.
- `bot/core/bot.py:165` - Startup initializes the database connection.
- `bot/core/bot.py:169` - Startup syncs slash commands.
- `bot/core/bot.py:237` - Database setup calls `psycopg2.connect(**params)`.
- `bot/core/bot.py:238` - The psycopg2 connection is stored as `self.db_conn`.
- `bot/core/bot.py:293` - `DarkBot.close()` handles shutdown cleanup.
- `bot/core/bot.py:301` - Shutdown closes `wavelink.Pool`.
- `bot/core/bot.py:309` - Shutdown closes `self.db_conn`.
- `bot/core/bot.py:320` - Shutdown closes Redis through the manager.
- `bot/core/bot.py:326` - Shutdown cleans up the event manager.
- `bot/utils/redis_manager.py:79` - `RedisManager.close()` exists.
- `bot/utils/redis_manager.py:82` - Redis close calls `await self.redis.close()`.
- `bot/cogs/Music.py:33` - Music initializes Lavalink from `cog_load`.
- `bot/cogs/Music.py:52` - Music connects `wavelink.Pool`.
- `bot/cogs/Music.py:57` - Music also defines `cog_unload`.
- `bot/cogs/Music.py:60` - `cog_unload` closes `wavelink.Pool`.
- `bot/cogs/Spotify.py:61` - Spotify uses a short-lived `aiohttp.ClientSession` for token fetch.
- `bot/utils/boardgames.py:35` - BGG utility uses a short-lived `aiohttp.ClientSession`.

## Discovered Unknowns
- The questions doc described six test files, but this checkout currently contains only `tests/test_boardgames.py` plus a committed `tests/__pycache__/...pyc` artifact.
- The questions doc described missing `__init__.py` files, but this checkout currently has `bot/__init__.py`, `bot/config/__init__.py`, `bot/core/__init__.py`, and `bot/cogs/__init__.py`; `bot/utils/__init__.py` is still absent.
- The questions doc mentioned `boardgame_helpers.py`, `boardgame_utils.py`, `spotify_helpers.py`, and `spotify_utils.py`; this checkout instead has `bot/utils/boardgames.py` and no Spotify utility module.
- A root `requirements.txt` exists in addition to `bot/requirements.txt`; Docker uses the bot-local file, while local development may be using the root file or another environment.

## Open Questions
- Which dependency file, if any, is currently used for local development installs?
- Whether committed package init files and the reduced test set are intentional recent changes or an intermediate cleanup state.
- Whether the root `venv` state should be treated as authoritative for local Python version during design, since Docker and the resolved human decision target Python 3.12 while the discovered venv is separate local state.
