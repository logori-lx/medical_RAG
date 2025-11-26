import os
from typing import List, Dict, Tuple, Optional
from query_constructing.query_constructor import QueryConstructor
from retrieve.retrieval import Retrieval, RetrievalMethod
from retrieve.rerank import Reranker


_retriever: Optional[Retrieval] = None
_query_constructor: Optional[QueryConstructor] = None


def _get_query_constructor() ->QueryConstructor:
    global _query_constructor
    if _query_constructor is None:
        api_key = os.getenv("MEDICAL_RAG")
        _query_constructor = QueryConstructor(api_key=api_key)
    return _query_constructor

def _get_retriever() -> Retrieval:
    global _retriever
    if _retriever is None:
        # If the local vector library is not initialized, ret.py will throw a clear error prompt internally
        _query_constructor = _get_query_constructor()
        _retriever = Retrieval(_query_constructor)
    return _retriever


def initialize_rag_system():
    """
    Pre-initialize the RAG system (including retriever and client).
It is recommended to call it when the application starts to avoid initialization delay during the first request.
    """
    print("The RAG system is being initialized...")
    try:
        retriever = _get_retriever()
        print("✓ Retriever initialization completed (including BM25 index)")
    except Exception as e:
        print(f"✗ Retriever Retriever initialization failed: {e}")
    
    print("The initialization of the RAG system is complete!")
    return retriever



def retrieve_and_generate(
    question: str,
    search_type: str=RetrievalMethod.HYBRID.value,
    model: str = "glm-4",
    temperature: float = 1.0,
    max_tokens: int = 65536,
) -> Tuple[str, List[Dict]]:
    """
    Complete RAG: Search -> Prompt Build -> Large Model Generation.

    Return
    - answer: Final Answer (Chinese)
    - context: The cited search results (for front-end display and traceability)
    """
    retriever = _get_retriever()
    rewritten_query = _get_query_constructor().get_query(question)
    # Recall
    contexts = retriever.retrieve(
        query=rewritten_query, top_k=50,  retrieval_type=search_type
    )
    reranker = Reranker()
    reranked_contexts = reranker.rerank(rewritten_query,contexts, top_k=5)
    answer = _get_query_constructor().process_medical_query(question=rewritten_query,
                                                            context=reranked_contexts,
                                                            model=model, 
                                                            temperature=temperature, 
                                                            max_tokens=max_tokens)
    final_context = []
    for context in reranked_contexts:
        final_context.append(
            {
                "ask": context["ask"],
                "answer": context["answer"],
                "department": context["department"],
            }
        )
    return answer, final_context


__all__ = ["retrieve_and_generate", "initialize_rag_system"]
