"""Phishing pattern detection and trend analysis routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta
from collections import Counter
import re

from database import get_db, User, ClassificationLog
from auth import get_optional_user
from logger_config import logger

router = APIRouter(prefix="/api/v1", tags=["patterns"])

# Common phishing keywords
PHISHING_KEYWORDS = [
    'verify', 'confirm', 'urgent', 'action required', 'click here',
    'update', 'suspended', 'locked', 'compromised', 'immediately',
    'password', 'account', 'credentials', 'confirm identity', 'validate',
    'unusual activity', 'suspicious', 'expire', 'reactivate'
]

SPAM_KEYWORDS = [
    'discount', 'offer', 'sale', 'limited time', 'free', 'click',
    'buy now', 'don\'t miss', 'act now', 'hurry', 'exclusive',
    'winner', 'congratulations', 'claim', 'unsubscribe'
]


@router.get("/patterns/common-keywords")
def get_common_keywords(
    label: str = "PHISHING",
    days: int = 30,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get most common keywords in classified emails."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(ClassificationLog).filter(
        ClassificationLog.label == label.upper(),
        ClassificationLog.success == True,
        ClassificationLog.timestamp >= cutoff_date
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    logs = query.all()

    # Extract keywords from email snippets
    keywords = []
    for log in logs:
        # Simple keyword extraction - split and filter
        words = log.email_snippet.lower().split()
        keywords.extend([w.strip('.,!?;:') for w in words if len(w) > 4])

    # Count occurrences
    keyword_counts = Counter(keywords)
    top_keywords = keyword_counts.most_common(limit)

    return {
        "label": label,
        "period_days": days,
        "total_emails": len(logs),
        "keywords": [
            {"word": word, "count": count, "percentage": round(count / len(keywords) * 100, 2)}
            for word, count in top_keywords
        ]
    }


@router.get("/patterns/sender-domains")
def get_sender_domains(
    label: str = "PHISHING",
    days: int = 30,
    limit: int = 15,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Analyze sender domains in classified emails."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(ClassificationLog).filter(
        ClassificationLog.label == label.upper(),
        ClassificationLog.success == True,
        ClassificationLog.timestamp >= cutoff_date
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    logs = query.all()

    # Extract domains from email snippets (simple regex)
    domains = []
    domain_pattern = r'[\w\.-]+@([\w\.-]+\.\w+)'
    for log in logs:
        matches = re.findall(domain_pattern, log.email_snippet.lower())
        domains.extend(matches)

    domain_counts = Counter(domains)
    top_domains = domain_counts.most_common(limit)

    return {
        "label": label,
        "period_days": days,
        "total_emails": len(logs),
        "domains": [
            {"domain": domain, "count": count, "percentage": round(count / len(domains) * 100, 2)}
            for domain, count in top_domains
        ] if domains else []
    }


@router.get("/patterns/threat-trends")
def get_threat_trends(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get threat classification trends over time."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(ClassificationLog).filter(
        ClassificationLog.success == True,
        ClassificationLog.timestamp >= cutoff_date
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    logs = query.all()

    # Group by day and label
    daily_trends = {}
    for log in logs:
        day = log.timestamp.date().isoformat()
        if day not in daily_trends:
            daily_trends[day] = {"PHISHING": 0, "SPAM": 0, "LEGITIMATE": 0, "total": 0}
        daily_trends[day][log.label] += 1
        daily_trends[day]["total"] += 1

    # Calculate percentages
    trends = []
    for day in sorted(daily_trends.keys()):
        data = daily_trends[day]
        total = data["total"]
        trends.append({
            "date": day,
            "phishing": data["PHISHING"],
            "spam": data["SPAM"],
            "legitimate": data["LEGITIMATE"],
            "phishing_percentage": round(data["PHISHING"] / total * 100, 1) if total > 0 else 0,
            "spam_percentage": round(data["SPAM"] / total * 100, 1) if total > 0 else 0,
            "legitimate_percentage": round(data["LEGITIMATE"] / total * 100, 1) if total > 0 else 0,
        })

    return {
        "period_days": days,
        "total_classifications": len(logs),
        "trends": trends
    }


@router.get("/patterns/risk-indicators")
def get_risk_indicators(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Identify emails with multiple phishing risk indicators."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(ClassificationLog).filter(
        ClassificationLog.label == "PHISHING",
        ClassificationLog.success == True,
        ClassificationLog.timestamp >= cutoff_date,
        ClassificationLog.confidence >= 0.8
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    high_confidence_phishing = query.limit(100).all()

    # Analyze risk indicators
    indicators = {keyword: 0 for keyword in PHISHING_KEYWORDS}

    for log in high_confidence_phishing:
        email_lower = log.email_snippet.lower()
        for keyword in PHISHING_KEYWORDS:
            if keyword in email_lower:
                indicators[keyword] += 1

    # Sort by frequency
    sorted_indicators = sorted(indicators.items(), key=lambda x: x[1], reverse=True)

    return {
        "period_days": days,
        "high_confidence_phishing_count": len(high_confidence_phishing),
        "risk_indicators": [
            {"indicator": ind, "frequency": count, "percentage": round(count / len(high_confidence_phishing) * 100, 1)}
            for ind, count in sorted_indicators if count > 0
        ]
    }


@router.get("/patterns/summary")
def get_pattern_summary(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Get comprehensive pattern summary."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(ClassificationLog).filter(
        ClassificationLog.success == True,
        ClassificationLog.timestamp >= cutoff_date
    )

    if current_user:
        query = query.filter(ClassificationLog.user_id == current_user.id)

    logs = query.all()

    if not logs:
        return {
            "period_days": days,
            "total_classifications": 0,
            "label_distribution": {},
            "confidence_metrics": {},
            "high_risk_count": 0
        }

    # Label distribution
    label_counts = {"PHISHING": 0, "SPAM": 0, "LEGITIMATE": 0}
    for log in logs:
        label_counts[log.label] += 1

    # Confidence metrics
    phishing_logs = [l for l in logs if l.label == "PHISHING"]
    avg_confidence = sum(l.confidence for l in logs) / len(logs) if logs else 0
    phishing_avg_confidence = sum(l.confidence for l in phishing_logs) / len(phishing_logs) if phishing_logs else 0

    # High risk count
    high_risk = len([l for l in logs if l.label == "PHISHING" and l.confidence >= 0.8])

    return {
        "period_days": days,
        "total_classifications": len(logs),
        "label_distribution": {
            "phishing": {"count": label_counts["PHISHING"], "percentage": round(label_counts["PHISHING"] / len(logs) * 100, 1)},
            "spam": {"count": label_counts["SPAM"], "percentage": round(label_counts["SPAM"] / len(logs) * 100, 1)},
            "legitimate": {"count": label_counts["LEGITIMATE"], "percentage": round(label_counts["LEGITIMATE"] / len(logs) * 100, 1)},
        },
        "confidence_metrics": {
            "overall_average": round(avg_confidence, 2),
            "phishing_average": round(phishing_avg_confidence, 2),
        },
        "high_risk_count": high_risk,
        "high_risk_percentage": round(high_risk / len(logs) * 100, 1) if logs else 0,
    }
