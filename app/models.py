import datetime as dt

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
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

    attendance_records = relationship("AttendanceRecord", back_populates="event", cascade="all, delete-orphan")


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
