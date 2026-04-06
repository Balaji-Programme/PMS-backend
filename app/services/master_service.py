from sqlalchemy.orm import Session, joinedload
from app.models.masters import UserStatus, Skill, Status, Priority
from app.models.roles import Role
from app.models.user import User

def get_user_statuses(db: Session):
    return db.query(UserStatus).all()

def get_statuses(db: Session):
    return db.query(Status).all()

def get_priorities(db: Session):
    return db.query(Priority).all()

def get_roles(db: Session):
    return db.query(Role).all()

def get_role(db: Session, role_id: int):
    return db.query(Role).options(joinedload(Role.users)).filter(Role.id == role_id).first()

def create_role(db: Session, role: dict):
    user_ids = role.pop('user_ids', [])
    
    db_role = Role(**role)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    
    if user_ids:
        users_to_update = db.query(User).filter(User.id.in_(user_ids)).all()
        for user in users_to_update:
            user.role_id = db_role.id
        db.commit()
        
    return db_role

def update_role(db: Session, role_id: int, role: dict):
    db_role = db.query(Role).filter(Role.id == role_id).first()
    
    if db_role:
        user_ids = role.pop('user_ids', None)
        
        for key, value in role.items():
            setattr(db_role, key, value)
            
        if user_ids is not None:
            db.query(User).filter(User.role_id == role_id).update({"role_id": None})
            
            if user_ids:
                users_to_update = db.query(User).filter(User.id.in_(user_ids)).all()
                for user in users_to_update:
                    user.role_id = db_role.id
                    
        db.commit()
        db.refresh(db_role)
        
    return db_role

def delete_role(db: Session, role_id: int):
    db_role = db.query(Role).filter(Role.id == role_id).first()
    if db_role:
        db.delete(db_role)
        db.commit()
        return True
    return False

def get_skills(db: Session):
    return db.query(Skill).all()

def search_statuses(db: Session, query: str, limit: int = 20):
    if not query:
        return []
    q = f"%{query}%"
    return db.query(Status).filter(Status.name.ilike(q)).limit(limit).all()

def search_priorities(db: Session, query: str, limit: int = 20):
    if not query:
        return []
    q = f"%{query}%"
    return db.query(Priority).filter(Priority.name.ilike(q)).limit(limit).all()

def search_user_statuses(db: Session, query: str, limit: int = 20):
    if not query:
        return []
    q = f"%{query}%"
    return db.query(UserStatus).filter(UserStatus.name.ilike(q)).limit(limit).all()

def search_roles(db: Session, query: str, limit: int = 20):
    if not query:
        return []
    q = f"%{query}%"
    return db.query(Role).filter(Role.name.ilike(q)).limit(limit).all()

def search_skills(db: Session, query: str, limit: int = 20):
    if not query:
        return []
    q = f"%{query}%"
    return db.query(Skill).filter(Skill.name.ilike(q)).limit(limit).all()
