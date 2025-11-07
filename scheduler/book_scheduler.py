import asyncio
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from utils.config import settings
from utils.email_sender import EmailSender
from utils.logger import get_logger
from utils.models import Book, ChangeLog
from utils.database import db, Database
from crawler.book_crawler import BookCrawler

logger = get_logger(__name__)


class ChangeDetector:

    def __init__(self):
        self.changes: List[ChangeLog] = []

    def compare_books(self, old_book: Dict[str, Any], new_book: Book) -> Optional[ChangeLog]:
        changed_fields = []
        old_values = {}
        new_values = {}

        fields_to_compare = {
            'name': ('name', lambda x: x),
            'description': ('description', lambda x: x),
            'category': ('category', lambda x: x),
            'price.including_tax': (
                'price',
                lambda x: x.get('including_tax') if isinstance(x, dict)
                else x.including_tax if hasattr(x, 'including_tax') else None
            ),
            'price.excluding_tax': (
                'price',
                lambda x: x.get('excluding_tax') if isinstance(x, dict)
                else x.excluding_tax if hasattr(x, 'excluding_tax') else None
            ),
            'availability': ('availability', lambda x: x),
            'availability_count': ('availability_count', lambda x: x),
            'num_reviews': ('num_reviews', lambda x: x),
            'rating': ('rating', lambda x: x),
            'rating_numeric': ('rating_numeric', lambda x: x),
        }

        for field_name, (field_key, extractor) in fields_to_compare.items():

            old_value = extractor(old_book.get(field_key))

            if '.' in field_name:
                parts = field_name.split('.')
                new_obj = getattr(new_book, parts[0], None)
                if new_obj:
                    if isinstance(new_obj, dict):
                        new_value = new_obj.get(parts[1])
                    else:
                        new_value = getattr(new_obj, parts[1], None)
                else:
                    new_value = None
            else:
                new_value = getattr(new_book, field_name, None)


            if old_value != new_value:
                changed_fields.append(field_name)
                old_values[field_name] = old_value
                new_values[field_name] = new_value

        if changed_fields:
            change_log = ChangeLog(
                book_id=new_book.book_id,
                book_name=new_book.name,
                change_type="updated",
                changed_fields=changed_fields,
                old_values=old_values,
                new_values=new_values,
                detected_at=datetime.utcnow()
            )
            return change_log

        return None

    async def detect_changes(self, new_books: List[Book]) -> List[ChangeLog]:

        logger.info("Starting change detection...")
        changes = []

        existing_books = await db.get_all_books()
        existing_book_map = {book['book_id']: book for book in existing_books}
        existing_book_ids = set(existing_book_map.keys())

        new_book_ids = set()

        for new_book in new_books:
            new_book_ids.add(new_book.book_id)

            if new_book.book_id in existing_book_ids:
                old_book = existing_book_map[new_book.book_id]

                old_hash = old_book.get('metadata', {}).get('content_hash')
                new_hash = new_book.metadata.content_hash

                if old_hash != new_hash:
                    logger.info(f"Change detected in: {new_book.name}")
                    change = self.compare_books(old_book, new_book)
                    if change:
                        changes.append(change)

                        await db.update_book(
                            new_book.book_id,
                            new_book.model_dump(by_alias=True, exclude_none=False)
                        )
            else:
                logger.info(f"New book found: {new_book.name}")
                change_log = ChangeLog(
                    book_id=new_book.book_id,
                    book_name=new_book.name,
                    change_type="new",
                    changed_fields=[],
                    old_values=None,
                    new_values=None,
                    detected_at=datetime.utcnow()
                )
                changes.append(change_log)


                await db.insert_book(new_book)

        deleted_book_ids = existing_book_ids - new_book_ids
        for book_id in deleted_book_ids:
            old_book = existing_book_map[book_id]
            logger.warning(f"Book deleted/unavailable: {old_book.get('name', 'Unknown')}")
            change_log = ChangeLog(
                book_id=book_id,
                book_name=old_book.get('name', 'Unknown'),
                change_type="deleted",
                changed_fields=[],
                old_values=None,
                new_values=None,
                detected_at=datetime.utcnow()
            )
            changes.append(change_log)

        for change in changes:
            await db.log_change(change)

        logger.info(f"Change detection complete. Found {len(changes)} changes:")
        logger.info(f"  New books: {sum(1 for c in changes if c.change_type == 'new')}")
        logger.info(f"  Updated books: {sum(1 for c in changes if c.change_type == 'updated')}")
        logger.info(f"  Deleted books: {sum(1 for c in changes if c.change_type == 'deleted')}")

        return changes

    async def generate_change_report(self, changes: List[ChangeLog], format: str = "json"):

        report_dir = Path("data/reports")
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if format == "json":
            report_file = report_dir / f"change_report_{timestamp}.json"

            report_data = []
            for change in changes:
                change_dict = change.model_dump(mode='json')
                if 'detected_at' in change_dict:
                    change_dict['detected_at'] = change_dict['detected_at'].isoformat() if hasattr(
                        change_dict['detected_at'], 'isoformat') else str(change_dict['detected_at'])
                report_data.append(change_dict)

            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)

            logger.info(f"JSON change report saved: {report_file}")

        elif format == "csv":
            report_file = report_dir / f"change_report_{timestamp}.csv"

            with open(report_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Book ID', 'Book Name', 'Change Type', 'Changed Fields',
                    'Old Values', 'New Values', 'Detected At'
                ])

                for change in changes:
                    writer.writerow([
                        change.book_id,
                        change.book_name,
                        change.change_type,
                        ', '.join(change.changed_fields) if change.changed_fields else '',
                        json.dumps(change.old_values) if change.old_values else '',
                        json.dumps(change.new_values) if change.new_values else '',
                        change.detected_at.isoformat()
                    ])

            logger.info(f"CSV change report saved: {report_file}")

        return str(report_file)


