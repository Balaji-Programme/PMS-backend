from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base, AuditMixin

class Milestone(AuditMixin, Base):
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    owner_email = Column(String(255), ForeignKey("users.email"), nullable=True)
    flags = Column(String(50), nullable=True)
    tags = Column(String(500), nullable=True)

    
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_processed = Column(Boolean, default=False)

    project = relationship("Project", back_populates="milestones")
    owner = relationship("User", foreign_keys=[owner_email])
