import smtplib
import ssl
import requests
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self, config_loader):
        self.config_loader = config_loader
        self.notification_settings = self.config_loader.get_setting('notification_settings')
        logger.info("Notifier initialized.")

    def _send_email(self, subject, body, to_addresses):
        """Sends an email notification."""
        email_config = self.notification_settings.get('email', {})
        if not email_config.get('enabled'):
            logger.info("Email notifications are disabled.")
            return False

        smtp_server = email_config.get('smtp_server')
        smtp_port = email_config.get('smtp_port')
        username = os.getenv('SMTP_USERNAME') or email_config.get('username')
        password = os.getenv('SMTP_PASSWORD') or email_config.get('password')
        from_address = os.getenv('FROM_EMAIL') or email_config.get('from_address')

        if not all([smtp_server, smtp_port, username, password, from_address, to_addresses]):
            logger.error("Missing email configuration or credentials. Cannot send email.")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_address
        msg["To"] = ", ".join(to_addresses)

        # Attach HTML body
        msg.attach(MIMEText(body, "html"))

        context = ssl.create_default_context()
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls(context=context)
                server.login(username, password)
                server.sendmail(from_address, to_addresses, msg.as_string())
            logger.info(f"Email sent successfully to {', '.join(to_addresses)}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _send_slack_webhook(self, message):
        """Sends a Slack notification via webhook."""
        slack_config = self.notification_settings.get('slack', {})
        if not slack_config.get('enabled'):
            logger.info("Slack notifications are disabled.")
            return False

        webhook_url = os.getenv('SLACK_WEBHOOK_URL') or slack_config.get('webhook_url')
        if not webhook_url:
            logger.error("Slack webhook URL is not configured. Cannot send Slack notification.")
            return False

        payload = {
            "text": message,
            "channel": slack_config.get('channel')
        }
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Slack notification sent successfully.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    def _send_teams_webhook(self, message):
        """Sends a Microsoft Teams notification via webhook."""
        teams_config = self.notification_settings.get('teams', {})
        if not teams_config.get('enabled'):
            logger.info("Teams notifications are disabled.")
            return False

        webhook_url = os.getenv('TEAMS_WEBHOOK_URL') or teams_config.get('webhook_url')
        if not webhook_url:
            logger.error("Teams webhook URL is not configured. Cannot send Teams notification.")
            return False

        # Teams expects a specific JSON structure for messages
        payload = {
            "text": message
        }
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Teams notification sent successfully.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Teams notification: {e}")
            return False

    def send_alert(self, change):
        """Sends an alert for a detected change."""
        subject = f"🚨 Payroll Form Change Detected: {change.form.name} ({change.form.agency.abbreviation})"
        
        # Basic HTML body for email
        email_body = f"""
        <html>
        <body>
            <p>A change has been detected for the following payroll form:</p>
            <ul>
                <li><strong>Agency:</strong> {change.form.agency.name} ({change.form.agency.abbreviation})</li>
                <li><strong>Form Name:</strong> {change.form.name}</li>
                <li><strong>Form Title:</strong> {change.form.title}</li>
                <li><strong>Change Timestamp:</strong> {change.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</li>
                <li><strong>Severity:</strong> <span style="color: {'red' if change.severity == 'critical' else 'orange' if change.severity == 'high' else 'yellow' if change.severity == 'medium' else 'gray'}; font-weight: bold;">{change.severity.upper()}</span></li>
                <li><strong>Details:</strong> {change.change_details}</li>
                <li><strong>Form URL:</strong> <a href="{change.form.url}">{change.form.url}</a></li>
                {f'<li><strong>Direct Form URL:</strong> <a href="{change.form.form_url}">{change.form.form_url}</a></li>' if change.form.form_url else ''}
                {f'<li><strong>Instructions URL:</strong> <a href="{change.form.instructions_url}">{change.form.instructions_url}</a></li>' if change.form.instructions_url else ''}
            </ul>
            <p>Please review the change and assess its impact.</p>
            <p>This is an automated notification from the Payroll Monitoring System.</p>
        </body>
        </html>
        """

        # Plain text message for Slack/Teams
        plain_message = (
            f"🚨 Payroll Form Change Detected!\n"
            f"Agency: {change.form.agency.name} ({change.form.agency.abbreviation})\n"
            f"Form: {change.form.name} - {change.form.title}\n"
            f"Timestamp: {change.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"Severity: {change.severity.upper()}\n"
            f"Details: {change.change_details}\n"
            f"URL: {change.form.url}"
        )

        # Send to configured channels
        to_addresses = self.notification_settings.get('email', {}).get('to_addresses', [])
        if to_addresses:
            self._send_email(subject, email_body, to_addresses)
        
        if self.notification_settings.get('slack', {}).get('enabled'):
            self._send_slack_webhook(plain_message)
        
        if self.notification_settings.get('teams', {}).get('enabled'):
            self._send_teams_webhook(plain_message)

    def test_notifications(self):
        """Sends a test notification to all configured channels."""
        logger.info("Attempting to send test notifications...")
        test_subject = "Payroll Monitor Test Notification"
        test_email_body = """
        <html>
        <body>
            <p>This is a test email from the Payroll Monitoring System.</p>
            <p>If you received this, email notifications are configured correctly.</p>
        </body>
        </html>
        """
        test_plain_message = "This is a test notification from the Payroll Monitoring System. If you received this, notifications are configured correctly."

        email_to_addresses = self.notification_settings.get('email', {}).get('to_addresses', [])
        if email_to_addresses:
            self._send_email(test_subject, test_email_body, email_to_addresses)
        else:
            logger.warning("No email recipients configured for test notification.")

        if self.notification_settings.get('slack', {}).get('enabled'):
            self._send_slack_webhook(test_plain_message)
        else:
            logger.warning("Slack notifications are disabled for test notification.")
        
        if self.notification_settings.get('teams', {}).get('enabled'):
            self._send_teams_webhook(test_plain_message)
        else:
            logger.warning("Teams notifications are disabled for test notification.")
        
        logger.info("Test notification attempts completed. Check logs for success/failure.")