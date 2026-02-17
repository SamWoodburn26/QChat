import os
from pymongo import MongoClient
from dotenv import load_dotenv
import certifi

load_dotenv()

class Database:
    _instance = None
    _client = None
    _db = None
    
    #Same objects keep being returned
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance
    
    def connect(self):
        if self._client is None:
            mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
            db_name = os.getenv('DB_NAME', 'qchat')
            kwargs = {}
            if mongodb_uri.startswith('mongodb+srv') or 'mongodb.net' in mongodb_uri:
                kwargs['tls'] = True
                kwargs['tlsCAFile'] = certifi.where()
                kwargs['serverSelectionTimeoutMS'] = 4000
            self._client = MongoClient(mongodb_uri, **kwargs)
            # Actively verify connectivity to avoid lazy failures later
            try:
                self._client.admin.command('ping')
                print("MongoDB ping successful")
            except Exception as e:
                print("MongoDB ping failed:", repr(e))
                # Keep the client but note that operations may fail until network is fixed
            self._db = self._client[db_name]
            print(f"Using database: {db_name}")
        return self._db
    
    def get_collection(self, collection_name):
        if self._db is None:
            self.connect()
        return self._db[collection_name]

# Singleton instance
db = Database()

# USER SERVICE SETUP
from services.user_service import UserService

# Get MongoDB database instance
_db_instance = db.connect()

# Get users collection
users_collection = _db_instance["users"]

# Initialize user service
user_service = UserService(users_collection)

# Export for use in Azure Functions
__all__ = ['db', 'user_service', 'users_collection']

print("User service initialized")