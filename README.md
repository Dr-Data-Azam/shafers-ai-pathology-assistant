# Shafer's AI Pathology Assistant

A retrieval-augmented generation system for querying Shafer's Textbook of Oral Pathology
(7th Edition). Questions are answered by retrieving grounded context from the indexed
textbook and generating responses via OpenAI GPT-4o or Groq Llama 3.1 70B — every
answer traceable to specific textbook pages.

This repository also documents the full development lifecycle that produced it: six
features built end-to-end using a spec-driven agentic workflow, with non-technical specs,
technical designs, automated quality gates, and agent-mediated code review at each step.
The git history and `specs/` directory preserve the full record.

---

## Architecture

### Modules

```
streamlit_app.py        — Web UI; entry point
main_console.py         — CLI alternative
rag_system.py           — RAG orchestration; ask_question() is the primary API
llm_provider_manager.py — OpenAI/Groq provider abstraction; cached LLM instances
vector_retriever.py     — FAISS MMR retrieval (k=12, λ=0.7) + query expansion
vector_store_creator.py — One-time PDF → FAISS index pipeline
chat_history_manager.py — JSON-backed history, capped at 100 interactions
exceptions.py           — Typed exception hierarchy (PathologyAppError)
eval_runner.py          — Standalone RAG evaluation; LLM-as-judge; regression detection
```

### Data Flow

```
PDF → vector_store_creator → vectorDB/my_FAISS_db
                                      ↓
question → vector_retriever (FAISS MMR + query expansion)
                                      ↓
                           rag_system (adaptive prompt + LLM)
                                      ↓
                           chat_history_manager → chat_history.json
```

### Key Design Decisions

- **Functional style, no classes.** Module-level globals (`_retriever`, `_llm_openai`, `_llm_groq`) for singleton caching — keeps the call graph flat and mock injection in tests straightforward.
- **Provider abstraction at a single boundary.** Only `llm_provider_manager.py` imports LangChain provider packages; all callers use `load_llm(provider)`. Swapping a provider is a one-file change.
- **MMR retrieval (k=12, λ=0.7) with query expansion.** Max Marginal Relevance reduces redundant chunk retrieval. `generate_related_terms()` catches medical terminology variants before FAISS search.
- **Chunk size 500, overlap 50, tuned for dense medical text.** Changing these values requires a full FAISS index rebuild.
- **Temperature fixed at 0.3.** Intentional for factual consistency — not a runtime parameter.
- **Pydantic Settings for all config.** Startup fails fast with a named validation error if a required key is missing, before any LLM or retrieval call.

---

## Development Workflow

Features in this project follow a structured lifecycle enforced by Claude Code: every change starts with a non-technical spec, progresses through a technical design, and is implemented, tested, reviewed, and shipped through an automated pipeline. The six features that produced this system each went through this process. The `specs/` directory and git history contain the full record.

### Feature Lifecycle

1. **`/create-spec <name>`** — Claude Code interviews the developer, pulls main, creates a feature branch, and writes `specs/<NN-slug>/non-tech-spec.md`. Developer reviews and approves.
2. **`"Create the tech spec"`** — In Plan Mode, Claude Code generates `tech-spec.md` with ordered implementation tasks, file changes, and testing strategy. Developer approves before any code is written.
3. **Implementation** — Claude Code builds each task. Auto-format (Black) and auto-lint (Ruff) hooks run on every file write.
4. **`"Use the test-writer agent"`** — Specialist sub-agent reads the diff and project test conventions, writes pytest tests for all new code, runs them, and reports coverage to `test-report.md`.
5. **`"Use the code-reviewer agent"`** — Reviews the diff against the approved tech spec. Produces a structured verdict (APPROVED / APPROVED WITH COMMENTS / CHANGES REQUESTED) saved to `code-review.md`.
6. **`"Use the security-reviewer agent"`** — Checks for secrets, prompt injection vectors, input sanitization gaps, and runs `pip-audit`. Findings saved to `security-review.md`.
7. **`/eval`** — Runs 20 golden questions through the pipeline. LLM-as-judge scores faithfulness, relevance, and completeness. Detects regressions vs. the previous dated baseline. Required before shipping any RAG change.
8. **`/ship-feature "type(scope): description"`** — Tests → lint → commit → push → creates PR → merges → returns to main → deletes feature branch.

