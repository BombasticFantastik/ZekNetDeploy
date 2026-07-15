"""Initial vector tables

Revision ID: 5102a20005c1
Revises: 
Create Date: 2026-07-05 20:26:53.135611

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '5102a20005c1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Отряды
    op.create_table(
        'units',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=256), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Сессии распознавания / построения
    op.create_table(
        'attendance_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('unit_id', sa.Integer(), nullable=False),
        sa.Column('snapshot_minio_path', sa.String(length=512), nullable=False),
        sa.Column('detected_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['unit_id'],
            ['units.id']
        ),
        sa.PrimaryKeyConstraint('id')
    )

    # Эталоны людей
    op.create_table(
        'prisoners_etalons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('fio', sa.String(length=255), nullable=True),
        sa.Column('photo_minio_path', sa.String(length=512), nullable=False),
        sa.Column('face_embedding', Vector(512), nullable=False),
        sa.Column('unit_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['unit_id'],
            ['units.id']
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('photo_minio_path')
    )

    # Результаты отдельных лиц на фотографии
    op.create_table(
        'attendance_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('matched_prisoner_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('bbox', sa.ARRAY(sa.Integer()), nullable=False),
        sa.Column('cropped_face_minio_path', sa.String(length=512), nullable=False),
        sa.ForeignKeyConstraint(
            ['matched_prisoner_id'],
            ['prisoners_etalons.id'],
            ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(
            ['session_id'],
            ['attendance_sessions.id'],
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table('attendance_logs')
    op.drop_table('prisoners_etalons')
    op.drop_table('attendance_sessions')
    op.drop_table('units')