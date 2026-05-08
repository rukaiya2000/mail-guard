"""Adversarial robustness testing: test models against evasion techniques."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import re
import string

from classifier import classify_email
from database import get_db, User
from auth import get_optional_user
from logger_config import logger

router = APIRouter(prefix="/api/v1", tags=["adversarial"])


class AdversarialExample(BaseModel):
    """Adversarial example for robustness testing."""
    original_email: str
    perturbed_email: str
    perturbation_type: str
    severity: str  # low, medium, high


class AdversarialTestResult(BaseModel):
    """Result from testing model against adversarial example."""
    original_prediction: str
    original_confidence: float
    perturbed_prediction: str
    perturbed_confidence: float
    robustness_score: float  # How much did prediction change? 0-1
    was_fooled: bool  # Did perturbation change the prediction?
    perturbation_type: str


class AdversarialRobustnessReport(BaseModel):
    """Overall robustness assessment."""
    total_tests: int
    successful_attacks: int
    attack_success_rate: float
    robustness_score: float  # 0-1, higher is more robust
    by_perturbation_type: dict
    by_severity: dict
    recommendations: list[str]


# Adversarial perturbation techniques
class AdversarialAttacks:
    """Collection of evasion techniques used in phishing attacks."""

    @staticmethod
    def homograph_attack(email: str) -> str:
        """Replace characters with lookalikes: l→1, O→0, etc.

        Real-world example: amaz0n.com looks like amazon.com
        """
        replacements = {
            'l': '1',
            'O': '0',
            'S': '5',
            'Z': '2',
            'A': '4',
        }
        result = email
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result

    @staticmethod
    def unicode_encoding_attack(email: str) -> str:
        """Add zero-width characters and unicode tricks.

        Real-world: phishing.com becomes p​h​i​s​h​i​n​g​.​com (zero-width spaces)
        """
        # Add zero-width space between words
        result = re.sub(r'(\w)(\w)', r'\1​\2', email[:200]) + email[200:]
        return result

    @staticmethod
    def obfuscation_attack(email: str) -> str:
        """Add extra whitespace and newlines to confuse parsing.

        Real-world: split "verify" into "ver\nify"
        """
        keywords = ['verify', 'confirm', 'password', 'account', 'urgent']
        result = email
        for keyword in keywords:
            if keyword in result.lower():
                obfuscated = keyword[0] + '\n' + keyword[1:]
                result = result.replace(keyword, obfuscated, 1)
        return result

    @staticmethod
    def typo_injection_attack(email: str) -> str:
        """Add intentional typos that humans understand but models might struggle with.

        Real-world: "Amaz0n Sec0rity" instead of "Amazon Security"
        """
        replacements = {
            'Amazon': 'Am4z0n',
            'Google': 'G00gle',
            'Microsoft': 'Micr0s0ft',
            'PayPal': 'P4yP41',
            'verify': 'v3rify',
            'confirm': 'c0nfirm',
        }
        result = email
        for original, typo in replacements.items():
            result = result.replace(original, typo, 1)
        return result

    @staticmethod
    def html_encoding_attack(email: str) -> str:
        """Use HTML entities and special encodings.

        Real-world: "Click &lt;here&gt;" or "&#118;erify"
        """
        keywords = ['verify', 'password', 'confirm']
        result = email
        for keyword in keywords:
            if keyword in result:
                # Replace with HTML entities
                html_encoded = ''.join(f'&#{ord(c)};' for c in keyword)
                result = result.replace(keyword, html_encoded, 1)
        return result

    @staticmethod
    def context_confusion_attack(email: str) -> str:
        """Add benign content to confuse threat analysis.

        Real-world: Mix legitimate business language with phishing requests
        """
        legitimate_prefixes = [
            "As part of our regular security updates, ",
            "To ensure service continuity, ",
            "Per industry compliance requirements, ",
        ]
        if email.startswith(legitimate_prefixes[0]):
            return email  # Already prefixed
        return legitimate_prefixes[0] + email

    @staticmethod
    def case_randomization_attack(email: str) -> str:
        """Randomize case to confuse pattern matching.

        Real-world: "VeRiFy" vs "verify"
        """
        keywords = ['verify', 'password', 'confirm', 'urgent', 'account']
        result = email
        for keyword in keywords:
            if keyword in result.lower():
                randomized = ''.join(
                    c.upper() if i % 2 == 0 else c.lower()
                    for i, c in enumerate(keyword)
                )
                result = result.replace(keyword, randomized, 1)
        return result


def get_attack_severity(attack_type: str) -> str:
    """Classify attack severity."""
    severe_attacks = ['homograph', 'unicode_encoding', 'html_encoding']
    moderate_attacks = ['obfuscation', 'context_confusion']

    if attack_type in severe_attacks:
        return "high"
    elif attack_type in moderate_attacks:
        return "medium"
    else:
        return "low"


def calculate_robustness_score(original_conf: float, perturbed_conf: float) -> float:
    """Calculate robustness score (0-1).

    0 = Model fooled (confidence changed significantly)
    1 = Model robust (confidence unchanged)
    """
    confidence_change = abs(original_conf - perturbed_conf)
    robustness = max(0, 1 - confidence_change)  # 0-1
    return round(robustness, 3)


@router.post("/adversarial/test-email")
def test_email_robustness(
    email_text: str,
    model: Optional[str] = "gpt-4-turbo",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Test how well a model handles adversarial perturbations of an email.

    Applies multiple evasion techniques and checks if model prediction changes.
    """
    user_id = current_user.id if current_user else None

    # Get original prediction
    try:
        original = classify_email(
            email_text=email_text,
            user_id=user_id,
            model=model,
            prompt_version="v4"
        )
    except Exception as e:
        logger.error(f"Failed to classify original email: {str(e)}")
        return {"error": str(e), "status": "failed"}

    # Apply adversarial attacks
    attacks = {
        "homograph": AdversarialAttacks.homograph_attack(email_text),
        "unicode_encoding": AdversarialAttacks.unicode_encoding_attack(email_text),
        "obfuscation": AdversarialAttacks.obfuscation_attack(email_text),
        "typo_injection": AdversarialAttacks.typo_injection_attack(email_text),
        "html_encoding": AdversarialAttacks.html_encoding_attack(email_text),
        "context_confusion": AdversarialAttacks.context_confusion_attack(email_text),
        "case_randomization": AdversarialAttacks.case_randomization_attack(email_text),
    }

    results = []
    successful_attacks = 0

    for attack_type, perturbed_email in attacks.items():
        try:
            perturbed = classify_email(
                email_text=perturbed_email,
                user_id=user_id,
                model=model,
                prompt_version="v4"
            )

            was_fooled = perturbed["label"] != original["label"]
            robustness = calculate_robustness_score(
                original["confidence"],
                perturbed["confidence"]
            )

            if was_fooled:
                successful_attacks += 1

            results.append(AdversarialTestResult(
                original_prediction=original["label"],
                original_confidence=round(original["confidence"], 3),
                perturbed_prediction=perturbed["label"],
                perturbed_confidence=round(perturbed["confidence"], 3),
                robustness_score=robustness,
                was_fooled=was_fooled,
                perturbation_type=attack_type
            ))

        except Exception as e:
            logger.warning(f"Failed to test {attack_type} attack: {str(e)}")
            continue

    # Calculate summary metrics
    attack_success_rate = (successful_attacks / len(results) * 100) if results else 0
    overall_robustness = (
        sum(r.robustness_score for r in results) / len(results)
        if results else 0
    )

    # Group by severity
    by_severity = {}
    for result in results:
        severity = get_attack_severity(result.perturbation_type)
        if severity not in by_severity:
            by_severity[severity] = {"attempted": 0, "successful": 0}
        by_severity[severity]["attempted"] += 1
        if result.was_fooled:
            by_severity[severity]["successful"] += 1

    # Recommendations
    recommendations = []
    if attack_success_rate > 50:
        recommendations.append("Model is vulnerable to adversarial attacks - consider ensemble or input sanitization")
    if attack_success_rate > 30:
        recommendations.append("Model should be evaluated against common phishing evasion techniques")
    if overall_robustness < 0.7:
        recommendations.append("Low robustness score - consider retraining with adversarial examples")
    if not recommendations:
        recommendations.append("Model shows good robustness to tested evasion techniques")

    return {
        "model": model,
        "total_attacks": len(results),
        "successful_attacks": successful_attacks,
        "attack_success_rate": round(attack_success_rate, 2),
        "overall_robustness_score": round(overall_robustness, 3),
        "results": results,
        "by_severity": by_severity,
        "recommendations": recommendations
    }


