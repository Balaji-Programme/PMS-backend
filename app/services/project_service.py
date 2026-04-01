from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.utils.ids import generate_public_id
from app.utils.audit_utils import capture_audit_details, write_audit

def get_project(db: Session, project_id: int):
    return db.query(Project).options(
        joinedload(Project.manager),
        joinedload(Project.creator),
        joinedload(Project.status),
        joinedload(Project.priority),
        joinedload(Project.users)
    ).filter(Project.id == project_id).first()

def get_projects(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    status_ids: Optional[List[int]] = None,
    priority_ids: Optional[List[int]] = None,
    manager_emails: Optional[List[str]] = None,
    current_user=None,
    **kwargs
):
    from app.models.project import project_users as pu_table
    query = db.query(Project).options(
        joinedload(Project.manager),
        joinedload(Project.creator),
        joinedload(Project.status),
        joinedload(Project.priority)
    )
    
    # Employee isolation: only show projects they are assigned to
    if current_user is not None:
        query = query.join(pu_table, pu_table.c.project_id == Project.id).filter(
            pu_table.c.user_id == current_user.id
        )

    if status_ids:
        query = query.filter(Project.status_id.in_(status_ids))
    if priority_ids:
        query = query.filter(Project.priority_id.in_(priority_ids))
    if manager_emails:
        query = query.filter(Project.manager_email.in_(manager_emails))
        
    return query.offset(skip).limit(limit).all()

def create_project(db: Session, project: ProjectCreate, actor_id: str):
    public_id = generate_public_id("PRJ-")
    db_project = Project(
        public_id=public_id,
        name=project.name,
        description=project.description,
        client=project.client,
        manager_email=project.manager_email,
        status_id=project.status_id,
        priority_id=project.priority_id,
        start_date=project.start_date,
        end_date=project.end_date,
        estimated_hours=project.estimated_hours
    )
    if project.user_ids:
        users = db.query(User).filter(User.id.in_(project.user_ids)).all()
        db_project.users = users

    db.add(db_project)
    db.flush() # Get ID for audit log

    write_audit(
        db,
        actor_id,
        "CREATE",
        "projects",
        db_project.id,
        db_project.id,
        [{"field_name": "name", "old_value": None, "new_value": project.name}]
    )

    db.commit()
    db.refresh(db_project)

    return get_project(db, db_project.id)

def update_project(db: Session, project_id: int, project_update: ProjectUpdate, actor_id: str):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        return None
    
    update_data = project_update.model_dump(exclude_unset=True)
    if not update_data:
        return db_project

    # Logic for previous_status - store the status_id (integer) so data types match
    if "status_id" in update_data and update_data["status_id"] != db_project.status_id:
        update_data["previous_status"] = db_project.status_id  # store old integer FK value

    # Capture diff explicitly BEFORE mutation
    changes = capture_audit_details(db_project, update_data)

    for key, value in update_data.items():
        setattr(db_project, key, value)
    
    if hasattr(project_update, 'user_ids') and project_update.user_ids is not None:
        users = db.query(User).filter(User.id.in_(project_update.user_ids)).all()
        db_project.users = users
        
    if actor_id:
        write_audit(db, actor_id, "UPDATE", "projects", project_id, project_id, changes)

    db.commit()
    db.refresh(db_project)
    
    return get_project(db, db_project.id)

def delete_project(db: Session, project_id: int, actor_id: str):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if db_project:
        db.delete(db_project)
        if actor_id:
            write_audit(db, actor_id, "DELETE", "projects", project_id, project_id, [])
        db.commit()
        return True
    return False

def add_user_to_project(db: Session, project_id: int, user_id: str, user_email: str, display_name: Optional[str] = None, role_id: Optional[int] = None, actor_id: Optional[str] = None):
    """Assign a user to a project, implementing JIT provisioning if they don't exist locally."""
    from sqlalchemy import insert, select
    from app.models.project import project_users
    from app.models.user import User
    from app.models.roles import Role
    from app.utils.ids import generate_public_id

    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        return False

    # --- JIT Provisioning (Identity Bridge) ---
    db_user = db.query(User).filter(User.o365_id == user_id).first()
    if not db_user:
        # Fallback: check by email in case of legacy user missing OID mapping
        db_user = db.query(User).filter(User.email == user_email).first()
        if db_user:
            db_user.o365_id = user_id
            db.commit()
        else:
            # Create completely new user from MSAL claims
            public_id = generate_public_id("USR-")
            employee_id = generate_public_id("EMP-")
            
            name_parts = (display_name or "New User").split(" ", 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else "User"

            db_user = User(
                public_id=public_id,
                employee_id=employee_id,
                o365_id=user_id,
                email=user_email,
                username=user_email.split("@")[0],
                first_name=first_name,
                last_name=last_name,
                display_name=display_name or f"{first_name} {last_name}",
                is_synced=True
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)

    # Check if already assigned using local Integer ID
    existing = db.execute(
        select(project_users).where(
            project_users.c.project_id == project_id,
            project_users.c.user_id == db_user.id,
        )
    ).first()

    if existing:
        return True  # Already assigned — idempotent

    db.execute(
        insert(project_users).values(
            project_id=project_id,
            user_id=db_user.id,
            user_email=user_email,
            role_id=role_id,
        )
    )

    # Always write audit log — fall back to stringified int id if o365_id not set
    effective_actor_id = actor_id or "system"

    # Resolve actor display name
    actor = db.query(User).filter(
        (User.o365_id == actor_id) if actor_id else (User.id == -1)  # no-match if no actor_id
    ).first()
    actor_name = actor.display_name if actor else "Admin"

    role_label = db.query(Role).filter(Role.id == role_id).first().name if role_id else "Member"
    write_audit(
        db,
        effective_actor_id,
        "ASSIGN_TO_PROJECT",
        "projects",
        project_id,
        db_user.id,
        [{"field_name": "project_users", "old_value": None, "new_value": f"Added {user_email} as {role_label} by {actor_name}"}]
    )

    db.commit()
    return True

def remove_user_from_project(db: Session, project_id: int, user_email: str, actor_id: Optional[str] = None):
    """
    Remove a user from a project by their email.
    """
    from sqlalchemy import delete as sa_delete
    from app.models.project import project_users
    from app.models.user import User

    db_user = db.query(User).filter(User.email == user_email).first()
    if not db_user:
        return False  # User doesn't exist at all

    result = db.execute(
        sa_delete(project_users).where(
            project_users.c.project_id == project_id,
            project_users.c.user_id == db_user.id,
        )
    )
    if result.rowcount > 0:
        effective_actor_id = actor_id or "system"
        write_audit(
            db,
            effective_actor_id,
            "REMOVE_FROM_PROJECT",
            "projects",
            project_id,
            db_user.id,
            [{"field_name": "project_users", "old_value": user_email, "new_value": None}]
        )
    db.commit()
    return result.rowcount > 0

def search_projects(db: Session, query: str, limit: int = 20):
    if not query:
        return []
    q = f"%{query}%"
    from sqlalchemy import or_
    return db.query(Project).options(
        joinedload(Project.manager),
        joinedload(Project.status),
        joinedload(Project.priority)
    ).filter(
        or_(
            Project.name.ilike(q),
            Project.public_id.ilike(q),
            Project.client.ilike(q)
        )
    ).limit(limit).all()
