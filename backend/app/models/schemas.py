from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime


# Request schemas
class URLRequest(BaseModel):
    url: HttpUrl
    max_keywords: int = Field(default=10, ge=1, le=50)


class KeywordSearchRequest(BaseModel):
    keywords: list[str]
    limit: int = Field(default=10, ge=1, le=50)
    min_score: float = Field(default=0.3, ge=0.0, le=1.0)


# Response schemas
class KeywordItem(BaseModel):
    keyword: str
    score: float
    type: str  # "phrase", "entity", "noun"


class EntityExtraction(BaseModel):
    persons: list[str] = []
    locations: list[str] = []
    organizations: list[str] = []
    dates: list[str] = []
    misc: list[str] = []


class NewsRecommendation(BaseModel):
    id: str
    title: str
    summary: str
    url: Optional[str] = None
    published_date: Optional[str] = None
    relevance_score: float
    matched_keywords: list[str]


class ExtractionResponse(BaseModel):
    content: str
    word_count: int
    keywords: list[KeywordItem]
    entities: EntityExtraction
    recommendations: list[NewsRecommendation]


class APIResponse(BaseModel):
    status: str = "success"
    data: dict
    processing_time_ms: Optional[int] = None
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    database: str
    nlp_model: str


# Database document schemas
class NewsArticleCreate(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    url: Optional[str] = None
    published_date: Optional[datetime] = None
    source: Optional[str] = None
    keywords: list[str] = []
    entities: EntityExtraction = EntityExtraction()


class NewsArticleInDB(NewsArticleCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class ExtractionLog(BaseModel):
    input_type: str  # "pdf" or "url"
    input_source: str
    extracted_keywords: list[str]
    recommendations_count: int
    processing_time_ms: int
    status: str  # "success" or "failed"
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
