"""Métricas sobre datos no usados para ajustar."""
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)


def calcular_metricas(y_real, y_pred) -> dict:
    """Precision, recall y F1 de la clase 1 (ataque), más accuracy y matriz de confusión."""
    return {
        "precision": float(precision_score(y_real, y_pred, zero_division=0)),
        "recall": float(recall_score(y_real, y_pred, zero_division=0)),
        "f1": float(f1_score(y_real, y_pred, zero_division=0)),
        "accuracy": float(accuracy_score(y_real, y_pred)),
        "matriz_confusion": confusion_matrix(y_real, y_pred, labels=[0, 1]).tolist(),
    }
