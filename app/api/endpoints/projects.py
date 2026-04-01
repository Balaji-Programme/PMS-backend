from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import (
    allow_authenticated, allow_pm, allow_team_lead_plus, 
    is_employee_only, FULL_ACCESS_ROLES
)
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectUserCreate
from app.schemas.audit import AuditLogResponse
from app.services import project_service

router = APIRouter(dependencies=[Depends(allow_authenticated)])

@router.post("/", response_model=ProjectResponse, dependencies=[Depends(allow_pm)])
def create_project(project: ProjectCreate, db: Session = Depends(get_db), current_user = Depends(allow_pm)):
    """Only Admin and Project Manager can create projects."""
    return project_service.create_project(db=db, project=project, actor_id=current_user.o365_id)

@router.get("/search", response_model=List[ProjectResponse])
def search_projects(
    q: str = Query(..., min_length=1),
    limit: int = 20,
    db: Session = Depends(get_db)
):
    return project_service.search_projects(db, query=q, limit=limit)

@router.get("/", response_model=List[ProjectResponse])
def read_projects(
    skip: int = 0,
    limit: int = 100,
    status_id: Optional[List[int]] = Query(None),
    priority_id: Optional[List[int]] = Query(None),
    manager_email: Optional[List[str]] = Query(None),
    is_archived: bool = Query(False, description="Set to true to list archived projects only"),
    db: Session = Depends(get_db),
    current_user = Depends(allow_authenticated)
):
    """
    List projects. Excludes archived projects by default.
    Pass `?is_archived=true` to retrieve archived projects.
    Employees only see projects they are assigned to.
    """
    projects = project_service.get_projects(
        db,
        skip=skip,
        limit=limit,
        status_ids=status_id,
        priority_ids=priority_id,
        manager_emails=manager_email,
        is_archived=is_archived,
        current_user=current_user if is_employee_only(current_user) else None,
    )
    return projects

