import datetime as dt

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship

from .database import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_at = Column(DateTime(timezone=True), nullable=False)
    timezone = Column(String(64), nullable=True)
    created_by = Column(String(40), nullable=False)
    guild_id = Column(String(40), nullable=True)
    required_role_ids = Column(ARRAY(String), nullable=True)

    attendance_records = relationship("AttendanceRecord", back_populates="event", cascade="all, delete-orphan")
    attendees = relationship("EventAttendee", back_populates="event", cascade="all, delete-orphan")


class RosterMember(Base, TimestampMixin):
    __tablename__ = "roster_members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(128), nullable=True)
    cp = Column(Integer, nullable=True)


class AttendanceRecord(Base, TimestampMixin):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    event_date = Column(DateTime(timezone=True), nullable=False)
    members = Column(JSONB, nullable=False, default=list)

    event = relationship("Event", back_populates="attendance_records")


class EventAttendee(Base, TimestampMixin):
    __tablename__ = "event_attendees"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(40), nullable=False)
    username = Column(String(255), nullable=False)

    event = relationship("Event", back_populates="attendees")


class CraftRequest(Base, TimestampMixin):
    __tablename__ = "craft_requests"

    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(String(40), nullable=False)
    requester_name = Column(String(255), nullable=False)
    item_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    notes = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="open")  # open, accepted, completed, cancelled

    assignment = relationship("CraftAssignment", back_populates="request", uselist=False, cascade="all, delete-orphan")


class CraftAssignment(Base, TimestampMixin):
    __tablename__ = "craft_assignments"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("craft_requests.id", ondelete="CASCADE"), nullable=False, unique=True)
    crafter_id = Column(String(40), nullable=False)
    crafter_name = Column(String(255), nullable=False)
    meet_at = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(255), nullable=False)
    estimated_completion = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False, default="accepted")  # accepted, fulfilled, cancelled

    request = relationship("CraftRequest", back_populates="assignment")
