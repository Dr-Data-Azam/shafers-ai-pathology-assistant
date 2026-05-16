# CLAUDE.md

Guidance for Claude Code working in the Shafer's AI Pathology Assistant repository.

## Project Overview

RAG-based Q&A system for Shafer's Textbook of Oral Pathology (7th Edition). Answers oral
pathology questions using semantic retrieval over the textbook + LLM generation. Supports
OpenAI GPT-4o and Groq Llama 3.1 as interchangeable providers.

## Setup & Running

**Prerequisites**: Python 3.13, uv package manager, `.env` with API keys (see `.env.example`)
**Required env vars**: `OPENAI_API_KEY`, `GROQ_API_KEY`, `HUGGINGFACEHUB_ACCESS_TOKEN`

```bash
uv sync                          # install dependencies
python vector_store_creator.py   # one-time: build FAISS index (place PDF in data/ first)
streamlit run streamlit_app.py   # web UI
python main_console.py           # CLI
python main_console.py test      # test both providers
```

## Architecture

Seven modules, functional style (no classes), module-level globals for singleton caching:

```
streamlit_app.py        ← Web UI; main entry point
main_console.py         ← CLI alternative
rag_system.py           ← RAG orchestration; ask_question() is the primary API
llm_provider_manager.py ← OpenAI/Groq abstraction; _llm_openai/_llm_groq globals
vector_retriever.py     ← FAISS MMR retrieval (k=12, λ=0.7) + query expansion
vector_store_creator.py ← One-time PDF → FAISS pipeline
chat_history_manager.py ← JSON-backed history, capped at 100 interactions
```

**Data flow**: PDF → `vector_store_creator` → `vectorDB/my_FAISS_db` → `vector_retriever`
→ `rag_system` (adaptive prompt + LLM) → `chat_history_manager`

**Key paths** (git-ignored): `vectorDB/my_FAISS_db`, `vectorDB/retriever.pkl`, `data/`, `chat_history.json`

**Provider abstraction**: Only `llm_provider_manager.py` imports LangChain provider packages.
All other modules call `load_llm(provider)`. Temperature fixed at 0.3 — intentional for
factual consistency, do not change without explicit instruction.

**Retriever caching**: Delete `vectorDB/retriever.pkl` (not the index) to force re-init.
Chunk size 500/overlap 50 is tuned for dense medical text — changing it requires a full rebuild.

## Coding Conventions

- **Formatter**: Black, 88-character line length
- **Linter**: Ruff — run before every commit
- **Style**: Functional. No classes unless unavoidable. Lazy-initialized module-level globals.
- **Commits**: `type(scope): description` — e.g. `feat(config): add Pydantic settings`
- **Branches**: `feature/<slug>`, `fix/<slug>`, `chore/<slug>`
- **Types**: All new/modified functions must have type hints on parameters and return values

## Permission Boundaries

Never:
- Modify or overwrite `.env`
- Delete or overwrite `vectorDB/` (expensive to rebuild, requires the PDF)
- Push directly to `main` — always use a feature branch and PR
- Change `temperature` without explicit instruction

## Spec-Driven Development Rule

**Never implement a feature without a spec.** Every feature starts with `/create-spec`.
The spec lives in `specs/<feature-slug>/` before any code is written.

## Feature Lifecycle

```
/create-spec <name>          → pulls main, creates branch, generates non-tech spec
YOU: review + approve spec
"create the tech spec"        → Plan Mode generates tech-spec.md, YOU approve
"implement task 1"            → Claude Code builds; hooks auto-format + auto-lint
/test                         → verify all tests pass
"use the test-writer agent"   → writes tests for the new code
"use the code-reviewer agent" → reviews the diff
"use the security-reviewer"   → security check (on credential/input changes)
write implementation summary  → save specs/<slug>/implementation-summary.md
/ship-feature "type(scope): description"  → commit, push, PR, merge, back to main
```

### Implementation Summary

After all reviews pass and before `/ship-feature`, write `specs/<spec-dir>/implementation-summary.md`.
It must include:
- Tasks completed (checklist from tech spec)
- Files created and modified (with row-per-file table)
- Test results (pass count, duration, coverage per module)
- Key implementation decisions (non-obvious choices made during build)
- Deviations from the tech spec (anything that changed from the approved plan)

## Commands

| Command | What It Does |
|---------|-------------|
| `/create-spec <name>` | Start a feature: pull main, create branch, generate non-tech spec |
| `/ship-feature "message"` | End a feature: test → lint → commit → push → PR → merge → cleanup |
| `/test` | Run pytest with coverage; report failures |
| `/lint` | Check Black + Ruff; report issues without fixing |
| `/fix` | Auto-fix all Black and Ruff issues |
| `/eval [provider]` | Run RAG evaluation against golden question set; detect regressions |

Full command logic: `.claude/commands/<command>.md`

## Skills

| Skill | Read By | Purpose |
|-------|---------|---------|
| `generate-non-tech-spec.md` | `/create-spec` | Questions to ask + non-tech spec template |
| `generate-tech-spec.md` | Claude Code in Plan Mode | Tech spec template + task rules |
| `write-test.md` | `test-writer` agent | Mock patterns, fixtures, coverage targets |
| `rag-eval.md` | `/eval` | Golden questions, scoring rubric, report format |

Full skill content: `.claude/skills/<skill>.md`

## Agents

| Agent | Invoke With | What It Does |
|-------|------------|-------------|
| `test-writer` | "use the test-writer agent" | Writes pytest tests; runs them; reports coverage |
| `code-reviewer` | "use the code-reviewer agent" | Reviews diff vs tech spec; verdict: APPROVED / CHANGES REQUESTED |
| `security-reviewer` | "use the security-reviewer agent" | Checks secrets, prompt injection, deps (pip-audit) |

Full agent config: `.claude/agents/<agent>.md`

## Testing Conventions

- Tests in `tests/`; file naming: `test_<module>.py`
- Use `pytest`; never hit real APIs or FAISS — mock everything external
- Use `tmp_path` for file I/O; `monkeypatch.setenv` for API keys
- Always import modules inside test functions (after monkeypatching)
- Integration tests in `tests/integration/` — skipped in CI with `@pytest.mark.skipif`
- Full patterns and fixtures: `.claude/skills/write-test.md`
