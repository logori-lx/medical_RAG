import os
import json
import requests
from retrieval import Retrieval 
import sys

API_KEY = os.getenv("MEDICAL_RAG")

class rerank:
    def __init__(self, model="rerank", top_n=4):
        self.model = model
        self.top_n = top_n
        self.url = "https://open.bigmodel.cn/api/paas/v4/rerank"
    def rank(self, query, documents):
        payload = {
            "model": self.model,
            "query": query,
            "top_n": self.top_n,
            "documents": documents
        }
        headers = {
            "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
        }
        response = requests.post(self.url, json=payload, headers=headers)
        return response.json()["results"]
    
    
if __name__ == "__main__":
    query = sys.argv[1]
    retriever = Retrieval()
    documents = retriever.bm25_retrieve(query)
    documents_final = [i.text for i in documents]
    rerank = rerank()
    results = rerank.rank(query, documents_final)
    print(results)



