from datetime import datetime

from pydantic import BaseModel, Field

from app.models.knowledge import EdgeType, NodeType


class KnowledgeNodeCreate(BaseModel):
    title: str
    node_type: NodeType = NodeType.CONCEPT
    content: str | None = None
    source: str | None = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)


class KnowledgeNodeUpdate(BaseModel):
    title: str | None = None
    node_type: NodeType | None = None
    content: str | None = None
    source: str | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)


class KnowledgeNodeOut(BaseModel):
    id: int
    title: str
    node_type: NodeType
    content: str | None
    source: str | None
    confidence_score: float
    is_active: bool
    created_by_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeEdgeCreate(BaseModel):
    source_node_id: int
    target_node_id: int
    edge_type: EdgeType = EdgeType.RELATED_TO
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    label: str | None = None


class KnowledgeEdgeOut(BaseModel):
    id: int
    source_node_id: int
    target_node_id: int
    edge_type: EdgeType
    weight: float
    label: str | None
    created_by_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeSnapshotCreate(BaseModel):
    name: str
    description: str | None = None
    data: dict = {}


class KnowledgeSnapshotOut(BaseModel):
    id: int
    name: str
    description: str | None
    node_count: int
    edge_count: int
    data: dict
    created_by_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
