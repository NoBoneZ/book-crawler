
import asyncio
import pytest
from datetime import datetime
from typing import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient

from utils.config import settings
from utils.models import Book, BookPrice, CrawlMetadata, ChangeLog
from utils.database import Database


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[Database, None]:
    test_database = Database()

    original_db_name = settings.mongodb_db_name
    settings.mongodb_db_name = "book_crawler_test"

    try:
        await test_database.connect()

        yield test_database

    finally:
        if test_database.client:
            await test_database.client.drop_database("book_crawler_test")
            await test_database.disconnect()

        settings.mongodb_db_name = original_db_name


@pytest.fixture
def sample_book() -> Book:
    return Book(
        book_id="test_book_001",
        upc="test_upc_123",
        name="Test Book Title",
        description="This is a test book description for testing purposes.",
        category="Fiction",
        price=BookPrice(
            including_tax=25.99,
            excluding_tax=24.99,
            currency="£"
        ),
        availability="In stock (15 available)",
        availability_count=15,
        num_reviews=10,
        rating="Four",
        rating_numeric=4,
        image_url="https://example.com/test-book.jpg",
        metadata=CrawlMetadata(
            crawl_timestamp=datetime.utcnow(),
            source_url="https://example.com/test-book",
            status="success",
            content_hash="test_hash_123"
        ),
        raw_html="<html>Test HTML</html>"
    )


@pytest.fixture
def sample_books() -> list[Book]:
    books = []
    categories = ["Fiction", "History", "Science", "Poetry"]
    ratings = [3, 4, 5]

    for i in range(10):
        book = Book(
            book_id=f"test_book_{i:03d}",
            upc=f"test_upc_{i:03d}",
            name=f"Test Book {i}",
            description=f"Description for test book {i}",
            category=categories[i % len(categories)],
            price=BookPrice(
                including_tax=10.0 + (i * 5),
                excluding_tax=9.0 + (i * 5),
                currency="£"
            ),
            availability=f"In stock ({10 + i} available)",
            availability_count=10 + i,
            num_reviews=i * 2,
            rating=["Three", "Four", "Five"][i % 3],
            rating_numeric=ratings[i % len(ratings)],
            image_url=f"https://example.com/book-{i}.jpg",
            metadata=CrawlMetadata(
                crawl_timestamp=datetime.utcnow(),
                source_url=f"https://example.com/book-{i}",
                status="success",
                content_hash=f"hash_{i}"
            ),
            raw_html=f"<html>Book {i}</html>"
        )
        books.append(book)

    return books


@pytest.fixture
def sample_change_log() -> ChangeLog:
    return ChangeLog(
        book_id="test_book_001",
        book_name="Test Book",
        change_type="updated",
        changed_fields=["price.including_tax", "availability_count"],
        old_values={
            "price.including_tax": 25.99,
            "availability_count": 15
        },
        new_values={
            "price.including_tax": 22.99,
            "availability_count": 12
        },
        detected_at=datetime.utcnow()
    )