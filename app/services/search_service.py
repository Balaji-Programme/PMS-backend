from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.project import Project
from app.models.task import Task
from app.models.issue import Issue

class SearchService:
    def global_search(self, db: Session, query: str, limit: int = 15):
        if not query:
            return []
        
        search_results = []
        q = f"%{query}%"

        projects = db.query(Project).filter(
            or_(
                Project.name.ilike(q),
                Project.public_id.ilike(q),
                Project.client.ilike(q)
            )
        ).limit(limit).all()
        
        for p in projects:
            search_results.append({
                "type": "project",
                "id": p.public_id,
                "title": p.name,
                "path": f"/projects/{p.id}"
            })

        tasks = db.query(Task).filter(
            or_(
                Task.title.ilike(q),
                Task.public_id.ilike(q)
            )
        ).limit(limit).all()
        
        for t in tasks:
            search_results.append({
                "type": "task",
                "id": t.public_id,
                "title": t.title,
                "path": f"/tasks/{t.id}"
            })

        issues = db.query(Issue).filter(
            or_(
                Issue.title.ilike(q),
                Issue.public_id.ilike(q)
            )
        ).limit(limit).all()
        
        for i in issues:
            search_results.append({
                "type": "issue",
                "id": i.public_id,
                "title": i.title,
                "path": f"/issues/{i.id}"
            })

        return search_results

    def search_work_items(self, db: Session, query: str = "", project_id: int = None, limit: int = 20):
        search_results = []
        
        task_filters = []
        issue_filters = []

        if query:
            q = f"%{query}%"
            task_filters.append(or_(Task.title.ilike(q), Task.public_id.ilike(q)))
            issue_filters.append(or_(Issue.title.ilike(q), Issue.public_id.ilike(q)))

        if project_id:
            task_filters.append(Task.project_id == project_id)
            issue_filters.append(Issue.project_id == project_id)

        tasks = db.query(Task).filter(*task_filters).limit(limit).all()
        for t in tasks:
            search_results.append({
                "type": "task",
                "id": t.id,
                "public_id": t.public_id,
                "name": t.title, # Use 'name' for dropdown compatibility
                "title": t.title
            })

        issues = db.query(Issue).filter(*issue_filters).limit(limit).all()
        for i in issues:
            search_results.append({
                "type": "issue",
                "id": i.id,
                "public_id": i.public_id,
                "name": f"[Issue] {i.title}", # Prefixing to distinguish
                "title": i.title
            })

        return search_results

search_service = SearchService()
