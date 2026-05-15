---
name: generate-tech-spec
description: >
  Use this skill whenever you need to generate a Technical Design Specification (tech spec)
  from an approved Non-Technical Specification. This skill is used in Plan Mode — after the
  coder has approved the non-tech spec and asks you to create the implementation plan.
  Trigger when the coder says "create the tech spec", "make the technical design", "plan
  the implementation", or "use Plan Mode". Always read the approved non-tech spec first
  before writing anything. Never write code — only produce the implementation plan.
  The coder must approve the tech spec before any code is written.
---

# Skill: Generate Technical Design Specification

This skill is used after the coder approves the Non-Technical Specification. It translates
the "what" (non-tech spec) into the "how" (technical design) — a concrete, ordered
implementation plan that Claude Code will follow when building the feature.

**Your role:** Read the non-tech spec, ask clarifying technical questions if needed, present
a plan in Plan Mode first, then write the tech spec. You produce a plan. You do NOT write
code yet.

---

## Step 1: Read the Non-Tech Spec

Before writing anything, read the approved non-tech spec at:
specs/<feature-slug>/non-tech-spec.md

Extract and internalize:
- The acceptance criteria — these become your implementation tasks
- The constraints — these become guard rails on your design choices
- The files likely affected — your starting scope
- Open questions — resolve these before designing

---

## Step 2: Ask Clarifying Technical Questions (If Needed)

Ask the coder about any technical ambiguities before designing. Common questions:
- Dependencies: "Should I add a new package for this, or build from what's already installed?"
- Data persistence: "Should this data live in memory, in the existing JSON file, or a new file?"
- Backward compatibility: "Can I change the function signature for X, or must it stay the same?"
- Config: "Should this new setting go in config.py, or is it hardcoded for now?"

Only ask questions that genuinely block the design. Do not ask questions you can answer
yourself from the non-tech spec or from reading the existing code.

---

## Step 3: Present the Plan First (Plan Mode)

Before writing the tech spec file, present a summary plan to the coder:

Here is my implementation plan for <Feature Name>:

Files to create: X, Y
Files to modify: A, B, C
New packages needed: (none / list them)
Number of tasks: N
Estimated breaking changes: (none / describe)

Task breakdown:
1. <One-line summary of task 1>
2. <One-line summary of task 2>
...

Shall I write the full tech spec?

STOP HERE. Do not write the full tech spec yet. Do not write any code.
Wait for the coder to respond. They may say "go ahead", adjust a task, change the approach,
or ask a question. Only proceed to Step 4 once they explicitly approve.

---

## Step 4: Write the Tech Spec

Once the plan is approved, generate the full tech spec using this template.
Write every section. Write "None." if a section is empty.

---

# Technical Design: <Feature Name>

## Summary
<2-3 sentences. What is being built and how, at a high level. A senior engineer who
hasn't read the non-tech spec should understand this paragraph.>

## Implementation Tasks
Tasks are ordered — complete them in sequence unless noted otherwise.

- [ ] Task 1: <Short imperative title>
      What: <What this task achieves>
      Where: <filename.py> -> <function or class name>
      How: <1-3 sentences on the approach. No pseudocode — clear English.>

- [ ] Task 2: <Short imperative title>
      What: <What this task achieves>
      Where: <filename.py> -> <function or class name>
      How: <1-3 sentences on the approach.>

## Files to Modify
| File | What Changes |
|------|-------------|
| filename.py | <Concise description of what changes and why> |

## Files to Create
| File | Purpose |
|------|---------|
| filename.py | <What this new file does and why it needs to exist> |

## New Dependencies
| Package | Version | Why Needed |
|---------|---------|------------|
| package-name | >=X.Y | <One sentence: what it provides> |

Write "None." if no new packages are needed.

## Breaking Changes
| What Breaks | Impact | Migration |
|------------|--------|-----------|
| function_name() signature change | <Who is affected> | <What callers must update> |

Write "None." if there are no breaking changes.

## Data Flow
<Only include if the feature changes how data moves through the system.>
<Describe in plain English: Input -> Step -> Step -> Output>

## Testing Strategy
| What to Test | Test Type | How to Mock |
|-------------|-----------|-------------|
| <Function or behavior> | Unit | <What to mock and how> |

Minimum coverage target: 80% on all new/modified code.

---

## Step 5: Present, Confirm, and Hand Off

After writing the spec:
1. Show the full tech spec to the coder.
2. Ask: "Does this implementation plan look right? Any tasks missing or approaches you want to change?"
3. Apply corrections, then show the updated spec.
4. State: "Tech spec is saved to specs/<feature-slug>/tech-spec.md. Ready to build when you are. Tell me to start with Task 1."

The coder must explicitly say "go ahead" or "start building" before any code is written.
Never begin implementation from within this skill.

---

## Rules for Writing Good Implementation Tasks

Each task must be:
- Atomic — one clear change per task. If a task edits two unrelated functions, split it.
- Ordered — tasks that depend on others come after them
- Imperative — title starts with a verb: Create, Add, Update, Replace, Remove
- Specific — points to the exact file and function, not just "update the backend"

### Good Task Examples
- "Create config.py with a Pydantic Settings class that reads OPENAI_API_KEY, GROQ_API_KEY,
  DB_PATH, DATA_PATH, TEMPERATURE, and MAX_TOKENS from .env with defaults."
- "Update llm_provider_manager.py -> load_llm() to read temperature from get_config()
  instead of the hardcoded literal 0.3."
- "Add tests/test_config.py with pytest cases for: missing required key raises ConfigError,
  default values are applied when optional keys are absent."

### Bad Task Examples
| Bad | Why It's Bad |
|-----|-------------|
| "Update the config stuff" | Not specific — which file? Which function? What changes? |
| "Make it work with Pydantic" | Not imperative, not scoped |
| "Fix the LLM provider and the retriever and the app" | Not atomic — three separate tasks |
| "Write tests" | Not specific — what to test? What to mock? |

---

## Task Sizing Guide

| Task Size | Lines of Code (approx) | Action |
|-----------|----------------------|--------|
| Small | < 20 lines | Fine as-is |
| Medium | 20-80 lines | Fine as-is |
| Large | > 80 lines | Split into smaller tasks |

---

## Project Architecture Reference

Never modify files outside this list without explicit coder approval.

| File | Role | Key Functions |
|------|------|--------------|
| streamlit_app.py | Web UI | main(), session state management |
| main_console.py | CLI | main(), test_providers() |
| rag_system.py | RAG core | ask_question(query, provider, save_history) |
| llm_provider_manager.py | LLM abstraction | load_llm(provider), validate_provider(provider), clear_llm_cache() |
| vector_retriever.py | FAISS retrieval | get_retriever(), process_documents_for_context(), generate_related_terms() |
| vector_store_creator.py | Index builder | create_vector_store() — run once only |
| chat_history_manager.py | History | save_chat_history(), load_chat_history(), get_history_stats() |
| config.py | Settings | get_config() — added in config-refactor feature |
| tests/conftest.py | Test fixtures | Shared fixtures for all test files |

---

## What Happens After the Tech Spec is Approved

The coder will say "start building" or "implement task 1". At that point, implement
the tasks in order, one at a time. After each task, report what was done before moving
to the next. Do not skip tasks or reorder them without asking.
