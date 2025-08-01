from flask import Flask, render_template, jsonify, request, abort
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import joinedload
from src.database.models import Base, Agency, Form, Change
from src.database.connection import db_session
import os
from datetime import datetime

app = Flask(__name__, template_folder='../../templates', static_folder='../../static')

# API Routes
@app.route('/api/stats')
def get_stats():
    with db_session() as session:
        total_agencies = session.query(Agency).count()
        total_forms = session.query(Form).count()
        recent_changes = session.query(Change).options(joinedload(Change.form)).order_by(desc(Change.timestamp)).limit(10).all()
    return jsonify({
        'total_agencies': total_agencies,
        'total_forms': total_forms,
        'recent_changes_count': len(recent_changes)
    })

@app.route('/api/agencies')
def get_agencies():
    with db_session() as session:
        agencies = session.query(Agency).all()
    return jsonify([agency.to_dict() for agency in agencies])

@app.route('/api/agency/<int:agency_id>/forms')
def get_agency_forms(agency_id):
    with db_session() as session:
        forms = session.query(Form).filter_by(agency_id=agency_id).all()
    return jsonify([form.to_dict() for form in forms])

@app.route('/api/changes')
def get_changes():
    with db_session() as session:
        changes = session.query(Change).options(joinedload(Change.form)).order_by(desc(Change.timestamp)).all()
    return jsonify([change.to_dict() for change in changes])

# Web Dashboard Routes
@app.route('/')
def index():
    with db_session() as session:
        total_agencies = session.query(Agency).count()
        total_forms = session.query(Form).count()
        
        # Subquery to get the latest change_id for each *agency*
        latest_change_per_agency_subquery = session.query(
            Agency.id.label('agency_id'),
            func.max(Change.timestamp).label('max_timestamp')
        ).join(Form, Agency.id == Form.agency_id).join(Change, Form.id == Change.form_id).group_by(Agency.id).subquery()

        # Query to get the Change objects corresponding to the latest timestamps per agency, eagerly loading form and agency
        recent_changes_query = session.query(Change).\
            join(Form, Change.form_id == Form.id).\
            join(Agency, Form.agency_id == Agency.id).\
            join(latest_change_per_agency_subquery,
                 (Agency.id == latest_change_per_agency_subquery.c.agency_id) & 
                 (Change.timestamp == latest_change_per_agency_subquery.c.max_timestamp)).\
            options(joinedload(Change.form).joinedload(Form.agency)).\
            order_by(desc(Change.timestamp)).\
            all()

        recent_changes = []
        for change in recent_changes_query:
            change_dict = change.to_dict()
            if change.form:
                form_dict = change.form.to_dict()
                if form_dict['last_scraped_at']:
                    form_dict['last_scraped_at'] = datetime.fromisoformat(form_dict['last_scraped_at']).strftime('%Y-%m-%d %H:%M:%S')
                if change.form.agency:
                    form_dict['agency'] = change.form.agency.to_dict()
                change_dict['form'] = form_dict
            recent_changes.append(change_dict)

    return render_template('index.html', 
                           total_agencies=total_agencies, 
                           total_forms=total_forms, 
                           recent_changes=recent_changes)

@app.route('/agencies')
def agencies_page():
    with db_session() as session:
        agencies = session.query(Agency).all()
        agencies_data = [agency.to_dict(include_forms=False) for agency in agencies] # include_forms=False to prevent too much data on overview
    return render_template('agencies.html', agencies=agencies_data)

@app.route('/agency/<int:agency_id>')
def agency_detail_page(agency_id):
    with db_session() as session:
        agency = session.query(Agency).filter_by(id=agency_id).first()
        if not agency:
            abort(404)
        # Eagerly load forms for the agency
        forms = session.query(Form).filter_by(agency_id=agency_id).options(joinedload(Form.changes)).all()
        agency_data = agency.to_dict() # Don't include forms here, pass separately
        forms_data = [form.to_dict(include_changes=True) for form in forms]
    return render_template('agency_detail.html', agency=agency_data, forms=forms_data)

@app.route('/form/<int:form_id>')
def form_detail_page(form_id):
    with db_session() as session:
        form = session.query(Form).filter_by(id=form_id).options(joinedload(Form.agency)).first()
        if not form:
            abort(404)
        changes = session.query(Change).filter_by(form_id=form_id).order_by(desc(Change.timestamp)).all()
        form_data = form.to_dict(include_agency=True) # Eagerly load agency
        changes_data = [change.to_dict(include_form=True) for change in changes] # Include form data for each change
    return render_template('form_detail.html', form=form_data, changes=changes_data)

if __name__ == '__main__':
    from src.database.connection import init_db
    init_db()
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 8000))