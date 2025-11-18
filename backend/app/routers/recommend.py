from fastapi import APIRouter
from app.models.schemas import KeywordSearchRequest, APIResponse, KeywordItem
from app.services.recommender import Recommender

router = APIRouter(prefix="/recommend", tags=["Recommendations"])

recommender = Recommender()


@router.post("", response_model=APIResponse)
async def get_recommendations(request: KeywordSearchRequest):
    """
    Get news recommendations for given keywords.

    Use this endpoint when you already have keywords extracted
    and just want to find matching news articles.
    """
    # Convert string keywords to KeywordItem objects
    keyword_items = [
        KeywordItem(keyword=kw, score=1.0, type="phrase")
        for kw in request.keywords
    ]

    # Get recommendations
    recommendations = await recommender.get_recommendations(
        keyword_items,
        limit=request.limit,
        min_score=request.min_score
    )

    return APIResponse(
        status="success",
        data={
            "recommendations": [r.model_dump() for r in recommendations],
            "total_matches": len(recommendations)
        }
    )
