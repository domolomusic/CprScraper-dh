from flask import Flask, render_template, jsonify
from sqlalchemy.orm import Session
from src.database.connection import SessionLocal, init_db
from src.database.models import Agency, Form, Change
import logging

# Configure logging for Flask app
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.route('/')
def index():
    """Dashboard home page showing recent changes and overall stats."""
    db: Session = next(get_db()) # Get a session
    
    total_agencies = db.query(Agency).count()
    total_forms = db.query(Form).count()
    recent_changes = db.query(Change).order_by(Change.timestamp.desc()).limit(10).all()
    
    return render_template('index.html', 
                           total_agencies=total_agencies,
                           total_forms=total_forms,
                           recent_changes=recent_changes)

@app.route('/agencies')
def list_agencies():
    """Page to list all monitored agencies."""
    db: Session = next(get_db())
    agencies = db.query(Agency).order_by(Agency.name).all()
    return render_template('agencies.html', agencies=agencies)

@app.route('/agency/<int:agency_id>')
def view_agency(agency_id):
    """Page to view details of a specific agency and its forms."""
    db: Session = next(get_db())
    agency = db.query(Agency).filter(Agency.id == agency_id).first_or_404()
    forms = db.query(Form).filter(Form.agency_id == agency_id).order_by(Form.name).all()
    return render_template('agency_detail.html', agency=agency, forms=forms)

@app.route('/form/<int:form_id>')
def view_form(form_id):
    """Page to view details of a specific form and its change history."""
    db: Session = next(get_db())
    form = db.query(Form).filter(Form.id == form_id).first_or_404()
    changes = db.query(Change).filter(Change.form_id == form_id).order_by(Change.timestamp.desc()).all()
    return render_template('form_detail.html', form=form, changes=changes)

# API Endpoints (as per README.md)
@app.route('/api/stats')
def api_stats():
    db: Session = next(get_db())
    total_agencies = db.query(Agency).count()
    total_forms = db.query(Form).count()
    recent_changes_count = db.query(Change).count() # Or filter by time
    return jsonify({
        "total_agencies": total_agencies,
        "total_forms": total_forms,
        "total_changes": recent_changes_count
    })

@app.route('/api/agencies')
def api_agencies():
    db: Session = next(get_db())
    agencies = db.query(Agency).all()
    return jsonify([
        {"id": a.id, "name": a.name, "abbreviation": a.abbreviation, "base_url": a.base_url}
        for a in agencies
    ])

@app.route('/api/agencies/<int:agency_id>/forms')
def api_agency_forms(agency_id):
    db: Session = next(get_db())
    forms = db.query(Form).filter(Form.agency_id == agency_id).all()
    return jsonify([
        {"id": f.id, "name": f.name, "title": f.title, "url": f.url, "check_frequency": f.check_frequency}
        for f in forms
    ])

@app.route('/api/changes')
def api_changes():
    db: Session = next(get_db())
    changes = db.query(Change).order_by(Change.timestamp.desc()).limit(20).all()
    return jsonify([
        {
            "id": c.id,
            "form_name": c.form.name if c.form else "N/A",
            "agency_name": c.form.agency.name if c.form and c.form.agency else "N/A",
            "timestamp": c.timestamp.isoformat(),
            "severity": c.severity,
            "change_details": c.change_details
        }
        for c in changes
    ])

if __name__ == '__main__':
    # This block is for direct running of the Flask app for development
    # In production, it will be run via main.py or a WSGI server
    print("Running Flask app directly for development...")
    # Ensure database is initialized if running directly
    init_db() 
    app.run(debug=True, port=8000)