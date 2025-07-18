# File: rag_system.py
import time
from typing import Tuple, Dict, Any
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from llm_provider_manager import load_llm, validate_provider
from vector_retriever import get_retriever, get_comprehensive_context, process_documents_for_context
from chat_history_manager import save_chat_history

# Adaptive prompt template for both specific and general questions
PROMPT_TEMPLATE = """You are a distinguished dental expert specializing in Oral Medicine, Diagnosis & Pathology. Your task is to provide accurate, educational answers using ONLY the provided textbook excerpts from Shafer's Oral Pathology.

IMPORTANT INSTRUCTIONS:
1. ANALYZE THE QUESTION TYPE first to determine the appropriate response approach
2. Synthesize information from ALL provided excerpts to create a complete, cohesive answer
3. Organize fragmented information into a logical response
4. Reference page numbers for key points when available
5. If information spans multiple excerpts, integrate them seamlessly

RESPONSE APPROACH BASED ON QUESTION TYPE:

FOR SPECIFIC REQUESTS (list, enumerate, classify, define, name, identify):
- Provide EXACTLY what is asked for
- Use clear, organized formatting (numbered lists, bullet points when appropriate)
- Focus solely on the requested information
- Do NOT add unrequested details about treatment, causes, etc. unless specifically asked
- Be concise and direct

FOR GENERAL CONCEPT QUESTIONS (explain, describe, discuss, what is):
- Start with a clear definition/overview
- Provide comprehensive coverage including: etiology, pathogenesis, clinical features, diagnosis, treatment, and prognosis (when available)
- Include classifications, subtypes, and variations
- Mention differential diagnoses and related conditions
- Conclude with clinical significance and key takeaways

FOR COMPARISON QUESTIONS (difference between, compare, contrast):
- Create clear comparisons in table or structured format
- Focus on distinguishing features
- Highlight key differences requested

FORMATTING GUIDELINES:
- Use numbered lists for enumerations/classifications
- Use bullet points for features/characteristics
- Use clear headings when covering multiple aspects
- Keep responses organized and scannable

If complete information is not available in the provided excerpts, state: "Based on the available excerpts, [provide what information is available], however, additional details may be found in other sections of the textbook."

Context from Shafer's Oral Pathology:
{context}

Question: {question}

Provide an appropriate answer based on the question type:"""

def create_prompt():
    """Create and return the prompt template"""
    return PromptTemplate(
        input_variables=["context", "question"],
        template=PROMPT_TEMPLATE
    )

def ask_question(query: str, provider: str = "openai", save_history: bool = True) -> Tuple[str, Dict[str, Any]]:
    """
    Ask a question and get comprehensive answer
    
    Args:
        query: The question to ask
        provider: LLM provider ('openai' or 'groq')
        save_history: Whether to save interaction to history
    
    Returns:
        Tuple of (answer, statistics)
    """
    start_time = time.time()
    
    try:
        # Validate provider
        validate_provider(provider)
        
        # Get retriever and LLM (cached after first call)
        retriever = get_retriever()
        llm = load_llm(provider)
        
        retrieval_start = time.time()
        # Get comprehensive context
        docs = get_comprehensive_context(query, retriever)
        retrieval_time = time.time() - retrieval_start
        
        # Process documents into organized context
        context, page_groups = process_documents_for_context(docs)
        
        # Create chain and invoke
        prompt = create_prompt()
        parser = StrOutputParser()
        chain = prompt | llm | parser
        
        llm_start = time.time()
        result = chain.invoke({"context": context, "question": query})
        llm_time = time.time() - llm_start
        
        total_time = time.time() - start_time
        
        # Performance stats
        stats = {
            "provider": provider.upper(),
            "documents_retrieved": len(docs),
            "pages_retrieved": len(page_groups),
            "retrieval_time": retrieval_time,
            "llm_time": llm_time,
            "total_time": total_time,
            "success": True,
            "error": None
        }
        
        # Save to history if requested
        if save_history:
            save_chat_history(query, result, provider, retrieval_time, llm_time, total_time, len(page_groups))
        
        return result, stats
        
    except Exception as e:
        error_stats = {
            "provider": provider.upper(),
            "documents_retrieved": 0,
            "pages_retrieved": 0,
            "retrieval_time": 0,
            "llm_time": 0,
            "total_time": time.time() - start_time,
            "success": False,
            "error": str(e)
        }
        return f"Error: {str(e)}", error_stats

def get_system_info() -> Dict[str, Any]:
    """Get information about the RAG system"""
    from llm_provider_manager import get_available_providers
    import os
    
    return {
        "available_providers": get_available_providers(),
        "vector_db_exists": os.path.exists("vectorDB/my_FAISS_db"),
        "retriever_cached": os.path.exists("vectorDB/retriever.pkl"),
        "chat_history_exists": os.path.exists("chat_history.json")
    }