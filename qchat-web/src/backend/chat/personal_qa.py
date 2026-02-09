"""
Personal Question Handler - Uses LLM to answer questions about the user from their profile

This module uses the LLM to intelligently:
- Detect when users ask personal questions (my major, my classes, etc.)
- Answer directly from their profile instead of searching the web
- Format responses naturally based on available profile data
"""

import json
import os
from typing import Optional, Dict, Any
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from .profile_service import get_user_profile

# LLM Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")

# LLM for personal question handling
personal_qa_llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_URL,
    temperature=0.2,  # Low temperature for consistent, factual answers
    format="json"
)

# Prompt for analyzing if question is personal
detection_prompt = ChatPromptTemplate.from_messages([
    ("system",
     """You are analyzing user questions to determine if they're asking about their personal information.

A question is PERSONAL if it:
- Asks about the user themselves (uses "my", "I", "me", "am I", etc.)
- Relates to student information (major, classes, schedule, activities, etc.)

A question is NOT PERSONAL if it:
- Asks about general university information
- Asks about services, locations, or policies
- Doesn't refer to the user specifically

Examples:
- "What's my major?" → PERSONAL
- "What are my classes?" → PERSONAL
- "When do I have practice?" → PERSONAL
- "What majors does QU offer?" → NOT PERSONAL (general question)
- "Where is the library?" → NOT PERSONAL (general question)
- "What's for lunch?" → NOT PERSONAL (general question)

Return JSON: {{"is_personal": true/false, "reasoning": "brief explanation"}}"""),
    ("human", "Question: {question}\n\nIs this a personal question about the user?")
])

# Prompt for answering from profile
answer_prompt = ChatPromptTemplate.from_messages([
    ("system",
     """You are QChat, answering questions about a student using their profile information.

Your task:
1. Look at the student's profile data
2. Answer their question using ONLY information from their profile
3. If the question asks for ADDITIONAL INFO about profile items (like course descriptions, dining hall menus, etc.), signal that enrichment is needed
4. Be friendly, concise, and helpful

RULES:
- ONLY use information from the provided profile
- Do NOT make up or assume information
- If profile is empty or missing the requested info, say: "I don't have that information about you yet. Feel free to tell me!"
- Format lists nicely (use bullet points for multiple items)
- Be conversational and friendly

ENRICHMENT DETECTION:
If the user asks for MORE INFO about items in their profile (e.g., "describe my courses", "what's for lunch at my dining hall"), set needs_enrichment=true and provide an enriched_query.

Examples:
- "What are my classes?" → can_answer=true (just list from profile)
- "Describe my courses" → needs_enrichment=true, enriched_query="What are the course descriptions for [course codes]?"
- "What's my favorite dining hall menu?" → needs_enrichment=true, enriched_query="What's on the menu at [dining hall]?"

Return JSON: {{
  "can_answer": true/false,
  "needs_enrichment": true/false,
  "enriched_query": "question to ask RAG with profile context" (if needs_enrichment),
  "answer": "your response to the user",
  "used_fields": ["list", "of", "profile fields used"]
}}"""),
    ("human",
     """Student Profile:
{profile}

Student Question: {question}

Answer the question using the profile information:""")
])


def try_answer_personal_question(question: str, username: str) -> Optional[Dict[str, Any]]:
    """
    Use LLM to detect personal questions and answer from profile.
    
    Args:
        question: The user's question
        username: The username
        
    Returns:
        Dict with reply if answered from profile, None to fall back to FAQ/RAG
    """
    if not username or username == "anonymous":
        return None
    
    try:
        # STEP 1: Use LLM to detect if this is a personal question
        detection_response = personal_qa_llm.invoke(
            detection_prompt.invoke({"question": question})
        )
        
        try:
            detection = json.loads(detection_response.content)
        except json.JSONDecodeError:
            print(f"Failed to parse detection response: {detection_response.content}")
            return None
        
        if not detection.get("is_personal"):
            print(f"Not a personal question: {detection.get('reasoning')}")
            return None
        
        print(f"✓ Detected personal question: {detection.get('reasoning')}")
        
        # STEP 2: Get user profile
        profile = get_user_profile(username)
        if not profile:
            return {
                "reply": "I don't have any information about you yet. Feel free to tell me about yourself, and I'll remember it!",
                "sources": ["user_profile"],
                "source": "profile"
            }
        
        # Format profile as readable text for LLM
        profile_text = _format_profile_for_llm(profile)
        
        # STEP 3: Use LLM to answer from profile
        answer_response = personal_qa_llm.invoke(
            answer_prompt.invoke({
                "profile": profile_text,
                "question": question
            })
        )
        
        try:
            answer_data = json.loads(answer_response.content)
        except json.JSONDecodeError:
            print(f"Failed to parse answer response: {answer_response.content}")
            return None
        
        # Check if we need to enrich with external data
        if answer_data.get("needs_enrichment"):
            enriched_query = answer_data.get("enriched_query")
            if enriched_query:
                print(f"✓ Needs enrichment - will use RAG with query: {enriched_query}")
                # Return special signal for enrichment
                return {
                    "needs_enrichment": True,
                    "enriched_query": enriched_query,
                    "profile": profile  # Pass profile for context
                }
        
        if answer_data.get("can_answer"):
            print(f"✓ Answered from profile using fields: {answer_data.get('used_fields', [])}")
            return {
                "reply": answer_data.get("answer", "I don't have that information about you yet."),
                "sources": ["user_profile"],
                "source": "profile"
            }
        else:
            # Personal question but no answer in profile
            return {
                "reply": answer_data.get("answer", "I don't have that information about you yet. Feel free to tell me!"),
                "sources": ["user_profile"],
                "source": "profile"
            }
        
    except Exception as e:
        print(f"Error in personal question handling: {repr(e)}")
        import traceback
        traceback.print_exc()
        return None


