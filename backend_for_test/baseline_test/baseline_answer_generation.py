from __future__ import annotations

"""
baseline_answer_generation.py

Function:
  - Generate the answer only based on the question itself using a "common large model" (here using Zhipu GLM-4.5-flash)
  - Do not use any retrieved documents as context
  - output JSON: generated_plain_answers.json
      [
        {
          "id": rag_generate_and_ragas_test,
          "user_input": "...",
          "response": "...",
          "retrieved_contexts": []   # Note: The baseline does not need to be retrieved; it is an empty list here
        },
        ...
      ]

dependency:
    pip install "zhipuai>=2.0.0"

Environmental variable:
    We recommend setting the environment variable ZHIPUAI_API_KEY to your Zhipu API key.
    Or you can directly write the key to the ZHIPU_API_KEY below
"""

import json
import os
from typing import Any, Dict, List

try:
    from zhipuai import ZhipuAI
except ImportError:
    ZhipuAI = None  # type: ignore


# ====== rag_generate_and_ragas_test. Configuration area ============================================

REWRITTEN_QUERY_PATH = "rewritten_query.json"
OUTPUT_PATH = "generated_plain_answers.json"

# SmartSpectrum API Key: Environment variables are preferred, but you can also hardcode it into a string.
ZHIPU_API_KEY = os.getenv("ZHIPUAI_API_KEY") or "d0b8bc52cf6b4c368982dfdd32384757.UcWBjZr72H7AWgyN"
ZHIPU_MODEL = "glm-4.5-flash"

# =============================================================


class ZhipuLLMClient:
    """Here's a simple wrapper around the GLM chat interface."""

    def __init__(self, api_key: str, model: str = ZHIPU_MODEL) -> None:
        if ZhipuAI is None:
            raise ImportError("If zhipuai is not installed, please run it first.: pip install zhipuai")

        if (not api_key) or "在这里填你的智谱APIKey" in api_key:
            raise ValueError(
                "No Zhipu API Key provided. Please set the environment variable ZHIPUAI_API_KEY."
                "Alternatively, enter your key in ZHIPU_API_KEY at the top of this file."
            )

        self._client = ZhipuAI(api_key=api_key)
        self._model = model

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        return resp.choices[0].message.content.strip()  # type: ignore[attr-defined]


def load_rewritten_queries(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"{path} The top-level JSON must be a list.")

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"The record {idx} in {path} is not an object (dict).")
        if "id" not in item or "rewritten_query" not in item:
            raise ValueError(
                f"The record {idx} in {path} is missing the id or rewritten_query field."
            )

    return data


def build_plain_system_prompt() -> str:
    """System prompts used for common large models (non-RAG)."""
    return (
        "你是一个谨慎的中文全科医生助理。\n"
        "现在不会给你任何检索到的问诊记录或文献，只能依靠你的一般医学知识做出解释和建议。\n"
        "要求：\n"
        "rag_generate_and_ragas_test. 给出的是健康教育性质的建议，而不是正式诊断或处方；\n"
        "2. 避免给出具体药品剂量、疗程等处方级用药方案；\n"
        "3. 如存在不确定性，要明确说明，并建议在有需要时尽快线下就医或咨询专科医生；\n"
        "4. 使用通俗、礼貌、结构清晰的中文回答，适合普通患者阅读；\n"
        "5. 在回答结尾加一句温馨提示，如：如症状持续或加重，请及时就医。"
    )


def build_user_prompt(question: str) -> str:
    """Simply package the user's question and send it to the large model."""
    return (
        "患者的提问如下：\n"
        f"{question.strip()}\n\n"
        "请根据你的医学常识，结合临床常见情况，用清晰的分点形式回答，"
        "说明可能的原因、建议的生活方式调整，以及在什么情况下需要尽快就医或进一步检查。"
    )


def main() -> None:
    print("=== Baseline: Generate answers for general large models ===\n")

    # rag_generate_and_ragas_test. 读取 rewritten_query.json
    try:
        queries = load_rewritten_queries(REWRITTEN_QUERY_PATH)
    except Exception as e:
        print(f"[BASELINE] read {REWRITTEN_QUERY_PATH} 失败：{e}")
        return

    print(f"[BASELINE] successfully read {len(queries)}  rewritten_query.")

    # 2. Initialize the GLM client
    try:
        llm = ZhipuLLMClient(api_key=ZHIPU_API_KEY)
    except Exception as e:
        print("[BASELINE] Initialization of ZHIPU LLM failed:", e)
        return

    system_prompt = build_plain_system_prompt()

    results: List[Dict[str, Any]] = []

    # 3. Generate answers one by one
    for item in queries:
        qid = item["id"]
        question = item["rewritten_query"]

        print(f"\n[BASELINE] In generating the {qid}th answer...")
        user_prompt = build_user_prompt(question)

        try:
            answer = llm.chat(system_prompt=system_prompt, user_prompt=user_prompt)
        except Exception as e:
            print(f"[BASELINE] The LLM call failed (id={qid}): {e}")
            answer = f"[ERROR] Model call failed:{e}"

        results.append(
            {
                "id": qid,
                "user_input": question,
                "response": answer,
                "retrieved_contexts": [],  # baseline No need to search
            }
        )

    # 4. save as generated_plain_answers.json
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[BASELINE] The answers for the regular large model have been saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
