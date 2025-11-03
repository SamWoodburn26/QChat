import azure.functions as func
import json, os
from datetime import datetime
from pymongo import MongoClient

# ollama to make the gemma model
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.prompts import ChatPromptTemplate


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

#It dynamically fills in the “question” field and sends it to the LLM.
prompt_template = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{question}")
])

#Each time the function is called, it returns the current connection 
# and checks whether the connection is active using db.command(‘ping’). 
def get_db():
    """MongoDB connection"""
    global mongo_client, db
    if db is None:
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client[DATABASE_NAME]
        db.command('ping')
        print("MongoDB connected")
    return db


def save_message(user_id, session_id, message, response):
    """Save chat to MongoDB"""
    try:
        database = get_db()
        chat_logs = database[CHAT_LOGS_COLLECTION]
        
        doc = {
            'userId': user_id,
            'sessionId': session_id,
            'timestamp': datetime.utcnow(),
            'message': message,
            'response': response
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
                'sessionId': doc.get('sessionId')
            })
        
        return messages[::-1]
    except Exception as e:
        print(f"History error: {e}")
        return []



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
        
        try:
            formatted = prompt_template.format_messages(question=msg)
            reply = llm.invoke(formatted).content.strip()
        except Exception as e:
            print("LLM error: ", repr(e))
            reply = "I'm having trouble right now. Please try again or contact IT Help Desk."
        
        # MongoDB'ye kaydet
        msg_id = save_message(user_id, session_id, msg, reply)
        
        return func.HttpResponse(
            json.dumps({
                "response": reply,
                "messageId": msg_id,
                "timestamp": datetime.utcnow().isoformat()
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