from __future__ import annotations

from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.task import Task
from app.models.issue import Issue

class SearchService:

    def global_search(
        self,
        db: Session,
        query: str,
        limit: int = 15,
    ) -> List[dict]:
        if not query:
            return []

        q = f"%{query}%"
        search_results: List[dict] = []

        projects = (
            db.execute(
                select(Project).where(
                    or_(Project.project_name.ilike(q), Project.public_id.ilike(q), Project.client_name.ilike(q))
                ).limit(limit)
            )
        ).scalars().all()
        search_results.extend(
            {"type": "project", "id": p.public_id, "title": p.project_name, "project_name": p.project_name, "path": f"/projects/{p.id}"}
            for p in projects
        )

        tasks = (
            db.execute(
                select(Task).where(or_(Task.task_name.ilike(q), Task.public_id.ilike(q))).limit(limit)
            )
        ).scalars().all()
        search_results.extend(
            {"type": "task", "id": t.public_id, "title": t.task_name, "path": f"/tasks/{t.id}"}
            for t in tasks
        )

        issues = (
            db.execute(
                select(Issue).where(or_(Issue.bug_name.ilike(q), Issue.public_id.ilike(q))).limit(limit)
            )
        ).scalars().all()
        search_results.extend(
            {"type": "issue", "id": i.public_id, "title": i.bug_name, "path": f"/issues/{i.id}"}
            for i in issues
        )

        return search_results

    def search_work_items(
        self,
        db: Session,
        query: str = "",
        project_id: Optional[int] = None,
        limit: int = 20,
    ) -> List[dict]:
        search_results: List[dict] = []
        task_stmt  = select(Task)
        issue_stmt = select(Issue)

        if query:
            q = f"%{query}%"
            task_stmt  = task_stmt.where(or_(Task.task_name.ilike(q),  Task.public_id.ilike(q)))
            issue_stmt = issue_stmt.where(or_(Issue.bug_name.ilike(q), Issue.public_id.ilike(q)))
        if project_id:
            task_stmt  = task_stmt.where(Task.project_id  == project_id)
            issue_stmt = issue_stmt.where(Issue.project_id == project_id)

        tasks  = (db.execute(task_stmt.limit(limit))).scalars().all()
        issues = (db.execute(issue_stmt.limit(limit))).scalars().all()

        search_results.extend(
            {"type": "task",  "id": t.id, "public_id": t.public_id, "name": t.task_name, "title": t.task_name}
            for t in tasks
        )
        search_results.extend(
            {"type": "issue", "id": i.id, "public_id": i.public_id, "name": f"[Issue] {i.bug_name}", "title": i.bug_name}
            for i in issues
        )
        return search_results

search_service = SearchService()
