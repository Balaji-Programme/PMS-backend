from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project, ProjectMember
from app.models.user import User
from app.models.template import ProjectTemplate, TemplateTask
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectSyncUpdate
from app.utils.ids import generate_public_id
from app.utils.audit_utils import capture_audit_details, write_audit

def _project_query(extra_options=()):
    return (
        select(Project)
        .options(
            selectinload(Project.owner),
            selectinload(Project.project_manager),
            selectinload(Project.delivery_head),
            selectinload(Project.source_template),
            selectinload(Project.team_members).selectinload(ProjectMember.user),
            *extra_options,
        )
    )

async def get_project(db: AsyncSession, project_id: int) -> Optional[Project]:
    result = await db.execute(_project_query().where(Project.id == project_id))
    return result.scalar_one_or_none()

async def get_projects(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    is_archived: Optional[bool] = None,
    is_template: Optional[bool] = None,
    include_all: bool = False,
    current_user=None,
) -> List[Project]:
    stmt = _project_query()

    if current_user is not None:
        stmt = stmt.join(ProjectMember, ProjectMember.project_id == Project.id).where(
            ProjectMember.user_id == current_user.id
        )

    if not include_all:
        if is_archived is not None:
            stmt = stmt.where(Project.is_archived == is_archived)
        if is_template is not None:
            stmt = stmt.where(Project.is_template == is_template)

    if status:
        stmt = stmt.where(Project.status == status)
    if priority:
        stmt = stmt.where(Project.priority == priority)

    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().unique().all()

async def create_project(
    db: AsyncSession,
    project: ProjectCreate,
    actor_id: str,
) -> Project:
    public_id = generate_public_id("PRJ-")

    db_project = Project(
        public_id               = public_id,
        project_name            = project.project_name,
        account_name            = project.account_name,
        customer_name           = project.customer_name,
        client_name             = project.client_name,
        project_id_sync         = project.project_id_sync,
        description             = project.description,
        billing_model           = project.billing_model,
        project_type            = project.project_type,
        project_status_external = project.project_status_external,
        project_manager_id      = project.project_manager_id,
        delivery_head_id        = project.delivery_head_id,
        owner_id                = project.owner_id,
        template_id             = project.template_id,
        status                  = project.status,
        priority                = project.priority,
        expected_start_date     = project.expected_start_date,
        expected_end_date       = project.expected_end_date,
        estimated_hours         = project.estimated_hours,
        actual_start_date       = project.actual_start_date,
        actual_end_date         = project.actual_end_date,
        actual_hours            = project.actual_hours,
        is_archived             = project.is_archived,
        is_template             = project.is_template,
        is_group                = project.is_group,
    )
    
    db.add(db_project)
    await db.flush()

    if project.template_id:
        await clone_from_template(db, db_project.id, project.template_id)

    if project.user_emails:
        users_result = await db.execute(select(User).where(User.email.in_(project.user_emails)))
        for u in users_result.scalars().all():
            db.add(ProjectMember(project_id=db_project.id, user_id=u.id, project_profile="Member", portal_profile="User"))

    await db.commit()
    return await get_project(db, db_project.id)

async def clone_from_template(
    db: AsyncSession,
    project_id: int,
    template_id: int,
) -> None:
    from app.models.task import Task
    tmpl_tasks_result = await db.execute(
        select(TemplateTask)
        .where(TemplateTask.template_id == template_id)
        .order_by(TemplateTask.order_index)
    )
    for tt in tmpl_tasks_result.scalars().all():
        db.add(Task(
            public_id       = generate_public_id("TSK-"),
            task_name       = tt.title,
            description     = tt.description,
            project_id      = project_id,
            estimated_hours = tt.estimated_hours,
            priority        = "Medium",
        ))
    await db.flush()
