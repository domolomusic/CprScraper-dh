import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from src.database.connection import SessionLocal
from src.database.models import Agency, Form, Change, MonitoringRun
from src.monitors.web_scraper import WebScraper # Corrected import
from src.monitors.change_detector import ChangeDetector
from src.notifications.notifier import Notifier
from src.utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class MonitoringScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.config_loader = ConfigLoader()
        self.scraper = WebScraper()
        self.detector = ChangeDetector()
        self.notifier = Notifier()
        self._load_jobs()

    def _load_jobs(self):
        session = SessionLocal()
        try:
            forms = session.query(Form).all()
            for form in forms:
                job_id = f"monitor_form_{form.id}"
                if form.check_frequency == 'daily':
                    trigger = CronTrigger(hour=3, minute=0) # Run daily at 3 AM UTC
                elif form.check_frequency == 'weekly':
                    trigger = CronTrigger(day_of_week='mon', hour=3, minute=0) # Run weekly on Monday at 3 AM UTC
                elif form.check_frequency == 'monthly':
                    trigger = CronTrigger(day=1, hour=3, minute=0) # Run monthly on the 1st at 3 AM UTC
                else:
                    logger.warning(f"Unknown check_frequency '{form.check_frequency}' for form {form.name}. Skipping scheduling.")
                    continue
                
                self.scheduler.add_job(
                    self._monitor_form_job,
                    trigger,
                    args=[form.id],
                    id=job_id,
                    name=f"Monitor {form.name}",
                    replace_existing=True
                )
                logger.info(f"Scheduled job '{job_id}' for form '{form.name}' with frequency '{form.check_frequency}'")
        except Exception as e:
            logger.error(f"Error loading jobs from database: {e}")
        finally:
            session.close()

    def _monitor_form_job(self, form_id):
        """Job function to monitor a single form."""
        session = SessionLocal()
        form = session.query(Form).get(form_id)
        if not form:
            logger.error(f"Form with ID {form_id} not found for monitoring job.")
            session.close()
            return

        logger.info(f"Executing scheduled monitoring for form: {form.name} from {form.agency.name}")
        
        run_status = 'success'
        run_details = f"Monitored form {form.name}."
        changes_detected_count = 0
        start_time = datetime.utcnow()

        try:
            current_content = self.scraper.scrape(form.url)
            if current_content:
                is_changed, change_details, severity = self.detector.detect_changes(form, current_content)
                if is_changed:
                    logger.warning(f"Change detected for {form.name}: {change_details}")
                    change_entry = Change(
                        form_id=form.id,
                        timestamp=datetime.utcnow(),
                        change_details=change_details,
                        severity=severity,
                        is_reviewed=False
                    )
                    session.add(change_entry)
                    session.commit()
                    changes_detected_count += 1
                    
                    # Send notification
                    subject = f"🚨 Payroll Form Change Detected: {form.name} ({form.agency.abbreviation})"
                    body_html = f"""
                    <html>
                    <body>
                        <p>A change has been detected for the form <b>{form.name} - {form.title}</b> from the <b>{form.agency.name}</b>.</p>
                        <p><b>Details:</b> {change_details}</p>
                        <p><b>Severity:</b> <span style="color: {'red' if severity == 'critical' else 'orange' if severity == 'high' else 'yellow' if severity == 'medium' else 'gray'};">{severity.upper()}</span></p>
                        <p><b>Form URL:</b> <a href="{form.url}">{form.url}</a></p>
                        <p>Please review the changes and assess the impact.</p>
                        <p>This notification was sent by the Payroll Monitoring System.</p>
                    </body>
                    </html>
                    """
                    plain_text_message = f"Change detected for {form.name} ({form.agency.abbreviation}). Details: {change_details}. Severity: {severity}. URL: {form.url}"
                    self.notifier.send_notification(subject, body_html, plain_text_message)
                else:
                    logger.info(f"No significant change detected for {form.name}.")
                
                form.last_scraped_at = datetime.utcnow()
                session.add(form)
                session.commit()
            else:
                run_status = 'partial_success'
                run_details += f" Could not scrape content for {form.name}."
                logger.warning(f"Could not scrape content for form {form.name}.")

        except Exception as e:
            logger.error(f"Error monitoring form {form.name}: {e}")
            run_status = 'failure'
            run_details += f" Error: {e}"
            session.rollback() # Rollback any changes if an error occurred

        finally:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            monitoring_run = MonitoringRun(
                timestamp=start_time,
                status=run_status,
                details=run_details,
                duration_seconds=int(duration),
                forms_checked=1,
                changes_detected=changes_detected_count
            )
            session.add(monitoring_run)
            session.commit()
            session.close()
            logger.info(f"Finished scheduled monitoring for form: {form.name}. Status: {run_status}")

    def start(self):
        """Starts the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started.")
        else:
            logger.info("Scheduler is already running.")

    def shutdown(self):
        """Shuts down the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shut down.")
        else:
            logger.info("Scheduler is not running.")

    def get_jobs(self):
        """Returns a list of scheduled jobs."""
        return self.scheduler.get_jobs()

    def run_immediate_check(self):
        """Runs an immediate check for all forms (for testing/manual trigger)."""
        logger.info("Running immediate check for all forms...")
        session = SessionLocal()
        try:
            forms = session.query(Form).all()
            for form in forms:
                self._monitor_form_job(form.id) # Directly call the job function
        except Exception as e:
            logger.error(f"Error during immediate check: {e}")
        finally:
            session.close()
        logger.info("Immediate check completed.")