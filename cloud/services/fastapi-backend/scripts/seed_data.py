"""ILEWS seed script – populates the database with initial sample data."""

import asyncio
import sys
from pathlib import Path

from passlib.hash import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Allow running from repo root: python -m scripts.seed_data
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import async_session_factory, engine  # noqa: E402
from app.models import Slope, SensorNode, User  # noqa: E402


ADMIN_USER = {
    "user_id": "USR-0001",
    "email": "admin@ilews.gov",
    "name": "System Administrator",
    "role": "system_admin",
    "organisation": "ILEWS Operations",
    "phone": "+60123456789",
    "is_active": True,
    "is_sms_alert_enabled": True,
    "is_push_alert_enabled": True,
    "password_hash": bcrypt.hash("changeme123"),
    "created_by": "seed_script",
}

SLOPES = [
    {
        "slope_id": "SLOPE_BKT_01",
        "name": "Bukit Antarabangsa Slope A",
        "description": "High-risk residential slope monitored since 2025.",
        "location_name": "Bukit Antarabangsa, Ampang, Selangor",
        "latitude_centroid": 3.2150,
        "longitude_centroid": 101.7647,
        "area_m2": 45000.00,
        "monitoring_status": "active",
        "created_by": "seed_script",
    },
    {
        "slope_id": "SLOPE_CMH_01",
        "name": "Cameron Highlands Cut Slope B",
        "description": "Agricultural terrace slope along main road.",
        "location_name": "Ringlet, Cameron Highlands, Pahang",
        "latitude_centroid": 4.3975,
        "longitude_centroid": 101.3894,
        "area_m2": 32000.00,
        "monitoring_status": "active",
        "created_by": "seed_script",
    },
]

NODES_PER_SLOPE = [
    # Bukit Antarabangsa – 3 nodes
    [
        {
            "node_id": "BKT01-A1",
            "slope_id": "SLOPE_BKT_01",
            "name": "BKT01 Upper Ridge Node",
            "latitude": 3.2155,
            "longitude": 101.7650,
            "firmware_version": "1.0.0",
            "hardware_revision": "rev3",
            "status": "active",
        },
        {
            "node_id": "BKT01-A2",
            "slope_id": "SLOPE_BKT_01",
            "name": "BKT01 Mid-Slope Node",
            "latitude": 3.2148,
            "longitude": 101.7645,
            "firmware_version": "1.0.0",
            "hardware_revision": "rev3",
            "status": "active",
        },
        {
            "node_id": "BKT01-A3",
            "slope_id": "SLOPE_BKT_01",
            "name": "BKT01 Toe Drainage Node",
            "latitude": 3.2142,
            "longitude": 101.7643,
            "firmware_version": "1.0.0",
            "hardware_revision": "rev3",
            "status": "active",
        },
    ],
    # Cameron Highlands – 3 nodes
    [
        {
            "node_id": "CMH01-B1",
            "slope_id": "SLOPE_CMH_01",
            "name": "CMH01 Road-Cut Top",
            "latitude": 4.3980,
            "longitude": 101.3897,
            "firmware_version": "1.0.0",
            "hardware_revision": "rev3",
            "status": "active",
        },
        {
            "node_id": "CMH01-B2",
            "slope_id": "SLOPE_CMH_01",
            "name": "CMH01 Terrace Mid",
            "latitude": 4.3973,
            "longitude": 101.3892,
            "firmware_version": "1.0.0",
            "hardware_revision": "rev3",
            "status": "active",
        },
        {
            "node_id": "CMH01-B3",
            "slope_id": "SLOPE_CMH_01",
            "name": "CMH01 Stream Bank",
            "latitude": 4.3968,
            "longitude": 101.3889,
            "firmware_version": "1.0.0",
            "hardware_revision": "rev3",
            "status": "active",
        },
    ],
]


async def seed() -> None:
    async with async_session_factory() as session:
        session: AsyncSession

        # -- Admin user --
        exists = await session.execute(
            text("SELECT 1 FROM users WHERE user_id = :uid"),
            {"uid": ADMIN_USER["user_id"]},
        )
        if exists.scalar() is None:
            session.add(User(**ADMIN_USER))
            await session.flush()
            print(f"✓ Created user: {ADMIN_USER['email']} (role={ADMIN_USER['role']})")
        else:
            print(f"• User already exists: {ADMIN_USER['email']}")

        # -- Slopes --
        for slope_data in SLOPES:
            exists = await session.execute(
                text("SELECT 1 FROM slopes WHERE slope_id = :sid"),
                {"sid": slope_data["slope_id"]},
            )
            if exists.scalar() is None:
                session.add(Slope(**slope_data))
                await session.flush()
                print(f"✓ Created slope: {slope_data['slope_id']} – {slope_data['name']}")
            else:
                print(f"• Slope already exists: {slope_data['slope_id']}")

        # -- Sensor nodes --
        for slope_nodes in NODES_PER_SLOPE:
            for node_data in slope_nodes:
                exists = await session.execute(
                    text("SELECT 1 FROM sensor_nodes WHERE node_id = :nid"),
                    {"nid": node_data["node_id"]},
                )
                if exists.scalar() is None:
                    session.add(SensorNode(**node_data))
                    await session.flush()
                    print(
                        f"✓ Created node: {node_data['node_id']} "
                        f"on slope {node_data['slope_id']}"
                    )
                else:
                    print(f"• Node already exists: {node_data['node_id']}")

        await session.commit()
        print("\n✅ Seed complete.")


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
