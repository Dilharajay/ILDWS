"""ILEWS Edge Gateway – Internet connectivity checker."""

import socket

from loguru import logger


def check_internet(
    host: str = "8.8.8.8", port: int = 53, timeout: int = 3
) -> bool:
    """Check internet connectivity by attempting a TCP connection.

    Args:
        host: Host to connect to (Google DNS by default).
        port: Port to connect to (DNS port).
        timeout: Connection timeout in seconds.

    Returns:
        True if internet is reachable, False otherwise.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except (socket.timeout, OSError):
        return False
