/**
 * Witness implementations for contracts/advisor.compact.
 *
 * This is the file that makes the whole privacy story real. Per Midnight's
 * docs: "the witness is not implemented in the Compact source code.
 * Instead, the implementation is the responsibility of the TypeScript code
 * of the DApp." These functions run LOCALLY, on the user's own machine —
 * never on a server, never on the AI backend, never on chain.
 *
 * IMPORTANT (read this before wiring this into midnight-js):
 * The exact shape of a witness object (how it's passed into a contract's
 * `simulate`/`callTx` in the current midnight-js SDK) changes between SDK
 * versions and isn't something to guess at from memory. Scaffold this
 * project from the official starter (`example-counter` or
 * `example-hello-world` — see README) and copy this logic into the
 * `witnesses` object shape *that starter already uses*. If you have it,
 * use the "Midnight Expert" Claude Code plugin / Midnight MCP mentioned in
 * the hackathon resources — it has live access to the current SDK API and
 * will not hallucinate the plumbing the way a general model might.
 *
 * The one thing that must NOT change no matter which SDK version you're
 * on: these functions must only ever read from local state
 * (`localPolicyStore` below) and must never make a network call.
 */

export type RiskLevel = 0 | 1 | 2; // LOW, MEDIUM, HIGH

export interface FinancialSnapshot {
  secretKey: Uint8Array;   // 32 bytes, generated once and stored locally
  income: bigint;
  expenses: bigint;
  savings: bigint;
  debt: bigint;
  riskTolerance: RiskLevel;
}

/**
 * Swap this for real local storage (encrypted browser storage, OS
 * keychain, whatever your frontend uses). The point is: this data
 * lives ONLY here, is read only by the witness functions below, and is
 * never sent anywhere except as inputs to local proof generation.
 */
let localPolicyStore: FinancialSnapshot | null = null;

export function setLocalPolicy(snapshot: FinancialSnapshot): void {
  localPolicyStore = snapshot;
}

function requirePolicy(): FinancialSnapshot {
  if (!localPolicyStore) {
    throw new Error(
      "No local financial policy set — call setLocalPolicy() first."
    );
  }
  return localPolicyStore;
}

/**
 * The witness object your midnight-js contract call expects. Names here
 * must match the `witness` declarations in advisor.compact exactly:
 * secretKey, income, expenses, savings, debt, riskTolerance.
 */
export const advisorWitnesses = {
  secretKey: (): Uint8Array => requirePolicy().secretKey,
  income: (): bigint => requirePolicy().income,
  expenses: (): bigint => requirePolicy().expenses,
  savings: (): bigint => requirePolicy().savings,
  debt: (): bigint => requirePolicy().debt,
  riskTolerance: (): bigint => BigInt(requirePolicy().riskTolerance),
};
