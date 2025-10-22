# ollama to make the gemma model
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.prompts import ChatPromptTemplate

import azure.functions as func
import json, os, requests

# for ollama
llm = ChatOllama(model="mistral:latest", base_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),);
embeddings = OllamaEmbeddings(model="mistral:latest");
vector_store = InMemoryVectorStore(embeddings);


prompt_template = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful assistant. Use ONLY the provided context to answer.\n"
     "If the answer is not in the context, say: 'I don't know.' Do not guess."),
    ("human", "Context:\n{context}\n\nQuestion: {question}")
])

def main(req: func.HttpRequest) -> func.HttpResponse:
    msg = (req.params.get("message") or "").strip()
    if not msg:
        try:
            body = req.get_json()
        except ValueError:
            body = {}
        msg = (body.get("message") or "").strip()
    
    if not msg:
        return func.HttpResponse('{"error":"missing message"}', status_code=400, mimetype="application/json")

    try:
        reply = llm.invoke(msg).content.strip()
    except Exception as e:
        print("LLM error: ", repr(e))
        reply = "local model is unavailable"

    return func.HttpResponse(json.dumps({"reply": reply}), mimetype="application/json")