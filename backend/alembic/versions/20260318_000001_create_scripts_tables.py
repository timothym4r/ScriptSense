"""create scripts tables"""

from alembic import op
import sqlalchemy as sa


revision = "20260318_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scripts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("total_scenes", sa.Integer(), nullable=False),
        sa.Column("total_elements", sa.Integer(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "scenes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("script_id", sa.String(length=36), nullable=False),
        sa.Column("scene_number", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(length=255), nullable=True),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["script_id"], ["scripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scenes_script_id"), "scenes", ["script_id"], unique=False)
    op.create_table(
        "script_blocks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("script_id", sa.String(length=36), nullable=False),
        sa.Column("scene_id", sa.String(length=36), nullable=False),
        sa.Column("global_element_index", sa.Integer(), nullable=False),
        sa.Column("element_index", sa.Integer(), nullable=False),
        sa.Column("element_type", sa.String(length=50), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("speaker", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["script_id"], ["scripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_script_blocks_element_type"), "script_blocks", ["element_type"], unique=False)
    op.create_index(op.f("ix_script_blocks_scene_id"), "script_blocks", ["scene_id"], unique=False)
    op.create_index(op.f("ix_script_blocks_script_id"), "script_blocks", ["script_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_script_blocks_script_id"), table_name="script_blocks")
    op.drop_index(op.f("ix_script_blocks_scene_id"), table_name="script_blocks")
    op.drop_index(op.f("ix_script_blocks_element_type"), table_name="script_blocks")
    op.drop_table("script_blocks")
    op.drop_index(op.f("ix_scenes_script_id"), table_name="scenes")
    op.drop_table("scenes")
    op.drop_table("scripts")
