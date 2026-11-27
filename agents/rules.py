"""Deterministic policy rules (F3, F10, ADR-0003): category, severity floor, escalation.

Does: map ticket text to one of the 10 categories by weighted keyword rules, give a severity
FLOOR that can only raise the model's severity, and match the escalation rule table (payment
dispute, account deletion, security, data loss, legal, enterprise outage), each with a named team.
Everything here is a pure function of text and plan name: no model call, no I/O, no SQL.
Must NOT: call an LLM, touch the database, or lower a severity. The model adds judgement only
where no rule matched (CLAUDE.md 7.2).
"""

import re
from dataclasses import dataclass

from app.schemas.common import Category, Severity

SEVERITY_ORDER: dict[Severity, int] = {
    Severity.low: 0,
    Severity.medium: 1,
    Severity.high: 2,
    Severity.critical: 3,
}


def _re(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


# ----------------------------------------------------------------------------- category

# (pattern, weight). The category with the highest summed weight wins; a tie goes to the category
# listed first, so the safer reading (security, billing) beats the vaguer one.
_CATEGORY_RULES: dict[Category, list[tuple[re.Pattern[str], int]]] = {
    Category.security: [
        (_re(r"\bbreach|compromis|hacked|account takeover|phishing"), 3),
        (_re(r"suspicious\s+(login|sign|activity|access)"), 3),
        (_re(r"unauthori[sz]ed\s+access"), 3),
        (_re(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions|admin\s+mode"), 3),
    ],
    Category.billing: [
        (
            _re(
                r"\brefund|\binvoice|\bbilled|\bbilling|\bcharge[sd]?\b|\bpayment|\bdispute|"
                r"chargeback|\bsubscription|\bseats?\b"
            ),
            2,
        ),
    ],
    Category.login_issue: [
        (_re(r"\bsso\b|\bsaml\b"), 3),
        (_re(r"\bmfa\b|\b2fa\b|recovery codes|locked out|lockout"), 3),
        (_re(r"sign[\s-]?in|log[\s-]?in|\bpassword reset"), 2),
    ],
    Category.api_failure: [
        (_re(r"\b429\b|rate[\s-]?limit|\b50[023]\b"), 3),
        (_re(r"\bapi\b|\bwebhook|sync job"), 2),
    ],
    Category.storage_quota: [
        (_re(r"quota"), 3),
        (_re(r"\bstorage\b|\buploads?\b"), 2),
    ],
    Category.workspace_permissions: [
        (_re(r"permission|\bshar(e|ing)\b|\bguests?\b|\broles?\b"), 2),
    ],
    Category.integration: [
        (_re(r"\bslack\b|zapier|\bintegration|connected app"), 3),
    ],
    Category.feature_request: [
        (_re(r"feature request|dark mode|would be lovely|would love|\bi wish\b|please add"), 3),
    ],
    Category.account: [
        (
            _re(
                r"delete\s+(our|the|my)\s+(\w+\s+)*(workspace|account)|\berase|data retention|"
                r"close\s+(our|my)\s+account|data erasure"
            ),
            3,
        ),
        (
            _re(
                r"disappear|vanished|went missing|are missing|empty today|"
                r"restore\s+(the|our|my)\s+files"
            ),
            3,
        ),
    ],
}


def rule_category(text: str) -> Category:
    """The category the keyword rules choose; `other` when nothing matches."""
    best, best_score = Category.other, 0
    for category, rules in _CATEGORY_RULES.items():
        score = sum(weight for pattern, weight in rules if pattern.search(text))
        if score > best_score:
            best, best_score = category, score
    return best


# ----------------------------------------------------------------------------- escalation


@dataclass(frozen=True)
class EscalationRule:
    name: str
    pattern: re.Pattern[str]
    team: str
    reason: str
    severity: Severity
    plan_name: str | None = None  # the rule applies only to this plan when set


# Table order is priority order: the first match names the team.
ESCALATION_RULES: tuple[EscalationRule, ...] = (
    EscalationRule(
        "security_incident",
        _re(
            r"\bbreach|compromis|hacked|account takeover|phishing|"
            r"suspicious\s+(login|sign|activity|access)|unauthori[sz]ed\s+access"
        ),
        "Security team",
        "Possible security incident; support does not investigate or confirm breaches.",
        Severity.high,
    ),
    EscalationRule(
        "data_loss",
        _re(
            r"disappear|vanished|went missing|are missing|empty today|"
            r"restore\s+(the|our|my)\s+files|data loss|lost\s+(all\s+)?(our\s+|my\s+)?files"
        ),
        "Data protection team",
        "Possible data loss; recovery is never promised by support.",
        Severity.high,
    ),
    EscalationRule(
        "account_deletion",
        _re(
            r"delete\s+(our|the|my)\s+(\w+\s+)*(workspace|account)|\berase\b|data erasure|"
            r"right to be forgotten|gdpr\s+(request|erasure|deletion)"
        ),
        "Privacy team",
        "Account or data deletion is irreversible and needs verification.",
        Severity.high,
    ),
    EscalationRule(
        "payment_dispute",
        _re(
            r"\bdispute|disputing|chargeback|unauthori[sz]ed\s+(charge|transaction|payment)|"
            r"did not authori[sz]e"
        ),
        "Billing disputes team",
        "Payment disputes carry financial and legal consequences.",
        Severity.high,
    ),
    EscalationRule(
        "legal",
        _re(r"\blawyer|\battorney|lawsuit|\bsue\b|subpoena|legal action|court order|litigation"),
        "Legal team",
        "Legal matters are never answered by support.",
        Severity.high,
    ),
    EscalationRule(
        "enterprise_outage",
        _re(r"\boutage|(is|are)\s+(completely\s+|fully\s+)?down\b|service unavailable"),
        "Enterprise support team",
        "Outage reported by an enterprise customer.",
        Severity.critical,
        plan_name="enterprise",
    ),
)


def matching_escalation_rules(text: str, plan_name: str | None) -> list[EscalationRule]:
    """Every escalation rule the text matches, in table order."""
    plan = (plan_name or "").strip().lower()
    return [
        r
        for r in ESCALATION_RULES
        if (r.plan_name is None or r.plan_name == plan) and r.pattern.search(text)
    ]


@dataclass(frozen=True)
class EscalationVerdict:
    required: bool
    team: str | None
    rule_names: tuple[str, ...]
    reasons: tuple[str, ...]


def rule_escalation(text: str, plan_name: str | None) -> EscalationVerdict:
    """The policy decision. When a rule matched the model cannot overturn it."""
    matched = matching_escalation_rules(text, plan_name)
    if not matched:
        return EscalationVerdict(False, None, (), ())
    return EscalationVerdict(
        True, matched[0].team, tuple(r.name for r in matched), tuple(r.reason for r in matched)
    )


# ----------------------------------------------------------------------------- severity

# (pattern, floor, reason) signals beyond the escalation table.
_SEVERITY_SIGNALS: tuple[tuple[re.Pattern[str], Severity, str], ...] = (
    (
        _re(r"\bbreach|compromis|hacked|account takeover"),
        Severity.critical,
        "Reported compromise of an account.",
    ),
    (
        _re(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions|admin\s+mode"),
        Severity.high,
        "Text tries to override the assistant instructions.",
    ),
    (
        _re(
            r"(whole|entire)\s+(team|company|org)|\bnobody\b.{0,30}\bcan\b|"
            r"\d{2,}\s+(people|users)\s+(are\s+)?(blocked|locked)"
        ),
        Severity.high,
        "Many users are blocked.",
    ),
)


@dataclass(frozen=True)
class SeverityVerdict:
    severity: Severity
    reason: str
    raised: bool


def rule_severity(
    text: str, plan_name: str | None = None, model_severity: Severity | None = None
) -> SeverityVerdict:
    """max(rule floor, model severity). Rules raise severity and never lower it (ADR-0003)."""
    floor, reason = Severity.low, "No severity rule matched."
    candidates = [(r.severity, r.reason) for r in matching_escalation_rules(text, plan_name)]
    candidates += [(sev, why) for pattern, sev, why in _SEVERITY_SIGNALS if pattern.search(text)]
    for sev, why in candidates:
        if SEVERITY_ORDER[sev] > SEVERITY_ORDER[floor]:
            floor, reason = sev, why
    if model_severity is not None and SEVERITY_ORDER[model_severity] > SEVERITY_ORDER[floor]:
        return SeverityVerdict(model_severity, "Model severity kept; no rule is higher.", False)
    raised = model_severity is not None and floor != model_severity
    return SeverityVerdict(floor, reason, raised)
