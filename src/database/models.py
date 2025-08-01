from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class Agency(Base):
    __tablename__ = 'agencies'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    abbreviation = Column(String)
    base_url = Column(String)
    prevailing_wage_url = Column(String) # Specific to state agencies
    phone = Column(String)
    email = Column(String)
    type = Column(String) # 'federal' or 'state'

    forms = relationship("Form", back_populates="agency")

    def __repr__(self):
        return f"<Agency(id={self.id}, name='{self.name}')>"

class Form(Base):
    __tablename__ = 'forms'
    id = Column(Integer, primary_key=True)
    agency_id = Column(Integer, ForeignKey('agencies.id'), nullable=False)
    name = Column(String, nullable=False)
    title = Column(String)
    url = Column(String, nullable=False)
    form_url = Column(String) # Direct link to the form PDF/document
    instructions_url = Column(String) # Link to instructions
    check_frequency = Column(String) # e.g., 'daily', 'weekly', 'monthly'
    contact_email = Column(String)
    last_updated = Column(DateTime) # Last updated date from the agency's site, if available
    last_scraped_at = Column(DateTime) # When we last scraped this form

    agency = relationship("Agency", back_populates="forms")
    changes = relationship("Change", back_populates="form")

    def __repr__(self):
        return f"<Form(id={self.id}, name='{self.name}', agency_id={self.agency_id})>"

class Change(Base):
    __tablename__ = 'changes'
    id = Column(Integer, primary_key=True)
    form_id = Column(Integer, ForeignKey('forms.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    change_details = Column(Text, nullable=False)
    severity = Column(String, default='medium') # e.g., 'low', 'medium', 'high', 'critical'
    is_reviewed = Column(Boolean, default=False)

    form = relationship("Form", back_populates="changes")

    def __repr__(self):
        return f"<Change(id={self.id}, form_id={self.form_id}, timestamp='{self.timestamp}')>"

class MonitoringRun(Base):
    __tablename__ = 'monitoring_runs'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String, nullable=False) # e.g., 'success', 'failure', 'partial_success'
    details = Column(Text) # Summary of the run, e.g., "5 forms checked, 2 changes detected"
    duration_seconds = Column(Integer)
    forms_checked = Column(Integer)
    changes_detected = Column(Integer)

    def __repr__(self):
        return f"<MonitoringRun(id={self.id}, timestamp='{self.timestamp}', status='{self.status}')>"