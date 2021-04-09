"""Add columns for additional information to the link table.

Revision ID: 522b1ff95551
Revises: 2dfd2999b555
Create Date: 2021-01-21 13:10:28.562171

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "522b1ff95551"
down_revision = "2dfd2999b555"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("link", sa.Column("quality", sa.Float(), nullable=True))
    op.add_column("link", sa.Column("neighbor_quality", sa.Float(), nullable=True))
    op.add_column("link", sa.Column("noise", sa.Float(), nullable=True))
    op.add_column("link", sa.Column("rx_rate", sa.Float(), nullable=True))
    op.add_column("link", sa.Column("signal", sa.Float(), nullable=True))
    op.add_column("link", sa.Column("tx_rate", sa.Float(), nullable=True))

    link_type = postgresql.ENUM("RADIO", "TUNNEL", "DIRECT", "UNKNOWN", name="linktype")
    link_type.create(op.get_bind(), checkfirst=True)
    op.add_column("link", sa.Column("type", link_type, nullable=True))


def downgrade():
    op.drop_column("link", "type")
    op.drop_column("link", "tx_rate")
    op.drop_column("link", "signal")
    op.drop_column("link", "rx_rate")
    op.drop_column("link", "noise")
    op.drop_column("link", "neighbor_quality")
    op.drop_column("link", "quality")
    link_type = postgresql.ENUM("RADIO", "TUNNEL", "DIRECT", "UNKNOWN", name="linktype")
    link_type.drop(op.get_bind())
