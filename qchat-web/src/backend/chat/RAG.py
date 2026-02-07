
import os
import time
import re
from pathlib import Path
from typing import List, Optional, Tuple

import requests
import bs4

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings


# paths
BASE_DIR = Path(__file__).parent
DEFAULT_URLS_TXT = BASE_DIR / "qu_docs.txt"
DEFAULT_INDEX_DIR = BASE_DIR / "faiss_index"


# config
USER_AGENT = os.getenv("QCHAT_USER_AGENT", "QChatIndexer/1.0")
REQUEST_TIMEOUT = float(os.getenv("QCHAT_REQUEST_TIMEOUT", "12"))
SLEEP_EVERY_N = int(os.getenv("QCHAT_SLEEP_EVERY_N", "25"))
SLEEP_SECONDS = float(os.getenv("QCHAT_SLEEP_SECONDS", "0.5"))
CHUNK_SIZE = int(os.getenv("QCHAT_CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("QCHAT_CHUNK_OVERLAP", "150"))
EMBED_MODEL = os.getenv("QCHAT_EMBED_MODEL", "nomic-embed-text")

# If you want to reject irrelevant retrievals in chat:
USE_SCORE_THRESHOLD = os.getenv("QCHAT_USE_SCORE_THRESHOLD", "false").lower() == "true"
# note: faiss score meaning varies; treat this as “tunable”
SCORE_THRESHOLD = float(os.getenv("QCHAT_SCORE_THRESHOLD", "0.9"))

DEBUG_RETRIEVAL = os.getenv("QCHAT_DEBUG_RETRIEVAL", "false").lower() == "true"


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

    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    # to store all url info
    docs: List[Document] = []
    ok = 0
    # loop through each url and build index
    print(f"[RAG] Building index from {len(urls)} URLs...")
    for i, url in enumerate(urls):
        try:
            # get text from the url
            page_text = fetch_url_text(url)
            if not page_text:
                continue
            # add content to docs
            docs.append(Document(page_content=page_text, metadata={"source": url}))
            ok += 1
        # if you cant fetch content from the url
        except Exception as e:
            print(f"[RAG] fetch failed: {url} | {repr(e)}")
        # sleep
        if SLEEP_EVERY_N and (i + 1) % SLEEP_EVERY_N == 0:
            time.sleep(SLEEP_SECONDS)
    # error handeling
    if not docs:
        raise RuntimeError("[RAG] No documents ingested. Check URLs and scraping access.")
    # split into chunks
    splits = splitter.split_documents(docs)
    print(f"[RAG] Ingested pages: {ok} | Chunks: {len(splits)}")
    # build + save
    store = FAISS.from_documents(splits, embeddings)
    index_dir.mkdir(parents=True, exist_ok=True)
    store.save_local(str(index_dir))
    print(f"[RAG] Saved FAISS index to: {index_dir}")
    # return num_pages_ingested and num_chunks
    return ok, len(splits)


# load the faiss index from disk
def load_index(index_dir: Path = DEFAULT_INDEX_DIR) -> FAISS:
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
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
    
# 


# Optional: if you want this file to be runnable manually
if __name__ == "__main__":
    # Example: build full index
    build_index(DEFAULT_URLS_TXT, DEFAULT_INDEX_DIR)
