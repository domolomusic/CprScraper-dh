from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class Agency(Base):
    __tablename__ = 'agencies'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    abbreviation = Column(String, unique=True, nullable=True)
    base_url = Column(String, nullable=False)
    prevailing_wage_url = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)

    forms = relationship("Form", back_populates="agency")

    def __repr__(self):
        return f"<Agency(name='{self.name}', abbreviation='{self.abbreviation}')>"

class Form(Base):
    __tablename__ = 'forms'
    id = Column(Integer, primary_key=True)
    agency_id = Column(Integer, ForeignKey('agencies.id'), nullable=False)
    name = Column(String, nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    form_url = Column(String, nullable=True)
    instructions_url = Column(String, nullable=True)
    check_frequency = Column(String, default="weekly")
    contact_email = Column(String, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    last_scraped_content = Column(Text, nullable=True) # Store the content for comparison
    last_scraped_at = Column(DateTime, nullable=True)

    agency = relationship("Agency", back_populates="forms")
    changes = relationship("Change", back_populates="form", order_by="Change.timestamp.desc()")

    def __repr__(self):
        return f"<Form(name='{self.name}', title='{self.title}', agency='{self.agency.name if self.agency else 'N/A'}')>"

class Change(Base):
    __tablename__ = 'changes'
    id = Column(Integer, primary_key=True)
    form_id = Column(Integer, ForeignKey('forms.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    old_content_hash = Column(String, nullable=True)
    new_content_hash = Column(String, nullable=True)
    change_details = Column(Text, nullable=True) # JSON string or simple message
    severity = Column(String, default="medium") # e.g., low, medium, high, critical
    is_reviewed = Column(Boolean, default=False)

    form = relationship("Form", back_populates="changes")

    def __repr__(self):
        return f"<Change(form='{self.form.name if self.form else 'N/A'}', timestamp='{self.timestamp}', severity='{self.severity}')>"