class BookScheduler:

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.change_detector = ChangeDetector()

    async def scheduled_crawl_and_detect(self):

        try:
            logger.info("=" * 80)
            logger.info("Starting scheduled crawl and change detection")
            logger.info("=" * 80)

            await db.connect()

            logger.info("Step 1: Crawling website...")
            async with BookCrawler() as crawler:
                new_books = await crawler.crawl_all_books(resume=False)

                logger.info(f"Step 2: Detecting changes in {len(new_books)} books...")
                changes = await self.change_detector.detect_changes(new_books)

                if changes:
                    logger.info("Step 3: Generating reports...")
                    await self.change_detector.generate_change_report(changes, format="json")
                    await self.change_detector.generate_change_report(changes, format="csv")

                    await self.send_alerts(changes)
                    await self.generate_reports(changes)
                else:
                    logger.info("No changes detected")

                logger.info(f"Scheduled task completed. Total changes: {len(changes)}")

        except Exception as e:
            logger.error(f"Error in scheduled task: {e}")
        finally:
            await db.disconnect()

    async def send_alerts(self, changes: List[ChangeLog]):
        if not settings.alert_email_enabled:
            logger.info("Email alerts are disabled in configuration")
            return

        try:


            new_books = sum(1 for c in changes if c.change_type == "new")
            updated_books = sum(1 for c in changes if c.change_type == "updated")
            deleted_books = sum(1 for c in changes if c.change_type == "deleted")

            logger.info("=" * 50)
            logger.info("📧 SENDING EMAIL ALERT")
            logger.info(f"  New books: {new_books}")
            logger.info(f"  Updated books: {updated_books}")
            logger.info(f"  Deleted books: {deleted_books}")
            logger.info("=" * 50)

            email_sender = EmailSender()
            success = email_sender.send_change_alert(changes)

            if success:
                logger.success("✓ Email alert sent successfully")
            else:
                logger.error("✗ Failed to send email alert")

        except Exception as e:
            logger.error(f"Error sending alerts: {e}")

    async def generate_reports(self, changes: List[ChangeLog]):
        if not changes:
            logger.info("No changes to report")
            return

        try:
            reports_dir = Path("data/reports")
            reports_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")

            new_books = sum(1 for c in changes if c.change_type == "new")
            updated_books = sum(1 for c in changes if c.change_type == "updated")
            deleted_books = sum(1 for c in changes if c.change_type == "deleted")

            logger.info("=" * 50)
            logger.info("📊 GENERATING REPORTS")
            logger.info(f"  Total changes: {len(changes)}")
            logger.info(f"  New books: {new_books}")
            logger.info(f"  Updated books: {updated_books}")
            logger.info(f"  Deleted books: {deleted_books}")
            logger.info("=" * 50)


            json_filename = reports_dir / f"changes_{timestamp}.json"

            report_data = {
                "report_generated_at": datetime.utcnow().isoformat(),
                "total_changes": len(changes),
                "summary": {
                    "new_books": new_books,
                    "updated_books": updated_books,
                    "deleted_books": deleted_books
                },
                "changes": []
            }

            for change in changes:
                change_dict = {
                    "book_id": change.book_id,
                    "book_name": change.book_name,
                    "change_type": change.change_type,
                    "changed_fields": change.changed_fields or [],
                    "old_values": change.old_values or {},
                    "new_values": change.new_values or {},
                    "detected_at": change.detected_at.isoformat()
                }
                report_data["changes"].append(change_dict)

            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            logger.info(f"✓ JSON report saved: {json_filename}")


            csv_filename = reports_dir / f"changes_{timestamp}.csv"

            csv_data = []
            for change in changes:
                row = {
                    "book_id": change.book_id,
                    "book_name": change.book_name,
                    "change_type": change.change_type,
                    "changed_fields": ",".join(change.changed_fields or []),
                    "old_values": json.dumps(change.old_values or {}),
                    "new_values": json.dumps(change.new_values or {}),
                    "detected_at": change.detected_at.isoformat()
                }
                csv_data.append(row)

            if csv_data:
                fieldnames = [
                    "book_id",
                    "book_name",
                    "change_type",
                    "changed_fields",
                    "old_values",
                    "new_values",
                    "detected_at"
                ]

                with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(csv_data)

                logger.info(f"✓ CSV report saved: {csv_filename}")

            logger.info("=" * 50)
            logger.info("✓ Reports generated successfully")
            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"Error generating reports: {e}")

    def start(self):
        if not settings.scheduler_enabled:
            logger.info("Scheduler is disabled in configuration")
            return

        next_run = datetime.now() + timedelta(hours=settings.scheduler_interval_hours)

        self.scheduler.add_job(
            self.scheduled_crawl_and_detect,
            trigger=IntervalTrigger(hours=settings.scheduler_interval_hours),
            id='book_crawler_job',
            name='Book Crawler and Change Detection',
            replace_existing=True,
            next_run_time=next_run
        )

        self.scheduler.start()


        logger.success("✓ Scheduler started successfully!")
        logger.info(f"📅 Crawl interval: Every {settings.scheduler_interval_hours} hours")
        logger.info(f"⏰ Next scheduled run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"🕐 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        logger.info("Press Ctrl+C to stop the scheduler")
        logger.info("=" * 60)

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")


async def run_once():
    scheduler = BookScheduler()
    await scheduler.scheduled_crawl_and_detect()


def run_continuous():
    scheduler = BookScheduler()
    scheduler.start()


if __name__ == "__main__":
    asyncio.run(run_once())