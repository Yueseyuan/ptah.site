"""Tool definitions and executor factory for agentic agent runs."""
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.services.workspace import ws_create_directory, ws_list_files, ws_read_file, ws_write_file

# Canonical tool list in Anthropic format
AGENT_TOOLS: list[dict[str, Any]] = [
    {
        "name": "write_file",
        "description": (
            "Write content to a file in the project workspace. "
            "Creates parent directories automatically. "
            "Use for ALL source files: HTML, CSS, JS/TS, Python, config, etc. "
            "Always write complete, production-ready content — never truncate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to workspace root, e.g. 'src/index.html'",
                },
                "content": {
                    "type": "string",
                    "description": "Complete file content to write",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the content of an existing file in the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path relative to workspace root",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "List all files in the workspace or a subdirectory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Subdirectory to list (omit for workspace root)",
                    "default": "",
                },
            },
        },
    },
    {
        "name": "create_directory",
        "description": "Create a directory (and any missing parents) in the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path relative to workspace root",
                },
            },
            "required": ["path"],
        },
    },
]


def anthropic_to_ollama_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Anthropic-format tools to OpenAI/Ollama function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        }
        for t in tools
    ]


OLLAMA_TOOLS = anthropic_to_ollama_tools(AGENT_TOOLS)

_TOOLS_SYSTEM_ADDENDUM = """
You have file system tools available. Use them to build the complete project:
- write_file: create any file (code, config, HTML, CSS, etc.)
- read_file: read a file you already wrote to verify or extend it
- list_files: see what you've built so far
- create_directory: create folders before writing files into them

Rules:
- Write COMPLETE files — never truncate with "..." or "// rest of code here"
- Build everything needed: entry points, configs, source files, styles, assets
- Use list_files to check progress before finishing
- After writing all files, provide a brief summary of what you built
"""


def make_tool_executor(workspace: Path) -> Callable[[str, dict[str, Any]], Awaitable[str]]:
    """Return an async callable that routes tool calls to workspace operations."""

    async def execute(name: str, args: dict[str, Any]) -> str:
        try:
            if name == "write_file":
                return ws_write_file(workspace, args["path"], args["content"])
            if name == "read_file":
                return ws_read_file(workspace, args["path"])
            if name == "list_files":
                return ws_list_files(workspace, args.get("directory", ""))
            if name == "create_directory":
                return ws_create_directory(workspace, args["path"])
            return f"Unknown tool: {name}"
        except Exception as exc:
            return f"Tool error ({name}): {exc}"

    return execute


def get_tools_system_addendum() -> str:
    return _TOOLS_SYSTEM_ADDENDUM
