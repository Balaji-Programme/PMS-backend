from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.milestone import Milestone
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate
from app.utils.ids import generate_public_id
from app.utils.audit_utils import capture_audit_details, write_audit

def _milestone_query():
    return (
        select(Milestone)
        .options(
            selectinload(Milestone.project),
            selectinload(Milestone.owner),
        )
    )

async def get_milestone(db: AsyncSession, milestone_id: int) -> Optional[Milestone]:
    result = await db.execute(_milestone_query().where(Milestone.id == milestone_id))
    return result.scalar_one_or_none()

async def get_milestones(
    db: AsyncSession,
    project_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Milestone]:
    stmt = _milestone_query()
    if project_id:
        stmt = stmt.where(Milestone.project_id == project_id)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().unique().all()

async def create_milestone(
    db: AsyncSession,
    milestone: MilestoneCreate,
    actor_id: Optional[str] = None,
) -> Milestone:
    public_id = generate_public_id("MLS-")
    db_milestone = Milestone(
        public_id   = public_id,
        title       = milestone.title,
        description = milestone.description,
        start_date  = milestone.start_date,
        end_date    = milestone.end_date,
        project_id  = milestone.project_id,
        owner_email = milestone.owner_email,
        flags       = milestone.flags,
        tags        = milestone.tags,
    )
    db.add(db_milestone)
    await db.flush()

    await write_audit(
        db, actor_id, "CREATE", "milestones",
        milestone.project_id or db_milestone.id, db_milestone.id,
        [{"field_name": "title", "old_value": None, "new_value": milestone.title}],
    )
    await db.commit()
    return await get_milestone(db, db_milestone.id)

async def update_milestone(
    db: AsyncSession,
    milestone_id: int,
    milestone_update: MilestoneUpdate,
    actor_id: Optional[str] = None,
) -> Optional[Milestone]:
    result = await db.execute(select(Milestone).where(Milestone.id == milestone_id))
    db_milestone = result.scalar_one_or_none()
    if not db_milestone:
        return None

    update_data = milestone_update.model_dump(exclude_unset=True)
    changes = capture_audit_details(db_milestone, update_data)
    for key, value in update_data.items():
        setattr(db_milestone, key, value)

    await write_audit(
        db, actor_id, "UPDATE", "milestones",
        db_milestone.project_id or milestone_id, milestone_id, changes,
    )
    await db.commit()
    return await get_milestone(db, milestone_id)

async def delete_milestone(
    db: AsyncSession,
    milestone_id: int,
    actor_id: Optional[str] = None,
) -> bool:
    result = await db.execute(select(Milestone).where(Milestone.id == milestone_id))
    db_milestone = result.scalar_one_or_none()
    if not db_milestone:
        return False
    await write_audit(
        db, actor_id, "DELETE", "milestones",
        db_milestone.project_id or milestone_id, milestone_id,
        [{"field_name": "title", "old_value": db_milestone.title, "new_value": None}],
    )
    await db.delete(db_milestone)
    await db.commit()
    return True
