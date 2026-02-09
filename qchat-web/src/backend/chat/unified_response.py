"""
Unified Response System - Single intelligent handler with access to all information sources

Instead of tiered checking (Personal → FAQ → RAG), this gives the LLM access to:
- User profile (if available)
- FAQ knowledge base
- Web content from university sites

The LLM intelligently decides what information to use based on the query.
"""

import os
import re
from typing import Optional, Dict, Any
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from bs4 import BeautifulSoup
import requests

from .profile_service import get_user_profile
from .faq_data import FAQ_DATA
from .profanity_filter import sanitize_text

# LLM Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")
_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "4096"))  # Larger context for unified approach
_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "512"))

# LLM for unified responses
unified_llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_URL,
    temperature=0.0,  # Zero temperature for completely deterministic, consistent formatting
    num_ctx=_NUM_CTX,
    model_kwargs={"num_predict": _NUM_PREDICT},
)

# Greetings pattern
GREETINGS_LIST = re.compile(r"\b(hi|hello|hey|hii|sup|what'?s up)\b", re.IGNORECASE)

# Load QU URLs
QU_DOCS_PATH = os.path.join(os.path.dirname(__file__), "qu_docs.txt")
try:
    with open(QU_DOCS_PATH, "r", encoding="utf-8") as f:
        QU_DOCS_URLS = [line.strip() for line in f if line.strip().startswith("http")]
    print(f"Unified system loaded {len(QU_DOCS_URLS)} QU URLs")
except Exception as e:
    print(f"ERROR loading qu_docs.txt: {e}")
    QU_DOCS_URLS = []

# Unified prompt template
unified_prompt = ChatPromptTemplate.from_messages([
    ("system",
     """You are QChat, a helpful assistant for Quinnipiac University students.

You have access to:
1. USER PROFILE - Personal information about this student
2. FAQ DATABASE - Common questions and official answers  
3. WEB CONTENT - Information from Quinnipiac University websites

ANSWER RULES:
- Use the most relevant information sources
- Be conversational and friendly
- Never make up information
- Personalize responses when you have user context
- Keep answers clear and concise

CRITICAL - URL FORMATTING:
When including URLs, write them EXACTLY as plain text with NO markup whatsoever:

✓ CORRECT:
"Visit https://dineoncampus.com/quinnipiac/events for dining info."
"Check out https://www.qu.edu/student-life/ today."
"Menu: https://dineoncampus.com/quinnipiac/cafe-q"

✗ WRONG - NEVER EVER DO THESE:
"Visit [the site](https://url.com)" ← NO
"Visit <a href='https://url.com'>link</a>" ← NO
"Visit https://url.com\" target=\"_blank\"" ← NO
"Visit href=\"https://url.com\"" ← NO
Any brackets, quotes, attributes, or tags ← NO

WRITE ONLY: https://example.com
NOTHING ELSE. NO MARKUP. NO TAGS. NO ATTRIBUTES.
"""),
    ("human",
     """USER PROFILE:
{profile}

FAQ DATABASE:
{faq_context}

WEB CONTENT:
{web_context}

USER QUESTION: {question}

Please answer using the appropriate information sources. Remember: Write URLs as plain text only, no markup.""")
])


