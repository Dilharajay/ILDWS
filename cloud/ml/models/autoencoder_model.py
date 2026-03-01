"""ILEWS ML Pipeline – Autoencoder model for anomaly detection fallback."""

import tensorflow as tf
from tensorflow import keras
from loguru import logger


def build_autoencoder_model(
    timesteps: int,
    n_features: int,
    encoding_dim: int = 32,
    learning_rate: float = 0.001,
) -> keras.Model:
    """Build autoencoder for anomaly detection on sensor data.

    Used as a fallback when insufficient labeled data exists for
    supervised LSTM training. Detects anomalous sensor patterns
    based on reconstruction error.

    Args:
        timesteps: Number of time steps in input sequences.
        n_features: Number of features per time step.
        encoding_dim: Dimension of the encoded representation.
        learning_rate: Adam optimizer learning rate.

    Returns:
        Compiled Keras autoencoder model.
    """
    # Encoder
    inputs = keras.layers.Input(shape=(timesteps, n_features))
    x = keras.layers.LSTM(64, return_sequences=True)(inputs)
    x = keras.layers.Dropout(0.2)(x)
    x = keras.layers.LSTM(encoding_dim, return_sequences=False)(x)
    encoded = keras.layers.Dense(encoding_dim, activation="relu")(x)

    # Decoder
    x = keras.layers.RepeatVector(timesteps)(encoded)
    x = keras.layers.LSTM(encoding_dim, return_sequences=True)(x)
    x = keras.layers.Dropout(0.2)(x)
    x = keras.layers.LSTM(64, return_sequences=True)(x)
    decoded = keras.layers.TimeDistributed(
        keras.layers.Dense(n_features)
    )(x)

    model = keras.Model(inputs, decoded)
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="mse",
    )

    logger.info(
        f"Autoencoder model built: timesteps={timesteps}, "
        f"features={n_features}, encoding_dim={encoding_dim}, "
        f"params={model.count_params()}"
    )

    return model


def compute_anomaly_scores(
    model: keras.Model,
    sequences: tf.Tensor,
) -> list[float]:
    """Compute anomaly scores as reconstruction error.

    Args:
        model: Trained autoencoder model.
        sequences: Input sequences of shape (N, timesteps, features).

    Returns:
        List of anomaly scores (MSE per sequence).
    """
    predictions = model.predict(sequences, verbose=0)
    mse = tf.reduce_mean(
        tf.square(sequences - predictions), axis=[1, 2]
    )
    return mse.numpy().tolist()
