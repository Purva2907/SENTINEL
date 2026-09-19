from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")

client = None
db = None

async def init_mongodb():
    global client, db
    try:
        client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=2000)
        # Verify connection
        await client.server_info()
        db = client.sentinel
        return True
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return False

def get_db():
    return db
