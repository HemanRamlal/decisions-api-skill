# Testing Playbook: ROI Prioritization, Fake Client & Test Suites

## Contents
1. [ROI-Based Test Prioritization Framework](#1-roi-based-test-prioritization-framework)
2. [Offline-First Testing Architecture](#2-offline-first-testing-architecture)
3. [Contract Verification Test Suite](#3-contract-verification-test-suite)
4. [Live API Testing & Cost Caps](#4-live-api-testing--cost-caps)
5. [Probe Replay Regression Testing](#5-probe-replay-regression-testing)
6. [Arithmetic & Property Tests](#6-arithmetic--property-tests)
7. [Rules, Reasons, and Counter-Examples](#7-rules-reasons-and-counter-examples)

---

## 1. ROI-Based Test Prioritization Framework

Candidate tests are evaluated and scored according to their return on investment (ROI):

$$\text{ROI Score} = \frac{P(\text{defect exists}) \times \text{Cost}(\text{defect ships})}{\text{Cost to run (money, time, stakeholder effort)}}$$

### Scored Test Catalog Template

| Test Class | Focus Area | $P(\text{defect})$ | Cost if Ships | Cost to Run | ROI Score | Action |
|---|---|---|---|---|---|---|
| **Contract Parser & Rounding** | Defensive parser handles two-decimal sums and missing fields | High (0.80) | High ($5,000) | Low (0.01h offline) | **400,000** | **Mandatory Unit Test** |
| **Question Registry & Scaffolding** | Unique names, non-empty descriptions, ascending levels | High (0.70) | Med ($1,000) | Low (0.01h offline) | **70,000** | **Mandatory Unit Test** |
| **Resilience & Fallbacks** | Refusals trigger question fallback; retries back off | Med (0.50) | High ($10,000) | Low (0.02h offline) | **250,000** | **Mandatory Unit Test** |
| **Probe Replay Determinism** | Frozen inputs yield identical outputs across model runs | Med (0.40) | High ($5,000) | Low ($0.05 live) | **40,000** | **Daily Canary** |
| **Interference Shift Sweep** | Multi-question batching shifts target probability | Low (0.20) | Low ($500) | Med ($2.00 live) | **50** | **Pre-deployment gate** |
| **Paraphrase Sensitivity** | Instruction wording fragility | Med (0.30) | Med ($1,000) | Med ($1.50 live) | **200** | **Pre-deployment gate** |

Always present the scored ROI table to the stakeholder before running paid live tests.

---

## 2. Offline-First Testing Architecture

Pipelines must run 100% offline by default without requiring an `OPENAI_API_KEY` or network connectivity:
- Inject an abstract client protocol (`DecisionsClientProtocol`) into all pipeline constructors.
- In unit tests, inject `FakeDecisionsClient` loaded with canned, realistic response fixtures.
- Test all branches: happy path, edge-case probabilities ($0.0, 1.0$), bimodal score distributions, refusal answers, missing fields, and network timeouts.

---

## 3. Contract Verification Test Suite

Verify that the application's contract assumptions match the real Decisions API wire protocol:
- Test that `parse_decision` accepts valid responses where distribution sums equal $1.00 \pm \text{tol}$.
- Test that missing required questions trigger `ContractViolationError`.
- Test that unknown choices or invalid types raise immediate exceptions.
- Test that gateway-wrapped refusals (e.g. 502 with `refused to answer question "X"`) are recovered properly.

---

## 4. Live API Testing & Cost Caps

Live network tests are strictly opt-in and cost-controlled:
- Mark live tests with `@pytest.mark.live` in pytest.
- In `pyproject.toml`, set `addopts = "-m 'not live'"` so `pytest` skips live calls by default.
- Set a hard spend ceiling (e.g., `MAX_LIVE_BUDGET = 0.50`). The test harness tracks cumulative tokens and aborts immediately if the budget is breached.
- State estimated test cost to the stakeholder before executing live suites.

---

## 5. Probe Replay Regression Testing

- Maintain a frozen probe dataset (`data/probe_items.jsonl`) of 50 representative inputs.
- Execute probe replay:
  ```bash
  dk replay --twice
  ```
- If outputs differ across identical runs on the same day, inspect model temperature or network proxy modifications. If outputs shift across weeks, upstream model drift has occurred.

---

## 6. Arithmetic & Property Tests

Unit test all mathematical equations without API interaction:
- **Patch Count & Token Estimator**: Verify that image patch dimensions and token multipliers match the exact formula across boundary resolutions ($31\times 31$, $32\times 32$, $33\times 33$, $512\times 512$).
- **Expected Score**: Verify that $\text{score} = \sum (i \cdot p_i) / \sum p_i$ calculates correctly and handles normalization when probabilities sum to $0.99$ or $1.01$.
- **Binomial Bounds**: Verify that `error_upper_bound(0, 300)` calculates $\approx 0.010$.
- **PSI**: Verify that two identical distributions yield $\text{PSI} = 0.0$.

---

## 7. Rules, Reasons, and Counter-Examples

| Rule | Reason | Counter-Example (Anti-Pattern) |
|---|---|---|
| **Make test suites offline by default** | Prevents CI/CD build failures due to API outages, billing exhaustion, or network lag. | Writing unit tests that fail if `OPENAI_API_KEY` is not exported in GitHub Actions. |
| **Mark all live API tests with `@pytest.mark.live`** | Prevents unintended billing when developers run standard `pytest`. | Committing a test that makes 500 live API calls on every git pre-commit hook. |
| **Score candidate tests by ROI before execution** | Focuses engineering effort on high-impact failure modes rather than low-value tests. | Spending days running exhaustive paraphrase tests while leaving basic contract parsing untested. |
| **Cap live test spend in code** | Prevents runaway while-loops or recursive cascades from exhausting API quotas. | Running an automated load test against the live OpenAI Decisions API without a budget cap. |