### Shipped Features

| # | Feature | What It Added |
|---|---------|---------------|
| 01 | Config Refactor | Pydantic Settings; all hardcoded values centralized in `config.py` |
| 02 | Testing Framework | 191 tests, 77% coverage, pytest infrastructure, conftest fixtures |
| 03 | Error Handling | Typed exception hierarchy, structured rotating logs (`app.log`) |
| 04 | Docker | Multi-stage build, non-root user, named volume, healthcheck |
| 05 | CI/CD | 3 parallel PR checks (lint, test, security) + Docker build on merge to main |
| 06 | RAG Evaluation | LLM-as-judge eval framework, 20 golden questions, regression detection |

Each feature's `specs/<NN-slug>/` directory contains the full paper trail: `non-tech-spec.md`, `tech-spec.md`, `code-review.md`, `security-review.md`, `test-report.md`, and `implementation-summary.md`.

---

## Quality Gates

### CI/CD Pipeline

| Job | Tool | Gate |
|-----|------|------|
| Lint | Black + Ruff | Format and style clean — required to merge |
| Test | pytest + coverage | Full suite, 75% coverage minimum — required to merge |
| Security | pip-audit | No unpatched CVEs in runtime deps — required to merge |
| Docker Build | docker/build-push-action | Image builds cleanly — runs on merge to main |

All three PR jobs are required status checks. Nothing merges to main without passing all three.

### Test Suite

- 191 tests across 11 test files; ~5 second run time
- All external dependencies mocked — no real API calls, no real FAISS in unit tests
- `tmp_path` for all file I/O; `monkeypatch.setenv` for API keys
- Coverage: 77% total, 92% on `eval_runner.py`
- 75% threshold enforced in `pyproject.toml` — CI fails below it

---

## RAG Evaluation

### What It Measures

| Dimension | What the judge asks |
|-----------|---------------------|
| Faithfulness | Does every claim trace back to the retrieved source chunks? |
| Relevance | Does the answer address the question that was asked? |
| Completeness | Does the answer cover the expected clinical key points? |

Each dimension is scored 1–5. The judge is always OpenAI GPT-4o at temperature=0, regardless of which provider generated the answer.

### Golden Question Set

20 questions across 5 categories — Definition (5), Classification (4), Clinical Features (5), Comparison (3), Edge Cases (3). Each question carries `expected_key_points`: specific clinical terms the judge uses to assess completeness. Stored in `evals/golden_questions.json`.

### Evaluator Design

- **Judge fixed to GPT-4o at temperature=0.** Using the same model as generator and judge creates self-evaluation bias; a fixed judge ensures scores are comparable across runs and providers.
- **Sentinel-based prompt template** (`__QUESTION__`, `__CONTEXT__`, `__KEY_POINTS__`) using `str.replace()` — not `str.format()`. Medical text and LLM outputs routinely contain literal `{...}` characters; `str.format()` would raise `KeyError` on real retrieval output.
- **Regression detection.** `detect_regressions()` compares each question's scores against the previous dated `eval_results_*.json`. Flags any question where the overall score drops more than 0.5, or where any single dimension falls below 2.0.
- **Committed baselines.** Dated results files (`eval_results_<date>.json`, `eval_report_<date>.md`) are tracked in git, not gitignored — regression baselines survive fresh clones and quality trajectory is visible in the commit history.

### Current Baseline (2026-05-16)