@router.get("/{project_id}", response_model=ProjectResponse)
def read_project(project_id: int, db: Session = Depends(get_db), current_user = Depends(allow_authenticated)):
    db_project = project_service.get_project(db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    # Employee can only view projects they are a member of
    if is_employee_only(current_user):
        member_emails = [u.email for u in db_project.users]
        if current_user.email not in member_emails:
            raise HTTPException(status_code=403, detail="Access denied: you are not a member of this project.")
    return db_project

@router.put("/{project_id}", response_model=ProjectResponse, dependencies=[Depends(allow_team_lead_plus)])
def update_project(project_id: int, project: ProjectUpdate, db: Session = Depends(get_db), current_user = Depends(allow_team_lead_plus)):
    """Team Lead and above can update projects."""
    db_project = project_service.update_project(db, project_id=project_id, project_update=project, actor_id=current_user.o365_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

@router.delete("/{project_id}", dependencies=[Depends(allow_pm)])
def delete_project(project_id: int, db: Session = Depends(get_db), current_user = Depends(allow_pm)):
    """Only Admin and Project Manager can hard-delete projects."""
    success = project_service.delete_project(db, project_id=project_id, actor_id=current_user.o365_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted successfully"}


@router.patch("/{project_id}/archive", response_model=ProjectResponse, dependencies=[Depends(allow_pm)])
def archive_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(allow_pm)
):
    """
    Soft-delete: marks the project as archived (is_archived=True).
    Only Admin and Project Manager can archive projects.
    """
    from app.models.project import Project
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    db_project.is_archived = True
    db.commit()
    db.refresh(db_project)
    return project_service.get_project(db, db_project.id)


@router.patch("/{project_id}/unarchive", response_model=ProjectResponse, dependencies=[Depends(allow_pm)])
def unarchive_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(allow_pm)
):
    """Restore a soft-deleted project — sets is_archived=False."""
    from app.models.project import Project
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    db_project.is_archived = False
    db.commit()
    db.refresh(db_project)
    return project_service.get_project(db, db_project.id)


# ─── Assignment Endpoints ─────────────────────────────────────

@router.post("/{project_id}/users", dependencies=[Depends(allow_team_lead_plus)])
def assign_user_to_project(
    project_id: int,
    payload: ProjectUserCreate,
    db: Session = Depends(get_db),
    current_user = Depends(allow_team_lead_plus)
):
    """Team Lead and above can assign users to projects."""
    if payload.project_id != project_id:
        raise HTTPException(status_code=400, detail="project_id in body must match the URL")
    success = project_service.add_user_to_project(
        db,
        project_id=project_id,
        user_id=payload.user_id,
        user_email=payload.user_email,
        display_name=payload.display_name,
        role_id=payload.role_id,
        actor_id=current_user.o365_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Project or User not found")
    return {"message": "User assigned to project successfully"}

@router.post("/{project_id}/users/bulk", dependencies=[Depends(allow_team_lead_plus)])
def bulk_assign_users_to_project(
    project_id: int,
    user_ids: List[int],
    db: Session = Depends(get_db),
    current_user = Depends(allow_team_lead_plus)
):
    """Add multiple system users to a project at once."""
    from app.models.user import User
    from app.models.project import Project
    
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    db_users = db.query(User).filter(User.id.in_(user_ids)).all()
    if len(db_users) != len(user_ids):
        raise HTTPException(status_code=400, detail="Some users were not found in the system")
        
    existing_user_ids = {u.id for u in db_project.users}
    for user in db_users:
        if user.id not in existing_user_ids:
            db_project.users.append(user)
            
    db.commit()
    return {"message": f"{len(db_users)} users assigned to project successfully"}

@router.post("/{project_id}/users/{user_email}", dependencies=[Depends(allow_team_lead_plus)])
def assign_user_to_project_legacy(project_id: int, user_email: str, db: Session = Depends(get_db)):
    """Legacy endpoint: Team Lead and above only."""
    from app.models.user import User
    db_user = db.query(User).filter(User.email == user_email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    success = project_service.add_user_to_project(
        db,
        project_id=project_id,
        user_id=db_user.id,
        user_email=db_user.email,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Project or User not found")
    return {"message": "User assigned to project successfully (legacy support)"}


@router.delete("/{project_id}/users/{user_email}", dependencies=[Depends(allow_team_lead_plus)])
def unassign_user_from_project(project_id: int, user_email: str, db: Session = Depends(get_db), current_user = Depends(allow_team_lead_plus)):
    """Team Lead and above can remove users from projects."""
    success = project_service.remove_user_from_project(db, project_id=project_id, user_email=user_email, actor_id=current_user.o365_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project or User not found")
    return {"message": "User removed from project successfully"}


# ─── Audited Update ─────────────────────────────────────────

@router.put("/{project_id}/audited", response_model=ProjectResponse, dependencies=[Depends(allow_team_lead_plus)])
def update_project_audited(
    project_id: int,
    project_update: ProjectUpdate,
    user_id: str = Query(..., description="Microsoft OID of the acting user"),
    db: Session = Depends(get_db),
):
    from app.models.project import Project
    from app.utils.audit_utils import write_audit, capture_audit_details

    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = project_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    changes = capture_audit_details(db_project, update_data)

    for key, value in update_data.items():
        setattr(db_project, key, value)

    if user_id:
        write_audit(db, user_id, "UPDATE", "projects", project_id, project_id, changes)

    db.commit()
    db.refresh(db_project)

    return project_service.get_project(db, db_project.id)

@router.get("/{project_id}/audit", response_model=List[AuditLogResponse])
def get_project_audit_logs(project_id: int, db: Session = Depends(get_db)):
    """Fetch the full activity timeline for a given project."""
    from app.models.audit import AuditLogs
    
    logs = db.query(AuditLogs).filter(
        AuditLogs.TableName == "projects",
        AuditLogs.Comments.like(f"%Record ID: {project_id}%")
    ).order_by(AuditLogs.PerformedOn.desc()).all()
    
    return logs
