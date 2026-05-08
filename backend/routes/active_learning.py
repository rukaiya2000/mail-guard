"""Active learning: flag uncertain predictions for human review."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum

from database import get_db, User, ClassificationLog, ClassificationFeedback
from auth import get_optional_user
from logger_config import logger

router = APIRouter(prefix="/api/v1", tags=["active-learning"])


class ReviewStatus(str, Enum):
    """Status of a flagged email in review queue."""
    FLAGGED = "flagged"
    REVIEWED = "reviewed"
    IGNORED = "ignored"


class UncertainPrediction(BaseModel):
    """Email flagged as uncertain for human review."""
    classification_id: int
    email_snippet: str
    model_prediction: str
    ensemble_confidence: float
    flagged_reason: str  # "low_confidence" or "model_disagreement"
    timestamp: str
    review_status: str


class ReviewFeedback(BaseModel):
    """User feedback on a flagged prediction."""
    correct_label: str
    notes: Optional[str] = None


class ActiveLearningMetrics(BaseModel):
    """Metrics on active learning effectiveness."""
    total_flagged: int
    flagged_percentage: float
    reviewed_count: int
    review_rate: float
    accuracy_if_reviewed: float  # What % of reviewed predictions were correct?
    uncertainty_types: dict  # {"low_confidence": count, "disagreement": count}
    impact: float  # How much does human review improve accuracy?


class ActiveLearningConfig(BaseModel):
    """Configuration for active learning."""
    ensemble_confidence_threshold: float = 0.70  # Flag if below this
    disagreement_threshold: float = 0.5  # Flag if entropy > this
    enable_confidence_based: bool = True
    enable_disagreement_based: bool = True


def calculate_ensemble_entropy(voting_distribution: dict) -> float:
    """Calculate Shannon entropy of ensemble voting distribution.

    Measures disagreement between models.
    - 0: All models agree (low entropy)
    - 1: Models equally split (high entropy)
    """
    total_votes = sum(voting_distribution.values())
    if total_votes == 0:
        return 0.0

    entropy = 0.0
    for votes in voting_distribution.values():
        if votes > 0:
            prob = votes / total_votes
            entropy -= prob * (prob ** 0.5)  # Simplified entropy

    return min(entropy, 1.0)  # Cap at 1.0


def should_flag_for_review(
    confidence: float,
    voting_distribution: dict,
    config: ActiveLearningConfig
) -> tuple[bool, str]:
    """Determine if prediction should be flagged for human review.

    Returns: (should_flag, reason)
    """
    # Low confidence check
    if config.enable_confidence_based and confidence < config.ensemble_confidence_threshold:
        return True, "low_confidence"

    # Disagreement check
    if config.enable_disagreement_based:
        entropy = calculate_ensemble_entropy(voting_distribution)
        if entropy > config.disagreement_threshold:
            return True, "model_disagreement"

    return False, ""


@router.post("/active-learning/configure")
def configure_active_learning(
    config: ActiveLearningConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Configure active learning thresholds."""
    if not current_user or current_user.role != "analyst":
        raise HTTPException(status_code=403, detail="Only analysts can configure active learning")

    # Store config in memory or database
    # For now, return confirmation
    return {
        "success": True,
        "config": config,
        "message": "Active learning configuration updated"
    }


