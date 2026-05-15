---
name: rag-eval
description: >
  Use this skill whenever you need to evaluate the quality of RAG answers produced by
  the Shafer's AI Pathology Assistant. Triggered by the /eval command, or when the coder
  asks to "run the evaluation", "check answer quality", "test the RAG pipeline", or
  "evaluate retrieval". This skill defines the golden question set, scoring rubric,
  how to run LLM-as-judge scoring, and how to generate the evaluation report. Use after
  any change to rag_system.py, vector_retriever.py, or the prompt template to detect
  quality regressions before shipping.
---

# Skill: RAG Evaluation Framework

This skill is used by the /eval command. It evaluates whether the RAG pipeline is producing
correct, faithful, and complete answers — not just any answers.

The core question this skill answers: "Is the system getting better or worse?"

---

## When to Run Evaluation

Run /eval after:
- Any change to rag_system.py (prompt template, chain construction)
- Any change to vector_retriever.py (k value, MMR params, query expansion)
- Adding a new LLM provider or changing model settings
- Any config change that affects retrieval or generation

Always run before /ship-feature on RAG-related features to catch regressions.

---

## The Golden Question Set

These 20 questions are the benchmark. They cover a range of question types the app
is designed to handle. Expected answers are based on Shafer's Textbook of Oral Pathology.

### Category 1: Definition Questions (should give concise, accurate definitions)

1. What is leukoplakia?
   Expected: White patch on oral mucosa that cannot be scraped off; pre-malignant potential

2. Define ameloblastoma.
   Expected: Benign but locally aggressive odontogenic tumor derived from enamel organ epithelium

3. What is periapical granuloma?
   Expected: Chronic inflammatory lesion at the root apex; granulation tissue replacing bone

4. Define oral submucous fibrosis.
   Expected: Chronic fibrotic disease of oral mucosa; associated with areca nut/betel quid; pre-malignant

5. What is a dentigerous cyst?
   Expected: Odontogenic cyst surrounding the crown of an unerupted tooth; most common developmental cyst

### Category 2: Classification Questions (should produce organized lists)

6. Classify odontogenic cysts.
   Expected: Developmental (dentigerous, OKC, lateral periodontal) and Inflammatory (periapical, residual)

7. What are the types of ameloblastoma?
   Expected: Solid/multicystic, unicystic, peripheral/extraosseous

8. List the pre-malignant conditions of the oral cavity.
   Expected: Leukoplakia, erythroplakia, oral submucous fibrosis, lichen planus (erosive)

