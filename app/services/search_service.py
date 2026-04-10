from __future__ import annotations

from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.task import Task
from app.models.issue import Issue

class SearchService:

    async def global_search(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 15,
    ) -> List[dict]:
        if not query:
            return []

        q = f"%{query}%"
        search_results: List[dict] = []

        projects = (
            await db.execute(
                select(Project).where(
                    or_(Project.name.ilike(q), Project.public_id.ilike(q), Project.client.ilike(q))
                ).limit(limit)
            )
        ).scalars().all()
        search_results.extend(
            {"type": "project", "id": p.public_id, "title": p.name, "path": f"/projects/{p.id}"}
            for p in projects
        )

        tasks = (
            await db.execute(
                select(Task).where(or_(Task.title.ilike(q), Task.public_id.ilike(q))).limit(limit)
            )
        ).scalars().all()
        search_results.extend(
            {"type": "task", "id": t.public_id, "title": t.title, "path": f"/tasks/{t.id}"}
            for t in tasks
        )

        issues = (
            await db.execute(
                select(Issue).where(or_(Issue.title.ilike(q), Issue.public_id.ilike(q))).limit(limit)
            )
        ).scalars().all()
        search_results.extend(
            {"type": "issue", "id": i.public_id, "title": i.title, "path": f"/issues/{i.id}"}
            for i in issues
        )

        return search_results

    async def search_work_items(
        self,
        db: AsyncSession,
        query: str = "",
        project_id: Optional[int] = None,
        limit: int = 20,
    ) -> List[dict]:
        search_results: List[dict] = []
        task_stmt  = select(Task)
        issue_stmt = select(Issue)

        if query:
            q = f"%{query}%"
            task_stmt  = task_stmt.where(or_(Task.title.ilike(q),  Task.public_id.ilike(q)))
            issue_stmt = issue_stmt.where(or_(Issue.title.ilike(q), Issue.public_id.ilike(q)))
        if project_id:
            task_stmt  = task_stmt.where(Task.project_id  == project_id)
            issue_stmt = issue_stmt.where(Issue.project_id == project_id)

        tasks  = (await db.execute(task_stmt.limit(limit))).scalars().all()
        issues = (await db.execute(issue_stmt.limit(limit))).scalars().all()

        search_results.extend(
            {"type": "task",  "id": t.id, "public_id": t.public_id, "name": t.title, "title": t.title}
            for t in tasks
        )
        search_results.extend(
            {"type": "issue", "id": i.id, "public_id": i.public_id, "name": f"[Issue] {i.title}", "title": i.title}
            for i in issues
        )
        return search_results

search_service = SearchService()
