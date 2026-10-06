# app/api/v1/endpoints/category.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.core.deps import get_current_user

router = APIRouter()

# Create Category
@router.post("/", response_model=CategoryOut)
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if category with same name and type already exists for this user
    existing_category = db.query(Category).filter(
        Category.user_id == current_user.id,
        Category.name == category.name,
        Category.type == category.type
    ).first()
    
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category '{category.name}' of type '{category.type}' already exists"
        )
    
    db_category = Category(
        name=category.name,
        type=category.type,
        user_id=current_user.id
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


# Get all categories for current user
@router.get("/", response_model=List[CategoryOut])
def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    categories = db.query(Category).filter(Category.user_id == current_user.id).all()
    return categories


# Update category
@router.put("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int,
    category: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()

    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    # Check for duplicate name/type combination if name or type is being updated
    if category.name is not None or category.type is not None:
        new_name = category.name if category.name is not None else db_category.name
        new_type = category.type if category.type is not None else db_category.type
        
        existing_category = db.query(Category).filter(
            Category.user_id == current_user.id,
            Category.name == new_name,
            Category.type == new_type,
            Category.id != category_id
        ).first()
        
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category '{new_name}' of type '{new_type}' already exists"
            )

    # Update only provided fields
    if category.name is not None:
        db_category.name = category.name
    if category.type is not None:
        db_category.type = category.type
        
    db.commit()
    db.refresh(db_category)
    return db_category


# Delete category
@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_category = db.query(Category).filter(
        Category.id == category_id,
        Category.user_id == current_user.id
    ).first()

    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    db.delete(db_category)
    db.commit()
    return None