def _format_profile_for_llm(profile: Dict[str, Any]) -> str:
    """
    Format profile data as readable text for the LLM.
    
    Args:
        profile: User profile dict
        
    Returns:
        Formatted profile string
    """
    lines = []
    
    # Personal Information
    personal = profile.get('personal_info', {})
    if personal:
        lines.append("PERSONAL INFORMATION:")
        if personal.get('name'):
            lines.append(f"  Name: {personal['name']}")
        if personal.get('year'):
            lines.append(f"  Year: {personal['year']}")
        if personal.get('major'):
            lines.append(f"  Major: {personal['major']}")
        if personal.get('minor'):
            lines.append(f"  Minor: {personal['minor']}")
        lines.append("")
    
    # Classes
    schedule = profile.get('schedule', {})
    classes = schedule.get('classes', [])
    if classes:
        lines.append("CLASSES:")
        for cls in classes:
            class_info = []
            if cls.get('code'):
                class_info.append(cls['code'])
            if cls.get('name'):
                class_info.append(cls['name'])
            line = f"  • {' - '.join(class_info) if class_info else 'Class'}"
            if cls.get('professor'):
                line += f" with {cls['professor']}"
            if cls.get('schedule'):
                line += f" ({cls['schedule']})"
            if cls.get('location'):
                line += f" in {cls['location']}"
            lines.append(line)
        lines.append("")
    
    # Activities
    activities = schedule.get('extracurriculars', [])
    if activities:
        lines.append("ACTIVITIES & EXTRACURRICULARS:")
        for activity in activities:
            lines.append(f"  • {activity}")
        lines.append("")
    
    # Preferences
    prefs = profile.get('preferences', {})
    if prefs:
        lines.append("PREFERENCES:")
        if prefs.get('dietary_restrictions'):
            lines.append(f"  Dietary: {', '.join(prefs['dietary_restrictions'])}")
        if prefs.get('favorite_dining_halls'):
            lines.append(f"  Favorite Dining: {', '.join(prefs['favorite_dining_halls'])}")
        if prefs.get('study_locations'):
            lines.append(f"  Study Locations: {', '.join(prefs['study_locations'])}")
        if prefs.get('topics_of_interest'):
            lines.append(f"  Interests: {', '.join(prefs['topics_of_interest'])}")
        lines.append("")
    
    # Academic
    academic = profile.get('academic', {})
    if academic:
        lines.append("ACADEMIC:")
        if academic.get('advisor'):
            lines.append(f"  Advisor: {academic['advisor']}")
        if academic.get('gpa'):
            lines.append(f"  GPA: {academic['gpa']}")
        if academic.get('dean_list'):
            lines.append(f"  Dean's List: Yes")
        lines.append("")
    
    # Recent Notes
    notes = profile.get('notes', [])
    if notes:
        lines.append("OTHER INFORMATION:")
        # Show last 5 notes
        recent_notes = sorted(notes, key=lambda x: x.get('timestamp', ''), reverse=True)[:5]
        for note in recent_notes:
            if isinstance(note, dict):
                lines.append(f"  • {note.get('text', '')}")
            else:
                lines.append(f"  • {note}")
        lines.append("")
    
    if not lines:
        return "No profile information available yet."
    
    return "\n".join(lines)
