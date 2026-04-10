from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.issue import Issue
from app.models.document import Document
from app.models.user import User
from app.schemas.issue import IssueCreate, IssueUpdate
from app.utils.ids import generate_public_id
from app.utils.audit_utils import capture_audit_details, write_audit

def _issue_query():
    return (
        select(Issue)
        .options(
            selectinload(Issue.project),
            selectinload(Issue.reporter),
            selectinload(Issue.assignee),
            selectinload(Issue.assignees),
            selectinload(Issue.followers),
            selectinload(Issue.status),
            selectinload(Issue.priority),
            selectinload(Issue.documents),
        )
    )

async def get_issue(db: AsyncSession, issue_id: int) -> Optional[Issue]:
    result = await db.execute(_issue_query().where(Issue.id == issue_id))
    return result.scalar_one_or_none()

async def get_issues(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    project_id: Optional[int] = None,
    status_ids: Optional[List[int]] = None,
    priority_ids: Optional[List[int]] = None,
    assignee_emails: Optional[List[str]] = None,
) -> dict:
    stmt = _issue_query()

    if project_id is not None:
        stmt = stmt.where(Issue.project_id == project_id)
    if status_ids:
        stmt = stmt.where(Issue.status_id.in_(status_ids))
    if priority_ids:
        stmt = stmt.where(Issue.priority_id.in_(priority_ids))
    if assignee_emails:
        stmt = stmt.where(Issue.assignee_email.in_(assignee_emails))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0
    items_result = await db.execute(stmt.offset(skip).limit(limit))
    return {"total": total, "items": items_result.scalars().unique().all()}

async def create_issue(
    db: AsyncSession,
    issue: IssueCreate,
    actor_id: Optional[str] = None,
) -> Issue:
    public_id = generate_public_id("ISS-")
    db_issue = Issue(
        public_id      = public_id,
        title          = issue.title,
        description    = issue.description,
        project_id     = issue.project_id,
        reporter_email = issue.reporter_email,
        assignee_email = issue.assignee_email,
        status_id      = issue.status_id,
        priority_id    = issue.priority_id,
        classification = issue.classification,
        module         = issue.module,
        tags           = issue.tags,
        start_date     = issue.start_date,
        end_date       = issue.end_date,
        due_date       = issue.due_date,
        estimated_hours = issue.estimated_hours,
    )

    if issue.follower_ids:
        followers = (await db.execute(select(User).where(User.id.in_(issue.follower_ids)))).scalars().all()
        db_issue.followers.extend(followers)
    if getattr(issue, "assignee_ids", None):
        assignees = (await db.execute(select(User).where(User.id.in_(issue.assignee_ids)))).scalars().all()
        db_issue.assignees.extend(assignees)
    if getattr(issue, "document_ids", None):
        docs = (await db.execute(select(Document).where(Document.id.in_(issue.document_ids)))).scalars().all()
        db_issue.documents.extend(docs)

    db.add(db_issue)
    await db.flush()

    await write_audit(
        db, actor_id, "CREATE", "issues",
        issue.project_id or db_issue.id, db_issue.id,
        [{"field_name": "title", "old_value": None, "new_value": issue.title}],
    )
    await db.commit()
    return await get_issue(db, db_issue.id)

async def update_issue(
    db: AsyncSession,
    issue_id: int,
    issue_update: IssueUpdate,
    actor_id: Optional[str] = None,
) -> Optional[Issue]:
    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    db_issue = result.scalar_one_or_none()
    if not db_issue:
        return None

    update_data = issue_update.model_dump(
        exclude_unset=True, exclude={"document_ids", "follower_ids", "assignee_ids"}
    )
    changes = capture_audit_details(db_issue, update_data)
    for key, value in update_data.items():
        setattr(db_issue, key, value)

    if issue_update.follower_ids is not None:
        db_issue.followers = list(
            (await db.execute(select(User).where(User.id.in_(issue_update.follower_ids)))).scalars().all()
        )
    if issue_update.assignee_ids is not None:
        db_issue.assignees = list(
            (await db.execute(select(User).where(User.id.in_(issue_update.assignee_ids)))).scalars().all()
        )
    if issue_update.document_ids is not None:
        db_issue.documents = list(
            (await db.execute(select(Document).where(Document.id.in_(issue_update.document_ids)))).scalars().all()
        )

    await write_audit(db, actor_id, "UPDATE", "issues", db_issue.project_id or issue_id, issue_id, changes)
    await db.commit()
    return await get_issue(db, issue_id)

async def delete_issue(
    db: AsyncSession,
    issue_id: int,
    actor_id: Optional[str] = None,
) -> bool:
    result = await db.execute(select(Issue).where(Issue.id == issue_id))
    db_issue = result.scalar_one_or_none()
    if not db_issue:
        return False
    await write_audit(
        db, actor_id, "DELETE", "issues",
        db_issue.project_id or issue_id, issue_id,
        [{"field_name": "title", "old_value": db_issue.title, "new_value": None}],
    )
    await db.delete(db_issue)
    await db.commit()
    return True

async def search_issues(
    db: AsyncSession,
    query: str,
    project_id: Optional[int] = None,
    limit: int = 20,
) -> List[Issue]:
    if not query:
        return []
    q = f"%{query}%"
    stmt = _issue_query().where(or_(Issue.title.ilike(q), Issue.public_id.ilike(q)))
    if project_id:
        stmt = stmt.where(Issue.project_id == project_id)
    result = await db.execute(stmt.limit(limit))
    return result.scalars().unique().all()
