# Knowledge Gaps: Unverified Parameters, Gateway Discrepancies & Open Queries

## Contents
1. [Overview & Ground Rules](#1-overview--ground-rules)
2. [Catalog of Current Knowledge Gaps](#2-catalog-of-current-knowledge-gaps)
3. [Gateway Inconsistencies & Behavioral Discrepancies](#3-gateway-inconsistencies--behavioral-discrepancies)
4. [Questions for the Stakeholder / API Vendor](#4-questions-for-the-stakeholder--api-vendor)

---

## 1. Overview & Ground Rules
In accordance with engineering standards: **Never invent API details.**
When a parameter, limit, response property, or internal behavior is not explicitly confirmed by official documentation or reproducible benchmarks, it is cataloged here as an open knowledge gap. The pipeline adopts conservative, defensive defaults until clarification is obtained.

---

## 2. Catalog of Current Knowledge Gaps

### Gap 1: Official Wire Limits on Questions and Choices
- *What is known*: Third-party benchmarks and gateways (OpenRouter, community linters) report that requests are capped at **200 questions** and **255 options per choice** [community report].
- *What is missing*: OpenAI's official API reference as of 2026-10-21 omits explicit question and option limit numbers [documented].
- *Safe Default*: Enforce a client-side ceiling of 200 questions and 255 options in the schema validator.

### Gap 2: Prompt Caching Parameters & Roadmap
- *What is known*: In the 2026-10-19 reference update, `prompt_cache_key` and `prompt_cache_breakpoint` were documented with a 30-minute TTL. In the 2026-10-21 update, these parameters were removed from the request schema, though cache token fields remain in the `usage` response [documented].
- *What is missing*: Whether prompt prefix caching occurs automatically without caller parameters, or whether caching on `/v1/decisions` is temporarily disabled pending general availability.
- *Safe Default*: Do not rely on prompt caching in economic calculations; assume full input token pricing for all rounds. Pass experimental parameters only via `extra_body` in dedicated test scripts.

### Gap 3: Long-Context Multiplier Pricing Cliff
- *What is known*: The course notes indicate that very long inputs incur long-context pricing multipliers [inference/estimate].
- *What is missing*: The exact token boundary where multipliers kick in (assumed at 272,000 input tokens) and the exact multiplier rate ($1.5\times$ vs $2.0\times$).
- *Safe Default*: Enforce a hard client-side chunking limit at 100,000 tokens per request to ensure the pipeline never approaches the long-context threshold.

### Gap 4: Internal Model Architecture & Mechanism
- *What is known*: The endpoint returns probabilities, argmax choices with confidence, and continuous scores while billing 0 output tokens and 0 reasoning tokens [documented].
- *What is missing*: Whether OpenAI uses a constrained softmax over the vocabulary during prefill, dedicated classification heads trained into `gpt-6-luna`, or an internal embedding similarity projection.
- *Safe Default*: Treat internal mechanics as an unverified black box. Focus solely on empirical calibration (AUROC, ECE) over domain-specific validation sets.

### Gap 5: Refusal Taxonomy & Disclosed Reasons
- *What is known*: When a question is refused, the answer returns `type: "refusal"` and `name`. Refusal scores and specific policy categories are not disclosed [documented].
- *What is missing*: The exact list of safety categories that trigger per-question refusals vs. request-level HTTP 400 errors.
- *Safe Default*: Enforce mandatory per-question refusal handling (`REFUSAL_POLICY`) in the registry, treating all refusals as un-evaluated signals that require fallback.

---

## 3. Gateway Inconsistencies & Behavioral Discrepancies

| Gateway / Proxy | Observed Discrepancy | Impact | Client Mitigation |
|---|---|---|---|
| **Vercel AI Gateway** | Uses separate model ID `openai/gpt-6-luna-decisions` for Decisions API vs `openai/gpt-6-luna` for Chat [documented]. | Specifying `gpt-6-luna` silently defaults to Structured Outputs at 10x cost and latency. | Enforce model ID validation in configuration builder. |
| **OpenRouter** | Wraps per-question refusals in HTTP 502 Bad Gateway with message `refused to answer question "X"` [community report]. | Kills surviving answers in the batched request. | Parse 502 error body using regex; recover surviving questions via immediate retry. |
| **LiteLLM** | Drops `prompt_cache_key` parameters silently for certain model versions without error [community report]. | Caching experiment fails silently. | Inspect `usage.input_tokens_details.cached_tokens` in tests to confirm gateway passthrough. |

---

## 4. Questions for the Stakeholder / API Vendor

1. **Question Limits**: What is the officially supported SLA limit on maximum batched questions per request for production enterprise tiers?
   - *Default*: 200 questions.
2. **Caching Availability**: When will explicit prompt caching parameters be re-introduced to the production request schema?
   - *Default*: Assume caching is unsupported.
3. **Model Pinning**: Will OpenAI introduce pinned snapshot IDs (e.g. `gpt-6-luna-2026-10-21`) upon General Availability to eliminate upstream drift?
   - *Default*: Maintain daily probe replay suites to detect unannounced model shifts.
