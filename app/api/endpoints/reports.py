from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.core.database import get_db
from app.core.security import allow_authenticated
from app.models.project import Project
from app.models.task import Task
from app.models.issue import Issue
from app.models.timelog import TimeLog
from app.models.milestone import Milestone
from app.models.masters import Status
import csv
import io

router = APIRouter(dependencies=[Depends(allow_authenticated)])

@router.get("/summary")
def get_report_summary(db: Session = Depends(get_db)):
    # ── Projects: total + active in 1 query ─────────────────────────────────
    proj_row = db.query(
        func.count(Project.id).label("total"),
        func.sum(
            case(
                (Status.name.notin_(["Completed", "Closed"]), 1),
                else_=0,
            )
        ).label("active")
    ).outerjoin(Status, Project.status_id == Status.id).one()

    # ── Tasks: total + completed in 1 query ──────────────────────────────────
    task_row = db.query(
        func.count(Task.id).label("total"),
        func.sum(
            case(
                (Status.name == "Completed", 1),
                else_=0,
            )
        ).label("completed")
    ).outerjoin(Status, Task.status_id == Status.id).one()

    # ── Issues: total + open in 1 query ──────────────────────────────────────
    issue_row = db.query(
        func.count(Issue.id).label("total"),
        func.sum(
            case(
                (Status.name.notin_(["Completed", "Closed", "Resolved"]), 1),
                else_=0,
            )
        ).label("open")
    ).outerjoin(Status, Issue.status_id == Status.id).one()

    total_hours_logged = db.query(func.sum(TimeLog.hours)).scalar() or 0.0
    total_milestones   = db.query(func.count(Milestone.id)).scalar() or 0

    return {
        "total_projects":    proj_row.total  or 0,
        "active_projects":   proj_row.active or 0,
        "total_tasks":       task_row.total  or 0,
        "completed_tasks":   task_row.completed or 0,
        "total_issues":      issue_row.total or 0,
        "open_issues":       issue_row.open  or 0,
        "total_hours_logged": float(total_hours_logged),
        "total_milestones":  total_milestones,
    }

@router.get("/project/{project_id}")
def get_project_report(project_id: int, db: Session = Depends(get_db)):
    from app.models.user import User
    from app.models.masters import Priority

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"error": "Project not found"}

    # ── Task counts by status ─────────────────────────────────────────────────
    task_rows = (
        db.query(Status.name, func.count(Task.id))
        .join(Status, Task.status_id == Status.id)
        .filter(Task.project_id == project_id)
        .group_by(Status.name)
        .all()
    )
    tasks_by_status  = [{"status": r[0], "count": r[1]} for r in task_rows]
    total_tasks      = sum(r["count"] for r in tasks_by_status)
    completed_tasks  = sum(r["count"] for r in tasks_by_status if r["status"] == "Completed")

    # ── Issue counts by priority ──────────────────────────────────────────────
    issue_rows = (
        db.query(Priority.name, func.count(Issue.id))
        .join(Priority, Issue.priority_id == Priority.id)
        .filter(Issue.project_id == project_id)
        .group_by(Priority.name)
        .all()
    )
    issues_by_priority = [{"priority": r[0], "count": r[1]} for r in issue_rows]
    total_issues       = sum(r["count"] for r in issues_by_priority)

    open_issues_count = (
        db.query(func.count(Issue.id))
        .join(Status, Issue.status_id == Status.id)
        .filter(Issue.project_id == project_id, Status.name.notin_(["Closed", "Resolved"]))
        .scalar() or 0
    )

    # ── Hours by user — single aggregation query, then 1 batch user lookup ───
    hours_rows = (
        db.query(TimeLog.user_email, func.sum(TimeLog.hours).label("total_hours"))
        .filter(TimeLog.project_id == project_id)
        .group_by(TimeLog.user_email)
        .order_by(func.sum(TimeLog.hours).desc())
        .limit(10)
        .all()
    )

    # Batch-fetch all relevant users in ONE query (fixes N+1)
    emails = [row.user_email for row in hours_rows]
    users_map = {}
    if emails:
        user_records = db.query(User.email, User.first_name, User.last_name).filter(User.email.in_(emails)).all()
        users_map = {u.email: f"{u.first_name} {u.last_name}".strip() for u in user_records}

    hours_by_user = [
        {
            "email": row.user_email,
            "name":  users_map.get(row.user_email, row.user_email),
            "hours": float(row.total_hours or 0),
        }
        for row in hours_rows
    ]
    total_hours = sum(r["hours"] for r in hours_by_user)

    # ── Milestones ─────────────────────────────────────────────────────────────
    total_milestones = db.query(func.count(Milestone.id)).filter(Milestone.project_id == project_id).scalar() or 0

    return {
        "project_id":         project_id,
        "project_name":       project.name,
        "total_tasks":        total_tasks,
        "completed_tasks":    completed_tasks,
        "total_issues":       total_issues,
        "open_issues":        open_issues_count,
        "total_milestones":   total_milestones,
        "total_hours_logged": total_hours,
        "tasks_by_status":    tasks_by_status,
        "issues_by_priority": issues_by_priority,
        "hours_by_user":      hours_by_user,
    }


@router.get("/export/csv")
def export_csv_report(report_type: str = "projects", db: Session = Depends(get_db)):

    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == "projects":
        writer.writerow(["ID", "Name", "Client", "Start Date", "End Date", "Estimated Hours"])
        for p in db.query(Project).all():
            writer.writerow([p.public_id, p.name, p.client or "", str(p.start_date or ""), str(p.end_date or ""), p.estimated_hours or 0])
    elif report_type == "tasks":
        writer.writerow(["ID", "Title", "Project ID", "Start Date", "End Date", "Estimated Hours"])
        for t in db.query(Task).all():
            writer.writerow([t.public_id, t.title, t.project_id, str(t.start_date or ""), str(t.end_date or ""), t.estimated_hours or 0])
    elif report_type == "issues":
        writer.writerow(["ID", "Title", "Project ID", "Start Date", "End Date", "Estimated Hours"])
        for i in db.query(Issue).all():
            writer.writerow([i.public_id, i.title, i.project_id, str(i.start_date or ""), str(i.end_date or ""), i.estimated_hours or 0])
    elif report_type == "timelogs":
        writer.writerow(["ID", "User Email", "Task ID", "Date", "Hours", "Description"])
        for tl in db.query(TimeLog).all():
            writer.writerow([tl.id, tl.user_email, tl.task_id, str(tl.date or ""), tl.hours, tl.description or ""])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report_type}_report.csv"}
    )


