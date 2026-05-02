---
date: 2026-05-02
ticket: thoughts/tickets/2026-05-02_maint-python-best-practices-sweep.md
---

# Questions: Whole-App Python Best-Practices Sweep

## Context
Perform a recommendation-oriented maintenance sweep across the entire DarkBot codebase (12 cogs, core/, config/, utils/, tests/) covering Python idioms, reliability, performance, architecture, testing, tooling, and DX, with Ruff as the lint/format anchor. The output of the downstream phases should be a prioritized, evidence-backed improvement plan distinguishing quick wins from larger refactors. This questions doc identifies what we don't yet know about the codebase so research can target the right files instead of forming opinions early.

## Technical Unknowns

### Q1: Tooling baseline — where should Ruff/pytest/typing config live, and what already exists?
**Unknown:** The repo has no `pyproject.toml`, `ruff.toml`, `setup.cfg`, `pytest.ini`, or `.pre-commit-config.yaml`. A `pyrightconfig.json` exists at the root but its strictness, included paths, and Python version target are unverified. We don't know whether the team prefers a single `pyproject.toml` or split config files, nor what Python version Ruff/pyright should target (CLAUDE.md says Python 3.10 in Docker).
**Why it matters:** Ruff is the explicit anchor for the sweep, so config placement and rule-set selection determine what "best practices" actually mean for this repo. Choosing `pyproject.toml` vs. `ruff.toml` affects whether pytest, coverage, and Ruff share one file. Python target version affects which lint rules and modernization fixes (e.g. `UP` rules, `PEP 604` unions) are applicable.
**Options:**
- A) Adopt a single `pyproject.toml` covering Ruff + pytest + project metadata (and align pyright there).
- B) Keep tools file-isolated (`ruff.toml`, `pytest.ini`, keep `pyrightconfig.json`).
- C) Defer config decisions; recommend a baseline rule set only.
**Research needed:** Read `pyrightconfig.json` to capture current strictness/paths/python version. Inspect `Dockerfile` for the actual installed Python version. Confirm no hidden `[tool.*]` sections exist anywhere (grep all .toml/.cfg/.ini files). Note that `bot/requirements.txt` lives under `bot/`, not root — this affects where a `pyproject.toml` should sit.

### Q2: `bot/requirements.txt` corruption — what is the real state and how do we recover ground truth?
**Unknown:** CLAUDE.md states `bot/requirements.txt` "has corrupted encoding (spaces between characters)" and the Dockerfile installs additional packages explicitly to compensate. We don't know which packages/versions are authoritative, whether the file is UTF-16 mis-saved, or how dev-only deps (pytest, aioresponses, pyright) are currently installed.
**Why it matters:** A reliable dependency manifest is a prerequisite for almost every other recommendation (pinning, security audit, dev/runtime split, reproducible installs, lockfile adoption). Without resolving this, Ruff/pytest/pre-commit recommendations will float against an unknown environment.
**Options:**
- A) Re-encode `requirements.txt` as UTF-8 in place and split into `requirements.txt` + `requirements-dev.txt`.
- B) Migrate to `pyproject.toml` with `[project.dependencies]` and `[project.optional-dependencies.dev]`, drop the legacy file.
- C) Adopt `uv` or `poetry` with a lockfile.
**Research needed:** Read `bot/requirements.txt` raw bytes (file/encoding/hexdump if needed) to confirm the corruption type. Read `Dockerfile` to enumerate the explicitly-installed compensating packages. Cross-check `tests/conftest.py` and test imports for hidden dev-only deps. Check `docker-compose.yml` for any pip install steps.

### Q3: Async/sync correctness across cogs — where are blocking calls hidden in async handlers?
**Unknown:** All 12 cogs are async (discord.py 2.3.2 hybrid commands), but we don't know which ones make blocking calls (sync `requests`, `time.sleep`, sync DB drivers, sync file I/O, CPU-heavy parsing) inside coroutines. Likely suspects based on feature names: `BoardGames` (BGG XML), `Mtg` (Scryfall), `Spotify`, `Utility` (crypto/weather/translation), `Chatgpt`, `Database` (raw SQL).
**Why it matters:** Blocking calls inside async event loops is the single biggest reliability/performance hazard for a Discord bot — one slow HTTP call freezes every other command. This is a top-priority finding category for the sweep.
**Options:**
- A) Audit by import (`requests`, `urllib`, `psycopg2` sync, `redis` sync client, `time.sleep`, `open()` in coroutine).
- B) Audit by call site (search for `await` density per cog and flag low-density coroutines).
- C) Both, in that order.
**Research needed:** Grep across `bot/cogs/*.py` and `bot/utils/*.py` for: `import requests`, `import urllib`, `time.sleep`, `psycopg2`, `redis.Redis(` (vs `redis.asyncio`), `open(` inside `async def`. Identify which HTTP client each cog uses (aiohttp vs requests). Confirm DB driver in `bot/utils/redis_manager.py` and `bot/cogs/Database.py`.

