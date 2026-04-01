from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.milestone import Milestone
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate
from app.utils.ids import generate_public_id
from app.utils.audit_utils import write_audit, capture_audit_details
from datetime import date

def get_milestone(db: Session, milestone_id: int):
    return db.query(Milestone).options(
        joinedload(Milestone.project),
        joinedload(Milestone.status),
        joinedload(Milestone.owner)
    ).filter(Milestone.id == milestone_id).first()

def get_milestones(
    db: Session, 
    project_id: int = None, 
    skip: int = 0, 
    limit: int = 100,
    status_ids: List[int] = None
):
    query = db.query(Milestone).options(
        joinedload(Milestone.project),
        joinedload(Milestone.status),
        joinedload(Milestone.owner)
    )
    if project_id:
        query = query.filter(Milestone.project_id == project_id)
    if status_ids:
        query = query.filter(Milestone.status_id.in_(status_ids))
        
    return query.offset(skip).limit(limit).all()

def create_milestone(db: Session, milestone: MilestoneCreate, actor_id: Optional[str] = None):
    public_id = generate_public_id("MLS-")
    db_milestone = Milestone(
        public_id=public_id,
        title=milestone.title,
        description=milestone.description,
        start_date=milestone.start_date,
        end_date=milestone.end_date,
        project_id=milestone.project_id,
        status_id=milestone.status_id,
        owner_email=milestone.owner_email,
        flags=milestone.flags,
        tags=milestone.tags
    )
    db.add(db_milestone)
    db.flush()

    write_audit(db, actor_id, "CREATE", "milestones",
                resource_id=milestone.project_id or db_milestone.id,
                record_id=db_milestone.id,
                details=[{"field_name": "title", "old_value": None, "new_value": milestone.title}])

    db.commit()
    db.refresh(db_milestone)
    return get_milestone(db, db_milestone.id)

def update_milestone(db: Session, milestone_id: int, milestone_update: MilestoneUpdate, actor_id: Optional[str] = None):
    db_milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not db_milestone:
        return None
    
    update_data = milestone_update.model_dump(exclude_unset=True)
    changes = capture_audit_details(db_milestone, update_data)

    for key, value in update_data.items():
        setattr(db_milestone, key, value)

    write_audit(db, actor_id, "UPDATE", "milestones",
                resource_id=db_milestone.project_id or milestone_id,
                record_id=milestone_id,
                details=changes)
        
    db.commit()
    db.refresh(db_milestone)
    return get_milestone(db, db_milestone.id)

def delete_milestone(db: Session, milestone_id: int, actor_id: Optional[str] = None):
    db_milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if db_milestone:
        write_audit(db, actor_id, "DELETE", "milestones",
                    resource_id=db_milestone.project_id or milestone_id,
                    record_id=milestone_id,
                    details=[{"field_name": "title", "old_value": db_milestone.title, "new_value": None}])
        db.delete(db_milestone)
        db.commit()
        return True
    return False
