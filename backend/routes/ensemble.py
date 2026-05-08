"""Ensemble classification combining multiple models for improved accuracy."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from classifier import classify_email
from database import get_db, User
from auth import get_optional_user
from logger_config import logger

router = APIRouter(prefix="/api/v1", tags=["ensemble"])


class EnsembleClassificationRequest(BaseModel):
    """Request for ensemble classification."""
    email_text: str
    models: Optional[list[str]] = None  # If None, use default ensemble
    prompt_version: Optional[str] = "v4"


class ModelPrediction(BaseModel):
    """Individual model prediction."""
    model: str
    label: str
    confidence: float
    reasoning: str


class EnsembleClassificationResponse(BaseModel):
    """Ensemble classification combining multiple models."""
    email_text: str
    ensemble_label: str
    ensemble_confidence: float
    ensemble_reasoning: str

    # Detailed results from each model
    predictions: list[ModelPrediction]

    # Voting results
    voting_distribution: dict  # {label: vote_count}
    confidence_distribution: dict  # {label: avg_confidence}

    # Agreement metrics
    consensus_percentage: float  # How much models agree on top choice


# Default ensemble: combination of cost-effective and capable models
DEFAULT_ENSEMBLE_MODELS = [
    "gpt-4-turbo",
    "llama-3.1-70b-instruct",
    "claude-3-opus",
]

# Lightweight ensemble for faster inference
FAST_ENSEMBLE_MODELS = [
    "gpt-3.5-turbo",
    "llama-3.1-70b-instruct",
]


def aggregate_predictions(predictions: list[dict]) -> dict:
    """Aggregate multiple model predictions using weighted voting.

    Weights models by confidence to favor high-confidence predictions.
    """
    if not predictions:
        raise ValueError("No predictions to aggregate")

    # Voting: weighted by model confidence
    label_votes = {}
    label_confidences = {}

    for pred in predictions:
        label = pred["label"]
        confidence = pred["confidence"]

        if label not in label_votes:
            label_votes[label] = 0
            label_confidences[label] = []

        # Weight vote by confidence
        label_votes[label] += confidence
        label_confidences[label].append(confidence)

    # Calculate average confidence per label
    avg_confidences = {}
    for label in label_confidences:
        avg_confidences[label] = sum(label_confidences[label]) / len(label_confidences[label])

    # Find ensemble prediction (highest weighted vote)
    ensemble_label = max(label_votes.items(), key=lambda x: x[1])[0]
    ensemble_confidence = avg_confidences[ensemble_label]

    # Consensus percentage: what % of models predicted the top choice?
    consensus_votes = sum(1 for p in predictions if p["label"] == ensemble_label)
    consensus_percentage = (consensus_votes / len(predictions)) * 100

    return {
        "ensemble_label": ensemble_label,
        "ensemble_confidence": ensemble_confidence,
        "voting_distribution": label_votes,
        "confidence_distribution": avg_confidences,
        "consensus_percentage": consensus_percentage,
        "predictions": predictions
    }


@router.post("/classify/ensemble", response_model=EnsembleClassificationResponse)
def classify_email_ensemble(
    request: EnsembleClassificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Classify email using ensemble of multiple models.

    Combines predictions from multiple LLMs using weighted voting based on confidence.
    This approach improves overall accuracy and provides better calibration through diversity.

    Benefits:
    - Reduces variance from single model predictions
    - Better handles edge cases with model disagreement
    - Higher confidence when models agree
    - Shows confidence distribution across predictions
    """
    user_id = current_user.id if current_user else None

    # Select models to use
    models = request.models or DEFAULT_ENSEMBLE_MODELS

    if not models:
        raise HTTPException(status_code=400, detail="No models specified")

    if len(models) < 2:
        raise HTTPException(status_code=400, detail="Ensemble requires at least 2 models")

    logger.info(
        f"Running ensemble classification with {len(models)} models: {models} "
        f"for user {user_id} with prompt {request.prompt_version}"
    )

    predictions = []
    errors = []

    # Get predictions from each model
    for model in models:
        try:
            result = classify_email(
                email_text=request.email_text,
                user_id=user_id,
                model=model,
                prompt_version=request.prompt_version
            )

            predictions.append(ModelPrediction(
                model=model,
                label=result["label"],
                confidence=result["confidence"],
                reasoning=result["reasoning"]
            ))

        except Exception as e:
            error_msg = f"Model {model} failed: {str(e)}"
            logger.warning(error_msg)
            errors.append(error_msg)
            # Continue with other models instead of failing completely

    if not predictions:
        raise HTTPException(
            status_code=503,
            detail=f"All models failed: {'; '.join(errors)}"
        )

    # Aggregate predictions
    aggregated = aggregate_predictions([
        {
            "label": p.label,
            "confidence": p.confidence,
            "reasoning": p.reasoning
        }
        for p in predictions
    ])

    # Generate ensemble reasoning
    consensus = aggregated["consensus_percentage"]
    consensus_text = f"Strong consensus ({consensus:.0f}% agreement)" if consensus > 80 else \
                     f"Moderate agreement ({consensus:.0f}%)" if consensus > 50 else \
                     f"Mixed predictions ({consensus:.0f}% agreement on top choice)"

    ensemble_reasoning = f"{consensus_text}. Models: {', '.join([p.model for p in predictions])}."

    return EnsembleClassificationResponse(
        email_text=request.email_text,
        ensemble_label=aggregated["ensemble_label"],
        ensemble_confidence=round(aggregated["ensemble_confidence"], 3),
        ensemble_reasoning=ensemble_reasoning,
        predictions=predictions,
        voting_distribution=aggregated["voting_distribution"],
        confidence_distribution={
            k: round(v, 3) for k, v in aggregated["confidence_distribution"].items()
        },
        consensus_percentage=round(aggregated["consensus_percentage"], 1)
    )


@router.get("/classify/ensemble/models")
def get_ensemble_info():
    """Get information about available ensemble configurations."""
    return {
        "default_ensemble": DEFAULT_ENSEMBLE_MODELS,
        "fast_ensemble": FAST_ENSEMBLE_MODELS,
        "info": {
            "default": "Balanced accuracy and cost (3 models)",
            "fast": "Faster inference with good accuracy (2 models)",
            "custom": "Specify any combination of available models"
        }
    }
