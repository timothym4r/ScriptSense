"""create correction records"""

from alembic import op
import sqlalchemy as sa


revision = "20260319_000002"
down_revision = "20260318_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "correction_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("script_id", sa.String(length=36), nullable=False),
        sa.Column("scene_id", sa.String(length=36), nullable=True),
        sa.Column("block_id", sa.String(length=36), nullable=True),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("corrected_field", sa.String(length=50), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["block_id"], ["script_blocks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["script_id"], ["scripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_correction_records_block_id"), "correction_records", ["block_id"], unique=False)
    op.create_index(op.f("ix_correction_records_scene_id"), "correction_records", ["scene_id"], unique=False)
    op.create_index(op.f("ix_correction_records_script_id"), "correction_records", ["script_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_correction_records_script_id"), table_name="correction_records")
    op.drop_index(op.f("ix_correction_records_scene_id"), table_name="correction_records")
    op.drop_index(op.f("ix_correction_records_block_id"), table_name="correction_records")
    op.drop_table("correction_records")
