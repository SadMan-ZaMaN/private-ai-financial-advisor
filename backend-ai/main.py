"""
Private AI Financial Advisor — AI backend (FastAPI)

Responsibility of this service, and ONLY this:
  Take a user's financial snapshot + policy, produce a recommendation
  (amount + risk level). Nothing here talks to Midnight, and nothing
  here persists the request. That split matters for the demo:

    - This service can be dumb about privacy, because it holds nothing.
      It computes a number and forgets the inputs the instant the
      response is sent (no DB, no logging of raw fields).
    - The privacy GUARANTEE is Midnight's job: the recommendation this
      service returns only becomes "trusted" once the frontend runs it
      through the Compact circuit in contracts/advisor.compact, which
      proves the recommendation respects the user's real (never-disclosed)
      income/expenses/savings/debt/risk tolerance.

  Run: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from enum import IntEnum

from advisor import recommend, RiskLevel

app = FastAPI(title="Private AI Financial Advisor — AI service")

# Dev-only CORS. Tighten this before you demo off localhost.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Policy(BaseModel):
    allow_investment_advice: bool = True
    allow_savings_advice: bool = True
    max_risk_level: RiskLevel = RiskLevel.LOW


class FinancialSnapshot(BaseModel):
    """
    This shape mirrors the witness functions in
    midnight-service/src/witnesses.ts *exactly on purpose* — the frontend
    holds one object like this locally, sends it here to get a
    recommendation, then feeds the same object into the ZK proof. It is
    never written to disk by this service.
    """
    income: int = Field(..., ge=0, description="Monthly income")
    expenses: int = Field(..., ge=0, description="Monthly fixed expenses")
    savings: int = Field(..., ge=0)
    debt: int = Field(..., ge=0)
    risk_tolerance: RiskLevel = RiskLevel.LOW
    policy: Policy = Policy()


class Recommendation(BaseModel):
    recommended_amount: int
    risk_level_used: RiskLevel
    rationale: str


@app.post("/recommend", response_model=Recommendation)
def get_recommendation(snapshot: FinancialSnapshot) -> Recommendation:
    amount, risk_level, rationale = recommend(snapshot)
    return Recommendation(
        recommended_amount=amount,
        risk_level_used=risk_level,
        rationale=rationale,
    )


@app.get("/health")
def health():
    return {"status": "ok"}
