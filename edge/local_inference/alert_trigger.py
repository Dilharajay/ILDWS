"""ILEWS Edge – Alert trigger with siren activation.

Checks risk scores against thresholds and activates the local siren
via GPIO when RED alert threshold is exceeded.
"""

import time
import threading

from loguru import logger

# Default threshold for RED alert
DEFAULT_RED_THRESHOLD = 0.85
SIREN_DURATION_SECONDS = 300  # 5 minutes


class AlertTrigger:
    """Manages alert detection and siren control."""

    def __init__(
        self,
        db_conn,
        red_threshold: float = DEFAULT_RED_THRESHOLD,
        gpio_pin: int = 17,
    ):
        self.conn = db_conn
        self.red_threshold = red_threshold
        self.gpio_pin = gpio_pin
        self._siren_active = False
        self._siren_timer = None
        self._gpio = None

        # Try to initialize GPIO
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_pin, GPIO.OUT)
            GPIO.output(self.gpio_pin, GPIO.LOW)
            self._gpio = GPIO
            logger.info(f"GPIO initialized on pin {self.gpio_pin}")
        except (ImportError, RuntimeError):
            logger.warning(
                "RPi.GPIO not available — siren will use mock output"
            )

    def check_and_trigger(self, risk_score: float) -> str:
        """Check risk score and trigger alert if needed.

        Args:
            risk_score: Model output in [0, 1].

        Returns:
            Risk level string (GREEN/YELLOW/ORANGE/RED).
        """
        risk_level = self._score_to_level(risk_score)

        if risk_score >= self.red_threshold:
            logger.warning(
                f"RED ALERT: score={risk_score:.4f}, "
                f"activating siren"
            )
            self.activate_siren()
            self._log_alert(risk_score, risk_level, siren=True)
        elif risk_score >= 0.65:
            logger.warning(
                f"ORANGE WARNING: score={risk_score:.4f}"
            )
            self._log_alert(risk_score, risk_level, siren=False)
        elif risk_score >= 0.40:
            logger.info(f"YELLOW ADVISORY: score={risk_score:.4f}")

        return risk_level

    def activate_siren(self) -> None:
        """Activate the siren (GPIO or mock)."""
        if self._siren_active:
            logger.debug("Siren already active")
            return

        self._siren_active = True

        if self._gpio:
            self._gpio.output(self.gpio_pin, self._gpio.HIGH)
            logger.info(f"SIREN ON (GPIO pin {self.gpio_pin})")
        else:
            logger.warning(
                f"[MOCK SIREN] ACTIVATED on pin {self.gpio_pin} "
                f"(GPIO not available)"
            )

        # Auto-deactivate after duration
        self._siren_timer = threading.Timer(
            SIREN_DURATION_SECONDS, self.deactivate_siren
        )
        self._siren_timer.daemon = True
        self._siren_timer.start()

    def deactivate_siren(self) -> None:
        """Deactivate the siren."""
        self._siren_active = False

        if self._gpio:
            self._gpio.output(self.gpio_pin, self._gpio.LOW)
            logger.info(f"SIREN OFF (GPIO pin {self.gpio_pin})")
        else:
            logger.warning(
                f"[MOCK SIREN] DEACTIVATED on pin {self.gpio_pin}"
            )

        if self._siren_timer:
            self._siren_timer.cancel()
            self._siren_timer = None

    def _log_alert(
        self, score: float, level: str, siren: bool
    ) -> None:
        """Log alert to SQLite."""
        try:
            self.conn.execute(
                "INSERT INTO local_alerts "
                "(risk_score, risk_level, siren_activated) "
                "VALUES (?, ?, ?)",
                (score, level, 1 if siren else 0),
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to log local alert: {e}")

    @staticmethod
    def _score_to_level(score: float) -> str:
        """Map score to risk level."""
        if score <= 0.39:
            return "GREEN"
        elif score <= 0.64:
            return "YELLOW"
        elif score <= 0.84:
            return "ORANGE"
        else:
            return "RED"
