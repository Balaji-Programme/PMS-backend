from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, allow_authenticated, allow_pm, is_employee_only
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate, UserListResponse
from app.services import user_service

router = APIRouter(dependencies=[Depends(allow_authenticated)])

@router.get("/me", response_model=UserResponse)
async def read_user_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/search", response_model=List[UserResponse])
async def search_users(
    q: str = Query(..., min_length=1),
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    return await user_service.search_users(db, query=q, limit=limit)

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(allow_pm),
):
    if await user_service.get_user_by_email(db, email=user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if user.username and await user_service.get_user_by_username(db, username=user.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    try:
        return await user_service.create_user(db=db, user=user, actor_id=current_user.o365_id or str(current_user.id))
    except Exception as e:
        if "Duplicate entry" in str(e) and "employee_id" in str(e):
            raise HTTPException(status_code=400, detail="Employee ID already exists")
        raise HTTPException(status_code=400, detail="Failed to create user. Data might violate constraints.")

@router.get("/", response_model=UserListResponse)
async def read_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    role_id: Optional[List[int]] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await user_service.get_users(db, skip=skip, limit=limit, search=search, role_ids=role_id)

@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    db_user = await user_service.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(allow_authenticated),
):
    if is_employee_only(current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied: you can only update your own profile.")
    db_user = await user_service.update_user(
        db, user_id=user_id, user_update=user_update, actor_id=current_user.o365_id or str(current_user.id)
    )
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(allow_pm),
):
    success = await user_service.delete_user(db, user_id=user_id, actor_id=current_user.o365_id or str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
