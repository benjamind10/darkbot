---
date: 2026-05-02
---

# Structure: Whole-App Python Best-Practices Sweep

## Approach

Six sequential PRs that modernize the codebase from the outside in: first the tooling and dependency baseline (so every later slice is auto-linted and type-checked), then config unification, then runtime correctness (async DB + sync-in-async fixes), then error/resource hygiene, and finally the test harness. Each slice is independently shippable and reviewable, with explicit checkpoints between phases.

## Resolved Decisions

### D1: Six sequential PRs over one mega-PR
**Decision:** Ship each slice as its own PR in the order below.
**Rationale:** Independent verification per slice; bisecting a regression doesn't drag unrelated changes; gives natural redirect checkpoints. The codebase touches 13 cogs ([CLAUDE.md cog table]) — a single PR would be unreviewable.

### D2: Python 3.12 in Docker and toolchain
**Decision:** Bump base image and tooling targets to Python 3.12.
**Rationale:** Better typing diagnostics, runtime perf wins, and matches the resolved-decision note in research's open questions ([thoughts/research/2026-05-02_maint-python-best-practices-sweep.md:161](../research/2026-05-02_maint-python-best-practices-sweep.md#L161)). Current image is `python:3.10` ([Dockerfile:2](../../Dockerfile#L2)).

