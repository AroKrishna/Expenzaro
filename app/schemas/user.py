from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional

# Shared properties
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True

# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str

# Properties to update via API
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None  # present, but we’ll restrict who can use it in step 2


# Properties to return to client
class UserOut(UserBase):
    id: int
    role: str  # NEW

    model_config = ConfigDict(from_attributes=True)