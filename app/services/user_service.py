from typing import List, Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from app.models.user import User
from app.models.masters import Skill
from app.models.roles import Role
from app.schemas.user import UserCreate, UserUpdate
from app.utils.ids import generate_public_id
from app.utils.audit_utils import write_audit, capture_audit_details

def get_user(db: Session, user_id: int):
    return db.query(User).options(
        joinedload(User.role),
        joinedload(User.status),
        joinedload(User.skills)
    ).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def get_users(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    search: Optional[str] = None,
    role_ids: Optional[List[int]] = None,
):
    query = db.query(User).options(
        joinedload(User.role),
        joinedload(User.status),
        joinedload(User.skills)
    )
    
    if search:
        from sqlalchemy import or_
        q = f"%{search}%"
        query = query.filter(
            or_(
                User.first_name.ilike(q),
                User.last_name.ilike(q),
                User.email.ilike(q),
                User.username.ilike(q),
                User.display_name.ilike(q)
            )
        )
        
    if role_ids:
        query = query.filter(User.role_id.in_(role_ids))
        
    total = query.count()
    data = query.offset(skip).limit(limit).all()
    
    return {"total": total, "data": data}

def create_user(db: Session, user: UserCreate, actor_id: Optional[str] = None):
    public_id = generate_public_id("USR-")
    
    db_user = User(
        public_id=public_id,
        employee_id=user.employee_id or generate_public_id("EMP-"),
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        username=user.username or user.email.split("@")[0],
        o365_id=user.o365_id,
        phone=user.phone,
        job_title=user.job_title,
        join_date=user.join_date,
        role_id=user.role_id,
        status_id=user.status_id,
        manager_email=user.manager_email,
        display_name=user.display_name,
        gender=user.gender,
        country=user.country,
        state=user.state,
        language=user.language,
        timezone=user.timezone
    )
    
    if user.skill_ids:
        skills = db.query(Skill).filter(Skill.id.in_(user.skill_ids)).all()
        db_user.skills.extend(skills)

    db.add(db_user)
    db.flush()

    write_audit(db, actor_id, "CREATE", "users",
                resource_id=db_user.id,
                record_id=db_user.id,
                details=[{"field_name": "email", "old_value": None, "new_value": user.email}])

    db.commit()
    db.refresh(db_user)
    return get_user(db, db_user.id)

def update_user(db: Session, user_id: int, user_update: UserUpdate, actor_id: Optional[str] = None):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return None
        
    update_data = user_update.model_dump(exclude_unset=True)
    changes = capture_audit_details(db_user, update_data)
    
    if "skill_ids" in update_data:
        skill_ids = update_data.pop("skill_ids")
        if skill_ids is not None:
            skills = db.query(Skill).filter(Skill.id.in_(skill_ids)).all()
            db_user.skills = skills
            
    for key, value in update_data.items():
        setattr(db_user, key, value)

    write_audit(db, actor_id, "UPDATE", "users",
                resource_id=user_id,
                record_id=user_id,
                details=changes)
        
    db.commit()
    db.refresh(db_user)
    return get_user(db, db_user.id)

def delete_user(db: Session, user_id: int, actor_id: Optional[str] = None):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        write_audit(db, actor_id, "DELETE", "users",
                    resource_id=user_id,
                    record_id=user_id,
                    details=[{"field_name": "email", "old_value": db_user.email, "new_value": None}])
        db.delete(db_user)
        db.commit()
        return True
    return False

def search_users(db: Session, query: str, limit: int = 20):
    if not query:
        return []
    q = f"%{query}%"
    from sqlalchemy import or_
    return db.query(User).options(
        joinedload(User.role),
        joinedload(User.status)
    ).filter(
        or_(
            User.first_name.ilike(q),
            User.last_name.ilike(q),
            User.email.ilike(q),
            User.username.ilike(q),
            User.display_name.ilike(q)
        )
    ).limit(limit).all()

def upsert_o365_user(
    db: Session,
    o365_id: str,
    email: str,
    first_name: str,
    last_name: str,
    display_name: Optional[str] = None,
) -> User:

    user = db.query(User).filter(User.o365_id == o365_id).first()
    
    if not user and email:
        user = db.query(User).filter(User.email == email.lower()).first()

    if user:
        user.o365_id = o365_id
        user.is_synced = True
        
        if not user.role_id:
            default_role = db.query(Role).filter(Role.name == "Employee").first()
            if default_role:
                user.role_id = default_role.id
        
        if not user.status_id:
            from app.models.masters import UserStatus
            default_status = db.query(UserStatus).filter(UserStatus.name == "Active").first()
            if default_status:
                user.status_id = default_status.id

        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if display_name:
            user.display_name = display_name
        db.commit()
        db.refresh(user)
        return user

    default_role = db.query(Role).filter(Role.name == "Employee").first()
    username = email.split("@")[0].lower().replace(".", "_")

    base_username = username
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}_{counter}"
        counter += 1

    new_user = User(
        public_id=generate_public_id("USR-"),
        employee_id=generate_public_id("EMP-"),
        first_name=first_name or email.split("@")[0],
        last_name=last_name or "",
        email=email.lower(),
        username=username,
        display_name=display_name or f"{first_name} {last_name}".strip(),
        o365_id=o365_id,
        is_synced=True,
        is_external=False,
        role_id=default_role.id if default_role else None,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
