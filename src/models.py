"""
Database models for storing papers
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Paper(Base):
    __tablename__ = 'papers'

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    authors = Column(String(500))
    journal = Column(String(200))
    publish_date = Column(String(50))
    abstract = Column(Text)
    url = Column(String(500))
    source = Column(String(50))
    sent_at = Column(DateTime, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'authors': self.authors,
            'journal': self.journal,
            'publish_date': self.publish_date,
            'abstract': self.abstract,
            'url': self.url,
            'source': self.source,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Paper(id={self.id}, title='{self.title[:30]}...')>"


class EmailLog(Base):
    __tablename__ = 'email_logs'

    id = Column(Integer, primary_key=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    paper_count = Column(Integer)
    status = Column(String(50))
    error_message = Column(Text)

    def to_dict(self):
        return {
            'id': self.id,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'paper_count': self.paper_count,
            'status': self.status,
            'error_message': self.error_message,
        }


class Subscriber(Base):
    __tablename__ = 'subscribers'

    id = Column(Integer, primary_key=True)
    email = Column(String(200), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Integer, default=1)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
        }
