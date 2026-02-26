# backend/models.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Connects to your AWS MongoDB Atlas cluster
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("❌ MONGODB_URI is missing from your .env file!")
client = MongoClient(MONGO_URI)

# Maps to the exact database and collection from your .js seed files
db = client.Entry_shield
visits_collection = db.gate_passes

try:
    # Ensure studentId is unique as per 04-gate-passes-student.js
    visits_collection.create_index("studentId", unique=True, sparse=True)
    print("✅ AWS MongoDB Connected. Indexes verified.")
except Exception as e:
    print(f"⚠️ Index Notice: {e}")