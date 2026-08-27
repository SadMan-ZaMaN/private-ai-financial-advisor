# Architecture

## Data flow

```
┌────────────────────────────────────────────────────────────────────┐
│ USER'S DEVICE                                                       │
│                                                                      │
│  financial form (income/expenses/savings/debt/risk) + policy toggles│
│         │                                                            │
│         ├─────────────────► backend-ai (Python)                     │
│         │   POST /recommend    returns {amount, riskLevel} only     │
│         │◄─────────────────┘                                        │
│         │                                                            │
│         ▼                                                            │
│  midnight-service: setLocalPolicy(sameFinancialData)                │
│         │                                                            │
│         ▼                                                            │
│  call advisor.verifyRecommendation(amount, riskLevel)                │
│  → Compact circuit re-derives bounds from private witnesses          │
│  → generates ZK proof LOCALLY                                        │
│         │                                                            │
└─────────┼──────────────────────────────────────────────────────────┘
          ▼
   Midnight ledger (public)
   owner-hash | verifiedCount | lastRecommendedAmount | lastRiskLevelUsed
   (income/expenses/savings/debt: NEVER written here, NEVER sent here)
```

## Judge Q&A prep

**"Why did you use Midnight here?"**
Because the interesting part of this product is a trust problem, not a
storage problem: the user needs proof that an AI advisor's number respects
rules *they* set on data *they* never want to hand over — to us, to the AI
provider, or to a chain. A database with an "I promise I checked" flag
can't give you that; a ZK circuit can.

**"What exactly is being proven?"**
`verifyRecommendation` in `contracts/advisor.compact` proves three
assertions hold for private witness values that are never disclosed:
`expenses + recommendedAmount <= income`, `riskLevelUsed <= riskTolerance`,
`debt <= savings`. If any assertion fails, the circuit aborts — no proof
is produced, so nothing is ever written to the ledger. Only a passing
result becomes public, and even then only the recommendation, never the
inputs that justified it.

**"What does the AI actually contribute, versus the contract?"**
The AI (`backend-ai/advisor.py`) proposes a number using its own
judgment/formula. The contract does not trust that number — it recomputes
the legal bounds from the user's private data inside the circuit and
rejects any AI proposal outside them. The AI can be swapped for a fancier
model, a different formula, or a human advisor entirely, and the privacy
guarantee is unchanged, because it lives in the contract, not in the AI.

**"Isn't the witness just self-reported? What stops someone lying to the
witness functions?"**
Nothing stops a user from feeding fake numbers into their *own* witness —
but that only lets them lie to themselves; there's no one else to defraud.
The interesting party the proof protects is anyone verifying the claim
externally (an app, a lender, a counterparty) — they get a mathematical
guarantee that *some* private income/expense/savings/debt values
consistent with the public formula justify the recommendation, without
learning what those values are.

## Known simplifications (say these proactively, don't wait to be asked)
- The affordability/risk formula is intentionally simple (linear,
  addition/comparison only) so it compiles predictably in Compact under
  hackathon time pressure. A production version would want richer
  budgeting logic, still expressed as circuit-safe arithmetic.
- `owner` binding uses a hash-of-secret pattern (same approach as
  Midnight's own "lock" example in their docs) rather than full wallet
  signature integration — enough to demo "only you can verify your own
  policy," upgradeable post-hackathon.
