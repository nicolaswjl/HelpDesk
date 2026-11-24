from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from .database import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """DateTime que sempre entrega objetos com fuso UTC.

    O SQLite não guarda fuso horário: sem este tipo, as datas voltam "ingênuas"
    (sem "Z" no JSON) e o navegador as interpreta como horário local, deslocando
    todos os horários exibidos.
    """

    impl = DateTime
    cache_ok = True

    def __init__(self) -> None:
        super().__init__(timezone=True)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('user','technician','admin')", name="ck_users_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now_utc, nullable=False)

    created_tickets = relationship(
        "Ticket", foreign_keys="Ticket.creator_id", back_populates="creator"
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open','in_progress','waiting','completed')",
            name="ck_tickets_status",
        ),
        CheckConstraint(
            "priority IN ('low','medium','high','urgent')",
            name="ck_tickets_priority",
        ),
        Index("ix_tickets_creator_created", "creator_id", "created_at"),
        Index("ix_tickets_assignee_status", "assignee_id", "status"),
        Index("ix_tickets_status_priority", "status", "priority"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=now_utc, onupdate=now_utc, nullable=False
    )

    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_tickets")
    assignee = relationship("User", foreign_keys=[assignee_id])
    category = relationship("Category")
    comments = relationship("Comment", back_populates="ticket", cascade="all, delete-orphan")
    history = relationship("TicketHistory", back_populates="ticket", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (Index("ix_comments_ticket_created", "ticket_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now_utc, nullable=False)

    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User")


class TicketHistory(Base):
    __tablename__ = "ticket_history"
    __table_args__ = (Index("ix_ticket_history_ticket_changed", "ticket_id", "changed_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    field: Mapped[str] = mapped_column(String(40), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False)
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=now_utc, nullable=False)

    ticket = relationship("Ticket", back_populates="history")
    actor = relationship("User")
