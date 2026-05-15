---
description: Check code formatting and linting with Black and Ruff — reports issues without fixing them
allowed-tools: Bash(black:*), Bash(ruff:*)
---

You are checking code quality for the Shafer's AI Pathology Assistant project.
Project standard: Black formatter at 88-character line length, Ruff linter.

## Step 1 — Run Black format check

Run:
```
black --check --line-length 88 .
```

Capture whether it passed or listed files that would be reformatted.

## Step 2 — Run Ruff lint check

Run:
```
ruff check .
```

Capture any lint violations found.

## Step 3 — Report results

If both pass with no issues:
```
Black:  OK — all files correctly formatted
Ruff:   OK — no lint violations
Status: CLEAN
```

If either fails:
```
Black:  <list of files that need reformatting, or OK>
Ruff:   <list of violations with file:line, or OK>
Status: ISSUES FOUND
```

Then say: "Run /fix to automatically fix all formatting and lint issues."

## Step 4 — Never auto-fix from this command

This command is read-only. It checks and reports only.
If the user wants to fix issues, they should run /fix.
