import glob
import json
import logging
import os
import pathlib
import re
from typing import Any

from langchain_openai import ChatOpenAI

from config import get_config
from exceptions import ConfigError, LLMError
from rag_system import ask_question
from vector_retriever import (
    get_comprehensive_context,
    get_retriever,
    process_documents_for_context,
)

logger = logging.getLogger(__name__)

# Absolute path to the project root — used for all file I/O so eval_runner
# works correctly regardless of the caller's working directory.
_PROJECT_ROOT = pathlib.Path(__file__).parent

JUDGE_PROMPT_TEMPLATE = """You are evaluating an oral pathology RAG system's answer quality.

Question: __QUESTION__
Expected key points: __KEY_POINTS__
System answer: __ANSWER__
Retrieved context: __CONTEXT__

Score on three dimensions (1-5 each):
1. Faithfulness: Is every claim supported by the retrieved context?
2. Relevance: Does the answer address what was specifically asked?
3. Completeness: Are the expected key points present in the answer?

Respond ONLY with valid JSON, no markdown fences, no extra text:
{
  "faithfulness": 1-5,
  "relevance": 1-5,
  "completeness": 1-5,
  "faithfulness_reason": "one sentence",
  "relevance_reason": "one sentence",
  "completeness_reason": "one sentence",
  "overall": average of three scores as a float
}"""

# Max characters of context forwarded to the judge to stay within token budget
_JUDGE_CONTEXT_LIMIT = 3000


