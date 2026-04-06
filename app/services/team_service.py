from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.team import Team
from app.models.user import User
from app.schemas.team import TeamCreate, TeamUpdate
from app.utils.ids import generate_public_id
from app.utils.audit_utils import write_audit, capture_audit_details

def get_team(db: Session, team_id: int):
    return db.query(Team).filter(Team.id == team_id).first()

def get_team_with_members(db: Session, team_id: int):
    return db.query(Team).options(
        joinedload(Team.members)
    ).filter(Team.id == team_id).first()

def get_teams(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Team).offset(skip).limit(limit).all()

def search_teams(db: Session, query: str = "", limit: int = 15):
    q = db.query(Team)
    if query:
        q = q.filter(Team.name.ilike(f"%{query}%"))
    return q.limit(limit).all()

def create_team(db: Session, team: TeamCreate, actor_id: Optional[str] = None):
    public_id = generate_public_id("TM-")
    
    db_team = Team(
        public_id=public_id,
        name=team.name,
        team_email=team.team_email,
        budget_allocation=team.budget_allocation,
        description=team.description,
        team_type=team.team_type,
        max_team_size=team.max_team_size,
        primary_communication_channel=team.primary_communication_channel,
        channel_id=team.channel_id,
        lead_email=team.lead_email,
    )
    
    if team.member_emails:
        members = db.query(User).filter(User.email.in_(team.member_emails)).all()
        db_team.members = members
        
    db.add(db_team)
    db.flush()

    write_audit(db, actor_id, "CREATE", "teams",
                resource_id=db_team.id,
                record_id=db_team.id,
                details=[{"field_name": "name", "old_value": None, "new_value": team.name}])

    db.commit()
    db.refresh(db_team)
    return get_team(db, db_team.id)

def update_team(db: Session, team_id: int, team_update: TeamUpdate, actor_id: Optional[str] = None):
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if not db_team:
        return None
        
    update_data = team_update.model_dump(exclude_unset=True)
    changes = capture_audit_details(db_team, update_data)
    
    if "member_emails" in update_data:
        member_emails = update_data.pop("member_emails")
        if member_emails is not None:
            members = db.query(User).filter(User.email.in_(member_emails)).all()
            db_team.members = members
            
    for key, value in update_data.items():
        setattr(db_team, key, value)

    write_audit(db, actor_id, "UPDATE", "teams",
                resource_id=team_id,
                record_id=team_id,
                details=changes)
        
    db.commit()
    db.refresh(db_team)
    return get_team(db, db_team.id)

def delete_team(db: Session, team_id: int, actor_id: Optional[str] = None):
    db_team = db.query(Team).filter(Team.id == team_id).first()
    if db_team:
        write_audit(db, actor_id, "DELETE", "teams",
                    resource_id=team_id,
                    record_id=team_id,
                    details=[{"field_name": "name", "old_value": db_team.name, "new_value": None}])
        db.delete(db_team)
        db.commit()
        return True
    return False

def add_team_member(db: Session, team_id: int, user_email: str, actor_id: Optional[str] = None):
    db_team = db.query(Team).filter(Team.id == team_id).first()
    db_user = db.query(User).filter(User.email == user_email).first()
    
    if db_team and db_user:
        if db_user not in db_team.members:
            db_team.members.append(db_user)
            write_audit(db, actor_id, "ASSIGN_TO_TEAM", "teams",
                        resource_id=team_id,
                        record_id=team_id,
                        details=[{"field_name": "members", "old_value": None, "new_value": user_email}])
            db.commit()
            return True
    return False

def remove_team_member(db: Session, team_id: int, user_email: str, actor_id: Optional[str] = None):
    db_team = db.query(Team).filter(Team.id == team_id).first()
    db_user = db.query(User).filter(User.email == user_email).first()
    
    if db_team and db_user:
        if db_user in db_team.members:
            db_team.members.remove(db_user)
            write_audit(db, actor_id, "REMOVE_FROM_TEAM", "teams",
                        resource_id=team_id,
                        record_id=team_id,
                        details=[{"field_name": "members", "old_value": user_email, "new_value": None}])
            db.commit()
            return True
    return False
