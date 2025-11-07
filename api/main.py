from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, Security, Request, status
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from utils.config import settings
from utils.logger import get_logger
from utils.database import db

logger = get_logger(__name__)


def get_rate_limit_key(request: Request) -> str:
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"api_key:{api_key}"

    return f"ip:{get_remote_address(request)}"



limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[f"{settings.rate_limit_per_hour}/hour"],
    storage_uri="memory://",
    strategy="fixed-window",
    swallow_errors=False
)


app = FastAPI(
    title="Book Crawler API",
    description="""
    RESTful API for book data from books.toscrape.com
    
    ## Features
    * Query books with advanced filters
    * Sort by price, rating, or reviews
    * Pagination support
    * Track data changes over time
    * API key authentication
    * Rate limiting
    
    ## Authentication
    All endpoints (except root and health) require API key authentication.
    Add header: `X-API-Key: your-api-key`
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SlowAPIMiddleware)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        logger.warning("API request without API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing. Add header: X-API-Key"
        )

    if api_key != settings.api_key:
        logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    return api_key


@app.on_event("startup")
async def startup_event():
    try:
        await db.connect()
        logger.info("API server started and connected to database")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    await db.disconnect()
    logger.info("API server shut down")


@app.get("/", tags=["Root"])
async def root():

    return {
        "message": "Book Crawler API",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "books": "/books",
            "book_detail": "/books/{book_id}",
            "changes": "/changes",
            "health": "/health"
        },
        "authentication": "Required for all endpoints except / and /health",
        "rate_limit": f"{settings.rate_limit_per_hour} requests per hour"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    try:
        await db.books_collection.find_one({})
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@app.get("/books", tags=["Books"])
@limiter.limit(f"{settings.rate_limit_per_hour}/hour")
async def get_books(
    request: Request,
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    rating: Optional[int] = None,
    sort_by: Optional[str] = "name",
    page: int = 1,
    page_size: int = 20,
    api_key: str = Depends(verify_api_key)
):

    try:
        valid_sort_fields = ["rating", "price", "reviews", "name"]
        if sort_by not in valid_sort_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort_by field. Must be one of: {', '.join(valid_sort_fields)}"
            )

        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page must be >= 1"
            )

        if page_size < 1 or page_size > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page size must be between 1 and 100"
            )

        skip = (page - 1) * page_size

        books, total = await db.query_books(
            category=category,
            min_price=min_price,
            max_price=max_price,
            rating=rating,
            sort_by=sort_by,
            skip=skip,
            limit=page_size
        )

        for book in books:
            if 'raw_html' in book:
                del book['raw_html']
            if '_id' in book:
                book['_id'] = str(book['_id'])

        total_pages = (total + page_size - 1) // page_size

        logger.info(f"API: Returning {len(books)} books (page {page}/{total_pages})")

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "books": books
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/books/{book_id}", tags=["Books"])
@limiter.limit(f"{settings.rate_limit_per_hour}/hour")
async def get_book_by_id(
    request: Request,
    book_id: str,
    api_key: str = Depends(verify_api_key)
):
    try:
        book = await db.get_book_by_id(book_id)

        if not book:
            logger.warning(f"Book not found: {book_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID '{book_id}' not found"
            )

        if '_id' in book:
            book['_id'] = str(book['_id'])

        logger.info(f"API: Returning book details for {book_id}")

        return book

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving book {book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/changes", tags=["Changes"])
@limiter.limit(f"{settings.rate_limit_per_hour}/hour")
async def get_changes(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    api_key: str = Depends(verify_api_key)
):
    try:
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page must be >= 1"
            )

        if page_size < 1 or page_size > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page size must be between 1 and 100"
            )

        skip = (page - 1) * page_size

        changes, total = await db.get_recent_changes(limit=page_size, skip=skip)


        for change in changes:
            if '_id' in change:
                change['_id'] = str(change['_id'])

        total_pages = (total + page_size - 1) // page_size

        logger.info(f"API: Returning {len(changes)} changes (page {page}/{total_pages})")

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "changes": changes
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving changes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )



@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Endpoint not found",
            "available_endpoints": {
                "root": "/",
                "health": "/health",
                "books": "/books",
                "book_detail": "/books/{book_id}",
                "changes": "/changes",
                "documentation": "/docs"
            }
        }
    )



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )