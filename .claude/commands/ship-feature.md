---
description: Ship the current feature — run tests, lint, commit, push, open a PR, merge, return to main, and delete the feature branch
argument-hint: "conventional commit message e.g. feat(config): add Pydantic-based centralized configuration"
allowed-tools: Read, Bash(git:*), Bash(pytest:*), Bash(black:*), Bash(ruff:*), Bash(python:*)
---

You are a senior developer on the Shafer's AI Pathology Assistant project.
This command closes the feature lifecycle. It only runs if tests pass and lint is clean.
Always follow the rules and conventions defined in CLAUDE.md.

User input: $ARGUMENTS

## Step 1 — Confirm you are on a feature branch

Run `git branch --show-current` and capture the branch name.

If the current branch is `main`, STOP immediately and say:
"You are on main. This command must be run from a feature branch.
Switch to your feature branch first: git checkout feature/<name>"

Save the branch name — you will need it in later steps.

## Step 2 — Parse the commit message

From $ARGUMENTS extract the commit message.

It must follow conventional commit format:
  type(scope): description

Valid types: feat, fix, test, ci, chore, docs, refactor, perf
Examples:
  feat(config): add Pydantic-based centralized configuration
  fix(retriever): correct page number offset calculation
  test(chat-history): add 100-item cap edge case

If $ARGUMENTS is empty or does not match this format, ask:
"Please provide a commit message in conventional commit format.
Example: feat(config): add Pydantic-based centralized configuration"
Wait for their answer before continuing.

## Step 3 — Run the full test suite

Run:
```
python -m pytest tests/ -v --tb=short --ignore=tests/integration/
```

If ANY test fails:
- Show the failing test names and error messages
- STOP. Do not proceed.
- Say: "Tests are failing. Fix the failures above before shipping.
  Run /test to re-check after fixing."

Only continue if all tests pass.

## Step 4 — Run lint checks

Run:
```
black --check . && ruff check .
```

If lint fails:
- Report which files have issues
- Ask: "Lint check failed. Run /fix to auto-fix formatting, then retry /ship-feature."
- STOP. Do not proceed.

Only continue if both black and ruff report no issues.

## Step 5 — Stage all changes

Run:
```
git add .
```

Then run `git diff --cached --stat` and show the coder a summary of what is being committed.
Wait 3 seconds (or for the user to say "ok") before continuing.
This is the last chance to catch accidental files.

## Step 6 — Commit

Run:
```
git commit -m "<commit_message_from_arguments>"
```

If the commit fails (e.g. nothing staged, pre-commit hook failure), report the error and STOP.

## Step 7 — Push to remote

Run:
```
git push origin <branch_name>
```

If the push fails, report the error and STOP.
Do not force push under any circumstances.

## Step 8 — Create a Pull Request

Use the GitHub MCP to create a Pull Request with:
- Title: the commit message from $ARGUMENTS
- Base branch: main
- Head branch: <branch_name>
- Body: Use this template exactly:

```
## Summary
<one paragraph describing the feature — derive from the commit message>

## Spec
See: specs/<feature_slug>/non-tech-spec.md
See: specs/<feature_slug>/tech-spec.md

## Changes
<paste the output of: git diff --stat main...<branch_name>>

## Testing
- [ ] All unit tests pass
- [ ] Lint clean (Black + Ruff)
- [ ] Manually verified the app still works
```

Capture the PR URL from the response.

## Step 9 — Merge the Pull Request

Use the GitHub MCP to merge the PR created in Step 8.
Use squash merge if possible. If not available, use regular merge.

If the merge fails due to conflicts, STOP and say:
"There are merge conflicts. Resolve them manually:
  git checkout <branch_name>
  git merge main
  # resolve conflicts
  git push origin <branch_name>
Then run /ship-feature again."

## Step 10 — Return to main and pull

Run:
```
git checkout main
git pull origin main
```

Verify you are now on main with the latest changes.

## Step 11 — Delete the feature branch

Run:
```
git branch -d <branch_name>
```

If the local delete fails, it is not fatal — continue.
Do NOT delete the remote branch — GitHub handles that after merge.

## Step 12 — Report to the user

Print this exact format:
```
Shipped:   <commit_message>
PR:        <PR URL>
Branch:    <branch_name> (deleted)
Now on:    main
```

Then say:
"Feature shipped successfully. You are back on main with the latest changes.
To start the next feature, run /create-spec <feature-name>"
