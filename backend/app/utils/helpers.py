from datetime import datetime
from bson import ObjectId


def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict."""
    if doc is None:
        return None

    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = serialize_doc(value)
        elif isinstance(value, list):
            result[key] = [
                serialize_doc(item) if isinstance(item, dict)
                else str(item) if isinstance(item, ObjectId)
                else item
                for item in value
            ]
        else:
            result[key] = value

    return result


def normalize_keyword(keyword: str) -> str:
    """Normalize keyword for consistent matching."""
    return keyword.lower().strip()


def calculate_relevance(matched_count: int, total_keywords: int) -> float:
    """Calculate relevance score based on keyword matches."""
    if total_keywords == 0:
        return 0.0
    return round(matched_count / total_keywords, 2)
