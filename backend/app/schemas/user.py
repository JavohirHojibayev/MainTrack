from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    role: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UserPasswordReset(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=64)
    password: str | None = Field(default=None, min_length=6, max_length=128)

    @model_validator(mode="after")
    def _require_any_field(self) -> "UserPasswordReset":
        if not self.username and not self.password:
            raise ValueError("At least one of username or password is required")
        return self
