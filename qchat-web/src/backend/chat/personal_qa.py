"""
Personal Question Handler - Answers questions about the user from their profile

This module detects when users ask personal questions (my major, my classes, etc.)
and answers directly from their profile instead of searching the web.
"""

import re
from typing import Optional, Dict, Any
from .profile_service import get_user_profile


def is_personal_question(question: str) -> bool:
    """
    Detect if a question is asking about the user's personal information.
    
    Args:
        question: The user's question
        
    Returns:
        True if it's a personal question, False otherwise
    """
    q_lower = question.lower()
    
    # Personal pronouns indicating questions about the user
    personal_indicators = [
        r'\bmy\b',
        r'\bam i\b',
        r"\bi'm\b",
        r'\bdo i\b',
        r'\bwhat am i\b',
        r'\bwhen do i\b',
        r'\bwhere do i\b',
        r'\bwho is my\b',
    ]
    
    # Topics that would be in profile
    profile_topics = [
        r'\bmajor\b',
        r'\bminor\b',
        r'\bclass(?:es)?\b',
        r'\bcourse(?:s)?\b',
        r'\bschedule\b',
        r'\badvisor\b',
        r'\bactiv(?:ity|ities)\b',
        r'\bclub(?:s)?\b',
        r'\bteam\b',
        r'\byear\b',
        r'\bgrade\b',
        r'\bgpa\b',
        r'\bprofessor\b',
        r'\bpractice\b',
        r'\bdietary\b',
        r'\ballerg(?:y|ies|ic)\b',
        r'\bfavorite\b',
        r'\bprefer(?:ence|red)?\b',
    ]
    
    # Check if question has personal pronouns AND profile topics
    has_personal = any(re.search(pattern, q_lower) for pattern in personal_indicators)
    has_topic = any(re.search(pattern, q_lower) for pattern in profile_topics)
    
    return has_personal and has_topic


