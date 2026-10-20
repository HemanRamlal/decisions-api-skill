# Task: build the skill `decisions-api-pipelines`

## Goal
Build a Claude skill (SKILL.md + references/ + scripts/) that lets a future Claude instance take a stakeholder's problem and deliver production-ready Decisions API pipelines in Python, with no developer in between. The attached sources (below) are your only sources. The finished skill must make them unnecessary: someone holding only the skill folder must be able to do everything the sources teach.

## Sources (attached)
Course transcripts and a sample project. Read in this order, in full. Dates come from the file paths and are the "as of" date for volatile facts.

| # | File | Date | Covers (heading scan only, unverified) |
|---|------|------|------|
| 1 | 184318-openai-decisions-api-foundations.md | 2026-10-09 | M1, M2 T1, course roadmap |
| 2 | 213239-openai-decisions-api-continued.md | 2026-10-19 | M2 T2–5, M3, M4 |
| 3 | 192319-openai-decisions-api-modules-3-4.md | 2026-10-20 | M3, M4 |
| 4 | 000936-openai-decisions-api-module-5.md | 2026-10-21 | M5 |
| 5 | files (9).zip | from file metadata | M6 |

Orientation map (headings only; the files win on any conflict):
- M1 Bounded decision paradigm: generation vs bounded evaluation, Decisions API vs structured outputs, engine and pricing, System 1 vs code.
- M2 Wire spec and primitives: request, response, predicate, choice, score.
- M3 Inputs: input state engineering (incl. adversarial defense), multimodal, instruction design.
- M4 Batching and independence: multi-question requests, non-chaining constraint, composite profiles.
- M5 Operations: calibration and thresholds, fallback/"Other" design, error and refusal handling, evaluation and drift.
- M6 Production example repository and pitfall catalog: cascades, question decomposition, anti-patterns (per the roadmap in file 1).

Source-handling rules:
- Files 2 and 3 overlap (M3, M4). Treat all files as one chronological timeline: later wins, differences between overlapping passages count as corrections, and the coverage matrix records both locations.
- The syllabus changed during the course (file 1 has a syllabus update). Inventory by content, not by module label.
- M6 has its own pitfall catalog. Merge it into yours; don't copy it.

## What the skill is
- **Runtime audience:** a stakeholder who is a domain expert, mathematically minded, technically strong, and available on demand. Nobody sits between them and the skill, so the skill talks to them directly. Probabilities, thresholds and expected-cost math are fine; don't dumb anything down.
- **Capability:** Python only. It builds well-tested, isolated pipelines: question sets, input builders, instructions/prompts, question chains, policy code. These must be reliable in production. If the stakeholder's stack isn't Python, deliver a Python service with a clean boundary, or a spec. Never write another language.

## Runtime behaviour to encode in SKILL.md (short, imperative)
1. **Fit check first.** The Decisions API makes glance-level judgments over evidence. Arithmetic, policy, chaining, extraction and deep reasoning belong to code or other tools. Say so when any part of the task is a poor fit, and propose the split.
2. **Intake.** Before designing, establish and restate:
   - inputs: shape, size, modality, how trusted, sensitive data
   - outputs: who or what consumes the decision, and what actions follow
   - constraints: latency (p50/p99), cost per item × volume, rate limits, data handling
   - the cost of each kind of error
   - what labeled examples exist
3. **Ask eagerly, in batches.** Ask whenever the answer would change a definition, threshold, cost, risk or anything irreversible. Decide alone only on mechanical, cheaply reversible matters. Each question gives your recommended default so a one-word reply works.
4. **Self-contained messages.** Every question and report quotes the exact question text, input sample, threshold or number it concerns. Never write "as above" or "the earlier one".
5. **State assumptions aloud at every stage,** numbered, each marked *assumed*, *confirmed by stakeholder*, or *verified by test*.
6. **Plan before, report after,** at each checkpoint: framing + intake, design, first draft, test selection, test results, handoff. Skip one only if trivial, and say so.
   - Plan: what, why, alternatives considered, assumptions, open questions, expected cost/time.
   - Report (one page): outcome first, then evidence (numbers), changes from plan, autonomous decisions (what, why, how to reverse), deferred decisions (what resolves each, safe default meanwhile), next step.
7. **Draft first, then test by ROI.** After the first draft, list candidate tests and score each as (chance this defect class exists) × (cost if it ships) ÷ (cost to run: money, time, stakeholder effort). Show the scored table, let the stakeholder veto or reweight it, run the top test(s), and report. State the cost before any paid live test.
8. **Frame trade-offs as expected cost** using the stakeholder's own error costs, e.g. when choosing thresholds, batching vs cascading, or detail levels.

## Engineering standards the skill must produce
- Each pipeline is an isolated package: versioned question registry, input builder, response parser, policy code, config, tests. No cross-pipeline imports. The API client is injected, never a global.
- Judgment comes from the API; everything else (policy, thresholds, arithmetic, chaining, extraction, routing) is code.
- Reliability: timeouts and a deadline passed down a chain, retries only of whole requests, defined handling for refusals and missing fields, fallbacks, idempotent side effects, and a decision record per decision (answers, question versions, evidence hash, schema version).
- Tests run offline by default against a fake client. Live tests are opt-in, cost-capped and marked.
- Typed code, pinned dependencies, pytest.

