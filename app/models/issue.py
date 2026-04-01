from sqlalchemy import Column, Integer, String, Text, ForeignKey, Date, Numeric, Boolean, Table
from sqlalchemy.orm import relationship
from app.core.database import AuditMixin, Base

# ── Zoho-compatible classification values ────────────────────────────────────
ISSUE_CLASSIFICATIONS = [
    "None", "Security", "Crash", "Data Loss", "Performance",
    "UI/UX", "Other", "Feature", "Enhancement"
]

# ── Zoho-compatible issue status values ─────────────────────────────────────
ISSUE_STATUSES = [
    "Open", "In Progress", "In Review", "To Be Tested", "Re-opened", "Closed"
]

issue_followers = Table(
    "issue_followers",
    Base.metadata,
    Column("issue_id", Integer, ForeignKey("issues.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)

issue_assignees = Table(
    "issue_assignees",
    Base.metadata,
    Column("issue_id", Integer, ForeignKey("issues.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)


class Issue(AuditMixin, Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)

    # Email-as-Key Foreign Keys
    reporter_email = Column(String(255), ForeignKey("users.email"), nullable=True)
    assignee_email = Column(String(255), ForeignKey("users.email"), nullable=True)

    status_id = Column(Integer, ForeignKey("statuses.id"), nullable=True)
    priority_id = Column(Integer, ForeignKey("priorities.id"), nullable=True)

    # ── Bug Classification (Zoho-compatible) ─────────────────────
    classification = Column(String(50), nullable=True, default="None")
    module = Column(String(100), nullable=True)
    tags = Column(String(500), nullable=True)

    # Shadow State for Automation (Backend Only)
    previous_status = Column(String(100), nullable=True)

    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    estimated_hours = Column(Numeric(5, 2), nullable=True)
    is_processed = Column(Boolean, default=False)

    # Relationships
    project = relationship("Project", back_populates="issues")
    reporter = relationship("User", foreign_keys=[reporter_email])
    assignee = relationship("User", foreign_keys=[assignee_email])
    status = relationship("Status")
    priority = relationship("Priority")

    followers = relationship("User", secondary=issue_followers, backref="followed_issues")
    assignees = relationship("User", secondary=issue_assignees, backref="assigned_issues")

    # Multi-Media Issue & Document Engine Link
    documents = relationship("Document", secondary="issue_document_link", back_populates="issues")
