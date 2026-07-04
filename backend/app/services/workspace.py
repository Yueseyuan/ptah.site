"""Per-run workspace directory — agents write project files here."""
import io
import zipfile
from pathlib import Path
from typing import Any


def _apex_workspaces() -> Path:
    root = Path.home() / ".apex" / "workspaces"
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_workspace_path(run_id: int | str) -> Path:
    return _apex_workspaces() / str(run_id)


async def create_workspace(run_id: int | str) -> Path:
    path = get_workspace_path(run_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe(workspace: Path, relative: str) -> Path:
    """Resolve relative path within workspace root; raise on traversal."""
    target = (workspace / relative).resolve()
    root = workspace.resolve()
    if not str(target).startswith(str(root)):
        raise ValueError(f"Path traversal blocked: {relative!r}")
    return target


def ws_write_file(workspace: Path, path: str, content: str) -> str:
    target = _safe(workspace, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Written: {path} ({len(content.encode())} bytes)"


def ws_read_file(workspace: Path, path: str) -> str:
    target = _safe(workspace, path)
    if not target.exists():
        return f"Error: not found: {path}"
    return target.read_text(encoding="utf-8")


def ws_list_files(workspace: Path, directory: str = "") -> str:
    if directory:
        target = _safe(workspace, directory)
    else:
        target = workspace
    if not target.exists():
        return f"Directory not found: {directory or '/'}"
    lines = []
    for f in sorted(target.rglob("*")):
        if f.is_file():
            rel = f.relative_to(workspace)
            lines.append(f"{rel}  ({f.stat().st_size} B)")
    return "\n".join(lines) if lines else "Workspace is empty."


def ws_create_directory(workspace: Path, path: str) -> str:
    target = _safe(workspace, path)
    target.mkdir(parents=True, exist_ok=True)
    return f"Directory created: {path}"


def ws_list_as_dicts(workspace: Path) -> list[dict[str, Any]]:
    if not workspace.exists():
        return []
    result = []
    for f in sorted(workspace.rglob("*")):
        if f.is_file():
            result.append({"path": str(f.relative_to(workspace)), "size": f.stat().st_size})
    return result


def ws_zip(workspace: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(workspace.rglob("*")):
            if f.is_file():
                zf.write(f, f.relative_to(workspace))
    return buf.getvalue()
