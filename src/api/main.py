import os
from flask import Flask, render_template, jsonify, request
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import logging

from src.database.models import Base, Agency, Form, Change
from src.utils.config_loader import load_config
from src.monitors.monitoring_scheduler import MonitoringScheduler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Determine the absolute path to the project root
# This assumes main.py is in src/api/ and templates is in the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
template_dir = os.path.join(project_root, 'templates')
static_dir = os.path.join(project_root, 'static')

# Initialize Flask app
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Database setup (using environment variable for URL)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./data/payroll_monitor.db')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Initialize scheduler (will be started by main.py)
scheduler = None

def get_db_session():
    """Helper function to get a new database session."""
    return Session()

@app.route('/')
def index():
    session = get_db_session()
    total_agencies = session.query(Agency).count()
    total_forms = session.query(Form).count()

    # Get recent changes (e.g., last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_changes = session.query(Change).filter(Change.timestamp >= seven_days_ago).order_by(Change.timestamp.desc()).all()
    
    session.close()
    return render_template('index.html', 
                           total_agencies=total_agencies, 
                           total_forms=total_forms, 
                           recent_changes=recent_changes)

@app.route('/agencies')
def agencies():
    session = get_db_session()
    all_agencies = session.query(Agency).order_by(Agency.name).all()
    session.close()
    return render_template('agencies.html', agencies=all_agencies)

@app.route('/agency/<int:agency_id>')
def agency_detail(agency_id):
    session = get_db_session()
    agency = session.query(Agency).filter_by(id=agency_id).first_or_404()
    forms = session.query(Form).filter_by(agency_id=agency_id).order_by(Form.name).all()
    session.close()
    return render_template('agency_detail.html', agency=agency, forms=forms)

@app.route('/form/<int:form_id>')
def form_detail(form_id):
    session = get_db_session()
    form = session.query(Form).filter_by(id=form_id).first_or_404()
    changes = session.query(Change).filter_by(form_id=form_id).order_by(Change.timestamp.desc()).all()
    session.close()
    return render_template('form_detail.html', form=form, changes=changes)

# API Endpoints
@app.route('/api/stats')
def api_stats():
    session = get_db_session()
    total_agencies = session.query(Agency).count()
    total_forms = session.query(Form).count()
    recent_changes_count = session.query(Change).filter(Change.timestamp >= datetime.utcnow() - timedelta(days=7)).count()
    session.close()
    return jsonify({
        'total_agencies': total_agencies,
        'total_forms': total_forms,
        'recent_changes_7d': recent_changes_count
    })

@app.route('/api/agencies')
def api_agencies():
    session = get_db_session()
    agencies_data = [{'id': a.id, 'name': a.name, 'abbreviation': a.abbreviation, 'base_url': a.base_url} for a in session.query(Agency).all()]
    session.close()
    return jsonify(agencies_data)

@app.route('/api/forms')
def api_forms():
    session = get_db_session()
    forms_data = [{'id': f.id, 'name': f.name, 'title': f.title, 'url': f.url, 'agency_id': f.agency_id} for f in session.query(Form).all()]
    session.close()
    return jsonify(forms_data)

@app.route('/api/changes')
def api_changes():
    session = get_db_session()
    changes_data = []
    for change in session.query(Change).order_by(Change.timestamp.desc()).limit(50).all():
        changes_data.append({
            'id': change.id,
            'form_id': change.form_id,
            'timestamp': change.timestamp.isoformat(),
            'change_details': change.change_details,
            'severity': change.severity,
            'is_reviewed': change.is_reviewed
        })
    session.close()
    return jsonify(changes_data)

@app.route('/api/scheduler/status')
def api_scheduler_status():
    global scheduler
    if scheduler:
        return jsonify({'status': 'running' if scheduler.is_running() else 'stopped'})
    return jsonify({'status': 'not initialized'})

@app.route('/api/scheduler/start', methods=['POST'])
def api_scheduler_start():
    global scheduler
    if scheduler and not scheduler.is_running():
        scheduler.start()
        return jsonify({'message': 'Scheduler started'}), 200
    return jsonify({'message': 'Scheduler already running or not initialized'}), 400

@app.route('/api/scheduler/stop', methods=['POST'])
def api_scheduler_stop():
    global scheduler
    if scheduler and scheduler.is_running():
        scheduler.stop()
        return jsonify({'message': 'Scheduler stopped'}), 200
    return jsonify({'message': 'Scheduler not running or not initialized'}), 400

@app.route('/api/scheduler/run-immediate', methods=['POST'])
def api_scheduler_run_immediate():
    global scheduler
    if scheduler:
        scheduler.run_immediate_check()
        return jsonify({'message': 'Immediate monitoring check initiated'}), 200
    return jsonify({'message': 'Scheduler not initialized'}), 400

def set_scheduler(s):
    """Allows main.py to pass the scheduler instance to the API."""
    global scheduler
    scheduler = s

if __name__ == '__main__':
    # This block is for direct running of the Flask app for development/testing
    # In production, it's typically run via main.py or a WSGI server
    logging.info("Running Flask app directly for development.")
    app.run(host='0.0.0.0', port=8000, debug=True)