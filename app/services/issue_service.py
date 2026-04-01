from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.issue import Issue
from app.models.document import Document
from app.models.user import User
from app.schemas.issue import IssueCreate, IssueUpdate
from app.utils.ids import generate_public_id
from app.utils.audit_utils import write_audit, capture_audit_details

def get_issue(db: Session, issue_id: int):
    return db.query(Issue).options(
        joinedload(Issue.project),
        joinedload(Issue.reporter),
        joinedload(Issue.assignee),
        joinedload(Issue.assignees),
        joinedload(Issue.followers),
        joinedload(Issue.status),
        joinedload(Issue.priority),
        joinedload(Issue.documents)
    ).filter(Issue.id == issue_id).first()

def get_issues(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    project_id: int = None,
    status_ids: Optional[List[int]] = None,
    priority_ids: Optional[List[int]] = None,
    assignee_emails: Optional[List[str]] = None
):
    query = db.query(Issue).options(
        joinedload(Issue.project),
        joinedload(Issue.reporter),
        joinedload(Issue.assignee),
        joinedload(Issue.assignees),
        joinedload(Issue.followers),
        joinedload(Issue.status),
        joinedload(Issue.priority),
        joinedload(Issue.documents)
    )
    if project_id is not None:
        query = query.filter(Issue.project_id == project_id)
    if status_ids:
        query = query.filter(Issue.status_id.in_(status_ids))
    if priority_ids:
        query = query.filter(Issue.priority_id.in_(priority_ids))
    if assignee_emails:
        query = query.filter(Issue.assignee_email.in_(assignee_emails))
        
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return {"total": total, "items": items}

def create_issue(db: Session, issue: IssueCreate, actor_id: Optional[str] = None):
    public_id = generate_public_id("ISS-")
    db_issue = Issue(
        public_id=public_id,
        title=issue.title,
        description=issue.description,
        project_id=issue.project_id,
        reporter_email=issue.reporter_email,
        assignee_email=issue.assignee_email,
        status_id=issue.status_id,
        priority_id=issue.priority_id,
        classification=issue.classification,
        module=issue.module,
        tags=issue.tags,
        start_date=issue.start_date,
        end_date=issue.end_date,
        due_date=issue.due_date,
        estimated_hours=issue.estimated_hours
    )
    
    if issue.follower_ids:
        followers = db.query(User).filter(User.id.in_(issue.follower_ids)).all()
        db_issue.followers.extend(followers)
    
    if hasattr(issue, 'assignee_ids') and issue.assignee_ids:
        assignees = db.query(User).filter(User.id.in_(issue.assignee_ids)).all()
        db_issue.assignees.extend(assignees)
    
    if hasattr(issue, 'document_ids') and issue.document_ids:
        docs = db.query(Document).filter(Document.id.in_(issue.document_ids)).all()
        db_issue.documents.extend(docs)

    db.add(db_issue)
    db.flush()

    write_audit(db, actor_id, "CREATE", "issues",
                resource_id=issue.project_id or db_issue.id,
                record_id=db_issue.id,
                details=[{"field_name": "title", "old_value": None, "new_value": issue.title}])

    db.commit()
    db.refresh(db_issue)
    return get_issue(db, db_issue.id)

def update_issue(db: Session, issue_id: int, issue_update: IssueUpdate, actor_id: Optional[str] = None):
    db_issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not db_issue:
        return None
    
    update_data = issue_update.model_dump(exclude_unset=True, exclude={'document_ids', 'follower_ids', 'assignee_ids'})
    changes = capture_audit_details(db_issue, update_data)

    for key, value in update_data.items():
        setattr(db_issue, key, value)
        
    if hasattr(issue_update, 'follower_ids') and issue_update.follower_ids is not None:
        followers = db.query(User).filter(User.id.in_(issue_update.follower_ids)).all()
        db_issue.followers = followers
        
    if hasattr(issue_update, 'assignee_ids') and issue_update.assignee_ids is not None:
        assignees = db.query(User).filter(User.id.in_(issue_update.assignee_ids)).all()
        db_issue.assignees = assignees
        
    if hasattr(issue_update, 'document_ids') and issue_update.document_ids is not None:
        docs = db.query(Document).filter(Document.id.in_(issue_update.document_ids)).all()
        db_issue.documents = docs

    write_audit(db, actor_id, "UPDATE", "issues",
                resource_id=db_issue.project_id or issue_id,
                record_id=issue_id,
                details=changes)

    db.commit()
    db.refresh(db_issue)
    return get_issue(db, db_issue.id)

def delete_issue(db: Session, issue_id: int, actor_id: Optional[str] = None):
    db_issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if db_issue:
        write_audit(db, actor_id, "DELETE", "issues",
                    resource_id=db_issue.project_id or issue_id,
                    record_id=issue_id,
                    details=[{"field_name": "title", "old_value": db_issue.title, "new_value": None}])
        db.delete(db_issue)
        db.commit()
        return True
    return False

def search_issues(db: Session, query: str, project_id: int = None, limit: int = 20):
    if not query:
        return []
    q = f"%{query}%"
    from sqlalchemy import or_
    query_obj = db.query(Issue).options(
        joinedload(Issue.project),
        joinedload(Issue.reporter),
        joinedload(Issue.assignee),
        joinedload(Issue.status),
        joinedload(Issue.documents)
    )
    if project_id:
        query_obj = query_obj.filter(Issue.project_id == project_id)
    
    return query_obj.filter(
        or_(
            Issue.title.ilike(q),
            Issue.public_id.ilike(q)
        )
    ).limit(limit).all()
