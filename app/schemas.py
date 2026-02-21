from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID

class AuthIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)

class TokenOut(BaseModel):
    accessToken: str

class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    color: str | None = Field(default=None, max_length=20)

class SessionCreate(BaseModel):
    tagId: UUID | None = None
    sessionDate: date
    durationMin: int = Field(ge=1, le=1440)
    notes: str | None = None

class SessionUpdate(BaseModel):
    tagId: UUID | None = None
    sessionDate: date | None = None
    durationMin: int | None = Field(default=None, ge=1, le=1440)
    notes: str | None = None
