from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.masters import UserStatus, Skill, Status, Priority
from app.models.roles import Role

REQUIRED_STATUSES = [
    "Planning",
    "Cancelled",
    "Open",
    "In Progress",
    "In Review",
    "To Be Tested",
    "Completed",
    "On Hold",
    "Re-Opened",
    "Closed",
]

def seed_data(db: Session):
    Base.metadata.create_all(bind=engine)

    if db.query(UserStatus).count() == 0:
        user_statuses = ["Active", "Inactive", "Pending", "Onboarding", "On Leave"]
        db.add_all([UserStatus(name=name) for name in user_statuses])

    existing_status_names = {s.name for s in db.query(Status).all()}
    missing_statuses = [name for name in REQUIRED_STATUSES if name not in existing_status_names]
    if missing_statuses:
        db.add_all([Status(name=name) for name in missing_statuses])
        print(f"Added missing statuses: {missing_statuses}")

    if db.query(Priority).count() == 0:
        priorities = ["Low", "Medium", "High", "Critical"]
        db.add_all([Priority(name=name) for name in priorities])

    canonical_roles = ["Admin", "Project Manager", "Team Lead", "Employee"]
    existing_roles = {r.name for r in db.query(Role).all()}

    missing_roles = [name for name in canonical_roles if name not in existing_roles]
    if missing_roles:
        new_roles = [Role(name=name, permissions={}) for name in missing_roles]
        db.add_all(new_roles)

    if db.query(Skill).count() == 0:
        skills = ["React", "Python", "FastAPI", "UI/UX Design", "Node.js", ".NET", "DevOps", "Project Management", "Data Analytics"]
        db.add_all([Skill(name=name) for name in skills])

    db.commit()
    print("Database seeding completed successfully.")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()