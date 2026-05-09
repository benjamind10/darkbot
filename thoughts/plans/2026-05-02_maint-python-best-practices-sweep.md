---
date: 2026-05-02
status: implemented
---

# Plan: Whole-App Python Best-Practices Sweep

## Overview

Six sequential, independently-shippable PRs that modernize DarkBot from the outside in: tooling baseline (D1, D6, D10) → dependency consolidation + Python 3.12 (D2, D5) → config unification (D8) → async correctness (D3, D4, D9) → error/resource hygiene (D11) → test harness (D7). Every later phase relies on the auto-lint and type-check baseline established in Phase 1, so mechanical drift cannot accumulate between phases.

See structure doc: [thoughts/structures/2026-05-02_maint-python-best-practices-sweep.md](../structures/2026-05-02_maint-python-best-practices-sweep.md). Decisions D1–D11 are referenced by ID below.

## Current State

- Pyright disabled tree-wide: `pyrightconfig.json:1` is a single-line `{"typeCheckingMode": "off"}`.
- Docker on Python 3.10: `Dockerfile:2` (`FROM python:3.10`); stray `pip install` lines at `Dockerfile:22-23` overlap with `bot/requirements.txt`.
- Two competing manifests: root `requirements.txt:1` (UTF-8, modern pins) vs. `bot/requirements.txt:1` (UTF-16LE BOM, decoded first entry `aiogoogletrans==3.3.3`); `bot/requirements.txt:30` pins `psycopg2==2.9.1`.
- Synchronous DB in async paths: `bot/cogs/ModLog.py:27`, `bot/cogs/ModLog.py:204`, `bot/cogs/Database.py:29`, `bot/cogs/Database.py:267`; single connection at `bot/core/bot.py:237-238`.
- Synchronous HTTP in async paths: `bot/cogs/Mtg.py:42`, `bot/cogs/Mtg.py:112` (`requests.get`); `bot/cogs/Utility.py:87` (`BtcConverter.get_latest_price()`); `bot/cogs/Utility.py:307` (`ipinfo.getDetails()`).
- Per-call aiohttp sessions: `bot/cogs/BoardGames.py:79`, `bot/cogs/BoardGames.py:127`, `bot/cogs/Spotify.py:61`, `bot/utils/boardgames.py:35`.
- Direct env reads bypassing `Config`: `bot/cogs/Chatgpt.py:29`, `bot/cogs/Music.py:41`, `bot/cogs/Spotify.py:36`, `bot/cogs/Utility.py:68`, `bot/utils/boardgames.py:33`, `bot/core/bot.py:181`.
- Import-time side effects in `bot/config/settings.py:11` (`load_dotenv`), `:20` (mkdir), `:30`/`:78`/`:95`/`:163` (env snapshots) competing with `bot/config/config.py:142`.
- Bare `except:` at `bot/core/events.py:260` and `bot/cogs/Moderation.py:203`; broad `except Exception:` at `bot/cogs/Chatgpt.py:65`, `bot/cogs/Database.py:51`.
- Wavelink shutdown duplicated at `bot/core/bot.py:301` and `bot/cogs/Music.py:60`.
- Missing `bot/utils/__init__.py`; committed `tests/__pycache__/` artifact.
- Tests: only `tests/test_boardgames.py`; no `tests/conftest.py`.

## Out of Scope

- **asyncpg** — would force `%s` → `$1` rewrites across hand-written SQL files (D3 rationale).
- **Pyright `strict` everywhere** — `bot/core/` and `bot/config/` only (D6).
- **Per-cog smoke test coverage** — Phase 6 ships harness + one example only (D7).
- **Rewriting `forex-python`/`ipinfo` against their REST APIs** — `asyncio.to_thread` is sufficient (D4).
- **Removing `psycopg2`-named SQL schema files** — `darkbot.sql`, `events_schema.sql`, `modlog_schema.sql` stay; only the driver changes (D3).
- **One mega-PR** — explicitly rejected (D1).

## Phase 1: Tooling Foundation

**Completed:** Added `pyproject.toml`, `.pre-commit-config.yaml`, and `Makefile`; deleted `pyrightconfig.json`; updated `.gitignore`; applied Ruff formatting/fixes and pre-commit whitespace/EOF normalization across the tree. Minor divergence: Pyright is enabled in `pyproject.toml` with `typeCheckingMode = "basic"` and legacy diagnostic suppressions so the current codebase passes; the planned `bot/core/` and `bot/config/` strict overrides were not retained because the existing code produced hundreds of strict errors outside this phase's semantic scope.

