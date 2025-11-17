# ollama to make the gemma model
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.prompts import ChatPromptTemplate

import azure.functions as func
import json, os
from datetime import datetime
from pymongo import MongoClient

# MongoDB Configuration
MONGO_URI = os.environ.get('MONGODB_URI') or os.getenv('MONGODB_URI')
DATABASE_NAME = os.environ.get('DB_NAME', 'qchat')
CHAT_LOGS_COLLECTION = 'chatLogs'

# MongoDB client (global)
mongo_client = None
db = None

# for ollama
llm = ChatOllama(model="mistral:latest", base_url=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"))
embeddings = OllamaEmbeddings(model="mistral:latest")
vector_store = InMemoryVectorStore(embeddings)

# QChat System Prompt
SYSTEM_PROMPT = """You are QChat, a helpful assistant for Quinnipiac University students.
Answer questions clearly and concisely. If you don't know something, say so.
Be friendly, professional, and helpful."""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{question}")
])

# ============ MONGODB FONKSİYONLARI ============

def get_db():
    """MongoDB connection"""
    global mongo_client, db
    if db is None:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client[DATABASE_NAME]
        db.command('ping')
        print("MongoDB connected")
    return db


def save_message(user_id, session_id, message, response, category=None, source=None):
    """Save chat to MongoDB"""
    try:
        database = get_db()
        chat_logs = database[CHAT_LOGS_COLLECTION]
        
        doc = {
            'userId': user_id,
            'sessionId': session_id,
            'timestamp': datetime.utcnow(),
            'message': message,
            'response': response,
            'category': category,
            'source': source
        }
        
        result = chat_logs.insert_one(doc)
        print(f"Saved: {result.inserted_id}")
        return str(result.inserted_id)
    except Exception as e:
        print(f"Save error: {e}")
        return None


def get_history(user_id, session_id=None, limit=50):
    """Get chat history"""
    try:
        database = get_db()
        chat_logs = database[CHAT_LOGS_COLLECTION]
        
        query = {'userId': user_id}
        if session_id:
            query['sessionId'] = session_id
        
        messages = []
        for doc in chat_logs.find(query).sort('timestamp', -1).limit(limit):
            messages.append({
                'id': str(doc['_id']),
                'timestamp': doc['timestamp'].isoformat(),
                'message': doc['message'],
                'response': doc['response'],
                'sessionId': doc.get('sessionId'),
                'category': doc.get('category'),
                'source': doc.get('source')
            })
        
        return messages[::-1]
    except Exception as e:
        print(f"History error: {e}")
        return []


def search_faq(query):
    """Search in universityInfo collection for FAQ answers with improved scoring"""
    try:
        database = get_db()
        university_info = database['universityInfo']
        
        all_faqs = list(university_info.find())
        
        if not all_faqs:
            return []
        
        query_lower = query.lower().strip()
        query_words = set(query_lower.split())
        
        # Remove common words (stop words)
        stop_words = {'i', 'a', 'an', 'the', 'is', 'are', 'what', 'how', 'can', 'do', 'does', 'in', 'to', 'of', 'for', 'on', 'at', 'with'}
        query_keywords = query_words - stop_words
        
        scored_faqs = []
        
        for faq in all_faqs:
            score = 0
            question_lower = faq.get('question', '').lower().strip()
            question_words = set(question_lower.split())
            question_keywords = question_words - stop_words
            keywords = [k.lower() for k in faq.get('keywords', [])]
            
            # Skip if no meaningful words to compare
            if not query_keywords or not question_keywords:
                continue
            
            # EXACT MATCH (very high score)
            if query_lower == question_lower:
                score = 1000
            
            # SUBSTRING MATCH (high score)
            elif query_lower in question_lower or question_lower in query_lower:
                score = 500
            
            # KEYWORD MATCHING (careful scoring)
            else:
                # Must have at least 50% keyword overlap
                matching_keywords = query_keywords.intersection(question_keywords)
                overlap_ratio = len(matching_keywords) / len(query_keywords)
                
                if overlap_ratio < 0.5:
                    # Not enough overlap, skip this FAQ
                    continue
                
                # Calculate score based on keyword matches
                score = len(matching_keywords) * 30
                
                # Bonus for keyword field matches
                for keyword in keywords:
                    if keyword in query_keywords:
                        score += 20
                
                # Penalty if FAQ question is too different in length
                length_ratio = len(question_keywords) / len(query_keywords)
                if length_ratio > 3 or length_ratio < 0.3:
                    score -= 50
            
            if score > 0:
                scored_faqs.append((score, faq))
        
        # Sort by score
        scored_faqs.sort(reverse=True, key=lambda x: x[0])
        
        # Return top 3
        results = []
        for score, faq in scored_faqs[:3]:
            results.append({
                'category': faq.get('category'),
                'question': faq.get('question'),
                'answer': faq.get('answer'),
                'keywords': faq.get('keywords', []),
                'score': score
            })
        
        return results
    except Exception as e:
        print(f"FAQ search error: {e}")
        return []


