"""Auth request and response bodies (docs/design/06_API_CONTRACT.md, Auth)."""

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.common import Role


class DemoLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str | None = None
    role: Role | None = None

    @model_validator(mode="after")
    def _needs_one(self) -> "DemoLoginRequest":
        if self.email is None and self.role is None:
            raise ValueError("send an email or a role")
        return self


class User(BaseModel):
    id: str
    email: str
    full_name: str
    role: Role
    avatar_url: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User
