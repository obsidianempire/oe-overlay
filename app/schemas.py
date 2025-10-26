import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiry in seconds")


class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_at: dt.datetime
    timezone: Optional[str] = None


class EventOut(EventBase):
    id: int

    class Config:
        orm_mode = True


class RosterMemberBase(BaseModel):
    name: str
    role: Optional[str] = None
    cp: Optional[int] = None


class RosterMemberOut(RosterMemberBase):
    id: int

    class Config:
        orm_mode = True


class AttendanceRecordOut(BaseModel):
    id: int
    event_id: int
    event_date: dt.datetime
    members: List[str]

    class Config:
        orm_mode = True


class DiscordUser(BaseModel):
    id: str
    username: str
    discriminator: str
    avatar: Optional[str] = None

