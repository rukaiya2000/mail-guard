"""User feedback and model accuracy tracking routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from typing import Optional

from database import get_db, User, ClassificationLog, ClassificationFeedback
from auth import get_current_user
from logger_config import logger

router = APIRouter(prefix="/api/v1", tags=["feedback"])


class FeedbackRequest(BaseModel):
    """Request schema for classification feedback."""
    classification_id: int
    is_correct: bool = Field(..., description="True if classification was correct")
    correct_label: Optional[str] = Field(None, description="If incorrect, what should it be?")
    feedback_text: Optional[str] = Field(None, max_length=500)


class FeedbackResponse(BaseModel):
    """Response schema for feedback."""
    id: int
    classification_id: int
    is_correct: bool
    correct_label: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ModelAccuracyMetrics(BaseModel):
    """Model accuracy metrics."""
    total_feedbacks: int
    correct_count: int
    incorrect_count: int
    accuracy_percentage: float
    by_label: dict  # {label: {correct: int, total: int, accuracy: float}}
    by_model: dict  # {model: {accuracy: float, count: int}}
    by_prompt_version: dict  # {version: {accuracy: float, count: int}}


@router.post("/classifications/{classification_id}/feedback", response_model=FeedbackResponse)
def submit_feedback(
    classification_id: int,
    feedback: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit feedback on a classification result."""
    # Verify classification exists and belongs to user
    classification = db.query(ClassificationLog).filter(
        ClassificationLog.id == classification_id,
        ClassificationLog.user_id == current_user.id
    ).first()

    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")

    # Check if feedback already exists
    existing_feedback = db.query(ClassificationFeedback).filter(
        ClassificationFeedback.classification_id == classification_id,
        ClassificationFeedback.user_id == current_user.id
    ).first()

    if existing_feedback:
        # Update existing feedback
        existing_feedback.is_correct = feedback.is_correct
        existing_feedback.correct_label = feedback.correct_label
        existing_feedback.feedback_text = feedback.feedback_text
        db.commit()
        db.refresh(existing_feedback)
        logger.info(f"Updated feedback for classification {classification_id}")
        return existing_feedback

    # Create new feedback
    new_feedback = ClassificationFeedback(
        classification_id=classification_id,
        user_id=current_user.id,
        is_correct=feedback.is_correct,
        correct_label=feedback.correct_label,
        feedback_text=feedback.feedback_text,
    )
    db.add(new_feedback)
    db.commit()
    db.refresh(new_feedback)

    logger.info(f"Feedback submitted for classification {classification_id}: {feedback.is_correct}")
    return new_feedback


@router.get("/feedback/accuracy", response_model=ModelAccuracyMetrics)
def get_model_accuracy(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get model accuracy metrics based on user feedback."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Get feedbacks
    feedbacks = db.query(ClassificationFeedback, ClassificationLog).join(
        ClassificationLog,
        ClassificationFeedback.classification_id == ClassificationLog.id
    ).filter(
        ClassificationFeedback.user_id == current_user.id,
        ClassificationFeedback.created_at >= cutoff_date,
        ClassificationFeedback.is_correct.isnot(None)
    ).all()

    if not feedbacks:
        return ModelAccuracyMetrics(
            total_feedbacks=0,
            correct_count=0,
            incorrect_count=0,
            accuracy_percentage=0.0,
            by_label={},
            by_model={},
            by_prompt_version={}
        )

    # Calculate overall metrics
    correct_count = sum(1 for f, _ in feedbacks if f.is_correct)
    incorrect_count = sum(1 for f, _ in feedbacks if not f.is_correct)
    total_feedbacks = len(feedbacks)
    accuracy_percentage = (correct_count / total_feedbacks * 100) if total_feedbacks > 0 else 0

    # By label
    by_label = {}
    for feedback, classification in feedbacks:
        label = classification.label
        if label not in by_label:
            by_label[label] = {"correct": 0, "total": 0}
        by_label[label]["total"] += 1
        if feedback.is_correct:
            by_label[label]["correct"] += 1

    for label in by_label:
        total = by_label[label]["total"]
        by_label[label]["accuracy"] = (by_label[label]["correct"] / total * 100) if total > 0 else 0

    # By model
    by_model = {}
    for feedback, classification in feedbacks:
        model = getattr(classification, "model", "unknown")
        if model not in by_model:
            by_model[model] = {"correct": 0, "total": 0}
        by_model[model]["total"] += 1
        if feedback.is_correct:
            by_model[model]["correct"] += 1

    for model in by_model:
        total = by_model[model]["total"]
        by_model[model]["accuracy"] = (by_model[model]["correct"] / total * 100) if total > 0 else 0

    # By prompt version
    by_prompt_version = {}
    for feedback, classification in feedbacks:
        prompt_version = getattr(classification, "prompt_version", "v2")
        if prompt_version not in by_prompt_version:
            by_prompt_version[prompt_version] = {"correct": 0, "total": 0}
        by_prompt_version[prompt_version]["total"] += 1
        if feedback.is_correct:
            by_prompt_version[prompt_version]["correct"] += 1

    for version in by_prompt_version:
        total = by_prompt_version[version]["total"]
        by_prompt_version[version]["accuracy"] = (by_prompt_version[version]["correct"] / total * 100) if total > 0 else 0

    return ModelAccuracyMetrics(
        total_feedbacks=total_feedbacks,
        correct_count=correct_count,
        incorrect_count=incorrect_count,
        accuracy_percentage=round(accuracy_percentage, 2),
        by_label=by_label,
        by_model={k: {"accuracy": v["accuracy"], "count": v["total"]} for k, v in by_model.items()},
        by_prompt_version={k: {"accuracy": v["accuracy"], "count": v["total"]} for k, v in by_prompt_version.items()}
    )


@router.get("/feedback/recent")
def get_recent_feedback(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent user feedback."""
    feedbacks = db.query(ClassificationFeedback).filter(
        ClassificationFeedback.user_id == current_user.id
    ).order_by(
        ClassificationFeedback.created_at.desc()
    ).limit(limit).all()

    return [
        {
            "id": f.id,
            "classification_id": f.classification_id,
            "is_correct": f.is_correct,
            "correct_label": f.correct_label,
            "feedback_text": f.feedback_text,
            "created_at": f.created_at,
        }
        for f in feedbacks
    ]