def answer_from_profile(question: str, username: str) -> Optional[Dict[str, Any]]:
    """
    Try to answer a personal question from the user's profile.
    
    Args:
        question: The user's question
        username: The username to look up
        
    Returns:
        Dict with reply and sources if answer found, None otherwise
    """
    if not username or username == "anonymous":
        return None
    
    profile = get_user_profile(username)
    if not profile:
        return None
    
    q_lower = question.lower()
    
    # Major question
    if 'major' in q_lower:
        major = profile.get('personal_info', {}).get('major')
        if major:
            return {
                "reply": f"Your major is {major}.",
                "sources": ["user_profile"],
                "source": "profile"
            }
    
    # Minor question
    if 'minor' in q_lower:
        minor = profile.get('personal_info', {}).get('minor')
        if minor:
            return {
                "reply": f"Your minor is {minor}.",
                "sources": ["user_profile"],
                "source": "profile"
            }
        elif profile.get('personal_info', {}).get('major'):
            return {
                "reply": "I don't have information about your minor. You can tell me if you have one!",
                "sources": ["user_profile"],
                "source": "profile"
            }
    
    # Year question
    if re.search(r'\byear\b|\bgrade\b', q_lower):
        year = profile.get('personal_info', {}).get('year')
        if year:
            return {
                "reply": f"You're a {year}.",
                "sources": ["user_profile"],
                "source": "profile"
            }
    
    # Classes question
    if re.search(r'\bclass(?:es)?\b|\bcourse(?:s)?\b', q_lower):
        classes = profile.get('schedule', {}).get('classes', [])
        if classes:
            class_list = []
            for cls in classes:
                code = cls.get('code', '')
                name = cls.get('name', '')
                prof = cls.get('professor', '')
                schedule = cls.get('schedule', '')
                
                class_str = code if code else name
                if prof:
                    class_str += f" with {prof}"
                if schedule:
                    class_str += f" ({schedule})"
                class_list.append(class_str)
            
            if len(class_list) == 1:
                reply = f"You're taking {class_list[0]}."
            else:
                reply = f"You're taking these classes:\n" + "\n".join(f"• {c}" for c in class_list)
            
            return {
                "reply": reply,
                "sources": ["user_profile"],
                "source": "profile"
            }
    
    # Schedule/practice question
    if re.search(r'\bschedule\b|\bpractice\b|\bwhen do i\b', q_lower):
        # Check for activities/schedule notes
        activities = profile.get('schedule', {}).get('extracurriculars', [])
        notes = profile.get('notes', [])
        
        schedule_items = []
        
        # Add activities
        if activities:
            schedule_items.extend([f"• {act}" for act in activities])
        
        # Check notes for schedule info
        for note in notes:
            if isinstance(note, dict):
                text = note.get('text', '')
            else:
                text = str(note)
            
            if 'schedule' in text.lower() or 'practice' in text.lower():
                schedule_items.append(f"• {text}")
        
        if schedule_items:
            reply = "Here's what I know about your schedule:\n" + "\n".join(schedule_items)
            return {
                "reply": reply,
                "sources": ["user_profile"],
                "source": "profile"
            }
    
    # Advisor question
    if 'advisor' in q_lower:
        advisor = profile.get('academic', {}).get('advisor')
        if advisor:
            return {
                "reply": f"Your advisor is {advisor}.",
                "sources": ["user_profile"],
                "source": "profile"
            }
    
    # GPA question
    if 'gpa' in q_lower:
        gpa = profile.get('academic', {}).get('gpa')
        if gpa:
            return {
                "reply": f"Your GPA is {gpa}.",
                "sources": ["user_profile"],
                "source": "profile"
            }
    
    # Dietary/allergies question
    if re.search(r'\bdietary\b|\ballerg', q_lower):
        dietary = profile.get('preferences', {}).get('dietary_restrictions', [])
        if dietary:
            reply = f"Your dietary restrictions: {', '.join(dietary)}."
            return {
                "reply": reply,
                "sources": ["user_profile"],
                "source": "profile"
            }
    
    # Favorite dining question
    if 'favorite' in q_lower and any(word in q_lower for word in ['dining', 'eat', 'food', 'caf']):
        favorites = profile.get('preferences', {}).get('favorite_dining_halls', [])
        if favorites:
            reply = f"Your favorite dining halls: {', '.join(favorites)}."
            return {
                "reply": reply,
                "sources": ["user_profile"],
                "source": "profile"
            }
    
    # General profile summary question
    if re.search(r'who am i|tell me about me|what do you know about me', q_lower):
        summary_parts = []
        
        personal = profile.get('personal_info', {})
        if personal.get('name'):
            summary_parts.append(f"Your name is {personal['name']}")
        if personal.get('year'):
            summary_parts.append(f"You're a {personal['year']}")
        if personal.get('major'):
            summary_parts.append(f"majoring in {personal['major']}")
        if personal.get('minor'):
            summary_parts.append(f"with a minor in {personal['minor']}")
        
        classes = profile.get('schedule', {}).get('classes', [])
        if classes:
            class_codes = [c.get('code', c.get('name', '')) for c in classes[:3]]
            summary_parts.append(f"taking {', '.join(class_codes)}")
        
        activities = profile.get('schedule', {}).get('extracurriculars', [])
        if activities:
            summary_parts.append(f"participating in {', '.join(activities[:3])}")
        
        if summary_parts:
            reply = ". ".join(summary_parts) + "."
            reply = reply.replace(". .", ".")
            return {
                "reply": reply,
                "sources": ["user_profile"],
                "source": "profile"
            }
    
    # If we get here, the question seems personal but we don't have the answer
    return None


def try_answer_personal_question(question: str, username: str) -> Optional[Dict[str, Any]]:
    """
    Main entry point: Check if question is personal and try to answer from profile.
    
    Args:
        question: The user's question
        username: The username
        
    Returns:
        Dict with reply if answered from profile, None to fall back to RAG
    """
    # Check if it's a personal question
    if not is_personal_question(question):
        return None
    
    # Try to answer from profile
    answer = answer_from_profile(question, username)
    
    if answer:
        return answer
    
    # Personal question but no answer in profile
    # Return a helpful message
    return {
        "reply": "I don't have that information about you yet. Feel free to tell me, and I'll remember it for next time!",
        "sources": ["user_profile"],
        "source": "profile"
    }
