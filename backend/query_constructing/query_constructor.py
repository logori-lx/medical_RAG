from zai import ZhipuAiClient
import os
from collections import deque
from typing import List, Dict

API_KEY = os.getenv("MEDICAL_RAG")
REWRITTEN_QUERY_CACHE_SIZE = 10


class QueryConstructor:
    def __init__(self, api_key=API_KEY):
        self.client = ZhipuAiClient(api_key=api_key)
        self._rewritten_query_cache_dict = {}
        self._rewritten_query_cache_queue = deque()

    def _update_rewritten_query_cache(self, query, rewritten_query):
        if len(self._rewritten_query_cache_dict) == REWRITTEN_QUERY_CACHE_SIZE:
            key = self._rewritten_query_cache_queue.popleft()
            del self._rewritten_query_cache_dict[key]
        self._rewritten_query_cache_dict[query] = rewritten_query
        self._rewritten_query_cache_queue.append(query)

    def _rewritten_query(self, query: str):
        """
        Transform user's colloquial health inquiry into a professional medical search query
        """
        prompt = f"""
        You are a professional medical terminology and clinical language optimization assistant. Your task is to rewrite the user's health inquiry or symptom description into a form that conforms to medical standards and is suitable for searching in a professional medical knowledge base.

        Please follow these principles:
        1. **Terminology Standardization**: Convert colloquial body parts or symptom descriptions into standard medical terms (e.g., "sore throat" → "pharyngalgia", "diarrhea" → "diarrhea").
        2. **Key Element Extraction**: Retain key symptoms, duration, triggers, and accompanying symptoms; remove irrelevant emotional expressions (e.g., "I'm worried", "help!").
        3. **Logical Clarity**: If multiple symptoms are included, organize them into a coherent clinical statement.
        4. **Neutral and Objective**: Maintain an objective tone, do not change the original meaning, do not diagnose (do not invent diseases unless the user specifically asks about a particular disease).
        5. **Strict Constraints**: Do not include any explanations, prefixes, or suffixes; only return the rewritten sentence.

        Original query: {query}
        """

        try:
            response = self.client.chat.completions.create(
                model="glm-4",  # Or any other medical fine-tuned model you are using
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                # Medical descriptions can be slightly longer than legal phrases, so increase token slightly
                temperature=0.1  # Reduce randomness, ensure precise terminology mapping
            )
            rewritten_query = response.choices[0].message.content.strip()
            return rewritten_query
        except Exception as e:
            print(f"Medical query rewrite failed, using original query: {e}")
            return query

    def get_query(self, query: str):
        rewritten_query = self._rewritten_query_cache_dict.get(query)
        if rewritten_query == None:
            rewritten_query = self._rewritten_query(query)
            self._update_rewritten_query_cache(query, rewritten_query)
        return rewritten_query

    def extract_category(self, query):
        response = self.client.chat.completions.create(
            model="GLM-4.5-AirX",
            messages=[
                {
                    "role": "system",
                    "content": "You are a medical expert. Extract diseases mentioned in the user's input. " \
                               "For example: " \
                               "User: I want to know the long-term medication risks of epilepsy " \
                               "You: Epilepsy " \
                               "User: Can people with high blood pressure donate blood? " \
                               "You: Hypertension " \
                               "If the user does not mention any disease, output: None " \
                               "If the user mentions multiple diseases, output the two most relevant diseases separated by |. " \
                               "Only output disease names, no other content. Do not add any punctuation other than |."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            temperature=0.6
        )
        content = response.choices[0].message.content.strip()
        content = content.replace("\n", "")
        list_content = content.split("|")
        list_content = [d.strip() for d in list_content]
        return list_content or ["None"]

    from typing import List, Dict, Tuple

    def _build_medical_qa_prompt(self, question: str, passages: List[Dict]) -> Tuple[str, str]:
        """
        Return (system_prompt, user_prompt).
        Scenario: Medical consultation for general users.
        Data source: Similar historical doctor-patient Q&A [{"ask": "...", "answer": "..."}].
        """

        def _format_qa_context(passages: List[Dict]) -> str:
            """
            Helper function: format [{"ask":..., "answer":...}] into readable string blocks
            """
            formatted = []
            for i, p in enumerate(passages, 1):
                # Extract ask and answer, handle possibly missing fields
                ask_text = p.get('ask', '').strip()
                answer_text = p.get('answer', '').strip()

                # Truncate overly long text to save tokens (optional)
                if len(ask_text) > 100: ask_text = ask_text[:100] + "..."
                if len(answer_text) > 300: answer_text = answer_text[:300] + "..."

                entry = (
                    f"[Case ID: {i}]\n"
                    f"  - Patient question: {ask_text}\n"
                    f"  - Doctor answer: {answer_text}\n"
                )
                formatted.append(entry)

            return "\n".join(formatted)

        # 1. Format context: specifically handle ask/answer structure
        context_block = _format_qa_context(passages) if passages else "(No similar cases or doctor answers retrieved)"

        # 2. System Prompt: define persona, safety boundaries, and language style
        system_prompt = (
            "You are a professional, warm, and rigorous intelligent medical assistant. Your task is to answer the user's inquiry based on retrieved historical doctor-patient Q&A data.\n"
            "**Core Principles**:\n"
            "- **Role Definition**: You are not a doctor and cannot provide definitive diagnoses. Your answers are for reference only and do not replace in-person medical consultation.\n"
            "- **Evidence Priority**: Must summarize based on the retrieved 'doctor answers'; do not go beyond the reference material.\n"
            "- **Easy to Understand**: Users are laypeople; convert medical terms into plain language (e.g., 'upper respiratory infection' → 'cold').\n"
            "- **Safety Red Line**: If the user describes critical conditions (e.g., chest pain, difficulty breathing, severe trauma), recommend immediate medical attention rather than just medication.\n"
            "- **No Fabrication**: Do not invent drug names or treatment plans that are not present in the retrieved material.\n"
        )

        # 3. User Prompt: guide answer logic and citation format
        user_prompt = (
            f"User's current inquiry:\n{question}\n\n"
            f"Retrieved similar doctor-patient Q&A (for reference only):\n{context_block}\n\n"
            "Please strictly follow these steps to generate the answer:\n"
            "1) Directly answer the user's question in plain language.\n"
            "2) Summarize the retrieved doctors' viewpoints and tell the user how such issues are 'usually handled'.\n"
            "3) If relevant cases exist, only show how they support the statements; ignore unrelated cases.\n"
            "4) Do not output content unrelated to medical advice, and do not add cases beyond the retrieved ones.\n"
        )

        return system_prompt, user_prompt

    def process_medical_query(self, question: str,
                              context: List[Dict],
                              model: str = "glm-4",
                              temperature: float = 1.0,
                              max_tokens: int = 65536) -> str:
        sys_prompt, usr_prompt = self._build_medical_qa_prompt(question, context)
        try:
            resp = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": usr_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            answer = resp.choices[0].message.content.strip()
        except Exception as e:
            # Fallback strategy: do not block the overall process, return brief error message with context
            answer = f"Sorry, an error occurred during generation: {e}. The following are the retrieved related cases for reference."
        return answer


if __name__ == "__main__":
    file_path = "./DATA/"
