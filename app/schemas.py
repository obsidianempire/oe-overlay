import datetime as dt
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiry in seconds")


class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_at: dt.datetime
    timezone: Optional[str] = None


class EventCreate(EventBase):
    required_role_ids: Optional[List[str]] = None


class EventOut(EventBase):
    id: int
    created_by: str
    guild_id: Optional[str] = None
    required_role_ids: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


class EventDetail(EventOut):
    attendees: List["EventAttendeeOut"] = Field(default_factory=list)


class RosterMemberBase(BaseModel):
    name: str
    role: Optional[str] = None
    cp: Optional[int] = None


class RosterMemberOut(RosterMemberBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class AttendanceRecordOut(BaseModel):
    id: int
    event_id: int
    event_date: dt.datetime
    members: List[str]

    model_config = ConfigDict(from_attributes=True)


class DiscordUser(BaseModel):
    id: str
    username: str
    discriminator: str
    avatar: Optional[str] = None


class EventAttendeeOut(BaseModel):
    id: int
    event_id: int
    user_id: str
    username: str

    model_config = ConfigDict(from_attributes=True)


class CraftRequestCreate(BaseModel):
    item_name: str
    quantity: int = Field(ge=1)
    notes: Optional[str] = None


class CraftRequestOut(BaseModel):
    id: int
    requester_id: str
    requester_name: str
    item_name: str
    quantity: int
    notes: Optional[str]
    status: str
    created_at: dt.datetime
    updated_at: dt.datetime
    assignment: Optional["CraftAssignmentOut"] = None

    model_config = ConfigDict(from_attributes=True)


class CraftAssignmentCreate(BaseModel):
    meet_at: dt.datetime
    location: str
    estimated_completion: Optional[dt.datetime] = None


class CraftAssignmentOut(BaseModel):
    id: int
    crafter_id: str
    crafter_name: str
    meet_at: dt.datetime
    location: str
    estimated_completion: Optional[dt.datetime]
    status: str

    model_config = ConfigDict(from_attributes=True)


CraftRequestOut.model_rebuild()
EventDetail.model_rebuild()


class AlertOut(BaseModel):
    event_id: int
    title: str
    start_at: dt.datetime
    lead_minutes: int


class UserInfo(BaseModel):
    id: str
    username: str
    discriminator: str
    guild_ids: List[int]
    guild_roles: Dict[str, List[str]] = Field(default_factory=dict)
    can_create_events: bool = False
    alert_lead_minutes: int = 15
