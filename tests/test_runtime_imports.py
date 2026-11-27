"""Guard against cogs importing the `bot.` package.

At runtime the bot runs from inside `bot/` (see main.py and docker-compose's
working_dir), so cogs must import `utils.*` / `core.*` / `config.*`. A
`bot.*` import resolves to the copy pip installed into the Docker image at
build time, which goes stale as soon as the mounted code changes, and
crashed production on 2026-11-27 (BoardGames failed to load).
"""

import re
from pathlib import Path

import pytest

BOT_DIR = Path(__file__).resolve().parent.parent / "bot"
RUNTIME_DIRS = ["cogs", "core", "utils", "config"]
BOT_PACKAGE_IMPORT = re.compile(r"^\s*(from\s+bot(\.|\s)|import\s+bot(\.|\s|$))", re.MULTILINE)


@pytest.mark.parametrize(
    "path",
    [p for d in RUNTIME_DIRS for p in sorted((BOT_DIR / d).rglob("*.py"))],
    ids=lambda p: str(p.relative_to(BOT_DIR)),
)
def test_runtime_modules_do_not_import_bot_package(path):
    matches = BOT_PACKAGE_IMPORT.findall(path.read_text())
    assert not matches, f"{path.relative_to(BOT_DIR)} imports the `bot.` package; use utils./core./config. instead"
