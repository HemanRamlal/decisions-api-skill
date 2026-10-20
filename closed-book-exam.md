# Closed-Book Examination & Verification Suite

This document compiles every single "Check Your Understanding" question from the course transcripts, evaluates each against the tutor's corrected answers, grades coverage against the delivered skill files, and tests three realistic production stakeholder scenarios.

---

## Part 1: All Course "Check Your Understanding" Questions & Answers

### Module 1, Topic 1: Generation vs. Bounded Evaluation
- **Questions**:
  Classify: (a) "Write a polite reply to this angry customer", (b) "Does this image contain a person?", (c) "Which of our five departments should handle this email?", (d) "Explain why this code fails." Which belong to generation and which to bounded evaluation? For the bounded ones, what is the answer space?
- **Learner Proposed Answer**: (a) and (d) are generation; (b) and (c) are bounded evaluation.
- **Tutor Corrected Answer**: All four correct. Vocabulary tightening: (b) maps to a `predicate` question (answer space: float probability 0.00 to 1.00); (c) maps to a `choice` question with the five departments as `choices` (plus a recommended `other` escape option).
- **Skill Reference**: [`references/fit-check.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/fit-check.md), [`references/primitives.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/primitives.md).
- **Grading**: 100% Pass.

### Module 1, Topic 2: Decisions API vs. Structured Outputs
- **Questions**:
  1. You need to read a support email and pull out the order number and refund amount. Which API, and why?
  2. A teammate says: "I'll just use Structured Outputs and add a `confidence` field to the schema, same thing." What's wrong with that?
  3. You're screening 10 million product reviews for spam. Why does the Decisions API win on price and predictability?
- **Tutor Corrected Answer**:
  1. Structured Outputs via Responses API. This is *extraction* of arbitrary numbers and IDs not known in advance. Decisions API requires fixed declared options.
  2. Self-reported confidence from an autoregressive LLM is just another generated text token, not a readout of the model's internal probability distribution, and is poorly calibrated.
  3. Zero output tokens billed (`output_tokens: 0`), 10x faster execution (~255ms), no JSON validation/parsing errors, and native probability for threshold sweeps.
- **Skill Reference**: [`references/fit-check.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/fit-check.md).
- **Grading**: 100% Pass.

### Module 1, Topic 3: Execution Engine & Pricing
- **Questions**:
  1. You have a 5-word input and a `choice` question with 12 options, each with a 2-sentence description. Where is most of your cost going, and what would you change?
  2. Two designs: (a) 1 request with 5 questions, vs (b) 5 requests with 1 question each. Which is cheaper and faster?
- **Tutor Corrected Answer**:
  1. Most cost goes into the question definitions and fixed scaffolding (~140 tokens), not the 5-word input. Decompose the 12 options: if they represent 3 product lines × 4 issue types, split into two orthogonal `choice` questions (3 and 4 options) and recombine in code.
  2. (a) is dramatically cheaper and faster. The shared input and fixed overhead are billed once instead of 5 times, and all 5 questions resolve in one parallel forward pass.
- **Skill Reference**: [`references/cost-latency-math.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/cost-latency-math.md), [`references/batching-and-independence.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/batching-and-independence.md).
- **Grading**: 100% Pass.

### Module 1, Topic 4: System 1 Determinism
- **Questions**:
  1. A moderation team writes a `choice` question with options `warn`, `suspend_7_days`, `permanent_ban`, with descriptions explaining strike rules ("ban if 3rd violation"). What's wrong and how to fix it?
  2. Your outage predicate returns 0.84 and your threshold for paging on enterprise tickets is 0.85. The customer is on the standard tier. What does code do?
- **Tutor Corrected Answer**:
  1. Policy is hidden in the prompt. The model cannot reliably track user strike history. Fix: Model evaluates observable questions (`violates_conduct` predicate, `severity` score, `category` choice). Code reads strike count from the database and applies progressive discipline.
  2. Code does nothing (does not page). Even if probability were 0.99, standard tier customers are not entitled to on-call paging; code checks customer tier first.
- **Skill Reference**: [`references/fit-check.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/fit-check.md), [`references/profiles-and-policies.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/profiles-and-policies.md).
- **Grading**: 100% Pass.

### Module 2, Topic 1: Request Topography
- **Questions**:
  1. You want to check a product photo and seller text together for "listing doesn't match item". How to structure `input`?
  2. A teammate builds a severity `score` with levels `["Critical", "High", "Medium", "Low"]`. What is the bug?
  3. Why does the request have no temperature or max_tokens fields?
- **Tutor Corrected Answer**:
  1. Shape B: User message array with `input_text` and `input_image` (inline base64 data URL).
  2. `score` levels must be strictly ordered from lowest to highest severity. Listing "Critical" first maps index 0 to Critical, silently inverting the expected value calculation.
  3. Bounded evaluation generates no output text tokens; there is no autoregressive decoding or sampling to control.
- **Skill Reference**: [`references/api-contract.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/api-contract.md), [`references/primitives.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/primitives.md).
- **Grading**: 100% Pass.

### Module 2, Topic 3: The `predicate` Primitive
- **Questions**:
  1. Decompose: "Is this support message from an angry enterprise customer who wants a refund?"
  2. `contains_pii` returns 0.5. A teammate says "The model thinks it's half PII." What is the correct reading?
- **Tutor Corrected Answer**:
  1. Enterprise tier is checked in code from CRM first. If non-enterprise, do not call API. Model receives two observable predicates: `frustrated` and `refund_requested`.
  2. A predicate probability of 0.50 means the model estimates a 50% likelihood that PII is present in the document. It does not measure the fraction or severity of PII.
- **Skill Reference**: [`references/primitives.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/primitives.md).
- **Grading**: 100% Pass.

