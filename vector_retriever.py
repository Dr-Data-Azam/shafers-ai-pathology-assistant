# File: vector_retriever.py
import logging
import os
import pickle
from typing import Any, Dict, List

from langchain_community.vectorstores import FAISS
from langchain_core.vectorstores import VectorStoreRetriever

from config import get_config
from exceptions import RetrieverError
from vector_store_creator import get_embedding_model

logger = logging.getLogger(__name__)

# Global cache for retriever
_retriever = None


def get_retriever() -> VectorStoreRetriever:
    """Get or create FAISS retriever with caching"""
    global _retriever
    if _retriever is not None:
        return _retriever

    cfg = get_config()
    db_path = cfg.db_path
    retriever_path = cfg.retriever_path

    if not os.path.exists(db_path):
        raise RetrieverError(
            "Vector DB not found. Please run vector_store_creator.py first."
        )

    if os.path.exists(retriever_path):
        with open(retriever_path, "rb") as f:
            _retriever = pickle.load(f)
            return _retriever

    logger.info("Loading vector database from %s", db_path)
    db = FAISS.load_local(
        folder_path=db_path,
        embeddings=get_embedding_model(),
        allow_dangerous_deserialization=True,
    )

    _retriever = db.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": cfg.retriever_k,
            "fetch_k": cfg.retriever_fetch_k,
            "lambda_mult": cfg.retriever_lambda_mult,
        },
    )

    with open(retriever_path, "wb") as f:
        pickle.dump(_retriever, f)

    return _retriever


def generate_related_terms(query: str) -> List[str]:
    """Generate related search terms for comprehensive coverage"""
    query_lower = query.lower()
    related_terms = []

    term_expansions = {
        "anomalies": ["abnormalities", "malformations", "developmental disorders"],
        "development": ["formation", "growth", "embryology"],
        "tooth": ["dental", "odontogenesis", "teeth"],
        "pathology": ["disease", "disorder", "condition"],
        "diagnosis": ["clinical features", "symptoms", "signs"],
        "treatment": ["management", "therapy", "intervention"],
        "etiology": ["cause", "pathogenesis", "origin"],
        "classification": ["types", "categories", "variants"],
    }

    for key, expansions in term_expansions.items():
        if key in query_lower:
            related_terms.extend(expansions)

    query_words = query.split()
    for word in query_words:
        if len(word) > 3:
            related_terms.append(word)

    return list(set(related_terms))[:5]


def get_comprehensive_context(query: str, retriever) -> List[Any]:
    """Enhanced context retrieval for comprehensive answers"""
    cfg = get_config()
    primary_docs = retriever.invoke(query)
    related_terms = generate_related_terms(query)

    all_docs = list(primary_docs)
    seen_content = set()

    for doc in primary_docs:
        seen_content.add(doc.page_content[:100])

    for term in related_terms:
        try:
            related_docs = retriever.invoke(term)
            for doc in related_docs:
                doc_id = doc.page_content[:100]
                if doc_id not in seen_content and len(all_docs) < cfg.max_context_docs:
                    all_docs.append(doc)
                    seen_content.add(doc_id)
        except Exception as e:
            logger.warning("Error searching for term '%s': %s", term, e)
            continue

    return all_docs


def process_documents_for_context(docs: List[Any]) -> tuple[str, Dict[str, List[str]]]:
    """Process retrieved documents into organized context"""
    context_parts = []
    page_groups: Dict[str, List[str]] = {}

    for doc in docs:
        page_num = doc.metadata.get("page_number", "N/A")
        if isinstance(page_num, int) and page_num > 0:
            corrected_page = page_num - 22
            page_display = (
                f"Page {corrected_page}" if corrected_page > 0 else "Front Matter"
            )
        else:
            page_display = "Front Matter"

        if page_display not in page_groups:
            page_groups[page_display] = []
        page_groups[page_display].append(doc.page_content)

    for page_display in sorted(
        page_groups.keys(), key=lambda x: (x != "Front Matter", x)
    ):
        page_content = " ".join(page_groups[page_display])
        context_parts.append(f"[{page_display}]\n{page_content}")

    context = "\n\n".join(context_parts)
    return context, page_groups
