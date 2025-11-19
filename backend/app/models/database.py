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

    # Indexes for link extraction feature
    await setup_link_extraction_indexes()


async def setup_link_extraction_indexes():
    """Create indexes for link extraction feature collections."""
    try:
        # Link extraction logs - track all PDF link extractions
        await db.db.link_extraction_logs.create_index([("created_at", ASCENDING)])
        await db.db.link_extraction_logs.create_index([("filename", ASCENDING)])

        # Link crawl cache - cache crawled webpage content
        try:
            await db.db.link_crawl_cache.create_index([("url", ASCENDING)], unique=True)
        except Exception:
            pass  # Index may already exist
        await db.db.link_crawl_cache.create_index([("created_at", ASCENDING)])

        # Extraction jobs - track async job status
        try:
            await db.db.extraction_jobs.create_index([("job_id", ASCENDING)], unique=True)
        except Exception:
            pass  # Index may already exist
        await db.db.extraction_jobs.create_index([("status", ASCENDING)])
        await db.db.extraction_jobs.create_index([("created_at", ASCENDING)])

        # Indexes for searchable collections
        # posts_table
        try:
            await db.db.posts_table.create_index([("post_text", TEXT)])
        except Exception:
            pass
        await db.db.posts_table.create_index([("key_narratives", ASCENDING)])
        await db.db.posts_table.create_index([("posted_at", ASCENDING)])

        # print_daily
        try:
            await db.db.print_daily.create_index([("content", TEXT)])
        except Exception:
            pass
        await db.db.print_daily.create_index([("intelligence", ASCENDING)])
        await db.db.print_daily.create_index([("published_at", ASCENDING)])

        # print_magazines
        try:
            await db.db.print_magazines.create_index([("content", TEXT)])
        except Exception:
            pass
        await db.db.print_magazines.create_index([("intelligence", ASCENDING)])
        await db.db.print_magazines.create_index([("published_at", ASCENDING)])

        print("Link extraction indexes created successfully")

    except Exception as e:
        print(f"Warning: Some indexes may not have been created: {e}")


def get_database():
    """Get database instance."""
    return db.db
