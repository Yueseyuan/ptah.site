from datetime import timedelta, timezone, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin, get_current_user
from app.database import get_db
from app.models.approval import (
    ActionPolicy,
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
    RiskPolicy,
)
from app.models.audit import AuditEventType
from app.models.base import utcnow
from app.models.user import User
from app.schemas.approval import (
    ActionPolicyCreate,
    ActionPolicyOut,
    ApprovalRequestCreate,
    ApprovalRequestList,
    ApprovalRequestOut,
    DecideIn,
    RiskPolicyCreate,
    RiskPolicyOut,
)
from app.services.audit import log_event

DEFAULT_TIMEOUT_MINUTES = 60

router = APIRouter()


async def _get_timeout(db: AsyncSession, action_type: str, resource_type: str | None) -> int:
    result = await db.execute(
        select(ActionPolicy).where(
            ActionPolicy.action_type == action_type,
            ActionPolicy.is_active.is_(True),
        )
    )
    policy = result.scalar_one_or_none()
    return policy.timeout_minutes if policy else DEFAULT_TIMEOUT_MINUTES


async def _load_request(db: AsyncSession, request_id: int) -> ApprovalRequest:
    result = await db.execute(select(ApprovalRequest).where(ApprovalRequest.id == request_id))
    req = result.scalar_one_or_none()
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")
    return req


async def _load_decision(db: AsyncSession, request_id: int) -> ApprovalDecision | None:
    result = await db.execute(
        select(ApprovalDecision).where(ApprovalDecision.request_id == request_id)
    )
    return result.scalar_one_or_none()


async def _build_out(db: AsyncSession, req: ApprovalRequest) -> ApprovalRequestOut:
    decision = await _load_decision(db, req.id)
    out = ApprovalRequestOut.model_validate(req)
    out.decision = decision
    return out


# ---------------------------------------------------------------------------
# Approval Requests
# ---------------------------------------------------------------------------

@router.post("/request", response_model=ApprovalRequestOut, status_code=status.HTTP_201_CREATED)
async def create_request(
    body: ApprovalRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = utcnow()
    if body.level == 0:
        req = ApprovalRequest(
            level=body.level,
            status=ApprovalStatus.AUTO_APPROVED,
            requester_id=current_user.id,
            action_type=body.action_type,
            resource_type=body.resource_type,
            resource_id=body.resource_id,
            payload=body.payload,
            reason=body.reason,
            expires_at=None,
        )
    else:
        timeout = await _get_timeout(db, body.action_type, body.resource_type)
        req = ApprovalRequest(
            level=body.level,
            status=ApprovalStatus.PENDING,
            requester_id=current_user.id,
            action_type=body.action_type,
            resource_type=body.resource_type,
            resource_id=body.resource_id,
            payload=body.payload,
            reason=body.reason,
            expires_at=now.replace(tzinfo=timezone.utc) + timedelta(minutes=timeout),
        )
    db.add(req)
    await log_event(db, AuditEventType.APPROVAL, user_id=current_user.id, resource_type="approval_request")
    await db.commit()
    await db.refresh(req)
    return await _build_out(db, req)


@router.get("", response_model=ApprovalRequestList)
async def list_requests(
    req_status: ApprovalStatus | None = Query(None, alias="status"),
    level: int | None = Query(None, ge=0, le=3),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    base = select(ApprovalRequest)
    if req_status is not None:
        base = base.where(ApprovalRequest.status == req_status)
    if level is not None:
        base = base.where(ApprovalRequest.level == level)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = list(
        (await db.execute(
            base.order_by(ApprovalRequest.created_at.desc()).offset((page - 1) * limit).limit(limit)
        )).scalars().all()
    )
    items = [await _build_out(db, r) for r in rows]
    return ApprovalRequestList(items=items, total=total, page=page, limit=limit)


@router.get("/{request_id}", response_model=ApprovalRequestOut)
async def get_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = await _load_request(db, request_id)
    if req.requester_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return await _build_out(db, req)


@router.post("/{request_id}/approve", response_model=ApprovalRequestOut)
async def approve_request(
    request_id: int,
    body: DecideIn = DecideIn(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = await _load_request(db, request_id)
    _assert_decidable(req, current_user)
    req.status = ApprovalStatus.APPROVED
    decision = ApprovalDecision(
        request_id=req.id,
        verdict="approved",
        decided_by_id=current_user.id,
        note=body.note,
    )
    db.add(decision)
    await log_event(db, AuditEventType.APPROVAL, user_id=current_user.id, resource_id=str(req.id), detail={"verdict": "approved"})
    await db.commit()
    await db.refresh(req)
    return await _build_out(db, req)


@router.post("/{request_id}/reject", response_model=ApprovalRequestOut)
async def reject_request(
    request_id: int,
    body: DecideIn = DecideIn(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = await _load_request(db, request_id)
    _assert_decidable(req, current_user)
    req.status = ApprovalStatus.REJECTED
    decision = ApprovalDecision(
        request_id=req.id,
        verdict="rejected",
        decided_by_id=current_user.id,
        note=body.note,
    )
    db.add(decision)
    await log_event(db, AuditEventType.APPROVAL, user_id=current_user.id, resource_id=str(req.id), detail={"verdict": "rejected"})
    await db.commit()
    await db.refresh(req)
    return await _build_out(db, req)


def _assert_decidable(req: ApprovalRequest, actor: User) -> None:
    if req.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is already {req.status.value}",
        )
    if req.expires_at:
        exp = req.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > exp:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Request has expired")
    if req.level == 3 and not actor.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Level 3 approval requires admin",
        )


# ---------------------------------------------------------------------------
# Risk Policies (admin CRUD)
# ---------------------------------------------------------------------------

@router.post("/policies/risk", response_model=RiskPolicyOut, status_code=status.HTTP_201_CREATED)
async def create_risk_policy(
    body: RiskPolicyCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    policy = RiskPolicy(**body.model_dump(), created_by_id=admin.id)
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


@router.get("/policies/risk", response_model=list[RiskPolicyOut])
async def list_risk_policies(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    rows = (await db.execute(select(RiskPolicy).order_by(RiskPolicy.id))).scalars().all()
    return list(rows)


# ---------------------------------------------------------------------------
# Action Policies (admin CRUD)
# ---------------------------------------------------------------------------

@router.post("/policies/action", response_model=ActionPolicyOut, status_code=status.HTTP_201_CREATED)
async def create_action_policy(
    body: ActionPolicyCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    policy = ActionPolicy(**body.model_dump())
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


@router.get("/policies/action", response_model=list[ActionPolicyOut])
async def list_action_policies(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    rows = (await db.execute(select(ActionPolicy).order_by(ActionPolicy.id))).scalars().all()
    return list(rows)
