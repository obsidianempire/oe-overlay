import datetime as dt
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import auth
from ..config import get_settings
from ..database import get_session
from ..models import Event, EventAttendee
from ..schemas import EventCreate, EventDetail, EventOut, EventAttendeeOut


router = APIRouter(prefix="/events", tags=["events"])
settings = get_settings()


@router.get("", response_model=List[EventDetail])
async def list_events(
    session: AsyncSession = Depends(get_session),
    _: auth.AuthenticatedUser = Depends(auth.get_current_user),
) -> List[EventDetail]:
    stmt = (
        select(Event)
        .options(selectinload(Event.attendees))
        .order_by(Event.start_at.asc())
    )
    result = await session.execute(stmt)
    events = result.unique().scalars().all()
    return [EventDetail.model_validate(event, from_attributes=True) for event in events]


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: EventCreate,
    session: AsyncSession = Depends(get_session),
    user: auth.AuthenticatedUser = Depends(auth.get_current_user),
) -> EventOut:
    if not user.can_create_events:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted to create events.")

    required_roles = payload.required_role_ids or settings.discord_event_role_ids or None
    event = Event(
        title=payload.title.strip(),
        description=(payload.description or "").strip() or None,
        start_at=payload.start_at,
        timezone=payload.timezone,
        created_by=user.id,
        guild_id=str(user.guild_ids[0]) if user.guild_ids else None,
        required_role_ids=required_roles,
    )
    session.add(event)
    await session.flush()
    await session.refresh(event)
    return EventOut.model_validate(event, from_attributes=True)


@router.post("/{event_id}/join", response_model=EventDetail)
async def join_event(
    event_id: int,
    session: AsyncSession = Depends(get_session),
    user: auth.AuthenticatedUser = Depends(auth.get_current_user),
) -> EventDetail:
    event = await _get_event_or_404(session, event_id)
    _enforce_event_roles(event, user)

    attendee_exists = any(att.user_id == user.id for att in event.attendees)
    if not attendee_exists:
        attendee = EventAttendee(
            event=event,
            user_id=user.id,
            username=f"{user.username}#{user.discriminator}",
        )
        session.add(attendee)
        await session.flush()
        await session.refresh(event)
    return EventDetail.model_validate(event, from_attributes=True)


@router.post("/{event_id}/leave", response_model=EventDetail)
async def leave_event(
    event_id: int,
    session: AsyncSession = Depends(get_session),
    user: auth.AuthenticatedUser = Depends(auth.get_current_user),
) -> EventDetail:
    event = await _get_event_or_404(session, event_id)
    stmt = select(EventAttendee).where(
        and_(EventAttendee.event_id == event_id, EventAttendee.user_id == user.id)
    )
    attendee = (await session.execute(stmt)).scalars().first()
    if attendee:
        await session.delete(attendee)
        await session.flush()
        await session.refresh(event)
    return EventDetail.model_validate(event, from_attributes=True)


@router.get("/{event_id}/attendees", response_model=List[EventAttendeeOut])
async def list_attendees(
    event_id: int,
    session: AsyncSession = Depends(get_session),
    _: auth.AuthenticatedUser = Depends(auth.get_current_user),
) -> List[EventAttendeeOut]:
    stmt = select(EventAttendee).where(EventAttendee.event_id == event_id).order_by(EventAttendee.created_at.asc())
    attendees = (await session.execute(stmt)).scalars().all()
    return [EventAttendeeOut.model_validate(a, from_attributes=True) for a in attendees]


async def _get_event_or_404(session: AsyncSession, event_id: int) -> Event:
    stmt = (
        select(Event)
        .where(Event.id == event_id)
        .options(selectinload(Event.attendees))
    )
    result = await session.execute(stmt)
    event = result.unique().scalars().first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found.")
    return event


def _enforce_event_roles(event: Event, user: auth.AuthenticatedUser) -> None:
    required_roles = event.required_role_ids or settings.discord_event_role_ids
    if not required_roles:
        return
    guild_id = event.guild_id or (str(user.guild_ids[0]) if user.guild_ids else None)
    if not guild_id:
        return
    user_roles = user.guild_roles.get(guild_id, [])
    if not any(role in required_roles for role in user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have the required Discord role for this event.",
        )
