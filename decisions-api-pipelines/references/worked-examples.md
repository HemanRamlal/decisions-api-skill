# Worked Examples: Fuzzy Question Decompositions & Observable Pipelines

## Contents
1. [Support Triage Pipeline](#1-support-triage-pipeline)
2. [Review Screening Pipeline](#2-review-screening-pipeline)
3. [Return Claims Pipeline](#3-return-claims-pipeline)
4. [Contract Review Pipeline](#4-contract-review-pipeline)
5. [Insurance Claims Cascade Pipeline](#5-insurance-claims-cascade-pipeline)
6. [Expense Claims Validation Rewrite](#6-expense-claims-validation-rewrite)
7. [Content Moderation Strike Policy Rewrite](#7-content-moderation-strike-policy-rewrite)
8. [ProofWriter Deduction Depth Examples](#8-proofwriter-deduction-depth-examples)

---

# Decompositions

For each pipeline: the original fuzzy question, the observable questions it was split into,
and everything that moved into code. Spec keys are the names `dk calibrate` writes under
`specs/`. Until a key has a spec, its decisions go to review (shadow mode).

---

## 1. Support triage (`pipelines/support_triage.py`)

**Original fuzzy question:** "What's going on with this ticket, and who should care?"

One profile request per ticket. Three policies read it, so the input is billed once and every consumer sees the same judgment.

| Question | Type | Observable criterion | Read by |
|---|---|---|---|
| `team` v4 | choice: 3 teams + `out_of_scope` + `no_request` | Which team owns what the customer needs resolved; escapes only when clearly none fits, or no need is stated | Router |
| `outage` v3 | predicate | The customer reports the product is unusable for them right now | Paging |
| `impact` v3 | score, 5 levels, None → Blocked | How much the problem stops work; adjacent levels differ by one fact | SLA priority |
| `scope` v2 | score, 3 levels | How many people the ticket says are affected | SLA priority |
| `frustrated` v2 | predicate | Hostile language, repeated-failure complaints, threats to cancel | Profile (account management) |
| `refund_requested` v1 | predicate | Asks for money back | Profile only: intent, never authorization |
| `mentions_delivery` v1 | predicate | Mentions a delivery, package, shipment, or tracking number | Consistency check on `team` |

**Moved into code**
- Customer tier and SLA, from your CRM. Affected accounts, from monitoring.
- The escape decision: a cutoff on P(`out_of_scope`) + P(`no_request`), separate from the team decision.
- Team choice: the best team's probability renormalized over the real teams, with its own cutoffs.
- Escalation: a reasoning model breaks ties between the top two teams. An answer outside the top two goes to a human. It never runs on an uncalibrated band.
- Priority: blocked × wide (or monitoring says wide) → P1. An uncertain block is treated as a block. Premium SLA bumps one level.
- Paging: only for enterprise customers. The review zone goes to an on-call queue; nobody is woken for an uncertain outage.
- Contradictions between `team` and `mentions_delivery`, or between `outage` and `impact`, send an auto-route to a human.
- Refund eligibility is never decided here: `refund_requested` is the customer's intent, not an entitlement.

**Specs**

| Key | Signal |
|---|---|
| `support_triage.team:escape` | P(escapes); single cutoff |
| `support_triage.team` | Renormalized team probability; act / escalate / human |
| `support_triage.outage` | Probability |
| `support_triage.blocked` | P(top impact level); single cutoff |
| `support_triage.wide` | P(A group) + P(Everyone); single cutoff |

**Refusals:** `team` → human queue. `outage` → on-call queue. `impact` and `scope` count as missing, and missing impact means P2, never the lowest priority.

**Degraded mode:** deterministic keyword routing (a unique best keyword team, otherwise human), priority by SLA, and paging left to monitoring alerts.

---

## 2. Review screening (`pipelines/review_screening.py`)

**Original fuzzy question:** "Is this review acceptable?"

| Question | Type | Observable criterion |
|---|---|---|
| `promotional` v4 | predicate | Promotes a product, link, or contact method other than the product in PRODUCT NAME; comparisons from the reviewer's own experience excluded |
| `off_topic` v3 | predicate | About something other than the product; delivery complaints count as on-topic |
| `personal_info` v2 | predicate | Phone number, email, street address, or a private individual's full name |

**Moved into code**
- Product name and category, from your catalog, as labeled context so the questions can refer to "the product".
- Delimiting the review and neutralizing `<<`, `>>`, and lines that imitate field labels. This closes the `<</REVIEW>>` attack; `tests/test_live.py` checks it against the API.
- Email and phone regexes alongside the model. Only match counts are logged, never the values.
- Action precedence: redaction hold > reject > review > publish.
- The truncation flag, and the author's hashed ID sent as `safety_identifier`.

**Specs:** `review_screening.promotional`, `.off_topic`, `.personal_info`. Each is a three-zone predicate with a review cap; `personal_info` has a strict cap on pass-zone errors.

**Refusals:** every question holds the review for a moderator.

**Degraded mode:** hold. An unscreened review is never published.

---

## 3. Return claims (`pipelines/return_claims.py`)

**Original fuzzy question:** "Is this return claim legitimate?"

Code settles what it can before any API call (`precheck`): the order belongs to the customer, delivery is inside the return window, and prior damage claims are under the limit.

| Question | Type | Observable criterion |
|---|---|---|
| `photo_usable` v2 | predicate | The item in CUSTOMER PHOTO is clear enough to judge its condition: the evidence gate |
| `same_product` v2 | predicate | CUSTOMER PHOTO shows the same product as LISTING PHOTO |
| `damaged` v3 | predicate | Crack, tear, or dent; shadows, packaging damage, and text written in the photo excluded |

**Moved into code**
- Image preprocessing: EXIF orientation, a deterministic resize, and a JPEG re-encode that strips GPS metadata.
- Detail per image: the listing photo at low (it only identifies the product), the customer photo at high.
- A pre-flight token estimate with a hard guard. The logged difference from actual usage tests the sizing formula on gpt-6-luna.
- Gating order: unusable photo → ask for a new one; uncertain → human; mismatch → human; then damage.
- Payouts and replacements are actions downstream of `damage_claim_flow`, executed by your systems with the decision id as idempotency key.

**Specs:** `return_claims.photo_usable`, `.same_product`, `.damaged`.

**Refusals:** human queue. **Degraded mode:** human review; no automatic damage payout without a decision.

---

## 4. Contract review (`pipelines/contract_review.py`)

**Original fuzzy question:** "Is this contract risky for us?" Narrowed to the two clauses legal asked for: auto-renewal with a long notice period, and the vendor's right to terminate for convenience.

| Step | Where | What |
|---|---|---|
| Text layer | code (pypdf) | Under 500 characters in the whole PDF → `needs_ocr` |
| Sectioning | code | Split on headings; cap pieces at about 5k tokens so each judgment is glance-sized |
| Prefilter | code | A broad regex skips sections that cannot hold either clause |
| `auto_renewal` v2 | predicate per section | The section makes the agreement renew automatically unless a party gives notice |
| `vendor_termination` v1 | predicate per section | The section lets the party in VENDOR terminate without cause or for convenience |
| Aggregation | code | "Exists" questions: the maximum over sections; refused sections block a "no clause" conclusion |
| Notice period | Responses API, Structured Outputs | Amount, unit, and an exact quote from the top section; the quote must appear in the section text |
| Unit conversion and policy | code | Days per unit, and the 60-day policy limit |

**Moved into code:** sectioning, prefiltering, max-aggregation, the grounding check, unit conversion, the policy limit, and the vendor's name (from your contract system).

**Specs:** `contract_review.auto_renewal`, `.vendor_termination`. Signal: the maximum section probability.

**Refusals:** legal review. **Degraded mode:** legal review.

---

## 5. Insurance claims (`pipelines/insurance_claims.py`)

**Original fuzzy question:** "Is this claim complete, and does it show water damage?"

| Stage | Detail | Per-page questions | Pages |
|---|---|---|---|
| 1 | low | `photo_p{n}`: contains a photograph (drawings, logos, signatures, scanned text excluded); `declaration_p{n}`: a declaration section with a signature line | All |
| 2 | high | `water_p{n}`: a photograph shows stains, standing water, warped flooring, or mold | Pages whose photo answer was not "pass" |
| 2 | high | `signed_p{n}`: a handwritten or drawn signature in the signature box | The declaration page |

**Why a cascade:** water damage and signatures are relevance dependencies that need high detail. Batching would send every page at high detail.

**Cost check:** an A4 page at 150 dpi renders at about 1240 × 1754.
- At low detail that's about 231 tokens per page; at high, about 2,574.
- For a 30-page claim with four photo pages: all pages at high ≈ 77,000 tokens; the cascade ≈ 30 × 231 + 5 × 2,574 ≈ 20,000.

**Moved into code**
- Rendering and labeling pages.
- Batching within 128 images, 200 questions, and a 200,000-token budget per request.
- Stage selection, with uncertain or refused photo answers going to stage 2.
- Choosing the declaration page: the highest act-zone probability.
- Routing precedence: human > request signature > water-damage track > standard track.

**Specs:** `insurance_claims.photo`, `.declaration`, `.water`, `.signed`. Calibrate stage 1 first. `water` is calibrated only on pages that reach stage 2, which is exactly the population its cutoff is applied to.

**Refusals:** human review. **Degraded mode:** human review.

---

## Where the course's rules live in the kit

| Rule | Module |
|---|---|
| Strict response contract; refusal as an explicit state; match by name | `decisions_kit/contract.py` |
| Versioned questions, one source of truth, refusal policy per question | `decisions_kit/registry.py` |
| Evidence only in `input`; delimiting; images as data URLs; EXIF; token estimates | `decisions_kit/inputs.py` |
| Retry only what can succeed; deadlines; retry budget; breaker; gateway refusals | `decisions_kit/client.py` |
| Shadow mode until calibrated; specs keyed to config and behavior | `decisions_kit/thresholds.py` |
| Ranking check, constrained cost sweep, per-zone certification | `decisions_kit/calibration.py` |
| Paired comparison and the written gate | `decisions_kit/evaluation.py` |
| Replay set, behavior fingerprint, PSI, per-zone audits | `decisions_kit/drift.py` |
| Live contract tests | `decisions_kit/contract_tests.py` |
| Tie-break escalation and grounded extraction | `decisions_kit/escalation.py` |
| Precheck → observe → policy → degraded, logged with reason codes | `decisions_kit/pipeline.py` |


---

## 6. Expense Claims Validation Rewrite

**Original fuzzy question:** "Is this expense claim valid and within policy?"

**Why it fails:** Conflates image evidence quality, expense category, receipt dates, company meal allowances, and policy thresholds into a single unobservable judgment.

**Observable Questions:**
1. `receipt_usable` (predicate): Is the receipt image legible, showing date, vendor, and total amount?
2. `category` (choice): `meal`, `travel_air`, `lodging`, `supplies`, `other`.
3. `is_alcohol_present` (predicate): Does the receipt list alcoholic beverages or bar charges?

**Moved into code:**
- Employee eligibility, policy limits ($50/day meal cap), and travel approval status.
- Receipt age: `datetime.now() - receipt_date <= timedelta(days=30)` (date difference computed in code).
- Alcohol policy: If `is_alcohol_present` is true, deduct itemized line items or route to manager approval.
- Entitlement: Reimbursement is authorized deterministically in Python against corporate travel ledgers.

---

## 7. Content Moderation Strike Policy Rewrite

**Original fuzzy question:** "Should this user be banned for this comment?"

**Why it fails:** Puts progressive discipline (3-strike rule), user history, and account type into prompt text, requiring the model to remember state and compute sanctions.

**Observable Questions:**
1. `violates_conduct` (predicate): Does the comment use dehumanizing slurs, incite physical violence, or promote commercial scams?
2. `severity` (score, 4 levels): Cosmetic, Minor, Severe, Egregious.
3. `category` (choice): `harassment`, `scam`, `hate_speech`, `off_topic`, `other`.

**Moved into code:**
- User strike history: Read prior strike count from database (`user.strikes`).
- Progressive sanction policy:
  - Strike 1: Warning email.
  - Strike 2: 7-day suspension.
  - Strike 3: Permanent account ban.
  - If `severity == Egregious`, skip strikes and immediately ban.
- Automated appeal routing: If user submits appeal, `category` tag routes to relevant specialist team.

---

## 8. ProofWriter Deduction Depth Examples

Demonstrates the boundary of Decisions API System 1 evaluation vs. reasoning models:

### Depth 0: Direct Fact (Ideal for Decisions API)
- *Facts*: The dog is big. The cat is red. The cat likes the dog.
- *Question*: "Is the cat red?"
- *Status*: Direct match. Model evaluates with >99% confidence.

### Depth 1: Single Rule (Supported)
- *Facts*: Erin is cold. Erin is rough. If someone is cold, they are quiet.
- *Question*: "Is Erin quiet?"
- *Status*: Single inference step. Evaluates reliably (>90%).

### Depth 2: Two Rules Chained (Decompose or Move to Code)
- *Facts*: Gary is round. If someone is round, they are big. If someone is big, they are slow.
- *Question*: "Is Gary slow?"
- *Status*: Borderline (~70% accuracy). Decompose into observable sub-questions.

### Depth 3+: Deep Deduction (Prohibited on Decisions API)
- *Facts*: Multiple branching rules with distractors.
- *Status*: Fails without token-by-token chain-of-thought scratchpad. Route to Responses API reasoning models (`gpt-6-sol`).
