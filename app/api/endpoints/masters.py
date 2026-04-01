from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import allow_authenticated
from app.schemas.masters import MasterResponse, RoleResponse, SkillResponse, RoleCreate, RoleUpdate
from app.schemas.user import RoleWithUsersResponse
from app.services import master_service

router = APIRouter(dependencies=[Depends(allow_authenticated)])


@router.get("/user-statuses", response_model=List[MasterResponse])
def read_user_statuses(db: Session = Depends(get_db)):
    return master_service.get_user_statuses(db)
@router.get("/user-statuses/search", response_model=List[MasterResponse])
def search_user_statuses(q: str = Query(..., min_length=1), limit: int = 20, db: Session = Depends(get_db)):
    return master_service.search_user_statuses(db, q, limit)

@router.get("/statuses", response_model=List[MasterResponse])
def read_statuses(db: Session = Depends(get_db)):
    return master_service.get_statuses(db)

@router.get("/statuses/search", response_model=List[MasterResponse])
def search_statuses(q: str = Query(..., min_length=1), limit: int = 20, db: Session = Depends(get_db)):
    return master_service.search_statuses(db, q, limit)

@router.get("/priorities", response_model=List[MasterResponse])
def read_priorities(db: Session = Depends(get_db)):
    return master_service.get_priorities(db)

@router.get("/priorities/search", response_model=List[MasterResponse])
def search_priorities(q: str = Query(..., min_length=1), limit: int = 20, db: Session = Depends(get_db)):
    return master_service.search_priorities(db, q, limit)

@router.get("/roles", response_model=List[RoleResponse])
def read_roles(db: Session = Depends(get_db)):
    return master_service.get_roles(db)

@router.get("/roles/search", response_model=List[RoleResponse])
def search_roles(q: str = Query(..., min_length=1), limit: int = 20, db: Session = Depends(get_db)):
    return master_service.search_roles(db, q, limit)

@router.get("/roles/{role_id}", response_model=RoleWithUsersResponse)
def read_role(role_id: int, db: Session = Depends(get_db)):
    db_role = master_service.get_role(db, role_id)
    if db_role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return db_role

@router.post("/roles", response_model=RoleResponse)
def create_role(role: RoleCreate, db: Session = Depends(get_db)):
    return master_service.create_role(db, role.model_dump())

@router.put("/roles/{role_id}", response_model=RoleResponse)
def update_role(role_id: int, role: RoleUpdate, db: Session = Depends(get_db)):
    return master_service.update_role(db, role_id, role.model_dump(exclude_unset=True))

@router.delete("/roles/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db)):
    success = master_service.delete_role(db, role_id)
    if not success:
        raise HTTPException(status_code=404, detail="Role not found")
    return {"message": "Role deleted successfully"}

@router.post("/roles/{role_id}/users/{user_email}")
def assign_user_to_role(role_id: int, user_email: str, db: Session = Depends(get_db)):
    """Assign a user (by email) to a role."""
    from app.models.user import User
    from app.models.roles import Role
    db_role = db.query(Role).filter(Role.id == role_id).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User with email '{user_email}' not found in system.")
    user.role_id = role_id
    db.commit()
    return {"message": "User assigned to role successfully"}

@router.delete("/roles/{role_id}/users/{user_email}")
def remove_user_from_role(role_id: int, user_email: str, db: Session = Depends(get_db)):
    """Remove a user (by email) from a role."""
    from app.models.user import User
    user = db.query(User).filter(User.email == user_email, User.role_id == role_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found in this role.")
    user.role_id = None
    db.commit()
    return {"message": "User removed from role successfully"}

@router.post("/roles/{role_id}/users/bulk")
def bulk_assign_users_to_role(role_id: int, user_ids: List[int], db: Session = Depends(get_db)):
    """Assign multiple users to a role."""
    from app.models.user import User
    from app.models.roles import Role
    db_role = db.query(Role).filter(Role.id == role_id).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Update bulk
    db.query(User).filter(User.id.in_(user_ids)).update({"role_id": role_id}, synchronize_session=False)
    db.commit()
    return {"message": f"{len(user_ids)} users assigned to role successfully"}

@router.get("/skills", response_model=List[SkillResponse])
def read_skills(db: Session = Depends(get_db)):
    return master_service.get_skills(db)

@router.get("/skills/search", response_model=List[SkillResponse])
def search_skills(q: str = Query(..., min_length=1), limit: int = 20, db: Session = Depends(get_db)):
    return master_service.search_skills(db, q, limit)
