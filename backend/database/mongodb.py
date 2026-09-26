from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()
def get_mongo_url() -> str:
    return os.getenv("MONGO_URL") or os.getenv("MONGODB_URI") or "mongodb://localhost:27017"

client = None
db = None

async def init_mongodb():
    global client, db
    try:
        url = get_mongo_url()
        client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=2000)
        # Verify connection
        await client.server_info()
        db = client.sentinel
        return True
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return False

def get_db():
    return db
