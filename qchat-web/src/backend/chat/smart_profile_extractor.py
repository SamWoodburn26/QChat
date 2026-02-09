"""
Smart Profile Extractor - Uses LLM to intelligently extract profile information

This module uses the Ollama LLM to:
- Analyze conversations naturally
- Identify information worth storing
- Extract structured data from unstructured conversations
- Consider conversation context and history
"""

import json
import os
from typing import Dict, List, Any, Optional
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

# LLM Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:latest")

# LLM for extraction (configured for structured output)
extraction_llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_URL,
    temperature=0.1,  # Low temperature for consistent extraction
    format="json",  # Request JSON output
)

# Extraction prompt template
extraction_prompt = ChatPromptTemplate.from_messages([
    ("system",
     """You are a profile information extractor for a university chatbot.

Your job is to analyze conversations and extract ONLY meaningful, factual information about the student that should be remembered for future interactions.

EXTRACT AND CATEGORIZE:
1. **personal_info**: name, academic year (freshman/sophomore/junior/senior/grad), major, minor
2. **classes**: course codes, course names, professors, schedules, locations
3. **schedule**: class times, study times, regular commitments
4. **activities**: clubs, sports teams, organizations, volunteer work, jobs
5. **preferences**: favorite places, dietary needs/restrictions, interests, hobbies
6. **academic**: advisor name, GPA, honors, academic goals
7. **general_notes**: any other important context about the student

RULES:
- Only extract FACTS explicitly stated by the user
- Do NOT extract questions or hypotheticals
- Do NOT extract temporary plans (unless they indicate a regular pattern)
- Do NOT extract information about other people (unless it's their professor/advisor)
- Extract specific details: "soccer practice on Tuesdays" not just "likes soccer"
- For classes, extract full information when available (code, name, schedule, location)

CONVERSATION CONTEXT:
Consider the full conversation history. A user might say:
- "I have soccer practice" → Extract: activity "soccer practice"
- "It's on Tuesdays at 4pm" → Extract: schedule detail for soccer practice
- "I'm a biology major" → Extract: major "Biology"
- "My CS101 class" → Extract: class "CS101"

OUTPUT FORMAT (JSON):
Return a JSON object with these keys (omit empty sections):
{{
  "personal_info": {{"year": "sophomore", "major": "Biology", ...}},
  "classes": [
    {{"code": "CS101", "name": "Intro to Programming", "schedule": "MWF 10-11am", ...}}
  ],
  "schedule": ["Soccer practice Tuesdays 4pm", ...],
  "activities": ["Soccer team", "Chess club", ...],
  "preferences": {{
    "dietary": ["vegetarian", "no nuts"],
    "dining": ["Rocky Top"],
    "study_locations": ["Library"],
    "interests": ["AI", "Web Development"]
  }},
  "academic": {{"advisor": "Dr. Smith", ...}},
  "notes": ["Takes notes on laptop", "Prefers morning classes", ...]
}}

If NO meaningful profile information is found, return: {{"extracted": false}}
"""),
    ("human",
     """Analyze this conversation and extract profile information:

CONVERSATION:
{conversation}

Extract meaningful profile information as JSON:""")
])


