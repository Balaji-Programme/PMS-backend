from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select, update as sa_update
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.models.masters import UserStatus, Skill, Status, Priority
from app.models.roles import Role
from app.models.user import User

def get_user_statuses(db: Session) -> List[UserStatus]:
    return (db.execute(select(UserStatus))).scalars().all()

def get_statuses(db: Session) -> List[Status]:
    return (db.execute(select(Status))).scalars().all()

def get_priorities(db: Session) -> List[Priority]:
    return (db.execute(select(Priority))).scalars().all()

def get_skills(db: Session) -> List[Skill]:
    return (db.execute(select(Skill))).scalars().all()

def get_roles(db: Session) -> List[Role]:
    return (db.execute(select(Role))).scalars().all()

def get_role(db: Session, role_id: int) -> Optional[Role]:
    result = db.execute(
        select(Role).options(selectinload(Role.users)).where(Role.id == role_id)
    )
    return result.scalar_one_or_none()

def create_role(db: Session, role: dict) -> Role:
    user_ids = role.pop("user_ids", [])
    db_role = Role(**role)
    db.add(db_role)
    db.flush()

    if user_ids:
        db.execute(
            sa_update(User).where(User.id.in_(user_ids)).values(role_id=db_role.id)
        )

    db.commit()
    db.refresh(db_role)
    return db_role

def update_role(db: Session, role_id: int, role: dict) -> Optional[Role]:
    result = db.execute(select(Role).where(Role.id == role_id))
    db_role = result.scalar_one_or_none()
    if not db_role:
        return None

    user_ids = role.pop("user_ids", None)
    for key, value in role.items():
        setattr(db_role, key, value)

    if user_ids is not None:
        db.execute(sa_update(User).where(User.role_id == role_id).values(role_id=None))
        if user_ids:
            db.execute(sa_update(User).where(User.id.in_(user_ids)).values(role_id=db_role.id))

    db.commit()
    db.refresh(db_role)
    return db_role

def delete_role(db: Session, role_id: int) -> bool:
    result = db.execute(select(Role).where(Role.id == role_id))
    db_role = result.scalar_one_or_none()
    if not db_role:
        return False
    db.delete(db_role)
    db.commit()
    return True

def search_statuses(db: Session, query: str, limit: int = 20) -> List[Status]:
    if not query:
        return []
    return (db.execute(select(Status).where(Status.name.ilike(f"%{query}%")).limit(limit))).scalars().all()

def search_priorities(db: Session, query: str, limit: int = 20) -> List[Priority]:
    if not query:
        return []
    return (db.execute(select(Priority).where(Priority.name.ilike(f"%{query}%")).limit(limit))).scalars().all()

def search_user_statuses(db: Session, query: str, limit: int = 20) -> List[UserStatus]:
    if not query:
        return []
    return (db.execute(select(UserStatus).where(UserStatus.name.ilike(f"%{query}%")).limit(limit))).scalars().all()

def search_roles(db: Session, query: str, limit: int = 20) -> List[Role]:
    if not query:
        return []
    return (db.execute(select(Role).where(Role.name.ilike(f"%{query}%")).limit(limit))).scalars().all()

def search_skills(db: Session, query: str, limit: int = 20) -> List[Skill]:
    if not query:
        return []
    return (db.execute(select(Skill).where(Skill.name.ilike(f"%{query}%")).limit(limit))).scalars().all()
