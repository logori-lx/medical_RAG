import os
import requests
from typing import List, Dict

API_KEY = os.getenv("MEDICAL_RAG") # 复用这个 KEY

class Reranker:
    def __init__(self):
        self.url = "https://open.bigmodel.cn/api/paas/v4/rerank"
        self.model = "rerank-3"
        self.api_key = API_KEY

    def rerank(self, query: str, documents: List[Dict], top_k: int = 3) -> List[Dict]:
        """
        调用远程 API 进行重排序
        :param documents: 也就是 Retrieval 返回的 list，包含 {'answer': 'code...'}
        """
        if not self.api_key or not documents:
            return documents[:top_k]

        # 提取纯文本用于 API 调用
        doc_texts = [doc.get("answer", "")[:2000] for doc in documents] # 截断防报错

        payload = {
            "model": self.model,
            "query": query[:1000], 
            "documents": doc_texts,
            "top_n": top_k
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(self.url, json=payload, headers=headers, timeout=5)
            if response.status_code == 200:
                results = response.json().get('results', [])
                
                reranked_docs = []
                for item in results:
                    original_idx = item['index']
                    # 取回原始文档对象
                    doc = documents[original_idx]
                    # 更新分数为 Rerank 分数
                    doc['score'] = item['relevance_score']
                    reranked_docs.append(doc)
                
                return reranked_docs
            else:
                return documents[:top_k] # 降级
        except Exception:
            return documents[:top_k] # 降级