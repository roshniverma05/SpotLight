from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool

    model_config = {
        "from_attributes": True,
    }

class UserLogin(BaseModel):
    email: EmailStr
    password: str    

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"    