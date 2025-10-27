import datetime as dt
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import auth
from ..config import get_settings
from ..database import get_session
from ..models import Event
from ..schemas import AlertOut


router = APIRouter(prefix="/alerts", tags=["alerts"])
settings = get_settings()


@router.get("", response_model=List[AlertOut])
async def list_alerts(
    session: AsyncSession = Depends(get_session),
    _: auth.AuthenticatedUser = Depends(auth.get_current_user),
) -> List[AlertOut]:
    now = dt.datetime.now(dt.timezone.utc)
    lead = dt.timedelta(minutes=settings.alert_lead_minutes)
    window_end = now + lead
    stmt = select(Event).where(Event.start_at.between(now, window_end)).order_by(Event.start_at.asc())
    result = await session.execute(stmt)
    events = result.scalars().all()
    return [
        AlertOut(
            event_id=event.id,
            title=event.title,
            start_at=event.start_at,
            lead_minutes=settings.alert_lead_minutes,
        )
        for event in events
    ]
