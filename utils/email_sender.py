import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional

from utils.config import settings
from utils.logger import get_logger
from utils.models import ChangeLog

logger = get_logger(__name__)


class EmailSender:

    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.username = settings.smtp_username
        self.password = settings.smtp_password
        self.sender = settings.smtp_username
        self.sender_name = settings.alert_sender_name

    def send_change_alert(
            self,
            changes: List[ChangeLog],
            recipient: Optional[str] = None
    ) -> bool:
        if not settings.alert_email_enabled:
            logger.info("Email alerts disabled in config")
            return False

        recipient = recipient or settings.alert_recipient

        if not recipient:
            logger.warning("No email recipient configured")
            return False

        try:
            new_books = sum(1 for c in changes if c.change_type == "new")
            updated_books = sum(1 for c in changes if c.change_type == "updated")
            deleted_books = sum(1 for c in changes if c.change_type == "deleted")

            subject = f"📚 Book Crawler Alert: {len(changes)} Changes Detected"
            body = self._create_email_body(changes, new_books, updated_books, deleted_books)

            self._send_email(recipient, subject, body)

            logger.info(f"Email alert sent to {recipient}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False

    def _create_email_body(
            self,
            changes: List[ChangeLog],
            new_books: int,
            updated_books: int,
            deleted_books: int
    ) -> str:

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .summary {{ background-color: #f9f9f9; padding: 15px; margin: 20px 0; border-left: 4px solid #4CAF50; }}
                .changes {{ margin: 20px 0; }}
                .change-item {{ 
                    background-color: #fff; 
                    border: 1px solid #ddd; 
                    padding: 15px; 
                    margin: 10px 0; 
                    border-radius: 4px;
                }}
                .new {{ border-left: 4px solid #4CAF50; }}
                .updated {{ border-left: 4px solid #2196F3; }}
                .deleted {{ border-left: 4px solid #f44336; }}
                .badge {{ 
                    display: inline-block; 
                    padding: 4px 8px; 
                    border-radius: 3px; 
                    font-size: 12px; 
                    font-weight: bold;
                    color: white;
                }}
                .badge-new {{ background-color: #4CAF50; }}
                .badge-updated {{ background-color: #2196F3; }}
                .badge-deleted {{ background-color: #f44336; }}
                .footer {{ 
                    margin-top: 30px; 
                    padding-top: 20px; 
                    border-top: 1px solid #ddd; 
                    color: #666; 
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📚 Book Crawler Alert</h1>
                <p>Change Detection Report</p>
            </div>

            <div class="summary">
                <h2>Summary</h2>
                <p><strong>Total Changes:</strong> {len(changes)}</p>
                <ul>
                    <li><span class="badge badge-new">NEW</span> New Books: {new_books}</li>
                    <li><span class="badge badge-updated">UPDATED</span> Updated Books: {updated_books}</li>
                    <li><span class="badge badge-deleted">DELETED</span> Deleted Books: {deleted_books}</li>
                </ul>
            </div>

            <div class="changes">
                <h2>Changes Details</h2>
        """


        for change in changes[:10]:
            badge_class = f"badge-{change.change_type}"
            item_class = change.change_type

            html += f"""
                <div class="change-item {item_class}">
                    <span class="badge {badge_class}">{change.change_type.upper()}</span>
                    <h3>{change.book_name}</h3>
                    <p><strong>Book ID:</strong> {change.book_id}</p>
            """

            if change.change_type == "updated" and change.changed_fields:
                html += f"<p><strong>Changed Fields:</strong> {', '.join(change.changed_fields)}</p>"

                if change.old_values and change.new_values:
                    html += "<ul>"
                    for field in change.changed_fields[:3]:  # Show first 3 changes
                        old = change.old_values.get(field, "N/A")
                        new = change.new_values.get(field, "N/A")
                        html += f"<li><strong>{field}:</strong> {old} → {new}</li>"
                    html += "</ul>"

            html += f"<p><small>Detected at: {change.detected_at.strftime('%Y-%m-%d %H:%M:%S')}</small></p>"
            html += "</div>"

        if len(changes) > 10:
            html += f"<p><em>... and {len(changes) - 10} more changes</em></p>"

        html += """
            </div>

            <div class="footer">
                <p>This is an automated alert from Book Crawler.</p>
                <p>To view all changes, check the reports in data/reports/ or query the API.</p>
            </div>
        </body>
        </html>
        """

        return html

    def _send_email(self, recipient: str, subject: str, body: str):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.sender_name} <{self.sender}>"
        msg['To'] = recipient

        html_part = MIMEText(body, 'html')
        msg.attach(html_part)

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)

        logger.info(f"Email sent: {subject}")

    def send_test_email(self, recipient: Optional[str] = "adekunleabraham09@gmail.com"):
        recipient = recipient or settings.alert_recipient

        subject = "🧪 Book Crawler - Test Email"
        body = """
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>✅ Email Configuration Test</h2>
            <p>If you're reading this, your email configuration is working correctly!</p>
            <p><strong>Configuration:</strong></p>
            <ul>
                <li>SMTP Host: {}</li>
                <li>SMTP Port: {}</li>
                <li>From: {}</li>
            </ul>
            <p>You will receive alerts when book changes are detected.</p>
        </body>
        </html>
        """.format(self.smtp_host, self.smtp_port, self.sender)

        try:
            self._send_email(recipient, subject, body)
            logger.info("Test email sent successfully!")
            return True
        except Exception as e:
            logger.error(f"Failed to send test email: {e}")
            return False