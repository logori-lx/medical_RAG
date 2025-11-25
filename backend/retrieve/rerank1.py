import os
import sys
import requests
from typing import List, Dict
from retrieval import Retrieval, RetrievalMethod
from query_constructing.query_constructor import QueryConstructor
API_KEY = os.getenv("MEDICAL_RAG")

root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_path)


class Rerank:
    def __init__(self, model="rerank"):
        self.model = model
        self.api_key = API_KEY
        self.url = "https://open.bigmodel.cn/api/paas/v4/rerank"

    def rerank(self, query: str, docs: List[Dict], top_k: int = 5) -> List[Dict]:
        if not docs:
            return []

        # Try API sorting first (if the key is obtained)
        if self.api_key:
            try:
                return self._api_rerank(query, docs, top_k)
            except Exception as e:
                print(f"[Rerank-API失败] {e}")

        # No key or failure → Local score as a safety net
        return self._score_rerank(docs, top_k)

    def _api_rerank(self, query: str, docs: List[Dict], top_k: int) -> List[Dict]:
        payload = {
            "model": self.model,
            "query": query,
            "documents": [d.get("answer", "") for d in docs],
            "top_n": top_k
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        resp = requests.post(self.url, json=payload, headers=headers).json()

        # API returns an exception → fallback sort
        if "results" not in resp:
            print("[The API returns an exception, which will be sorted using score]")
            return self._score_rerank(docs, top_k)

        # Sort by relevance_score to take the topK (keep the original structure without adding new fields)
        ranked = sorted(resp["results"], key=lambda x: x["relevance_score"], reverse=True)
        return [docs[i["index"]] for i in ranked][:top_k]

    def _score_rerank(self, docs: List[Dict], top_k: int) -> List[Dict]:
        docs_sorted = sorted(docs, key=lambda d: d.get("score", 0), reverse=True)
        return docs_sorted[:top_k]


if __name__ == "__main__":

    query = "What are the symptoms of diabetes"
    qc = QueryConstructor(API_KEY)
    retriever = Retrieval(query_constructor=qc)

    docs = retriever.retrieve(RetrievalMethod.BM25.value, query, top_k=50)
    reranker = Rerank()
    results = reranker.rerank(query, docs, top_k=5)
