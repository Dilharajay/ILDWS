"""ILEWS ORM models – import all models so Alembic can discover them."""

from app.models.slopes import Slope
from app.models.sensor_nodes import SensorNode
from app.models.sensor_readings import SensorReading
from app.models.risk_scores import RiskScore
from app.models.alerts import Alert
from app.models.alert_notifications import AlertNotification
from app.models.users import User
from app.models.audit_logs import AuditLog
from app.models.node_health_snapshots import NodeHealthSnapshot
from app.models.model_registry import ModelRegistry
from app.models.reports import Report

__all__ = [
    "Slope",
    "SensorNode",
    "SensorReading",
    "RiskScore",
    "Alert",
    "AlertNotification",
    "User",
    "AuditLog",
    "NodeHealthSnapshot",
    "ModelRegistry",
    "Report",
]