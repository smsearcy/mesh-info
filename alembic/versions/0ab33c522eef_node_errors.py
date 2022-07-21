"""Add *node_error* table to track node polling errors.

Revision ID: 0ab33c522eef
Revises: f7672ee42a36
Create Date: 2022-07-05 21:57:06.056079

"""
import sqlalchemy as sa
from alembic import op

import meshinfo.models

# revision identifiers, used by Alembic.
revision = "0ab33c522eef"
down_revision = "f7672ee42a36"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "node_error",
        sa.Column(
            "timestamp", meshinfo.models.meta.PDateTime(timezone=True), nullable=False
        ),
        sa.Column("ip_address", sa.String(length=15), nullable=False),
        sa.Column("dns_name", sa.String(length=70), nullable=False),
        sa.Column(
            "error_type",
            sa.Enum(
                "INVALID_RESPONSE",
                "PARSE_ERROR",
                "CONNECTION_ERROR",
                "HTTP_ERROR",
                "TIMEOUT_ERROR",
                name="pollingerror",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("details", sa.UnicodeText(), nullable=False),
        sa.ForeignKeyConstraint(
            ["timestamp"],
            ["collector_stat.started_at"],
            name=op.f("fk_node_error_timestamp_collector_stat"),
        ),
        sa.PrimaryKeyConstraint("timestamp", "ip_address", name=op.f("pk_node_error")),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("node_error")
    # ### end Alembic commands ###