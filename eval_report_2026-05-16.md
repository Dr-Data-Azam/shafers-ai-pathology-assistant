# RAG Evaluation Report
**Date:** 2026-05-16
**Generation provider:** openai
**Judge:** OpenAI gpt-4o (temperature=0)

## Summary
- Questions evaluated: 20
- Average Faithfulness: 3.35 / 5.0
- Average Relevance: 4.3 / 5.0
- Average Completeness: 3.7 / 5.0
- Overall Average: 3.78 / 5.0
- Pass rate (overall ≥ 3.5): 60.0%
- Critical failures (any dimension < 2.0): 0

**Verdict: ACCEPTABLE** — Below 80% target. Review report before shipping.

## Regressions vs Last Run
No regressions detected (or first run).

## Failures (any dimension < 3.0)
| Q# | Question | F | R | C | Issue |
|----|----------|---|---|---|-------|
| 7 | What are the types of ameloblastoma? | 3 | 3 | 2 | C: The expected key points of solid/multicystic, unicystic, and peripheral/extraosseous are not full |
| 8 | List the pre-malignant conditions of the oral cavi | 2 | 4 | 4 | F: The claim about sideropenic dysphagia is not supported by the retrieved context. |
| 11 | Describe the clinical features of oral squamous ce | 3 | 3 | 2 | C: The answer misses key points like 'ulcer with raised everted edges' and 'induration'. |
| 20 | Describe the management of odontogenic keratocyst. | 3 | 3 | 2 | C: The answer mentions the high recurrence rate but omits key management strategies like enucleation |

## Full Results
| Q# | Category | Question | F | R | C | Overall | Verdict |
|----|----------|----------|---|---|---|---------|---------|
| 1 | Definition | What is leukoplakia? | 4 | 5 | 5 | 4.67 | PASS |
| 2 | Definition | Define ameloblastoma. | 3 | 5 | 5 | 4.33 | PASS |
| 3 | Definition | What is periapical granuloma? | 4 | 5 | 5 | 4.67 | PASS |
| 4 | Definition | Define oral submucous fibrosis. | 4 | 5 | 4 | 4.33 | PASS |
| 5 | Definition | What is a dentigerous cyst? | 4 | 5 | 5 | 4.67 | PASS |
| 6 | Classification | Classify odontogenic cysts. | 3 | 4 | 4 | 3.67 | PASS |
| 7 | Classification | What are the types of ameloblastoma? | 3 | 3 | 2 | 2.67 | FAIL |
| 8 | Classification | List the pre-malignant conditions of the oral | 2 | 4 | 4 | 3.33 | FAIL |
| 9 | Classification | Classify salivary gland tumors. | 3 | 4 | 3 | 3.33 | FAIL |
| 10 | Classification | What are the types of fibro-osseous lesions? | 3 | 4 | 3 | 3.33 | FAIL |
| 11 | Clinical Features | Describe the clinical features of oral squamo | 3 | 3 | 2 | 2.67 | FAIL |
| 12 | Clinical Features | What are the histological features of pleomor | 4 | 4 | 3 | 3.67 | PASS |
| 13 | Clinical Features | Describe the clinical presentation of geograp | 3 | 5 | 4 | 4.0 | PASS |
| 14 | Clinical Features | What are the features of Sjogren's syndrome? | 4 | 4 | 4 | 4.0 | PASS |
| 15 | Clinical Features | Describe the radiographic features of amelobl | 3 | 4 | 3 | 3.33 | FAIL |
| 16 | Comparison | What is the difference between leukoplakia an | 4 | 5 | 4 | 4.33 | PASS |
| 17 | Comparison | Differentiate periapical granuloma from peria | 3 | 5 | 4 | 4.0 | PASS |
| 18 | Comparison | Compare pleomorphic adenoma and mucoepidermoi | 4 | 5 | 5 | 4.67 | PASS |
| 19 | Edge Cases | What causes white sponge nevus? | 3 | 4 | 3 | 3.33 | FAIL |
| 20 | Edge Cases | Describe the management of odontogenic kerato | 3 | 3 | 2 | 2.67 | FAIL |