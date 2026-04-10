from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.template import ProjectTemplate, TemplateTask
from app.schemas.template import ProjectTemplateCreate

async def get_templates(db: AsyncSession) -> List[ProjectTemplate]:
    result = await db.execute(
        select(ProjectTemplate)
        .options(selectinload(ProjectTemplate.tasks))
        .where(ProjectTemplate.is_deleted == False)  
        .order_by(ProjectTemplate.name)
    )
    return result.scalars().all()

async def get_template(db: AsyncSession, template_id: int) -> Optional[ProjectTemplate]:
    result = await db.execute(
        select(ProjectTemplate)
        .options(selectinload(ProjectTemplate.tasks))
        .where(ProjectTemplate.id == template_id)
    )
    return result.scalar_one_or_none()

async def create_template(
    db: AsyncSession,
    data: ProjectTemplateCreate,
    created_by_id: Optional[int] = None,
) -> ProjectTemplate:
    db_template = ProjectTemplate(
        name          = data.name,
        description   = data.description,
        created_by_id = created_by_id,
    )
    db.add(db_template)
    await db.flush()

    if data.tasks:
        db.add_all([
            TemplateTask(
                template_id     = db_template.id,
                title           = t.title,
                description     = t.description,
                estimated_hours = t.estimated_hours,
                priority_id     = t.priority_id,
                order_index     = t.order_index,
            )
            for t in data.tasks
        ])
        await db.flush()

    await db.commit()
    return await get_template(db, db_template.id)

async def delete_template(db: AsyncSession, template_id: int) -> bool:
    template = await get_template(db, template_id)
    if not template:
        return False
    await db.delete(template)
    await db.commit()
    return True
