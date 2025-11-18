"""
Script to explore the MongoDB Atlas database structure.
This helps understand the schema of existing news data.

Usage:
    python scripts/explore_database.py
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json
from bson import ObjectId


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)


async def explore_database():
    """Explore the database structure."""
    # Connection string with URL-encoded password
    MONGODB_URL = "mongodb+srv://smart_radar_db_user:smart-radar%40123@smart-radar.exjrbpk.mongodb.net/?retryWrites=true&w=majority"
    DB_NAME = "smart_radar"

    print(f"Connecting to MongoDB Atlas...")
    client = AsyncIOMotorClient(MONGODB_URL)

    try:
        # Test connection
        await client.admin.command('ping')
        print("Successfully connected to MongoDB Atlas!\n")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    db = client[DB_NAME]

    # List all collections
    collections = await db.list_collection_names()
    print(f"Database: {DB_NAME}")
    print(f"Collections found: {collections}\n")

    # Explore each collection
    for collection_name in collections:
        print(f"\n{'='*50}")
        print(f"Collection: {collection_name}")
        print(f"{'='*50}")

        collection = db[collection_name]

        # Get document count
        count = await collection.count_documents({})
        print(f"Document count: {count}")

        if count > 0:
            # Get sample document
            sample = await collection.find_one()
            print(f"\nSample document structure:")
            print(f"Fields: {list(sample.keys())}")

            # Print sample with truncated values
            print(f"\nSample document:")
            for key, value in sample.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"  {key}: {value[:100]}...")
                elif isinstance(value, list) and len(value) > 5:
                    print(f"  {key}: {value[:5]}... (total: {len(value)} items)")
                else:
                    print(f"  {key}: {value}")

            # Check for keywords field
            if 'keywords' in sample:
                print(f"\n  Keywords field type: {type(sample['keywords'])}")
                if isinstance(sample['keywords'], list):
                    print(f"  Sample keywords: {sample['keywords'][:10]}")

            # Get all unique field names across documents
            pipeline = [
                {"$project": {"fields": {"$objectToArray": "$$ROOT"}}},
                {"$unwind": "$fields"},
                {"$group": {"_id": "$fields.k"}},
                {"$limit": 50}
            ]
            cursor = collection.aggregate(pipeline)
            all_fields = [doc['_id'] async for doc in cursor]
            print(f"\nAll fields in collection: {all_fields}")

    client.close()
    print("\n\nDone exploring database!")


if __name__ == "__main__":
    asyncio.run(explore_database())