def extract_profile_info_from_conversation(
    user_message: str,
    bot_reply: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    current_profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Use LLM to intelligently extract profile information from a conversation.
    
    Args:
        user_message: The user's latest message
        bot_reply: The bot's reply
        conversation_history: Recent messages for context (list of {role, text})
        current_profile: User's existing profile for context
        
    Returns:
        Dict with extracted information or {"extracted": false} if nothing found
    """
    try:
        # Build conversation context
        conversation_parts = []
        
        # Include recent history for context (last 5 exchanges)
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 5 exchanges (10 messages)
                role = "Student" if msg.get("role") == "user" else "QChat"
                conversation_parts.append(f"{role}: {msg.get('text', '')}")
        
        # Add current exchange
        conversation_parts.append(f"Student: {user_message}")
        conversation_parts.append(f"QChat: {bot_reply}")
        
        conversation_text = "\n".join(conversation_parts)
        
        # Optional: Add current profile context to avoid duplicates
        profile_context = ""
        if current_profile:
            profile_context = f"\nCURRENT PROFILE SUMMARY: {_summarize_profile(current_profile)}\n"
        
        # Call LLM for extraction
        response = extraction_llm.invoke(
            extraction_prompt.invoke({
                "conversation": conversation_text + profile_context
            })
        )
        
        # Parse JSON response
        result = json.loads(response.content)
        
        # Validate and clean the result
        if result.get("extracted") == False:
            return {"extracted": False}
        
        # Clean and structure the extracted data
        cleaned = _clean_extracted_data(result)
        
        if not cleaned or not any(cleaned.values()):
            return {"extracted": False}
        
        cleaned["extracted"] = True
        return cleaned
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM extraction output: {e}")
        print(f"Raw output: {response.content if 'response' in locals() else 'N/A'}")
        return {"extracted": False}
    except Exception as e:
        print(f"Error in smart profile extraction: {repr(e)}")
        return {"extracted": False}


def _summarize_profile(profile: Dict[str, Any]) -> str:
    """Create a brief summary of existing profile to avoid duplicate extraction."""
    parts = []
    
    personal = profile.get("personal_info", {})
    if personal.get("year"):
        parts.append(f"Year: {personal['year']}")
    if personal.get("major"):
        parts.append(f"Major: {personal['major']}")
    
    classes = profile.get("schedule", {}).get("classes", [])
    if classes:
        class_codes = [c.get("code", c.get("name", "")) for c in classes[:3]]
        parts.append(f"Classes: {', '.join(class_codes)}")
    
    activities = profile.get("schedule", {}).get("extracurriculars", [])
    if activities:
        parts.append(f"Activities: {', '.join(activities[:3])}")
    
    return " | ".join(parts) if parts else "No profile yet"


def _clean_extracted_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Clean and validate extracted data."""
    cleaned = {}
    
    # Clean personal_info
    if "personal_info" in data and data["personal_info"]:
        personal = {}
        if data["personal_info"].get("year"):
            year = str(data["personal_info"]["year"]).lower()
            # Normalize year values
            if "fresh" in year or "first" in year:
                personal["year"] = "freshman"
            elif "soph" in year or "second" in year:
                personal["year"] = "sophomore"
            elif "junior" in year or "third" in year:
                personal["year"] = "junior"
            elif "senior" in year or "fourth" in year:
                personal["year"] = "senior"
            elif "grad" in year:
                personal["year"] = "grad"
            else:
                personal["year"] = year
        
        for key in ["name", "major", "minor"]:
            if data["personal_info"].get(key):
                personal[key] = str(data["personal_info"][key]).strip()
        
        if personal:
            cleaned["personal_info"] = personal
    
    # Clean classes - ensure they're properly structured
    if "classes" in data and data["classes"]:
        classes = []
        for cls in data["classes"]:
            if isinstance(cls, dict) and (cls.get("code") or cls.get("name")):
                class_obj = {}
                for key in ["code", "name", "professor", "schedule", "location"]:
                    if cls.get(key):
                        class_obj[key] = str(cls[key]).strip()
                if class_obj:
                    classes.append(class_obj)
        if classes:
            cleaned["classes"] = classes
    
    # Clean schedule items
    if "schedule" in data and isinstance(data["schedule"], list):
        schedule = [str(s).strip() for s in data["schedule"] if s]
        if schedule:
            cleaned["schedule"] = schedule
    
    # Clean activities
    if "activities" in data and isinstance(data["activities"], list):
        activities = [str(a).strip() for a in data["activities"] if a]
        if activities:
            cleaned["activities"] = activities
    
    # Clean preferences
    if "preferences" in data and isinstance(data["preferences"], dict):
        prefs = {}
        for key in ["dietary", "dining", "study_locations", "interests"]:
            if data["preferences"].get(key):
                items = data["preferences"][key]
                if isinstance(items, list):
                    prefs[key] = [str(i).strip() for i in items if i]
                elif isinstance(items, str):
                    prefs[key] = [str(items).strip()]
        if prefs:
            cleaned["preferences"] = prefs
    
    # Clean academic
    if "academic" in data and isinstance(data["academic"], dict):
        academic = {}
        for key in ["advisor", "gpa", "dean_list"]:
            if data["academic"].get(key) is not None:
                academic[key] = data["academic"][key]
        if academic:
            cleaned["academic"] = academic
    
    # Clean notes
    if "notes" in data and isinstance(data["notes"], list):
        notes = [str(n).strip() for n in data["notes"] if n]
        if notes:
            cleaned["notes"] = notes
    
    return cleaned


def apply_extracted_info_to_profile(
    username: str,
    extracted_data: Dict[str, Any],
    profile_service
) -> bool:
    """
    Apply extracted information to user's profile intelligently.
    
    Args:
        username: The username
        extracted_data: Data extracted from conversation
        profile_service: The profile_service module
        
    Returns:
        True if profile was updated, False otherwise
    """
    if not extracted_data.get("extracted"):
        return False
    
    try:
        updated = False
        
        # Update personal info
        if "personal_info" in extracted_data:
            updates = {}
            for key, value in extracted_data["personal_info"].items():
                updates[f"personal_info.{key}"] = value
            if updates:
                profile_service.update_user_profile(username, updates)
                updated = True
                print(f"Updated personal info for {username}: {updates}")
        
        # Add classes
        if "classes" in extracted_data:
            for class_obj in extracted_data["classes"]:
                profile_service.add_to_profile_array(username, "schedule.classes", class_obj)
                updated = True
                print(f"Added class for {username}: {class_obj.get('code', class_obj.get('name'))}")
        
        # Add schedule items as notes
        if "schedule" in extracted_data:
            for schedule_item in extracted_data["schedule"]:
                profile_service.add_note_to_profile(username, f"Schedule: {schedule_item}")
                updated = True
        
        # Add activities
        if "activities" in extracted_data:
            for activity in extracted_data["activities"]:
                profile_service.add_to_profile_array(username, "schedule.extracurriculars", activity)
                updated = True
                print(f"Added activity for {username}: {activity}")
        
        # Update preferences
        if "preferences" in extracted_data:
            prefs = extracted_data["preferences"]
            updates = {}
            
            # For preferences, we want to append to existing arrays, not replace
            current_profile = profile_service.get_user_profile(username)
            current_prefs = current_profile.get("preferences", {}) if current_profile else {}
            
            if prefs.get("dietary"):
                existing = current_prefs.get("dietary_restrictions", [])
                new_items = [d for d in prefs["dietary"] if d not in existing]
                if new_items:
                    updates["preferences.dietary_restrictions"] = existing + new_items
            
            if prefs.get("dining"):
                existing = current_prefs.get("favorite_dining_halls", [])
                new_items = [d for d in prefs["dining"] if d not in existing]
                if new_items:
                    updates["preferences.favorite_dining_halls"] = existing + new_items
            
            if prefs.get("study_locations"):
                existing = current_prefs.get("study_locations", [])
                new_items = [s for s in prefs["study_locations"] if s not in existing]
                if new_items:
                    updates["preferences.study_locations"] = existing + new_items
            
            if prefs.get("interests"):
                existing = current_prefs.get("topics_of_interest", [])
                new_items = [i for i in prefs["interests"] if i not in existing]
                if new_items:
                    updates["preferences.topics_of_interest"] = existing + new_items
            
            if updates:
                profile_service.update_user_profile(username, updates)
                updated = True
                print(f"Updated preferences for {username}")
        
        # Update academic info
        if "academic" in extracted_data:
            updates = {}
            for key, value in extracted_data["academic"].items():
                updates[f"academic.{key}"] = value
            if updates:
                profile_service.update_user_profile(username, updates)
                updated = True
        
        # Add general notes
        if "notes" in extracted_data:
            for note in extracted_data["notes"]:
                profile_service.add_note_to_profile(username, note)
                updated = True
        
        return updated
        
    except Exception as e:
        print(f"Error applying extracted info to profile: {repr(e)}")
        return False
