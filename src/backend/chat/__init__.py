# ollama to make the gemma model
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.prompts import ChatPromptTemplate

import azure.functions as func
import json, os

from .RAG import store_from_txt

# for ollama llm model and embeddings
llm = ChatOllama(model="mistral:latest", base_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"))
embeddings = OllamaEmbeddings(model="nomic-embed-text");

# prompt to only use given context
prompt_template = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful assistant. Use ONLY the provided context to answer.\n"
     "If the answer is not in the provided context, say: 'I don't know.' Do not guess."),
    ("human", "Context:\n{context}\n\nQuestion: {question}")
])

_vector_store = None

# get vector store using RAG.py function and qu_docs txt files
def get_vector_store():
    global _vector_store
    if _vector_store is None:
        _vector_store = store_from_txt("qu_docs.txt")
    return _vector_store


# answer using rag
def answer_with_rag(question:str) -> dict:
    vector_store = get_vector_store()
    docs = vector_store.similarity_search(question, k=4)
    ctx = "\n\n".join(d.page_content for d in docs)
    reply = llm.invoke(prompt_template.invoke({"context": ctx, "question": question})).content.strip()
    sources = [d.metadata.get("source") for d in docs if d.metadata.get("source")]
    print(f"Retrieved {len(docs)} docs from {len(sources)} sources")
    return {"reply": reply, "sources": sources}


def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.method == "OPTIONS":
        response = func.HttpResponse("")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    print("main called")
    try:
        body = req.get_json()
    except ValueError:
        body = {}

    q = (req.params.get("message") or body.get("message") or "").strip()
    if not q:
        return func.HttpResponse('{"error":"missing message"}', status_code=400, mimetype="application/json")

    try:
        reply = answer_with_rag(q)
    except Exception as e:
        print("RAG error: ", repr(e))
        reply = {"reply": "I don't know.", "sources":[]}

    response = func.HttpResponse(
        json.dumps(reply),
        mimetype="application/json"
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"

    return func.HttpResponse(json.dumps(reply), mimetype="application/json")