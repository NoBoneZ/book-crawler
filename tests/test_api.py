
import pytest
from fastapi.testclient import TestClient

from api.main import app
from utils.config import settings


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": settings.api_key}


@pytest.mark.api
class TestRootEndpoints:

    def test_root_endpoint(self, client):
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "endpoints" in data

    def test_health_check(self, client):
        response = client.get("/health")

        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "timestamp" in data


@pytest.mark.api
class TestAuthentication:

    def test_books_without_auth(self, client):
        response = client.get("/books")

        assert response.status_code == 401
        data = response.json()
        assert "API key is missing" in data['detail']

    def test_books_with_invalid_auth(self, client):
        response = client.get(
            "/books",
            headers={"X-API-Key": "invalid_key"}
        )

        assert response.status_code == 403
        data = response.json()
        assert "Invalid API key" in data['detail']

    def test_books_with_valid_auth(self, client, auth_headers):
        response = client.get("/books", headers=auth_headers)

        assert response.status_code not in [401, 403]


@pytest.mark.api
class TestBooksEndpoint:

    def test_get_books_basic(self, client, auth_headers):
        response = client.get("/books", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "books" in data
        assert isinstance(data['books'], list)

    def test_get_books_with_category_filter(self, client, auth_headers):
        response = client.get(
            "/books",
            headers=auth_headers,
            params={"category": "Fiction"}
        )

        assert response.status_code == 200
        data = response.json()

        for book in data['books']:
            assert "Fiction" in book['category']

    def test_get_books_with_price_filter(self, client, auth_headers):
        response = client.get(
            "/books",
            headers=auth_headers,
            params={"min_price": 20, "max_price": 50}
        )

        assert response.status_code == 200
        data = response.json()

        for book in data['books']:
            price = book['price']['including_tax']
            assert 20 <= price <= 50

    def test_get_books_pagination(self, client, auth_headers):
        response = client.get(
            "/books",
            headers=auth_headers,
            params={"page": 1, "page_size": 10}
        )

        assert response.status_code == 200
        data = response.json()

        assert data['page'] == 1
        assert data['page_size'] == 10
        assert len(data['books']) <= 10

    def test_get_books_invalid_sort(self, client, auth_headers):
        response = client.get(
            "/books",
            headers=auth_headers,
            params={"sort_by": "invalid_field"}
        )

        assert response.status_code == 400
        assert "Invalid sort_by field" in response.json()['detail']

    def test_get_books_invalid_page(self, client, auth_headers):
        response = client.get(
            "/books",
            headers=auth_headers,
            params={"page": 0}
        )

        assert response.status_code == 400
        assert "Page must be >= 1" in response.json()['detail']


@pytest.mark.api
class TestBookDetailEndpoint:

    def test_get_book_by_id(self, client, auth_headers):
        response = client.get("/books", headers=auth_headers, params={"page_size": 1})
        assert response.status_code == 200

        books = response.json()['books']
        if books:
            book_id = books[0]['book_id']

            response = client.get(f"/books/{book_id}", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert data['book_id'] == book_id

    def test_get_nonexistent_book(self, client, auth_headers):
        response = client.get(
            "/books/nonexistent_id_12345",
            headers=auth_headers
        )

        assert response.status_code == 404
        assert "not found" in response.json()['detail'].lower()


@pytest.mark.api
class TestChangesEndpoint:

    def test_get_changes(self, client, auth_headers):
        response = client.get("/changes", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "changes" in data
        assert isinstance(data['changes'], list)

    def test_get_changes_pagination(self, client, auth_headers):
        response = client.get(
            "/changes",
            headers=auth_headers,
            params={"page": 1, "page_size": 10}
        )

        assert response.status_code == 200
        data = response.json()

        assert data['page'] == 1
        assert data['page_size'] == 10


@pytest.mark.api
class TestErrorHandling:

    def test_404_on_invalid_endpoint(self, client):
        response = client.get("/invalid_endpoint")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data['detail'].lower()