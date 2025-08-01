import argparse
import logging
import os
from src.database.connection import init_db, SessionLocal
from src.utils.config_loader import load_agencies_from_yaml
from src.monitors.web_scraper import WebScraper
from src.monitors.change_detector import ChangeDetector
from src.notifications.notifier import Notifier
from src.scheduler.monitoring_scheduler import MonitoringScheduler
from src.api.main import app as flask_app # Import the Flask app

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    parser = argparse.ArgumentParser(description="Payroll Monitoring System")
    parser.add_argument("command", choices=["init-db", "load-data", "monitor", "dashboard", "scheduler", "test"],
                        help="Command to execute")

    args = parser.parse_args()

    if args.command == "init-db":
        logging.info("Initializing database...")
        init_db()
        logging.info("Database initialization complete.")
    elif args.command == "load-data":
        logging.info("Loading agency and form data from config/agencies.yaml into database...")
        db_session = SessionLocal()
        try:
            load_agencies_from_yaml(db_session)
            logging.info("Data loading complete.")
        except Exception as e:
            logging.error(f"Error loading data: {e}")
            db_session.rollback()
        finally:
            db_session.close()
    elif args.command == "monitor":
        logging.info("Running immediate monitoring check...")
        # Placeholder for full monitoring logic
        db_session = SessionLocal()
        try:
            scraper = WebScraper()
            detector = ChangeDetector()
            # notifier = Notifier() # Will initialize later with proper config
            
            forms = db_session.query(Form).all()
            for form in forms:
                logging.info(f"Monitoring form: {form.name} from {form.agency.name}")
                new_content = scraper.scrape_page(form.url)
                
                if new_content:
                    is_changed, change_details = detector.detect_change(form.last_scraped_content, new_content)
                    
                    if is_changed:
                        logging.warning(f"Change detected for {form.name} ({form.agency.name}): {change_details['message']}")
                        # Save change to DB
                        # new_change = Change(
                        #     form_id=form.id,
                        #     old_content_hash=change_details.get('old_hash'),
                        #     new_content_hash=change_details.get('new_hash'),
                        #     change_details=change_details['message'],
                        #     severity="medium" # Default severity
                        # )
                        # db_session.add(new_change)
                        # db_session.commit()
                        # notifier.send_alert(form, change_details) # Send notification
                    else:
                        logging.info(f"No change detected for {form.name} ({form.agency.name}).")
                    
                    # Update last scraped content and timestamp
                    form.last_scraped_content = new_content
                    form.last_scraped_at = datetime.utcnow()
                    db_session.commit()
                else:
                    logging.error(f"Failed to scrape content for {form.name} at {form.url}")
        except Exception as e:
            logging.error(f"Error during monitoring run: {e}")
            db_session.rollback()
        finally:
            db_session.close()
        logging.info("Monitoring check complete.")
    elif args.command == "dashboard":
        logging.info("Starting web dashboard...")
        # This will run the Flask app
        # For development, you might use: flask_app.run(debug=True, port=8000)
        # For production, use a WSGI server like Gunicorn
        from werkzeug.serving import run_simple
        run_simple('0.0.0.0', 8000, flask_app, use_reloader=True, use_debugger=True)
    elif args.command == "scheduler":
        logging.info("Starting monitoring scheduler...")
        scheduler = MonitoringScheduler()
        scheduler.start()
        # Keep the main thread alive
        try:
            while True:
                pass
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            logging.info("Scheduler stopped.")
    elif args.command == "test":
        logging.info("Running system tests...")
        # Placeholder for running tests
        print("No specific system tests implemented yet beyond component self-tests.")
        print("You can run individual component tests like: python src/monitors/web_scraper.py")
        print("And: python src/monitors/change_detector.py")
    else:
        parser.print_help()

if __name__ == "__main__":
    from datetime import datetime # Import here to avoid circular dependency if main is imported elsewhere
    from src.database.models import Form, Change # Import models for type hinting and usage in monitor command
    main()