import os
from pymongo import MongoClient
from dotenv import load_dotenv

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
            self._client = MongoClient(mongodb_uri)
            self._db = self._client['qchat']
            print("MongoDB connected successfully")
        return self._db
    
    def get_collection(self, collection_name):
        if self._db is None:
            self.connect()
        return self._db[collection_name]

# Singleton instance
db = Database()