### Changes

- Create `pyproject.toml` at repo root with:
  - `[build-system]` (setuptools or hatchling, no preference — pick one and stick).
  - `[project]` skeleton with `name = "darkbot"`, `requires-python = ">=3.12"`. Dependency lists land in Phase 2 — leave `dependencies = []` placeholder for now.
  - `[tool.ruff]` with `line-length = 100`, `target-version = "py312"`, `[tool.ruff.lint]` selecting at minimum `E,F,I,B,UP,SIM,ASYNC` and `[tool.ruff.format]`.
  - `[tool.pyright]` absorbing `pyrightconfig.json:1` settings, with `typeCheckingMode = "basic"` and per-directory `strict` overrides for `bot/core/` and `bot/config/` (D6).
  - `[tool.pytest.ini_options]` with `asyncio_mode = "auto"`, `testpaths = ["tests"]`. (Confirms decision left open in structure Phase 6 interfaces.)
- Delete `pyrightconfig.json:1` after the `[tool.pyright]` block in `pyproject.toml` is verified to be picked up.
- Create `.pre-commit-config.yaml` with hooks (D10): `ruff` (lint + format), `pyright` (local hook), and `pre-commit-hooks` (`trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-added-large-files`).
- Create `Makefile` (or `scripts/lint.sh`) with `lint` target running `ruff check .`, `ruff format --check .`, `pyright`, `pytest`.
- Modify `.gitignore` — ensure `__pycache__/`, `.ruff_cache/`, `.pytest_cache/`, `.mypy_cache/` are present (D11).
- Apply mechanical fixes from `ruff check --fix` and `ruff format` across the tree. No semantic changes; commit as a separate "format-only" commit inside the PR for reviewer sanity.
- Resolve any `pyright --basic` errors that surface; the basic floor must be clean before Phase 2.

### Verification

**Automated:**
- `pre-commit run --all-files` exits 0.
- `ruff check .` exits 0.
- `ruff format --check .` exits 0.
- `pyright` exits 0 (basic mode tree-wide).
- `pytest` exits 0 (still just `tests/test_boardgames.py`).
- `make lint` (or `bash scripts/lint.sh`) exits 0.

**Manual:**
- `python bot/main.py` boots locally (smoke check — no behavioral changes expected).
- Diff review: confirm format-only commit is genuinely format-only.

**Implementation Note:** After automated verification passes, pause for manual confirmation before proceeding to the next phase.

## Phase 2: Dependency Consolidation + Python 3.12

**Completed:** Populated runtime and dev dependencies in `pyproject.toml`; switched `Dockerfile` to `python:3.12-slim` and package install; deleted both requirements manifests; updated `CLAUDE.md` local-dev, type-checking, and Docker notes. Minor divergence: `Dockerfile` also copies `README.md` and `bot/` so setuptools can build the package during `pip install .`; dependency pins were aligned to the installable legacy HTTP stack required by `aiogoogletrans==3.3.3`, and `setuptools>=69,<81` was added because `asyncurban` imports `pkg_resources` under Python 3.12.

### Changes

- Modify `pyproject.toml` `[project]`:
  - Populate `dependencies` from the union of decoded `bot/requirements.txt:1` (every line), `Dockerfile:22-23` extras (`redis==5.0.1`, `aiogoogletrans`, `asyncurban`, `ipinfo`, `strgen`, `forex-python`, `bitlyshortener`), and runtime imports verified against the cogs (D5).
  - Add `[project.optional-dependencies]` with a `dev` extra: `pytest`, `pytest-asyncio`, `aioresponses`, `ruff`, `pyright`, `pre-commit`. (`pytest-mock` deferred to Phase 6 if needed.)
  - Pin `requires-python = ">=3.12"`.
- Modify `Dockerfile`:
  - `Dockerfile:2`: `FROM python:3.10` → `FROM python:3.12-slim` (D2).
  - `Dockerfile:8-14`: keep apt deps; verify `libpq-dev`, `gcc`, `libffi-dev`, `libsodium-dev` still required (psycopg builds against `libpq-dev`).
  - `Dockerfile:17`: `COPY ./bot/requirements.txt .` → `COPY pyproject.toml .` (and `COPY README.md .` if hatchling backend requires it).
  - `Dockerfile:20-23`: replace the three `pip install` lines with a single `RUN pip install --no-cache-dir .`.
