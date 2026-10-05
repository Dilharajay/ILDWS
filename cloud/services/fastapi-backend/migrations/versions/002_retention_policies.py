"""retention policies

Revision ID: 002
Revises: 001
Create Date: 2026-03-01
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- Compression policy on sensor_readings --
    # Enable compression settings
    op.execute(
        "ALTER TABLE sensor_readings SET ("
        "  timescaledb.compress,"
        "  timescaledb.compress_orderby = 'timestamp DESC',"
        "  timescaledb.compress_segmentby = 'node_id'"
        ")"
    )
    # Compress chunks older than 7 days
    op.execute("SELECT add_compression_policy('sensor_readings', INTERVAL '7 days')")

    # -- Retention policy on sensor_readings --
    # NOTE: Before this policy drops chunks older than 90 days, an external
    # archival job MUST export them to Google Cloud Storage (GCS) in Parquet
    # format. See docs/05_Deployment_DevOps_Guide_ILEWS.txt for the archival
    # pipeline configuration.
    op.execute(
        "SELECT add_retention_policy('sensor_readings', "
        "INTERVAL '90 days', schedule_interval => INTERVAL '1 day')"
    )


def downgrade() -> None:
    op.execute("SELECT remove_retention_policy('sensor_readings', if_exists => true)")
    op.execute("SELECT remove_compression_policy('sensor_readings', if_exists => true)")
    op.execute(
        "ALTER TABLE sensor_readings SET ("
        "  timescaledb.compress = false"
        ")"
    )
