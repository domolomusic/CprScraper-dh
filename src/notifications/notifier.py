import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
import logging
from src.utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self):
        self.config = ConfigLoader().get_config()
        self.notification_settings = self.config.get('notification_settings', {})

    def send_email_notification(self, subject, body_html, to_addresses=None):
        email_settings = self.notification_settings.get('email', {})
        if not email_settings.get('enabled'):
            logger.info("Email notifications are disabled.")
            return

        smtp_server = email_settings.get('smtp_server')
        smtp_port = email_settings.get('smtp_port')
        username = email_settings.get('username')
        password = email_settings.get('password')
        from_address = email_settings.get('from_address')
        
        if not to_addresses:
            to_addresses = email_settings.get('to_addresses', [])

        if not all([smtp_server, smtp_port, username, password, from_address, to_addresses]):
            logger.error("Missing email configuration. Cannot send email.")
            return

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_address
        msg['To'] = ", ".join(to_addresses)

        part1 = MIMEText(body_html, 'html')
        msg.attach(part1)

        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.sendmail(from_address, to_addresses, msg.as_string())
            logger.info(f"Email notification sent to {', '.join(to_addresses)}")
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")

    def send_slack_notification(self, message):
        slack_settings = self.notification_settings.get('slack', {})
        if not slack_settings.get('enabled'):
            logger.info("Slack notifications are disabled.")
            return

        webhook_url = slack_settings.get('webhook_url')
        if not webhook_url:
            logger.error("Slack webhook URL is not configured. Cannot send Slack notification.")
            return

        payload = {
            "text": message
        }
        try:
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            logger.info("Slack notification sent.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack notification: {e}")

    def send_teams_notification(self, message):
        teams_settings = self.notification_settings.get('teams', {})
        if not teams_settings.get('enabled'):
            logger.info("Microsoft Teams notifications are disabled.")
            return

        webhook_url = teams_settings.get('webhook_url')
        if not webhook_url:
            logger.error("Microsoft Teams webhook URL is not configured. Cannot send Teams notification.")
            return

        payload = {
            "text": message
        }
        try:
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            logger.info("Microsoft Teams notification sent.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Microsoft Teams notification: {e}")

    def send_notification(self, subject, body_html, plain_text_message):
        self.send_email_notification(subject, body_html)
        self.send_slack_notification(plain_text_message)
        self.send_teams_notification(plain_text_message)