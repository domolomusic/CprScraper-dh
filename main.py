import argparse
import logging
import os
import sys
import threading
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.utils.config_loader import ConfigLoader
from src.database.connection import init_db, db_session
from src.database.models import Base, Agency, Form, Change
from src.monitors.web_scraper import WebScraper
from src.monitors.change_detector import ChangeDetector
from src.notifications.notifier import Notifier
from src.scheduler.monitoring_scheduler import MonitoringScheduler
from src.api.main import app as flask_app, set_scheduler_instance # Import Flask app and setter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

config_loader = ConfigLoader()
app_config = config_loader.get_config()

def load_agency_data():
    """Loads agency and form data from config/agencies.yaml into the database."""
    logger.info("Loading agency and form data...")
    federal_agencies_config = app_config.get('federal', {})
    state_agencies_config = app_config.get('states', {})

    with db_session() as session:
        # Process Federal Agencies
        for agency_key, agency_data in federal_agencies_config.items():
            agency = session.query(Agency).filter_by(name=agency_data['name']).first()
            if not agency:
                agency = Agency(
                    name=agency_data['name'],
                    base_url=agency_data.get('base_url'),
                    phone=agency_data.get('contact', {}).get('phone'),
                    email=agency_data.get('contact', {}).get('email')
                )
                session.add(agency)
                session.flush() # To get agency.id

            for form_data in agency_data.get('forms', []):
                form = session.query(Form).filter_by(agency_id=agency.id, name=form_data['name']).first()
                if not form:
                    form = Form(
                        agency_id=agency.id,
                        name=form_data['name'],
                        title=form_data.get('title'),
                        url=form_data['url'],
                        form_url=form_data.get('form_url'),
                        instructions_url=form_data.get('instructions_url'),
                        check_frequency=form_data.get('check_frequency', app_config.get('monitoring_settings', {}).get('default_check_frequency')),
                        contact_email=form_data.get('contact_email')
                    )
                    session.add(form)
        
        # Process State Agencies
        for agency_key, agency_data in state_agencies_config.items():
            agency = session.query(Agency).filter_by(name=agency_data['name']).first()
            if not agency:
                agency = Agency(
                    name=agency_data['name'],
                    abbreviation=agency_data.get('abbreviation'),
                    base_url=agency_data.get('base_url'),
                    prevailing_wage_url=agency_data.get('prevailing_wage_url'),
                    phone=agency_data.get('contact', {}).get('phone'),
                    email=agency_data.get('contact', {}).get('email')
                )
                session.add(agency)
                session.flush() # To get agency.id

            for form_data in agency_data.get('forms', []):
                form = session.query(Form).filter_by(agency_id=agency.id, name=form_data['name']).first()
                if not form:
                    form = Form(
                        agency_id=agency.id,
                        name=form_data['name'],
                        title=form_data.get('title'),
                        url=form_data['url'],
                        form_url=form_data.get('form_url'),
                        instructions_url=form_data.get('instructions_url'),
                        check_frequency=form_data.get('check_frequency', app_config.get('monitoring_settings', {}).get('default_check_frequency')),
                        contact_email=form_data.get('contact_email')
                    )
                    session.add(form)
        session.commit()
    logger.info("Agency and form data loaded successfully.")

