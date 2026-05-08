"""Advanced email threat analysis routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import re
from urllib.parse import urlparse

from database import get_db, User
from auth import get_optional_user
from logger_config import logger

router = APIRouter(prefix="/api/v1", tags=["threats"])


class ThreatAnalysisRequest(BaseModel):
    """Request for threat analysis."""
    email_text: str


class URLThreatIndicator(BaseModel):
    """URL threat indicators."""
    url: str
    is_suspicious: bool
    indicators: list[str]  # List of threat indicators found


class HeaderValidation(BaseModel):
    """Email header validation results."""
    has_spf: bool
    has_dkim: bool
    has_dmarc: bool
    sender_domain: str
    is_spoofed: bool
    spoofing_indicators: list[str]


class CredentialTheftIndicators(BaseModel):
    """Indicators of credential theft attempts."""
    has_password_request: bool
    has_account_verification: bool
    has_urgent_action: bool
    has_form_fields: bool
    risk_level: str  # low, medium, high


class ThreatAnalysisResponse(BaseModel):
    """Complete threat analysis response."""
    url_threats: list[URLThreatIndicator]
    header_validation: HeaderValidation
    credential_theft: CredentialTheftIndicators
    overall_threat_score: float  # 0-1
    threat_summary: str


class DomainReputation(BaseModel):
    """Domain reputation check."""
    domain: str
    reputation_score: float  # 0-1 (0=good, 1=bad)
    is_blacklisted: bool
    indicators: list[str]


# Common suspicious URL patterns
SUSPICIOUS_URL_PATTERNS = [
    r'bit\.ly',
    r'tinyurl',
    r'short\.url',
    r'cloud\.com',
    r'accounts\.',
    r'verify',
    r'confirm',
    r'update',
    r'validate',
]

# Suspicious domain patterns
SUSPICIOUS_DOMAIN_PATTERNS = [
    r'rn\.com',  # rn looks like m
    r'o0\.com',  # looks like Microsoft
    r'google-verify',
    r'amazon-security',
    r'paypal-confirm',
]

# Credential theft keywords
CREDENTIAL_KEYWORDS = [
    'password', 'verify password', 'confirm password', 'update password',
    'login', 'sign in', 'credentials', 'username', 'account number',
    'social security', 'ssn', 'credit card', 'card number', 'cvv',
    'pin', 'two-factor', '2fa'
]

# Urgency keywords
URGENCY_KEYWORDS = [
    'urgent', 'immediate', 'asap', 'act now', 'immediately',
    'don\'t delay', 'expire', 'suspended', 'limited time',
    'action required', 'verify now', 'confirm immediately'
]


def analyze_urls(email_text: str) -> list[URLThreatIndicator]:
    """Extract and analyze URLs in email."""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, email_text, re.IGNORECASE)

    threat_indicators = []
    for url in urls:
        indicators = []
        url_lower = url.lower()

        # Check for suspicious patterns
        for pattern in SUSPICIOUS_URL_PATTERNS:
            if re.search(pattern, url_lower):
                indicators.append(f"URL contains suspicious pattern: {pattern}")

        # Check for IP address instead of domain
        if re.match(r'https?://\d+\.\d+\.\d+\.\d+', url):
            indicators.append("Uses IP address instead of domain")

        # Check for very long URLs
        if len(url) > 100:
            indicators.append("Unusually long URL")

        threat_indicators.append(URLThreatIndicator(
            url=url,
            is_suspicious=len(indicators) > 0,
            indicators=indicators
        ))

    return threat_indicators


def analyze_headers(email_text: str) -> HeaderValidation:
    """Analyze email headers for spoofing indicators."""
    from_pattern = r'From:\s*([^\n<>]+)(?:<([^\n>]+)>)?'
    to_pattern = r'To:\s*([^\n<>]+)(?:<([^\n>]+)>)?'

    from_match = re.search(from_pattern, email_text, re.IGNORECASE)
    to_match = re.search(to_pattern, email_text, re.IGNORECASE)

    from_addr = from_match.group(2) if from_match and from_match.group(2) else (from_match.group(1) if from_match else "")
    to_addr = to_match.group(2) if to_match and to_match.group(2) else (to_match.group(1) if to_match else "")

    # Extract domain
    try:
        sender_domain = from_addr.split('@')[1] if '@' in from_addr else "unknown"
    except:
        sender_domain = "unknown"

    # Check for spoofing indicators
    spoofing_indicators = []

    # Check if domain is suspicious
    for pattern in SUSPICIOUS_DOMAIN_PATTERNS:
        if re.search(pattern, sender_domain.lower()):
            spoofing_indicators.append(f"Domain matches suspicious pattern: {pattern}")

    # Check if From and To domains don't match (common phishing tactic)
    to_domain = to_addr.split('@')[1] if '@' in to_addr else ""
    if to_domain and sender_domain != to_domain and sender_domain != "unknown":
        spoofing_indicators.append("From and To domains don't match")

    # Check for lookalike domains
    if any(char in sender_domain for char in ['0', 'O', 'l', '1', 'I']):
        spoofing_indicators.append("Domain contains lookalike characters")

    # Check headers
    has_spf = bool(re.search(r'Received-SPF:', email_text, re.IGNORECASE))
    has_dkim = bool(re.search(r'DKIM-Signature:', email_text, re.IGNORECASE))
    has_dmarc = bool(re.search(r'DMARC:', email_text, re.IGNORECASE))

    return HeaderValidation(
        has_spf=has_spf,
        has_dkim=has_dkim,
        has_dmarc=has_dmarc,
        sender_domain=sender_domain,
        is_spoofed=len(spoofing_indicators) > 0,
        spoofing_indicators=spoofing_indicators
    )


def analyze_credential_theft(email_text: str) -> CredentialTheftIndicators:
    """Detect credential theft indicators."""
    email_lower = email_text.lower()

    has_password_request = any(kw in email_lower for kw in ['password', 'verify password', 'confirm password'])
    has_account_verification = any(kw in email_lower for kw in ['verify account', 'confirm identity', 'validate account'])
    has_urgent_action = any(kw in email_lower for kw in URGENCY_KEYWORDS)
    has_form_fields = bool(re.search(r'<input|<form', email_text, re.IGNORECASE))

    # Calculate risk level
    risk_indicators = sum([
        has_password_request,
        has_account_verification,
        has_urgent_action,
        has_form_fields
    ])

    if risk_indicators >= 3:
        risk_level = "high"
    elif risk_indicators >= 2:
        risk_level = "medium"
    else:
        risk_level = "low"

    return CredentialTheftIndicators(
        has_password_request=has_password_request,
        has_account_verification=has_account_verification,
        has_urgent_action=has_urgent_action,
        has_form_fields=has_form_fields,
        risk_level=risk_level
    )


def calculate_threat_score(
    url_threats: list[URLThreatIndicator],
    header_validation: HeaderValidation,
    credential_theft: CredentialTheftIndicators
) -> float:
    """Calculate overall threat score."""
    score = 0.0

    # URL threats (up to 0.3)
    if url_threats:
        suspicious_count = sum(1 for u in url_threats if u.is_suspicious)
        score += (suspicious_count / len(url_threats)) * 0.3

    # Header validation (up to 0.3)
    if header_validation.is_spoofed:
        score += 0.3
    elif not (header_validation.has_spf or header_validation.has_dkim or header_validation.has_dmarc):
        score += 0.15

    # Credential theft (up to 0.4)
    if credential_theft.risk_level == "high":
        score += 0.4
    elif credential_theft.risk_level == "medium":
        score += 0.2

    return min(score, 1.0)  # Cap at 1.0


@router.post("/analyze-threat", response_model=ThreatAnalysisResponse)
def analyze_threat(
    request: ThreatAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Perform advanced threat analysis on email."""
    logger.info(f"Analyzing threat indicators for user {current_user.id if current_user else 'anonymous'}")

    # Analyze different threat aspects
    url_threats = analyze_urls(request.email_text)
    header_validation = analyze_headers(request.email_text)
    credential_theft = analyze_credential_theft(request.email_text)

    # Calculate overall threat score
    threat_score = calculate_threat_score(url_threats, header_validation, credential_theft)

    # Generate summary
    threat_factors = []
    if url_threats and any(u.is_suspicious for u in url_threats):
        threat_factors.append("suspicious URLs detected")
    if header_validation.is_spoofed:
        threat_factors.append("possible domain spoofing")
    if credential_theft.risk_level in ["high", "medium"]:
        threat_factors.append(f"{credential_theft.risk_level} risk of credential theft")

    threat_summary = f"Threat score: {threat_score:.2f}. "
    if threat_factors:
        threat_summary += "Detected: " + ", ".join(threat_factors)
    else:
        threat_summary += "No major threats detected."

    return ThreatAnalysisResponse(
        url_threats=url_threats,
        header_validation=header_validation,
        credential_theft=credential_theft,
        overall_threat_score=round(threat_score, 2),
        threat_summary=threat_summary
    )