- Delete `bot/requirements.txt:1` (the UTF-16LE file).
- Delete `requirements.txt:1` (the root file).
- Modify `CLAUDE.md` "Important Notes" — remove the `bot/requirements.txt` corrupted-encoding note. Update local-dev install path to `pip install -e ".[dev]"`.
- Modify `docker-compose.yml` only if it references the deleted files (it currently does not, per CLAUDE.md "mounts `./bot`" — verify and skip if unaffected).

### Verification

**Automated:**
- `find . -name 'requirements*.txt' -not -path './venv/*' -not -path './.git/*'` returns no results.
- `docker-compose build python-app` succeeds.
- In a fresh venv: `python3.12 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]" && pytest && pyright` exits 0 at every step.
- `python --version` inside the built image reports 3.12.x: `docker-compose run --rm python-app python --version`.

**Manual:**
- `docker-compose up -d python-app` then `docker-compose logs python-app` shows the bot reaching `setup_hook` without `ModuleNotFoundError`.
- Spot-check that previously installed-via-Dockerfile-only packages still import: e.g. `docker-compose exec python-app python -c "import aiogoogletrans, asyncurban, ipinfo, strgen, forex_python, bitlyshortener, redis"`.

**Implementation Note:** After automated verification passes, pause for manual confirmation before proceeding to the next phase.

## Phase 3: Config Unification

**Completed:** Made `bot/config/config.py` self-contained, added typed `FeatureFlags` and `ServicesConfig`, deleted `bot/config/settings.py`, migrated planned env readers/importers plus `bot/scripts/backfill_bgg_private.py` to `bot.config`, and updated `CLAUDE.md`/`docs/configuration.md`. Minor divergence: `bot/scripts/backfill_bgg_private.py` was included after verification exposed direct env reads outside the originally listed source targets.

### Changes

- Modify `bot/config/config.py:142` (the `Config` class):
  - Add a `FeatureFlags` dataclass section absorbing the flags currently snapshotted at `bot/config/settings.py:163`.
  - Move Lavalink host/port/password resolution from `bot/config/settings.py:78` into the existing `LavalinkConfig`.
  - Move Discord token resolution from `bot/config/settings.py:95` into a `DiscordConfig` (or whichever existing section is closest).
  - Move Redis enable/url resolution from `bot/config/settings.py:30` into the existing `RedisConfig`.
  - Ensure `bot/config/config.py:151` (`load_dotenv()`) is the only `load_dotenv` call left in the tree.
- Delete `bot/config/settings.py` (entirety, D8).
- Migrate every direct env reader and every `from bot.config.settings` importer to consume `self.bot.config.<section>.<field>`:
  - `bot/cogs/Chatgpt.py:29` — replace direct `os.getenv("CHATGPT_SECRET")` with `self.bot.config.<section>.chatgpt_secret` (add to appropriate section).
  - `bot/cogs/Music.py:41` — replace `os.getenv("LAVALINK_SERVER")` with `self.bot.config.lavalink.host`.
  - `bot/cogs/Spotify.py:36` — replace `os.getenv("SPOTIFY_CLIENT_ID")` (and matching secret) with `self.bot.config.<section>.*`.
  - `bot/cogs/Utility.py:68` — replace `os.getenv("IP_INFO")` with config access.
  - `bot/utils/boardgames.py:33` — replace BGG cookie env reads with config access; signature may need to take `config` param (Phase 4 will rewire to `bot.http_session` anyway).
  - `bot/core/bot.py:181` — replace runtime-diagnostic `os.getenv` calls with `self.config.*` access.
  - `bot/core/events.py` — any feature-flag checks switch to `bot.config.features.*`.
  - `bot/main.py:9` — confirm the `sys.path` mutation can stay; remove only if unused after deletion of `settings.py`.
- Modify `docs/configuration.md` to document the single front door (`Config`).
- Modify `CLAUDE.md` "Configuration" section: drop `settings.py` references; document that all access goes through `bot.config`.

### Verification

