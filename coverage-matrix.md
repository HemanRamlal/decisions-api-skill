# Coverage Matrix: Source Location to Skill Artifact Audit

## Overview
This audit matrix documents full traceability from the raw course sources to the delivered skill files in `decisions-api-pipelines/`.

### Source Timeline & Precedence
1. **File 1**: `artifacts/2026-10-09/semantic-tree/184318-openai-decisions-api-foundations.md` (Date: 2026-10-09) — Module 1, Module 2 Topic 1, initial syllabus.
2. **File 2**: `artifacts/2026-10-19/semantic-tree/213239-openai-decisions-api-continued.md` (Date: 2026-10-19) — Module 2 Topics 2–5, Module 3, Module 4.
3. **File 3**: `artifacts/2026-10-20/semantic-tree/192319-openai-decisions-api-modules-3-4.md` (Date: 2026-10-20) — Module 3 & 4 overlapping revision.
4. **File 4**: `artifacts/2026-10-21/semantic-tree/000936-openai-decisions-api-module-5.md` (Date: 2026-10-21) — Module 5, superseding earlier API reference claims (images, roles, caching parameters).
5. **File 5**: `files (9).zip` (M6 Production Repository & Documentation) — `decisions-capstone/`, `decompositions.md`, `pitfalls.md`.

*Chronological Precedence*: Later files override earlier statements. Where File 2 and File 3 overlap, both locations are documented below; File 4 overrides Module 3/4 on image URLs, non-user roles, and caching parameters.

---

## Detailed Traceability Matrix

