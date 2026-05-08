"""Model performance comparison and confidence calibration analysis."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional

from database import get_db, User, ClassificationLog, ClassificationFeedback
from auth import get_optional_user
from logger_config import logger

router = APIRouter(prefix="/api/v1", tags=["models"])


class ConfidenceCalibration(BaseModel):
    """Confidence calibration metrics for a model."""
    model: str
    confidence_bins: dict  # {bin: {"expected_accuracy": %, "actual_accuracy": %}}
    calibration_error: float  # Mean absolute difference between expected and actual
    is_well_calibrated: bool  # True if |difference| < 5%
    over_confident: bool  # True if model confidence > actual accuracy


class ModelPerformanceMetric(BaseModel):
    """Performance metrics for a single model."""
    model: str
    total_classifications: int
    feedback_count: int
    accuracy_percentage: float
    precision_by_label: dict  # {label: precision}
    recall_by_label: dict  # {label: recall}
    f1_by_label: dict  # {label: f1}
    avg_confidence: float
    confidence_accuracy_correlation: float  # How well confidence predicts accuracy


class ModelComparison(BaseModel):
    """Comparison across multiple models."""
    period_days: int
    models: list[ModelPerformanceMetric]
    best_model_overall: str
    best_model_by_label: dict  # {label: best_model}
    calibration_analysis: dict  # {model: ConfidenceCalibration}


def calculate_confidence_calibration(
    classifications: list,
    feedback_map: dict,
    confidence_bins: int = 5
) -> dict:
    """Calculate confidence calibration for predictions.

    Confidence calibration measures if the model's confidence matches reality:
    - Well-calibrated: 90% confidence = 90% accuracy
    - Over-confident: 90% confidence but only 70% accuracy
    - Under-confident: 70% confidence but 90% accuracy
    """
    # Create confidence bins
    bin_width = 1.0 / confidence_bins
    bins = {}

    for i in range(confidence_bins):
        bin_key = f"{round(i * bin_width, 2)}-{round((i + 1) * bin_width, 2)}"
        bins[bin_key] = {"predictions": 0, "correct": 0}

    # Populate bins
    calibration_errors = []

    for classification in classifications:
        feedback = feedback_map.get(classification.id)
        if feedback and feedback.is_correct is not None:
            confidence = classification.confidence

            # Find appropriate bin
            bin_index = min(int(confidence / bin_width), confidence_bins - 1)
            bin_key = f"{round(bin_index * bin_width, 2)}-{round((bin_index + 1) * bin_width, 2)}"

            bins[bin_key]["predictions"] += 1
            if feedback.is_correct:
                bins[bin_key]["correct"] += 1

    # Calculate accuracy per bin
    calibration_result = {}
    for bin_key, data in bins.items():
        if data["predictions"] > 0:
            bin_center = (float(bin_key.split("-")[0]) + float(bin_key.split("-")[1])) / 2
            actual_accuracy = (data["correct"] / data["predictions"]) * 100
            expected_accuracy = bin_center * 100

            calibration_result[bin_key] = {
                "expected_accuracy": round(expected_accuracy, 1),
                "actual_accuracy": round(actual_accuracy, 1),
                "count": data["predictions"]
            }

            calibration_errors.append(abs(expected_accuracy - actual_accuracy))

    # Overall calibration metrics
    mean_calibration_error = sum(calibration_errors) / len(calibration_errors) if calibration_errors else 0

    return {
        "bins": calibration_result,
        "mean_calibration_error": round(mean_calibration_error, 2),
        "is_well_calibrated": mean_calibration_error < 5.0,
        "over_confident": sum(
            data["actual_accuracy"] < data["expected_accuracy"]
            for data in calibration_result.values()
        ) > len(calibration_result) / 2
    }


def calculate_precision_recall_f1(classifications: list, feedback_map: dict, label: str) -> dict:
    """Calculate precision, recall, and F1 for a specific label."""
    tp = 0  # True positives
    fp = 0  # False positives
    fn = 0  # False negatives

    for classification in classifications:
        feedback = feedback_map.get(classification.id)
        if feedback and feedback.is_correct is not None:
            actual_label = feedback.correct_label if not feedback.is_correct else classification.label
            predicted_label = classification.label

            if predicted_label == label:
                if actual_label == label:
                    tp += 1
                else:
                    fp += 1
            else:
                if actual_label == label:
                    fn += 1

    precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0
    recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3)
    }


def calculate_confidence_accuracy_correlation(
    classifications: list,
    feedback_map: dict
) -> float:
    """Calculate correlation between model confidence and actual accuracy.

    Returns value between -1 and 1:
    - 1.0: Perfect correlation (high confidence → high accuracy)
    - 0.5: Moderate correlation
    - 0.0: No correlation
    - Negative: Inverse correlation (bad signal)
    """
    if not classifications:
        return 0.0

    confidences = []
    accuracies = []

    for classification in classifications:
        feedback = feedback_map.get(classification.id)
        if feedback and feedback.is_correct is not None:
            confidences.append(classification.confidence)
            accuracies.append(1.0 if feedback.is_correct else 0.0)

    if len(confidences) < 2:
        return 0.0

    # Calculate correlation
    mean_conf = sum(confidences) / len(confidences)
    mean_acc = sum(accuracies) / len(accuracies)

    numerator = sum(
        (conf - mean_conf) * (acc - mean_acc)
        for conf, acc in zip(confidences, accuracies)
    )

    denominator = (
        sum((conf - mean_conf) ** 2 for conf in confidences) ** 0.5 *
        sum((acc - mean_acc) ** 2 for acc in accuracies) ** 0.5
    )

    correlation = numerator / denominator if denominator > 0 else 0.0
    return round(correlation, 3)


@router.get("/models/comparison", response_model=ModelComparison)
def get_model_comparison(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Compare performance across all models."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(ClassificationLog).filter(
        ClassificationLog.success == True,
        ClassificationLog.timestamp >= cutoff_date
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    classifications = query.all()

    if not classifications:
        return ModelComparison(
            period_days=days,
            models=[],
            best_model_overall="",
            best_model_by_label={},
            calibration_analysis={}
        )

    # Group by model
    models_data = {}
    for classification in classifications:
        model = getattr(classification, "model", "llama-3.1-70b-instruct")
        if model not in models_data:
            models_data[model] = []
        models_data[model].append(classification)

    # Get feedback
    feedback_query = db.query(ClassificationFeedback).filter(
        ClassificationFeedback.created_at >= cutoff_date
    )
    if current_user:
        feedback_query = feedback_query.filter(ClassificationFeedback.user_id == current_user.id)

    feedbacks = feedback_query.all()
    feedback_map = {f.classification_id: f for f in feedbacks}

    # Calculate metrics per model
    model_metrics = []
    model_accuracies = {}

    for model, classifications_for_model in models_data.items():
        total = len(classifications_for_model)

        # Accuracy
        correct_count = 0
        feedback_count = 0

        for classification in classifications_for_model:
            feedback = feedback_map.get(classification.id)
            if feedback and feedback.is_correct is not None:
                feedback_count += 1
                if feedback.is_correct:
                    correct_count += 1

        accuracy = (correct_count / feedback_count * 100) if feedback_count > 0 else 0
        model_accuracies[model] = accuracy

        # Precision, recall, F1 per label
        precision_by_label = {}
        recall_by_label = {}
        f1_by_label = {}

        for label in ["PHISHING", "SPAM", "LEGITIMATE"]:
            metrics = calculate_precision_recall_f1(classifications_for_model, feedback_map, label)
            precision_by_label[label] = metrics["precision"]
            recall_by_label[label] = metrics["recall"]
            f1_by_label[label] = metrics["f1"]

        # Confidence metrics
        avg_confidence = (
            sum(c.confidence for c in classifications_for_model) / total
            if total > 0 else 0
        )

        # Confidence-accuracy correlation
        correlation = calculate_confidence_accuracy_correlation(
            classifications_for_model, feedback_map
        )

        metric = ModelPerformanceMetric(
            model=model,
            total_classifications=total,
            feedback_count=feedback_count,
            accuracy_percentage=round(accuracy, 2),
            precision_by_label=precision_by_label,
            recall_by_label=recall_by_label,
            f1_by_label=f1_by_label,
            avg_confidence=round(avg_confidence, 3),
            confidence_accuracy_correlation=correlation
        )

        model_metrics.append(metric)

    # Find best model overall
    best_model = max(model_metrics, key=lambda x: x.accuracy_percentage).model if model_metrics else ""

    # Find best model per label
    best_by_label = {}
    for label in ["PHISHING", "SPAM", "LEGITIMATE"]:
        best = max(
            model_metrics,
            key=lambda x: x.f1_by_label.get(label, 0)
        )
        best_by_label[label] = best.model

    # Calibration analysis
    calibration_analysis = {}
    for model, classifications_for_model in models_data.items():
        cal = calculate_confidence_calibration(classifications_for_model, feedback_map)
        calibration_analysis[model] = cal

    return ModelComparison(
        period_days=days,
        models=sorted(model_metrics, key=lambda x: x.accuracy_percentage, reverse=True),
        best_model_overall=best_model,
        best_model_by_label=best_by_label,
        calibration_analysis=calibration_analysis
    )


@router.get("/models/{model}/calibration")
def get_model_calibration(
    model: str,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get detailed confidence calibration for a specific model."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(ClassificationLog).filter(
        ClassificationLog.model == model,
        ClassificationLog.success == True,
        ClassificationLog.timestamp >= cutoff_date
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    classifications = query.all()

    if not classifications:
        return {"model": model, "message": "No data available"}

    # Get feedback
    feedback_query = db.query(ClassificationFeedback).filter(
        ClassificationFeedback.created_at >= cutoff_date
    )
    if current_user:
        feedback_query = feedback_query.filter(ClassificationFeedback.user_id == current_user.id)

    feedbacks = feedback_query.all()
    feedback_map = {f.classification_id: f for f in feedbacks}

    calibration = calculate_confidence_calibration(classifications, feedback_map)

    return {
        "model": model,
        "period_days": days,
        "calibration": calibration,
        "interpretation": (
            "Well-calibrated model - confidence matches accuracy" if calibration["is_well_calibrated"]
            else ("Over-confident model - reports higher confidence than justified" if calibration["over_confident"]
                  else "Under-confident model - reports lower confidence than justified")
        )
    }