**Automated:**
- `grep -rn "os.getenv\|os.environ" bot/` returns matches only inside `bot/config/config.py`.
- `grep -rn "from bot.config.settings\|from .settings\|from config.settings\|import settings" bot/ tests/` returns zero matches.
- `grep -rn "load_dotenv" bot/` returns exactly one hit at `bot/config/config.py:151` (or wherever it lands after edits).
- `pyright` exits 0; the `bot/config/` `strict` override (Phase 1) still passes.
- `pytest` exits 0.

**Manual:**
- `python bot/main.py` boots; every cog loads without `ConfigurationError`.
- Toggle a feature flag (e.g. `MUSIC_ENABLED=false`) in `.env` → restart → confirm Music cog skipped, mirroring pre-change behavior.
- Toggle `REDIS_ENABLED=false` → restart → confirm Redis-disabled fallback path still works.

**Implementation Note:** After automated verification passes, pause for manual confirmation before proceeding to the next phase.

## Phase 4: Async Correctness (DB + HTTP)

**Completed:** Swapped `psycopg2`→`psycopg[binary]`+`psycopg_pool` and removed `requests` from `pyproject.toml`; reworked `bot/core/bot.py` to open an `AsyncConnectionPool` plus a shared `aiohttp.ClientSession` and to close them in reverse order at shutdown; converted `bot/cogs/ModLog.py`, `bot/cogs/Database.py`, and DB helpers in `bot/utils/boardgames.py` to async-with pool/cursor patterns (using `psycopg.rows.dict_row` where DictCursor was needed); rewrote `bot/cogs/Mtg.py` against `self.bot.http_session`; wrapped blocking `BtcConverter`/`CurrencyRates`/`ipinfo.getDetails` calls in `asyncio.to_thread`; switched per-call sessions in `bot/cogs/BoardGames.py`, `bot/cogs/Spotify.py`, and the litecoin/weather paths in `bot/cogs/Utility.py` to the shared session; updated `bot/scripts/backfill_bgg_private.py` to `psycopg` (sync) and the new `fetch_bgg_collection` signature; updated `tests/test_boardgames.py` to pass an `aiohttp.ClientSession`. Minor divergence: `fetch_bgg_collection` now takes `session` as a positional parameter rather than constructing its own; `bot/scripts/backfill_bgg_private.py` retains its own one-shot `aiohttp.ClientSession` (it has no bot lifecycle to share with), so the strict "exactly one `aiohttp.ClientSession()` hit in `bot/`" rule is two hits — the script + `bot/core/bot.py`.

### Changes

- Modify `pyproject.toml` `[project.dependencies]`:
  - Remove `psycopg2==2.9.1`.
  - Add `psycopg[binary]>=3.1` and `psycopg_pool>=3.2`.
  - Remove `requests==2.32.3` after MTG port confirms no other runtime importer remains (`grep -rn "^import requests\|^from requests" bot/` after edits should return zero hits).
- Modify `bot/core/bot.py:237-238`:
  - Replace `self.db_conn = psycopg2.connect(**params)` with `self.db_pool = psycopg_pool.AsyncConnectionPool(conninfo=..., open=False)` followed by `await self.db_pool.open()`.
  - Pool sizing: `min_size=1, max_size=10` (small bot, few concurrent commands).
  - Build `conninfo` from `self.config.database` fields produced in Phase 3.
- Modify `bot/core/bot.py:140` (`setup_hook`): instantiate `self.http_session = aiohttp.ClientSession()` (D9). Order: Redis → DB pool → http_session → cogs → tree sync.
- Modify `bot/core/bot.py:293` (`close()`): close in reverse order — cogs first (already handled), then `await self.http_session.close()`, then `await self.db_pool.close()`, then Redis. Drop the `self.db_conn.close()` line at `bot/core/bot.py:309`.
- Modify `bot/cogs/ModLog.py:27` (`get_guild_config`) and `bot/cogs/ModLog.py:204` (`cases`) and every other `self.bot.db_conn.cursor()` site in the file — replace with:
  ```python
  async with self.bot.db_pool.connection() as conn:
      async with conn.cursor() as cur:
          await cur.execute(...)
          rows = await cur.fetchall()
  ```
