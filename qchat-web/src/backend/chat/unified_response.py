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
    temperature=0.3,  # Balanced for factual yet natural responses
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
     """You are QChat, a helpful and intelligent assistant for Quinnipiac University students.

You have access to THREE sources of information:
1. USER PROFILE - Personal information about this specific student
2. FAQ DATABASE - Common questions and official answers
3. WEB CONTENT - Live information from Quinnipiac University websites

YOUR TASK:
- Understand what the user is asking
- Decide which information sources are relevant
- Provide accurate, helpful, personalized answers
- Cite your sources appropriately

DECISION MAKING:
- Personal questions (my major, my classes, my schedule) → Use USER PROFILE
- Common policy/procedure questions → Prefer FAQ DATABASE (most reliable)
- Specific current info (menus, events, details) → Use WEB CONTENT
- Questions about user's profile items (describe my courses) → Combine PROFILE + WEB CONTENT

RULES:
- Be conversational and friendly
- NEVER make up information - only use provided sources
- If you don't have the info, say so clearly
- Personalize responses when you have user context
- For greetings, be welcoming and invite questions
- Keep answers concise but complete

URL FORMATTING:
- When mentioning URLs, format them as plain text followed by the URL in parentheses
- Example: "You can find more information on the Programs Listing page (https://www.qu.edu/academics/about-our-programs/programs-listing/)"
- DO NOT use markdown link syntax like [text](url)
- Always include the full URL so users can click it

SOURCE CITATION:
Indicate which sources you used: "user_profile", "faq", "web", or combinations like "profile+web"
"""),
    ("human",
     """USER PROFILE:
{profile}

FAQ DATABASE:
{faq_context}

WEB CONTENT:
{web_context}

USER QUESTION: {question}

Please answer using the appropriate information sources.""")
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
    # Handle simple greetings quickly
    if GREETINGS_LIST.search(question.strip()):
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
        reply = sanitize_text(reply)
        reply = _format_urls_as_links(reply)
        
        # Determine source type from content
        source_type = _detect_source_type(reply, bool(profile_text), bool(faq_context), bool(web_sources))
        
        # Compile sources
        all_sources = []
        if "profile" in source_type:
            all_sources.append("user_profile")
        if web_sources:
            all_sources.extend(web_sources[:3])  # Top 3 web sources
        
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
                text = soup.get_text(separator=" ", strip=True)
                clean = re.sub(r"\s+", " ", text)[:3000]  # Limit per URL
                context_parts.append(f"From {url}:\n{clean}\n")
                sources.append(url)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            continue
    
    web_context = "\n".join(context_parts) if context_parts else "No web content retrieved."
    return web_context, sources


def _format_urls_as_links(text: str) -> str:
    """
    Convert plain URLs in text to HTML anchor tags for clickable links.
    Also removes markdown-style link formatting if present.
    
    Args:
        text: Text potentially containing URLs
        
    Returns:
        Text with URLs converted to HTML links
    """
    # First, convert markdown links [text](url) to "text (url)" format
    # This handles cases where LLM still uses markdown despite instructions
    markdown_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    text = re.sub(markdown_link_pattern, r'\1 (\2)', text)
    
    # Then convert plain URLs to HTML anchor tags
    # Match http:// or https:// URLs
    url_pattern = r'(https?://[^\s\)]+)'
    
    def make_link(match):
        url = match.group(1)
        # Extract a friendly name from the URL path
        # e.g., https://www.qu.edu/admissions/ -> "admissions"
        try:
            path_parts = url.rstrip('/').split('/')
            if len(path_parts) > 3:
                friendly_name = path_parts[-1].replace('-', ' ').title()
            else:
                friendly_name = "here"
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>'
        except:
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>'
    
    text = re.sub(url_pattern, make_link, text)
    
    return text


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
