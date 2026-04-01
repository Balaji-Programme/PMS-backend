from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base, AuditMixin

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class TimeLog(AuditMixin, Base):
    __tablename__ = "timelogs"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), ForeignKey("users.email"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=True)
    timesheet_id = Column(Integer, ForeignKey("timesheets.id", name="fk_timelog_timesheet"), nullable=True)
    
    date = Column(Date, nullable=False)
    hours = Column(Numeric(5, 2), nullable=False)
    description = Column(Text, nullable=True)
    
    log_title = Column(String(255), nullable=True)
    billing_type = Column(String(50), default="Billable")
    approval_status = Column(String(50), default="Pending")
    general_log = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_email])
    project = relationship("Project")
    task = relationship("Task", back_populates="timelogs")
    issue = relationship("Issue")
    timesheet = relationship("Timesheet", back_populates="timelogs")