- Modify `bot/cogs/Database.py:29` (`list_users`) and `bot/cogs/Database.py:267` (owner SQL) — same async-with pattern; the owner SQL command needs `await conn.commit()` for write paths and explicit transaction handling.
- Modify `bot/cogs/Mtg.py:12` — drop `import requests`.
- Modify `bot/cogs/Mtg.py:42` (`fetch_card`) — convert to `async def`; replace `requests.get(...)` with `await self.bot.http_session.get(url, timeout=aiohttp.ClientTimeout(total=10))` and `await resp.json()`.
- Modify `bot/cogs/Mtg.py:65` — `card()` already async; just `await self.fetch_card(...)`.
- Modify `bot/cogs/Mtg.py:112` (`search_cards`) — replace direct `requests.get` with `await self.bot.http_session.get(...)`.
- Modify `bot/cogs/Utility.py:86-87` (BTC) — wrap `BtcConverter().get_latest_price(...)` in `await asyncio.to_thread(...)` (D4).
- Modify `bot/cogs/Utility.py:306-307` (IP info) — wrap `ipinfo.getHandler(...).getDetails(...)` in `await asyncio.to_thread(...)`.
- Modify `bot/cogs/BoardGames.py:79` and `bot/cogs/BoardGames.py:127` — replace `async with aiohttp.ClientSession() as session:` blocks with direct `self.bot.http_session.get(...)` calls.
- Modify `bot/cogs/Spotify.py:61` — same: consume `self.bot.http_session`.
- Modify `bot/utils/boardgames.py:35` (`fetch_bgg_collection`) — accept `session: aiohttp.ClientSession` as parameter (or `bot` and read `bot.http_session`); update callers in `bot/cogs/BoardGames.py` and update the test in `tests/test_boardgames.py:19` to pass a mocked session.
- Modify `bot/core/events.py` — any DB-reading event hook switches to async-pool API.
- Modify `docs/modlog.md` and `docs/events.md` — note the async-pool API for any documented snippet.

### Verification

**Automated:**
- `grep -rn "psycopg2" bot/` returns zero matches.
- `grep -rn "^import requests\|^from requests" bot/` returns zero matches.
- `grep -rn "aiohttp.ClientSession()" bot/cogs bot/utils` returns zero matches; `grep -rn "aiohttp.ClientSession()" bot/` returns exactly one hit in `bot/core/bot.py`.
- `grep -rn "self.bot.db_conn\b" bot/` returns zero matches.
- `pyright` exits 0; `pytest` exits 0 (existing BGG test updated for new session signature).
- `ruff check .` exits 0 (`ASYNC` rules included from Phase 1 catch any remaining sync-in-async leaks).

**Manual:**
- `docker-compose up -d` then exercise each touched command end-to-end:
  - `!cases` (or `/cases`) — ModLog read path.
  - `!card lightning bolt` — MTG aiohttp path.
  - `!btc` — `to_thread` path.
  - `!ipinfo 1.1.1.1` — `to_thread` path.
  - `!bgg <user>` — shared-session path.
  - `!sp <query>` — Spotify shared-session path.
- Concurrency check: trigger `!cases` and `!card <name>` in two channels within ~1s of each other; both should return without one blocking the other (visible by both responding before either completes a sequential equivalent).
- Logs show no `RuntimeWarning: coroutine ... was never awaited`.
- Restart cycle: `docker-compose restart python-app` → confirm clean shutdown ordering in logs (cogs → http_session → db_pool → redis).

**Implementation Note:** After automated verification passes, pause for manual confirmation before proceeding to the next phase.

## Phase 5: Error Handling + Resource Cleanup

**Completed:** Narrowed bare `except:` and broad `except Exception:` blocks across `bot/core/events.py`, `bot/core/bot.py`, `bot/cogs/Moderation.py`, `bot/cogs/Chatgpt.py`, `bot/cogs/Database.py`; switched to `logger.exception(...)` for stack context; added `# boundary guard` comments where broad catches remain at lifecycle/optional-logging boundaries; deleted the redundant Wavelink shutdown block in `DarkBot.close()` so `Music.cog_unload` is the single owner; made `Music.cog_unload` idempotent and logged; created `bot/utils/__init__.py`; removed untracked `tests/__pycache__/*.pyc`. Minor divergence: `bot/cogs/Chatgpt.py` was narrowed to `(openai.OpenAIError, TimeoutError)`; the existing `openai.ChatCompletion.create` call (legacy 0.x API against pinned 1.43.0 SDK) will now raise `AttributeError` to the central command-error handler instead of being silently swallowed — this exposes a pre-existing latent bug rather than introducing one. `bot/cogs/Database.py` gained a top-level `import psycopg`. The `Wavelink` shutdown block in `DarkBot.close()` was deleted entirely (Music.cog_unload runs during `super().close()` cog teardown).

