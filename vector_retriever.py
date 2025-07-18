# File: vector_retriever.py
import os
import pickle
from typing import List, Dict, Any
from langchain_community.vectorstores import FAISS
from vector_store_creator import embedding_model

DB_PATH = "vectorDB/my_FAISS_db"
RETRIEVER_PATH = "vectorDB/retriever.pkl"

# Global cache for retriever
_retriever = None

def get_retriever():
    """Get or create FAISS retriever with caching"""
    global _retriever
    if _retriever is not None:
        return _retriever
    
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError("Vector DB not found. Please run vector_store_creator.py first.")
    
    if os.path.exists(RETRIEVER_PATH):
        with open(RETRIEVER_PATH, "rb") as f:
            _retriever = pickle.load(f)
            return _retriever
    
    print("Loading vector database...")
    db = FAISS.load_local(folder_path=DB_PATH, embeddings=embedding_model, allow_dangerous_deserialization=True)
    
    # Enhanced retriever configuration for comprehensive answers
    _retriever = db.as_retriever(
        search_type="mmr",  # MMR for better diversity
        search_kwargs={
            "k": 12,  # Increased for more comprehensive context
            "fetch_k": 25,  # Fetch more candidates for better diversity
            "lambda_mult": 0.7  # Balance between relevance and diversity
        }
    )
    
    with open(RETRIEVER_PATH, "wb") as f:
        pickle.dump(_retriever, f)
    
    return _retriever

def generate_related_terms(query: str) -> List[str]:
    """Generate related search terms for comprehensive coverage"""
    query_lower = query.lower()
    related_terms = []
    
    # Common dental terminology expansion
    term_expansions = {
        'anomalies': ['abnormalities', 'malformations', 'developmental disorders'],
        'development': ['formation', 'growth', 'embryology'],
        'tooth': ['dental', 'odontogenesis', 'teeth'],
        'pathology': ['disease', 'disorder', 'condition'],
        'diagnosis': ['clinical features', 'symptoms', 'signs'],
        'treatment': ['management', 'therapy', 'intervention'],
        'etiology': ['cause', 'pathogenesis', 'origin'],
        'classification': ['types', 'categories', 'variants']
    }
    
    # Add expanded terms
    for key, expansions in term_expansions.items():
        if key in query_lower:
            related_terms.extend(expansions)
    
    # Add the original query terms
    query_words = query.split()
    for word in query_words:
        if len(word) > 3:  # Skip short words
            related_terms.append(word)
    
    return list(set(related_terms))[:5]  # Return unique terms, limit to 5

def get_comprehensive_context(query: str, retriever) -> List[Any]:
    """Enhanced context retrieval for comprehensive answers"""
    
    # Primary search with original query
    primary_docs = retriever.invoke(query)
    
    # Generate related search terms for better coverage
    related_terms = generate_related_terms(query)
    
    all_docs = list(primary_docs)
    seen_content = set()
    
    # Add content from primary docs
    for doc in primary_docs:
        seen_content.add(doc.page_content[:100])  # Use first 100 chars as identifier
    
    # Search for related terms to get comprehensive coverage
    for term in related_terms:
        try:
            related_docs = retriever.invoke(term)
            for doc in related_docs:
                doc_id = doc.page_content[:100]
                if doc_id not in seen_content and len(all_docs) < 20:  # Limit total docs
                    all_docs.append(doc)
                    seen_content.add(doc_id)
        except Exception as e:
            print(f"Error searching for term '{term}': {e}")
            continue
    
    return all_docs

def process_documents_for_context(docs: List[Any]) -> tuple[str, Dict[str, List[str]]]:
    """Process retrieved documents into organized context"""
    context_parts = []
    page_groups = {}
    
    # Group content by page for better organization
    for doc in docs:
        page_num = doc.metadata.get('page_number', 'N/A')
        # Correct the page number offset (subtract 22)
        if isinstance(page_num, int) and page_num > 0:
            corrected_page = page_num - 22
            page_display = f"Page {corrected_page}" if corrected_page > 0 else "Front Matter"
        else:
            page_display = "Front Matter"
        
        if page_display not in page_groups:
            page_groups[page_display] = []
        page_groups[page_display].append(doc.page_content)
    
    # Build organized context
    for page_display in sorted(page_groups.keys(), key=lambda x: (x != "Front Matter", x)):
        page_content = " ".join(page_groups[page_display])
        context_parts.append(f"[{page_display}]\n{page_content}")
    
    context = "\n\n".join(context_parts)
    return context, page_groups