from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import TEXT, ASCENDING
from app.config import get_settings

settings = get_settings()


class Database:
    client: AsyncIOMotorClient = None
    db = None


db = Database()


async def connect_to_mongo():
    """Create database connection."""
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    db.db = db.client[settings.MONGODB_DB_NAME]

    # Create indexes
    await create_indexes()

    print(f"Connected to MongoDB: {settings.MONGODB_DB_NAME}")


async def close_mongo_connection():
    """Close database connection."""
    if db.client:
        db.client.close()
        print("Closed MongoDB connection")


async def create_indexes():
    """Create necessary indexes for performance."""
    # Text index for full-text search on news articles
    await db.db.news_articles.create_index([
        ("title", TEXT),
        ("content", TEXT),
        ("keywords", TEXT)
    ], name="text_search_index", default_language="english")

    # Regular index on keywords array for exact matching
    await db.db.news_articles.create_index([("keywords", ASCENDING)])

    # Index on published_date for sorting
    await db.db.news_articles.create_index([("published_date", ASCENDING)])

    # Index for keyword_index collection
    await db.db.keyword_index.create_index([("keyword", ASCENDING)], unique=True)
    await db.db.keyword_index.create_index([("keyword", TEXT)])


def get_database():
    """Get database instance."""
    return db.db
