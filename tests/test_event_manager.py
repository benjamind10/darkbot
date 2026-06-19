import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bot"))
sys.modules.setdefault("psutil", ModuleType("psutil"))
sys.modules.setdefault("distro", ModuleType("distro"))

events_spec = importlib.util.spec_from_file_location("test_event_manager_module", ROOT / "bot/core/events.py")
events_module = importlib.util.module_from_spec(events_spec)
assert events_spec is not None and events_spec.loader is not None
events_spec.loader.exec_module(events_module)
EventManager = events_module.EventManager


@pytest.mark.asyncio
async def test_dispatch_event_runs_handlers_and_increments_stats(bot):
    manager = EventManager(bot)
    handler = AsyncMock()
    manager.register_event("custom", handler)

    await manager.dispatch_event("custom", 1, key="value")

    handler.assert_awaited_once_with(1, key="value")
    assert manager.get_event_stats()["custom"] == 1


@pytest.mark.asyncio
async def test_dispatch_event_isolates_handler_failure(bot):
    manager = EventManager(bot)
    failing = AsyncMock(side_effect=RuntimeError("boom"))
    succeeding = AsyncMock()
    manager.register_event("custom", failing)
    manager.register_event("custom", succeeding)

    await manager.dispatch_event("custom")

    succeeding.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_cleanup_clears_registered_events(bot):
    manager = EventManager(bot)

    await manager.cleanup()

    assert manager.get_registered_events() == []


@pytest.mark.asyncio
async def test_on_message_processes_non_bot_messages(bot):
    bot.stats = {"messages_seen": 0, "command_count": 0, "errors": 0}
    bot.process_commands = AsyncMock()
    bot.redis_manager.redis = None
    manager = EventManager(bot)
    message = SimpleNamespace(author=SimpleNamespace(bot=False))

    await manager.on_message(message)

    assert bot.stats["messages_seen"] == 1
    bot.process_commands.assert_awaited_once_with(message)