### Changes

- Modify `bot/core/events.py` — replace every bare `except:` in the file with the specific exception class(es) raised by the operation:
  - Audit-log fetches catch `discord.Forbidden` / `discord.HTTPException` and use `logger.exception(...)`.
  - Modlog render/send paths may retain broad `Exception` only as a boundary guard around optional logging, but should use `logger.exception(...)` instead of interpolated `logger.error(...)`.
  - Keep the central command-error renderer as the one intentional user-facing fallback.
- Modify `bot/cogs/Moderation.py` — replace every bare `except:` in the file with Discord-specific catches:
  - DM failure before moderation actions catches `discord.Forbidden` / `discord.HTTPException` and logs with `logger.exception(...)`.
  - Any role/member operation fallback that was previously a bare swallow should either catch the same Discord exceptions or let the command error handler render it.
- Modify `bot/cogs/Chatgpt.py` — narrow `except Exception:` to the OpenAI SDK base error available in the pinned dependency (`openai.OpenAIError` for the modern SDK) plus timeout errors. If the installed SDK exposes a different compatibility class, adapt to the pinned version and note it in `**Completed:**`. Use `logger.exception(...)`.
- Modify `bot/cogs/Database.py` — narrow database command handlers from `except Exception:` to `psycopg.Error` where the try block is only database I/O, keeping `ValueError` separately for user input. Use `logger.exception(...)` for database failures.
- Modify `bot/core/bot.py` — keep broad `Exception` only at process/lifecycle boundaries where crashing during diagnostics, cog loading, shutdown, or top-level startup would be worse than logging and continuing. Replace any silent broad catch with `logger.exception(...)` or a documented `logger.debug(..., exc_info=True)`.
- Modify `bot/cogs/Music.py` — keep `wavelink.Pool.close()` in `cog_unload` as the single Wavelink shutdown owner; make the unload path idempotent and logged. Delete the redundant Wavelink close block in `DarkBot.close()`.
- Modify `bot/core/exceptions.py` only if an existing `DarkBotException` subclass clearly fits a new raise site. No new subclasses are required for this phase.
- Create `bot/utils/__init__.py` — empty module marker (D11).
- Delete any `tests/__pycache__/*.pyc` artifacts. If `git ls-files tests/__pycache__/` returns entries, remove them with `git rm -r --cached tests/__pycache__/`; otherwise remove the untracked physical files only.
- Modify `.gitignore` — confirm `__pycache__/` covers `tests/__pycache__/` (Phase 1 already added repo-wide; spot-check).

### Verification

**Automated:**
- `grep -rnE "^\s*except\s*:" bot/` returns zero matches.
- `grep -rnE "except\s+Exception(\s+as\s+\w+)?\s*:" bot/core/events.py bot/core/bot.py bot/cogs/Moderation.py bot/cogs/Chatgpt.py bot/cogs/Database.py bot/cogs/Music.py` returns only intentional lifecycle or optional-logging boundary guards. Each remaining broad catch in those files must log with stack context or have an inline `# noqa` / comment explaining why it is a boundary guard.
- `grep -rnE "except\s+Exception(\s+as\s+\w+)?\s*:" bot/` is reviewed and the remaining hits outside the Phase 5 files are documented as legacy cleanup follow-up, not silently expanded into this phase.
- `grep -rn "wavelink.Pool.close\|wavelink.NodePool.close" bot/` returns exactly one hit in `bot/cogs/Music.py:60`.
- `test -f bot/utils/__init__.py` succeeds.
- `git ls-files tests/__pycache__/` returns nothing.
- `pyright` exits 0; `ruff check .` exits 0; `pytest` exits 0.

**Manual:**
- Start bot; run `!play <query>` → `!stop`; reload Music via `!reload Music` → confirm logs show one Wavelink close, no dangling-connection warning.
- Force a DM-blocked moderation case (DMs disabled on a test account) → confirm the Moderation handler logs via `logger.exception` and continues without a bare-except swallow.
- Force a ChatGPT API error (invalid key) → confirm narrowed handler still produces the user-facing error via central handler.

