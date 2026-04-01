from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, Numeric, Boolean, Table
from sqlalchemy.orm import relationship
from sqlalchemy import event
from sqlalchemy.orm.attributes import get_history
from app.core.database import Base, AuditMixin

task_owners = Table(
    "task_owners",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)

task_assignees = Table(
    "task_assignees",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)

class Task(AuditMixin, Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    task_list_id = Column(Integer, ForeignKey("task_lists.id", ondelete="SET NULL"), nullable=True)

    # Email-as-Key
    assignee_email = Column(String(255), ForeignKey("users.email"), nullable=True)
    created_by_email = Column(String(255), ForeignKey("users.email", ondelete="SET NULL"), nullable=True)

    status_id = Column(Integer, ForeignKey("statuses.id"), nullable=True)
    priority_id = Column(Integer, ForeignKey("priorities.id"), nullable=True)

    # Shadow State for Automation (Backend Only)
    previous_status = Column(String(100), nullable=True)

    # ── Planned Schedule ─────────────────────────────────────────
    start_date = Column(Date, nullable=True)        # expected_start_date
    end_date = Column(Date, nullable=True)          # expected_end_date
    due_date = Column(Date, nullable=True)
    progress = Column(Integer, default=0)

    # ── Hours Tracking ────────────────────────────────────────────
    estimated_hours = Column(Numeric(5, 2), nullable=True)
    actual_hours = Column(Numeric(5, 2), nullable=True, default=0)
    billing_type = Column(String(50), default="Billable")

    is_processed = Column(Boolean, default=False)

    # Relationships — joinedload to prevent N+1
    project = relationship("Project", back_populates="tasks")
    task_list = relationship("TaskList", back_populates="tasks")
    assignee = relationship("User", foreign_keys=[assignee_email], lazy="joined")
    creator = relationship("User", foreign_keys=[created_by_email], lazy="joined")
    status = relationship("Status", lazy="joined")
    priority = relationship("Priority", lazy="joined")

    owners = relationship("User", secondary=task_owners, backref="task_ownerships")
    assignees = relationship("User", secondary=task_assignees, backref="task_assignments")

    timelogs = relationship("TimeLog", back_populates="task", cascade="all, delete-orphan")


@event.listens_for(Task, 'before_update')
def receive_before_update_task(mapper, connection, target):
    """
    Automatically capture changes to 'status_id' and log the exact previous state.
    """
    history = get_history(target, 'status_id')
    if history.has_changes() and history.deleted:
        target.previous_status = str(history.deleted[0])
