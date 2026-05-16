---
description: Run the RAG evaluation suite against the golden question set and generate a quality report
argument-hint: "optional: provider to use e.g. openai or groq (defaults to openai)"
allowed-tools: Read, Bash(python:*)
---

You are evaluating the answer quality of the Shafer's AI Pathology Assistant RAG pipeline.

User input: $ARGUMENTS

## Step 1 — Read the evaluation skill

Read: `.claude/skills/rag-eval.md`

This skill contains the full golden question set, the scoring rubric, and the report
format. Use it as reference when interpreting the results in Step 4.

## Step 2 — Determine provider

If $ARGUMENTS contains "groq", use provider="groq".
Otherwise default to provider="openai".

## Step 3 — Check API keys

The judge always uses OpenAI GPT-4o regardless of the generation provider.
Both keys may be required depending on the provider chosen.

Check that these keys are set in .env:
- `OPENAI_API_KEY` — **always required** (used by the judge LLM)
- `GROQ_API_KEY` — required only when provider="groq"

If `OPENAI_API_KEY` is missing, STOP and say:
"OPENAI_API_KEY is not set in .env. It is required for the evaluation judge even when
using Groq for generation. Please add it before running evaluation."

If provider="groq" and `GROQ_API_KEY` is missing, STOP and say:
"GROQ_API_KEY is not set in .env. Please add it before running evaluation with Groq."

## Step 4 — Run the evaluation

Run the evaluation pipeline via the CLI:

```
python eval_runner.py --provider <provider>
```

The script handles everything: loading the golden question set, running each question
through the RAG pipeline, scoring answers with the OpenAI judge, detecting regressions
against any previous `eval_results_*.json`, and saving the dated JSON results and
markdown report to the project root.

Progress is logged to `app.log`. The script prints the summary to stdout when complete.

## Step 5 — Report summary to the user

Read the stdout output from Step 4 and relay it to the user in this exact format:

```
Evaluation complete
Provider:         <provider>
Questions scored: 20
Avg Faithfulness: X.X / 5.0
Avg Relevance:    X.X / 5.0
Avg Completeness: X.X / 5.0
Overall avg:      X.X / 5.0
Pass rate (≥3.5): XX%
Regressions:      <count, or "none">
Report saved:     eval_report_<YYYY-MM-DD>.md
```

Then add a verdict line based on the pass rate:
- pass rate >= 80%: "Quality target met. Safe to ship."
- pass rate 60–79%: "Below 80% target. Review the report before shipping."
- pass rate < 60%: "QUALITY ALERT: Pass rate is critically low. Do not ship RAG changes until resolved."

If regressions > 0, also say:
"Regressions detected. Review eval_report_<YYYY-MM-DD>.md for per-question details
before shipping any RAG-related changes."
