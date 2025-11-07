import pytest

from utils.database import Database


@pytest.mark.integration
class TestDatabaseConnection:

    @pytest.mark.asyncio
    async def test_connection(self, test_db):
        assert test_db.client is not None
        assert test_db.db is not None
        assert test_db.books_collection is not None

    @pytest.mark.asyncio
    async def test_collections_created(self, test_db):
        collections = await test_db.db.list_collection_names()
        assert isinstance(collections, list)


@pytest.mark.integration
class TestBookOperations:


    @pytest.mark.asyncio
    async def test_insert_book(self, test_db, sample_book):
        book_id = await test_db.insert_book(sample_book)

        assert book_id is not None
        assert isinstance(book_id, str)

    @pytest.mark.asyncio
    async def test_get_book_by_id(self, test_db, sample_book):
        await test_db.insert_book(sample_book)

        retrieved = await test_db.get_book_by_id(sample_book.book_id)

        assert retrieved is not None
        assert retrieved['book_id'] == sample_book.book_id
        assert retrieved['name'] == sample_book.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_book(self, test_db):
        result = await test_db.get_book_by_id("nonexistent_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_book(self, test_db, sample_book):
        await test_db.insert_book(sample_book)

        updated = await test_db.update_book(
            sample_book.book_id,
            {"price.including_tax": 30.99}
        )

        assert updated is True

        retrieved = await test_db.get_book_by_id(sample_book.book_id)
        assert retrieved['price']['including_tax'] == 30.99

    @pytest.mark.asyncio
    async def test_get_all_books(self, test_db, sample_books):

        for book in sample_books:
            await test_db.insert_book(book)

        all_books = await test_db.get_all_books()

        assert len(all_books) == len(sample_books)


@pytest.mark.integration
class TestBookQuerying:

    @pytest.mark.asyncio
    async def test_query_by_category(self, test_db, sample_books):
        for book in sample_books:
            await test_db.insert_book(book)

        books, total = await test_db.query_books(category="Fiction")

        assert total > 0
        assert all(book['category'] == "Fiction" for book in books)

    @pytest.mark.asyncio
    async def test_query_by_price_range(self, test_db, sample_books):
        for book in sample_books:
            await test_db.insert_book(book)

        books, total = await test_db.query_books(
            min_price=20.0,
            max_price=40.0
        )

        assert total > 0
        for book in books:
            price = book['price']['including_tax']
            assert 20.0 <= price <= 40.0

    @pytest.mark.asyncio
    async def test_query_by_rating(self, test_db, sample_books):
        for book in sample_books:
            await test_db.insert_book(book)

        books, total = await test_db.query_books(rating=5)

        assert all(book['rating_numeric'] == 5 for book in books)

    @pytest.mark.asyncio
    async def test_query_with_pagination(self, test_db, sample_books):
        for book in sample_books:
            await test_db.insert_book(book)

        page1, total = await test_db.query_books(skip=0, limit=5)
        assert len(page1) == 5

        page2, total = await test_db.query_books(skip=5, limit=5)
        assert len(page2) == 5

        page1_ids = {book['book_id'] for book in page1}
        page2_ids = {book['book_id'] for book in page2}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_query_sorting(self, test_db, sample_books):

        for book in sample_books:
            await test_db.insert_book(book)

        books, _ = await test_db.query_books(sort_by="price")
        prices = [book['price']['including_tax'] for book in books]
        assert prices == sorted(prices)

        books, _ = await test_db.query_books(sort_by="rating")
        ratings = [book['rating_numeric'] for book in books]
        assert ratings == sorted(ratings, reverse=True)


@pytest.mark.integration
class TestChangeOperations:

    @pytest.mark.asyncio
    async def test_log_change(self, test_db, sample_change_log):
        await test_db.log_change(sample_change_log)

        changes, total = await test_db.get_recent_changes(limit=10)
        assert total == 1
        assert changes[0]['book_id'] == sample_change_log.book_id

    @pytest.mark.asyncio
    async def test_get_recent_changes(self, test_db, sample_change_log):

        for i in range(5):
            sample_change_log.book_id = f"book_{i}"
            await test_db.log_change(sample_change_log)

        changes, total = await test_db.get_recent_changes(limit=3)

        assert len(changes) == 3
        assert total == 5


@pytest.mark.unit
class TestContentHashing:

    def test_compute_content_hash(self):
        book_data = {
            "name": "Test Book",
            "price": {"including_tax": 25.99},
            "availability": "In stock",
            "description": "Test description"
        }

        hash1 = Database.compute_content_hash(book_data)

        assert isinstance(hash1, str)
        assert len(hash1) == 64

    def test_same_data_same_hash(self):
        book_data = {
            "name": "Test Book",
            "price": {"including_tax": 25.99},
            "availability": "In stock"
        }

        hash1 = Database.compute_content_hash(book_data)
        hash2 = Database.compute_content_hash(book_data)

        assert hash1 == hash2

    def test_different_data_different_hash(self):
        book_data1 = {
            "name": "Test Book",
            "price": {"including_tax": 25.99}
        }

        book_data2 = {
            "name": "Test Book",
            "price": {"including_tax": 30.99}
        }

        hash1 = Database.compute_content_hash(book_data1)
        hash2 = Database.compute_content_hash(book_data2)

        assert hash1 != hash2