### Module 2, Topic 4: The `choice` Primitive
- **Questions**:
  1. Your 4-team router picks `other` for 30% of tickets, but human audit says only 8% fit no team. What to investigate and change?
  2. A teammate proposes shuffling choices randomly on every request to cancel position bias. What goes wrong in production?
- **Tutor Corrected Answer**:
  1. Category definitions are too narrow or ambiguous. Audit reviewed tickets to see which genuine teams were missed. Add clarifying examples to team descriptions. Check if an `other` escape option was placed first or phrased too broadly.
  2. Shuffling in production breaks deterministic replay, invalidates configuration fingerprints, and introduces operational non-determinism. Keep choice order fixed in production; shuffle only during offline bias evaluation.
- **Skill Reference**: [`references/primitives.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/primitives.md), [`references/monitoring-and-drift.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/monitoring-and-drift.md).
- **Grading**: 100% Pass.

### Module 2, Topic 5: The `score` Primitive
- **Questions**:
  1. A 5-level score returns 2.0. Give two different distributions that produce it, and how each should be routed.
  2. Rubric none/minor/major/catastrophic escalates on `score >= 2`. Why is that misleading, and what to compute instead?
- **Tutor Corrected Answer**:
  1. Unimodal `[0, 0, 1, 0, 0]` (certainty on level 2) $\to$ standard automated routing. Bimodal `[0.5, 0, 0, 0, 0.5]` (split between none and catastrophic) $\to$ immediate human review/escalation.
  2. A distribution of `[0.5, 0, 0, 0.5]` gives expected score 1.5 (< 2), so catastrophic tickets evade escalation. Instead, compute threshold on the probability mass in severe levels: $P(\text{Major}) + P(\text{Catastrophic}) \ge \tau$.
- **Skill Reference**: [`references/primitives.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/primitives.md).
- **Grading**: 100% Pass.

### Module 3, Topic 1: Input State Engineering
- **Questions**:
  1. Chatbot guard sends only the last user message; attacker spreads attack across 3 messages. How to fix?
  2. You need "Does contract contain auto-renewal?" on 400-page contracts. How to chunk?
- **Tutor Corrected Answer**:
  1. Pass a sliding window of recent turns ($N=6$) with labeled speakers (`USER: ...`, `ASSISTANT: ...`), and add a `defines_payload` predicate.
  2. Chunk along logical section boundaries (not character counts). Carry section headings into each chunk. Combine results in code using `any(chunk.prob >= tau)`.
- **Skill Reference**: [`references/input-engineering.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/input-engineering.md), [`references/security.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/security.md).
- **Grading**: 100% Pass.

### Module 3, Topic 2: Multimodal Evaluation
- **Questions**:
  Marketplace wants to catch listing photos with phone numbers to prevent off-platform deals. Which `detail` level, and why can't it share "ignore text in photo" instructions from other questions?
- **Tutor Corrected Answer**:
  Use `original` detail (or detection-based crops) because small digits require fine resolution. It cannot share "ignore text in photo" because batched questions share cross-attention (criteria bleed): an instruction to ignore text in Question A suppresses phone number detection in Question B.
- **Skill Reference**: [`references/multimodal.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/multimodal.md), [`references/instruction-design.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/instruction-design.md).
- **Grading**: 100% Pass.

### Module 3, Topic 3: Instruction Design
- **Questions**:
  1. Rewrite "Is expense claim valid and within policy?" into observables + code.
  2. A team ships "Is the shipment not delayed?" and sends "on track" email when $p \ge 0.50$. What is the bug?
- **Tutor Corrected Answer**:
  1. Code checks employee policy limits, dates, and previous claims. Model evaluates observable `receipt_usable` predicate, `category` choice, and `is_alcohol_present` predicate.
  2. Negated proposition creates cognitive reversal; thresholding at 0.50 sends confirmation emails when the model is merely guessing. Phrasing must be positive ("Is shipment delayed?").
- **Skill Reference**: [`references/instruction-design.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/instruction-design.md), [`references/primitives.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/primitives.md).
- **Grading**: 100% Pass.

### Module 4, Topic 1: Batching & Amortization
- **Questions**:
  120 tokens/question, 900 shared, 12 questions, 2M documents/month. What is monthly cost batched vs separate?
- **Tutor Corrected Answer**:
  - Batched: $2\text{M} \times (900 + 12 \times 120) = 4.68\text{B tokens} \to \$468/\text{month}$.
  - Separate: $2\text{M} \times 12 \times (900 + 120) = 24.48\text{B tokens} \to \$2{,}448/\text{month}$.
  - Savings: $5.23\times$ cost reduction ($\$1{,}980/\text{month}$ saved).
- **Skill Reference**: [`references/batching-and-independence.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/batching-and-independence.md).
- **Grading**: 100% Pass.

