"""
Agent SDK Experiment: Hooks, Subagents, and Custom Tools

Run with:
    env -u CLAUDECODE python experiments/agent_demo.py [demo]

Demos:
    tools       -- Custom tools via external MCP stdio server (cog_tools_server.py)
    hooks       -- PostToolUse/PreToolUse callbacks on built-in Agent SDK tools
    subagents   -- Specialized child agents via AgentDefinition + Task tool
    all         -- Run all demos in sequence (default)

Notes:
    The Agent SDK's in-process MCP server (create_sdk_mcp_server) requires
    a newer claude CLI. Custom tools are served via an external MCP stdio
    process (experiments/cog_tools_server.py) instead.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

BOT_ROOT = Path(__file__).parent.parent / "bot"
AUDIT_LOG = Path(__file__).parent / "audit.log"
COG_SERVER = str(Path(__file__).parent / "cog_tools_server.py")


# ===========================================================================
# Demo 1: Custom Tools via external MCP stdio server
# ===========================================================================
# cog_tools_server.py implements list_cogs and count_lines using the MCP
# stdio protocol. The Agent SDK launches it as a subprocess and routes tool
# calls through it — no API key needed, auth goes through the claude CLI.

async def demo_tools() -> None:
    print("\n" + "=" * 60)
    print("DEMO 1: Custom tools — external MCP stdio server")
    print("=" * 60)

    from claude_agent_sdk import ClaudeAgentOptions, query

    try:
        async for message in query(
            prompt=(
                "List all cogs in the bot, then count lines in "
                "Moderation.py and Music.py. Summarize the results."
            ),
            options=ClaudeAgentOptions(
                cwd=str(BOT_ROOT.parent),
                mcp_servers={
                    "cog-tools": {
                        "command": sys.executable,
                        "args": [COG_SERVER],
                    }
                },
                allowed_tools=["list_cogs", "count_lines"],
            ),
        ):
            if isinstance(message, ResultMessage):
                print(f"\nResult:\n{message.result}")
    except Exception as e:
        print(f"[non-fatal SDK error, result already printed]: {type(e).__name__}: {e}")


# ===========================================================================
# Demo 2: Hooks — Agent SDK with built-in tools
# ===========================================================================
# Hooks attach callbacks to agent lifecycle events.
# Here we hook PostToolUse (audit log) and PreToolUse (block Bash).

from claude_agent_sdk import (  # noqa: E402
    AgentDefinition,
    ClaudeAgentOptions,
    HookContext,
    HookMatcher,
    PostToolUseHookInput,
    PreToolUseHookInput,
    ResultMessage,
    query,
)


async def log_tool_use(
    hook_input: PostToolUseHookInput,
    _tool_use_id: str | None,
    _context: HookContext,
) -> dict:
    """PostToolUse: append each tool call to experiments/audit.log."""
    tool_name = hook_input.get("tool_name", "unknown")
    tool_input = hook_input.get("tool_input", {})
    timestamp = datetime.now().isoformat(timespec="seconds")
    AUDIT_LOG.parent.mkdir(exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(f"[{timestamp}] {tool_name}({tool_input})\n")
    print(f"  [audit hook] logged: {tool_name}")
    return {}


async def block_bash(
    _hook_input: PreToolUseHookInput,
    _tool_use_id: str | None,
    _context: HookContext,
) -> dict:
    """PreToolUse: block Bash tool calls."""
    print("  [block hook] Bash call blocked by PreToolUse hook!")
    return {"decision": "block", "reason": "Bash is disabled in this demo."}


async def demo_hooks() -> None:
    print("\n" + "=" * 60)
    print("DEMO 2: Hooks (PostToolUse audit log + PreToolUse Bash block)")
    print("=" * 60)

    try:
        async for message in query(
            prompt=(
                "Use Glob to find all .py files in bot/cogs/, "
                "then Read one of them and tell me what it does. "
                "Do not use Bash."
            ),
            options=ClaudeAgentOptions(
                cwd=str(BOT_ROOT.parent),
                allowed_tools=["Glob", "Read"],
                hooks={
                    "PostToolUse": [
                        HookMatcher(matcher="Glob|Read", hooks=[log_tool_use])
                    ],
                    "PreToolUse": [
                        HookMatcher(matcher="Bash", hooks=[block_bash])
                    ],
                },
            ),
        ):
            if isinstance(message, ResultMessage):
                print(f"\nResult:\n{message.result}")
    except Exception as e:
        # SDK 0.1.39 raises MessageParseError on unknown CLI events (rate_limit_event)
        # from CLI 2.1.50 — non-fatal if the result was already printed above.
        print(f"[non-fatal SDK error, result already printed]: {type(e).__name__}: {e}")

    if AUDIT_LOG.exists():
        print(f"\nAudit log ({AUDIT_LOG.name}):")
        print(AUDIT_LOG.read_text())


# ===========================================================================
# Demo 3: Subagents
# ===========================================================================
# The parent agent spawns a specialised child agent using the Task tool.
# Each subagent has its own description (for routing), prompt, and tools.

async def demo_subagents() -> None:
    print("\n" + "=" * 60)
    print("DEMO 3: Subagents (parent spawns a specialised child agent)")
    print("=" * 60)

    try:
        async for message in query(
            prompt=(
                "Use the cog-analyst subagent to find the largest and "
                "smallest cog by line count in bot/cogs/."
            ),
            options=ClaudeAgentOptions(
                cwd=str(BOT_ROOT.parent),
                allowed_tools=["Task", "Glob", "Read", "Grep"],
                agents={
                    "cog-analyst": AgentDefinition(
                        description=(
                            "Analyses DarkBot cog file sizes. Use when you "
                            "need to compare line counts across cogs."
                        ),
                        prompt=(
                            "You are a code analyst for a Discord bot. "
                            "Use Glob to find all .py files in bot/cogs/, "
                            "then use Bash or Grep to count lines in each. "
                            "Return a sorted summary (largest first) with counts."
                        ),
                        tools=["Glob", "Read", "Grep", "Bash"],
                    )
                },
            ),
        ):
            if isinstance(message, ResultMessage):
                print(f"\nResult:\n{message.result}")
    except Exception as e:
        print(f"[non-fatal SDK error, result already printed]: {type(e).__name__}: {e}")


# ===========================================================================
# Entrypoint
# ===========================================================================

async def main() -> None:
    # Guard: running inside a Claude Code session breaks the Agent SDK
    if os.environ.get("CLAUDECODE"):
        print("ERROR: Unset CLAUDECODE before running:")
        print("  env -u CLAUDECODE python experiments/agent_demo.py")
        sys.exit(1)

    demo = sys.argv[1] if len(sys.argv) > 1 else "all"

    match demo:
        case "tools":
            await demo_tools()
        case "hooks":
            await demo_hooks()
        case "subagents":
            await demo_subagents()
        case "all":
            await demo_tools()
            await demo_hooks()
            await demo_subagents()
        case _:
            print(f"Unknown demo: {demo!r}")
            print("Usage: env -u CLAUDECODE python experiments/agent_demo.py [tools|hooks|subagents|all]")


if __name__ == "__main__":
    asyncio.run(main())
