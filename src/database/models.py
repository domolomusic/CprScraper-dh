from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Agency(Base):
    __tablename__ = 'agencies'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    abbreviation = Column(String)
    base_url = Column(String)
    prevailing_wage_url = Column(String)
    phone = Column(String)
    email = Column(String)
    forms = relationship("Form", back_populates="agency")

    def to_dict(self, include_forms=False):
        data = {
            'id': self.id,
            'name': self.name,
            'abbreviation': self.abbreviation,
            'base_url': self.base_url,
            'prevailing_wage_url': self.prevailing_wage_url,
            'phone': self.phone,
            'email': self.email
        }
        if include_forms and self.forms:
            data['forms'] = [form.to_dict() for form in self.forms]
        return data

class Form(Base):
    __tablename__ = 'forms'
    id = Column(Integer, primary_key=True)
    agency_id = Column(Integer, ForeignKey('agencies.id'))
    name = Column(String, nullable=False)
    title = Column(String)
    url = Column(String, nullable=False)
    form_url = Column(String) # Direct link to PDF or specific form page
    instructions_url = Column(String)
    check_frequency = Column(String) # e.g., 'daily', 'weekly', 'monthly'
    contact_email = Column(String)
    last_hash = Column(String) # Hash of the last scraped content
    last_scraped_at = Column(DateTime)
    agency = relationship("Agency", back_populates="forms")
    changes = relationship("Change", back_populates="form")

    def to_dict(self, include_agency=False, include_changes=False):
        data = {
            'id': self.id,
            'agency_id': self.agency_id,
            'name': self.name,
            'title': self.title,
            'url': self.url,
            'form_url': self.form_url,
            'instructions_url': self.instructions_url,
            'check_frequency': self.check_frequency,
            'contact_email': self.contact_email,
            'last_hash': self.last_hash,
            'last_scraped_at': self.last_scraped_at.isoformat() if self.last_scraped_at else None
        }
        if include_agency and self.agency:
            data['agency'] = self.agency.to_dict()
        if include_changes and self.changes:
            data['changes'] = [change.to_dict() for change in self.changes]
        return data

class Change(Base):
    __tablename__ = 'changes'
    id = Column(Integer, primary_key=True)
    form_id = Column(Integer, ForeignKey('forms.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    change_details = Column(Text)
    severity = Column(String) # e.g., 'low', 'medium', 'high', 'critical'
    is_reviewed = Column(Boolean, default=False)
    form = relationship("Form", back_populates="changes")

    def to_dict(self, include_form=False):
        data = {
            'id': self.id,
            'form_id': self.form_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'change_details': self.change_details,
            'severity': self.severity,
            'is_reviewed': self.is_reviewed
        }
        if include_form and self.form:
            data['form'] = self.form.to_dict()
        return data