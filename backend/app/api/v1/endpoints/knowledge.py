from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.knowledge import KnowledgeEdge, KnowledgeNode, KnowledgeSnapshot, NodeType
from app.models.user import User
from app.schemas.knowledge import (
    KnowledgeEdgeCreate, KnowledgeEdgeOut,
    KnowledgeNodeCreate, KnowledgeNodeOut, KnowledgeNodeUpdate,
    KnowledgeSnapshotCreate, KnowledgeSnapshotOut,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

@router.post("/nodes", response_model=KnowledgeNodeOut, status_code=status.HTTP_201_CREATED)
async def create_node(body: KnowledgeNodeCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    node = KnowledgeNode(**body.model_dump(), created_by_id=current_user.id)
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return node


@router.get("/nodes", response_model=list[KnowledgeNodeOut])
async def list_nodes(
    node_type: NodeType | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(KnowledgeNode).where(KnowledgeNode.is_active.is_(True))
    if node_type is not None:
        stmt = stmt.where(KnowledgeNode.node_type == node_type)
    stmt = stmt.order_by(KnowledgeNode.confidence_score.desc(), KnowledgeNode.id.desc())
    return list((await db.execute(stmt)).scalars().all())


@router.get("/nodes/{node_id}", response_model=KnowledgeNodeOut)
async def get_node(node_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await _load_node(db, node_id)


@router.patch("/nodes/{node_id}", response_model=KnowledgeNodeOut)
async def update_node(node_id: int, body: KnowledgeNodeUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    node = await _load_node(db, node_id)
    for f, v in body.model_dump(exclude_none=True).items():
        setattr(node, f, v)
    await db.commit()
    await db.refresh(node)
    return node


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_node(node_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    node = await _load_node(db, node_id)
    node.is_active = False
    await db.commit()


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------

@router.post("/edges", response_model=KnowledgeEdgeOut, status_code=status.HTTP_201_CREATED)
async def create_edge(body: KnowledgeEdgeCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    await _load_node(db, body.source_node_id)
    await _load_node(db, body.target_node_id)
    edge = KnowledgeEdge(**body.model_dump(), created_by_id=current_user.id)
    db.add(edge)
    await db.commit()
    await db.refresh(edge)
    return edge


@router.get("/edges", response_model=list[KnowledgeEdgeOut])
async def list_edges(
    node_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(KnowledgeEdge)
    if node_id is not None:
        stmt = stmt.where(or_(KnowledgeEdge.source_node_id == node_id, KnowledgeEdge.target_node_id == node_id))
    stmt = stmt.order_by(KnowledgeEdge.id.desc())
    return list((await db.execute(stmt)).scalars().all())


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

@router.post("/snapshots", response_model=KnowledgeSnapshotOut, status_code=status.HTTP_201_CREATED)
async def create_snapshot(body: KnowledgeSnapshotCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    node_count = (await db.execute(select(func.count()).where(KnowledgeNode.is_active.is_(True)))).scalar_one()
    edge_count = (await db.execute(select(func.count(KnowledgeEdge.id)))).scalar_one()
    snap = KnowledgeSnapshot(
        **body.model_dump(),
        node_count=node_count,
        edge_count=edge_count,
        created_by_id=current_user.id,
    )
    db.add(snap)
    await db.commit()
    await db.refresh(snap)
    return snap


@router.get("/snapshots", response_model=list[KnowledgeSnapshotOut])
async def list_snapshots(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return list((await db.execute(select(KnowledgeSnapshot).order_by(KnowledgeSnapshot.id.desc()))).scalars().all())


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@router.get("/search", response_model=list[KnowledgeNodeOut])
async def search_nodes(q: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    stmt = select(KnowledgeNode).where(
        KnowledgeNode.is_active.is_(True),
        or_(KnowledgeNode.title.ilike(f"%{q}%"), KnowledgeNode.content.ilike(f"%{q}%")),
    ).order_by(KnowledgeNode.confidence_score.desc()).limit(50)
    return list((await db.execute(stmt)).scalars().all())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load_node(db: AsyncSession, node_id: int) -> KnowledgeNode:
    node = (await db.execute(select(KnowledgeNode).where(KnowledgeNode.id == node_id))).scalar_one_or_none()
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge node not found")
    return node