## How to read the sources
They are tutoring transcripts: lessons, a learner's replies, and tutor corrections. So:
- Later corrections override earlier statements. Examples: image input formats, accepted message roles, question limits and caching were all corrected mid-transcript.
- A learner's reply is not a fact unless the tutor's response confirms it.
- Tag every claim in the references: [documented] [vendor claim] [community report] [inference/estimate] [untested]. Keep the tutor's own uncertainty labels. Volatile facts (prices, limits, model-specific behaviour, caching) also get "as of <source date>" and a script that verifies them.
- Never invent API details. If something is used but not defined (a response parser, response shape, calibration, fallback strategy, a referenced repo), list it in `references/knowledge-gaps.md` and ask me.

## Distillation rules
- Read everything first. Inventory every rule, number, limit, formula, snippet, pitfall, worked example, and open experiment. Keep a coverage matrix (source location → destination file) as a separate audit file, not inside the skill.
- Keep each rule together with its reason and its counter-example. Keep numbers and formulas exactly.
- Merge the pitfall lists scattered across topics into one catalog: pitfall, why it bites, how to detect it, fix.
- Keep every "fuzzy question → observable questions + code" rewrite as a worked example.
- Port every code snippet into tested Python under scripts/ (fix errors, keep names, add unit tests). Turn each open experiment into a runnable script.
- SKILL.md under ~400 lines: workflow, behaviour rules, and an index saying when to read which reference. References one level deep, one topic per file, each starting with a contents list. Frontmatter: name, plus a third-person description of what the skill does and when to trigger it.
- If a skill-authoring guide exists in your environment, read it first and follow it.

## Draft file tree (reference only)
This tree is a rough draft built from a heading scan, not from the sources. It is not a specification. Use it only as a starting point and change it freely at any time during skill generation, including after the plan is approved: add, merge, split, rename or drop files and folders wherever the sources or the work justify it. The module/topic labels beside each file are unverified guesses. The rules above (SKILL.md length, references one level deep, one topic per file, contents list at the top of each file, full coverage of the inventory) still apply to whatever tree you end up with. List every deviation from this draft in your plan and in your final report, under autonomous decisions.

```
decisions-api-pipelines/
├── SKILL.md
├── references/
│   ├── fit-check.md                  M1: bounded evaluation vs generation; Decisions API vs structured outputs; what goes to code
│   ├── api-contract.md               M2 T1–2: request/response wire spec, usage, limits, errors  [volatile]
│   ├── primitives.md                 M2 T3–5: predicate / choice / score; probability and expected-value math
│   ├── input-engineering.md          M3 T1: serialization, evidence boundaries, formats, multi-item payloads
│   ├── multimodal.md                 M3 T2: images, mixed inputs, document/PDF workarounds
│   ├── instruction-design.md         M3 T3: rubrics, System 1 framing, criteria bleed; M5 T2 "Other" design
│   ├── batching-and-independence.md  M4 T1–2: shared-input questions, amortization, non-chaining
│   ├── chaining-and-cascades.md      M4 T2, M6: app-code chains, cascades, decomposition
│   ├── profiles-and-policies.md      M4 T3, M1 T4: composite profiles; policy as code
│   ├── calibration-and-thresholds.md M5 T1–2: AUROC vs ECE, routing thresholds, review bands
│   ├── reliability-and-errors.md     M5 T3: refusals, transport/schema failures, fallbacks, retries, deadlines, idempotency
│   ├── monitoring-and-drift.md       M5 T4: dev sets, confusion matrices, drift, shadow mode, decision records
│   ├── security.md                   M3 T1: delimiter escaping, injection isolation, sensitive data
│   ├── cost-latency-math.md          M1 T3, M4 T1: pricing, amortization, expected-cost framing  [volatile]
│   ├── testing-playbook.md           ROI test catalog, fake client, live-test rules
│   ├── pitfalls.md                   merged catalog, all modules incl. M6
│   ├── worked-examples.md            every fuzzy→observable rewrite, profiles, cascades
│   ├── open-experiments.md           each experiment → scripts/experiments/
│   ├── communication-templates.md    intake checklist, question format, assumption ledger, plan/report/ROI-table templates
│   └── knowledge-gaps.md
├── scripts/
│   ├── pipeline_template/            isolated-package scaffold, copied into each pipeline, never imported across pipelines
│   ├── runtime/                      client protocol, fake client, retry + deadline, decision record, refusal/missing-field handling (vendored the same way)
│   ├── snippets/                     every course snippet, ported, names kept
│   ├── experiments/                  one runnable script per open experiment
│   ├── verify_volatile_facts.py      live, opt-in; re-checks prices, limits, caching, model behaviour
│   └── tests/                        pytest; offline by default, live tests marked and cost-capped
└── pyproject.toml / lock             pinned dependencies

Outside the skill (audit, not shipped): coverage-matrix.md, number-audit.md, closed-book-exam.md, unresolved-gaps.md
```

## Verification before you say done
1. **Closed-book exam.** Give a fresh reader (a subagent if you can spawn one) only the skill folder. Ask it every "check your understanding" question in the sources plus three realistic stakeholder scenarios. Grade against the tutor's corrected answers and fix every gap.
2. Run the unit tests.
3. Audit every number in the references against its source.
4. Deliver the coverage matrix and the list of unresolved gaps.

## How you work on this task
Start with a plan: a source manifest (including the zip's contents, with anything expected but absent or unreadable flagged), the inventory, your proposed file tree (starting from the draft above and marking each deviation), and all your questions in one batch with defaults. Then wait for my answers. If I'm unavailable, proceed on your defaults and list them. Finish with a report in the format above.

yo, autonomously create whole skill in ~/skill-bro. dont explore any other artifact, dont explore any semantic-trees under current workspace. only refeer to mentioned files in the chat
