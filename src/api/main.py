from flask import Flask, jsonify, request, render_template
import logging
from datetime import datetime, timedelta

# Assuming these imports are available in the src directory
from src.database.connection import db_session
from src.database.models import Agency, Form, Change
from src.notifications.notifier import Notifier
from src.utils.config_loader import ConfigLoader

app = Flask(__name__, template_folder='../../templates', static_folder='../../static')
logger = logging.getLogger(__name__)

# Global variables to hold scheduler and monitor function instances
# These will be set by main.py
_scheduler_instance = None
_monitor_all_forms_function = None

def set_scheduler_instance(scheduler):
    global _scheduler_instance
    _scheduler_instance = scheduler
    logger.info("Scheduler instance set in API.")

def set_monitor_function(func):
    global _monitor_all_forms_function
    _monitor_all_forms_function = func
    logger.info("Monitor function set in API.")

@app.route('/')
def index():
    with db_session() as session:
        total_agencies = session.query(Agency).count()
        total_forms = session.query(Form).count()
        
        # Get recent changes (e.g., last 24 hours)
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        recent_changes = session.query(Change).filter(Change.timestamp >= one_day_ago).order_by(Change.timestamp.desc()).all()

        return render_template('index.html', 
                               total_agencies=total_agencies, 
                               total_forms=total_forms, 
                               recent_changes=recent_changes)

@app.route('/agencies')
def agencies_page():
    with db_session() as session:
        agencies = session.query(Agency).order_by(Agency.name).all()
        return render_template('agencies.html', agencies=agencies)

@app.route('/agency/<int:agency_id>')
def agency_detail_page(agency_id):
    with db_session() as session:
        agency = session.query(Agency).filter_by(id=agency_id).first_or_404()
        forms = session.query(Form).filter_by(agency_id=agency_id).order_by(Form.name).all()
        return render_template('agency_detail.html', agency=agency, forms=forms)

@app.route('/form/<int:form_id>')
def form_detail_page(form_id):
    with db_session() as session:
        form = session.query(Form).filter_by(id=form_id).first_or_404()
        changes = session.query(Change).filter_by(form_id=form_id).order_by(Change.timestamp.desc()).all()
        return render_template('form_detail.html', form=form, changes=changes)


# API Endpoints
@app.route('/api/stats', methods=['GET'])
def get_stats():
    with db_session() as session:
        total_agencies = session.query(Agency).count()
        total_forms = session.query(Form).count()
        recent_changes_count = session.query(Change).filter(Change.timestamp >= datetime.utcnow() - timedelta(days=1)).count()
        
        return jsonify({
            'total_agencies': total_agencies,
            'total_forms': total_forms,
            'recent_changes_24h': recent_changes_count
        })

@app.route('/api/agencies', methods=['GET'])
def get_agencies():
    with db_session() as session:
        agencies = session.query(Agency).all()
        return jsonify([{
            'id': a.id,
            'name': a.name,
            'abbreviation': a.abbreviation,
            'base_url': a.base_url,
            'prevailing_wage_url': a.prevailing_wage_url,
            'phone': a.phone,
            'email': a.email
        } for a in agencies])

@app.route('/api/agencies/<int:agency_id>/forms', methods=['GET'])
def get_agency_forms(agency_id):
    with db_session() as session:
        agency = session.query(Agency).filter_by(id=agency_id).first()
        if not agency:
            return jsonify({'error': 'Agency not found'}), 404
        
        forms = session.query(Form).filter_by(agency_id=agency_id).all()
        return jsonify([{
            'id': f.id,
            'name': f.name,
            'title': f.title,
            'url': f.url,
            'form_url': f.form_url,
            'instructions_url': f.instructions_url,
            'check_frequency': f.check_frequency,
            'contact_email': f.contact_email,
            'last_scraped_at': f.last_scraped_at.isoformat() if f.last_scraped_at else None
        } for f in forms])

@app.route('/api/forms/<int:form_id>/changes', methods=['GET'])
def get_form_changes(form_id):
    with db_session() as session:
        form = session.query(Form).filter_by(id=form_id).first()
        if not form:
            return jsonify({'error': 'Form not found'}), 404
        
        changes = session.query(Change).filter_by(form_id=form_id).order_by(Change.timestamp.desc()).all()
        return jsonify([{
            'id': c.id,
            'timestamp': c.timestamp.isoformat(),
            'change_details': c.change_details,
            'severity': c.severity,
            'is_reviewed': c.is_reviewed
        } for c in changes])

@app.route('/api/changes', methods=['GET'])
def get_recent_changes():
    with db_session() as session:
        # Fetch all changes, ordered by timestamp, for the API.
        # The dashboard might filter by 'recent' but API can provide full list.
        changes = session.query(Change).order_by(Change.timestamp.desc()).limit(100).all() # Limit for performance
        return jsonify([{
            'id': c.id,
            'form_id': c.form_id,
            'form_name': c.form.name,
            'agency_name': c.form.agency.name,
            'timestamp': c.timestamp.isoformat(),
            'change_details': c.change_details,
            'severity': c.severity,
            'is_reviewed': c.is_reviewed
        } for c in changes])

@app.route('/api/scheduler/status', methods=['GET'])
def get_scheduler_status():
    if _scheduler_instance:
        return jsonify(_scheduler_instance.get_scheduler_info())
    return jsonify({'error': 'Scheduler not initialized'}), 500

@app.route('/api/scheduler/start', methods=['POST'])
def start_scheduler():
    if _scheduler_instance:
        _scheduler_instance.start()
        return jsonify({'message': 'Scheduler started'}), 200
    return jsonify({'error': 'Scheduler not initialized'}), 500

@app.route('/api/scheduler/stop', methods=['POST'])
def stop_scheduler():
    if _scheduler_instance:
        _scheduler_instance.stop()
        return jsonify({'message': 'Scheduler stopped'}), 200
    return jsonify({'error': 'Scheduler not initialized'}), 500

@app.route('/api/scheduler/run-immediate', methods=['POST'])
def run_immediate_monitor():
    if _monitor_all_forms_function:
        # Run in a separate thread to avoid blocking the API request
        import threading
        threading.Thread(target=_monitor_all_forms_function).start()
        return jsonify({'message': 'Immediate monitoring run initiated'}), 202
    return jsonify({'error': 'Monitor function not available'}), 500

@app.route('/api/notifications/test', methods=['POST'])
def test_notifications_api():
    try:
        config_loader = ConfigLoader() # Re-initialize to ensure latest config
        notifier = Notifier(config_loader)
        notifier.test_notifications()
        return jsonify({'message': 'Test notifications sent. Check logs and configured channels.'}), 200
    except Exception as e:
        logger.error(f"Error sending test notifications via API: {e}")
        return jsonify({'error': f'Failed to send test notifications: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    try:
        with db_session() as session:
            # Try to query something simple to check DB connection
            session.query(Agency).first()
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'database': 'disconnected', 'error': str(e)}), 500