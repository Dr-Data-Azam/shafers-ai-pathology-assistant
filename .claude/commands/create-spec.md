---
description: Start a new feature — pull latest main, create a feature branch, and generate a non-technical spec by interviewing the coder
argument-hint: "feature name in kebab-case e.g. config-refactor or llm-response-cache"
allowed-tools: Read, Write, Glob, Bash(git:*)
---

You are a senior developer on the Shafer's AI Pathology Assistant project.
Always follow the rules and conventions defined in CLAUDE.md.

User input: $ARGUMENTS

## Step 1 — Check working directory is clean

Run `git status` and inspect the output.
If there are any uncommitted, unstaged, or untracked files, STOP immediately and say:

"Your working directory has uncommitted changes. Please commit or stash them before
starting a new feature. Run `git status` to see what needs to be addressed."

DO NOT CONTINUE until the working directory is clean.

## Step 2 — Parse the arguments

From $ARGUMENTS extract:

1. `feature_slug` — git and file-safe slug
   - Lowercase, kebab-case only
   - Characters: a-z, 0-9, and hyphens only
   - Maximum 40 characters
   - Examples: config-refactor, llm-response-cache, answer-feedback

2. `feature_title` — human-readable title in Title Case
   - Derive from the slug: "config-refactor" → "Config Refactor"
   - Examples: "Config Refactor", "LLM Response Cache", "Answer Feedback"

3. `branch_name` — format: `feature/<feature_slug>`
   - Examples: feature/config-refactor, feature/answer-feedback

If $ARGUMENTS is empty or cannot be parsed into a slug, ask the user:
"What is the feature name? Please provide it in kebab-case, e.g. config-refactor"
Wait for their answer before continuing.

## Step 3 — Check the branch name is not already taken

Run `git branch -a` to list all local and remote branches.
If `branch_name` already exists, append a counter:
  feature/config-refactor-01, feature/config-refactor-02, etc.
Tell the user if a suffix was added.

## Step 4 — Switch to main and pull latest

Run:
```
git checkout main
git pull origin main
```

If either command fails, STOP and report the error to the user.
Do not proceed with a stale main branch.

## Step 5 — Create and switch to the feature branch

Run:
```
git checkout -b <branch_name>
```

Confirm the branch was created by running `git branch --show-current`
and verifying it matches `branch_name`.

## Step 6 — Determine the spec number and create the spec directory

List all existing numbered spec directories to find the next available number.
Run `ls specs/` via Bash and filter for entries matching the pattern `NN-*` (two-digit
prefix). Extract the two-digit prefix from each name, find the highest number in use,
and set the next spec number to that value + 1, zero-padded to two digits
(01, 02, ... 09, 10, 11, ...).
If no numbered directories exist yet, start at 01.

IMPORTANT: Always use Bash(`ls specs/`) — never use Glob — to detect existing spec
directories. Glob does not reliably match directories on all platforms.

Set `spec_dir_slug` = `NN-<feature_slug>`
Example: feature_slug="llm-response-cache", next number=02 → spec_dir_slug="02-llm-response-cache"

Create the directory: `specs/<spec_dir_slug>/`

This is where both the non-tech spec and tech spec will live. From this point on,
all references to the spec directory use `specs/<spec_dir_slug>/` (the numbered form),
not `specs/<feature_slug>/`.

## Step 7 — Read the skill and interview the coder

Read the skill file at: `.claude/skills/generate-non-tech-spec.md`
Follow it exactly. It defines the five questions to ask and the template to fill in.

Ask the coder all five questions. Wait for their answers.
Do not generate the spec until you have answers to at least Q1, Q2, and Q3.
Q4 and Q5 can be inferred if the coder says "not sure" or "none".

## Step 8 — Generate and save the non-tech spec

Using the coder's answers and the template from the skill, generate the spec.
Save it to: `specs/<spec_dir_slug>/non-tech-spec.md`

Do NOT print the full spec in chat. Instead say:
"Spec saved. Here is a summary:" and show only the Problem Statement and Acceptance Criteria.

## Step 9 — Report to the user

Print this exact format:
```
Branch:    <branch_name>
Spec file: specs/<spec_dir_slug>/non-tech-spec.md
Feature:   <feature_title>
```

Then say:
"Review the spec at specs/<spec_dir_slug>/non-tech-spec.md and let me know if anything
needs changing. Once you approve it, say: 'Create the tech spec' and I will switch to
Plan Mode to design the implementation."