def load_golden_questions(path: str) -> list[dict]:
    """Load the golden question set from a JSON file."""
    if not os.path.exists(path):
        raise ConfigError(f"Golden questions file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_answer_with_context(question: str, provider: str) -> tuple[str, str]:
    """Run a question through the RAG pipeline and return (answer, context).

    Context is retrieved independently so the judge can assess faithfulness.
    Both calls share the cached retriever — FAISS is only loaded once.
    """
    retriever = get_retriever()
    docs = get_comprehensive_context(question, retriever)
    context, _ = process_documents_for_context(docs)
    answer, _ = ask_question(question, provider=provider, save_history=False)
    return answer, context


def _create_judge_llm() -> ChatOpenAI:
    """Create a fresh OpenAI judge instance (temperature=0, not the cached app LLM)."""
    cfg = get_config()
    if not cfg.openai_api_key:
        raise LLMError(
            provider="openai",
            message=(
                "OPENAI_API_KEY is required for the evaluation judge "
                "regardless of the generation provider"
            ),
        )
    return ChatOpenAI(model=cfg.openai_model, temperature=0, api_key=cfg.openai_api_key)


def score_answer(
    question: str,
    answer: str,
    context: str,
    expected_key_points: list[str],
    judge_llm: ChatOpenAI | None = None,
) -> dict[str, Any]:
    """Score one answer on faithfulness, relevance, and completeness via LLM judge.

    Pass a pre-built judge_llm to reuse one instance across many calls (recommended
    for batch scoring). When None, a fresh instance is created via _create_judge_llm().
    Returns a dict with keys: faithfulness, relevance, completeness,
    faithfulness_reason, relevance_reason, completeness_reason, overall.
    Raises LLMError if the judge returns unparseable output.
    """
    prompt = (
        JUDGE_PROMPT_TEMPLATE.replace("__QUESTION__", question)
        .replace("__KEY_POINTS__", ", ".join(expected_key_points))
        .replace("__ANSWER__", answer)
        .replace("__CONTEXT__", context[:_JUDGE_CONTEXT_LIMIT])
    )
    llm = judge_llm if judge_llm is not None else _create_judge_llm()
    response = llm.invoke(prompt)
    raw = response.content.strip()

    # Strip markdown code fences if the model wraps the JSON anyway
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        scores = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.debug("Judge raw response (unparseable): %s", raw)
        raise LLMError(
            provider="openai",
            message=f"Judge returned unparseable JSON ({len(raw)} chars).",
        ) from exc

    required = {
        "faithfulness",
        "relevance",
        "completeness",
        "faithfulness_reason",
        "relevance_reason",
        "completeness_reason",
        "overall",
    }
    missing = required - scores.keys()
    if missing:
        raise LLMError(
            provider="openai",
            message=f"Judge response missing required fields: {missing}",
        )
    return scores


def compute_summary(scored_results: list[dict]) -> dict[str, Any]:
    """Compute per-dimension averages, overall average, pass rate, and fail count."""
    n = len(scored_results)
    if n == 0:
        return {
            "questions_evaluated": 0,
            "avg_faithfulness": 0.0,
            "avg_relevance": 0.0,
            "avg_completeness": 0.0,
            "overall_avg": 0.0,
            "pass_rate": 0.0,
            "fail_count": 0,
        }

    avg_f = sum(r["faithfulness"] for r in scored_results) / n
    avg_r = sum(r["relevance"] for r in scored_results) / n
    avg_c = sum(r["completeness"] for r in scored_results) / n
    overall_avg = sum(r["overall"] for r in scored_results) / n

    pass_count = sum(1 for r in scored_results if r["overall"] >= 3.5)
    fail_count = sum(
        1
        for r in scored_results
        if r["faithfulness"] < 2.0 or r["relevance"] < 2.0 or r["completeness"] < 2.0
    )

    return {
        "questions_evaluated": n,
        "avg_faithfulness": round(avg_f, 2),
        "avg_relevance": round(avg_r, 2),
        "avg_completeness": round(avg_c, 2),
        "overall_avg": round(overall_avg, 2),
        "pass_rate": round(pass_count / n * 100, 1),
        "fail_count": fail_count,
    }


def find_previous_results(glob_pattern: str) -> dict | None:
    """Return the parsed JSON of the most recent eval results file, or None."""
    matches = sorted(glob.glob(glob_pattern))
    if not matches:
        return None
    with open(matches[-1], encoding="utf-8") as f:
        return json.load(f)


def detect_regressions(current: list[dict], previous: dict | None) -> list[dict]:
    """Return questions where overall score dropped >0.5 or any dimension fell <2.0."""
    if previous is None:
        return []
    prev_by_id = {q["id"]: q for q in previous.get("questions", [])}
    regressions = []
    for result in current:
        qid = result["id"]
        if qid not in prev_by_id:
            continue
        prev_overall = prev_by_id[qid].get("overall", 0)
        curr_overall = result["overall"]
        drop = round(prev_overall - curr_overall, 2)
        critical = (
            result["faithfulness"] < 2.0
            or result["relevance"] < 2.0
            or result["completeness"] < 2.0
        )
        if drop > 0.5 or critical:
            regressions.append(
                {
                    "id": qid,
                    "question": result["question"],
                    "prev_overall": prev_overall,
                    "curr_overall": curr_overall,
                    "drop": max(drop, 0.0),
                    "critical": critical,
                }
            )
    return regressions


def generate_markdown_report(
    results: list[dict],
    summary: dict,
    regressions: list[dict],
    provider: str,
    date_str: str,
) -> str:
    """Build the full markdown evaluation report string."""
    cfg = get_config()
    lines: list[str] = [
        "# RAG Evaluation Report",
        f"**Date:** {date_str}",
        f"**Generation provider:** {provider}",
        f"**Judge:** OpenAI {cfg.openai_model} (temperature=0)",
        "",
        "## Summary",
        f"- Questions evaluated: {summary['questions_evaluated']}",
        f"- Average Faithfulness: {summary['avg_faithfulness']} / 5.0",
        f"- Average Relevance: {summary['avg_relevance']} / 5.0",
        f"- Average Completeness: {summary['avg_completeness']} / 5.0",
        f"- Overall Average: {summary['overall_avg']} / 5.0",
        f"- Pass rate (overall ≥ 3.5): {summary['pass_rate']}%",
        f"- Critical failures (any dimension < 2.0): {summary['fail_count']}",
    ]

    if summary["pass_rate"] >= 80:
        lines.append("\n**Verdict: PASS** — Quality target met. Safe to ship.")
    elif summary["pass_rate"] >= 60:
        lines.append(
            "\n**Verdict: ACCEPTABLE** — Below 80% target. Review report before shipping."
        )
    else:
        lines.append(
            "\n**Verdict: FAIL** — Pass rate critically low. Do not ship RAG changes."
        )

    lines += ["", "## Regressions vs Last Run"]
    if regressions:
        lines += [
            "| Q# | Question | Prev Overall | Curr Overall | Drop |",
            "|----|----------|-------------|-------------|------|",
        ]
        for r in regressions:
            drop_display = (
                "CRIT" if r.get("critical") and r["drop"] == 0.0 else r["drop"]
            )
            lines.append(
                f"| {r['id']} | {r['question'][:60]} "
                f"| {r['prev_overall']} | {r['curr_overall']} | {drop_display} |"
            )
    else:
        lines.append("No regressions detected (or first run).")

    failures = [
        r
        for r in results
        if r["faithfulness"] < 3.0 or r["relevance"] < 3.0 or r["completeness"] < 3.0
    ]
    lines += ["", "## Failures (any dimension < 3.0)"]
    if failures:
        lines += [
            "| Q# | Question | F | R | C | Issue |",
            "|----|----------|---|---|---|-------|",
        ]
        for r in failures:
            issues = []
            if r["faithfulness"] < 3.0:
                issues.append(f"F: {r['faithfulness_reason']}")
            if r["relevance"] < 3.0:
                issues.append(f"R: {r['relevance_reason']}")
            if r["completeness"] < 3.0:
                issues.append(f"C: {r['completeness_reason']}")
            lines.append(
                f"| {r['id']} | {r['question'][:50]} "
                f"| {r['faithfulness']} | {r['relevance']} | {r['completeness']} "
                f"| {'; '.join(issues)[:100]} |"
            )
    else:
        lines.append("No failures.")

    lines += ["", "## Full Results"]
    lines += [
        "| Q# | Category | Question | F | R | C | Overall | Verdict |",
        "|----|----------|----------|---|---|---|---------|---------|",
    ]
    for r in results:
        verdict = "PASS" if r["overall"] >= 3.5 else "FAIL"
        lines.append(
            f"| {r['id']} | {r.get('category', '')} | {r['question'][:45]} "
            f"| {r['faithfulness']} | {r['relevance']} | {r['completeness']} "
            f"| {r['overall']} | {verdict} |"
        )

    return "\n".join(lines)


def save_results(
    results: list[dict],
    summary: dict,
    provider: str,
    date_str: str,
    output_dir: pathlib.Path | None = None,
) -> str:
    """Write scored results to eval_results_<date>.json and return the filename."""
    directory = output_dir if output_dir is not None else _PROJECT_ROOT
    filename = f"eval_results_{date_str}.json"
    filepath = directory / filename
    payload = {
        "date": date_str,
        "provider": provider,
        "summary": summary,
        "questions": results,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    logger.info("Evaluation results saved to %s", filepath)
    return filename


def run_full_evaluation(
    provider: str = "openai",
    questions_path: str | None = None,
    output_dir: pathlib.Path | None = None,
) -> dict:
    """Orchestrate the full evaluation pipeline and return the summary dict.

    Loads golden questions, scores each answer via LLM judge, compares to the
    previous run for regressions, and writes both a JSON results file and a
    markdown report. All output is written to output_dir (defaults to the
    project root so paths are stable regardless of the caller's cwd).
    """
    from datetime import date

    directory = output_dir if output_dir is not None else _PROJECT_ROOT
    if questions_path is None:
        questions_path = str(_PROJECT_ROOT / "evals" / "golden_questions.json")

    date_str = date.today().isoformat()

    questions = load_golden_questions(questions_path)
    total = len(questions)
    scored: list[dict] = []

    # Create the judge LLM once — avoids 20 redundant instantiations and
    # surfaces a missing API key before the loop starts.
    judge = _create_judge_llm()

    for i, q in enumerate(questions, start=1):
        logger.info("Evaluating question %d/%d — %s", i, total, q["question"])
        answer, context = get_answer_with_context(q["question"], provider)
        scores = score_answer(
            question=q["question"],
            answer=answer,
            context=context,
            expected_key_points=q["expected_key_points"],
            judge_llm=judge,
        )
        scored.append(
            {
                "id": q["id"],
                "category": q.get("category", ""),
                "question": q["question"],
                "answer": answer,
                "expected_key_points": q["expected_key_points"],
                **scores,
            }
        )

    summary = compute_summary(scored)
    previous = find_previous_results(str(directory / "eval_results_*.json"))
    regressions = detect_regressions(scored, previous)

    report_md = generate_markdown_report(
        scored, summary, regressions, provider, date_str
    )
    report_filename = f"eval_report_{date_str}.md"
    report_path = directory / report_filename
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    logger.info("Evaluation report saved to %s", report_path)

    save_results(scored, summary, provider, date_str, output_dir=directory)

    summary["report_file"] = report_filename
    summary["regressions"] = len(regressions)
    return summary


if __name__ == "__main__":
    import argparse

    from config import configure_logging

    configure_logging(get_config())

    parser = argparse.ArgumentParser(description="Run RAG evaluation suite")
    parser.add_argument(
        "--provider",
        default="openai",
        choices=["openai", "groq"],
        help="LLM provider used for answer generation (judge always uses OpenAI)",
    )
    args = parser.parse_args()

    result = run_full_evaluation(provider=args.provider)

    print(
        f"\nEvaluation complete\n"
        f"Provider:         {args.provider}\n"
        f"Questions scored: {result['questions_evaluated']}\n"
        f"Avg Faithfulness: {result['avg_faithfulness']} / 5.0\n"
        f"Avg Relevance:    {result['avg_relevance']} / 5.0\n"
        f"Avg Completeness: {result['avg_completeness']} / 5.0\n"
        f"Overall avg:      {result['overall_avg']} / 5.0\n"
        f"Pass rate (>=3.5): {result['pass_rate']}%\n"
        f"Regressions:      {result['regressions']}\n"
        f"Report saved:     {result['report_file']}"
    )
