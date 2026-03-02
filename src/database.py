"""
Database operations module
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base, Paper, EmailLog, Subscriber

# Database URL - use SQLite for local/ Railway
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///papers.db')

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(engine)


def get_session():
    """Get a database session"""
    return Session()


def save_paper(paper_data):
    """Save a paper to the database"""
    session = get_session()
    try:
        # Check if paper already exists
        existing = session.query(Paper).filter(
            Paper.title == paper_data['title']
        ).first()

        if existing:
            return existing

        paper = Paper(
            title=paper_data['title'],
            authors=paper_data.get('authors', ''),
            journal=paper_data.get('journal', ''),
            publish_date=paper_data.get('publish_date', ''),
            abstract=paper_data.get('abstract', ''),
            url=paper_data.get('url', ''),
            source=paper_data.get('source', ''),
        )
        session.add(paper)
        session.commit()
        return paper
    finally:
        session.close()


def get_unsent_papers():
    """Get papers that haven't been sent yet, sorted from oldest to newest"""
    session = get_session()
    try:
        papers = session.query(Paper).filter(
            Paper.sent_at == None
        ).order_by(Paper.publish_date.asc()).all()  # Sort from oldest to newest
        return papers
    finally:
        session.close()


def mark_papers_as_sent(papers):
    """Mark papers as sent"""
    session = get_session()
    try:
        for paper in papers:
            p = session.query(Paper).filter(Paper.id == paper.id).first()
            if p:
                p.sent_at = datetime.utcnow()
        session.commit()
    finally:
        session.close()


def get_all_papers(limit=50):
    """Get all papers, most recent first"""
    session = get_session()
    try:
        papers = session.query(Paper).order_by(
            Paper.created_at.desc()
        ).limit(limit).all()
        return papers
    finally:
        session.close()


def log_email(paper_count, status, error_message=None):
    """Log email sending activity"""
    session = get_session()
    try:
        log = EmailLog(
            paper_count=paper_count,
            status=status,
            error_message=error_message
        )
        session.add(log)
        session.commit()
        return log
    finally:
        session.close()


def get_email_logs(limit=20):
    """Get recent email logs"""
    session = get_session()
    try:
        logs = session.query(EmailLog).order_by(
            EmailLog.sent_at.desc()
        ).limit(limit).all()
        return logs
    finally:
        session.close()


def add_subscriber(email):
    """Add a new subscriber"""
    session = get_session()
    try:
        # Check if already exists
        existing = session.query(Subscriber).filter(
            Subscriber.email == email
        ).first()

        if existing:
            if existing.is_active:
                return existing  # Already subscribed
            else:
                # Reactivate
                existing.is_active = 1
                session.commit()
                return existing

        subscriber = Subscriber(email=email)
        session.add(subscriber)
        session.commit()
        return subscriber
    finally:
        session.close()


def remove_subscriber(email):
    """Remove a subscriber"""
    session = get_session()
    try:
        subscriber = session.query(Subscriber).filter(
            Subscriber.email == email
        ).first()
        if subscriber:
            subscriber.is_active = 0
            session.commit()
        return True
    finally:
        session.close()


def get_subscribers():
    """Get all active subscribers"""
    session = get_session()
    try:
        subscribers = session.query(Subscriber).filter(
            Subscriber.is_active == 1
        ).all()
        return subscribers
    finally:
        session.close()


def get_all_subscribers():
    """Get all subscribers (including inactive)"""
    session = get_session()
    try:
        subscribers = session.query(Subscriber).order_by(
            Subscriber.created_at.desc()
        ).all()
        return subscribers
    finally:
        session.close()