9. Classify salivary gland tumors.
   Expected: Benign (pleomorphic adenoma, Warthin's tumor) and Malignant (mucoepidermoid carcinoma, adenoid cystic)

10. What are the types of fibro-osseous lesions?
    Expected: Fibrous dysplasia, ossifying fibroma, cemento-ossifying fibroma, CGCL

### Category 3: Clinical Features Questions (should cover signs, symptoms, characteristics)

11. Describe the clinical features of oral squamous cell carcinoma.
    Expected: Ulcer with raised everted edges, induration, cervical lymphadenopathy; floor of mouth/lateral tongue common sites

12. What are the histological features of pleomorphic adenoma?
    Expected: Mixed epithelial and mesenchymal elements; myxoid/chondroid stroma; encapsulated

13. Describe the clinical presentation of geographic tongue.
    Expected: Erythematous patches with white serpentine borders; migratory; usually asymptomatic

14. What are the features of Sjogren's syndrome?
    Expected: Xerostomia, xerophthalmia (sicca symptoms); autoimmune; anti-SSA/SSB antibodies

15. Describe the radiographic features of ameloblastoma.
    Expected: Multilocular (soap bubble) or unilocular radiolucency; root resorption; mandible > maxilla

### Category 4: Comparison Questions (should produce clear differentiations)

16. What is the difference between leukoplakia and lichen planus?
    Expected: Leukoplakia is idiopathic white patch; lichen planus is autoimmune with Wickham's striae, bilateral

17. Differentiate periapical granuloma from periapical cyst.
    Expected: Granuloma has no epithelial lining; cyst lined by epithelium; both at root apex

18. Compare pleomorphic adenoma and mucoepidermoid carcinoma.
    Expected: PA is benign, mixed elements, parotid; MEC is malignant, mucous+epidermoid cells, parotid

### Category 5: Edge Cases (tests retrieval limits)

19. What causes white sponge nevus?
    Expected: Autosomal dominant; mutation in keratin 4 or 13; bilateral white folded mucosa

20. Describe the management of odontogenic keratocyst.
    Expected: High recurrence rate; treatment ranges from enucleation to resection; Carnoy's solution adjunct

---

## Scoring Rubric

Score each answer on three dimensions, 1-5 scale:

### Faithfulness (Is the answer grounded in the textbook?)
- 5: Every claim is directly supported by the retrieved context
- 4: Mostly supported; one minor unsupported detail
- 3: Core answer supported; some statements go beyond retrieved context
- 2: Mixed — significant content not in retrieved context
- 1: Answer contradicts or ignores the retrieved context

### Relevance (Does it answer what was asked?)
- 5: Answers exactly what was asked, appropriate level of detail
- 4: Answers the question with minor tangents
- 3: Partially answers; misses an important aspect
- 2: Addresses the topic but not the specific question
- 1: Does not answer the question asked

### Completeness (Did it cover the key points?)
- 5: All expected key points present
- 4: Most key points; missing one minor detail
- 3: Core answer there; missing 1-2 important points
- 2: Significant gaps in expected content
- 1: Missing most expected content

---

## How to Run the Evaluation

### Step 1: Set up the evaluation

```python
# evaluator.py (create if not exists)
import json
from rag_system import ask_question

GOLDEN_QUESTIONS = [
    {"id": 1, "question": "What is leukoplakia?",
     "expected_key_points": ["white patch", "cannot be scraped", "pre-malignant"]},
    # ... (add all 20 from the golden question set above)
]

def run_evaluation(provider="openai", save_to="eval_results.json"):
    results = []
    for item in GOLDEN_QUESTIONS:
        answer, stats = ask_question(item["question"], provider=provider, save_history=False)
        results.append({
            "id": item["id"],
            "question": item["question"],
            "answer": answer,
            "stats": stats,
            "expected_key_points": item["expected_key_points"]
        })
    with open(save_to, "w") as f:
        json.dump(results, f, indent=2)
    return results
```

### Step 2: Score with LLM-as-judge

For each answer, call the LLM with this scoring prompt:

```
You are evaluating an oral pathology RAG system's answer quality.

Question: {question}
Expected key points: {expected_key_points}
System answer: {answer}
Retrieved context: {context}

Score on three dimensions (1-5 each):
1. Faithfulness: Is every claim supported by the retrieved context?
2. Relevance: Does the answer address what was specifically asked?
3. Completeness: Are the expected key points present in the answer?

Respond in JSON:
{
  "faithfulness": <1-5>,
  "relevance": <1-5>,
  "completeness": <1-5>,
  "faithfulness_reason": "<one sentence>",
  "relevance_reason": "<one sentence>",
  "completeness_reason": "<one sentence>",
  "overall": <average of three scores>
}
```

### Step 3: Generate the Report

After scoring all 20 questions, generate a markdown report:

```markdown
# RAG Evaluation Report
Date: <today>
Provider: <openai/groq>
Model: <model name>

## Summary
- Questions evaluated: 20
- Average Faithfulness: X.X / 5.0
- Average Relevance: X.X / 5.0
- Average Completeness: X.X / 5.0
- Overall Average: X.X / 5.0
- Pass rate (score >= 3.5): XX%

## Regressions vs Last Run
<Compare to previous eval_results.json if it exists>
- Questions that got worse: list them
- Questions that improved: list them

## Failures (score < 3.0 on any dimension)
| Q# | Question | Faithfulness | Relevance | Completeness | Issue |
|----|----------|-------------|-----------|--------------|-------|

## Full Results
| Q# | Question | F | R | C | Overall |
|----|----------|---|---|---|---------|
```

Save the report as eval_report_<date>.md in the project root.

---

## Regression Detection

Before running /ship-feature on any RAG-related change:

1. Run /eval and save results as eval_before.json
2. Make the change
3. Run /eval and save results as eval_after.json
4. Compare: flag any question where overall score dropped by more than 0.5

If regressions are found, do not ship. Fix the regression first.

---

## Pass/Fail Thresholds

| Score | Verdict |
|-------|---------|
| >= 4.0 overall | PASS — excellent quality |
| 3.0 - 3.9 overall | ACCEPTABLE — monitor for drift |
| < 3.0 overall | FAIL — do not ship, investigate |
| Any dimension < 2.0 | FAIL — critical issue |

Target: 80%+ of questions at PASS level before any release.
