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

class Change(Base):
    __tablename__ = 'changes'
    id = Column(Integer, primary_key=True)
    form_id = Column(Integer, ForeignKey('forms.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    change_details = Column(Text)
    severity = Column(String) # e.g., 'low', 'medium', 'high', 'critical'
    is_reviewed = Column(Boolean, default=False)
    form = relationship("Form", back_populates="changes")