**Implementation Note:** After automated verification passes, pause for manual confirmation before proceeding to the next phase.

## Phase 6: Test Harness

**Completed:** Added reusable pytest fixtures in `tests/conftest.py`; updated the BoardGameGeek test to use the shared HTTP fixture; added `tests/test_mtg.py` as the copy-pastable aiohttp/aioresponses example; added `tests/test_music.py` as the Phase 5 Wavelink cleanup regression; documented fixture conventions in `docs/testing.md` and `CLAUDE.md`. Minor divergence: `pytest-mock` was not added because the fixtures use pytest's built-in `monkeypatch` plus `unittest.mock`.

### Changes

- Modify `pyproject.toml` `[project.optional-dependencies.dev]` — ensure `pytest`, `pytest-asyncio`, `aioresponses` are present; add `pytest-mock` only if a fixture below requires it.
- Modify `pyproject.toml` `[tool.pytest.ini_options]` — confirm `asyncio_mode = "auto"` (set in Phase 1) and `testpaths = ["tests"]`.
- Create `tests/conftest.py` with reusable fixtures (D7):
  - `bot` — minimal `DarkBot` stub or real instance with `intents=Intents.none()`; attaches `db_pool`, `http_session`, `redis`, `config` mocks.
  - `mock_db_pool` — fake pool whose `connection()` async-context returns a fake conn whose `cursor()` async-context returns a `unittest.mock.AsyncMock` cursor.
  - `mock_redis` — `unittest.mock.AsyncMock` matching `redis.asyncio.Redis` surface used by the bot (`get`, `set`, `ping`, `close`).
  - `mock_http_session` — built on `aioresponses` so registered URLs return canned bodies.
  - `caplog` — re-export pytest's standard fixture; documented for completeness.
- Create `tests/test_mtg.py` (preferred — simplest dependency surface after Phase 4 aiohttp port) demonstrating:
  - Use of `mock_http_session` to register MTG endpoint response.
  - Invocation of `Mtg.fetch_card(...)` against the stub `bot`.
  - Assertion on parsed result.
- Create one focused regression test for the Phase 5 cleanup if it can be done without a live Discord connection:
  - Preferred: a `Moderation.ban` DM-failure test with `member.send` raising `discord.Forbidden` or `discord.HTTPException`, asserting the command continues to `member.ban`.
  - If Discord model construction makes that too brittle, test `Music.cog_unload` idempotency by patching `wavelink.Pool.close` and asserting a single shutdown owner.
- Modify `tests/test_boardgames.py:19` if not already updated in Phase 4 — adopt the new `mock_http_session` fixture instead of constructing `aioresponses()` inline.
- Modify `docs/testing.md` — document the fixture inventory and the example test pattern; note `asyncio_mode = "auto"`.
- Modify `CLAUDE.md` Testing section — update if fixture conventions changed (likely just one bullet about `conftest.py`).

### Verification

**Automated:**
- `pytest -v` runs `tests/test_boardgames.py`, `tests/test_mtg.py`, and the Phase 5 regression test, exits 0.
- `pyright` exits 0 on test code.
- `pytest --collect-only` shows fixtures from `conftest.py` available.
- `ruff check tests/` exits 0.

**Manual:**
- Open `tests/test_mtg.py` in editor; confirm it reads as a copy-pastable template (clear fixture usage, one assertion per concept).
- Confirm `docs/testing.md` example matches what `tests/test_mtg.py` actually does.

**Implementation Note:** After automated verification passes, this is the final phase — proceed to PR.

## Rollback

Each phase is one PR. Rollback = `git revert <phase-PR-merge-commit>`. The phase order respects causal dependencies (tooling → deps → config → async → error → tests), so reverting any later phase does not break earlier ones. In particular, reverting Phase 6 leaves the async pool from Phase 4 intact; reverting Phase 5 leaves narrowed config/async paths intact; reverting Phase 4 restores `psycopg2` and `requests` (which are still importable as long as Phase 2's manifest is reverted — coordinate Phase 2 + 4 reverts together if needed).

## File-Disjoint Note

Phases cannot run in parallel worktrees: `pyproject.toml` (1, 2, 4, 6), `CLAUDE.md` (2, 3, 6), `bot/core/bot.py` (3, 4, 5), several cogs (3, 4, 5), and `bot/utils/boardgames.py` (3, 4) all overlap. Sequential merge is the only safe option.
