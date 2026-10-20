# Cost & Latency Math: Pricing, Token Accounting & SLA Optimization

## Contents
1. [Pricing Model & Rates](#1-pricing-model--rates)
2. [Token Cost Accounting & Formulas](#2-token-cost-accounting--formulas)
3. [Image Token Calculation](#3-image-token-calculation)
4. [Expected Business Cost Equations](#4-expected-business-cost-equations)
5. [Latency Profiles & Time Budgets](#5-latency-profiles--time-budgets)
6. [Cost vs. Complexity Ceilings](#6-cost-vs-complexity-ceilings)
7. [Rules, Reasons, and Counter-Examples](#7-rules-reasons-and-counter-examples)

---

## 1. Pricing Model & Rates

As of **2026-10-21**, pricing for `POST /v1/decisions` on `gpt-6-luna` is structured as follows [volatile, documented as of 2026-10-09]:

| Component | Rate | Notes |
|---|---|---|
| **Input Tokens** | **$0.10 per 1,000,000 tokens** | All text, images, and question definitions. |
| **Output Tokens** | **$0.00 (Zero)** | `output_tokens: 0`; no text generation charges. |
| **Reasoning Tokens** | **$0.00 (Zero)** | `reasoning_tokens: 0`; no chain-of-thought charges. |
| **Cached Tokens** | Not separately billed | `cached_tokens` appears in usage details, but separate cache read/write discounts are not currently published [documented]. |
| **Long-Context Cliff** | Multiplier at $\ge 272{,}000$ tokens | Significant price increase above threshold [inference/estimate]. |

---

## 2. Token Cost Accounting & Formulas

Total input tokens billed per request:
$$\text{Tokens}_{\text{total}} = \text{Overhead}_{\text{fixed}} + \text{Tokens}_{\text{input}} + \sum_{j=1}^{K} \text{Tokens}_{\text{question}_j}$$

- **Fixed Request Overhead ($\text{Overhead}_{\text{fixed}}$)**: ~137 to 145 tokens [community report].
- **Text Input Tokens ($\text{Tokens}_{\text{input}}$)**: Standard byte-pair encoding (~1 token per 4 English characters).
- **Question Definition Tokens ($\text{Tokens}_{\text{question}_j}$)**:
  - Instructions string: ~15 to 40 tokens.
  - Choices (`choice`): Each option's value and description (~15 to 30 tokens per option). A 5-choice question typically costs ~100–150 tokens.
  - Levels (`score`): Each level's label and description (~15 to 25 tokens per level). A 4-level score typically costs ~80–120 tokens.

---

## 3. Image Token Calculation

Image tokens are calculated strictly via the patch grid formula [documented]:

$$\text{patches}_w = \left\lceil \frac{\text{width}}{32} \right\rceil, \quad \text{patches}_h = \left\lceil \frac{\text{height}}{32} \right\rceil$$

$$\text{image\_tokens} = \left\lceil (\text{patches}_w \times \text{patches}_h) \times 1.2 \right\rceil$$

### Detail Modes
- `low`: Fits within $512 \times 512$ bounding box $\to$ max $16 \times 16 = 256$ patches $\to$ max $\lceil 256 \times 1.2 \rceil = 308$ tokens.
- `original`: Native patch grid. A $1024 \times 768$ photo $\to 32 \times 24 = 768$ patches $\to \lceil 768 \times 1.2 \rceil = 922$ tokens.

---

## 4. Expected Business Cost Equations

When setting thresholds, cascading stages, or choosing review capacity, frame all decisions using total expected cost:

$$\mathbb{E}[\text{Total Cost}] = \mathbb{E}[\text{Operational Cost}] + \text{Cost}_{\text{API}}$$

$$\mathbb{E}[\text{Operational Cost}] = P(\text{act}) \cdot C(\text{action}) + P(\text{review}) \cdot C_R + P(\text{FP}) \cdot C_{\text{FP}} + P(\text{FN}) \cdot C_{\text{FN}}$$

- $C_R$: Cost of human review (e.g. $2.50 per manual review).
- $C_{\text{FP}}$: Cost of a False Positive error.
- $C_{\text{FN}}$: Cost of a False Negative error.
- $\text{Cost}_{\text{API}}$: Token cost ($0.10 / 1\text{M}$ tokens $\approx \$0.0000001/\text{token}$).

Because API tokens are orders of magnitude cheaper than human review or business error costs ($0.0003 vs $2.50), **never optimize API token micro-costs at the expense of higher error rates**.

---

## 5. Latency Profiles & Time Budgets

- **API Median Latency (p50)**: ~255ms on typical 3-to-6 question batched requests [community report].
- **API Tail Latency (p99)**: ~600ms to 1,200ms depending on gateway queuing.
- **Serial Cascades Multiply Latency**: A 3-stage cascade runs 3 sequential round-trips:
  $$\text{Latency}_{\text{p50}} \approx 3 \times 255\text{ms} = 765\text{ms}$$
  $$\text{Latency}_{\text{p99}} \approx 3 \times 1{,}000\text{ms} = 3{,}000\text{ms}$$
- **Budget Rule**: If your service has a strict 500ms p99 SLA, multi-round serial cascades are prohibited in the synchronous path. Use speculative branching or asynchronous worker execution.

---

## 6. Cost vs. Complexity Ceilings

Do not build complex architectural optimizers for savings smaller than the maintenance overhead they create:
- If a pipeline evaluates 10,000 requests per month, total monthly API spend is:
  $$10{,}000 \times 1{,}000 \text{ tokens} = 10\text{M tokens} = \$1.00/\text{month}$$
- Spending 40 developer hours to build dynamic prefix-caching or 3-tier cascades to save 40% reduces monthly spend from $1.00 to $0.60.
- **Rule of Thumb**: Only invest in elaborate token-reduction architectures (cascades, dynamic detail downscaling) when monthly volume exceeds 1,000,000 calls ($\ge \$100/mo$) or when input sizes exceed 100,000 tokens.

---

## 7. Rules, Reasons, and Counter-Examples

| Rule | Reason | Counter-Example (Anti-Pattern) |
|---|---|---|
| **Frame all threshold trade-offs as expected cost** | Intuitive cutoffs ignore real-world business penalties and labor costs. | Choosing a threshold of 0.90 because "90% sounds safe" without knowing $C_{\text{FP}}$ and $C_{\text{FN}}$. |
| **Never spend high engineering effort on low-volume token savings** | Decisions API tokens are exceptionally inexpensive ($0.10/1M); complexity overhead dwarfs token savings. | Spending two weeks optimizing a prompt to save 80 tokens on an internal tool called 200 times a day. |
| **Enforce a strict latency budget on multi-stage chains** | Serial round-trips quickly breach synchronous web SLA limits. | Designing a 4-round interactive chat moderator that takes 2.5 seconds to return a verdict. |
| **Always account for the fixed request overhead (~140 tokens)** | Underestimating base token usage produces skewed unit economics on short inputs. | Assuming a 5-word text input will only consume 5 tokens on the bill. |
