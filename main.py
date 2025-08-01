import argparse
import logging
import os
from datetime import datetime

from src.database.connection import SessionLocal, engine
from src.database import models
from src.utils.config_loader import ConfigLoader
from src.monitors.web_scraper import WebScraper
from src.monitors.change_detector import ChangeDetector
from src.notifications.notifier import Notifier
from src.scheduler.monitoring_scheduler import MonitoringScheduler
from src.api.main import app as flask_app # Import the Flask app

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_db():
    """Initializes the database and creates tables."""
    logger.info("Initializing database...")
    models.Base.metadata.create_all(bind=engine)
    logger.info("Database initialized.")

def load_data():
    """Loads agency and form data from config/agencies.yaml into the database."""
    logger.info("Loading agency and form data from config/agencies.yaml...")
    config_loader = ConfigLoader()
    config = config_loader.get_config()

    federal_agencies_data = config.get('federal', {})
    state_agencies_data = config.get('states', {})

    session = SessionLocal()
    try:
        # Load Federal Agencies
        for agency_key, agency_data in federal_agencies_data.items():
            agency = session.query(models.Agency).filter_by(name=agency_data['name']).first()
            if not agency:
                agency = models.Agency(
                    name=agency_data['name'],
                    abbreviation=agency_data.get('abbreviation'),
                    base_url=agency_data.get('base_url'),
                    phone=agency_data.get('contact', {}).get('phone'),
                    email=agency_data.get('contact', {}).get('email'),
                    type='federal'
                )
                session.add(agency)
                session.flush() # To get agency.id

            for form_data in agency_data.get('forms', []):
                form = session.query(models.Form).filter_by(name=form_data['name'], agency_id=agency.id).first()
                if not form:
                    form = models.Form(
                        agency_id=agency.id,
                        name=form_data['name'],
                        title=form_data['title'],
                        url=form_data['url'],
                        form_url=form_data.get('form_url'),
                        instructions_url=form_data.get('instructions_url'),
                        check_frequency=form_data.get('check_frequency', config.get('monitoring_settings', {}).get('default_check_frequency', 'weekly')),
                        contact_email=form_data.get('contact_email'),
                        last_updated=form_data.get('last_updated')
                    )
                    session.add(form)
        
        # Load State Agencies
        for agency_key, agency_data in state_agencies_data.items():
            agency = session.query(models.Agency).filter_by(name=agency_data['name']).first()
            if not agency:
                agency = models.Agency(
                    name=agency_data['name'],
                    abbreviation=agency_data.get('abbreviation'),
                    base_url=agency_data.get('base_url'),
                    prevailing_wage_url=agency_data.get('prevailing_wage_url'),
                    phone=agency_data.get('contact', {}).get('phone'),
                    email=agency_data.get('contact', {}).get('email'),
                    type='state'
                )
                session.add(agency)
                session.flush() # To get agency.id

            for form_data in agency_data.get('forms', []):
                form = session.query(models.Form).filter_by(name=form_data['name'], agency_id=agency.id).first()
                if not form:
                    form = models.Form(
                        agency_id=agency.id,
                        name=form_data['name'],
                        title=form_data['title'],
                        url=form_data['url'],
                        form_url=form_data.get('form_url'),
                        instructions_url=form_data.get('instructions_url'),
                        check_frequency=form_data.get('check_frequency', config.get('monitoring_settings', {}).get('default_check_frequency', 'weekly')),
                        contact_email=form_data.get('contact_email'),
                        last_updated=form_data.get('last_updated')
                    )
                    session.add(form)

        session.commit()
        logger.info("Agency and form data loaded successfully.")
    except Exception as e:
        session.rollback()
        logger.error(f"Error loading data: {e}")
    finally:
        session.close()

def run_monitor():
    """Runs an immediate monitoring check for all forms."""
    logger.info("Starting immediate monitoring check...")
    session = SessionLocal()
    try:
        forms = session.query(models.Form).all()
        scraper = WebScraper()
        detector = ChangeDetector()
        notifier = Notifier()

        for form in forms:
            logger.info(f"Monitoring form: {form.name} from {form.agency.name}")
            try:
                current_content = scraper.scrape(form.url)
                if current_content:
                    is_changed, change_details, severity = detector.detect_changes(form, current_content)
                    if is_changed:
                        logger.warning(f"Change detected for {form.name}: {change_details}")
                        change_entry = models.Change(
                            form_id=form.id,
                            timestamp=datetime.utcnow(),
                            change_details=change_details,
                            severity=severity,
                            is_reviewed=False
                        )
                        session.add(change_entry)
                        session.commit() # Commit immediately to record the change
                        
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
                        notifier.send_notification(subject, body_html, plain_text_message)
                    else:
                        logger.info(f"No significant change detected for {form.name}.")
                    
                    # Update last_scraped_at regardless of change
                    form.last_scraped_at = datetime.utcnow()
                    session.add(form)
                    session.commit()

            except Exception as e:
                logger.error(f"Error monitoring form {form.name}: {e}")
                session.rollback() # Rollback if an error occurs during processing a single form
    except Exception as e:
        logger.error(f"Error during overall monitoring run: {e}")
    finally:
        session.close()
    logger.info("Immediate monitoring check finished.")

def start_dashboard():
    """Starts the Flask web dashboard."""
    logger.info("Starting Flask web dashboard...")
    # This will run the Flask app. Ensure FLASK_APP and FLASK_ENV are set if needed.
    # For development, you might run it directly like this:
    flask_app.run(debug=True, host='0.0.0.0', port=8000)

def start_scheduler():
    """Starts the monitoring scheduler."""
    logger.info("Starting monitoring scheduler...")
    scheduler = MonitoringScheduler()
    scheduler.start()
    # Keep the main thread alive for the scheduler
    try:
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler shut down.")

def run_tests():
    """Placeholder for running system tests."""
    logger.info("Running system tests (not yet implemented).")
    # In a real scenario, you'd integrate a testing framework like pytest here.

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Payroll Monitoring System CLI")
    parser.add_argument("command", choices=["init-db", "load-data", "monitor", "dashboard", "scheduler", "start", "test"],
                        help="Command to execute")

    args = parser.parse_args()

    if args.command == "init-db":
        init_db()
    elif args.command == "load-data":
        load_data()
    elif args.command == "monitor":
        run_monitor()
    elif args.command == "dashboard":
        start_dashboard()
    elif args.command == "scheduler":
        start_scheduler()
    elif args.command == "start":
        # This command will start both the dashboard and the scheduler
        # For simplicity, we'll start the dashboard in debug mode and assume
        # the scheduler will be run as a separate process or managed by a process manager.
        # In a production setup, these would typically be separate services.
        logger.info("Starting Payroll Monitoring System (Dashboard and Scheduler)...")
        # You might want to run these in separate threads/processes for a single 'start' command
        # For now, let's just start the dashboard, and the user can manually start scheduler if needed.
        # Or, we can make 'start' run both in a more robust way (e.g., using multiprocessing)
        # For this exercise, let's assume 'start' primarily launches the dashboard for preview.
        start_dashboard() # This is blocking, so scheduler won't start unless in a separate thread/process
        # If you want both, you'd need to use threading/multiprocessing:
        # import threading
        # dashboard_thread = threading.Thread(target=start_dashboard)
        # scheduler_thread = threading.Thread(target=start_scheduler)
        # dashboard_thread.start()
        # scheduler_thread.start()
        # dashboard_thread.join()
        # scheduler_thread.join()
    elif args.command == "test":
        run_tests()