import logging
from datetime import datetime, timedelta

from flask import Flask, render_template, jsonify, request

from src.utils.config_loader import ConfigLoader
from src.database.models import Agency, Form, Change
from src.database.connection import db_session
from src.scheduler.monitoring_scheduler import MonitoringScheduler
from src.notifications.notifier import Notifier

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, template_folder='../../templates', static_folder='../../static')

# Initialize ConfigLoader
config_loader = ConfigLoader()
app_config = config_loader.get_config()

# Global variable to hold the scheduler instance, set by main.py
scheduler_instance = None 

def set_scheduler_instance(scheduler):
    """Sets the global scheduler instance for API access."""
    global scheduler_instance
    scheduler_instance = scheduler

# --- Web Dashboard Routes ---

@app.route('/')
def dashboard():
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
def list_agencies():
    with db_session() as session:
        agencies = session.query(Agency).order_by(Agency.name).all()
        return render_template('agencies.html', agencies=agencies)

@app.route('/agency/<int:agency_id>')
def agency_detail(agency_id):
    with db_session() as session:
        agency = session.query(Agency).filter_by(id=agency_id).first_or_404()
        forms = session.query(Form).filter_by(agency_id=agency_id).order_by(Form.name).all()
        return render_template('agency_detail.html', agency=agency, forms=forms)

@app.route('/form/<int:form_id>')
def form_detail(form_id):
    with db_session() as session:
        form = session.query(Form).filter_by(id=form_id).first_or_404()
        changes = session.query(Change).filter_by(form_id=form_id).order_by(Change.timestamp.desc()).all()
        return render_template('form_detail.html', form=form, changes=changes)

# --- API Endpoints ---

@app.route('/api/stats', methods=['GET'])
def get_stats():
    with db_session() as session:
        total_agencies = session.query(Agency).count()
        total_forms = session.query(Form).count()
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        recent_changes_count = session.query(Change).filter(Change.timestamp >= one_day_ago).count()
        
        return jsonify({
            'total_agencies': total_agencies,
            'total_forms': total_forms,
            'recent_changes_24h': recent_changes_count
        })

@app.route('/api/agencies', methods=['GET'])
def api_list_agencies():
    with db_session() as session:
        agencies = session.query(Agency).all()
        return jsonify([agency.to_dict() for agency in agencies])

@app.route('/api/agencies/<int:agency_id>/forms', methods=['GET'])
def api_agency_forms(agency_id):
    with db_session() as session:
        forms = session.query(Form).filter_by(agency_id=agency_id).all()
        return jsonify([form.to_dict() for form in forms])

@app.route('/api/changes', methods=['GET'])
def api_list_changes():
    with db_session() as session:
        changes = session.query(Change).order_by(Change.timestamp.desc()).limit(100).all() # Limit for API
        return jsonify([change.to_dict() for change in changes])

# --- Scheduler Control API ---

@app.route('/api/scheduler/status', methods=['GET'])
def scheduler_status():
    if scheduler_instance:
        return jsonify({'status': 'running' if scheduler_instance.is_running() else 'stopped'})
    return jsonify({'status': 'unknown', 'message': 'Scheduler not initialized or running in this process.'})

@app.route('/api/scheduler/start', methods=['POST'])
def scheduler_start():
    if scheduler_instance:
        scheduler_instance.start()
        return jsonify({'status': 'started', 'message': 'Scheduler started.'})
    return jsonify({'status': 'error', 'message': 'Scheduler not initialized.'}), 500

@app.route('/api/scheduler/stop', methods=['POST'])
def scheduler_stop():
    if scheduler_instance:
        scheduler_instance.stop()
        return jsonify({'status': 'stopped', 'message': 'Scheduler stopped.'})
    return jsonify({'status': 'error', 'message': 'Scheduler not initialized.'}), 500

@app.route('/api/scheduler/run-immediate', methods=['POST'])
def scheduler_run_immediate():
    if scheduler_instance:
        # This would ideally trigger an immediate job run
        logger.info("Triggering immediate monitoring run via API.")
        # A more robust implementation would add a one-time job to the scheduler
        return jsonify({'status': 'triggered', 'message': 'Immediate monitoring run triggered (if scheduler is active).'})
    return jsonify({'status': 'error', 'message': 'Scheduler not initialized.'}), 500

# --- Notification API ---

@app.route('/api/notifications/send', methods=['POST'])
def send_notification_api():
    data = request.get_json()
    if not data or 'change_id' not in data:
        return jsonify({'error': 'Missing change_id in request body'}), 400
    
    change_id = data['change_id']
    with db_session() as session:
        change = session.query(Change).filter_by(id=change_id).first()
        if not change:
            return jsonify({'error': 'Change not found'}), 404
        
        notifier = Notifier(config_loader) 
        try:
            notifier.send_alert(change)
            return jsonify({'status': 'success', 'message': f'Notification sent for change {change_id}'})
        except Exception as e:
            logger.error(f"Error sending notification for change {change_id}: {e}")
            return jsonify({'status': 'error', 'message': f'Failed to send notification: {str(e)}'}), 500

@app.route('/api/notifications/test', methods=['POST'])
def test_notifications_api():
    notifier = Notifier(config_loader)
    try:
        notifier.test_notifications()
        return jsonify({'status': 'success', 'message': 'Test notifications sent.'})
    except Exception as e:
        logger.error(f"Error sending test notifications: {e}")
        return jsonify({'status': 'error', 'message': f'Failed to send test notifications: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    # Basic health check: check database connection
    try:
        with db_session() as session:
            session.query(Agency).first() # Try to query something simple
        return jsonify({'status': 'healthy', 'database': 'connected'}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'database': 'disconnected', 'error': str(e)}), 500