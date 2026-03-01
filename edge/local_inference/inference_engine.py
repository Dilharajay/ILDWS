"""ILEWS Edge – TFLite inference engine for on-device risk scoring."""

import os

import numpy as np
from loguru import logger


class EdgeInferenceEngine:
    """Wraps TFLite model for edge inference."""

    def __init__(self):
        self._interpreter = None
        self._input_details = None
        self._output_details = None
        self._loaded = False

    def load_model(self, path: str) -> bool:
        """Load a TFLite model from disk.

        Args:
            path: Path to .tflite model file.

        Returns:
            True if loaded successfully.
        """
        if not os.path.exists(path):
            logger.warning(f"Model file not found: {path}")
            return False

        try:
            # Try tflite_runtime first (lighter, preferred on edge)
            try:
                import tflite_runtime.interpreter as tflite
                self._interpreter = tflite.Interpreter(model_path=path)
            except ImportError:
                # Fall back to full TensorFlow
                import tensorflow as tf
                self._interpreter = tf.lite.Interpreter(model_path=path)

            self._interpreter.allocate_tensors()
            self._input_details = self._interpreter.get_input_details()
            self._output_details = self._interpreter.get_output_details()
            self._loaded = True

            input_shape = self._input_details[0]["shape"]
            logger.info(
                f"TFLite model loaded from {path}, "
                f"input shape: {input_shape}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to load TFLite model: {e}")
            self._loaded = False
            return False

    def is_model_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self._loaded

    def predict(self, feature_window: np.ndarray) -> float:
        """Run inference on a feature window.

        Args:
            feature_window: Input array of shape (1, timesteps, features)
                           or (timesteps, features).

        Returns:
            Risk score in range [0, 1].
        """
        if not self._loaded:
            raise RuntimeError("No model loaded")

        # Ensure correct shape (add batch dim if needed)
        if feature_window.ndim == 2:
            feature_window = np.expand_dims(feature_window, axis=0)

        # Ensure float32
        input_data = feature_window.astype(np.float32)

        # Resize input tensor if needed
        expected_shape = self._input_details[0]["shape"]
        if not np.array_equal(input_data.shape, expected_shape):
            self._interpreter.resize_tensor_input(
                self._input_details[0]["index"], input_data.shape
            )
            self._interpreter.allocate_tensors()

        self._interpreter.set_tensor(
            self._input_details[0]["index"], input_data
        )
        self._interpreter.invoke()

        output = self._interpreter.get_tensor(
            self._output_details[0]["index"]
        )
        score = float(output.flatten()[0])

        # Clamp to [0, 1]
        return max(0.0, min(1.0, score))
