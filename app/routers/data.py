from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import auth
from ..database import get_session
from ..models import AttendanceRecord, Event, RosterMember
from ..schemas import AttendanceRecordOut, EventOut, RosterMemberOut


router = APIRouter(prefix="/overlay", tags=["overlay-data"])


@router.get("/events", response_model=List[EventOut])
async def list_events(
    session: AsyncSession = Depends(get_session),
    _: auth.AuthenticatedUser = Depends(auth.get_current_user),
):
    result = await session.execute(select(Event).order_by(Event.start_at.asc()))
    return result.scalars().all()


@router.get("/roster", response_model=List[RosterMemberOut])
async def list_roster(
    session: AsyncSession = Depends(get_session),
    _: auth.AuthenticatedUser = Depends(auth.get_current_user),
):
    result = await session.execute(select(RosterMember).order_by(RosterMember.name.asc()))
    return result.scalars().all()


@router.get("/attendance", response_model=List[AttendanceRecordOut])
async def list_attendance(
    session: AsyncSession = Depends(get_session),
    _: auth.AuthenticatedUser = Depends(auth.get_current_user),
):
    result = await session.execute(select(AttendanceRecord).order_by(AttendanceRecord.event_date.desc()))
    return result.scalars().all()

