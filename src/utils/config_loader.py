import yaml
import os
import logging
from sqlalchemy.orm import Session
from src.database.models import Agency, Form
from src.database.connection import SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_agencies_from_yaml(db: Session, config_path='config/agencies.yaml'):
    """
    Loads agency and form data from a YAML file into the database.
    
    Args:
        db (Session): The SQLAlchemy database session.
        config_path (str): The path to the YAML configuration file.
    """
    if not os.path.exists(config_path):
        logging.error(f"Configuration file not found at {config_path}")
        return

    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)

    if not config:
        logging.warning("YAML configuration is empty.")
        return

    logging.info(f"Loading agencies and forms from {config_path} into the database...")

    # Process Federal Agencies
    if 'federal' in config:
        for agency_key, agency_data in config['federal'].items():
            _process_agency(db, agency_data, is_federal=True)

    # Process State Agencies
    if 'states' in config:
        for agency_key, agency_data in config['states'].items():
            _process_agency(db, agency_data, is_federal=False)
            
    db.commit()
    logging.info("Finished loading agencies and forms.")

def _process_agency(db: Session, agency_data: dict, is_federal: bool):
    """Helper to process individual agency data and its forms."""
    agency_name = agency_data.get('name')
    if not agency_name:
        logging.warning(f"Skipping agency due to missing 'name': {agency_data}")
        return

    agency = db.query(Agency).filter_by(name=agency_name).first()
    if not agency:
        agency = Agency(
            name=agency_name,
            abbreviation=agency_data.get('abbreviation'),
            base_url=agency_data.get('base_url'),
            prevailing_wage_url=agency_data.get('prevailing_wage_url'),
            phone=agency_data.get('contact', {}).get('phone'),
            email=agency_data.get('contact', {}).get('email')
        )
        db.add(agency)
        db.flush() # Flush to get agency.id for forms
        logging.info(f"Added new agency: {agency.name}")
    else:
        # Update existing agency details if necessary
        agency.abbreviation = agency_data.get('abbreviation', agency.abbreviation)
        agency.base_url = agency_data.get('base_url', agency.base_url)
        agency.prevailing_wage_url = agency_data.get('prevailing_wage_url', agency.prevailing_wage_url)
        agency.phone = agency_data.get('contact', {}).get('phone', agency.phone)
        agency.email = agency_data.get('contact', {}).get('email', agency.email)
        logging.info(f"Updated existing agency: {agency.name}")

    for form_data in agency_data.get('forms', []):
        _process_form(db, agency, form_data)

def _process_form(db: Session, agency: Agency, form_data: dict):
    """Helper to process individual form data."""
    form_name = form_data.get('name')
    form_title = form_data.get('title')
    form_url = form_data.get('url')

    if not all([form_name, form_title, form_url]):
        logging.warning(f"Skipping form due to missing required fields (name, title, url): {form_data}")
        return

    form = db.query(Form).filter_by(agency_id=agency.id, name=form_name).first()
    if not form:
        form = Form(
            agency_id=agency.id,
            name=form_name,
            title=form_title,
            url=form_url,
            form_url=form_data.get('form_url'),
            instructions_url=form_data.get('instructions_url'),
            check_frequency=form_data.get('check_frequency', "weekly"),
            contact_email=form_data.get('contact_email')
        )
        db.add(form)
        logging.info(f"Added new form: {form.name} for {agency.name}")
    else:
        # Update existing form details if necessary
        form.title = form_data.get('title', form.title)
        form.url = form_data.get('url', form.url)
        form.form_url = form_data.get('form_url', form.form_url)
        form.instructions_url = form_data.get('instructions_url', form.instructions_url)
        form.check_frequency = form_data.get('check_frequency', form.check_frequency)
        form.contact_email = form_data.get('contact_email', form.contact_email)
        logging.info(f"Updated existing form: {form.name} for {agency.name}")

if __name__ == '__main__':
    # Example usage for testing the config loader
    # This will attempt to load data into your configured database
    print("Running config_loader.py directly for testing...")
    db_session = SessionLocal()
    try:
        load_agencies_from_yaml(db_session)
        print("Configuration loaded successfully. Check your database.")
    except Exception as e:
        print(f"An error occurred: {e}")
        db_session.rollback()
    finally:
        db_session.close()