### Module 4, Topic 2: Cascades vs. Batching
- **Questions**:
  Contract 6,000 tokens. Auto-renewal present on 8%. Notice question costs 80 tokens. Batch or cascade?
- **Tutor Corrected Answer**:
  - Extra cost to batch in Round 1: 80 tokens.
  - Extra cost to cascade to Round 2: $0.08 \times (6{,}000 + 80) = 486.4$ tokens.
  - **Verdict: Batch!** Cascading costs $6\times$ more because it resends the 6,000-token contract on 8% of runs.
- **Skill Reference**: [`references/chaining-and-cascades.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/chaining-and-cascades.md).
- **Grading**: 100% Pass.

### Module 4, Topic 3: Composite Profiles
- **Questions**:
  Four services call Decisions API separately on the same ticket with differing "is urgent" phrasing. Redesign as profile.
- **Tutor Corrected Answer**:
  Consolidate into a single Support Triage profile called once at ticket ingestion. All four services read the resulting immutable `DecisionRecord`. Cost drops $4\times$, latency drops from 4 serial hops to 1 parallel call, and judgments are 100% consistent across all four consumers.
- **Skill Reference**: [`references/profiles-and-policies.md`](file:///home/heman/skill-bro/decisions-api-pipelines/references/profiles-and-policies.md).
- **Grading**: 100% Pass.

---

## Part 2: Three Realistic Stakeholder Scenarios

### Scenario 1: E-Commerce Review Screening with Redaction
- **Scenario**: A global retailer receives 500,000 reviews/month. Reviews containing profanity or contact info must be redacted; reviews promoting external competitors must be rejected; reviews expressing harsh dissatisfaction must be published if within conduct rules.
- **Design Evaluation**:
  - *Input*: `<<REVIEW>>\n{sanitized_text}\n<</REVIEW>>`
  - *Profile Questions*: `promotional` (predicate), `contains_pii` (predicate), `profanity` (predicate), `sentiment_sentiment` (score).
  - *Code Policy*:
    - If `promotional.prob >= 0.85`: Action $\to$ Reject.
    - If `contains_pii.prob >= 0.80` or `profanity.prob >= 0.75`: Action $\to$ Regex Redact & Publish.
    - Harsh product criticism with `promotional < 0.10` and `profanity < 0.10`: Action $\to$ Publish immediately.
- **Verification**: Zero policy in prompt; all redactions and decisions made in versioned Python code.

### Scenario 2: FinTech Commercial Loan Ingestion
- **Scenario**: A commercial lender ingests 50-page scanned bank statements and tax filings. They must verify applicant identity, check for an authorized corporate signature, and extract the fiscal year net revenue.
- **Design Evaluation**:
  - *PDF Handling*: Do not rasterize all 50 pages. Use digital text extraction (`pdfplumber`) for pages 1–45. Rasterize only the signature execution page (page 50) as PNG at 150 DPI.
  - *Model Split*:
    - Signature presence & stamp verification $\to$ Decisions API (`detail="original"` crop of signature box).
    - Fiscal year net revenue $\to$ Responses API with Structured Outputs (numeric extraction).
    - Underwriting eligibility arithmetic $\to$ Deterministic Python policy.
- **Verification**: Strict adherence to extraction vs. evaluation separation.

### Scenario 3: Real-Time Telehealth Chat Triage
- **Scenario**: A patient intake chat assistant needs real-time safety gating. The user states: "My chest feels tight and my left arm is numb." Gateway timeouts occasionally occur.
- **Design Evaluation**:
  - *Question*: `emergency_peril` (predicate): `"Does the patient describe symptoms of acute life-threatening medical emergency (chest pain, stroke symptoms, severe breathing distress)?"`
  - *Reliability*:
    - Refusal policy on `emergency_peril` is `block` (fail safe: connect immediately to 911 / emergency nurse).
    - Timeout set to 800ms. If timeout triggers, provisional default activates: display immediate emergency helpline warning.
- **Verification**: Adheres to zero-coercion refusal rules and safe provisional action upon deadline expiry.