def get_faq_answer(query):
    """Get best FAQ answer with threshold check"""
    faq_results = search_faq(query)
    
    if not faq_results:
        print("DEBUG: No FAQ results found")
        return None, None, None, None
    
    best_match = faq_results[0]
    best_score = best_match.get('score', 0)
    
    print(f"DEBUG: Best FAQ score: {best_score}")
    print(f"DEBUG: Best FAQ question: {best_match.get('question')}")
    
    # Threshold check - must be high enough
    if best_score >= 100:  # Yüksek threshold
        return (
            best_match.get('answer'),
            best_match.get('category'),
            'faq_database',
            best_match.get('question')
        )
    else:
        print(f"DEBUG: Best score too low: {best_score}")
        return None, None, None, None


# ============ ANA FONKSİYON ============

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        body = {}
    
    action = body.get("action", "chat")
    user_id = body.get("userId")
    
    # userId kontrolü
    if not user_id:
        return func.HttpResponse('{"error":"userId required"}', status_code=400, mimetype="application/json")
    
    # CHAT ACTION
    if action == "chat":
        msg = (body.get("message") or "").strip()
        session_id = body.get("sessionId")
        
        if not msg or not session_id:
            return func.HttpResponse('{"error":"message and sessionId required"}', status_code=400, mimetype="application/json")
        
        # ============ YENİ: FAQ'den cevap ara ============
        print(f"DEBUG: Searching FAQ for: {msg}")
        faq_answer, faq_category, faq_source, faq_question = get_faq_answer(msg)
        print(f"DEBUG: FAQ Result - answer={faq_answer is not None}, category={faq_category}")
        
        if faq_answer:
            # FAQ'de bulundu - direkt FAQ cevabını kullan
            reply = faq_answer
            category = faq_category
            source = faq_source
            related_question = faq_question
            print(f"✅ FAQ FOUND: {faq_question}")
        else:
            # FAQ'de bulunamadı - LLM kullan
            try:
                formatted = prompt_template.format_messages(question=msg)
                reply = llm.invoke(formatted).content.strip()
                category = "General"
                source = "llm"
                related_question = None
                print("🤖 LLM USED")
            except Exception as e:
                print("LLM error: ", repr(e))
                reply = "I'm having trouble right now. Please try again or contact IT Help Desk."
                category = "Error"
                source = "error"
                related_question = None
        # ============================================
        
        # MongoDB'ye kaydet
        msg_id = save_message(user_id, session_id, msg, reply, category, source)
        
        return func.HttpResponse(
            json.dumps({
                "response": reply,
                "messageId": msg_id,
                "timestamp": datetime.utcnow().isoformat(),
                "category": category,
                "source": source,
                "relatedQuestion": related_question
            }),
            mimetype="application/json"
        )
    
    # HISTORY ACTION
    elif action == "history":
        session_id = body.get("sessionId")
        limit = body.get("limit", 50)
        
        history = get_history(user_id, session_id, limit)
        
        return func.HttpResponse(
            json.dumps({"history": history}),
            mimetype="application/json"
        )
    
    else:
        return func.HttpResponse('{"error":"unknown action"}', status_code=400, mimetype="application/json")