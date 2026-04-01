"""add_zoho_fields_actual_hours_classification_archiving

Revision ID: 765541d1aad8
Revises: 56d7b87c646b
Create Date: 2026-03-31 15:53:32.164688

Adds:
  - projects.actual_start_date
  - projects.actual_end_date
  - projects.actual_hours
  - projects.is_archived (soft-delete flag)
  - tasks.actual_hours
  - issues.classification (Zoho bug classification)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '765541d1aad8'
down_revision: Union[str, Sequence[str], None] = '56d7b87c646b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Zoho-compatible tracking fields."""

    # ── Issues: bug classification ────────────────────────────────────────────
    op.add_column('issues', sa.Column('classification', sa.String(length=50), nullable=True))

    # ── Projects: actual schedule + soft-delete ───────────────────────────────
    op.add_column('projects', sa.Column('actual_start_date', sa.Date(), nullable=True))
    op.add_column('projects', sa.Column('actual_end_date', sa.Date(), nullable=True))
    op.add_column('projects', sa.Column('actual_hours', sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column('projects', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.text('0')))

    # ── Tasks: actual hours ───────────────────────────────────────────────────
    op.add_column('tasks', sa.Column('actual_hours', sa.Numeric(precision=5, scale=2), nullable=True))


def downgrade() -> None:
    """Remove Zoho-compatible tracking fields."""
    op.drop_column('tasks', 'actual_hours')
    op.drop_column('projects', 'is_archived')
    op.drop_column('projects', 'actual_hours')
    op.drop_column('projects', 'actual_end_date')
    op.drop_column('projects', 'actual_start_date')
    op.drop_column('issues', 'classification')
