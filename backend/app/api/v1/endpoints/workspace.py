"""Workspace REST endpoints — browse and download agent-generated files."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.workspace import get_workspace_path, ws_list_as_dicts, ws_read_file, ws_zip

router = APIRouter()


@router.get("/{run_id}")
async def list_workspace_files(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[dict]:
    """List all files in a run's workspace."""
    workspace = get_workspace_path(run_id)
    if not workspace.exists():
        return []
    return ws_list_as_dicts(workspace)


@router.get("/{run_id}/file", response_class=PlainTextResponse)
async def read_workspace_file(
    run_id: int,
    path: str = Query(..., description="File path relative to workspace root"),
    _: User = Depends(get_current_user),
) -> str:
    """Read the content of a specific file in a run's workspace."""
    workspace = get_workspace_path(run_id)
    if not workspace.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    try:
        content = ws_read_file(workspace, path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if content.startswith("Error:"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=content)
    return content


@router.get("/{run_id}/download")
async def download_workspace(
    run_id: int,
    _: User = Depends(get_current_user),
) -> Response:
    """Download all workspace files as a ZIP archive."""
    workspace = get_workspace_path(run_id)
    if not workspace.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    zip_bytes = ws_zip(workspace)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=run-{run_id}-workspace.zip"},
    )
