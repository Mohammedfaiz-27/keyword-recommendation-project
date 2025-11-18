from fastapi import APIRouter
from app.models.database import get_database
from app.models.schemas import HealthResponse
from app.services.keyword_extractor import KeywordExtractor

router = APIRouter(prefix="/health", tags=["Health"])

# Singleton for keyword extractor
keyword_extractor = KeywordExtractor()


@router.get("", response_model=HealthResponse)
async def health_check():
    """Check API health status."""
    # Check database connection
    try:
        db = get_database()
        await db.command("ping")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # Check NLP model
    nlp_status = "loaded" if keyword_extractor.is_loaded() else "not loaded"

    overall_status = "healthy" if db_status == "connected" and nlp_status == "loaded" else "degraded"

    return HealthResponse(
        status=overall_status,
        database=db_status,
        nlp_model=nlp_status
    )


@router.get("/db-info")
async def database_info():
    """Get database information and sample data."""
    try:
        db = get_database()

        # Get all collections
        collections = await db.list_collection_names()

        result = {
            "status": "connected",
            "collections": {},
            "sample_keywords": []
        }

        for collection_name in collections:
            collection = db[collection_name]
            count = await collection.count_documents({})

            # Get sample document
            sample = await collection.find_one()

            collection_info = {
                "document_count": count,
                "fields": list(sample.keys()) if sample else []
            }

            # Check for keywords field
            if sample:
                for kw_field in ['keywords', 'tags', 'categories', 'topics']:
                    if kw_field in sample:
                        kw_value = sample[kw_field]
                        if isinstance(kw_value, list) and len(kw_value) > 0:
                            collection_info["keyword_field"] = kw_field
                            collection_info["sample_keywords"] = kw_value[:10]
                            result["sample_keywords"] = kw_value[:10]
                        break

            result["collections"][collection_name] = collection_info

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
