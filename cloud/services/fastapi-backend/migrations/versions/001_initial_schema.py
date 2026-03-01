"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- Enable TimescaleDB extension --
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")

    # ================================================================
    # 1. slopes
    # ================================================================
    op.create_table(
        "slopes",
        sa.Column("slope_id", sa.String(20), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("location_name", sa.String(200)),
        sa.Column("latitude_centroid", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude_centroid", sa.Numeric(9, 6), nullable=False),
        sa.Column("area_m2", sa.Numeric(12, 2)),
        sa.Column("zone_polygon", postgresql.JSONB),
        sa.Column("monitoring_status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("risk_threshold_red", sa.Numeric(4, 2), nullable=False, server_default="0.85"),
        sa.Column("risk_threshold_orange", sa.Numeric(4, 2), nullable=False, server_default="0.65"),
        sa.Column("risk_threshold_yellow", sa.Numeric(4, 2), nullable=False, server_default="0.40"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(100)),
        sa.CheckConstraint(
            "monitoring_status IN ('active','inactive','archived')",
            name="chk_slopes_status",
        ),
        sa.CheckConstraint("latitude_centroid BETWEEN -90 AND 90", name="chk_slopes_lat"),
        sa.CheckConstraint("longitude_centroid BETWEEN -180 AND 180", name="chk_slopes_lon"),
    )
    op.create_index("idx_slopes_status", "slopes", ["monitoring_status"])

    # ================================================================
    # 2. sensor_nodes
    # ================================================================
    op.create_table(
        "sensor_nodes",
        sa.Column("node_id", sa.String(20), primary_key=True),
        sa.Column("slope_id", sa.String(20), sa.ForeignKey("slopes.slope_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(100)),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("depth_config", postgresql.ARRAY(sa.Numeric), nullable=False, server_default="{0.5,1.0,2.0}"),
        sa.Column("coordinate_source", sa.String(100)),
        sa.Column("survey_reference", sa.String(100)),
        sa.Column("firmware_version", sa.String(20)),
        sa.Column("hardware_revision", sa.String(20)),
        sa.Column("installed_date", sa.Date),
        sa.Column("last_maintenance_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('active','inactive','error','decommissioned')",
            name="chk_nodes_status",
        ),
        sa.CheckConstraint("latitude BETWEEN -90 AND 90", name="chk_nodes_lat"),
        sa.CheckConstraint("longitude BETWEEN -180 AND 180", name="chk_nodes_lon"),
    )
    op.create_index("idx_nodes_slope_id", "sensor_nodes", ["slope_id"])
    op.create_index("idx_nodes_status", "sensor_nodes", ["status"], postgresql_where=sa.text("NOT is_deleted"))

    # ================================================================
    # 3. sensor_readings (TimescaleDB hypertable)
    # ================================================================
    op.create_table(
        "sensor_readings",
        sa.Column("reading_id", sa.BigInteger, autoincrement=True),
        sa.Column("node_id", sa.String(20), nullable=False),
        sa.Column("slope_id", sa.String(20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("packet_id", sa.String(40)),
        sa.Column("soil_moisture_d1_pct", sa.Numeric(5, 2)),
        sa.Column("soil_moisture_d2_pct", sa.Numeric(5, 2)),
        sa.Column("soil_moisture_d3_pct", sa.Numeric(5, 2)),
        sa.Column("soil_moisture_d4_pct", sa.Numeric(5, 2)),
        sa.Column("soil_moisture_d5_pct", sa.Numeric(5, 2)),
        sa.Column("rainfall_mm", sa.Numeric(6, 2)),
        sa.Column("tilt_x_deg", sa.Numeric(7, 4)),
        sa.Column("tilt_y_deg", sa.Numeric(7, 4)),
        sa.Column("accel_x_ms2", sa.Numeric(8, 4)),
        sa.Column("accel_y_ms2", sa.Numeric(8, 4)),
        sa.Column("accel_z_ms2", sa.Numeric(8, 4)),
        sa.Column("vibration_hz", sa.Numeric(8, 3)),
        sa.Column("vibration_amplitude", sa.Numeric(8, 4)),
        sa.Column("battery_voltage_v", sa.Numeric(5, 2)),
        sa.Column("solar_input_w", sa.Numeric(5, 2)),
        sa.Column("rssi_dbm", sa.SmallInteger),
        sa.Column("data_quality", sa.String(20), nullable=False, server_default="valid"),
        sa.Column("quality_flags", postgresql.JSONB),
        sa.Column("source", sa.String(20), nullable=False, server_default="lora"),
        sa.PrimaryKeyConstraint("reading_id", "timestamp"),
        sa.CheckConstraint(
            "data_quality IN ('valid','suspect','invalid')",
            name="chk_readings_quality",
        ),
        sa.CheckConstraint(
            "source IN ('lora','edge_buffer','manual','synthetic')",
            name="chk_readings_source",
        ),
    )

    # Convert to TimescaleDB hypertable with 1-day chunks
    op.execute(
        "SELECT create_hypertable('sensor_readings', 'timestamp', "
        "chunk_time_interval => INTERVAL '1 day')"
    )

    # Deduplication unique index
    op.create_index(
        "idx_readings_dedup",
        "sensor_readings",
        ["node_id", "timestamp", "packet_id"],
        unique=True,
    )
    op.create_index("idx_readings_node_time", "sensor_readings", ["node_id", sa.text("timestamp DESC")])
    op.create_index("idx_readings_slope_time", "sensor_readings", ["slope_id", sa.text("timestamp DESC")])

    # ================================================================
    # 4. risk_scores (TimescaleDB hypertable)
    # ================================================================
    op.create_table(
        "risk_scores",
        sa.Column("score_id", sa.BigInteger, autoincrement=True),
        sa.Column("slope_id", sa.String(20), sa.ForeignKey("slopes.slope_id"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("risk_level", sa.String(10), nullable=False),
        sa.Column("model_version", sa.String(30), nullable=False),
        sa.Column("inference_source", sa.String(20), nullable=False, server_default="cloud"),
        sa.Column("feature_window_start", sa.DateTime(timezone=True)),
        sa.Column("feature_window_end", sa.DateTime(timezone=True)),
        sa.Column("contributing_nodes", postgresql.ARRAY(sa.String(20))),
        sa.Column("model_confidence", sa.Numeric(4, 3)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("score_id", "timestamp"),
        sa.CheckConstraint("risk_score BETWEEN 0 AND 1", name="chk_score_range"),
        sa.CheckConstraint(
            "risk_level IN ('GREEN','YELLOW','ORANGE','RED')",
            name="chk_risk_level",
        ),
        sa.CheckConstraint(
            "inference_source IN ('cloud','edge')",
            name="chk_score_source",
        ),
    )

    # Convert to TimescaleDB hypertable with 7-day chunks
    op.execute(
        "SELECT create_hypertable('risk_scores', 'timestamp', "
        "chunk_time_interval => INTERVAL '7 days')"
    )

    op.create_index("idx_risk_slope_time", "risk_scores", ["slope_id", sa.text("timestamp DESC")])
    op.create_index("idx_risk_level", "risk_scores", ["risk_level", sa.text("timestamp DESC")])

    # ================================================================
    # 5. alerts
    # ================================================================
    op.create_table(
        "alerts",
        sa.Column("alert_id", sa.String(30), primary_key=True),
        sa.Column("slope_id", sa.String(20), sa.ForeignKey("slopes.slope_id"), nullable=False),
        sa.Column("trigger_score_id", sa.BigInteger),
        sa.Column("level", sa.String(10), nullable=False),
        sa.Column("risk_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("source", sa.String(30), nullable=False, server_default="ml_inference"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("acknowledged_by", sa.String(100)),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("acknowledged_notes", sa.Text),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolution_notes", sa.Text),
        sa.Column("false_alarm_confirmed", sa.Boolean, server_default="false"),
        sa.Column("false_alarm_reason", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("level IN ('YELLOW','ORANGE','RED')", name="chk_alert_level"),
        sa.CheckConstraint(
            "source IN ('ml_inference','edge_local','manual_override','scheduled_test')",
            name="chk_alert_source",
        ),
        sa.CheckConstraint(
            "status IN ('active','acknowledged','resolved','false_alarm')",
            name="chk_alert_status",
        ),
        sa.CheckConstraint("risk_score BETWEEN 0 AND 1", name="chk_alerts_risk_score"),
    )
    op.create_index("idx_alerts_slope_time", "alerts", ["slope_id", sa.text("triggered_at DESC")])
    op.create_index("idx_alerts_level_status", "alerts", ["level", "status"])
    op.create_index("idx_alerts_triggered", "alerts", [sa.text("triggered_at DESC")])

    # ================================================================
    # 6. users
    # ================================================================
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(20), primary_key=True),
        sa.Column("email", sa.String(200), unique=True, nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("organisation", sa.String(200)),
        sa.Column("phone", sa.String(30)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_sms_alert_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_push_alert_enabled", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("slope_access", postgresql.ARRAY(sa.String(20))),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("password_hash", sa.Text),
        sa.Column("sso_subject", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(100)),
        sa.CheckConstraint(
            "role IN ('system_admin','operator','analyst','government_viewer','read_only')",
            name="chk_user_role",
        ),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_role", "users", ["role"], postgresql_where=sa.text("is_active"))

    # ================================================================
    # 7. alert_notifications
    # ================================================================
    op.create_table(
        "alert_notifications",
        sa.Column("notification_id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("alert_id", sa.String(30), sa.ForeignKey("alerts.alert_id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("recipient", sa.String(200)),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text),
        sa.Column("provider_response", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "channel IN ('sms','push','siren','email','websocket')",
            name="chk_notif_channel",
        ),
        sa.CheckConstraint(
            "status IN ('pending','sent','delivered','failed')",
            name="chk_notif_status",
        ),
    )
    op.create_index("idx_notif_alert", "alert_notifications", ["alert_id"])
    op.create_index(
        "idx_notif_status", "alert_notifications", ["status"],
        postgresql_where=sa.text("status != 'delivered'"),
    )

    # ================================================================
    # 8. audit_logs
    # ================================================================
    op.create_table(
        "audit_logs",
        sa.Column("log_id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("actor_id", sa.String(100)),
        sa.Column("actor_ip", postgresql.INET),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50)),
        sa.Column("resource_id", sa.String(100)),
        sa.Column("old_value", postgresql.JSONB),
        sa.Column("new_value", postgresql.JSONB),
        sa.Column("result", sa.String(20), nullable=False),
        sa.Column("error_detail", sa.Text),
        sa.Column("request_id", postgresql.UUID),
        sa.CheckConstraint(
            "result IN ('success','failure','partial')",
            name="chk_audit_result",
        ),
    )
    op.create_index("idx_audit_timestamp", "audit_logs", [sa.text("timestamp DESC")])
    op.create_index("idx_audit_actor", "audit_logs", ["actor_id", sa.text("timestamp DESC")])
    op.create_index("idx_audit_resource", "audit_logs", ["resource_type", "resource_id"])

    # ================================================================
    # 9. node_health_snapshots (TimescaleDB hypertable)
    # ================================================================
    op.create_table(
        "node_health_snapshots",
        sa.Column("snapshot_id", sa.BigInteger, autoincrement=True),
        sa.Column("node_id", sa.String(20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("connectivity_status", sa.String(20), nullable=False),
        sa.Column("battery_voltage_v", sa.Numeric(5, 2)),
        sa.Column("battery_pct", sa.SmallInteger),
        sa.Column("solar_input_w", sa.Numeric(5, 2)),
        sa.Column("enclosure_temp_c", sa.Numeric(5, 2)),
        sa.Column("packet_success_1h", sa.SmallInteger),
        sa.Column("packet_total_1h", sa.SmallInteger),
        sa.Column("rssi_dbm_avg", sa.SmallInteger),
        sa.Column("firmware_version", sa.String(20)),
        sa.PrimaryKeyConstraint("snapshot_id", "timestamp"),
        sa.CheckConstraint(
            "connectivity_status IN ('online','offline','degraded')",
            name="chk_health_conn",
        ),
    )

    # Convert to TimescaleDB hypertable with 7-day chunks
    op.execute(
        "SELECT create_hypertable('node_health_snapshots', 'timestamp', "
        "chunk_time_interval => INTERVAL '7 days')"
    )

    op.create_index("idx_health_node_time", "node_health_snapshots", ["node_id", sa.text("timestamp DESC")])

    # ================================================================
    # 10. model_registry
    # ================================================================
    op.create_table(
        "model_registry",
        sa.Column("registry_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("model_version", sa.String(30), unique=True, nullable=False),
        sa.Column("mlflow_run_id", sa.String(100)),
        sa.Column("model_type", sa.String(50), nullable=False),
        sa.Column("training_start", sa.Date, nullable=False),
        sa.Column("training_end", sa.Date, nullable=False),
        sa.Column("training_samples", sa.Integer),
        sa.Column("auc_roc", sa.Numeric(5, 4)),
        sa.Column("precision_score", sa.Numeric(5, 4)),
        sa.Column("recall_score", sa.Numeric(5, 4)),
        sa.Column("f1_score", sa.Numeric(5, 4)),
        sa.Column("false_alarm_rate_pct", sa.Numeric(5, 2)),
        sa.Column("lead_time_avg_min", sa.Numeric(7, 2)),
        sa.Column("lead_time_min_min", sa.Numeric(7, 2)),
        sa.Column("deployment_status", sa.String(20), nullable=False, server_default="trained"),
        sa.Column("deployed_at", sa.DateTime(timezone=True)),
        sa.Column("deployed_by", sa.String(100)),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "deployment_status IN ('trained','staging','production','archived','rejected')",
            name="chk_model_status",
        ),
    )
    op.create_index("idx_model_status", "model_registry", ["deployment_status"])

    # ================================================================
    # 11. reports
    # ================================================================
    op.create_table(
        "reports",
        sa.Column("report_id", sa.String(20), primary_key=True),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("requested_by", sa.String(100), nullable=False),
        sa.Column("slope_ids", postgresql.ARRAY(sa.String(20))),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("output_format", sa.String(10), nullable=False, server_default="pdf"),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("file_path", sa.Text),
        sa.Column("download_url", sa.Text),
        sa.Column("url_expires_at", sa.DateTime(timezone=True)),
        sa.Column("file_size_bytes", sa.BigInteger),
        sa.Column("error_message", sa.Text),
        sa.Column("generated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("output_format IN ('pdf','csv','json')", name="chk_report_format"),
        sa.CheckConstraint(
            "status IN ('queued','generating','ready','failed')",
            name="chk_report_status",
        ),
    )
    op.create_index("idx_reports_status", "reports", ["status", sa.text("created_at DESC")])
    op.create_index("idx_reports_user", "reports", ["requested_by", sa.text("created_at DESC")])


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("model_registry")
    op.drop_table("node_health_snapshots")
    op.drop_table("audit_logs")
    op.drop_table("alert_notifications")
    op.drop_table("users")
    op.drop_table("alerts")
    op.drop_table("risk_scores")
    op.drop_table("sensor_readings")
    op.drop_table("sensor_nodes")
    op.drop_table("slopes")
