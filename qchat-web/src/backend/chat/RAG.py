
import random
from urllib.parse import unquote, urlparse
from langchain_core.prompts import ChatPromptTemplate
import os
import re
from bs4 import BeautifulSoup
from langchain_ollama import ChatOllama, OllamaEmbeddings
import requests
from .profanity_filter import sanitize_text

# greetings to aviod rag answering
GREETINGS_LIST = re.compile(r"\b(hi|hello|hey|hii|sup|what'?s up)\b", re.IGNORECASE)
# stop words and punctuation
STOPWORDS = {"the","a","an","and","or","to","of","in","on","for","with","is","are","was","were","it","this","that","i","you","we","they","my","your","our","at","from","by","as","about","please","can","could","would","tell","me","what","when","where","how"}
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

# get the important words/ tokenize
def tokenize(q:str) -> list[str]:
    q = q.lower
    q = re.sub(r"[^a-z0-9\s]", " ", q)
    # tokens = words not in stopwords (fillers) and length greater than 2
    tokens = [t for t in q.split() if t and t not in STOPWORDS and len(t)>2]
    return tokens

def url_tokens(url: str) -> set[str]:
    p = urlparse(url)
    path = unquote(p.path.lower())
    #split on / - _ .
    parts = re.split(r"[\/\-_\.]+", path)
    return {x for x in parts if x and len(x)>2}

# scoring function to rank urls and break ties randomly
def rank_urls(question: str, urls: list[str], k: int=5) -> list[str]:
    print("ranking urls")
    q_tokens = tokenize(question)
    if not q_tokens:
        return urls[:k]
    # loop through each url and get a list of urls matching the tokens
    scored = []
    for url in urls:
        u_tokens = url_tokens(url)
        # number of keyword matches
        hits = sum(1 for t in q_tokens if t in u_tokens)
        if hits > 0:
            scored.append((url, hits))
    # if no urls are found get random (this could be improved but is better than just the first few)
    if not scored:
        return random.sample(urls, min(k, len(urls)))
    # sort by hits descending, then shuffle within ties
    scored.sort(key=lambda x: x[1], revers = True)
    top_score = scored[0][1]
    top_bucket = [u for u, s in scored if s == top_score]
    rest = [u for u, s in scored if s != top_score]
    random.shuffle(top_bucket)
    # return
    return (top_bucket + rest)[:k]
        

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
     "- NEVER make up or modify the links given, provide the exact link without any adjustments.\n"
     "- assume the student is an undergraduate living on Mount Carmel, unless otherwise told. \n"
     "Formatting rules:\n"
     "- Use short paragraphs\n"
     "- Use bullet points for lists\n"
     "- Use headings when appropriate\n"
     "- Do NOT return one long block of text\n"
     "- Preserve line breaks\n"
     "- When there is a numbered list seperate each number with a new line"),
    ("human", "Context:\n{context}\n\nUser: {question}")
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

def answer_with_rag(question: str) -> dict:
    # handle greeting
    if GREETINGS_LIST.search(question.strip()):
        return {"reply": "Hi! I'm QChat. Ask me anything about Quinnipiac!", "sources": []}

    try:
        '''
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
        '''
        #top_urls = [url for url, _ in candidates[:4]]
        top_urls = rank_urls(question, QU_DOCS_URLS, k=5)

        for url in top_urls:
            print(url)

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
                # Keep some line breaks to encourage better formatting in the LLM output.
                text = soup.get_text(separator="\n", strip=True)
                clean = re.sub(r"[ \t]+", " ", text)[:5000]
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
        def _format_reply(text: str) -> str:
            text = text.strip().replace("\r\n", "\n").replace("\r", "\n")
            # Put numbered list items on their own lines.
            text = re.sub(r"(?<!\n)(\d+\.)\s+", r"\n\1 ", text)
            # Put bullet items on their own lines.
            text = re.sub(r"(?<!\n)([•*-])\s+", r"\n\1 ", text)
            # If the model still returns a single paragraph, split on sentences.
            if "\n" not in text:
                text = re.sub(r"(?<=[.!?])\s+", "\n", text)
            # Limit excessive vertical whitespace.
            return re.sub(r"\n{3,}", "\n\n", text)

        try:
            reply = llm.invoke(prompt_template.invoke({
                "context": context,
                "question": question
            })).content.strip()
            reply = sanitize_text(reply)
            reply = _format_reply(reply)
        except Exception as e:
            print("LLM error:", e)
            reply = "I'm having trouble thinking right now."

        return {
            "reply": reply or ", no information found in given resources.",
            "sources": sources[:5]
        }

    except Exception as e:
        print("RAG error:", e)
        return {
            "reply": "Sorry, I'm having trouble right now.",
            "sources": []  # ← ALWAYS INCLUDE
        }
