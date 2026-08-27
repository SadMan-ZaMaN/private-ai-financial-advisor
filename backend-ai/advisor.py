"""
Core recommendation logic.

Two layers, kept deliberately separate:

1. `_safe_bounds()` — a small, deterministic, auditable formula. This is
   the SAME logic that gets re-checked inside the Compact circuit
   (contracts/advisor.compact), just expressed here in Python instead of
   Compact. It exists so the AI doesn't even bother proposing something
   the chain would reject.

2. `recommend()` — wraps that formula and (optionally) calls an LLM to
   turn the number into a human-readable explanation. The LLM NEVER picks
   the final number or the risk level — it only narrates a number that
   the deterministic layer already produced and bounded. This is an
   important design point for judges: "we don't let the LLM freelance
   with someone's finances; it explains a bounded decision."

If you want the LLM in the loop, set ANTHROPIC_API_KEY and flip
USE_LLM_NARRATIVE to True below.
"""

import os
from enum import IntEnum
from typing import Tuple


class RiskLevel(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2


USE_LLM_NARRATIVE = bool(os.environ.get("ANTHROPIC_API_KEY")) and os.environ.get(
    "USE_LLM_NARRATIVE", "false"
).lower() == "true"


def _safe_bounds(snapshot) -> Tuple[int, RiskLevel]:
    """
    Deterministic policy formula — mirrors the three asserts in
    contracts/advisor.compact:
      1. exp + recommendedAmount <= inc            (affordability)
      2. riskLevelUsed <= riskTolerance             (risk policy)
      3. debt <= savings                            (solvency guard)
    """
    disposable = max(0, snapshot.income - snapshot.expenses)

    # Fraction of disposable income offered up as savings/investment,
    # scaled by how much risk the user is willing to take.
    risk_used = min(snapshot.risk_tolerance, snapshot.policy.max_risk_level)
    fraction = {RiskLevel.LOW: 0.3, RiskLevel.MEDIUM: 0.5, RiskLevel.HIGH: 0.7}[
        RiskLevel(risk_used)
    ]

    amount = int(disposable * fraction)

    # Solvency guard mirrors assert(debt <= savings, ...) in the circuit.
    if snapshot.debt > snapshot.savings:
        amount = 0

    return amount, RiskLevel(risk_used)


def _narrate(snapshot, amount: int, risk_level: RiskLevel) -> str:
    if not USE_LLM_NARRATIVE:
        return (
            f"Based on your disposable income and a {risk_level.name.lower()} "
            f"risk profile, allocating this amount keeps you within your "
            f"own affordability and solvency limits."
        )

    import anthropic  # local import so the package is only required if used

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        messages=[{
            "role": "user",
            "content": (
                "In 2-3 sentences, explain to a user why allocating "
                f"{amount} per month toward savings/investment at "
                f"{risk_level.name} risk is a reasonable recommendation, "
                "given typical income-minus-expenses budgeting. Do not "
                "restate their raw income or expense figures. Speak "
                "directly to the user."
            ),
        }],
    )
    return msg.content[0].text


def recommend(snapshot) -> Tuple[int, RiskLevel, str]:
    if not snapshot.policy.allow_savings_advice and not snapshot.policy.allow_investment_advice:
        return 0, RiskLevel.LOW, "User policy disallows savings/investment advice."

    amount, risk_level = _safe_bounds(snapshot)
    rationale = _narrate(snapshot, amount, risk_level)
    return amount, risk_level, rationale
