import os
import chromadb
from typing import List, Dict
from pyparsing import Enum
from zai import ZhipuAiClient  # 确保 zai.py 在PYTHONPATH中
import pandas as pd
from llama_index.core import Document
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.node_parser import SentenceSplitter
import jieba
import sys
import sys
# Get the directory where the current file is located
current_dir = os.path.dirname(os.path.abspath(__file__))
# Obtain the project root directory (adjust according to the actual directory structure)
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
# Add the root directory to the Python path
if root_dir not in sys.path:
    sys.path.append(root_dir)
from query_constructing.query_constructor import QueryConstructor

# Obtain the absolute path of the project root directory (the current file is in the "retrieve" folder, and the root directory is at the previous level).
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# Add the root directory to the Python system path
sys.path.append(root_path)
API_KEY = os.getenv("MEDICAL_RAG")
COLLECTION_NAME = "medical_db"
# Solve the path problem
KEYWORDS_FILE = os.path.join(root_path,"retrieve","disease_names_processed.csv")
DB_PATH = os.path.join(root_path,"DATA","chroma_db")


class RetrievalMethod(Enum):
    VECTOR = "vector"
    HYBRID = "hybrid"
    BM25 = "bm25"
class ZhipuEmbeddingFunction:
    """Zhipu Embedding3 embedding function"""
    """(Add the name attribute)"""
    def name(self):
        """Return the name of the embedded model (the method required by Chroma"""
        return "zhipu-embedding-3"  # Key fix: Change "name" to a method
    def __call__(self, input: List[str]) -> List[List[float]]:
        self.zhipu_api_key = API_KEY
        if not self.zhipu_api_key:
             raise ValueError("ZHIPU_API_KEY environment variable not set.")
        client = ZhipuAiClient(api_key= self.zhipu_api_key)
        response = client.embeddings.create(
                        model="embedding-3", #Fill in the model code that needs to be called
                        input=input,
                    )
        return [data_point.embedding for data_point in response.data]
    def embed_query(self, input) -> List[float]:
        """
        Embed the query string.
        
        :param query: The query string input by the user
        :return: Embedding vector
        """
        return self.__call__(input)
    
