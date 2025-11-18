import time
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.models.schemas import URLRequest, APIResponse
from app.services.pdf_extractor import PDFExtractor
from app.services.url_extractor import URLExtractor
from app.services.content_cleaner import ContentCleaner
from app.services.keyword_extractor import KeywordExtractor
from app.services.recommender import Recommender

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
    max_keywords: int = Form(default=10, ge=1, le=50)
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
