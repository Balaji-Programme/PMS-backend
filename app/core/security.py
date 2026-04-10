from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

pwd_context    = CryptContext(schemes=["bcrypt"], deprecated="auto")
_bearer_scheme = HTTPBearer(auto_error=False)

ROLE_ADMIN           = "Admin"
ROLE_PROJECT_MANAGER = "Project Manager"
ROLE_TEAM_LEAD       = "Team Lead"
ROLE_EMPLOYEE        = "Employee"

FULL_ACCESS_ROLES     = [ROLE_ADMIN, ROLE_PROJECT_MANAGER]
TEAM_LEAD_PLUS_ROLES  = [ROLE_ADMIN, ROLE_PROJECT_MANAGER, ROLE_TEAM_LEAD]
ALL_ROLES             = [ROLE_ADMIN, ROLE_PROJECT_MANAGER, ROLE_TEAM_LEAD, ROLE_EMPLOYEE]

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode(
        {"exp": expire, "sub": str(subject)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload   = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_s = payload.get("sub")
        if not user_id_s:
            raise ValueError("No sub in payload")
        user_id = int(user_id_s)
    except (JWTError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from app.models.user import User
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or user.is_deleted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def get_user_role_name(user) -> Optional[str]:
    return user.role.name if user and user.role else None

def is_full_access(user) -> bool:
    return get_user_role_name(user) in FULL_ACCESS_ROLES

def is_team_lead_plus(user) -> bool:
    return get_user_role_name(user) in TEAM_LEAD_PLUS_ROLES

def is_employee_only(user) -> bool:
    return get_user_role_name(user) == ROLE_EMPLOYEE

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user=Depends(get_current_user)):
        if current_user.role and current_user.role.name in self.allowed_roles:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Requires one of: {', '.join(self.allowed_roles)}",
        )

allow_pm             = RoleChecker(FULL_ACCESS_ROLES)
allow_team_lead_plus = RoleChecker(TEAM_LEAD_PLUS_ROLES)
allow_all_roles      = RoleChecker(ALL_ROLES)

async def allow_authenticated(current_user=Depends(get_current_user)):
    return current_user

class CheckProjectOwner:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        project_id: int,
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        from app.models.project import Project

        result   = await db.execute(select(Project.owner_id).where(Project.id == project_id))
        owner_id = result.scalar_one_or_none()

        if owner_id is not None and owner_id == current_user.id:
            return current_user

        if current_user.role and current_user.role.name in self.allowed_roles:
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Requires project ownership or one of: {', '.join(self.allowed_roles)}",
        )

class CheckTaskOwner:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles
        
    async def __call__(
        self,
        task_id: int,
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        from app.models.task import Task
        from app.models.project import Project
        
        result = await db.execute(
            select(Task.assignee_id, Project.owner_id)
            .outerjoin(Project, Project.id == Task.project_id)
            .where(Task.id == task_id)
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
            
        assignee_id, owner_id = row
        
        if owner_id is not None and owner_id == current_user.id:
            return current_user
        if assignee_id is not None and assignee_id == current_user.id:
            return current_user
        if current_user.role and current_user.role.name in self.allowed_roles:
            return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Requires assignee, project ownership or one of: {', '.join(self.allowed_roles)}",
        )

check_project_owner_or_pm       = CheckProjectOwner(FULL_ACCESS_ROLES)
check_project_owner_or_lead     = CheckProjectOwner(TEAM_LEAD_PLUS_ROLES)
check_task_owner_or_lead        = CheckTaskOwner(TEAM_LEAD_PLUS_ROLES)

class ProjectRoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        project_id: int,
        current_user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        if current_user.role and current_user.role.name in FULL_ACCESS_ROLES:
            return current_user

        from app.models.project import project_users
        assignment = (
            await db.execute(
                select(project_users.c.role_id).where(
                    project_users.c.project_id == project_id,
                    project_users.c.user_id    == current_user.id,
                )
            )
        ).first()

        if not assignment:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this project.")

        if not assignment.role_id:
            if "Member" in self.allowed_roles:
                return current_user
        else:
            from app.models.roles import Role
            role = (await db.execute(select(Role).where(Role.id == assignment.role_id))).scalar_one_or_none()
            if role and role.name in self.allowed_roles:
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires project-specific role: {', '.join(self.allowed_roles)}",
        )

allow_project_lead   = ProjectRoleChecker(["Project Lead"])
allow_project_member = ProjectRoleChecker(["Project Lead", "Developer", "Member"])
