from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.core.database import get_sync_db
from app.core.security import allow_authenticated
from app.models.project import Project
from app.models.task import Task
from app.models.issue import Issue
from app.models.timelog import TimeLog
from app.models.milestone import Milestone
from app.models.master import MasterLookup
import csv
import io

router = APIRouter(dependencies=[Depends(allow_authenticated)])

@router.get("/summary")
def get_report_summary(db: Session = Depends(get_sync_db)):
    
    proj_row = db.query(
        func.count(Project.id).label("total"),
        func.sum(
            case(
                (MasterLookup.label.notin_(["Completed", "Closed"]), 1),
                else_=0,
            )
        ).label("active")
    ).outerjoin(MasterLookup, Project.status_id == MasterLookup.id).one()

    task_total = db.query(func.count(Task.id)).scalar() or 0
    task_completed = db.query(func.count(Task.id)).join(Task.status_master).filter(MasterLookup.label == "Completed").scalar() or 0

    issue_total = db.query(func.count(Issue.id)).scalar() or 0
    issue_open = db.query(func.count(Issue.id)).join(Issue.status_master).filter(MasterLookup.label.notin_(["Completed", "Closed", "Resolved"])).scalar() or 0

    total_hours_logged = db.query(func.sum(TimeLog.daily_log_hours)).scalar() or 0.0
    total_milestones   = db.query(func.count(Milestone.id)).scalar() or 0

    return {
        "total_projects":    proj_row.total  or 0,
        "active_projects":   proj_row.active or 0,
        "total_tasks":       task_total,
        "completed_tasks":   task_completed,
        "total_issues":      issue_total,
        "open_issues":       issue_open,
        "total_hours_logged": float(total_hours_logged),
        "total_milestones":  total_milestones,
    }

@router.get("/project/{project_id}")
def get_project_report(project_id: int, db: Session = Depends(get_sync_db)):
    from app.models.user import User

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    task_rows = (
        db.query(MasterLookup.label, func.count(Task.id))
        .join(Task.status_master)
        .filter(Task.project_id == project_id)
        .group_by(MasterLookup.label)
        .all()
    )
    tasks_by_status  = [{"status": r[0] or "Unknown", "count": r[1]} for r in task_rows]
    total_tasks      = sum(r["count"] for r in tasks_by_status)
    completed_tasks  = sum(r["count"] for r in tasks_by_status if r["status"] == "Completed")

    issue_rows = (
        db.query(MasterLookup.label, func.count(Issue.id))
        .join(Issue.severity_master)
        .filter(Issue.project_id == project_id)
        .group_by(MasterLookup.label)
        .all()
    )
    issues_by_priority = [{"priority": r[0] or "Normal", "count": r[1]} for r in issue_rows]
    total_issues       = sum(r["count"] for r in issues_by_priority)

    open_issues_count = (
        db.query(func.count(Issue.id))
        .join(Issue.status_master)
        .filter(Issue.project_id == project_id, MasterLookup.label.notin_(["Closed", "Resolved"]))
        .scalar() or 0
    )

    hours_rows = (
        db.query(
            User.email,
            User.first_name,
            User.last_name,
            func.sum(TimeLog.daily_log_hours).label("total_hours")
        )
        .join(User, TimeLog.user_id == User.id)
        .filter(TimeLog.project_id == project_id)
        .group_by(User.email, User.first_name, User.last_name)
        .order_by(func.sum(TimeLog.daily_log_hours).desc())
        .limit(10)
        .all()
    )

    hours_by_user = [
        {
            "email": row.email,
            "name":  f"{row.first_name} {row.last_name}".strip() if row.first_name else row.email,
            "hours": float(row.total_hours or 0),
        }
        for row in hours_rows
    ]
    total_hours = sum(r["hours"] for r in hours_by_user)

    total_milestones = db.query(func.count(Milestone.id)).filter(Milestone.project_id == project_id).scalar() or 0

    return {
        "project_id":         project_id,
        "project_name":       project.project_name,
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
def export_csv_report(report_type: str = "projects", db: Session = Depends(get_sync_db)):

    def iter_csv():
        output = io.StringIO()
        csv_writer = csv.writer(output)

        if report_type == "projects":
            csv_writer.writerow(["ID", "Name", "Client", "Start Date", "End Date", "Estimated Hours"])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
            for p in db.query(Project).yield_per(1000):
                csv_writer.writerow([p.public_id, p.project_name, p.client_name or "", str(p.expected_start_date or ""), str(p.expected_end_date or ""), p.estimated_hours or 0])
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

        elif report_type == "tasks":
            csv_writer.writerow(["ID", "Title", "Project ID", "Start Date", "End Date", "Estimated Hours"])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
            for t in db.query(Task).yield_per(1000):
                csv_writer.writerow([t.public_id, t.task_name, t.project_id, str(t.start_date or ""), str(t.due_date or ""), t.estimated_hours or 0])
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

        elif report_type == "issues":
            csv_writer.writerow(["ID", "Title", "Project ID", "Start Date", "End Date", "Estimated Hours"])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
            for i in db.query(Issue).yield_per(1000):
                csv_writer.writerow([i.public_id, i.bug_name, i.project_id, str(i.created_at or ""), str(i.due_date or ""), 0])
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

        elif report_type == "timelogs":
            from sqlalchemy.orm import joinedload
            csv_writer.writerow(["ID", "User Email", "Task ID", "Date", "Hours", "Notes"])
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)
            for tl in db.query(TimeLog).options(joinedload(TimeLog.user)).yield_per(1000):
                csv_writer.writerow([tl.id, tl.user.email if tl.user else "", tl.task_id, str(tl.date or ""), tl.daily_log_hours, tl.notes or ""])
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report_type}_report.csv"}
    )