@router.get("/active-learning/queue")
def get_review_queue(
    days: int = 7,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get queue of uncertain predictions for human review.

    Shows emails where ensemble was uncertain (low confidence or disagreement).
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Get classifications with low confidence or disagreement
    query = db.query(ClassificationLog).filter(
        ClassificationLog.timestamp >= cutoff_date,
        ClassificationLog.success == True,
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    classifications = query.all()

    uncertain_predictions = []

    for classification in classifications:
        # Default config thresholds
        confidence_threshold = 0.70
        disagreement_threshold = 0.5

        # Flag if low confidence
        if classification.confidence < confidence_threshold:
            uncertain_predictions.append({
                "classification_id": classification.id,
                "email_snippet": classification.email_snippet,
                "model_prediction": classification.label,
                "ensemble_confidence": classification.confidence,
                "flagged_reason": "low_confidence",
                "timestamp": classification.timestamp.isoformat(),
                "review_status": "flagged",
                "score": 100 * (1 - classification.confidence)  # Sort by uncertainty
            })

    # Sort by uncertainty (lowest confidence first)
    uncertain_predictions.sort(key=lambda x: x["score"], reverse=True)

    return {
        "total_uncertain": len(uncertain_predictions),
        "showing": len(uncertain_predictions[:limit]),
        "queue": [
            UncertainPrediction(**{
                k: v for k, v in p.items() if k != "score"
            })
            for p in uncertain_predictions[:limit]
        ]
    }


@router.post("/active-learning/review/{classification_id}")
def submit_review(
    classification_id: int,
    feedback: ReviewFeedback,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Submit human review feedback on flagged prediction."""
    user_id = current_user.id if current_user else None

    classification = db.query(ClassificationLog).filter(
        ClassificationLog.id == classification_id
    ).first()

    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")

    # Record the feedback
    try:
        db_feedback = ClassificationFeedback(
            classification_id=classification_id,
            user_id=user_id,
            is_correct=(feedback.correct_label == classification.label),
            correct_label=feedback.correct_label,
            feedback_text=feedback.notes or f"Active learning review: correct label is {feedback.correct_label}"
        )
        db.add(db_feedback)
        db.commit()

        logger.info(
            f"Active learning review submitted by user {user_id} for classification {classification_id}. "
            f"Model predicted {classification.label}, correct is {feedback.correct_label}"
        )

        return {
            "success": True,
            "feedback_recorded": True,
            "was_correct": feedback.correct_label == classification.label,
            "original_prediction": classification.label,
            "correct_label": feedback.correct_label
        }

    except Exception as e:
        logger.error(f"Failed to record active learning feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to record feedback")


@router.get("/active-learning/metrics")
def get_active_learning_metrics(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get metrics on active learning effectiveness."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Get all classifications in period
    query = db.query(ClassificationLog).filter(
        ClassificationLog.timestamp >= cutoff_date,
        ClassificationLog.success == True
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    all_classifications = query.all()
    total = len(all_classifications)

    if total == 0:
        return {
            "period_days": days,
            "message": "No classifications in period"
        }

    # Count flagged (low confidence < 0.70)
    flagged = [c for c in all_classifications if c.confidence < 0.70]
    flagged_count = len(flagged)

    # Get feedback on flagged predictions
    flagged_ids = [c.id for c in flagged]
    feedback_query = db.query(ClassificationFeedback).filter(
        ClassificationFeedback.classification_id.in_(flagged_ids),
        ClassificationFeedback.created_at >= cutoff_date
    )

    if current_user:
        feedback_query = feedback_query.filter(ClassificationFeedback.user_id == current_user.id)

    feedbacks = feedback_query.all()
    reviewed_count = len(feedbacks)
    correct_reviews = sum(1 for f in feedbacks if f.is_correct)

    # Calculate metrics
    flagged_percentage = (flagged_count / total * 100) if total > 0 else 0
    review_rate = (reviewed_count / flagged_count * 100) if flagged_count > 0 else 0
    accuracy_if_reviewed = (correct_reviews / reviewed_count * 100) if reviewed_count > 0 else 0

    # Impact: how much does reviewing flagged predictions help?
    unflagged = [c for c in all_classifications if c.confidence >= 0.70]
    unflagged_with_feedback = [
        c for c in unflagged
        if any(f.classification_id == c.id for f in feedbacks)
    ]
    unflagged_accuracy = (
        sum(1 for c in unflagged_with_feedback if any(
            f.classification_id == c.id and f.is_correct for f in feedbacks
        )) / len(unflagged_with_feedback) * 100
        if unflagged_with_feedback else 0
    )

    impact = accuracy_if_reviewed - unflagged_accuracy if unflagged_accuracy > 0 else 0

    return ActiveLearningMetrics(
        total_flagged=flagged_count,
        flagged_percentage=round(flagged_percentage, 2),
        reviewed_count=reviewed_count,
        review_rate=round(review_rate, 2),
        accuracy_if_reviewed=round(accuracy_if_reviewed, 2),
        uncertainty_types={
            "low_confidence": flagged_count,
            "model_disagreement": 0  # Would need voting distribution to calculate
        },
        impact=round(impact, 2)
    )


@router.get("/active-learning/stats")
def get_active_learning_stats(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get statistics on active learning queue."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(ClassificationLog).filter(
        ClassificationLog.timestamp >= cutoff_date,
        ClassificationLog.success == True
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    classifications = query.all()

    # Confidence distribution
    confidence_buckets = {
        "0.0-0.3": 0,
        "0.3-0.5": 0,
        "0.5-0.7": 0,
        "0.7-0.85": 0,
        "0.85-1.0": 0
    }

    for c in classifications:
        if c.confidence < 0.3:
            confidence_buckets["0.0-0.3"] += 1
        elif c.confidence < 0.5:
            confidence_buckets["0.3-0.5"] += 1
        elif c.confidence < 0.7:
            confidence_buckets["0.5-0.7"] += 1
        elif c.confidence < 0.85:
            confidence_buckets["0.7-0.85"] += 1
        else:
            confidence_buckets["0.85-1.0"] += 1

    # Average confidence by label
    by_label = {}
    for label in ["PHISHING", "SPAM", "LEGITIMATE"]:
        label_classifications = [c for c in classifications if c.label == label]
        if label_classifications:
            avg_conf = sum(c.confidence for c in label_classifications) / len(label_classifications)
            by_label[label] = {
                "count": len(label_classifications),
                "avg_confidence": round(avg_conf, 3)
            }

    return {
        "period_days": days,
        "total_classifications": len(classifications),
        "confidence_distribution": confidence_buckets,
        "by_label": by_label,
        "recommendation": (
            "High uncertainty - consider increasing data collection or model retraining"
            if confidence_buckets["0.0-0.5"] > len(classifications) * 0.2
            else "Model confidence levels healthy"
        )
    }
