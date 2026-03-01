"""ILEWS ML Pipeline – LSTM model architecture (TensorFlow/Keras)."""

import tensorflow as tf
from tensorflow import keras
from loguru import logger


def build_lstm_model(
    timesteps: int,
    n_features: int,
    learning_rate: float = 0.001,
) -> keras.Model:
    """Build and compile the LSTM model for slope risk prediction.

    Architecture:
        Input(timesteps, n_features)
        → LSTM(128, return_sequences=True)
        → Dropout(0.2)
        → LSTM(64, return_sequences=False)
        → Dropout(0.2)
        → Dense(32, activation='relu')
        → Dense(1, activation='sigmoid')

    Args:
        timesteps: Number of time steps in input sequences.
        n_features: Number of features per time step.
        learning_rate: Adam optimizer learning rate.

    Returns:
        Compiled Keras model.
    """
    model = keras.Sequential([
        keras.layers.Input(shape=(timesteps, n_features)),
        keras.layers.LSTM(128, return_sequences=True),
        keras.layers.Dropout(0.2),
        keras.layers.LSTM(64, return_sequences=False),
        keras.layers.Dropout(0.2),
        keras.layers.Dense(32, activation="relu"),
        keras.layers.Dense(1, activation="sigmoid"),
    ])

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="binary_crossentropy",
        metrics=[
            keras.metrics.AUC(name="auc"),
            keras.metrics.Precision(name="precision"),
            keras.metrics.Recall(name="recall"),
        ],
    )

    logger.info(
        f"LSTM model built: timesteps={timesteps}, "
        f"features={n_features}, params={model.count_params()}"
    )

    return model


def export_tflite(model: keras.Model, output_path: str) -> str:
    """Export Keras model to TFLite format for edge deployment.

    Args:
        model: Trained Keras model.
        output_path: Path to save the .tflite file.

    Returns:
        Path to the saved TFLite model.
    """
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    # LSTM ops require Select TF ops for TFLite conversion
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS,
        tf.lite.OpsSet.SELECT_TF_OPS,
    ]
    converter._experimental_lower_tensor_list_ops = False
    tflite_model = converter.convert()

    with open(output_path, "wb") as f:
        f.write(tflite_model)

    logger.info(
        f"TFLite model exported to {output_path} "
        f"({len(tflite_model)} bytes)"
    )
    return output_path