def get_unified_response(question: str, username: str = None) -> Dict[str, Any]:
    """
    Generate intelligent response with access to all information sources.
    
    Args:
        question: User's question
        username: Username for profile lookup (None for anonymous)
        
    Returns:
        Dict with reply, sources, and source type
    """
    # Handle simple greetings quickly - only if it's JUST a greeting
    # Remove common punctuation and check if what remains is only greeting words
    question_check = re.sub(r'[!?.,:;]+', '', question.strip().lower())
    words = question_check.split()
    
    # Only treat as greeting if it's 1-3 words and all are greetings
    greeting_words = {'hi', 'hello', 'hey', 'hii', 'sup', 'what\'s', 'up', 'whats', 'there'}
    if len(words) <= 3 and all(word in greeting_words for word in words):
        return {
            "reply": "Hi! I'm QChat, your Quinnipiac University assistant. Ask me anything about classes, dining, housing, athletics, or campus life!",
            "sources": [],
            "source": "greeting"
        }
    
    try:
        # 1. Get user profile
        profile_text = _get_profile_context(username)
        
        # 2. Get relevant FAQ context
        faq_context = _get_faq_context(question)
        
        # 3. Get web content
        web_context, web_sources = _get_web_context(question)
        
        # 4. Call LLM with all information
        response = unified_llm.invoke(
            unified_prompt.invoke({
                "profile": profile_text,
                "faq_context": faq_context,
                "web_context": web_context,
                "question": question
            })
        )
        
        reply = response.content.strip()
        
        # Debug: Show what LLM generated before cleanup
        if '" target=' in reply or '">http' in reply:
            print(f"⚠️  LLM generated broken HTML in reply. Cleaning...")
            print(f"First 200 chars: {reply[:200]}")
        
        reply = sanitize_text(reply)
        reply = _clean_technical_references(reply)
        reply = _format_reply_text(reply)
        reply = _format_urls_as_links(reply)
        
        # Determine source type from content
        source_type = _detect_source_type(reply, bool(profile_text), bool(faq_context), bool(web_sources))
        
        # Compile sources
        all_sources = []
        if "profile" in source_type:
            all_sources.append("user_profile")
        if web_sources:
            # Clean any broken HTML from source URLs before adding them
            clean_sources = []
            for url in web_sources[:3]:
                cleaned = _clean_url(url)
                if '" target=' in url or '">http' in url:
                    print(f"⚠️  Cleaned source URL: {url[:80]}... -> {cleaned[:80]}...")
                clean_sources.append(cleaned)
            all_sources.extend(clean_sources)
        
        return {
            "reply": reply,
            "sources": all_sources,
            "source": source_type
        }
        
    except Exception as e:
        print(f"Error in unified response: {repr(e)}")
        import traceback
        traceback.print_exc()
        return {
            "reply": "I'm having trouble right now. Please try again.",
            "sources": [],
            "source": "error"
        }


def _get_profile_context(username: Optional[str]) -> str:
    """Get formatted user profile or empty string."""
    if not username or username == "anonymous":
        return "No user profile available (anonymous user)."
    
    profile = get_user_profile(username)
    if not profile:
        return f"User: {username} (no profile data yet)"
    
    # Format profile for LLM
    lines = [f"User: {username}\n"]
    
    personal = profile.get('personal_info', {})
    if personal:
        if personal.get('name'):
            lines.append(f"Name: {personal['name']}")
        if personal.get('major'):
            lines.append(f"Major: {personal['major']}")
        if personal.get('year'):
            lines.append(f"Year: {personal['year']}")
    
    schedule = profile.get('schedule', {})
    classes = schedule.get('classes', [])
    if classes:
        lines.append("\nClasses:")
        for cls in classes:
            class_str = f"  • {cls.get('code', 'Unknown')}"
            if cls.get('name'):
                class_str += f" - {cls['name']}"
            lines.append(class_str)
    
    activities = schedule.get('extracurriculars', [])
    if activities:
        lines.append(f"\nActivities: {', '.join(activities)}")
    
    prefs = profile.get('preferences', {})
    if prefs:
        if prefs.get('dietary_restrictions'):
            lines.append(f"Dietary: {', '.join(prefs['dietary_restrictions'])}")
        if prefs.get('favorite_dining_halls'):
            lines.append(f"Favorite Dining: {', '.join(prefs['favorite_dining_halls'])}")
    
    return "\n".join(lines) if len(lines) > 1 else "User has minimal profile data."


