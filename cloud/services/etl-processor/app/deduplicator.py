"""ILEWS ETL Processor – Packet deduplication via Redis.

Uses Redis keys with TTL to detect duplicate packets within a
10-minute window based on node_id + timestamp_minute.
"""

from loguru import logger

DEDUP_TTL = 600  # 10 minutes


async def is_duplicate(redis, node_id: str, timestamp: str) -> bool:
    """Check if a packet is a duplicate.

    Args:
        redis: async Redis client instance.
        node_id: Sensor node ID.
        timestamp: ISO timestamp string.

    Returns:
        True if duplicate (already seen), False if new.
    """
    # Extract minute-level key for dedup window
    ts_minute = timestamp[:16]  # YYYY-MM-DDTHH:MM
    key = f"dedup:{node_id}:{ts_minute}"

    try:
        exists = await redis.exists(key)
        if exists:
            logger.debug(f"Duplicate packet detected: {key}")
            return True

        # Mark as seen with TTL
        await redis.set(key, "1", ex=DEDUP_TTL)
        return False
    except Exception as e:
        logger.warning(f"Redis dedup check failed: {e}; allowing packet through")
        return False
