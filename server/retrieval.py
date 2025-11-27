import os
import sys
import pandas as pd
import chromadb
from typing import List, Dict, Any
from enum import Enum
from zhipuai import ZhipuAI
from git import Repo

# --- 1. 自动定位项目根目录与数据库路径 ---
try:
    repo_obj = Repo(".", search_parent_directories=True)
    REPO_PATH = repo_obj.working_tree_dir
except:
    REPO_PATH = "."

# 数据库路径 (必须与 Indexer 保持一致)
DB_PATH = os.path.join(REPO_PATH, ".git_guard", "chroma_db")
API_KEY = os.getenv("MEDICAL_RAG")  # 或者 ZHIPUAI_API_KEY

# 文件后缀与集合映射
EXT_TO_COLLECTION = {
    ".py": "repo_python", ".java": "repo_java", ".js": "repo_js",
    ".ts": "repo_js", ".html": "repo_html", ".go": "repo_go", ".cpp": "repo_cpp"
}

class RetrievalMethod(Enum):
    VECTOR = "vector"
    HYBRID = "hybrid"

class ZhipuEmbeddingFunction(chromadb.EmbeddingFunction):
    def __init__(self):
        self.api_key = API_KEY
        self.client = ZhipuAI(api_key=self.api_key)
    
    def __call__(self, input: List[str]) -> List[List[float]]:
        if not self.api_key: return [[]] * len(input)
        response = self.client.embeddings.create(model="embedding-3", input=input)
        return [data.embedding for data in response.data]

class Retrieval:
    def __init__(self):
        # 确保数据库存在
        if not os.path.exists(DB_PATH):
            self.client = None
            return

        self.client = chromadb.PersistentClient(path=DB_PATH)
        self.embedding_function = ZhipuEmbeddingFunction()
        self.vector_distance_max = 2.0

    def vector_retrieve(self, query: str, collection_name: str, top_k: int = 5) -> List[Dict]:
        """纯向量检索"""
        if not self.client: return []
        
        try:
            collection = self.client.get_collection(
                name=collection_name, 
                embedding_function=self.embedding_function
            )
            results = collection.query(query_texts=[query], n_results=top_k)
            
            hits = []
            if results['ids'] and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    dist = results['distances'][0][i]
                    # 将距离转换为相似度分数 (0~1)
                    score = 1 - min(dist / self.vector_distance_max, 1.0)
                    hits.append({
                        "id": results['ids'][0][i],
                        "answer": results['documents'][0][i], # 统一字段名为 answer
                        "metadata": results['metadatas'][0][i],
                        "score": score,
                        "source": "vector"
                    })
            return hits
        except Exception:
            return []

    def hybrid_retrieve(self, query: str, collection_name: str, top_k: int = 5) -> List[Dict]:
        """
        简化版混合检索：向量检索 + 关键词匹配加权
        (由于在 Git Hook 环境下不宜安装 pandas/jieba 等重型库，这里使用轻量级混合策略)
        """
        # 1. 获取向量结果
        vector_hits = self.vector_retrieve(query, collection_name, top_k=top_k * 2) # 扩大召回
        
        # 2. 简单的关键词/字面匹配加权 (模拟 Keyword Search)
        # 如果代码片段中直接包含了 Query 中的关键词，增加权重
        keywords = set(query.split())
        
        for hit in vector_hits:
            code_content = hit["answer"]
            match_count = sum(1 for kw in keywords if kw in code_content)
            
            # 混合打分公式: Vector Score * 0.7 + Keyword Match * 0.3
            keyword_score = min(match_count * 0.1, 1.0) # 简单的归一化
            hit["score"] = (hit["score"] * 0.7) + (keyword_score * 0.3)
            hit["source"] = "hybrid"

        # 3. 重新排序并截断
        sorted_hits = sorted(vector_hits, key=lambda x: x["score"], reverse=True)[:top_k]
        return sorted_hits

    def retrieve_code(self, query_diff: str, file_ext: str, top_k: int = 5) -> List[Dict]:
        """对外暴露的统一接口"""
        if file_ext not in EXT_TO_COLLECTION:
            return []
            
        col_name = EXT_TO_COLLECTION[file_ext]
        # 默认使用混合检索
        return self.hybrid_retrieve(query_diff, col_name, top_k)