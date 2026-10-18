"""Explicit transport schemas; ORM models and credential hashes are never serialized."""
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=1, max_length=160)
    organization_name: str = Field(min_length=2, max_length=160)
    organization_slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", min_length=2, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    organization_id: str | None = None


class OrganizationPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    status: str | None = Field(default=None, pattern=r"^(active|suspended)$")


class MemberPatch(BaseModel):
    status: str | None = Field(default=None, pattern=r"^(active|suspended|revoked)$")
    role_id: str | None = Field(default=None, min_length=1, max_length=36)


class MemberCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)
    role_id: str = Field(min_length=1, max_length=36)


class RolePatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    permissions: list[str] | None = Field(default=None, max_length=100)


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(default="", max_length=255)
    permissions: list[str] = Field(default_factory=list, max_length=100)


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    name: str
    description: str
    is_system: bool


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    is_active: bool


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    slug: str
    status: str


class OrganizationUnitCreate(BaseModel):
    unit_type: str = Field(pattern=r"^(business_unit|location|department|team)$")
    name: str = Field(min_length=2, max_length=160)
    code: str | None = Field(default=None, max_length=60)
    parent_id: str | None = Field(default=None, max_length=36)


class OrganizationUnitPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    code: str | None = Field(default=None, max_length=60)
    parent_id: str | None = Field(default=None, max_length=36)
