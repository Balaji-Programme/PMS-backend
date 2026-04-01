from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, Float, Table, Boolean, Numeric, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy import event
from sqlalchemy.orm.attributes import get_history
from app.core.database import Base, AuditMixin

project_users = Table(
    "project_users",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("project_id", Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("user_email", String(255), nullable=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True),
    Column("is_processed", Boolean, default=False),
    Column("created_at", DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), default=None, onupdate=func.now(), nullable=True),
    Column("is_active", Boolean, default=True, nullable=False),
    Column("is_deleted", Boolean, default=False, nullable=False)
)

class Project(AuditMixin, Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)
    client = Column(String(255), nullable=True)
    
    # Email-as-Key
    manager_email = Column(String(255), ForeignKey("users.email"), nullable=True)
    created_by_email = Column(String(255), ForeignKey("users.email", ondelete="SET NULL"), nullable=True)
    
    status_id = Column(Integer, ForeignKey("statuses.id"), nullable=True)
    previous_status = Column(Integer, ForeignKey("statuses.id", ondelete="SET NULL"), nullable=True)
    priority_id = Column(Integer, ForeignKey("priorities.id"), nullable=True)

    # ── Planned / Expected Schedule (required in business logic) ──
    start_date = Column(Date, nullable=True)        # expected_start_date alias
    end_date = Column(Date, nullable=True)          # expected_end_date alias
    estimated_hours = Column(Numeric(10, 2), nullable=True)

    # ── Actual Tracking (populated as work progresses) ──────────
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)
    actual_hours = Column(Numeric(10, 2), nullable=True, default=0)

    # ── Soft Delete / Archiving ──────────────────────────────────
    is_archived = Column(Boolean, default=False, nullable=False)
    is_processed = Column(Boolean, default=False)

    # Relationships — joinedload to prevent N+1
    manager = relationship("User", foreign_keys=[manager_email], lazy="joined")
    creator = relationship("User", foreign_keys=[created_by_email], lazy="joined")
    status = relationship("Status", foreign_keys=[status_id], lazy="joined")
    previous_status_rel = relationship("Status", foreign_keys=[previous_status], lazy="joined")
    priority = relationship("Priority", lazy="joined")

    users = relationship("User", secondary="project_users", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="project", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    task_lists = relationship("TaskList", back_populates="project", cascade="all, delete-orphan")
