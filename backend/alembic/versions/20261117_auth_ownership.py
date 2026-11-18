"""add authentication and ownership fields

Revision ID: 20261117_auth_ownership
Revises:
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from app import models  # noqa: F401

revision = "20261117_auth_ownership"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # The project historically bootstrapped SQLite/Postgres with create_all
    # and had no checked-in base revision. Create the complete current schema
    # on a fresh database, then back-fill only missing columns on legacy DBs.
    models.Base.metadata.create_all(bind=bind)
    inspector = inspect(bind)

    additions = {
        "users": [("password_hash", sa.String(length=512), "") , ("token_version", sa.Integer(), 1)],
        "personas": [("owner_id", sa.String(length=32), None)],
        "virtual_friends": [("owner_id", sa.String(length=32), None)],
        "vf_imports": [("owner_id", sa.String(length=32), None)],
    }
    for table, columns in additions.items():
        existing = {column["name"] for column in inspector.get_columns(table)}
        for name, column_type, default in columns:
            if name not in existing:
                op.add_column(table, sa.Column(name, column_type, nullable=True, server_default=str(default) if default is not None else None))

    for table, name in (("personas", "owner_id"), ("virtual_friends", "owner_id"), ("vf_imports", "owner_id")):
        index_name = f"ix_{table}_{name}"
        if not any(index["name"] == index_name for index in inspector.get_indexes(table)):
            op.create_index(index_name, table, [name])


def downgrade() -> None:
    op.drop_index("ix_vf_imports_owner_id", table_name="vf_imports")
    op.drop_constraint("fk_vf_imports_owner_id_users", "vf_imports", type_="foreignkey")
    op.drop_column("vf_imports", "owner_id")
    op.drop_index("ix_virtual_friends_owner_id", table_name="virtual_friends")
    op.drop_constraint("fk_virtual_friends_owner_id_users", "virtual_friends", type_="foreignkey")
    op.drop_column("virtual_friends", "owner_id")
    op.drop_index("ix_personas_owner_id", table_name="personas")
    op.drop_constraint("fk_personas_owner_id_users", "personas", type_="foreignkey")
    op.drop_column("personas", "owner_id")
    op.drop_column("users", "token_version")
    op.drop_column("users", "password_hash")