@router.get("/domain-reputation/{domain}")
def check_domain_reputation(
    domain: str,
    db: Session = Depends(get_db),
) -> DomainReputation:
    """Check domain reputation (simplified)."""
    # This is a simplified version. In production, integrate with real threat databases
    # like URLhaus, PhishTank, etc.

    domain_lower = domain.lower()
    indicators = []
    reputation_score = 0.0
    is_blacklisted = False

    # Check against known malicious patterns
    suspicious_patterns = [
        (r'paypal', 'Mimics PayPal'),
        (r'amazon', 'Mimics Amazon'),
        (r'microsoft', 'Mimics Microsoft'),
        (r'apple', 'Mimics Apple'),
        (r'google', 'Mimics Google'),
    ]

    for pattern, indicator in suspicious_patterns:
        if re.search(pattern, domain_lower) and not domain_lower.startswith(pattern):
            indicators.append(indicator)
            reputation_score += 0.2

    # Check for newly registered domains (high risk)
    if domain.endswith('.tk') or domain.endswith('.ml') or domain.endswith('.ga'):
        indicators.append("High-risk TLD")
        reputation_score += 0.2

    # Check for suspicious characters
    if any(char in domain for char in ['0', 'l', 'I']):
        indicators.append("Contains lookalike characters")
        reputation_score += 0.1

    reputation_score = min(reputation_score, 1.0)
    is_blacklisted = reputation_score >= 0.7

    return DomainReputation(
        domain=domain,
        reputation_score=reputation_score,
        is_blacklisted=is_blacklisted,
        indicators=indicators
    )
