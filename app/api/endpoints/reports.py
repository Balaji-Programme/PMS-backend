from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
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
    total_projects = db.query(Project).count()
    active_projects = db.query(Project).join(
        Status, Project.status_id == Status.id
    ).filter(Status.name.notin_(["Completed", "Closed"])).count()
    
    total_issues = db.query(Issue).count()
    open_issues = db.query(Issue).join(
        Status, Issue.status_id == Status.id
    ).filter(Status.name.notin_(["Completed", "Closed", "Resolved"])).count()
    
    total_tasks = db.query(Task).count()
    completed_tasks = db.query(Task).join(
        Status, Task.status_id == Status.id
    ).filter(Status.name == "Completed").count()
    
    total_hours_logged = db.query(func.sum(TimeLog.hours)).scalar() or 0.0
    total_milestones = db.query(Milestone).count()
    
    return {
        "total_projects": total_projects,
        "active_projects": active_projects,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "total_issues": total_issues,
        "open_issues": open_issues,
        "total_hours_logged": float(total_hours_logged),
        "total_milestones": total_milestones
    }

@router.get("/project/{project_id}")
def get_project_report(project_id: int, db: Session = Depends(get_db)):

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"error": "Project not found"}

    total_tasks = db.query(Task).filter(Task.project_id == project_id).count()
    completed_tasks = db.query(Task).filter(Task.project_id == project_id, Task.status_id != None).count()
    total_issues = db.query(Issue).filter(Issue.project_id == project_id).count()
    total_milestones = db.query(Milestone).filter(Milestone.project_id == project_id).count()
    total_hours = db.query(func.sum(TimeLog.hours)).filter(TimeLog.project_id == project_id).scalar() or 0.0

    return {
        "project_id": project_id,
        "project_name": project.name,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "total_issues": total_issues,
        "total_milestones": total_milestones,
        "total_hours_logged": float(total_hours)
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

