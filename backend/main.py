from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, List

# Consistent with the user example: Imported from rag_pipeline
from pipeline import retrieve_and_generate

app = FastAPI()


class Query(BaseModel):
    question: str


@app.post("/api/user/ask")
async def ask_question(query: Query) -> Dict[str, Any]:
    answer, context = retrieve_and_generate(query.question)
    return {"answer": answer, "context": context}
