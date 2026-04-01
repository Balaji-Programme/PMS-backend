from sqlalchemy import text, inspect
from app.core.database import engine, Base

# Import all models to register them with Base.metadata
import app.models.user
import app.models.project
import app.models.task
import app.models.issue
import app.models.team
import app.models.masters
import app.models.roles
import app.models.document
import app.models.milestone
import app.models.timelog
import app.models.timesheet
import app.models.task_list


def run_migrations():
    """Run safe ALTER TABLE migrations for new columns."""
    column_migrations = [
        "ALTER TABLE tasks ADD COLUMN billing_type VARCHAR(50) DEFAULT 'Billable';",
        "ALTER TABLE issues ADD COLUMN module VARCHAR(100);",
        "ALTER TABLE issues ADD COLUMN tags VARCHAR(500);",
        "ALTER TABLE issues ADD COLUMN due_date DATE;",
        "ALTER TABLE timelogs ADD COLUMN general_log BOOLEAN DEFAULT 0;",
        "ALTER TABLE milestones ADD COLUMN flags VARCHAR(50);",
        "ALTER TABLE milestones ADD COLUMN tags VARCHAR(500);",
    ]

    with engine.connect() as conn:
        for q in column_migrations:
            try:
                conn.execute(text(q))
                print(f"[OK] Executed: {q}")
            except Exception as e:
                print(f"[SKIP] May already exist: {e}")
        conn.commit()


def create_all_tables():
    """Create all tables from model definitions (safe - skips existing)."""
    print("\n[*] Creating/verifying all tables from ORM models...")
    Base.metadata.create_all(bind=engine)
    print("[OK] All ORM tables created/verified.")

    # List tables that were created
    insp = inspect(engine)
    tables = insp.get_table_names()
    new_tables = [t for t in ['task_assignees', 'issue_assignees', 'task_owners'] if t in tables]
    if new_tables:
        print(f"[OK] M2M tables present: {', '.join(new_tables)}")
    else:
        print("[WARN] M2M tables not found - check model definitions.")


if __name__ == "__main__":
    print("=== TechnoRUCS PMS Migration Runner ===\n")
    create_all_tables()
    run_migrations()
    print("\n[DONE] All migrations complete.")
