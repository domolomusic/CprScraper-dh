from flask import Flask, render_template, jsonify, request, abort
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, desc
from src.database.models import Base, Agency, Form, Change
from src.database.connection import SessionLocal
import os

app = Flask(__name__, template_folder='../../templates', static_folder='../../static')

# API Routes
@app.route('/api/stats')
def get_stats():
    session = SessionLocal()
    total_agencies = session.query(Agency).count()
    total_forms = session.query(Form).count()
    recent_changes = session.query(Change).order_by(desc(Change.timestamp)).limit(10).all()
    session.close()
    return jsonify({
        'total_agencies': total_agencies,
        'total_forms': total_forms,
        'recent_changes_count': len(recent_changes)
    })

@app.route('/api/agencies')
def get_agencies():
    session = SessionLocal()
    agencies = session.query(Agency).all()
    session.close()
    return jsonify([agency.to_dict() for agency in agencies])

@app.route('/api/agency/<int:agency_id>/forms')
def get_agency_forms(agency_id):
    session = SessionLocal()
    forms = session.query(Form).filter_by(agency_id=agency_id).all()
    session.close()
    return jsonify([form.to_dict() for form in forms])

@app.route('/api/changes')
def get_changes():
    session = SessionLocal()
    changes = session.query(Change).order_by(desc(Change.timestamp)).all()
    session.close()
    return jsonify([change.to_dict() for change in changes])

# Web Dashboard Routes
@app.route('/')
def index():
    session = SessionLocal()
    total_agencies = session.query(Agency).count()
    total_forms = session.query(Form).count()
    recent_changes = session.query(Change).order_by(desc(Change.timestamp)).limit(10).all()
    session.close()
    return render_template('index.html', 
                           total_agencies=total_agencies, 
                           total_forms=total_forms, 
                           recent_changes=recent_changes)

@app.route('/agencies')
def agencies_page():
    session = SessionLocal()
    agencies = session.query(Agency).all()
    session.close()
    return render_template('agencies.html', agencies=agencies)

@app.route('/agency/<int:agency_id>')
def agency_detail_page(agency_id):
    session = SessionLocal()
    agency = session.query(Agency).filter_by(id=agency_id).first()
    if not agency:
        abort(404)
    forms = session.query(Form).filter_by(agency_id=agency_id).all()
    session.close()
    return render_template('agency_detail.html', agency=agency, forms=forms)

@app.route('/form/<int:form_id>')
def form_detail_page(form_id):
    session = SessionLocal()
    form = session.query(Form).filter_by(id=form_id).first()
    if not form:
        abort(404)
    changes = session.query(Change).filter_by(form_id=form_id).order_by(desc(Change.timestamp)).all()
    session.close()
    return render_template('form_detail.html', form=form, changes=changes)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('PORT', 8000))