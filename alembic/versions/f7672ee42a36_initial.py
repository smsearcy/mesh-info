"""Initial database creation

Revision ID: f7672ee42a36
Revises:
Create Date: 2021-11-08 13:36:34.683960

"""
import sqlalchemy as sa
from alembic import op

import meshinfo.models

# revision identifiers, used by Alembic.
revision = "f7672ee42a36"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "collector_stat",
        sa.Column(
            "started_at", meshinfo.models.meta.PDateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "finished_at",
            meshinfo.models.meta.PDateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("node_count", sa.Integer(), nullable=False),
        sa.Column("link_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("polling_duration", sa.Float(), nullable=False),
        sa.Column("total_duration", sa.Float(), nullable=False),
        sa.Column("other_stats", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("started_at", name=op.f("pk_collector_stat")),
    )
    op.create_table(
        "node",
        sa.Column("node_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=70), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "INACTIVE", name="nodestatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(length=70), nullable=False),
        sa.Column("wlan_ip", sa.String(length=15), nullable=False),
        sa.Column("description", sa.Unicode(length=1024), nullable=False),
        sa.Column("wlan_mac_address", sa.String(length=12), nullable=False),
        sa.Column(
            "last_seen", meshinfo.models.meta.PDateTime(timezone=True), nullable=False
        ),
        sa.Column("up_time", sa.String(length=25), nullable=False),
        sa.Column("up_time_seconds", sa.Integer(), nullable=True),
        sa.Column("load_averages", sa.JSON(), nullable=True),
        sa.Column("model", sa.String(length=50), nullable=False),
        sa.Column("board_id", sa.String(length=50), nullable=False),
        sa.Column("firmware_version", sa.String(length=50), nullable=False),
        sa.Column("firmware_manufacturer", sa.String(length=100), nullable=False),
        sa.Column("api_version", sa.String(length=5), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("grid_square", sa.String(length=20), nullable=False),
        sa.Column("ssid", sa.String(length=50), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("channel_bandwidth", sa.String(length=50), nullable=False),
        sa.Column("band", sa.String(length=25), nullable=False),
        sa.Column("services", sa.JSON(), nullable=False),
        sa.Column("tunnel_installed", sa.Boolean(), nullable=False),
        sa.Column("active_tunnel_count", sa.Integer(), nullable=False),
        sa.Column("link_count", sa.Integer(), nullable=True),
        sa.Column("radio_link_count", sa.Integer(), nullable=True),
        sa.Column("dtd_link_count", sa.Integer(), nullable=True),
        sa.Column("tunnel_link_count", sa.Integer(), nullable=True),
        sa.Column("system_info", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", meshinfo.models.meta.PDateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "last_updated_at",
            meshinfo.models.meta.PDateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("node_id", name=op.f("pk_node")),
    )
    op.create_index("idx_mac_name", "node", ["wlan_mac_address", "name"], unique=False)
    op.create_table(
        "link",
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("destination_id", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            sa.Enum("DTD", "TUN", "RF", "UNKNOWN", name="linktype"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "CURRENT", "RECENT", "INACTIVE", name="linkstatus", native_enum=False
            ),
            nullable=False,
        ),
        sa.Column(
            "last_seen", meshinfo.models.meta.PDateTime(timezone=True), nullable=False
        ),
        sa.Column("olsr_cost", sa.Float(), nullable=True),
        sa.Column("distance", sa.Float(), nullable=True),
        sa.Column("bearing", sa.Float(), nullable=True),
        sa.Column("signal", sa.Float(), nullable=True),
        sa.Column("noise", sa.Float(), nullable=True),
        sa.Column("tx_rate", sa.Float(), nullable=True),
        sa.Column("rx_rate", sa.Float(), nullable=True),
        sa.Column("quality", sa.Float(), nullable=True),
        sa.Column("neighbor_quality", sa.Float(), nullable=True),
        sa.Column(
            "created_at", meshinfo.models.meta.PDateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "last_updated_at",
            meshinfo.models.meta.PDateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["destination_id"],
            ["node.node_id"],
            name=op.f("fk_link_destination_id_node"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["node.node_id"], name=op.f("fk_link_source_id_node")
        ),
        sa.PrimaryKeyConstraint(
            "source_id", "destination_id", "type", name=op.f("pk_link")
        ),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("link")
    op.drop_index("idx_mac_name", table_name="node")
    op.drop_table("node")
    op.drop_table("collector_stat")
    # ### end Alembic commands ###