| Source Location | Source Topic / Heading | Key Concepts & Rules | Destination Artifact(s) |
|---|---|---|---|
| **File 1: M1·T1** | Generative Generation vs. Bounded Evaluation | Mode 1 vs Mode 2; constrained softmax concept; 10x speedup claim; accuracy caveats (Jev vs Luna, nic-esp benchmark, ML6, matsonj); PDF workaround | `references/fit-check.md`, `references/multimodal.md` |
| **File 1: M1·T2** | Decisions API vs. Structured Outputs | Three differences: distribution, true probabilities vs generated tokens, 0 output tokens billed; extraction vs evaluation; gateway model IDs | `references/fit-check.md`, `references/api-contract.md` |
| **File 1: M1·T3** | Execution Engine & Pricing Model | $0.10/1M tokens; 0 output/reasoning tokens; definitions cost more than content (~140 token fixed overhead); Classmethod benchmark | `references/cost-latency-math.md`, `references/fit-check.md` |
| **File 1: M1·T4** | System 1 Determinism | Perception to model, policy to code; anti-pattern: policy inside prompt; strike counting in code; syllabus update adding M6 capstone | `references/fit-check.md`, `references/profiles-and-policies.md` |
| **File 1: M2·T1** | Request Topography | 3 fields: `model` (gpt-6-luna), `input` (string or user messages), `questions[]` (`type`, `name`, `instructions`, choices, levels); SDK versions | `references/api-contract.md`, `scripts/runtime/protocol.py` |
| **File 2: M2·T2** | Response Topography | Envelope shape (`id`, `usage`, `answers[]`); 4 answer variants; probability vs confidence; refusals are answers, not errors; defensive parser | `references/api-contract.md`, `references/reliability-and-errors.md`, `scripts/snippets/m2_response_parser.py` |
| **File 2: M2·T3** | The `predicate` Primitive | Output probability; 5 phrasing rules (positive polarity, single condition, observable cues, no thinking directives, separate evidence gate) | `references/primitives.md`, `references/instruction-design.md` |
| **File 2: M2·T4** | The `choice` Primitive | Categorical argmax; margin; value + description; escape options (`out_of_scope`, `no_request`); no "unsure" option; fixed production order | `references/primitives.md`, `references/instruction-design.md` |
| **File 2: M2·T5** | The `score` Primitive | Ordered levels (lowest first); expected score formula $\sum i \cdot p_i / \sum p_i$; three numbers, three jobs; bimodal distributions; queue ranking | `references/primitives.md`, `scripts/snippets/m2_response_parser.py` |
| **File 2 & 3: M3·T1** | Input State Engineering | Labeled boundary delimiters (`<<TAG>>`); policy out of input; treat input as hostile; delimiter escaping; multi-turn sliding window; chunking | `references/input-engineering.md`, `references/security.md`, `scripts/snippets/m3_multimodal_inputs.py` |
| **File 2 & 3: M3·T2** | Multimodal Evaluation | Base64 data URLs only; 32x32 patch math $\lceil w/32 \rceil \times \lceil h/32 \rceil \times 1.2$; detail levels (`low`, `high`, `original`); small text; cropping | `references/multimodal.md`, `scripts/snippets/m3_multimodal_inputs.py` |
| **File 2 & 3: M3·T3** | Instruction Design | System 1 observable criteria; Proof depth (Depth 0–1 vs 2+); criteria bleed; DRY definitions; wording sensitivity vs uncertainty; paraphrase test | `references/instruction-design.md`, `references/worked-examples.md`, `scripts/snippets/m3_multimodal_inputs.py` |
| **File 2 & 3: M4·T1** | Single-Context Parallel Evaluation | Multi-question batching; token amortization formula & ratio ceiling; interference test; question registry pattern; max 200 questions | `references/batching-and-independence.md`, `scripts/snippets/m4_batching_cascades.py` |
| **File 2 & 3: M4·T2** | The Non-Chaining Constraint | No intra-request chaining; application-code chaining; anti-pattern: pasting earlier answers; cascade vs batch formula (`cascade_or_batch`) | `references/chaining-and-cascades.md`, `scripts/snippets/m4_batching_cascades.py` |
| **File 2 & 3: M4·T3** | Composite Profiling | Orthogonal signals in one request; Support Triage profile; missing/refused field dependencies; policy-as-code evaluation | `references/profiles-and-policies.md`, `references/worked-examples.md` |
| **File 4: M5·T1** | Confidence Thresholding | Ranking (AUROC) vs calibration (ECE); signal selection; cost-optimal cutoffs; `sweep_three_zone`; base rate precision trap; binomial certification | `references/calibration-and-thresholds.md`, `scripts/snippets/m5_thresholds_drift.py` |
| **File 4: M5·T2** | Fallback and "Other" Design | Fallback options vs fallback paths; escape options (`out_of_scope` vs `no_request`); renormalization over active teams; escalation models | `references/calibration-and-thresholds.md`, `references/primitives.md` |
| **File 4: M5·T3** | Error & Refusal Handling | API reference corrections (data URLs, user role only, caching removed); refusal facts & 3 rules; gateway 502 recovery; whole-request retries; Breaker | `references/reliability-and-errors.md`, `scripts/runtime/resilience.py`, `scripts/runtime/refusal.py` |
| **File 4: M5·T4** | Evaluation & Drift Tracking | 4 evaluation splits; gate rules (`gate`); paired bootstrap test; probe replay sets; PSI calculation; weekly human audits; 5-step drift runbook | `references/monitoring-and-drift.md`, `scripts/snippets/m5_thresholds_drift.py` |
| **File 5: M6** | `decompositions.md` | 5 complete domain pipelines: Support Triage, Review Screening, Return Claims, Contract Review, Insurance Claims; fuzzy $\to$ observable rewrites | `references/worked-examples.md`, `scripts/pipeline_template/` |
| **File 5: M6** | `pitfalls.md` | 144 deduplicated pitfalls across 15 categories (decomposition, choice, score, parser, input, vision, batching, profiles, thresholds, fallbacks, etc.) | `references/pitfalls.md` |
| **File 5: M6** | `decisions-capstone/` | Reference Python implementation (`decisions_kit/`, `pipelines/`, `tests/`, `config/`) | `scripts/pipeline_template/`, `scripts/runtime/`, `scripts/snippets/`, `scripts/tests/` |

---

## Verification of Overlapping & Superseded Material
- **Image URLs & Caching**: In File 2 (2026-10-19) M3·T2, caching parameters (`prompt_cache_key`, `prompt_cache_breakpoint`) were introduced. In File 4 (2026-10-21) M5·T3, the API reference removed them from the request schema. The delivered skill marks caching as volatile/unsupported in `references/api-contract.md` and isolates it to `scripts/experiments/caching_experiment.py`.
- **Accepted Roles**: File 3 explored multi-turn chat message formatting; File 4 M5·T3 reiterated that the live API accepts only `role: "user"`. The delivered skill standardizes on user-role serialized strings in `references/input-engineering.md` and `scripts/snippets/m3_multimodal_inputs.py`.
- **Refusal Coercion**: Early learner replies suggested setting refused predicates to `False` or 0. Tutor corrections in File 2 M2·T2, File 4 M5·T3, and M6 strictly prohibited this. The delivered skill enforces typed `RefusalAnswer` handling across all templates.
