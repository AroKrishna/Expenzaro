# app/schemas/category.py
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.category import CategoryType

class CategoryBase(BaseModel):
    name: str
    type: CategoryType  # "income" | "expense"

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[CategoryType] = None

class CategoryOut(CategoryBase):
    id: int
    user_id: int
    model_config = ConfigDict(from_attributes=True)