def monitor_all_forms():
    """Monitors all forms in the database for changes."""
    logger.info("Starting a full monitoring run...")
    scraper = WebScraper(config_loader)
    detector = ChangeDetector()
    notifier = Notifier(config_loader)

    with db_session() as session:
        forms = session.query(Form).all()
        for form in forms:
            logger.info(f"Monitoring form: {form.name} from {form.agency.name}")
            
            target_url = form.form_url if form.form_url else form.url
            if not target_url:
                logger.warning(f"Skipping form {form.name}: No URL configured.")
                continue

            new_content = None
            new_hash_value = None

            try:
                if target_url.lower().endswith('.pdf'):
                    logger.info(f"Fetching PDF hash for {form.name} from {target_url}")
                    new_hash_value = scraper.get_pdf_hash(target_url)
                    if not new_hash_value:
                        logger.error(f"Failed to get PDF hash for {form.name} from {target_url}")
                        continue
                else:
                    logger.info(f"Fetching HTML content for {form.name} from {target_url}")
                    # For now, not using JS rendering by default. Can be added as a form property.
                    new_content = scraper.fetch_content(target_url, use_js_rendering=False) 
                    if not new_content:
                        logger.error(f"Failed to fetch HTML content for {form.name} from {target_url}")
                        continue
                
                is_changed, change_details, final_new_hash = detector.detect_change(
                    form.last_hash, 
                    new_content=new_content, 
                    new_hash_value=new_hash_value
                )
                
                if is_changed:
                    logger.warning(f"Change detected for {form.name}! Details: {change_details}")
                    # Determine severity (simple example, could be more complex based on change_details)
                    severity = "medium" 
                    if "critical" in change_details.lower():
                        severity = "critical"
                    elif "major" in change_details.lower() or "significant" in change_details.lower():
                        severity = "high"
                    
                    change = Change(
                        form_id=form.id,
                        timestamp=datetime.utcnow(),
                        change_details=change_details,
                        severity=severity
                    )
                    session.add(change)
                    session.commit() # Commit immediately to get change ID for notification
                    
                    notifier.send_alert(change)
                    logger.info(f"Alert sent for change on {form.name}.")
                else:
                    logger.info(f"No change detected for {form.name}.")
                
                form.last_hash = final_new_hash
                form.last_scraped_at = datetime.utcnow()
                session.add(form)
                session.commit()

            except Exception as e:
                logger.error(f"Error monitoring {form.name} at {target_url}: {e}")
    logger.info("Full monitoring run completed.")

def run_dashboard():
    """Runs the Flask web dashboard."""
    logger.info("Starting Flask web dashboard...")
    flask_app.run(debug=True, host='0.0.0.0', port=8000)

def run_scheduler_only():
    """Runs only the monitoring scheduler."""
    logger.info("Starting monitoring scheduler...")
    scheduler = MonitoringScheduler(config_loader, monitor_all_forms)
    set_scheduler_instance(scheduler) # Pass the scheduler instance to the Flask app
    scheduler.add_monitoring_jobs() # Add jobs based on config/DB
    scheduler.start()
    
    # Keep the main thread alive for the scheduler
    try:
        while True:
            import time
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()
        logger.info("Scheduler stopped.")

def run_tests():
    """Runs system tests."""
    logger.info("Running system tests...")
    try:
        # Test database connection
        with db_session() as session:
            session.query(Agency).first()
        logger.info("Database connection test: SUCCESS")

        # Test config loading
        test_config = config_loader.get_config()
        if test_config:
            logger.info("Config loading test: SUCCESS")
        else:
            logger.error("Config loading test: FAILED (config is empty)")

        # Test notifier (sends dummy email/slack/teams)
        notifier = Notifier(config_loader)
        notifier.test_notifications()
        logger.info("Notifier test: Check your configured notification channels for test messages.")

        logger.info("All basic tests completed. Review logs for details.")
    except Exception as e:
        logger.error(f"An error occurred during tests: {e}")
    logger.info("System tests finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Payroll Monitoring System CLI")
    parser.add_argument('command', choices=['init-db', 'load-data', 'monitor', 'start', 'dashboard', 'scheduler', 'test'],
                        help="Command to execute")

    args = parser.parse_args()

    if args.command == 'init-db':
        init_db()
        logger.info("Database initialized.")
    elif args.command == 'load-data':
        load_agency_data()
    elif args.command == 'monitor':
        monitor_all_forms()
    elif args.command == 'start':
        # Start scheduler in a separate thread
        scheduler_thread = threading.Thread(target=run_scheduler_only)
        scheduler_thread.daemon = True # Allow main program to exit even if thread is running
        scheduler_thread.start()
        
        # Run dashboard in the main thread (Flask's run() is blocking)
        run_dashboard()
    elif args.command == 'dashboard':
        run_dashboard()
    elif args.command == 'scheduler':
        run_scheduler_only()
    elif args.command == 'test':
        run_tests()