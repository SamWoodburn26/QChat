import os
import time
import re
import json
from pathlib import Path
from typing import List, Optional, Tuple

import requests
import bs4
from tqdm import tqdm

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings, ChatOllama

from .profanity_filter import sanitize_text
from .profile_service import get_profile_context


# paths
BASE_DIR = Path(__file__).parent
DEFAULT_URLS_TXT = BASE_DIR / "qu_docs.txt"
DEFAULT_INDEX_DIR = BASE_DIR / "faiss_index"


# Load settings from local.settings.json if environment variable not set
def _load_local_settings():
    """Load configuration from local.settings.json if it exists."""
    try:
        settings_path = BASE_DIR.parent / "local.settings.json"
        if settings_path.exists():
            with open(settings_path, 'r') as f:
                data = json.load(f)
                return data.get('Values', {})
    except Exception as e:
        print(f"[RAG] Could not load local.settings.json: {e}")
    return {}

_LOCAL_SETTINGS = _load_local_settings()

def _get_setting(key: str, default: str) -> str:
    """Get setting from environment or local.settings.json."""
    return os.getenv(key) or _LOCAL_SETTINGS.get(key, default)


# config
USER_AGENT = _get_setting("QCHAT_USER_AGENT", "QChatIndexer/1.0")
REQUEST_TIMEOUT = float(_get_setting("QCHAT_REQUEST_TIMEOUT", "12"))
SLEEP_EVERY_N = int(_get_setting("QCHAT_SLEEP_EVERY_N", "25"))
SLEEP_SECONDS = float(_get_setting("QCHAT_SLEEP_SECONDS", "0.5"))
CHUNK_SIZE = int(_get_setting("QCHAT_CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(_get_setting("QCHAT_CHUNK_OVERLAP", "150"))
EMBED_MODEL = _get_setting("QCHAT_EMBED_MODEL", "nomic-embed-text")

# If you want to reject irrelevant retrievals in chat:
USE_SCORE_THRESHOLD = _get_setting("QCHAT_USE_SCORE_THRESHOLD", "false").lower() == "true"
# note: faiss score meaning varies; treat this as "tunable"
SCORE_THRESHOLD = float(_get_setting("QCHAT_SCORE_THRESHOLD", "0.9"))

DEBUG_RETRIEVAL = _get_setting("QCHAT_DEBUG_RETRIEVAL", "false").lower() == "true"

# LLM Configuration
OLLAMA_URL = _get_setting("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = _get_setting("OLLAMA_MODEL", "mistral:latest")
_NUM_CTX = int(_get_setting("OLLAMA_NUM_CTX", "2048"))
_NUM_PREDICT = int(_get_setting("OLLAMA_NUM_PREDICT", "256"))

print(f"[RAG] Using Ollama at: {OLLAMA_URL}")


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


def read_urls(txt_path: Path = DEFAULT_URLS_TXT) -> List[str]:
    # read URLs from a text file, preserve order
    if not txt_path.exists():
        raise FileNotFoundError(f"URLs file not found: {txt_path}")
    # all urls
    raw = []
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            u = line.strip()
            if u.startswith("http://") or u.startswith("https://"):
                raw.append(u)
    # ensure there are no duplicates
    seen = set()
    out = []
    for u in raw:
        if u not in seen:
            out.append(u)
            seen.add(u)
    return out

# read through the url to get the text
def _clean_html_to_text(html: str) -> str:
    soup = bs4.BeautifulSoup(html, "html.parser")
    # remove html elements before extracting the text
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    # get text
    text = soup.get_text(separator="\n", strip=True)
    # basic whitespace cleanup (keep line breaks)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # return cleaned text
    return text


# fetch and extract visible text from usable urls, returns None if empty/unusable.
def fetch_url_text(url: str) -> Optional[str]:
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    # if blocked or forbidden skip
    if r.status_code != 200:
        return None
    # get text from the page
    text = _clean_html_to_text(r.text)
    # skip pages that are basically empty or likely login pages
    if not text or len(text) < 150:
        return None
    # detect common sign-in page patterns
    lower = text.lower()
    if "sign in" in lower and "password" in lower and "microsoft" in lower:
        # likely private SharePoint redirect / auth page
        return None
    # return text
    return text

# build faiss index and save to disk, returns num_pages_ingested and num_chunks
def build_index(urls_txt: Path = DEFAULT_URLS_TXT, index_dir: Path = DEFAULT_INDEX_DIR, max_urls: Optional[int] = None,) -> Tuple[int, int]:
    # get urls
    urls = read_urls(urls_txt)
    if max_urls is not None:
        urls = urls[:max_urls]

    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_URL)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    # to store all url info
    docs: List[Document] = []
    ok = 0
    # loop through each url and build index
    print(f"[RAG] Building index from {len(urls)} URLs...")
    with tqdm(total=len(urls), desc="Fetching URLs", unit="url") as pbar:
        for i, url in enumerate(urls):
            try:
                # get text from the url
                page_text = fetch_url_text(url)
                if not page_text:
                    pbar.update(1)
                    continue
                # add content to docs
                docs.append(Document(page_content=page_text, metadata={"source": url}))
                ok += 1
                pbar.set_postfix({"success": ok, "failed": i + 1 - ok})
            # if you cant fetch content from the url
            except Exception as e:
                print(f"\n[RAG] fetch failed: {url} | {repr(e)}")
            finally:
                pbar.update(1)
            # sleep
            if SLEEP_EVERY_N and (i + 1) % SLEEP_EVERY_N == 0:
                time.sleep(SLEEP_SECONDS)
    # error handeling
    if not docs:
        raise RuntimeError("[RAG] No documents ingested. Check URLs and scraping access.")
    # split into chunks
    print(f"\n[RAG] Splitting {ok} documents into chunks...")
    splits = splitter.split_documents(docs)
    print(f"[RAG] Created {len(splits)} chunks from {ok} pages")
    # build + save
    print(f"[RAG] Building FAISS index with {len(splits)} chunks (this may take a while)...")
    store = FAISS.from_documents(splits, embeddings)
    index_dir.mkdir(parents=True, exist_ok=True)
    print(f"[RAG] Saving index to disk...")
    store.save_local(str(index_dir))
    print(f"[RAG] ✓ Successfully saved FAISS index to: {index_dir}")
    # return num_pages_ingested and num_chunks
    return ok, len(splits)


# load the faiss index from disk
def load_index(index_dir: Path = DEFAULT_INDEX_DIR) -> FAISS:
    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_URL)
    return FAISS.load_local(
        str(index_dir),
        embeddings,
        allow_dangerous_deserialization=True,
    )


# cache vector store per process (fast for Azure Functions)
_VECTOR_STORE: Optional[FAISS] = None


# get vector store
def get_vector_store(index_dir: Path = DEFAULT_INDEX_DIR) -> FAISS:
    global _VECTOR_STORE
    if _VECTOR_STORE is None:
        if not index_dir.exists():
            raise FileNotFoundError(
                f"[RAG] FAISS index not found at {index_dir}. "
                f"Run build_index() first (nightly job) or build locally."
            )
        _VECTOR_STORE = load_index(index_dir)
        print("[RAG] FAISS index loaded.")
    return _VECTOR_STORE


def retrieve(question: str, k: int = 6) -> List[Document]:
    store = get_vector_store()
    if USE_SCORE_THRESHOLD:
        docs_and_scores = store.similarity_search_with_score(question, k=k)
        filtered = [d for (d, score) in docs_and_scores if score < SCORE_THRESHOLD]
        if DEBUG_RETRIEVAL:
            for d, score in docs_and_scores:
                print("\n--- RETRIEVED ---")
                print("score:", score, "source:", d.metadata.get("source"))
                print(d.page_content[:350])
        return filtered[:k]
    else:
        docs = store.similarity_search(question, k=k)
        if DEBUG_RETRIEVAL:
            for d in docs:
                print("\n--- RETRIEVED ---")
                print("source:", d.metadata.get("source"))
                print(d.page_content[:350])
        return docs


def answer_with_rag(question: str, username: Optional[str] = None) -> dict:
    """
    Legacy function for backward compatibility. 
    Uses the new vector store retrieval system.
    """
    # handle greeting - only if it's JUST a greeting
    question_check = re.sub(r'[!?.,:;]+', '', question.strip().lower())
    words = question_check.split()
    greeting_words = {'hi', 'hello', 'hey', 'hii', 'sup', 'what\'s', 'up', 'whats', 'there'}
    
    if len(words) <= 3 and all(word in greeting_words for word in words):
        return {"reply": "Hi! I'm QChat. Ask me anything about Quinnipiac!", "sources": []}

    try:
        # Get user profile context if username provided
        user_context = ""
        if username:
            user_context = get_profile_context(username)
            if user_context:
                user_context = user_context + "\n\n"
        
        # Use vector store retrieval
        try:
            docs = retrieve(question, k=4)
        except FileNotFoundError:
            # Fallback if index not built yet
            return {
                "reply": "I'm still learning about Quinnipiac. The knowledge base is being built. Please try again soon!",
                "sources": []
            }
        
        if not docs:
            return {
                "reply": "I couldn't find current info on that. Try asking about dining, events, or housing!",
                "sources": []
            }

        # Build context from retrieved documents
        context = ""
        sources = []
        for doc in docs:
            source_url = doc.metadata.get("source", "Unknown")
            context += f"\n\n--- From {source_url} ---\n{doc.page_content}"
            if source_url not in sources:
                sources.append(source_url)

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
            "sources": []
        }


# Optional: if you want this file to be runnable manually
if __name__ == "__main__":
    # Example: build full index
    build_index(DEFAULT_URLS_TXT, DEFAULT_INDEX_DIR)
