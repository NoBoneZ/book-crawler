from datetime import datetime

import pytest
from pydantic import ValidationError

from utils.models import Book, BookPrice, CrawlMetadata, ChangeLog


@pytest.mark.unit
class TestBookPrice:

    def test_price_creation(self):
        price = BookPrice(
            including_tax=25.99,
            excluding_tax=24.99,
            currency="£"
        )
        assert price.including_tax == 25.99
        assert price.excluding_tax == 24.99
        assert price.currency == "£"

    def test_price_parsing_from_string(self):
        price = BookPrice(
            including_tax="£51.77",
            excluding_tax="£50.77",
            currency="£"
        )
        assert price.including_tax == 51.77
        assert price.excluding_tax == 50.77

    def test_negative_price_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            BookPrice(
                including_tax=-10.0,
                excluding_tax=-10.0
            )

        assert "greater than or equal to 0" in str(exc_info.value).lower()

    def test_price_with_comma(self):
        price = BookPrice(
            including_tax="1,234.56",
            excluding_tax="1,234.56"
        )
        assert price.including_tax == 1234.56


@pytest.mark.unit
class TestBook:

    def test_book_creation(self, sample_book):
        assert sample_book.book_id == "test_book_001"
        assert sample_book.name == "Test Book Title"
        assert sample_book.category == "Fiction"
        assert sample_book.price.including_tax == 25.99

    def test_book_missing_required_fields(self):
        with pytest.raises(ValidationError) as exc_info:
            Book(
                name="Test Book"

            )

        errors = exc_info.value.errors()
        required_fields = {error['loc'][0] for error in errors}
        assert 'category' in required_fields
        assert 'price' in required_fields

    def test_book_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            Book(
                name="",  # Empty!
                category="Fiction",
                price=BookPrice(including_tax=10, excluding_tax=10),
                availability="In stock",
                metadata=CrawlMetadata(source_url="https://example.com")
            )

    def test_book_serialization(self, sample_book):
        book_dict = sample_book.model_dump()

        assert isinstance(book_dict, dict)
        assert book_dict['name'] == "Test Book Title"
        assert book_dict['price']['including_tax'] == 25.99
        assert 'metadata' in book_dict


@pytest.mark.unit
class TestChangeLog:

    def test_change_log_creation(self, sample_change_log):
        assert sample_change_log.book_id == "test_book_001"
        assert sample_change_log.change_type == "updated"
        assert len(sample_change_log.changed_fields) == 2

    def test_change_log_types(self):
        for change_type in ["new", "updated", "deleted"]:
            change = ChangeLog(
                book_id="test",
                book_name="Test",
                change_type=change_type,
                changed_fields=[],
                detected_at=datetime.utcnow()
            )
            assert change.change_type == change_type