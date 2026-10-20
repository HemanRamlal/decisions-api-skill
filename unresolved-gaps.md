# Unresolved Knowledge Gaps & Autonomous Decision Defaults

## Overview
This audit document catalogs all open knowledge gaps, unverified API behaviors, and ambiguous vendor details identified across the source materials, along with the conservative autonomous default adopted by the `decisions-api-pipelines` skill.

---

## Catalog of Gaps & Autonomous Defaults

| # | Unresolved Knowledge Gap | Source Evidence & Ambiguity | Autonomous Default Adopted | Operational Impact |
|---|---|---|---|---|
| **1** | **Official Batched Question Limits** | Third-party benchmarks (OpenRouter) report a 200-question ceiling. OpenAI's reference as of 2026-10-21 states no explicit maximum. | **Enforce client-side maximum of 200 questions** per request in schema validator. | Prevents request rejection; maintains sub-second latency SLA. |
| **2** | **Option Limit per Choice** | Community linting rules cite a 255-option limit. Official reference omits the limit. | **Enforce client-side maximum of 255 options** per `choice` primitive. | Prevents silent gateway truncation. |
| **3** | **Prompt Caching Roadmap on Decisions Endpoint** | Documented in 2026-10-19 reference (`prompt_cache_key`), but removed from request schema in 2026-10-21 reference update. | **Assume caching parameters are unsupported**. Isolate caching checks to dedicated opt-in experiment script (`scripts/experiments/caching_experiment.py`). | Prevents reliance on unannounced cost savings in production financial projections. |
| **4** | **Long-Context Pricing Multiplier Boundary** | Sources mention long-context multipliers for very long documents (inferred at 272,000 tokens). Exact multipliers and thresholds are unpublished. | **Enforce client-side chunking at 100,000 tokens**, far below the 272k threshold. | Guarantees standard $0.10/1M pricing; avoids unexpected cost spikes. |
| **5** | **Exact Internal Softmax Mechanism** | Described conceptually as "constrained softmax", but OpenAI's internal layer/head architecture is proprietary and unpublished. | **Treat model internals as a black box**. Rely strictly on empirical calibration (AUROC, ECE) and three-zone sweeps. | Decouples engineering reliability from vendor architectural assumptions. |
| **6** | **Disclosed Safety Refusal Taxonomy** | Refusals return `type: "refusal"` without disclosing confidence, severity, or safety category codes. | **Declare mandatory per-question refusal policies** in the registry (`block`, `hold_and_review`, `human_queue`, `missing`). | Zero silent failures; safety gates fail closed. |
| **7** | **Gateway Error Wrapping Variations** | Certain gateways (e.g. OpenRouter) wrap individual refusals in HTTP 502 errors rather than returning HTTP 200 with partial answers. | **Implement regex parser for gateway 502 messages** (`recover_gateway_refusal`) and re-issue requests for surviving questions. | Ensures resilience when deploying behind multi-cloud AI proxies. |
| **8** | **Model Identifier Standardization** | Vercel uses `openai/gpt-6-luna-decisions`; direct OpenAI endpoint uses `gpt-6-luna`. | **Pass model as an injected configuration parameter**, with validation against known gateway patterns. | Prevents accidental routing to generative chat endpoints. |

---

## Autonomous Engineering Decisions

Because this task ran autonomously, the following engineering decisions were adopted without blocking for stakeholder response:
1. **Isolated Package Blueprint**: Built `scripts/pipeline_template/` as a completely decoupled package containing its own registry, input builder, parser, and policy, adhering to the strict "no cross-pipeline imports" rule.
2. **Offline-First Test Harness**: Verified all 15 test suites and 8 empirical experiments against an injected `FakeDecisionsClient`, ensuring CI/CD determinism without requiring external API tokens.
3. **Conservative Wire Spec**: Standardized image ingestion strictly on inline base64 data URLs (`data:image/jpeg;base64,...`) and user-role message arrays, honoring the latest 2026-10-21 API reference update.