@router.post("/adversarial/benchmark")
def run_adversarial_benchmark(
    models: Optional[list[str]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """Run adversarial robustness benchmark across multiple models.

    Tests a standard set of phishing emails against common evasion techniques.
    """
    if not models:
        models = ["gpt-4-turbo", "llama-3.1-70b-instruct", "claude-3-opus"]

    # Standard test emails (known phishing patterns)
    test_emails = [
        """From: security-alert@amazon-verify.xyz
Subject: Verify Your Account - URGENT

Click here immediately to confirm your password:
http://bit.ly/amazon-verify""",

        """From: noreply@paypal-confirm.net
Subject: Account Suspended - Action Required

Your PayPal account has been limited. Verify your information now:
http://short.url/paypal""",

        """From: admin@bank-security.tk
Subject: Update Required - Confirm Password

Please confirm your banking credentials to continue:
<input type="password" name="pwd">""",
    ]

    benchmark_results = {}

    for model in models:
        logger.info(f"Running adversarial benchmark for {model}")
        model_results = []

        for i, test_email in enumerate(test_emails):
            result = test_email_robustness(
                email_text=test_email,
                model=model,
                db=db,
                current_user=current_user
            )

            if "error" not in result:
                model_results.append(result)

        if model_results:
            avg_robustness = sum(r["overall_robustness_score"] for r in model_results) / len(model_results)
            avg_attack_success = sum(r["attack_success_rate"] for r in model_results) / len(model_results)

            benchmark_results[model] = {
                "average_robustness_score": round(avg_robustness, 3),
                "average_attack_success_rate": round(avg_attack_success, 2),
                "test_results": model_results
            }

    # Ranking
    ranked = sorted(
        benchmark_results.items(),
        key=lambda x: x[1]["average_robustness_score"],
        reverse=True
    )

    return {
        "benchmark": "adversarial_robustness",
        "models_tested": list(models),
        "results": benchmark_results,
        "ranking": [
            {"rank": i + 1, "model": model, "score": data["average_robustness_score"]}
            for i, (model, data) in enumerate(ranked)
        ],
        "recommendation": f"Best model: {ranked[0][0]} with {ranked[0][1]['average_robustness_score']} robustness"
    }


@router.get("/adversarial/attack-types")
def get_attack_types():
    """Get documentation of all adversarial attack types."""
    return {
        "attacks": [
            {
                "name": "Homograph Attack",
                "description": "Replace characters with lookalikes (l→1, O→0). Makes domain look legitimate.",
                "severity": "high",
                "example": "amaz0n.com"
            },
            {
                "name": "Unicode Encoding",
                "description": "Add zero-width characters or unicode tricks to confuse parsing.",
                "severity": "high",
                "example": "p​h​i​s​h​i​n​g​.com (zero-width spaces)"
            },
            {
                "name": "Obfuscation",
                "description": "Split keywords with newlines or whitespace.",
                "severity": "medium",
                "example": "ver\\nify"
            },
            {
                "name": "Typo Injection",
                "description": "Intentional typos humans understand but models might miss.",
                "severity": "low",
                "example": "Am4z0n"
            },
            {
                "name": "HTML Encoding",
                "description": "Use HTML entities to obfuscate keywords.",
                "severity": "high",
                "example": "&#118;erify"
            },
            {
                "name": "Context Confusion",
                "description": "Mix legitimate business language with phishing requests.",
                "severity": "medium",
                "example": "Per compliance requirements, please verify..."
            },
            {
                "name": "Case Randomization",
                "description": "Randomize case to confuse pattern matching.",
                "severity": "low",
                "example": "VeRiFy"
            },
        ]
    }
