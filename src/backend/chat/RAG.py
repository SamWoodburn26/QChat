import os
# Ensure OpenMP duplicate runtime is tolerated when FAISS (LLVM OMP) mixes with MKL-dependent libs
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_THREADING_LAYER", "SEQUENTIAL")
from pathlib import Path
import time
from typing import List
import bs4
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS


# === CONFIG ===
BATCH_SIZE = 50
SLEEP_BETWEEN_BATCHES = 0.2
# === END CONFIG ===


def resolve_path(relative_path: str)-> Path:
    return Path(__file__).parent / relative_path

# read in all urls 
def read_urls(txt_path: str) -> List[str]:
    # get file path
    file_path = resolve_path(txt_path)

    # if file doesn't exist
    if not file_path.exists():
        raise FileNotFoundError(f"URL not found: {file_path}")
    
    # get array of all urls
    urls = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if not url or not url.startswith(("http://", "https://")):
                continue
            urls.append(url)

    #preserve order
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            out.append(u)
            seen.add(u)
    return out


# get urls and return clean readable text of the entire page
def scrape_text(url: str) -> str:
    # try to load the full page with mno filtering using langchain web base loader
    try:
        loader = WebBaseLoader(web_paths=(url,))
        docs = loader.load()
        # catch for empty page, docs not read
        if not docs or not docs[0].page_content.strip():
            print(f"  Empty page: {url}")
            return ""

        # parse with beautiful soup
        soup = bs4.BeautifulSoup(docs[0].page_content, "html.parser")

        # remove unwanted elements from the doc
        for selector in [
            "script", "style", "nav", "footer", "aside", 
            "header", "iframe", "noscript", "svg", 
            ".advertisement", ".ad", ".sidebar", ".menu"
        ]:
            for tag in soup.select(selector):
                tag.decompose()

        # get text with newlines
        text = soup.get_text(separator="\n", strip=True)

        # filter out very short pages (maybe not needed)
        if len(text) < 100:
            print(f"  Too short (<100 chars): {url}")
            return ""

        # print that scraping was complete and how many characters were saved from the url
        print(f"  Scraped {len(text)} chars from {url}")

        return text
    # exception, failed to load the url to bs4
    except Exception as e:
        print(f"  Failed {url}: {e}")
        return ""


# load urls, scrape clean text, split, and index with FAISS
def store_from_txt(txt_path: str = "qu_docs.txt") -> FAISS:
    print(f"store_from_txt('{txt_path}')")

    # get urls
    urls = read_urls(txt_path)
    # if no urls are found
    if not urls:
        print("No URLs found. Returning empty FAISS.")
        embeddings = OllamaEmbeddings(model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"))
        return FAISS.from_texts(["No data"], embeddings)

    embeddings = OllamaEmbeddings(model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"))
    index_path = resolve_path("faiss_index")

    # try to load from disk
    if index_path.exists():
        print(f"Loading cached FAISS index from {index_path}...")
        # try indexing to FAISS
        try:
            vector_store = FAISS.load_local(str(index_path), embeddings, allow_dangerous_deserialization=True)
            print(f"Loaded {len(vector_store.docstore._dict)} documents from cache")
            return vector_store
        except Exception as e:
            print(f"Cache load failed: {e} → rebuilding...")

    # building FAISS index
    print("Building new FAISS index...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    all_chunks: List[Document] = []

    for i in range(0, len(urls), BATCH_SIZE):
        batch = urls[i:i + BATCH_SIZE]
        batch_docs: List[Document] = []

        print(f"  Scraping batch {i//BATCH_SIZE + 1}/{(len(urls)-1)//BATCH_SIZE + 1} ({len(batch)} URLs)")

        # for each url scrape to get the content
        for url in batch:
            text = scrape_text(url)
            if text:
                batch_docs.append(Document(page_content=text, metadata={"source": url}))

        if batch_docs:
            splits = text_splitter.split_documents(batch_docs)
            all_chunks.extend(splits)

        # sleep between batches, better for servers
        if i + BATCH_SIZE < len(urls):
            time.sleep(SLEEP_BETWEEN_BATCHES)

    # create FAISS index
    if all_chunks:
        print(f"Indexing {len(all_chunks)} chunks in batches...")
    
        BATCH_EMBED = 500  # ← Safe batch size
        vector_store = None
    
        for i in range(0, len(all_chunks), BATCH_EMBED):
            batch = all_chunks[i:i + BATCH_EMBED]
            print(f"  Embedding batch {i//BATCH_EMBED + 1}/{(len(all_chunks)-1)//BATCH_EMBED + 1} ({len(batch)} chunks)")
        
            try:
                if vector_store is None:
                    vector_store = FAISS.from_documents(batch, embeddings)
                else:
                    vector_store.add_documents(batch)
            except Exception as e:
                print(f"  Embedding failed: {e}")
                print("  Saving partial index and stopping...")
                break
    
        if vector_store:
            vector_store.save_local(str(index_path))
            print(f"Partial index saved to {index_path}")
        # if not content was scraped
        else:
            print("No embeddings created.")
    else:
        print("nothing scraped")

    return vector_store
