import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import discord
import pytest
from discord import app_commands
from discord.ext import commands

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bot"))
sys.modules.setdefault("psutil", ModuleType("psutil"))
sys.modules.setdefault("distro", ModuleType("distro"))

psycopg_module = sys.modules.setdefault("psycopg", ModuleType("psycopg"))
psycopg_rows_module = sys.modules.setdefault("psycopg.rows", ModuleType("psycopg.rows"))
psycopg_rows_module.dict_row = object()
psycopg_module.rows = psycopg_rows_module

psycopg_pool_module = sys.modules.setdefault("psycopg_pool", ModuleType("psycopg_pool"))
psycopg_pool_module.AsyncConnectionPool = type("AsyncConnectionPool", (), {})
psycopg_pool_module.ConnectionPool = type("ConnectionPool", (), {})
psycopg_pool_module.AsyncConnection = SimpleNamespace


def test_discord_py_target_version():
    assert discord.__version__ == "2.6.4"


def test_discord_surface_imports():
    assert commands.Bot is not None
    assert commands.hybrid_command is not None
    assert commands.hybrid_group is not None
    assert discord.Intents.default is not None
    assert app_commands.CommandTree is not None


@pytest.mark.parametrize(
    "module_name",
    [
        "bot.core.bot",
        "bot.core.events",
        "bot.cogs.Information",
        "bot.cogs.Moderation",
        "bot.cogs.ModLog",
        "bot.cogs.Events",
        "bot.cogs.Music",
    ],
)
def test_discord_heavy_modules_import(module_name):
    assert importlib.import_module(module_name) is not None
