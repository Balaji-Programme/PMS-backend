import logging
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.masters import UserStatus, Skill, Status, Priority
from app.models.roles import Role
from app.models.user import User
from app.models.master import MasterLookup

logger = logging.getLogger("app.seeding")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

def seed_simple_records(db: Session, model, data, name_field="name"):
    added = 0
    skipped = 0
    for name in data:
        existing = db.query(model).filter(getattr(model, name_field) == name).first()
        if not existing:
            db.add(model(**{name_field: name}))
            added += 1
        else:
            skipped += 1
    db.commit()
    return added, skipped

def seed_master_lookups(db: Session):
    lookups = {
        "ProjectStatus": ["Active", "Completed", "On Hold", "Cancelled", "Planning"],
        "TaskStatus":    ["Open", "In Progress", "In Review", "Completed", "Cancelled", "On Hold"],
        "IssueStatus":   ["Open", "Active", "In Progress", "To Be Tested", "In Review", "Closed", "Re-Opened", "On Hold", "Cancelled"],
        "Priority":      ["Low", "Medium", "High", "Critical"],
        "Severity":      ["Low", "Medium", "High", "Critical"],
        "Classification":["Feature", "Bug", "Enhancement", "Support"],
        "ProjectType":   ["Internal", "External"],
        "BillingType":   ["Billable", "Non-Billable"],
    }
    
    total_inserted = 0
    total_skipped = 0
    for category, values in lookups.items():
        for val in values:
            existing = db.query(MasterLookup).filter(
                MasterLookup.category == category,
                MasterLookup.value == val
            ).first()
            if not existing:
                db.add(MasterLookup(category=category, label=val, value=val))
                total_inserted += 1
            else:
                total_skipped += 1
    db.commit()
    logger.info(f"MasterLookups: {total_inserted} inserted, {total_skipped} already exist.")

def seed_roles(db: Session):
    canonical_roles = ["Super Admin", "Admin", "Team Lead", "Project Manager", "Employee"]
    for r_name in canonical_roles:
        role = db.query(Role).filter(Role.name == r_name).first()
        if not role:
            db.add(Role(name=r_name, description=f"{r_name} role"))
            logger.info(f"Added Role: {r_name}")
    db.commit()

def seed_admin_user(db: Session):
    email = "test1@technorucspltd.onmicrosoft.com"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        from app.utils.ids import generate_public_id
        admin_role = db.query(Role).filter(Role.name == "Super Admin").first()
        active_status = db.query(UserStatus).filter(UserStatus.name == "Active").first()
        
        new_user = User(
            public_id    = generate_public_id("USR-"),
            employee_id  = generate_public_id("EMP-"),
            first_name   = "TechnoRUCS",
            last_name    = "Admin",
            email        = email,
            username     = "admin",
            display_name = "System Administrator",
            is_synced    = True,
            role_id      = admin_role.id if admin_role else None,
            status_id    = active_status.id if active_status else None
        )
        db.add(new_user)
        db.commit()
        logger.info(f"Created default admin user: {email}")
    else:
        logger.info(f"Admin user already exists: {email}")

def seed_all(reset=False):
    if reset:
        logger.warning("Reset requested - Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        # User Statuses
        u_added, u_skip = seed_simple_records(db, UserStatus, ["Active", "Inactive", "Pending", "Onboarding", "On Leave"])
        if u_added: logger.info(f"Added User Statuses: {u_added}")
        
        # General Statuses
        s_added, s_skip = seed_simple_records(db, Status, ["Open", "In Progress", "In Review", "Completed", "Cancelled", "On Hold", "Planning", "Active", "Closed", "To Be Tested", "Re-Opened"])
        if s_added: logger.info(f"Added General Statuses: {s_added}")
        
        # Priorities
        p_added, p_skip = seed_simple_records(db, Priority, ["Low", "Medium", "High", "Critical"])
        if p_added: logger.info(f"Added Priorities: {p_added}")
        
        # Skills
        sk_added, sk_skip = seed_simple_records(db, Skill, ["React", "Python", "FastAPI", "UI/UX Design", "Node.js", ".NET", "DevOps", "Project Management", "Data Analytics"])
        if sk_added: logger.info(f"Added Skills: {sk_added}")
        
        seed_roles(db)
        seed_master_lookups(db)
        seed_admin_user(db)
        
    logger.info("Database seeding completed successfully.")
