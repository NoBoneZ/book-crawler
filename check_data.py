"""Analyze crawled data"""
import asyncio
from utils.database import db
from utils.logger import get_logger

logger = get_logger(__name__)


async def analyze_data():
    """Analyze crawled book data"""
    await db.connect()

    # Get all books
    books = await db.get_all_books()

    logger.info(f"📊 Data Analysis")
    logger.info(f"=" * 50)
    logger.info(f"Total books: {len(books)}")

    # Category breakdown
    categories = {}
    for book in books:
        cat = book.get('category', 'Unknown')
        categories[cat] = categories.get(cat, 0) + 1

    logger.info(f"\n📚 Top 10 Categories:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
        logger.info(f"  {cat}: {count} books")

    # Price analysis
    prices = [book['price']['including_tax'] for book in books]
    avg_price = sum(prices) / len(prices)
    max_price = max(prices)
    min_price = min(prices)

    logger.info(f"\n💰 Price Analysis:")
    logger.info(f"  Average: £{avg_price:.2f}")
    logger.info(f"  Highest: £{max_price:.2f}")
    logger.info(f"  Lowest: £{min_price:.2f}")

    # Rating analysis
    ratings = {}
    for book in books:
        rating = book.get('rating_numeric', 0)
        ratings[rating] = ratings.get(rating, 0) + 1

    logger.info(f"\n⭐ Rating Distribution:")
    for rating in sorted(ratings.keys(), reverse=True):
        logger.info(f"  {rating} stars: {ratings[rating]} books")

    # Availability
    in_stock = sum(1 for book in books if 'In stock' in book.get('availability', ''))
    logger.info(f"\n📦 Availability:")
    logger.info(f"  In stock: {in_stock} books")
    logger.info(f"  Out of stock: {len(books) - in_stock} books")

    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(analyze_data())