from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Role = Literal["user", "technician", "admin"]
TicketStatus = Literal["open", "in_progress", "waiting", "completed"]
TicketPriority = Literal["low", "medium", "high", "urgent"]


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("O nome precisa ter pelo menos 2 caracteres.")
        return value


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr
    role: Role
    is_active: bool
    created_at: datetime


class UserActiveUpdate(BaseModel):
    is_active: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("A categoria precisa ter pelo menos 2 caracteres.")
        return value


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None


class TicketCreate(BaseModel):
    title: str = Field(min_length=4, max_length=160)
    description: str = Field(min_length=10, max_length=10000)
    priority: TicketPriority = "medium"
    category_id: int = Field(gt=0)

    @field_validator("title", "description")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O campo não pode ficar vazio.")
        return value


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=4, max_length=160)
    description: str | None = Field(default=None, min_length=10, max_length=10000)
    priority: TicketPriority | None = None
    status: TicketStatus | None = None

    @field_validator("title", "description")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("O campo não pode ficar vazio.")
        return value


class TicketAssign(BaseModel):
    assignee_id: int | None


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    creator_id: int
    assignee_id: int | None
    category_id: int
    created_at: datetime
    updated_at: datetime
    creator: UserOut
    assignee: UserOut | None
    category: CategoryOut


class TicketPage(BaseModel):
    items: list[TicketOut]
    total: int
    page: int
    size: int
    pages: int


class DashboardSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    by_priority: dict[str, int]


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=3000)

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O comentário não pode ficar vazio.")
        return value


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    content: str
    ticket_id: int
    author_id: int
    created_at: datetime
    author: UserOut


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    field: str
    old_value: str | None
    new_value: str | None
    ticket_id: int
    changed_by: int
    changed_at: datetime
    actor: UserOut
