import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class Notifier:
    def __init__(self, config_loader):
        self.config_loader = config_loader
        self.notification_settings = self.config_loader.get_setting('notification_settings')
        logger.info("Notifier initialized.")

    def send_alert(self, change):
        """Sends a notification for a detected change."""
        logger.info(f"Attempting to send alert for change ID: {change.id}")
        if not self.notification_settings:
            logger.warning("Notification settings not found in config. Skipping alerts.")
            return

        if self.notification_settings.get('email', {}).get('enabled'):
            self._send_email_alert(change)
        if self.notification_settings.get('slack', {}).get('enabled'):
            self._send_slack_alert(change)
        if self.notification_settings.get('teams', {}).get('enabled'):
            self._send_teams_alert(change)

    def _send_email_alert(self, change):
        email_settings = self.notification_settings.get('email', {})
        if not email_settings.get('enabled'):
            return

        try:
            msg = MIMEMultipart("alternative")
            msg['Subject'] = f"Payroll Monitor Alert: Change Detected for {change.form.name}"
            msg['From'] = email_settings.get('from_address')
            msg['To'] = ", ".join(email_settings.get('to_addresses', []))

            text = f"""
            A change has been detected for:
            Form: {change.form.name} - {change.form.title}
            Agency: {change.form.agency.name}
            Timestamp: {change.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC
            Severity: {change.severity}
            Details: {change.change_details}
            Form URL: {change.form.url}
            """
            html = f"""
            <html>
                <body>
                    <p>A change has been detected for:</p>
                    <ul>
                        <li><strong>Form:</strong> {change.form.name} - {change.form.title}</li>
                        <li><strong>Agency:</strong> {change.form.agency.name}</li>
                        <li><strong>Timestamp:</strong> {change.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC</li>
                        <li><strong>Severity:</strong> <span style="color:{self._get_severity_color(change.severity)};font-weight:bold;">{change.severity.upper()}</span></li>
                        <li><strong>Details:</strong> {change.change_details}</li>
                        <li><strong>Form URL:</strong> <a href="{change.form.url}">{change.form.url}</a></li>
                    </ul>
                    <p>Please review the dashboard for more details.</p>
                </body>
            </html>
            """
            msg.attach(MIMEText(text, 'plain'))
            msg.attach(MIMEText(html, 'html'))

            with smtplib.SMTP(email_settings.get('smtp_server'), email_settings.get('smtp_port')) as server:
                server.starttls()
                server.login(email_settings.get('username'), email_settings.get('password'))
                server.sendmail(msg['From'], email_settings.get('to_addresses'), msg.as_string())
            logger.info(f"Email alert sent for change ID: {change.id}")
        except Exception as e:
            logger.error(f"Failed to send email alert for change ID {change.id}: {e}")

    def _send_slack_alert(self, change):
        slack_settings = self.notification_settings.get('slack', {})
        if not slack_settings.get('enabled'):
            return
        webhook_url = slack_settings.get('webhook_url')
        if not webhook_url:
            logger.warning("Slack webhook URL not configured. Skipping Slack alert.")
            return

        try:
            payload = {
                "text": f"🚨 *Payroll Monitor Alert: Change Detected for {change.form.name}* 🚨\n"
                        f"• *Agency:* {change.form.agency.name}\n"
                        f"• *Form:* {change.form.title} ({change.form.name})\n"
                        f"• *Severity:* {change.severity.upper()}\n"
                        f"• *Details:* {change.change_details}\n"
                        f"• *Link:* <{change.form.url}|View Form>\n"
                        f"• *Dashboard:* <{os.getenv('APP_BASE_URL', 'http://localhost:8000')}/form/{change.form.id}|View Details on Dashboard>"
            }
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            logger.info(f"Slack alert sent for change ID: {change.id}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Slack alert for change ID {change.id}: {e}")

    def _send_teams_alert(self, change):
        teams_settings = self.notification_settings.get('teams', {})
        if not teams_settings.get('enabled'):
            return
        webhook_url = teams_settings.get('webhook_url')
        if not webhook_url:
            logger.warning("Teams webhook URL not configured. Skipping Teams alert.")
            return

        try:
            payload = {
                "type": "MessageCard",
                "context": "http://schema.org/extensions",
                "summary": f"Payroll Monitor Alert: Change Detected for {change.form.name}",
                "sections": [
                    {
                        "activityTitle": f"🚨 Change Detected: {change.form.name} - {change.form.title}",
                        "activitySubtitle": f"Agency: {change.form.agency.name}",
                        "facts": [
                            {"name": "Severity", "value": change.severity.upper()},
                            {"name": "Timestamp", "value": change.timestamp.strftime('%Y-%m-%d %H:%M:%S') + " UTC"},
                            {"name": "Details", "value": change.change_details}
                        ],
                        "markdown": True
                    }
                ],
                "potentialAction": [
                    {
                        "@type": "OpenUri",
                        "name": "View Form",
                        "targets": [{"os": "default", "uri": change.form.url}]
                    },
                    {
                        "@type": "OpenUri",
                        "name": "View on Dashboard",
                        "targets": [{"os": "default", "uri": f"{os.getenv('APP_BASE_URL', 'http://localhost:8000')}/form/{change.form.id}"}]
                    }
                ]
            }
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            logger.info(f"Teams alert sent for change ID: {change.id}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Teams alert for change ID {change.id}: {e}")

    def test_notifications(self):
        logger.info("Sending test notifications...")
        # Create a dummy change object for testing
        class DummyAgency:
            name = "Test Agency"
        class DummyForm:
            name = "TEST-FORM-001"
            title = "Test Certified Payroll Report"
            url = "http://example.com/test-form"
            agency = DummyAgency()
        class DummyChange:
            id = 0
            form = DummyForm()
            timestamp = datetime.utcnow()
            change_details = "This is a test notification from the Payroll Monitoring System."
            severity = "low" # Can be 'low', 'medium', 'high', 'critical'
        
        dummy_change = DummyChange()
        self.send_alert(dummy_change)
        logger.info("Test notifications attempt complete.")

    def _get_severity_color(self, severity):
        colors = {
            'critical': '#FF0000', # Red
            'high': '#FFA500',     # Orange
            'medium': '#FFFF00',   # Yellow
            'low': '#008000'       # Green
        }
        return colors.get(severity.lower(), '#808080') # Default to gray