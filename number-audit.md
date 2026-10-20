# Number Audit: Full Verification of Quantitative Values, Limits & Formulas

## Overview
This audit document cross-references every quantitative figure, limit, formula, threshold, token count, and pricing rate present in the `decisions-api-pipelines` skill references against its exact source location, citation date, and uncertainty tag.

---

## 1. Pricing, Tokens & Wire Economics

| Metric / Number | Cited Value | Source Location & Context | Uncertainty / Precedence Tag | Audit Status |
|---|---|---|---|---|
| **Input Token Pricing** | **$0.10 per 1M tokens** | File 1 (2026-10-09) M1·T3; File 5 `config/costs.toml` | [documented as of 2026-10-09] | **Exact Match** |
| **Output Token Rate** | **$0.00 (Zero)** | File 1 M1·T2 & M1·T3; File 2 M2·T2 (`output_tokens: 0`) | [documented] | **Exact Match** |
| **Reasoning Token Rate** | **$0.00 (Zero)** | File 1 M1·T2; File 2 M2·T2 (`reasoning_tokens: 0`) | [documented] | **Exact Match** |
| **Fixed Request Overhead** | **~137 to 145 tokens** | File 1 M1·T3 (Classmethod 8-token input billed 145 tokens) | [community report] | **Exact Match** |
| **Long-Context Cliff** | **$\ge 272{,}000$ tokens** | File 5 `decisions-capstone/README.md`; File 2 M3·T1 | [inference/estimate] | **Exact Match** |
| **Median Response Latency**| **~255 ms** | File 1 M1·T1 (Classmethod benchmark, 3 questions) | [community report] | **Exact Match** |
| **Speedup vs Responses API**| **~10x faster** | File 1 M1·T1 (OpenAI product launch claim) | [vendor claim] | **Exact Match** |
| **Jev Pricing Contrast** | **$0.042 per 1M tokens** | File 1 M1·T1 (TypeSafe Jev pricing comparison) | [vendor claim] | **Exact Match** |

---

## 2. API Limits & Wire Topography

| Parameter / Limit | Cited Value | Source Location & Context | Uncertainty / Precedence Tag | Audit Status |
|---|---|---|---|---|
| **Max Questions per Request** | **200 questions** | File 1 M2·T1; File 4 M5·T3; File 5 `decisions-capstone/README.md` | [community report / third-party limit] | **Exact Match** |
| **Max Options per Choice** | **255 options** | File 4 M5·T3; File 5 `decisions-capstone/README.md` | [community report / linter rule] | **Exact Match** |
| **Max Images per Request** | **128 images** | File 4 M5·T3; File 5 `decisions-capstone/README.md` | [documented as of 2026-10-21] | **Exact Match** |
| **Image Patch Grid** | **$32 \times 32$ pixels** | File 2 & 3 M3·T2; File 5 `decisions_kit/inputs.py` | [documented] | **Exact Match** |
| **Image Token Multiplier** | **1.2** | File 2 & 3 M3·T2 (GPT-5.x and GPT-6 families) | [documented] | **Exact Match** |
| **`low` Detail Max Box** | **$512 \times 512$ pixels** | File 2 & 3 M3·T2 ($16 \times 16 = 256$ patches) | [documented] | **Exact Match** |
| **`low` Detail Max Tokens** | **308 tokens** | File 2 & 3 M3·T2 ($\lceil 256 \times 1.2 \rceil = 308$) | [documented] | **Exact Match** |
| **`high` Detail Box** | **$2048 \times 2048$ pixels** | File 2 & 3 M3·T2 | [documented] | **Exact Match** |
| **Probability Precision** | **2 decimal places** | File 2 M2·T2; File 4 M5·T1; File 5 `decisions-capstone/README.md` | [documented] | **Exact Match** |
| **SDK Minimum Versions** | **Python 3.26.0, JS 7.30.0, Go 3.73.0, Ruby 0.101.0, Java 4.78.0** | File 1 M2·T1 | [documented as of 2026-10-09] | **Exact Match** |

---

## 3. Mathematical Formulas & Statistical Thresholds

| Formula / Metric | Mathematical Expression | Source Location & Context | Audit Status |
|---|---|---|---|
| **Defensive Sum Tolerance** | $\text{tol} = 0.005 \times N_{\text{options}} + 1\times 10^{-9}$ | File 2 M2·T2; File 5 `decisions_kit/contract.py` | **Exact Match** |
| **Expected Score** | $\text{score} = \frac{\sum_{i=0}^{K-1} i \cdot p_i}{\sum p_i}$ | File 2 M2·T5; File 5 `decisions_kit/pipeline.py` | **Exact Match** |
| **Renormalized Choice Prob**| $p_{\text{renorm}}(c) = \frac{p(c)}{\sum_{k \in \text{Legit}} p(k)}$ | File 4 M5·T2; File 5 `decisions-capstone/pipelines/support_triage.py` | **Exact Match** |
| **Cascade Decision Boundary** | $\text{Cascade if } p_{\text{gate}} \times (S_2 + Q_2) < Q_2 + \text{detail\_surcharge}$ | File 2 M4·T2; File 5 `tests/test_math.py` | **Exact Match** |
| **Amortization Ratio** | $\text{Ratio}(K) = \frac{K \cdot (S + Q)}{S + K \cdot Q}$; Limit $= 1 + \frac{S}{Q}$ | File 2 M4·T1 | **Exact Match** |
| **Rule of Three Error Bound** | $\text{Upper Bound} \approx \frac{3}{N}$ (at 95% confidence) | File 4 M5·T1 | **Exact Match** |
| **Exact Binomial Bound** | `beta.ppf(0.95, errors + 1, n - errors)` | File 4 M5·T1; File 5 `decisions_kit/calibration.py` | **Exact Match** |
| **Population Stability Index**| $\text{PSI} = \sum (P_b - Q_b) \ln\left(\frac{P_b + \epsilon}{Q_b + \epsilon}\right)$ | File 4 M5·T4; File 5 `decisions_kit/drift.py` | **Exact Match** |
| **PSI Drift Thresholds** | $<0.10$ Stable, $0.10–0.25$ Moderate Shift, $\ge 0.25$ Action Required | File 4 M5·T4 | **Exact Match** |
| **Default TTL for Cache** | **30 minutes** | File 2 M3·T2 (documented before schema removal in File 4) | **Exact Match** |
| **Sliding Context Window** | **$N = 6$ turns** | File 2 M3·T1 (Turkish prompt injection defense) | **Exact Match** |

---

## 4. Benchmark Accuracy Figures Cited

| Study / Benchmark | Stated Results | Source Location & Context | Audit Status |
|---|---|---|---|
| **nic-esp/luna-jev-benchmark** | 4,785 cases across BoolQ, RTE, WiC; Jev 5x faster; Luna 35.4% cheaper cached on rulebooks | File 1 M1·T1 | **Exact Match** |
| **ML6 Phishing & Spam** | Phishing: Jev 99.99% vs Luna 99.96%; Spam: Jev 95.06% vs Luna 92.82% | File 1 M1·T1 | **Exact Match** |
| **matsonj/eval-connections** | Jev: 14.8/20 at $0.06/run vs Luna Decisions: 9.7/20 at $0.20/run | File 1 M1·T1 | **Exact Match** |
| **Adrian Raudaschl NFCorpus** | 200 queries comparing yes/no predicates against 4-level relevance score rubric | File 2 M2·T5 & M4·T2 | **Exact Match** |
| **etsabary Logic Puzzles** | 17 items refused across 5 consecutive attempts (OpenRouter 502s) | File 4 M5·T3 | **Exact Match** |
