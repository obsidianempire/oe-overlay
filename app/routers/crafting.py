import datetime as dt
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import auth
from ..database import get_session
from ..models import CraftAssignment, CraftRequest
from ..schemas import (
    CraftAssignmentCreate,
    CraftAssignmentOut,
    CraftRequestCreate,
    CraftRequestOut,
)


router = APIRouter(prefix="/crafting", tags=["crafting"])


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


@router.post("/requests", response_model=CraftRequestOut, status_code=status.HTTP_201_CREATED)
async def create_request(
    payload: CraftRequestCreate,
    session: AsyncSession = Depends(get_session),
    user: auth.AuthenticatedUser = Depends(auth.get_current_user),
) -> CraftRequestOut:
    request = CraftRequest(
        requester_id=user.id,
        requester_name=f"{user.username}#{user.discriminator}",
        item_name=payload.item_name.strip(),
        quantity=payload.quantity,
        notes=(payload.notes or "").strip() or None,
        status="open",
    )
    session.add(request)
    await session.flush()
    await session.refresh(request)
    return CraftRequestOut.model_validate(request, from_attributes=True)


@router.get("/requests", response_model=List[CraftRequestOut])
async def list_requests(
    session: AsyncSession = Depends(get_session),
    _: auth.AuthenticatedUser = Depends(auth.get_current_user),
) -> List[CraftRequestOut]:
    stmt = (
        select(CraftRequest)
        .options(selectinload(CraftRequest.assignment))
        .order_by(CraftRequest.status.asc(), CraftRequest.created_at.desc())
    )
    result = await session.execute(stmt)
    records = result.unique().scalars().all()
    return [CraftRequestOut.model_validate(r, from_attributes=True) for r in records]


@router.get("/requests/mine", response_model=List[CraftRequestOut])
async def list_my_requests(
    session: AsyncSession = Depends(get_session),
    user: auth.AuthenticatedUser = Depends(auth.get_current_user),
) -> List[CraftRequestOut]:
    stmt = select(CraftRequest).options(selectinload(CraftRequest.assignment)).order_by(CraftRequest.updated_at.desc())
    result = await session.execute(stmt)
    records = [
        r for r in result.unique().scalars().all()
        if r.requester_id == user.id or (r.assignment is not None and r.assignment.crafter_id == user.id)
    ]
    return [CraftRequestOut.model_validate(r, from_attributes=True) for r in records]


@router.post("/requests/{request_id}/accept", response_model=CraftRequestOut)
async def accept_request(
    request_id: int,
    payload: CraftAssignmentCreate,
    session: AsyncSession = Depends(get_session),
    user: auth.AuthenticatedUser = Depends(auth.get_current_user),
) -> CraftRequestOut:
    stmt = (
        select(CraftRequest)
        .where(CraftRequest.id == request_id)
        .options(selectinload(CraftRequest.assignment))
        .with_for_update()
    )
    result = await session.execute(stmt)
    craft_request = result.unique().scalars().first()
    if not craft_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
    if craft_request.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request already claimed.")

    if not payload.location.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location is required.")

    assignment = CraftAssignment(
        request=craft_request,
        crafter_id=user.id,
        crafter_name=f"{user.username}#{user.discriminator}",
        meet_at=payload.meet_at,
        location=payload.location.strip(),
        estimated_completion=payload.estimated_completion,
        status="accepted",
    )
    craft_request.status = "accepted"
    session.add(assignment)
    await session.flush()
    await session.refresh(craft_request)
    return CraftRequestOut.model_validate(craft_request, from_attributes=True)


@router.post("/requests/{request_id}/complete", response_model=CraftRequestOut)
async def complete_request(
    request_id: int,
    session: AsyncSession = Depends(get_session),
    user: auth.AuthenticatedUser = Depends(auth.get_current_user),
) -> CraftRequestOut:
    craft_request = await _get_request_or_404(session, request_id)
    if not craft_request.assignment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request has not been accepted yet.")
    if craft_request.assignment.crafter_id != user.id and craft_request.requester_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted to complete this request.")

    craft_request.status = "completed"
    craft_request.assignment.status = "fulfilled"
    craft_request.assignment.estimated_completion = craft_request.assignment.estimated_completion or _now()
    await session.flush()
    await session.refresh(craft_request)
    return CraftRequestOut.model_validate(craft_request, from_attributes=True)


@router.post("/requests/{request_id}/cancel", response_model=CraftRequestOut)
async def cancel_request(
    request_id: int,
    session: AsyncSession = Depends(get_session),
    user: auth.AuthenticatedUser = Depends(auth.get_current_user),
) -> CraftRequestOut:
    craft_request = await _get_request_or_404(session, request_id)
    authorised = {craft_request.requester_id}
    if craft_request.assignment:
        authorised.add(craft_request.assignment.crafter_id)
    if user.id not in authorised:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted to cancel this request.")

    craft_request.status = "cancelled"
    if craft_request.assignment:
        craft_request.assignment.status = "cancelled"
    await session.flush()
    await session.refresh(craft_request)
    return CraftRequestOut.model_validate(craft_request, from_attributes=True)


async def _get_request_or_404(session: AsyncSession, request_id: int) -> CraftRequest:
    stmt = (
        select(CraftRequest)
        .where(CraftRequest.id == request_id)
        .options(selectinload(CraftRequest.assignment))
    )
    result = await session.execute(stmt)
    craft_request = result.scalars().first()
    if not craft_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found.")
    return craft_request

