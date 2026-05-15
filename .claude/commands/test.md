---
description: Run the full pytest test suite with coverage and report results
allowed-tools: Bash(python:*), Bash(pytest:*)
---

You are running the test suite for the Shafer's AI Pathology Assistant project.

## Step 1 — Run the test suite

Run:
```
python -m pytest tests/ -v --tb=short --ignore=tests/integration/ --cov=. --cov-report=term-missing
```

## Step 2 — Report results

After the run completes, report in this format:

```
Tests run:   <total>
Passed:      <passed>
Failed:      <failed>
Errors:      <errors>
Coverage:    <percentage>%
```

## Step 3 — Handle failures

If any tests failed:
- List each failing test by name
- Show the short traceback for each
- Say: "X test(s) failing. Fix these before running /ship-feature."

If all tests passed:
- Say: "All tests passing. Coverage: <X>%"
- If coverage is below 75%, say: "Coverage is below the 75% target. Consider adding tests for the uncovered lines shown above."

## Step 4 — Handle missing test dependencies

If pytest is not found, run:
```
uv add --dev pytest pytest-cov pytest-mock
```
Then re-run Step 1.
