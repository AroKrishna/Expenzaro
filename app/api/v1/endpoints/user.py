# app/api/v1/endpoints/user.py
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import get_password_hash, decode_access_token
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter(tags=["Users"])

@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        is_active=payload.is_active,
        role="user",  # Always set new users as "user" role
        hashed_password=get_password_hash(payload.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# Admin-only endpoint to create users with specific roles
@router.post("/admin/create", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    payload: UserCreate, 
    role: str = "user",
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Admin-only endpoint to create users with specific roles"""
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    # Validate role
    valid_roles = ["user", "admin"]
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        is_active=payload.is_active,
        role=role,
        hashed_password=get_password_hash(payload.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/", response_model=list[UserOut])
def list_users(
    skip: int = 0, 
    limit: int = 50, 
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)  # Only admins can list all users
):
    users = db.query(User).offset(skip).limit(limit).all()
    return users


# Helper function to get current user from token
def get_current_user_from_token(token: str, db: Session):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


@router.get("/me", response_model=UserOut)
def get_current_user_info(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.split(" ")[1]
    return get_current_user_from_token(token, db)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int, 
    payload: UserUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # RBAC: Admin can update any user, regular users can only update themselves
    if current_user.role != "admin" and current_user.id != user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions to update this user")
    
    # Prevent normal users from changing roles
    if payload.role is not None and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can change user roles")
    
    # Update only provided fields
    if payload.email is not None:
        # Check if new email is unique
        existing = db.query(User).filter(User.email == payload.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")
        user.email = payload.email
    
    if payload.full_name is not None:
        user.full_name = payload.full_name
    
    if payload.password is not None:
        user.hashed_password = get_password_hash(payload.password)
    
    if payload.is_active is not None:
        user.is_active = payload.is_active
    
    if payload.role is not None and current_user.role == "admin":
        user.role = payload.role
    
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int, 
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)  # Only admins can delete users
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    return None