```
Questions evaluated:  20
Average Faithfulness: 3.35 / 5.0
Average Relevance:    4.30 / 5.0
Average Completeness: 3.70 / 5.0
Overall Average:      3.78 / 5.0
Pass rate (≥ 3.5):    60.0%
Critical failures:    0

Verdict: ACCEPTABLE — Below 80% target. Review report before shipping.
```

The 80% pass rate is the ship gate; this run sits below it. Failures concentrate in classification completeness and clinical feature enumeration — the retriever returns relevant chunks but not always exhaustive lists. The eval framework tracks this over time; `eval_report_2026-05-16.md` contains the full question-level breakdown.

### Running an Evaluation

```bash
python eval_runner.py                    # default provider (openai)
python eval_runner.py --provider groq    # Llama 3.1 for generation; GPT-4o judge always
```

---

## Quick Start

**Prerequisites:** Python 3.13, `uv` package manager, Shafer's Textbook of Oral Pathology (7th Ed.) PDF, and at least one of `OPENAI_API_KEY` or `GROQ_API_KEY` plus `HUGGINGFACEHUB_ACCESS_TOKEN`.

```bash
cp .env.example .env          # fill in API keys

uv sync

# place the textbook PDF in data/
python vector_store_creator.py        # one-time: builds FAISS index (~minutes)

streamlit run streamlit_app.py        # web UI at http://localhost:8501
python main_console.py                # CLI
python main_console.py test           # smoke test both providers
```

---

## Docker

```bash
# One-time: build FAISS index (place PDF in data/ first)
docker compose --profile build run --rm vector-builder

# Start web UI at http://localhost:8501
docker compose up
```

- Multi-stage build — only the venv and app code land in the runtime image
- Non-root user (`appuser`, uid 1000)
- Named volume `vectordb:/app/vectorDB` — FAISS index persists across container restarts and image rebuilds
- HuggingFace embedding model pre-downloaded at build time — no network calls at startup
- Healthcheck via Streamlit's built-in `/_stcore/health` endpoint

---

## Configuration

All settings are managed by Pydantic Settings in `config.py`. Every field can be overridden via environment variable or `.env` file. Startup validates that at least one LLM key is present before any application code runs.

| Variable | Default | Notes |
|----------|---------|-------|
| `OPENAI_API_KEY` | — | At least one LLM key required |
| `GROQ_API_KEY` | — | At least one LLM key required |
| `HUGGINGFACEHUB_ACCESS_TOKEN` | — | Required for embedding model |
| `OPENAI_MODEL` | `gpt-4o` | |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | |
| `TEMPERATURE` | `0.3` | Fixed for factual consistency — do not change at runtime |
| `MAX_TOKENS` | `1500` | |
| `RETRIEVER_K` | `12` | MMR retrieval k |
| `RETRIEVER_LAMBDA_MULT` | `0.7` | MMR diversity parameter |
| `LOG_LEVEL` | `INFO` | |
| `LOG_FILE` | `app.log` | Rotating, 10 MB / 3 backups |

---

## Repository Structure

```
.
├── specs/                    # Feature specs: non-tech, tech, reviews, summaries
│   ├── 01-config-refactor/
│   ├── 02-testing-framework/
│   ├── 03-error-handling/
│   ├── 04-docker/
│   ├── 05-ci-cd/
│   └── 06-rag-evaluation/
├── .claude/
│   ├── commands/             # /create-spec, /ship-feature, /test, /lint, /fix, /eval
│   ├── skills/               # generate-non-tech-spec, generate-tech-spec, write-test, rag-eval
│   └── agents/               # test-writer, code-reviewer, security-reviewer
├── .github/workflows/        # pr-checks.yml (3 parallel jobs), docker-build.yml
├── evals/
│   └── golden_questions.json # 20 curated Q&A pairs with expected clinical key points
└── tests/                    # 191 unit tests across 11 files
```

---

## Legal

This system is for educational and research use. Users must own a legitimate copy of Shafer's Textbook of Oral Pathology (7th Edition) and comply with all applicable copyright terms.
