
from langchain_core.prompts import ChatPromptTemplate
import os
import re
from bs4 import BeautifulSoup
from langchain_ollama import ChatOllama, OllamaEmbeddings
import requests
from .profanity_filter import sanitize_text
from .profile_service import get_profile_context

# greetings to aviod rag answering
GREETINGS_LIST = re.compile(r"\b(hi|hello|hey|hii|sup|what'?s up)\b", re.IGNORECASE)
# reading qu doc
QU_DOCS_PATH = os.path.join(os.path.dirname(__file__), "qu_docs.txt")
# llm
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")
_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "2048"))
_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "256"))
def _preload_model():
    try:
        # Preload and keep the model warm to reduce first-token latency
        requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={"model": OLLAMA_MODEL, "messages": [], "keep_alive": -1},
            timeout=2,
        )
    except Exception:
        pass

_preload_model()

# LangChain LLM configured to call local Ollama (tuned for speed)
llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_URL,
    temperature=0,
    num_ctx=_NUM_CTX,
    model_kwargs={"num_predict": _NUM_PREDICT},
)

# for ollama llm model and embeddings
#llm = ChatOllama(model="mistral:latest", base_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"))
embeddings = OllamaEmbeddings(model="nomic-embed-text");

# prompt to only use given context
prompt_template = ChatPromptTemplate.from_messages([
    ("system",
     "You are QChat, a helpful assistant for Quinnipiac University.\n"
     "Your job is to answer using ONLY the provided context.\n\n"
     "RULES:\n"
     "- If the answer is in the context → answer clearly and concisely.\n"
     "- If the question is a greeting (hi, hello, hey, etc.) → respond friendly and invite a real question.\n"
     "- If the answer is NOT in the context and NOT a greeting → say: 'I don't know. Try asking about dining, housing, athletics, or MyQ.'\n"
     "- NEVER make up information.\n"
     "- ALWAYS be helpful and positive.\n"
     "- If user profile information is provided, use it to personalize your responses.\n"
     "- Remember details about the user (classes, schedule, preferences) to provide better assistance.\n"),
    ("human", "{user_context}Context:\n{context}\n\nUser: {question}")
])

try:
    with open(QU_DOCS_PATH, "r", encoding="utf-8") as f:
        QU_DOCS_URLS = [
            line.strip()
            for line in f
            if line.strip().startswith("http")
        ]
    print(f"QChat loaded {len(QU_DOCS_URLS)} official Quinnipiac URLs from qu_docs.txt")
except Exception as e:
    print(f"ERROR loading qu_docs.txt: {e}")
    QU_DOCS_URLS = []
# prompt template

# qu docs url

def answer_with_rag(question: str, username: str = None) -> dict:
    # handle greeting
    if GREETINGS_LIST.search(question.strip()):
        return {"reply": "Hi! I'm QChat. Ask me anything about Quinnipiac!", "sources": []}

    try:
        # Get user profile context if username provided
        user_context = ""
        if username:
            user_context = get_profile_context(username)
            if user_context:
                user_context = user_context + "\n\n"
        
        q_lower = question.lower()
        candidates = []

        # rank URLs from qu_docs.txt
        for url in QU_DOCS_URLS:
            score = 0
            url_lower = url.lower()
            if any(k in q_lower for k in ["menu", "dining", "eat", "food"]) and "dining" in url_lower:
                score += 10
            if any(k in q_lower for k in ["event", "calendar", "happening"]) and "event" in url_lower:
                score += 10
            if any(word in url_lower for word in q_lower.split()):
                score += 3
            if score > 0:
                candidates.append((url, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        top_urls = [url for url, _ in candidates[:4]]
        if not top_urls:
            top_urls = QU_DOCS_URLS[:3]

        # fetch content safely
        context = ""
        sources = []
        headers = {"User-Agent": "QChat-Bot/1.0"}

        for url in top_urls:
            try:
                r = requests.get(url, timeout=8, headers=headers)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "html.parser")
                text = soup.get_text(separator=" ", strip=True)
                clean = re.sub(r"\s+", " ", text)[:5000]
                context += f"\n\n--- From {url} ---\n{clean}"
                sources.append(url)
            except Exception as e:
                print(f"Failed to fetch {url}: {e}")
                continue  # ← Keep going!

        #if no context → fallback
        if not context.strip():
            return {
                "reply": "I couldn't find current info on that. Try asking about dining, events, or housing!",
                "sources": []
            }

        # call LLM
        try:
            reply = llm.invoke(prompt_template.invoke({
                "user_context": user_context,
                "context": context,
                "question": question
            })).content.strip()
            reply = sanitize_text(reply)
        except Exception as e:
            print("LLM error:", e)
            reply = "I'm having trouble thinking right now."

        return {
            "reply": reply or "I don't know.",
            "sources": sources[:2]
        }

    except Exception as e:
        print("RAG error:", e)
        return {
            "reply": "Sorry, I'm having trouble right now.",
            "sources": []  # ← ALWAYS INCLUDE
        }