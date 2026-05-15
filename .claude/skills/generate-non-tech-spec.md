---
name: generate-non-tech-spec
description: >
  Use this skill whenever you need to generate a Non-Technical Specification (non-tech spec)
  for a software feature — especially when the /create-spec command is invoked. This skill
  defines the exact questions to ask the coder, the template to fill in, and rules for
  writing good acceptance criteria in plain English. Always use this skill before writing
  any code or technical design. Trigger on any request to "start a feature", "create a spec",
  "define requirements", "what do we need to build", or when /create-spec is called.
  Never skip this skill when beginning feature work — the spec must come before any code.
---

# Skill: Generate Non-Technical Specification

This skill is used by the `/create-spec` command. It produces a Non-Technical Specification
(non-tech spec) — a plain-English requirements document — before any code is written.

**Your role:** Ask the coder the five questions below, take their answers, and fill in the
template. You gather requirements. You do NOT write code, suggest implementation approaches,
or create the technical spec (that comes later, from a different skill).

---

## Step 1: Ask the Coder These Five Questions

Ask them one at a time or together. Accept plain English — no code or jargon required.

**Q1 — The Problem:**
> "What problem does this feature solve? What is broken, missing, or painful right now?"

**Q2 — The Desired Behavior:**
> "What should the feature do? Walk me through it from a user's point of view — what happens
> when someone uses it? Describe it like you're explaining to a non-technical colleague."

**Q3 — What It Should NOT Do:**
> "Are there any constraints? Things the feature should avoid, not break, or not change?
> Any existing behavior that must stay exactly the same?"

**Q4 — Files Likely Affected:**
> "Which parts of the codebase do you think this will touch? Files, modules, or even just
> layers like 'the UI' or 'the database' — anything that helps scope the work."
>
> If the coder's answer is vague (e.g., "probably the UI" or "the backend somewhere"),
> use the Project Context Table at the bottom of this skill to map their description to
> specific files, then confirm: "Does that sound right — would it be streamlit_app.py
> and chat_history_manager.py?"

**Q5 — Open Questions:**
> "Is there anything unclear, undecided, or that you want to think about more before
> building starts?"

---

## Step 2: Fill In the Template

Use the coder's answers to generate the spec. Follow this exact template — every section.
Write "None." if a section genuinely has nothing to say.

---

# Feature: <Name — short, descriptive, title case>

## Problem Statement
<2-4 sentences. What is broken or missing right now? Why does it matter? Who is affected?>

## User Story
As a <type of user>, I want <what they want to do> so that <the benefit they get>.

## What It Should Do (Acceptance Criteria)
- When <trigger or condition>, <the system does this specific, observable thing>
- When <trigger or condition>, <the system does this specific, observable thing>
- The system should handle <edge case> by <specific expected behavior>

## What It Should NOT Do (Constraints)
- Must not <specific thing to avoid>
- Must not change <specific existing behavior that must stay the same>
- Must not expose <security or privacy concern>

## Files Likely Affected
- `<filename.py>` — <one sentence: why it will be touched>

## Open Questions
- <Anything unclear, undecided, or needing more discussion before building>

---

## Step 3: Present, Confirm, and Hand Off

After generating the spec:
1. Show the full spec to the coder.
2. Ask: "Does this capture what you want? Anything missing or wrong?"
3. Apply corrections the coder requests, then show the updated version.
4. State: "This content is ready to be saved as specs/<feature-slug>/non-tech-spec.md. The /create-spec command will save it."

NOTE: This skill produces the content. The /create-spec command is responsible for
creating the directory and saving the file. Do not save the file yourself from within this skill.

Do NOT proceed to the technical design spec until the coder says the non-tech spec is approved.
When they approve it, say: "Great. When you're ready, ask me to create the technical design
spec using Plan Mode."

---

## Rules for Writing Good Acceptance Criteria

Each criterion must be:
- Testable — someone can clearly verify whether it passed or failed
- Specific — no vague words like "works well", "handles things", "is accurate"
- Behavioral — describes what the system does, not how it does it internally

### Good Examples
- "When the user submits a question with no text, the system shows: Please enter a question."
- "When OPENAI_API_KEY is missing from .env, the app exits on startup with: Missing required config: OPENAI_API_KEY"
- "When the user switches providers mid-session, previous chat history is preserved."
- "When an API call fails, the system displays the error type and suggests retrying."

### Bad Examples (and why)

| Bad | Why It's Bad | Fix |
|-----|-------------|-----|
| "The app should work correctly." | Not testable | Describe each specific behavior separately |
| "Handle errors gracefully." | Vague — which error? What response? | "When the OpenAI API returns a 429 error, show: Rate limit reached. Please wait 30 seconds." |
| "The UI should be fast." | Not measurable without a number | "The answer should begin displaying within 3 seconds for a standard question." |
| "Answers should be clinically accurate." | Not testable by the system | "When context does not contain relevant info, respond: I could not find relevant information in the textbook." |

---

## Project Context Table

Use this when the coder's Q4 answer is vague. Confirm mapping with the coder before adding to spec.

| Layer | Files | What It Handles |
|-------|-------|-----------------|
| Web UI | streamlit_app.py | All user-facing interface, session state, Streamlit components |
| CLI | main_console.py | Command-line interface |
| RAG Core | rag_system.py | Orchestrates retrieval + LLM answer generation (ask_question()) |
| LLM Providers | llm_provider_manager.py | OpenAI / Groq abstraction, model loading |
| Vector Retrieval | vector_retriever.py | FAISS MMR search, query expansion, document grouping |
| Vector Store Build | vector_store_creator.py | PDF to FAISS pipeline (run once only) |
| Chat History | chat_history_manager.py | JSON-backed interaction log, stats |
| Config | config.py | Centralized settings via Pydantic (after config-refactor feature) |

---

## What Happens After the Non-Tech Spec is Approved

The coder will ask you to create the Technical Design Spec using Plan Mode.
At that point, read .claude/skills/generate-tech-spec.md. Not now.
