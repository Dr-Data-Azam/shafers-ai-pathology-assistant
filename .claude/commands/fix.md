---
description: Auto-fix all formatting and lint issues with Black and Ruff
allowed-tools: Bash(black:*), Bash(ruff:*)
---

You are fixing code quality issues in the Shafer's AI Pathology Assistant project.
Project standard: Black formatter at 88-character line length, Ruff linter.

## Step 1 — Run Black to reformat all files

Run:
```
black --line-length 88 .
```

Capture which files were reformatted.

## Step 2 — Run Ruff with auto-fix

Run:
```
ruff check --fix .
```

Capture which violations were fixed and which (if any) require manual attention.

## Step 3 — Verify everything is now clean

Run:
```
black --check --line-length 88 . && ruff check .
```

This confirms no remaining issues after the fixes.

## Step 4 — Report results

```
Black fixed:  <list of reformatted files, or "no changes needed">
Ruff fixed:   <count of auto-fixed violations, or "no changes needed">
Ruff manual:  <any violations that could not be auto-fixed, or "none">
Status:       <CLEAN or MANUAL FIXES NEEDED>
```

If Status is CLEAN:
- Say: "All formatting and lint issues fixed. Ready to commit."

If Status is MANUAL FIXES NEEDED:
- List each remaining violation with file, line number, and rule code
- Say: "These violations require manual fixes. Ruff cannot auto-fix them."
