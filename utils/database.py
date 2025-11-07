import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING
from utils.config import settings
from utils.logger import get_logger
from utils.models import Book, ChangeLog

logger = get_logger(__name__)


class Database:

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.books_collection: Optional[AsyncIOMotorCollection] = None
        self.changes_collection: Optional[AsyncIOMotorCollection] = None
        self.crawl_state_collection: Optional[AsyncIOMotorCollection] = None

    async def connect(self):
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_url)
            self.db = self.client[settings.mongodb_db_name]

            self.books_collection = self.db["books"]
            self.changes_collection = self.db["changes"]
            self.crawl_state_collection = self.db["crawl_state"]

            await self._create_indexes()

            logger.info(f"Connected to MongoDB: {settings.mongodb_db_name}")

        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self):
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    async def _create_indexes(self):
        try:
            await self.books_collection.create_index(
                [("book_id", ASCENDING)],
                unique=True
            )
            await self.books_collection.create_index([("name", ASCENDING)])
            await self.books_collection.create_index([("category", ASCENDING)])
            await self.books_collection.create_index([("price.including_tax", ASCENDING)])
            await self.books_collection.create_index([("rating_numeric", DESCENDING)])
            await self.books_collection.create_index([("num_reviews", DESCENDING)])
            await self.books_collection.create_index([("metadata.crawl_timestamp", DESCENDING)])
            await self.books_collection.create_index([("metadata.content_hash", ASCENDING)])

            await self.changes_collection.create_index([("book_id", ASCENDING)])
            await self.changes_collection.create_index([("detected_at", DESCENDING)])
            await self.changes_collection.create_index([("change_type", ASCENDING)])

            await self.crawl_state_collection.create_index([("last_crawl_time", DESCENDING)])

            logger.info("Database indexes created successfully")

        except Exception as e:
            logger.warning(f"Error creating indexes: {e}")



    async def insert_book(self, book: Book) -> str:
        try:
            book_dict = book.model_dump(by_alias=True, exclude_none=False)
            result = await self.books_collection.insert_one(book_dict)
            logger.info(f"Inserted book: {book.name} (ID: {book.book_id})")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error inserting book {book.name}: {e}")
            raise

    async def update_book(self, book_id: str, update_data: Dict[str, Any]) -> bool:
        try:
            result = await self.books_collection.update_one(
                {"book_id": book_id},
                {"$set": update_data}
            )
            if result.modified_count > 0:
                logger.info(f"Updated book: {book_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating book {book_id}: {e}")
            raise

    async def get_book_by_id(self, book_id: str) -> Optional[Dict[str, Any]]:
        try:
            book = await self.books_collection.find_one({"book_id": book_id})
            return book
        except Exception as e:
            logger.error(f"Error retrieving book {book_id}: {e}")
            return None

    async def get_book_by_url(self, url: str) -> Optional[Dict[str, Any]]:

        try:
            book = await self.books_collection.find_one({"metadata.source_url": url})
            return book
        except Exception as e:
            logger.error(f"Error retrieving book by URL {url}: {e}")
            return None

    async def query_books(
            self,
            category: Optional[str] = None,
            min_price: Optional[float] = None,
            max_price: Optional[float] = None,
            rating: Optional[int] = None,
            sort_by: str = "name",
            skip: int = 0,
            limit: int = 20
    ) -> tuple[List[Dict[str, Any]], int]:
        try:
            query_filter = {}

            if category:
                query_filter["category"] = {"$regex": category, "$options": "i"}

            if min_price is not None or max_price is not None:
                price_filter = {}
                if min_price is not None:
                    price_filter["$gte"] = min_price
                if max_price is not None:
                    price_filter["$lte"] = max_price
                query_filter["price.including_tax"] = price_filter

            if rating is not None:
                query_filter["rating_numeric"] = rating


            sort_mapping = {
                "rating": ("rating_numeric", DESCENDING),
                "price": ("price.including_tax", ASCENDING),
                "reviews": ("num_reviews", DESCENDING),
                "name": ("name", ASCENDING)
            }

            sort_field, sort_direction = sort_mapping.get(sort_by, ("name", ASCENDING))


            cursor = self.books_collection.find(query_filter).sort(
                sort_field, sort_direction
            ).skip(skip).limit(limit)

            books = await cursor.to_list(length=limit)


            total = await self.books_collection.count_documents(query_filter)

            return books, total

        except Exception as e:
            logger.error(f"Error querying books: {e}")
            return [], 0

    async def get_all_books(self) -> List[Dict[str, Any]]:
        try:
            cursor = self.books_collection.find({})
            books = await cursor.to_list(length=None)
            return books
        except Exception as e:
            logger.error(f"Error retrieving all books: {e}")
            return []



    async def log_change(self, change: ChangeLog):
        try:
            change_dict = change.model_dump(by_alias=True)
            await self.changes_collection.insert_one(change_dict)
            logger.info(f"Logged change for book: {change.book_name} ({change.change_type})")
        except Exception as e:
            logger.error(f"Error logging change: {e}")
            raise

    async def get_recent_changes(
            self,
            limit: int = 50,
            skip: int = 0
    ) -> tuple[List[Dict[str, Any]], int]:

        try:
            cursor = self.changes_collection.find({}).sort(
                "detected_at", DESCENDING
            ).skip(skip).limit(limit)

            changes = await cursor.to_list(length=limit)
            total = await self.changes_collection.count_documents({})

            return changes, total
        except Exception as e:
            logger.error(f"Error retrieving changes: {e}")
            return [], 0


    async def save_crawl_state(self, state: Dict[str, Any]):

        try:
            await self.crawl_state_collection.replace_one(
                {"_id": "latest"},
                {**state, "_id": "latest", "updated_at": datetime.utcnow()},
                upsert=True
            )
            logger.info("Crawl state saved")
        except Exception as e:
            logger.error(f"Error saving crawl state: {e}")

    async def get_crawl_state(self) -> Optional[Dict[str, Any]]:
        try:
            state = await self.crawl_state_collection.find_one({"_id": "latest"})
            return state
        except Exception as e:
            logger.error(f"Error retrieving crawl state: {e}")
            return None


    @staticmethod
    def compute_content_hash(book_data: Dict[str, Any]) -> str:
        relevant_fields = {
            "name": book_data.get("name"),
            "price": book_data.get("price"),
            "availability": book_data.get("availability"),
            "availability_count": book_data.get("availability_count"),
            "description": book_data.get("description"),
            "rating": book_data.get("rating")
        }

        content_str = str(sorted(relevant_fields.items()))
        return hashlib.sha256(content_str.encode()).hexdigest()


db = Database()