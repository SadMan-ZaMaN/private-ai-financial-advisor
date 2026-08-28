# Private AI Financial Advisor — built on Midnight

An AI advisor that recommends a savings/investment allocation from your
finances — and a Compact smart contract that cryptographically proves the
recommendation respects your own private rules (affordability, risk
tolerance, solvency), without your income, expenses, savings or debt ever
touching a server or a chain.

## Repo layout

```
private-ai-advisor/
├── contracts/
│   └── advisor.compact        # the ZK policy-verification circuit
├── backend-ai/                # Python FastAPI — computes the recommendation
│   ├── main.py
│   ├── advisor.py
│   └── requirements.txt
├── midnight-service/
│   └── src/
│       └── witnesses.ts       # private data, read only on the user's device
└── docs/
    └── architecture.md
```

## Why it's split this way

Midnight's proving/witness layer is TypeScript-only — Compact witnesses are
implemented in the DApp's TS code, not Python (there is no Python Midnight
SDK). So the AI reasoning (which you already know in Python) and the
proof/chain layer (which must be TS) are two separate services that talk
over HTTP, never sharing raw data:

```
 USER (browser / local app)
   │  financial data typed in, stored ONLY in browser memory/local storage
   ▼
 backend-ai (Python/FastAPI)  ──► returns { amount, riskLevel } ONLY
   (never persists what you sent it)
   │
   ▼
 midnight-service (TypeScript + midnight-js)
   - loads the SAME financial data locally into witnesses.ts
   - calls advisor.verifyRecommendation(amount, riskLevel)
   - Compact circuit re-derives the bounds from the private witnesses
     and asserts the AI's numbers fall inside them
   - a ZK proof is generated locally and submitted to the ledger
   ▼
 Midnight ledger: only stores "verified ✅, amount, riskLevel, owner-hash"
   — never income/expenses/savings/debt
```

The Python service is deliberately "dumb" about privacy — it can be, because
it never sees anything worth protecting for longer than one request. The
actual privacy *guarantee* is enforced by the Compact contract, not by
Claude, not by promises in a README.

## What is actually being proven

`contracts/advisor.compact` — `verifyRecommendation` — proves, without
revealing income/expenses/savings/debt/risk tolerance:

1. **Affordability** — `expenses + recommendedAmount <= income`
2. **Risk policy** — `riskLevelUsed <= riskTolerance`
3. **Solvency guard** — `debt <= savings` (won't verify new allocations for an over-leveraged user)

That's the sentence to say when a judge asks "what exactly is being
proven?" — see `docs/architecture.md` for the longer version.

## Setup workflow (do this in order)

### 1. AI backend (works right now, no blockchain needed)
```bash
cd backend-ai
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# test:
curl -X POST localhost:8000/recommend -H "Content-Type: application/json" -d '{
  "income": 80000, "expenses": 45000, "savings": 400000, "debt": 100000,
  "risk_tolerance": 0
}'
```
This part is done and tested. Iterate on `advisor.py`'s `_safe_bounds()`
formula freely — just remember to keep the *same* formula mirrored in the
three `assert`s in `advisor.compact`, since the chain is what actually
enforces it.

### 2. Midnight toolchain (do this next, it's the part with setup friction)
Follow Midnight's own [installation guide](https://docs.midnight.network/getting-started/installation)
then clone their starter as your TS scaffold instead of building the
midnight-js wiring from scratch:
```bash
git clone https://github.com/midnightntwrk/example-counter.git midnight-scaffold
cd midnight-scaffold && yarn install
```
Copy `contracts/advisor.compact` (from this repo) into
`midnight-scaffold/contracts/`, and merge `witnesses.ts` into the
scaffold's existing witness file/pattern — don't reinvent the provider
setup, deploy script, or wallet plumbing; the starter already has a tested
version of that. Compile with:
```bash
cd contracts && compact compile advisor.compact managed/advisor
```

### 3. Wire it together
Point the scaffold's test/dApp script at `localhost:8000/recommend` to get
`{amount, riskLevel}`, feed the *same* financial snapshot into
`setLocalPolicy()`, then call `verifyRecommendation(amount, riskLevel)`.

### If the Compact compiler complains about syntax
This contract was written against Midnight's published docs (`pragma
language_version 0.16`, ledger/circuit/witness patterns, `assert`,
`disclose`, `Counter.increment`), but Compact evolves fast and I don't have
a live compiler to check it against. Two good fallbacks, both mentioned in
the hackathon resources:
- The **Midnight Expert plug-in for Claude Code** / **Midnight MCP** — it
  queries live docs and validates against the real compiler, so it won't
  guess at syntax the way a plain chat model can.
- `docs.midnight.network/compact` (language reference) for anything the
  compiler flags.

hackathons starts at 10pm  friday

## Roadmap (where you are)
- ✅ Lesson 1-3: concepts, Compact basics
- ✅ Lesson 4/5 shortcut: contract + AI backend above are real, working code
- ▶️ Lesson 6: wire midnight-service to the local devnet (`yarn env:up`,
  `yarn test:local` from the starter repo) and confirm
  `verifyRecommendation` runs end-to-end with a real proof
- ▶️ Lesson 7: minimal frontend (financial form → policy toggles →
  recommendation → "✅ Verified" badge), demo script, README polish,
  architecture diagram image for GitHub
