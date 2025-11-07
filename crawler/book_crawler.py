import asyncio
import re
from typing import List, Optional
from urllib.parse import urljoin
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from utils.config import settings
from utils.logger import get_logger
from utils.models import Book, BookPrice, CrawlMetadata
from utils.database import db, Database

logger = get_logger(__name__)


class BookCrawler:

    def __init__(self):
        self.base_url = settings.target_url
        self.concurrent_requests = settings.crawler_concurrent_requests
        self.retry_attempts = settings.crawler_retry_attempts
        self.retry_delay = settings.crawler_retry_delay
        self.timeout = settings.crawler_timeout

        self.client: Optional[httpx.AsyncClient] = None
        self.semaphore: Optional[asyncio.Semaphore] = None

        self.stats = {
            "total_books": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0
        }

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"User-Agent": settings.crawler_user_agent},
            follow_redirects=True
        )
        self.semaphore = asyncio.Semaphore(self.concurrent_requests)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def fetch_page(self, url: str, retry_count: int = 0) -> Optional[str]:
        if not self.client or not self.semaphore:
            raise RuntimeError("Crawler must be used as async context manager")


        async with self.semaphore:
            for attempt in range(self.retry_attempts):
                try:
                    logger.debug(f"Fetching: {url} (attempt {attempt + 1})")

                    response = await self.client.get(url)
                    response.raise_for_status()

                    return response.text

                except httpx.HTTPStatusError as e:

                    logger.warning(f"HTTP error {e.response.status_code} for {url}")

                    if e.response.status_code >= 500:

                        if attempt < self.retry_attempts - 1:
                            wait_time = self.retry_delay * (attempt + 1)
                            logger.info(f"Retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue

                    raise

                except httpx.RequestError as e:
                    logger.warning(f"Request error for {url}: {e}")

                    if attempt < self.retry_attempts - 1:
                        wait_time = self.retry_delay * (attempt + 1)
                        logger.info(f"Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    raise

                except Exception as e:
                    logger.error(f"Unexpected error fetching {url}: {e}")

                    if attempt < self.retry_attempts - 1:
                        wait_time = self.retry_delay * (attempt + 1)
                        logger.info(f"Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    raise

        return None

    async def get_all_book_urls(self) -> List[str]:

        book_urls = []
        page = 1

        while True:
            try:
                if page == 1:
                    url = f"{self.base_url}/index.html"
                else:
                    url = f"{self.base_url}/catalogue/page-{page}.html"

                logger.info(f"Fetching catalogue page {page}")
                html = await self.fetch_page(url)

                if not html:
                    logger.warning(f"Empty response for page {page}")
                    break

                soup = BeautifulSoup(html, 'lxml')


                book_elements = soup.select('article.product_pod h3 a')

                if not book_elements:
                    logger.info(f"No more books found on page {page}")
                    break

                for book_element in book_elements:
                    book_url = book_element.get('href')
                    if book_url:
                        if book_url.startswith('../../../'):
                            book_url = book_url.replace('../../../', '')
                            full_url = urljoin(f"{self.base_url}/", book_url)
                        elif book_url.startswith('../../'):
                            book_url = book_url.replace('../../', '')
                            full_url = urljoin(f"{self.base_url}/", book_url)
                        elif book_url.startswith('catalogue/'):

                            full_url = urljoin(f"{self.base_url}/", book_url)
                        else:
                            full_url = urljoin(f"{self.base_url}/catalogue/", book_url)

                        book_urls.append(full_url)

                logger.info(f"Found {len(book_elements)} books on page {page}")
                page += 1


                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                break

        logger.info(f"Total book URLs collected: {len(book_urls)}")
        return book_urls

    def parse_book_page(self, html: str, url: str) -> Optional[Book]:
        try:
            soup = BeautifulSoup(html, 'lxml')

            name_elem = soup.select_one('div.product_main h1')
            name = name_elem.text.strip() if name_elem else "Unknown"


            description_elem = soup.select_one('#product_description ~ p')
            description = description_elem.text.strip() if description_elem else None

            if not description:
                description_elem = soup.select_one('article.product_page > p')
                description = description_elem.text.strip() if description_elem else None


            category_elem = soup.select('ul.breadcrumb li')
            category = "Unknown"
            if len(category_elem) >= 3:
                category = category_elem[2].text.strip()


            price_table = soup.select('table.table tr')
            price_incl_tax = 0.0
            price_excl_tax = 0.0

            for row in price_table:
                th = row.select_one('th')
                td = row.select_one('td')
                if th and td:
                    if 'Price (incl. tax)' in th.text:
                        price_incl_tax = float(td.text.strip().replace('£', ''))
                    elif 'Price (excl. tax)' in th.text:
                        price_excl_tax = float(td.text.strip().replace('£', ''))

            price = BookPrice(
                including_tax=price_incl_tax,
                excluding_tax=price_excl_tax,
                currency="£"
            )

            availability_elem = soup.select_one('p.availability')
            availability = "Unknown"
            availability_count = None

            if availability_elem:
                availability_text = availability_elem.text.strip()
                availability = availability_text


                match = re.search(r'\((\d+) available\)', availability_text)
                if match:
                    availability_count = int(match.group(1))


            num_reviews = 0
            for row in price_table:
                th = row.select_one('th')
                td = row.select_one('td')
                if th and td and 'Number of reviews' in th.text:
                    num_reviews = int(td.text.strip())

            rating_elem = soup.select_one('p.star-rating')
            rating = None
            rating_numeric = None

            if rating_elem:
                classes = rating_elem.get('class', [])
                rating_map = {
                    'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5
                }
                for cls in classes:
                    if cls in rating_map:
                        rating = cls
                        rating_numeric = rating_map[cls]
                        break


            image_elem = soup.select_one('div.item.active img')
            image_url = None
            if image_elem:
                image_src = image_elem.get('src')
                if image_src:
                    image_url = urljoin(self.base_url, image_src.replace('../', ''))


            upc = None
            for row in price_table:
                th = row.select_one('th')
                td = row.select_one('td')
                if th and td and 'UPC' in th.text:
                    upc = td.text.strip()


            book_id = url.split('/')[-2]


            metadata = CrawlMetadata(
                crawl_timestamp=datetime.utcnow(),
                source_url=url,
                status="success",
                retry_count=0
            )

            book_data_for_hash = {
                "name": name,
                "price": price.model_dump(),
                "availability": availability,
                "availability_count": availability_count,
                "description": description,
                "rating": rating
            }
            metadata.content_hash = Database.compute_content_hash(book_data_for_hash)

            book = Book(
                book_id=book_id,
                upc=upc,
                name=name,
                description=description,
                category=category,
                price=price,
                availability=availability,
                availability_count=availability_count,
                num_reviews=num_reviews,
                rating=rating,
                rating_numeric=rating_numeric,
                image_url=image_url,
                metadata=metadata,
                raw_html=html
            )

            return book

        except Exception as e:
            logger.error(f"Error parsing book page {url}: {e}")
            return None

    async def crawl_book(self, url: str) -> Optional[Book]:
        try:
            html = await self.fetch_page(url)
            if not html:
                self.stats["failed"] += 1
                return None

            book = self.parse_book_page(html, url)
            if book:
                self.stats["successful"] += 1
                return book
            else:
                self.stats["failed"] += 1
                return None

        except Exception as e:
            logger.error(f"Error crawling book {url}: {e}")
            self.stats["failed"] += 1
            return None

    async def crawl_all_books(self, resume: bool = False) -> List[Book]:
        logger.info("Starting book crawl...")

        crawl_state = None
        if resume:
            crawl_state = await db.get_crawl_state()
            if crawl_state:
                logger.info(f"Resuming from book {crawl_state.get('last_processed_index', 0)}")


        book_urls = await self.get_all_book_urls()
        self.stats["total_books"] = len(book_urls)

        start_index = 0
        if crawl_state:
            start_index = crawl_state.get('last_processed_index', 0)
            book_urls = book_urls[start_index:]

        books = []

        batch_size = self.concurrent_requests
        for i in range(0, len(book_urls), batch_size):
            batch_urls = book_urls[i:i + batch_size]

            tasks = [self.crawl_book(url) for url in batch_urls]
            batch_books = await asyncio.gather(*tasks)

            valid_books = [book for book in batch_books if book is not None]
            books.extend(valid_books)

            await db.save_crawl_state({
                "last_processed_index": start_index + i + len(batch_urls),
                "total_books": self.stats["total_books"],
                "successful": self.stats["successful"],
                "failed": self.stats["failed"]
            })

            logger.info(f"Progress: {start_index + i + len(batch_urls)}/{self.stats['total_books']} books processed")

            await asyncio.sleep(1)

        logger.info(f"Crawl complete! Total: {self.stats['total_books']}, "
                    f"Successful: {self.stats['successful']}, Failed: {self.stats['failed']}")

        return books

    async def save_books_to_db(self, books: List[Book]):
        logger.info(f"Saving {len(books)} books to database...")

        for book in books:
            try:
                existing_book = await db.get_book_by_url(book.metadata.source_url)

                if existing_book:
                    await db.update_book(
                        book.book_id,
                        book.model_dump(by_alias=True, exclude_none=False)
                    )
                else:
                    await db.insert_book(book)

            except Exception as e:
                logger.error(f"Error saving book {book.name}: {e}")

        logger.info("Books saved successfully")


async def run_crawler(resume: bool = False):
    try:
        await db.connect()

        async with BookCrawler() as crawler:
            books = await crawler.crawl_all_books(resume=resume)
            await crawler.save_books_to_db(books)

        logger.info("Crawler completed successfully")

    except Exception as e:
        logger.error(f"Crawler failed: {e}")
        raise
    finally:
        await db.disconnect()