def _get_faq_context(question: str) -> str:
    """Get relevant FAQ entries based on question keywords."""
    q_lower = question.lower()
    relevant_faqs = []
    
    # Find FAQs that match keywords in the question
    for faq in FAQ_DATA[:50]:  # Limit to first 50 FAQs to avoid context overflow
        # Check if question keywords match FAQ
        faq_text = f"{faq.get('question', '')} {faq.get('answer', '')}".lower()
        
        # Simple keyword matching
        words = q_lower.split()
        matches = sum(1 for word in words if len(word) > 3 and word in faq_text)
        
        if matches >= 2:  # At least 2 keyword matches
            relevant_faqs.append(faq)
            if len(relevant_faqs) >= 5:  # Limit to top 5 FAQs
                break
    
    if not relevant_faqs:
        return "No particularly relevant FAQs found."
    
    # Format FAQs
    faq_lines = []
    for i, faq in enumerate(relevant_faqs, 1):
        faq_lines.append(f"FAQ {i} ({faq.get('category', 'General')}):")
        faq_lines.append(f"Q: {faq.get('question')}")
        faq_lines.append(f"A: {faq.get('answer')}")
        faq_lines.append("")
    
    return "\n".join(faq_lines)


def _get_web_context(question: str) -> tuple[str, list]:
    """Get relevant web content from QU sites."""
    q_lower = question.lower()
    candidates = []
    
    # Rank URLs based on question keywords
    for url in QU_DOCS_URLS:
        score = 0
        url_lower = url.lower()
        
        # Keyword matching
        if any(k in q_lower for k in ["menu", "dining", "eat", "food"]) and "dining" in url_lower:
            score += 10
        if any(k in q_lower for k in ["event", "calendar", "happening"]) and "event" in url_lower:
            score += 10
        if any(k in q_lower for k in ["catalog", "course", "class"]) and "catalog" in url_lower:
            score += 10
        
        # General word matching
        for word in q_lower.split():
            if len(word) > 3 and word in url_lower:
                score += 2
        
        if score > 0:
            candidates.append((url, score))
    
    candidates.sort(key=lambda x: x[1], reverse=True)
    top_urls = [url for url, _ in candidates[:3]]
    
    if not top_urls:
        top_urls = QU_DOCS_URLS[:2]  # Default fallback
    
    # Fetch content
    context_parts = []
    sources = []
    headers = {"User-Agent": "QChat-Bot/1.0"}
    
    for url in top_urls:
        try:
            r = requests.get(url, timeout=8, headers=headers)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text(separator=" ", strip=True)
                # Remove any remaining HTML entities and excessive whitespace
                clean = re.sub(r"\s+", " ", text)
                # Remove any stray HTML-like patterns
                clean = re.sub(r'<[^>]+>', '', clean)
                clean = re.sub(r'href="[^"]*"', '', clean)
                clean = clean[:3000]  # Limit per URL
                context_parts.append(f"From {url}:\n{clean}\n")
                sources.append(url)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            continue
    
    web_context = "\n".join(context_parts) if context_parts else "No web content retrieved."
    return web_context, sources


def _clean_technical_references(text: str) -> str:
    """
    Clean up technical references to make responses more natural.
    
    Args:
        text: Response text possibly containing technical references
        
    Returns:
        Cleaned text with technical references removed or simplified
    """
    # Remove overly technical source references
    text = re.sub(r'\bFAQ DATABASE\b', 'our information', text, flags=re.IGNORECASE)
    text = re.sub(r'\bWEB CONTENT\b', 'university information', text, flags=re.IGNORECASE)
    text = re.sub(r'\bUSER PROFILE\b', 'your profile', text, flags=re.IGNORECASE)
    
    # Clean up phrases like "Based on the FAQ DATABASE,"
    text = re.sub(r'Based on (the |our )?our information,?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'According to (the |our )?our information,?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'From (the |our )?university information,?\s*', '', text, flags=re.IGNORECASE)
    
    return text


