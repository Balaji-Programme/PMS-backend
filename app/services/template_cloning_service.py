from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.project import Project
from app.models.task import Task
from app.models.template import ProjectTemplate, TemplateTask
from app.schemas.template import TemplateCloneRequest


class TemplateCloningService:
    @staticmethod
    def clone_project_to_template(db: Session, project_id: int, request: TemplateCloneRequest, user_id: int) -> ProjectTemplate:
        project = db.query(Project).filter(Project.id == project_id, Project.is_deleted == False).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        try:
            with db.begin_nested():
                new_template = ProjectTemplate(
                    name=request.template_name,
                    description=project.description,
                    billing_type=project.billing_model,
                    is_public=True,
                    created_by_id=user_id
                )
                db.add(new_template)
                db.flush()

                order_idx = 0

                tasks = db.query(Task).filter(Task.project_id == project_id, Task.is_deleted == False)

                if not request.include_milestones:
                    tasks = tasks.filter(Task.milestone_id == None)

                tasks = tasks.order_by(Task.id).all()

                for task in tasks:
                    template_task = TemplateTask(
                        template_id=new_template.id,
                        title=task.task_name,
                        description=task.description,
                        estimated_hours=task.estimated_hours,
                        duration=task.duration,
                        billing_type=task.billing_type,
                        tags=task.tags,
                        order_index=order_idx
                    )
                    db.add(template_task)
                    order_idx += 1

                db.flush()

            db.commit()
            return new_template
        except Exception as e:
            db.rollback()
            raise e
