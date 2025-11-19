import time
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from app.models.schemas import URLRequest, APIResponse
from app.models.database import get_database
from app.services.pdf_extractor import PDFExtractor
from app.services.url_extractor import URLExtractor
from app.services.content_cleaner import ContentCleaner
from app.services.keyword_extractor import KeywordExtractor
from app.services.recommender import Recommender
from app.services.link_extractor import LinkExtractor
from app.services.webpage_crawler import WebpageCrawler
from app.services.optimized_search import OptimizedSearchService
from app.services.pdf_link_scraper import PDFLinkScraper

logger = logging.getLogger(__name__)


# Response Models for PDF Link Extraction
class KeywordItem(BaseModel):
    keyword: str
    score: float
    type: str


class RelatedNewsItem(BaseModel):
    title: Optional[str] = None
    content_preview: str = ""
    source: str = ""
    relevance_score: float
    url: Optional[str] = None
    published_at: Optional[str] = None
    matched_keywords: List[str] = []


class EntityItem(BaseModel):
    persons: List[str] = []
    locations: List[str] = []
    organizations: List[str] = []
    dates: List[str] = []
    misc: List[str] = []


class LinkAnalysisResult(BaseModel):
    source_link: str
    crawl_success: bool
    page_title: str = ""
    scraped_content_preview: str = ""  # First 500 chars of scraped content
    word_count: int = 0
    keywords: List[KeywordItem]
    entities: EntityItem = EntityItem()
    related_news: List[RelatedNewsItem]
    error_message: str = ""
    crawl_time_ms: int = 0


class PDFLinkExtractionResponse(BaseModel):
    success: bool
    total_links_found: int
    total_links_processed: int
    processing_time_ms: int
    results: List[LinkAnalysisResult]
    errors: List[str] = []

router = APIRouter(prefix="/extract", tags=["Extraction"])

# Initialize services
pdf_extractor = PDFExtractor()
url_extractor = URLExtractor()
content_cleaner = ContentCleaner()
keyword_extractor = KeywordExtractor()
recommender = Recommender()