def _format_reply_text(text: str) -> str:
    """
    Format response text to be more readable.
    
    Args:
        text: Raw text response
        
    Returns:
        Formatted text with proper line breaks and spacing
    """
    if not text:
        return text
    t = text.strip().replace("\r\n", "\n").replace("\r", "\n")

    # ensure headings start on their own line
    t = re.sub(r"\s*(\*\*[^*\n]{2,80}\*\*:)\s*", r"\n\n\1\n", t)
    # put bullets on their own lines (handles "- ", "• ", "* ")
    t = re.sub(r"\s+(-\s+)", r"\n- ", t)
    t = re.sub(r"\s+(•\s+)", r"\n• ", t)
    t = re.sub(r"\s+(\*\s+)", r"\n* ", t)
    # if a bullet is glued to a heading like "**X:** - item", split it
    t = re.sub(r"(\*\*[^*\n]{2,80}\*\*:)\s*-\s*", r"\1\n- ", t)
    # keep numbered items clean 
    t = re.sub(r"\s+(\d+\.)\s+", r"\n\1 ", t)
    # collapse too many blank lines
    t = re.sub(r"\n{3,}", "\n\n", t)
    # return cleaned version
    return t.strip()


def _format_urls_as_links(text: str) -> str:
    """
    Convert plain URLs in text to clean HTML anchor tags for clickable links.
    Aggressively removes any broken HTML fragments first.
    
    Args:
        text: Text potentially containing URLs
        
    Returns:
        Text with URLs converted to HTML links
    """
    # AGGRESSIVE CLEANUP: Remove ALL broken HTML patterns first
    # Pattern: href="url" or href='url'
    text = re.sub(r'href=["\']https?://[^"\'>]*["\']', '', text)
    
    # Pattern: Any " target="_blank" or similar attributes
    text = re.sub(r'"[^"]*target[^>]*>', '', text)
    text = re.sub(r"'[^']*target[^>]*>", '', text)
    
    # Pattern: Any stray > preceded by quotes
    text = re.sub(r'["\'][^"\'>]{0,50}>', '', text)
    
    # Remove all HTML anchor tags (both opening and closing)
    text = re.sub(r'</?a[^>]*>', '', text)
    
    # Remove markdown links [text](url)
    text = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'\2', text)
    
    # Clean up any remaining broken patterns around URLs
    # This catches: URL"stuff or URL'stuff
    text = re.sub(r'(https?://[^\s<>"\'";]+)["\'][^\s<>]*', r'\1', text)
    
    # Now convert plain URLs to clean HTML
    # Match URLs not already in href=""
    url_pattern = r'(?<!href=")(?<!href=\')(https?://[^\s<>"\'";]+)'
    
    def make_link(match):
        url = match.group(1).rstrip('.,;:!?)"\'')  # Remove trailing punctuation
    
    return text


def _clean_url(url: str) -> str:
    """
    Clean a URL of any broken HTML fragments.
    Extracts just the pure URL.
    
    Args:
        url: URL string that might contain broken HTML
        
    Returns:
        Clean URL string
    """
    # Strip everything and extract ONLY the URL
    # Remove quotes and everything after them
    url = re.split(r'["\']', url)[0]
    
    # Remove any HTML tag fragments
    url = re.sub(r'<[^>]*>', '', url)
    url = re.sub(r'target=.*', '', url)
    url = re.sub(r'rel=.*', '', url)
    url = re.sub(r'href=.*', '', url)
    
    # Extract the first complete URL
    match = re.search(r'(https?://[^\s<>"\';]+)', url)
    if match:
        clean = match.group(1).rstrip('.,;:!?)"\'')
        return clean
    
    # If no URL found Return original stripped
def _detect_source_type(reply: str, has_profile: bool, has_faq: bool, has_web: bool) -> str:
    """Detect which sources were likely used based on available data."""
    # This is a simple heuristic - could be improved with LLM signaling
    if has_profile and any(word in reply.lower() for word in ["you're", "your classes", "your major"]):
        if has_web:
            return "profile+web"
        return "profile"
    elif has_faq:
        return "faq+web" if has_web else "faq"
    elif has_web:
        return "web"
    else:
        return "general"
