import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

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
    forms = relationship("Form", back_populates="agency", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Agency(name='{self.name}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'abbreviation': self.abbreviation,
            'base_url': self.base_url,
            'prevailing_wage_url': self.prevailing_wage_url,
            'phone': self.phone,
            'email': self.email
        }

class Form(Base):
    __tablename__ = 'forms'
    id = Column(Integer, primary_key=True)
    agency_id = Column(Integer, ForeignKey('agencies.id'))
    name = Column(String, nullable=False)
    title = Column(String)
    url = Column(String, nullable=False)
    form_url = Column(String) # Direct link to the form PDF/document
    instructions_url = Column(String) # Link to instructions
    check_frequency = Column(String) # e.g., daily, weekly, monthly
    contact_email = Column(String)
    last_scraped_at = Column(DateTime)
    last_hash = Column(String) # Hash of the content for change detection
    
    agency = relationship("Agency", back_populates="forms")
    changes = relationship("Change", back_populates="form", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Form(name='{self.name}', agency='{self.agency.name if self.agency else 'N/A'}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'agency_id': self.agency_id,
            'name': self.name,
            'title': self.title,
            'url': self.url,
            'form_url': self.form_url,
            'instructions_url': self.instructions_url,
            'check_frequency': self.check_frequency,
            'contact_email': self.contact_email,
            'last_scraped_at': self.last_scraped_at.isoformat() if self.last_scraped_at else None,
            'last_hash': self.last_hash
        }

class Change(Base):
    __tablename__ = 'changes'
    id = Column(Integer, primary_key=True)
    form_id = Column(Integer, ForeignKey('forms.id'))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    change_details = Column(Text)
    severity = Column(String) # e.g., low, medium, high, critical
    is_reviewed = Column(Boolean, default=False)
    
    form = relationship("Form", back_populates="changes")

    def __repr__(self):
        return f"<Change(form='{self.form.name if self.form else 'N/A'}', timestamp='{self.timestamp}')>"

    def to_dict(self):
        return {
            'id': self.id,
            'form_id': self.form_id,
            'timestamp': self.timestamp.isoformat(),
            'change_details': self.change_details,
            'severity': self.severity,
            'is_reviewed': self.is_reviewed,
            'form_name': self.form.name if self.form else None,
            'agency_name': self.form.agency.name if self.form and self.form.agency else None
        }