### Q4: Error handling and logging consistency — what patterns exist, and where do they diverge?
**Unknown:** We don't know the current error-handling style: bare `except:`, `except Exception:`, custom exceptions in `bot/core/exceptions.py`, command error handlers, or per-cog `try/except`. Logging style is also unknown — direct `print`, `logging.getLogger(__name__)`, the `bot/utils/logger.py` helper, or mixed.
**Why it matters:** The ticket explicitly calls out "overly broad exception handling" and "logging" as concerns. A consistent pattern recommendation only works if we know the current diversity. Discord.py also has its own command-error dispatch hooks that may or may not be wired up.
**Options:**
- A) Standardize on `bot/utils/logger.py` + structured per-cog loggers + a global `on_command_error` handler.
- B) Per-cog error handlers leveraging discord.py's `cog_command_error`.
- C) Rely on framework defaults; only flag the most egregious cases.
**Research needed:** Grep for `except`, `except Exception`, `except:`, `print(`, `logging.`, `logger.` across all `bot/**/*.py`. Check whether `bot/core/bot.py` registers `on_command_error` / `on_error`. Read `bot/utils/logger.py` to see what's exported. Catalog usage of `bot/core/exceptions.py` (which symbols are imported where).

### Q5: Test coverage and reliability gaps — which cogs/utilities have no tests, and what fixtures support the existing ones?
**Unknown:** Six test files exist (`test_boardgames`, `test_chatgpt`, `test_events`, `test_information`, `test_moderation`, `test_mtg`). Six cogs have no test files: `Database`, `ModLog`, `Music`, `Owner`, `Spotify`, `Utility`. We don't know what the existing tests actually exercise (happy path? mocking style?), what `conftest.py` provides, or whether async fixtures and aioresponses are set up consistently.
**Why it matters:** The ticket says "recommend coverage or fixture improvements where risk is high." High-risk untested cogs are `ModLog` (touches event pipeline + DB), `Music` (Wavelink/Lavalink lifecycle, voice state), and `Database` (raw SQL execution). Fixture quality determines how easy adding coverage will be.
**Options:**
- A) Recommend coverage targets per cog by risk tier.
- B) Recommend a unified fixture set in `conftest.py` first, then coverage.
- C) Recommend a coverage tool (`pytest-cov`) and a baseline before prioritizing.
**Research needed:** Read `tests/conftest.py` for shared fixtures and bot mocks. Skim each `tests/test_*.py` to classify test depth (smoke vs. behavior). Confirm whether `pytest-asyncio` mode is configured (auto vs strict) — likely lives in `pyproject.toml` which doesn't exist, so probably implicit. Check whether `aioresponses` is used uniformly.

### Q6: Architecture hygiene — missing `__init__.py`, import-time side effects, and `helpers` vs `utils` split
**Unknown:** No `__init__.py` files exist anywhere in `bot/` despite multiple subpackages — discord.py cogs are loaded by string path so this works, but it affects type checking, import resolution, and namespace packages. We also don't know whether `bot/main.py`, `bot/core/bot.py`, or `bot/config/settings.py` execute side effects at import time (network calls, env reads, logger config). Finally, `bot/utils/` has paired files (`boardgame_helpers.py` + `boardgame_utils.py`, `spotify_helpers.py` + `spotify_utils.py`) — the distinction is unverified.
**Why it matters:** Missing `__init__.py` files affect Ruff/pyright module discovery and may cause subtle test-collection or import-order issues. Side effects at import time are a known reliability hazard the ticket flags. Duplicate-suffix files are a maintainability smell that may be a real separation or accidental drift.
**Options:**
- A) Add `__init__.py` to all subpackages; recommend collapsing helpers/utils pairs after diff review.
- B) Adopt namespace packages (PEP 420) explicitly and keep the structure.
- C) Defer until import-time side effects are mapped.
**Research needed:** Read top of `bot/main.py`, `bot/core/bot.py`, `bot/core/events.py`, `bot/config/settings.py`, `bot/config/config.py`, `bot/utils/logger.py` for module-level executable code (logger config, env reads, network connections). Diff `boardgame_helpers.py` vs `boardgame_utils.py` and `spotify_helpers.py` vs `spotify_utils.py` to see if they differ in role or duplicate logic.

### Q7: Configuration loading — does the three-level fallback duplicate logic across cogs?
**Unknown:** CLAUDE.md describes a typed dataclass `Config` in `bot/config/config.py` with env→file→default fallback, plus `bot/config/settings.py` for constants and feature flags. We don't know whether cogs consistently consume the typed `Config` object, whether they re-read `os.environ` directly (bypassing the dataclass), or whether feature flags are checked correctly at cog load.
**Why it matters:** Inconsistent config consumption is a common source of "works locally, breaks in Docker" bugs and undermines the testability the ticket calls out. If every cog reads env vars independently, the typed config layer is essentially decorative.
**Options:**
- A) Mandate cogs receive `Config` via `bot.config` and never call `os.getenv` directly.
- B) Allow direct `settings.py` imports for feature flags but route runtime values through `Config`.
- C) Refactor to a Pydantic-settings-style loader.
**Research needed:** Grep for `os.getenv`, `os.environ`, `getenv` across `bot/cogs/*.py` and `bot/utils/*.py`. Grep for `from bot.config` and `from config` imports. Identify which cogs check feature flags (e.g. `MUSIC_ENABLED`) and how. Read `bot/config/config.py` and `bot/config/settings.py` once research begins.

