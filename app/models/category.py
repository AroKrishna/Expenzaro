# app/models/category.py
import enum
from sqlalchemy import Column, Integer, String, Enum as SAEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base

class CategoryType(str, enum.Enum):
    income = "income"
    expense = "expense"

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(SAEnum(CategoryType, name="category_type"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "name", "type", name="uq_categories_user_name_type"),
    )

    user = relationship("User", backref="categories")
