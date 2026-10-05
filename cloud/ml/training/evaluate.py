"""ILEWS ML Pipeline – Model evaluation metrics."""

import numpy as np
import pandas as pd
from sklearn.metrics import (
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)
from loguru import logger


def evaluate_model(
    model,
    X_test: np.ndarray,
    y_test: np.ndarray,
    timestamps: np.ndarray = None,
    threshold: float = 0.5,
) -> dict:
    """Evaluate trained model and compute all required metrics.

    Args:
        model: Trained Keras model.
        X_test: Test sequences of shape (N, timesteps, features).
        y_test: Binary labels (0=no event, 1=event).
        timestamps: Optional timestamps for lead time calculation.
        threshold: Classification threshold for predictions.

    Returns:
        Dict with auc_roc, precision, recall, f1, false_alarm_rate,
        lead_time_avg_minutes, and confusion_matrix.
    """
    y_prob = model.predict(X_test, verbose=0).flatten()
    y_pred = (y_prob >= threshold).astype(int)

    # Handle edge cases
    if len(np.unique(y_test)) < 2:
        logger.warning("Only one class in test set, AUC undefined")
        auc = 0.0
    else:
        auc = roc_auc_score(y_test, y_prob)

    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])

    # False Alarm Rate = FP / (FP + TN)
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
    far = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    # Lead time: average time from first positive prediction to actual event
    lead_time = _compute_lead_time(y_pred, y_test, timestamps)

    metrics = {
        "auc_roc": float(auc),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "false_alarm_rate": float(far),
        "lead_time_avg_minutes": float(lead_time),
        "confusion_matrix": cm.tolist(),
        "true_positives": int(tp),
        "false_positives": int(fp),
        "true_negatives": int(tn),
        "false_negatives": int(fn),
        "threshold": threshold,
        "n_test_samples": len(y_test),
    }

    logger.info(
        f"Evaluation: AUC={auc:.4f}, F1={f1:.4f}, "
        f"FAR={far:.4f}, Lead={lead_time:.1f}min"
    )

    return metrics


def _compute_lead_time(
    y_pred: np.ndarray,
    y_true: np.ndarray,
    timestamps: np.ndarray = None,
) -> float:
    """Compute average lead time before actual events.

    Lead time = time between first positive prediction and
    the actual labeled event start.
    """
    if timestamps is None:
        return 0.0

    lead_times = []
    in_event = False
    first_pred_time = None

    for i in range(len(y_true)):
        if y_pred[i] == 1 and not in_event and first_pred_time is None:
            first_pred_time = timestamps[i]

        if y_true[i] == 1 and not in_event:
            in_event = True
            if first_pred_time is not None:
                delta = timestamps[i] - first_pred_time
                if isinstance(delta, (pd.Timedelta, np.timedelta64)):
                    lead_times.append(
                        pd.Timedelta(delta).total_seconds() / 60
                    )
                else:
                    lead_times.append(float(delta) / 60)
            first_pred_time = None

        if y_true[i] == 0 and in_event:
            in_event = False
            first_pred_time = None

    return float(np.mean(lead_times)) if lead_times else 0.0
