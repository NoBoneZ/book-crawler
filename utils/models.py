from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class BookRating(str, Enum):
    ONE = "One"
    TWO = "Two"
    THREE = "Three"
    FOUR = "Four"
    FIVE = "Five"

    @property
    def numeric_value(self) -> int:
        mapping = {
            "One": 1,
            "Two": 2,
            "Three": 3,
            "Four": 4,
            "Five": 5
        }
        return mapping.get(self.value, 0)


class BookPrice(BaseModel):
    including_tax: float = Field(..., ge=0, description="Price including tax")
    excluding_tax: float = Field(..., ge=0, description="Price excluding tax")
    currency: str = Field(default="£", description="Currency symbol")

    @field_validator('including_tax', 'excluding_tax', mode='before')
    @classmethod
    def parse_price(cls, v):
        if isinstance(v, str):
            cleaned = v.replace('£', '').replace('$', '').replace(',', '').strip()
            return float(cleaned)
        return v


class CrawlMetadata(BaseModel):
    crawl_timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_url: str = Field(..., description="URL where book was found")
    status: str = Field(default="success", description="Crawl status")
    error_message: Optional[str] = None
    retry_count: int = Field(default=0, ge=0)
    content_hash: Optional[str] = Field(None, description="SHA-256 hash for change detection")


class Book(BaseModel):
    book_id: Optional[str] = Field(None, description="Unique identifier")
    upc: Optional[str] = Field(None, description="Universal Product Code")

    name: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, description="Book description")
    category: str = Field(..., description="Book category")
    price: BookPrice

    availability: str = Field(..., description="Availability status text")
    availability_count: Optional[int] = Field(None, ge=0, description="Number in stock")

    num_reviews: int = Field(default=0, ge=0, description="Number of reviews")
    rating: Optional[str] = Field(None, description="Rating as text (One, Two, etc.)")
    rating_numeric: Optional[int] = Field(None, ge=0, le=5, description="Rating as number (1-5)")

    image_url: Optional[str] = Field(None, description="URL to book cover image")

    metadata: CrawlMetadata

    raw_html: Optional[str] = Field(None, description="Raw HTML for fallback")

    class Config:
        json_schema_extra = {
            "example": {
                "book_id": "a-light-in-the-attic_1000",
                "name": "A Light in the Attic",
                "description": "It's hard to imagine a world without...",
                "category": "Poetry",
                "price": {
                    "including_tax": 51.77,
                    "excluding_tax": 51.77,
                    "currency": "£"
                },
                "availability": "In stock (22 available)",
                "availability_count": 22,
                "num_reviews": 0,
                "rating": "Three",
                "rating_numeric": 3,
                "image_url": "https://books.toscrape.com/media/cache/2c/da/2cdad67c44b002e7ead0cc35693c0e8b.jpg",
                "metadata": {
                    "crawl_timestamp": "2024-01-15T10:30:00Z",
                    "source_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
                    "status": "success"
                }
            }
        }



class ChangeLog(BaseModel):
    book_id: str
    book_name: str
    change_type: str = Field(..., description="Type: new, updated, deleted")
    changed_fields: List[str] = Field(default_factory=list)
    old_values: Optional[dict] = Field(None, description="Values before change")
    new_values: Optional[dict] = Field(None, description="Values after change")
    detected_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "book_id": "abc123",
                "book_name": "Sample Book",
                "change_type": "updated",
                "changed_fields": ["price.including_tax", "availability_count"],
                "old_values": {
                    "price.including_tax": 51.77,
                    "availability_count": 22
                },
                "new_values": {
                    "price.including_tax": 45.99,
                    "availability_count": 15
                },
                "detected_at": "2024-01-16T10:30:00Z"
            }
        }



class BookQuery(BaseModel):
    category: Optional[str] = None
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    rating: Optional[int] = Field(None, ge=1, le=5)
    sort_by: Optional[str] = Field(None, pattern="^(rating|price|reviews|name)$")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)