### Q8: Resource lifecycle — startup/shutdown correctness for Redis, Postgres, Lavalink
**Unknown:** `setup_hook()` initializes Redis, loads cogs, connects to PostgreSQL, syncs slash commands. We don't know whether DB pools, Redis client, aiohttp sessions, and Wavelink node connections are properly closed on shutdown — discord.py's `close()` hook needs explicit teardown for these. Redis is described as "optional" with graceful fallback; the failure mode is unverified.
**Why it matters:** Resource leaks on bot restart manifest as connection-pool exhaustion, hung containers, or zombie voice sessions. The ticket explicitly lists "startup/shutdown behavior" and "resource cleanup" in scope.
**Options:**
- A) Audit `bot/core/bot.py` for `close()` / `cog_unload` symmetry; recommend explicit teardown.
- B) Recommend an `AsyncExitStack` / context-managed startup pattern.
- C) Add a smoke test that runs `setup_hook` + `close` and asserts no leaked tasks.
**Research needed:** Read `bot/core/bot.py` `setup_hook` and any `close`/`on_shutdown`. Check `bot/utils/redis_manager.py` for connect/disconnect symmetry. Check `bot/cogs/Music.py` for Wavelink node lifecycle and `cog_unload`. Check `bot/cogs/Database.py` for connection pool management. Look for `aiohttp.ClientSession` instances and confirm they're closed.

## Human Decisions (Resolved)

1. **Python target version:** **Resolved:** Python 3.12 — plan an upgrade from the current 3.10 base. Ruff/pyright/Dockerfile should all target 3.12. Modernization rules (`UP`, `PEP 604` unions, `match` statements, etc.) are in scope.
2. **Tooling consolidation:** **Resolved:** Migrate to a single `pyproject.toml` covering Ruff + pytest + project metadata; align pyright there too.
3. **Dependency strategy:** **Resolved:** Adopt `pyproject.toml` with `[project.dependencies]` and `[project.optional-dependencies.dev]`. Retire `bot/requirements.txt`. (Lockfile choice — `uv` vs `poetry` vs none — to be decided in design phase.)
4. **Risk appetite for refactors:** **Resolved:** Deep refactor is in scope. Behavior-preserving restructuring (unified error handling, collapsing `helpers`/`utils`, `__init__.py` additions, config consolidation) is on the table alongside quick wins.
5. **Test coverage target:** **Resolved:** Aim for TDD across the whole codebase — every cog and utility module should have tests. Risk prioritization still applies for ordering, but parity is the goal.
6. **CI introduction:** **Resolved:** Recommendation-only. Mono-repo, single-developer setup; dev runs locally, prod is a DigitalOcean droplet. No GitHub Actions / hosted CI in scope. Pre-commit hooks (local) are still on the table.

## Out-of-Band Findings (already established by the locator, no research needed)

These don't need research — they are confirmed quick wins to fold into the eventual plan:

- `__pycache__/` directories and `.pyc` files are committed under `bot/cogs/`, `bot/config/`, `bot/core/`, `bot/utils/`. No `.gitignore` exists at the repo root.
- No `README.md` at repo root (only `CLAUDE.md`).
- No `.dockerignore`.
- No CI/CD pipeline (`.github/`, `.gitlab-ci.yml`, `Makefile` all absent).
- Cog files use `PascalCase.py` (`BoardGames.py`, `Chatgpt.py`) while every other Python file uses `snake_case.py` — an inconsistency to flag, though renames are higher-risk because cogs are loaded by filename.

## Research Plan

Ordered by which question unblocks the most downstream decisions:

1. **Q2 (requirements.txt corruption)** — blocks every dependency-related recommendation; cheapest to verify (one file read).
2. **Q1 (tooling baseline)** — read `pyrightconfig.json` and `Dockerfile`; sets the Python target version that all later rule-set choices depend on.
3. **Q3 (async/sync correctness)** — broad grep sweep; the ticket's highest-impact reliability category.
4. **Q6 (architecture hygiene + import-time side effects)** — needs to happen before refactor recommendations; cheap once paths are known.
5. **Q4 (error handling and logging)** — pattern catalog; informs both reliability and DX recommendations.
6. **Q7 (config consumption)** — depends on Q6 (knowing import-time behavior of `bot/config/`).
7. **Q8 (resource lifecycle)** — focused read of `bot/core/bot.py` + Music/Database/Redis lifecycle.
8. **Q5 (test coverage)** — last; informed by Q3/Q4/Q8 findings about which cogs are highest risk.