class Retrieval:
    def __init__(self, query_constructor: QueryConstructor, collection_name= COLLECTION_NAME, embedding_function = ZhipuEmbeddingFunction()):
        self.client = chromadb.PersistentClient(path=DB_PATH)
        self.collection_name = collection_name
        self.embedding_function = embedding_function
        self.keywords = pd.read_csv(KEYWORDS_FILE)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function
        )
        self.query_constructor = query_constructor
        self.vector_distance_max = 2.0  # Maximum distance for vector retrieval (for normalization)
        
    def jaccard_similarity(self,word1, word2):
        set1 = set(word1)
        set2 = set(word2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union != 0 else 0


    def vector_retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search using the Vector Retrieval model (ChromaDB).
        
        :param query: The query string input by the user
        :param top_k: The number of Top-K results returned
        :return: A list containing document ID, distance and metadata
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
        )
        return results
    
    def keywords_search(self, keyword_in_query: str, top_k: int = 1) -> List[Dict]:
        self.keywords["similarity"] = self.keywords["disease_name"].apply(
            lambda x: self.jaccard_similarity(x, keyword_in_query))
        results = self.keywords.sort_values(by="similarity", ascending=False).head(top_k)
        return results.iloc[:top_k][["disease_name", "similarity"]].to_dict('records') 
    
    def keywords_retrieve(self, query: str, top_k: int = 1) -> List[Dict]:
        keywords_in_query = self.query_constructor.extract_category(query)
        if not keywords_in_query or keywords_in_query[0] == '无':
            return {}  # Return the dictionary type uniformly to avoid subsequent judgment errors

        or_expression_list = []
        keyword_similarities = {}  # Store the similarity of keywords
        for keyword_in_query in keywords_in_query:
            keywords_in_dict = self.keywords_search(keyword_in_query, top_k)
            for item in keywords_in_dict:
                keyword = item["disease_name"]
                keyword_similarities[keyword] = item["similarity"]  # Record the similarity of keywords
                or_expression_list.append({"related_disease_1": keyword})
                or_expression_list.append({"related_disease_2": keyword})

        if not or_expression_list:
            return {}

        results = self.collection.get(where={"$or": or_expression_list})
        # Add similarity information to the keyword search results
        if results.get("metadatas"):
            for i, meta in enumerate(results["metadatas"]):
                # Find the matching keywords and obtain the similarity
                matched_keyword = next(
                    (k for k in keyword_similarities if k in [meta.get("related_disease_1"), meta.get("related_disease_2")]),
                    None
                )
                if matched_keyword:
                    # Keyword search score: Normalized to the same order of magnitude as vector distance (the higher, the more relevant)
                    results.setdefault("similarities", []).append(keyword_similarities[matched_keyword])
                else:
                    results.setdefault("similarities", []).append(0.0)
        return results

    def hybrid_retrieve(self, query: str, top_k: int = 5) -> Dict:
        """Optimized hybrid retrieval: Unified score dimension, weighted fusion, strict deduplication, and quantity control"""
        # 1. Perform two types of retrieval in parallel (true parallelism can be achieved in actual projects using concurrent.futures)
        vector_results = self.vector_retrieve(query, top_k)
        keywords_results = self.keywords_retrieve(query)

        # 2. Standardize the format of vector retrieval results
        vector_hits = []
        if vector_results.get("ids") and vector_results["ids"][0]:
            for idx, doc_id in enumerate(vector_results["ids"][0]):
                # Vector distance normalization (converted to the 0-1 range, the smaller the value, the more relevant
                normalized_dist = min(vector_results["distances"][0][idx] / self.vector_distance_max, 1.0)
                vector_hits.append({
                    "id": doc_id,
                    "document": vector_results["documents"][0][idx],
                    "metadata": vector_results["metadatas"][0][idx],
                    "score": 1 - normalized_dist,  # Convert to a similarity score (the higher, the more relevant)
                    "source": "vector"
                })

        # 3. Standardize the format of keyword search results
        keyword_hits = []
        if keywords_results.get("ids"):
            for idx, doc_id in enumerate(keywords_results["ids"]):
                # The keyword score has been calculated in keywords_retrieve (range 0-1).
                keyword_hits.append({
                    "id": doc_id,
                    "document": keywords_results["documents"][idx],
                    "metadata": keywords_results["metadatas"][idx],
                    "score": keywords_results["similarities"][idx],
                    "source": "keyword"
                })

        # 4. Fusion result (de-duplication + weighting
        merged = {}
        for hit in vector_hits + keyword_hits:
            doc_id = hit["id"]
            if doc_id not in merged:
                merged[doc_id] = hit
            else:
                # Perform score fusion on duplicate documents (vector retrieval has a higher weight)
                merged[doc_id]["score"] = 0.7 * merged[doc_id]["score"] + 0.3 * hit["score"]
                merged[doc_id]["source"] = "hybrid"

        # 5. Sort by score and truncate to top_k
        sorted_hits = sorted(merged.values(), key=lambda x: x["score"], reverse=True)[:top_k]

        # 6. Convert to the standard output format
        return {
            "ids": [hit["id"] for hit in sorted_hits],
            "documents": [hit["document"] for hit in sorted_hits],
            "metadatas": [hit["metadata"] for hit in sorted_hits],
            "distances": [1 - hit["score"] for hit in sorted_hits]  # Switch back to the distance format (the lower, the more relevant
        }


    def chinese_tokenizer(self, text: str) -> List[str]:
        return jieba.lcut(text)
    def bm25_retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        The BM25 model is used for retrieval to return results including text, score, and ask and title in metadata.
        
        :param query: The query string input by the user
        :param top_k: The number of Top-K results returned
        :return: A list containing text, score, ask, and title
        """
        results = self.hybrid_retrieve(query, 2 * top_k)
        
        # Prepare a document with complete metadata (retain the original metadata for extracting ask and title later)
        documents = []
        for meta in results["metadatas"]:
            # Store the complete metadata in the metadata field of the Document
            doc = Document(
                text=meta["answer"],  # The document content uses the "answer" field
                metadata={
                          "ask":meta["ask"],
                          "department":meta["department"]
                          }  # Retain the original complete metadata
            )
            documents.append(doc)
        
        # Document partitioning (the original metadata will still be inherited after partitioning)
        splitter = SentenceSplitter(chunk_size=1024)
        nodes = splitter.get_nodes_from_documents(documents)
        
        # Initialize the BM25 searcher
        retriever = BM25Retriever.from_defaults(
            nodes=nodes,
            tokenizer=self.chinese_tokenizer,
            similarity_top_k=top_k
        )
        
        # Perform a search
        bm25_nodes = retriever.retrieve(query)
        
        # Construct the final result: Extract ask and title from text, score, and metadata
        results_with_info = []
        for node in bm25_nodes:
            results_with_info.append({
                "text": node.text,  # The text content after being divided into blocks
                "similarity":node.score,
                "department":node.metadata.get("department",""),
                "ask": node.metadata.get("ask",""),  # Extract ask from the metadata
            })
        return results_with_info
    def retrieve(self, retrieval_type: str, query: str, **kwargs) -> List[Dict]:
        """Unified Search Interface (Scheduler
        Args:
            retrieval_type: Search type, optional value：vector/keywords/hybrid/bm25
            query: User queries text
            **kwargs: Other parameters (such as top_k, only supported by vector/hybrid)
        Returns:
            Search results (Format may vary slightly by type, see specific methods)
        """
        # Extract general parameters (the default value of top_k is adjusted according to the search type)
        top_k = kwargs.get("top_k", 5)
        # Match the retrieval type and call the corresponding method
        if retrieval_type == RetrievalMethod.VECTOR.value:
            query_results = self.vector_retrieve(query, top_k=top_k)
            metadatas = query_results.get("metadatas", [[]])[0]
            distances = query_results.get("distances", [[]])[0]
            
            results=[]
            # Traverse the results and combine the required fields
            for meta, distance in zip(metadatas, distances):
                filtered_item = {
                    "ask": meta.get("ask", ""),       # Extract ask from the metadata
                    "answer": meta.get("answer", ""), # Extract the answer from the metadata
                    "department": meta.get("department", ""),
                    "similarity": distance              # Add distance information
                }
            results.append(filtered_item)
            return results
        elif retrieval_type == RetrievalMethod.HYBRID.value:
            hybrid_results = self.hybrid_retrieve(query, top_k=top_k)
            # Handle the format of mixed search results
            metadatas = hybrid_results.get("metadatas", [])
            distances = hybrid_results.get("distances", [])
            
            results = []
            for meta, distance in zip(metadatas, distances):
                filtered_item = {
                    "ask": meta.get("ask", ""),
                    "answer": meta.get("answer", ""),
                    "department": meta.get("department", ""),
                    "similarity": distance
                }
                results.append(filtered_item)
            return results
        elif retrieval_type == RetrievalMethod.BM25.value:
            return self.bm25_retrieve(query, top_k=top_k)
        else:
            raise ValueError(f"Unsupported search types：{retrieval_type}，Optional value：vector/keywords/hybrid/bm25")
    
if __name__ == "__main__":
    query = "What are the symptoms of diabetes？"
    top_k = 3
    retriever = Retrieval(query_constructor= QueryConstructor())
    query_constructor = QueryConstructor()
    results = retriever.retrieve(RetrievalMethod.BM25.value,query,top_k = 3)
    for i in range(len(results)):
        print(f"{i+1}.{results[i]}\n")
