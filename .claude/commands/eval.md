---
description: Run the RAG evaluation suite against the golden question set and generate a quality report
argument-hint: "optional: provider to use e.g. openai or groq (defaults to openai)"
allowed-tools: Read, Write, Bash(python:*), Glob
---

You are evaluating the answer quality of the Shafer's AI Pathology Assistant RAG pipeline.

User input: $ARGUMENTS

## Step 1 — Read the evaluation skill

Read: `.claude/skills/rag-eval.md`

This skill contains the full golden question set (20 questions), the scoring rubric,
and the report format. Follow it for all subsequent steps.

## Step 2 — Determine provider

If $ARGUMENTS contains "groq", use provider="groq".
Otherwise default to provider="openai".

Check that the required API key is set:
- openai → OPENAI_API_KEY must be in .env
- groq → GROQ_API_KEY must be in .env

If the key is missing, STOP and say:
"The <PROVIDER>_API_KEY is not set in .env. Please add it before running evaluation."

## Step 3 — Check for previous results

Look for any file matching: `eval_results_*.json`
If one exists, load it as the "previous run" for regression comparison in Step 6.
If none exists, note that this is the first evaluation run (no regression comparison possible).

## Step 4 — Run evaluation

For each of the 20 questions in the golden question set (from the skill):

```python
from rag_system import ask_question

results = []
for question in golden_questions:
    answer, stats = ask_question(question["question"], provider=provider, save_history=False)
    results.append({
        "id": question["id"],
        "question": question["question"],
        "answer": answer,
        "expected_key_points": question["expected_key_points"],
        "stats": stats
    })
```

Show progress to the coder: "Evaluating question X of 20..."

## Step 5 — Score each answer with LLM-as-judge

For each result, send the scoring prompt defined in the rag-eval skill to the LLM.
Score faithfulness, relevance, and completeness on a 1-5 scale each.
Calculate overall as the average of the three dimensions.

## Step 6 — Detect regressions

If a previous eval_results file was found in Step 3:
- Compare overall score for each question
- Flag any question where the overall score dropped by more than 0.5
- Flag any question where any single dimension dropped below 2.0

## Step 7 — Save results

Save full results to: `eval_results_<YYYY-MM-DD>.json`

Format:
```json
{
  "date": "<YYYY-MM-DD>",
  "provider": "<provider>",
  "questions": [...results with scores...]
}
```

## Step 8 — Generate and save the report

Generate the markdown report as defined in the rag-eval skill.
Save it to: `eval_report_<YYYY-MM-DD>.md`

## Step 9 — Report summary to the user

Print this exact format:
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

Then:
- If pass rate >= 80%: "Quality target met. Safe to ship."
- If pass rate 60-79%: "Below 80% target. Review the report before shipping."
- If pass rate < 60%: "QUALITY ALERT: Pass rate is critically low. Do not ship RAG changes until resolved."
- If regressions found: List each regressed question by ID and show the score drop.