### D3: Async DB via `psycopg` v3 + `psycopg_pool`
**Decision:** Replace synchronous `psycopg2` with `psycopg` v3 async driver and `psycopg_pool` for a real connection pool. SQL strings stay (`%s` placeholders compatible).
**Rationale:** Current code blocks the event loop on every cursor call ([bot/cogs/ModLog.py:27](../../bot/cogs/ModLog.py#L27), [bot/cogs/ModLog.py:204](../../bot/cogs/ModLog.py#L204), [bot/cogs/Database.py:29](../../bot/cogs/Database.py#L29), [bot/cogs/Database.py:267](../../bot/cogs/Database.py#L267)) and shares a single connection ([bot/core/bot.py:237-238](../../bot/core/bot.py#L237-L238)). asyncpg would force rewriting `%s` → `$1` across hand-written SQL files for a hobby-scale workload — not worth it.

### D4: MTG → aiohttp; forex/ipinfo → `asyncio.to_thread`
**Decision:** Rewrite MTG HTTP against `aiohttp` directly (REST is trivial). Wrap blocking SDK calls (`forex-python`, `ipinfo`) in `asyncio.to_thread`.
**Rationale:** MTG's API is plain JSON over HTTP ([bot/cogs/Mtg.py:42](../../bot/cogs/Mtg.py#L42), [bot/cogs/Mtg.py:112](../../bot/cogs/Mtg.py#L112)) — easy aiohttp port. Rewriting against the underlying REST APIs of `forex-python`/`ipinfo` ([bot/cogs/Utility.py:87](../../bot/cogs/Utility.py#L87), [bot/cogs/Utility.py:307](../../bot/cogs/Utility.py#L307)) is scope creep for low-frequency commands; `to_thread` is sufficient.

### D5: `pyproject.toml` is the single dependency manifest
**Decision:** Consolidate into PEP 621 `pyproject.toml` with `[project]` and `[project.optional-dependencies.dev]`. Delete root `requirements.txt` ([requirements.txt:1](../../requirements.txt#L1)) and the UTF-16LE `bot/requirements.txt` ([bot/requirements.txt:1](../../bot/requirements.txt#L1)). Tooling config (ruff, pyright, pytest) co-locates in the same file. Dockerfile's stray `pip install` lines ([Dockerfile:22-23](../../Dockerfile#L22-L23)) are absorbed.
**Rationale:** Two competing manifests + ad-hoc Docker layer is the current state and the highest-value cleanup target. PEP 621 is the modern Python convention.

### D6: Pyright `basic` everywhere, `strict` on `bot/core/` + `bot/config/`
**Decision:** Default `typeCheckingMode = "basic"` for the tree; `strict` overrides for `bot/core/` and `bot/config/`. Currently disabled at [pyrightconfig.json:1](../../pyrightconfig.json#L1).
**Rationale:** `strict` everywhere is multi-week work across 13 cogs; `basic` everywhere underdelivers on the modules that touch every cog. This gives leverage where it matters.

### D7: Test slice = harness + one example, expansion is follow-up
**Decision:** Phase 6 ships `conftest.py` + reusable fixtures (bot, Redis, DB pool, aiohttp mocks) + ONE new async cog test demonstrating the pattern. Per-cog smoke tests are out of scope for this sweep.
**Rationale:** 13 cogs × full smoke coverage is a separate project; landing the harness unlocks future test work without bloating this PR series.

### D8: Delete `bot/config/settings.py` entirely
**Decision:** Move feature flags onto `Config`. All `settings.py` consumers migrate to `bot.config`. File is removed.
**Rationale:** `settings.py` snapshots env at import time ([bot/config/settings.py:11](../../bot/config/settings.py#L11), [bot/config/settings.py:30](../../bot/config/settings.py#L30), [bot/config/settings.py:95](../../bot/config/settings.py#L95)) and competes with `Config` ([bot/config/config.py:142](../../bot/config/config.py#L142)). One front door is the goal.

### D9: Bot-level shared `aiohttp.ClientSession`
**Decision:** Introduce `self.http_session` on `DarkBot`, opened in `setup_hook()` and closed in `close()`. Cogs and utils consume it instead of opening per-call sessions ([bot/cogs/BoardGames.py:79](../../bot/cogs/BoardGames.py#L79), [bot/cogs/BoardGames.py:127](../../bot/cogs/BoardGames.py#L127), [bot/cogs/Spotify.py:61](../../bot/cogs/Spotify.py#L61), [bot/utils/boardgames.py:35](../../bot/utils/boardgames.py#L35)).
**Rationale:** Connection reuse, single shutdown owner, easier to mock in tests.

### D10: Pre-commit on changed files; full-tree in CI
**Decision:** `pre-commit-config.yaml` runs ruff format + ruff check + pyright on staged files plus standard hygiene hooks (trailing-whitespace, end-of-file-fixer, check-yaml). A `make lint` target (or equivalent) runs the full tree for CI.
**Rationale:** Keeps daily commits friction-free without giving up coverage.

### D11: Repo hygiene
**Decision:** Add missing [bot/utils/__init__.py](../../bot/utils/); remove committed `tests/__pycache__/*.pyc` artifact; add `__pycache__/` to `.gitignore` if not present.
**Rationale:** Research flagged both as in-flight cleanup state ([thoughts/research/2026-05-02_maint-python-best-practices-sweep.md:153-154](../research/2026-05-02_maint-python-best-practices-sweep.md#L153-L154)).

## Not Doing

- **asyncpg** — would force rewriting all SQL placeholders and schema-attached query strings for negligible benefit at this scale.
- **Pyright `strict` everywhere** — multi-week scope, separate project.
- **Per-cog smoke test coverage** — Phase 6 lands the harness only; coverage expansion is follow-up work.
- **Rewriting forex-python / ipinfo against their REST APIs** — `asyncio.to_thread` is good enough for low-frequency commands.
- **Removing `psycopg2`-named SQL files** — schemas (`darkbot.sql`, `events_schema.sql`, `modlog_schema.sql`) stay as-is; only the driver changes.
- **One mega-PR** — explicitly rejected in D1.
- **Mega test refactor** — see D7.

## Phase Overview

### Phase 1: Tooling Foundation
**Goal:** `ruff check`, `ruff format --check`, `pyright`, `pytest`, and `pre-commit` all run from a clean clone and pass on the unchanged tree (or with mechanical-only fixes applied).
**Files:**
- Create: `pyproject.toml` (project metadata + tool config), `.pre-commit-config.yaml`, `.ruff.toml` (only if not consolidated into pyproject), `Makefile` or `scripts/lint.sh` for full-tree lint.
- Modify: `pyrightconfig.json` (toggle `typeCheckingMode` to `basic`, add `strict` overrides for `bot/core/` and `bot/config/`) — or absorb entirely into `pyproject.toml` and delete the JSON.
- Modify: `.gitignore` (ensure `__pycache__/`, `.ruff_cache/`, `.pytest_cache/` covered).
- Mechanical fixes from `ruff --fix` and basic Pyright across the tree.
**Interfaces:**
- `pyproject.toml` `[tool.ruff]`, `[tool.pyright]`, `[tool.pytest.ini_options]` sections established.
- Pre-commit hook contract: ruff format + ruff check + pyright on staged Python files + hygiene hooks.
- `make lint` (or equivalent) runs the full tree.
**Depends on:** nothing.
**Checkpoint:**
- `pre-commit run --all-files` exits 0 (or with only mechanical fixes that get committed).
- `pyright` exits 0 in basic mode.
- `pytest` runs and passes (still the existing single test).
- Bot still starts via `python bot/main.py` — smoke check.

### Phase 2: Dependency Consolidation + Python 3.12
**Goal:** Single source of truth for dependencies; Docker image runs Python 3.12; the UTF-16LE manifest and root `requirements.txt` are gone.
**Files:**
- Modify: `pyproject.toml` (add `[project.dependencies]` and `[project.optional-dependencies.dev]` populated from decoded `bot/requirements.txt` + Dockerfile stray installs + test deps).
- Modify: `Dockerfile` (base → `python:3.12-slim`, replace `pip install -r requirements.txt` + extra `pip install` lines with `pip install .` or `pip install --no-cache-dir .`).
- Delete: `bot/requirements.txt`, root `requirements.txt`.
- Modify: `CLAUDE.md` (remove the "corrupted encoding" note about `bot/requirements.txt` since it's gone; update local-dev install instructions).
- Modify: `docker-compose.yml` if it references the old file.
**Interfaces:**
- `pyproject.toml` `[project]` block: `name`, `version`, `requires-python = ">=3.12"`, `dependencies = [...]`.
- Local install contract: `pip install -e ".[dev]"` is the documented path.
- Docker install contract: `pip install --no-cache-dir .` inside the image.
**Depends on:** Phase 1 (pyproject.toml exists).
**Checkpoint:**
- `docker-compose build` succeeds on the new base image.
- `docker-compose up python-app` boots without missing-dependency errors.
- Fresh `pip install -e ".[dev]"` in a clean venv reproduces working `pytest` + `pyright`.
- `find . -name 'requirements*.txt'` returns nothing.

### Phase 3: Config Unification
**Goal:** `Config` is the only path to settings. `bot/config/settings.py` is deleted. No cog calls `os.getenv` directly.
**Files:**
- Modify: `bot/config/config.py` (absorb feature flags + Lavalink/Redis snapshot logic from `settings.py`; expose feature-flag accessors).
- Delete: `bot/config/settings.py`.
- Modify: every cog/util that imports from `settings.py` or calls `os.getenv` directly: [bot/cogs/Chatgpt.py](../../bot/cogs/Chatgpt.py), [bot/cogs/Music.py](../../bot/cogs/Music.py), [bot/cogs/Spotify.py](../../bot/cogs/Spotify.py), [bot/cogs/Utility.py](../../bot/cogs/Utility.py), [bot/utils/boardgames.py](../../bot/utils/boardgames.py), [bot/core/bot.py](../../bot/core/bot.py), [bot/core/events.py](../../bot/core/events.py), [bot/main.py](../../bot/main.py).
- Modify: `docs/configuration.md` (reflect single front door).
- Modify: `CLAUDE.md` (remove `settings.py` from the configuration section; document the unified path).
**Interfaces:**
- `Config.features.<flag_name>` (or equivalent) replaces `from bot.config.settings import FEATURES`.
- `Config.lavalink.host`, `Config.lavalink.port` replace direct env reads.
- All cogs receive config via `self.bot.config` — no module-level env reads.
**Depends on:** Phase 2 (clean dep base) — not strictly required but clearer.
**Checkpoint:**
- `grep -rn "os.getenv\|os.environ" bot/` returns matches only in `bot/config/config.py`.
- `grep -rn "from bot.config.settings\|from .settings\|from config.settings" bot/` returns zero matches.
- Bot starts; every cog loads; feature flags toggle via env as before.
- Pyright `strict` on `bot/config/` passes.

### Phase 4: Async Correctness (DB + HTTP)
**Goal:** Zero blocking I/O in async paths. DB calls go through an async pool; MTG uses aiohttp; forex/ipinfo wrapped in `to_thread`. Bot owns one shared aiohttp session.
**Files:**
- Modify: `pyproject.toml` (swap `psycopg2` → `psycopg[binary]`, add `psycopg_pool`; remove `requests` from runtime deps if unused after MTG port).
- Modify: `bot/core/bot.py` (replace `db_conn` with `db_pool: AsyncConnectionPool`; open in `setup_hook`, close in `close()`; introduce `self.http_session: aiohttp.ClientSession`).
- Modify: `bot/cogs/ModLog.py` (`async with self.bot.db_pool.connection() as conn: async with conn.cursor() as cur: ...` pattern across [ModLog.py:27](../../bot/cogs/ModLog.py#L27), [ModLog.py:204](../../bot/cogs/ModLog.py#L204), and the rest).
- Modify: `bot/cogs/Database.py` (same pattern; the owner-SQL command at [Database.py:267](../../bot/cogs/Database.py#L267) needs the most care).
- Modify: `bot/cogs/Mtg.py` (replace `requests.get` with `await self.bot.http_session.get(...)`; remove `requests` import).
- Modify: `bot/cogs/Utility.py` (wrap `BtcConverter.get_latest_price()` and `ipinfo.getDetails()` in `asyncio.to_thread`).
- Modify: `bot/cogs/BoardGames.py`, `bot/cogs/Spotify.py`, `bot/utils/boardgames.py` (consume `bot.http_session` instead of opening per-call sessions).
- Modify: `bot/core/events.py` (any DB-reading event hooks switch to async pool API).
- Modify: `docs/modlog.md`, `docs/events.md` (note the async-pool API).
**Interfaces:**
- `DarkBot.db_pool: psycopg_pool.AsyncConnectionPool` replaces `DarkBot.db_conn`.
- `DarkBot.http_session: aiohttp.ClientSession` (created in `setup_hook`).
- DB usage contract: `async with bot.db_pool.connection() as conn: async with conn.cursor() as cur: ...`.
- HTTP usage contract: `await bot.http_session.get(url, ...)`; per-call sessions only in tests.
**Depends on:** Phase 3 (DB DSN + Redis URL come from `Config`).
**Checkpoint:**
- `grep -rn "psycopg2\|import requests" bot/` returns zero matches.
- `grep -rn "aiohttp.ClientSession()" bot/cogs bot/utils` returns zero matches (only `bot/core/bot.py` instantiates one).
- Bot starts, runs `!cases`, `!card <name>`, `!btc`, `!ipinfo <ip>`, `!bgg <user>`, `!sp <query>` — all return without `RuntimeWarning: coroutine ... was never awaited` and without blocking other commands during the call.
- Concurrent stress: trigger two DB-reading commands simultaneously; both complete without serializing.

### Phase 5: Error Handling + Resource Cleanup
**Goal:** No bare `except:`. Cogs raise typed `DarkBotException` subclasses where appropriate. Wavelink cleanup has a single owner. `bot/utils/__init__.py` exists. Stray pyc artifact removed.
**Files:**
- Modify: [bot/core/events.py:260](../../bot/core/events.py#L260) (replace bare `except:` with specific catch + `logger.exception`).
- Modify: [bot/cogs/Moderation.py:203](../../bot/cogs/Moderation.py#L203) (same).
- Modify: [bot/cogs/Chatgpt.py:65](../../bot/cogs/Chatgpt.py#L65), [bot/cogs/Database.py:51](../../bot/cogs/Database.py#L51) (narrow broad `except Exception:` to specific exceptions; keep one outer guard if user-facing render is required, with `logger.exception`).
- Modify: [bot/core/bot.py:301](../../bot/core/bot.py#L301) **or** [bot/cogs/Music.py:60](../../bot/cogs/Music.py#L60) — pick one owner; remove the other. Recommend keeping `cog_unload` in Music since it's lifecycle-scoped to the cog.
- Modify: [bot/core/exceptions.py](../../bot/core/exceptions.py) (audit for any subclass that should be raised at the new error sites).
- Create: `bot/utils/__init__.py`.
- Delete: any committed `tests/__pycache__/*.pyc` files.
- Modify: `.gitignore` if missing `__pycache__/` patterns.
**Interfaces:**
- Error-handling contract: cogs raise `DarkBotException` subclasses; `EventManager.on_command_error` is the single render point.
- Logging contract: stack-trace-worthy paths use `logger.exception`; user-visible errors use `logger.error` only when intentional.
- Wavelink shutdown contract: owned by `Music.cog_unload` only.
**Depends on:** Phase 4 (async refactor lands first; some error sites disappear or move).
**Checkpoint:**
- `grep -rn "except:" bot/` returns zero matches.
- `grep -rnE "except Exception(\s*as\s+\w+)?:" bot/` only flags the central `EventManager.on_command_error`.
- Pyright still passes; ruff still passes.
- Bot starts; `!play`, `!stop` cycle works; reload via `!reload Music` works without dangling Wavelink connections.

### Phase 6: Test Harness
**Goal:** Reusable test infrastructure exists; one new async cog test demonstrates the pattern; CI-runnable.
**Files:**
- Create: `tests/conftest.py` (fixtures: `bot` (in-memory DarkBot stub), `mock_db_pool`, `mock_redis`, `mock_http_session` via `aioresponses`, `caplog`).
- Create: one new test file demonstrating an async cog command test (e.g., `tests/test_modlog.py` or `tests/test_mtg.py` — pick the one with the simplest dependency surface, likely MTG after Phase 4).
- Modify: `pyproject.toml` (`[project.optional-dependencies.dev]` includes `pytest`, `pytest-asyncio`, `aioresponses`, `pytest-mock` if not already added in Phase 1).
- Modify: `pyproject.toml` `[tool.pytest.ini_options]` (asyncio_mode, testpaths).
- Modify: `docs/testing.md` (document fixture inventory and the example test pattern).
- Modify: `CLAUDE.md` (update Testing section if fixture conventions change).
**Interfaces:**
- Fixture contract: `bot`, `mock_db_pool`, `mock_redis`, `mock_http_session` available to every test.
- `pytest-asyncio` mode = `auto` (or `strict` — pick in plan phase, document either way).
- One example test serves as the template for future cog tests.
**Depends on:** Phase 4 (mocks need to model the async pool + shared http session).
**Checkpoint:**
- `pytest` runs both the original BGG test and the new example test, exits 0.
- New fixtures importable from `conftest.py`; example test demonstrates each.
- `pyright` clean on the new test code.

## Rollback

Each phase is one PR. Rollback = `git revert <phase-PR-merge-commit>`. Phases are ordered so that reverting any single later phase does not break earlier ones (e.g., reverting Phase 6 doesn't break the async pool from Phase 4).

## File-Disjoint Check

**Phases cannot run in parallel worktrees.** Multiple phases touch the same files:

- `pyproject.toml` is touched by Phases 1, 2, 4, and 6.
- `CLAUDE.md` is touched by Phases 2, 3, and 6.
- `bot/core/bot.py` is touched by Phases 3, 4, and 5.
- `bot/cogs/*.py` (Chatgpt, Music, Spotify, Utility, ModLog, Database, Moderation, BoardGames) are touched by Phases 3, 4, and 5.
- `bot/utils/boardgames.py` is touched by Phases 3 and 4.

Sequential execution is the only safe option. The phase order respects causal dependencies (tooling first, deps before config, config before async, async before error refactor, infrastructure before tests).