@router.post("/pdf", response_model=APIResponse)
async def extract_from_pdf(
    file: UploadFile = File(...),
    max_keywords: int = Form(default=100, ge=1, le=500)
):
    """
    Extract content and keywords from uploaded PDF file.

    Returns cleaned content, keywords, entities, and news recommendations.
    """
    start_time = time.time()

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    try:
        # Step 1: Extract text from PDF
        raw_text = await pdf_extractor.extract(file)

        # Step 2: Clean the extracted text
        clean_text = content_cleaner.clean(raw_text)
        word_count = content_cleaner.get_word_count(clean_text)

        # Step 3: Extract keywords and entities
        keywords, entities = keyword_extractor.extract(clean_text, max_keywords)

        # Step 4: Get recommendations
        recommendations = await recommender.get_recommendations(keywords)

        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)

        # Log extraction
        await recommender.log_extraction({
            "input_type": "pdf",
            "input_source": file.filename,
            "extracted_keywords": [k.keyword for k in keywords],
            "recommendations_count": len(recommendations),
            "processing_time_ms": processing_time,
            "status": "success",
            "error_message": None,
            "created_at": datetime.utcnow()
        })

        return APIResponse(
            status="success",
            data={
                "content": clean_text,
                "word_count": word_count,
                "keywords": [k.model_dump() for k in keywords],
                "entities": entities.model_dump(),
                "recommendations": [r.model_dump() for r in recommendations]
            },
            processing_time_ms=processing_time
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log failed extraction
        await recommender.log_extraction({
            "input_type": "pdf",
            "input_source": file.filename,
            "extracted_keywords": [],
            "recommendations_count": 0,
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "status": "failed",
            "error_message": str(e),
            "created_at": datetime.utcnow()
        })
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


@router.post("/url", response_model=APIResponse)
async def extract_from_url(request: URLRequest):
    """
    Extract content and keywords from web article URL.

    Returns cleaned content, keywords, entities, and news recommendations.
    """
    start_time = time.time()
    url_str = str(request.url)

    try:
        # Step 1: Extract content from URL
        result = await url_extractor.extract(url_str)
        raw_text = result.get("text", "")

        # Step 2: Clean the extracted text
        clean_text = content_cleaner.clean(raw_text)
        word_count = content_cleaner.get_word_count(clean_text)

        # Step 3: Extract keywords and entities
        keywords, entities = keyword_extractor.extract(clean_text, request.max_keywords)

        # Step 4: Get recommendations
        recommendations = await recommender.get_recommendations(keywords)

        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)

        # Log extraction
        await recommender.log_extraction({
            "input_type": "url",
            "input_source": url_str,
            "extracted_keywords": [k.keyword for k in keywords],
            "recommendations_count": len(recommendations),
            "processing_time_ms": processing_time,
            "status": "success",
            "error_message": None,
            "created_at": datetime.utcnow()
        })

        return APIResponse(
            status="success",
            data={
                "content": clean_text,
                "word_count": word_count,
                "keywords": [k.model_dump() for k in keywords],
                "entities": entities.model_dump(),
                "recommendations": [r.model_dump() for r in recommendations],
                "source_title": result.get("title", ""),
                "source_authors": result.get("authors", [])
            },
            processing_time_ms=processing_time
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log failed extraction
        await recommender.log_extraction({
            "input_type": "url",
            "input_source": url_str,
            "extracted_keywords": [],
            "recommendations_count": 0,
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "status": "failed",
            "error_message": str(e),
            "created_at": datetime.utcnow()
        })
        raise HTTPException(status_code=500, detail=f"Failed to process URL: {str(e)}")


# PDF Link Extraction Endpoint
@router.post(
    "/pdf-links",
    response_model=PDFLinkExtractionResponse,
    summary="Extract links from PDF, scrape webpages, and analyze",
    description="""
    Extracts all hyperlinks from a PDF document, VISITS each link to scrape the webpage content,
    extracts keywords from the SCRAPED CONTENT (not the URL), and searches for related news.

    Returns grouped results for each link with:
    - Scraped webpage content preview
    - Keywords extracted from the webpage
    - Related news articles from database
    """
)
async def extract_pdf_links(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to extract links from"),
    max_keywords_per_link: int = Query(
        default=15,
        ge=5,
        le=500,
        description="Maximum keywords to extract per link"
    ),
    max_news_per_link: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum related news items per link"
    ),
    min_relevance_score: float = Query(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score for news items"
    ),
    crawl_timeout: int = Query(
        default=15,
        ge=5,
        le=60,
        description="Timeout in seconds for each URL crawl"
    )
):
    """
    Main endpoint for PDF link extraction and webpage scraping.

    This endpoint:
    1. Extracts URLs from the PDF
    2. Actually VISITS each URL and scrapes the webpage content
    3. Extracts keywords from the SCRAPED CONTENT
    4. Searches database for related news using those keywords
    """
    start_time = time.time()
    errors = []

    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="File must be a PDF document"
        )

    try:
        # Read PDF content
        pdf_content = await file.read()

        if len(pdf_content) == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty"
            )

        # Initialize the PDF Link Scraper service
        scraper = PDFLinkScraper(timeout=crawl_timeout)

        db = get_database()
        search_service = OptimizedSearchService(db)

        # Step 1 & 2: Extract links from PDF and scrape each webpage
        logger.info("=" * 60)
        logger.info("STEP 1: Extracting URLs from PDF...")
        urls, scraped_pages = await scraper.extract_and_scrape(pdf_content)
        total_links_found = len(urls)
        logger.info("=" * 60)

        if not urls:
            return PDFLinkExtractionResponse(
                success=True,
                total_links_found=0,
                total_links_processed=0,
                processing_time_ms=int((time.time() - start_time) * 1000),
                results=[],
                errors=["No links found in the PDF"]
            )

        # Step 3: Extract keywords from scraped content
        logger.info("=" * 60)
        logger.info("STEP 2: Extracting keywords from SCRAPED WEBPAGE CONTENT...")

        all_keywords = []
        all_entities = []
        successful_scrapes = []

        for page in scraped_pages:
            if page.success and page.content:
                # Clean the scraped content
                cleaned_content = content_cleaner.clean(page.content)

                # Extract keywords and entities from the WEBPAGE CONTENT (not URL!)
                keywords, entities = keyword_extractor.extract(cleaned_content, max_keywords_per_link)
                kw_list = [
                    {"keyword": kw.keyword, "score": kw.score, "type": kw.type}
                    for kw in keywords
                ]
                all_keywords.append(kw_list)
                all_entities.append(entities)
                successful_scrapes.append((page, cleaned_content))

                # Log what was extracted
                logger.info(f"Scraped: {page.url}")
                logger.info(f"  Title: {page.title}")
                logger.info(f"  Content: {len(cleaned_content)} chars, {page.word_count} words")
                logger.info(f"  Keywords extracted from webpage:")
                for kw in kw_list[:5]:
                    logger.info(f"    - {kw['keyword']} (score: {kw['score']})")
            else:
                errors.append(f"Failed to scrape {page.url}: {page.error_message}")
                logger.warning(f"Failed to scrape {page.url}: {page.error_message}")

        logger.info("=" * 60)

        # Step 4: Search database for related news using the old Recommender
        logger.info("STEP 3: Searching database for related news...")
        all_news_results = []

        for idx, kw_list in enumerate(all_keywords):
            # Convert dict format to KeywordItem objects for Recommender
            from app.models.schemas import KeywordItem as SchemaKeywordItem
            keyword_items = [
                SchemaKeywordItem(keyword=kw['keyword'], score=kw['score'], type=kw['type'])
                for kw in kw_list
            ]

            # Use the old Recommender service
            recommendations = await recommender.get_recommendations(
                keyword_items,
                limit=max_news_per_link,
                min_score=min_relevance_score
            )
            all_news_results.append(recommendations)

        # Step 5: Build response
        results = []
        keyword_index = 0

        for page in scraped_pages:
            if page.success and page.content:
                # Get keywords, entities and news for this scraped page
                keywords = all_keywords[keyword_index] if keyword_index < len(all_keywords) else []
                entities = all_entities[keyword_index] if keyword_index < len(all_entities) else None
                news = all_news_results[keyword_index] if keyword_index < len(all_news_results) else []

                # Get cleaned content
                _, cleaned_content = successful_scrapes[keyword_index] if keyword_index < len(successful_scrapes) else (None, "")
                content_preview = cleaned_content[:500] + "..." if len(cleaned_content) > 500 else cleaned_content

                # Format keywords
                formatted_keywords = [
                    KeywordItem(
                        keyword=kw['keyword'],
                        score=kw['score'],
                        type=kw['type']
                    )
                    for kw in keywords
                ]

                # Format entities
                formatted_entities = EntityItem()
                if entities:
                    formatted_entities = EntityItem(
                        persons=entities.persons,
                        locations=entities.locations,
                        organizations=entities.organizations,
                        dates=entities.dates,
                        misc=entities.misc
                    )

                # Format news items from NewsRecommendation objects
                formatted_news = []
                for rec in news:
                    formatted_news.append(RelatedNewsItem(
                        title=rec.title,
                        content_preview=rec.summary,
                        source="database",
                        relevance_score=rec.relevance_score,
                        url=rec.url,
                        published_at=rec.published_date,
                        matched_keywords=rec.matched_keywords
                    ))

                results.append(LinkAnalysisResult(
                    source_link=page.url,
                    crawl_success=True,
                    page_title=page.title,
                    scraped_content_preview=content_preview,
                    word_count=page.word_count,
                    keywords=formatted_keywords,
                    entities=formatted_entities,
                    related_news=formatted_news,
                    crawl_time_ms=page.scrape_time_ms
                ))

                keyword_index += 1
            else:
                # Failed scrape
                results.append(LinkAnalysisResult(
                    source_link=page.url,
                    crawl_success=False,
                    scraped_content_preview="",
                    word_count=0,
                    keywords=[],
                    related_news=[],
                    error_message=page.error_message
                ))

        # Calculate total processing time
        processing_time = int((time.time() - start_time) * 1000)

        # Log extraction to database (background)
        background_tasks.add_task(
            log_link_extraction,
            db,
            file.filename,
            total_links_found,
            len(successful_scrapes),
            processing_time,
            errors
        )

        logger.info(f"Completed! Found {total_links_found} links, successfully scraped {len(successful_scrapes)}")

        return PDFLinkExtractionResponse(
            success=True,
            total_links_found=total_links_found,
            total_links_processed=len(successful_scrapes),
            processing_time_ms=processing_time,
            results=results,
            errors=errors
        )

    except Exception as e:
        logger.error(f"PDF link extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process PDF: {str(e)}"
        )


async def log_link_extraction(
    db,
    filename: str,
    links_found: int,
    links_processed: int,
    processing_time: int,
    errors: List[str]
):
    """Log the extraction to database for analytics."""
    try:
        await db.link_extraction_logs.insert_one({
            'filename': filename,
            'links_found': links_found,
            'links_processed': links_processed,
            'processing_time_ms': processing_time,
            'errors': errors,
            'created_at': datetime.utcnow()
        })
    except Exception as e:
        logger.error(f"Failed to log extraction: {e}")
