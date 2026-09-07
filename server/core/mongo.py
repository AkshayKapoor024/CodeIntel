from pymongo import MongoClient
import os 
import certifi
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGODB_URL')

# Adding Atlas URL with CA certs for reliable TLS on all platforms
if MONGO_URI and "mongodb+srv://" in MONGO_URI:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
else:
    client = MongoClient(MONGO_URI)

# Database
db = client["code_intel"]

# Collections
users = db["users"]
sessions = db['sessions']
chat_history = db['chat_history']
