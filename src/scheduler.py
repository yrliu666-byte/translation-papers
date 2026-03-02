"""
Scheduler module
Weekly task to search and send papers
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

# Import modules
from src.paper_finder import search_translation_studies_papers
from src.database import (
    init_db, save_paper, get_unsent_papers,
    mark_papers_as_sent, log_email
)
from src.email_sender import send_email

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def collect_and_send_weekly():
    """
    Main weekly task:
    1. Search for new papers
    2. Save to database
    3. Get unsent papers
    4. Send email
    5. Mark as sent
    """
    logger.info("=" * 50)
    logger.info("Starting weekly paper collection...")
    start_time = datetime.now()

    try:
        # Step 1: Search for papers
        logger.info("Searching for papers...")
        papers = search_translation_studies_papers()
        logger.info(f"Found {len(papers)} papers")

        # Step 2: Save papers to database
        saved_papers = []
        for paper in papers:
            try:
                saved = save_paper(paper)
                if saved:
                    saved_papers.append(saved)
            except Exception as e:
                logger.error(f"Error saving paper: {e}")

        logger.info(f"Saved {len(saved_papers)} new papers to database")

        # Step 3: Get unsent papers
        unsent_papers = get_unsent_papers()
        logger.info(f"Found {len(unsent_papers)} unsent papers")

        # Step 4: Send email
        if unsent_papers:
            success = send_email(unsent_papers)

            if success:
                # Step 5: Mark papers as sent
                mark_papers_as_sent(unsent_papers)
                log_email(len(unsent_papers), 'success')
                logger.info(f"Email sent successfully with {len(unsent_papers)} papers")
            else:
                log_email(len(unsent_papers), 'failed', 'Email sending failed')
                logger.error("Failed to send email")
        else:
            # Even if no papers, send an empty notification
            logger.info("No new papers to send")
            send_email([])  # Send empty notification
            log_email(0, 'success', 'No new papers found')

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Weekly task completed in {duration:.2f} seconds")

    except Exception as e:
        logger.error(f"Error in weekly task: {e}")
        log_email(0, 'error', str(e))


def run_scheduler():
    """Run the scheduler"""
    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Create scheduler
    scheduler = BlockingScheduler()

    # Add job: Every Monday at 9:00 AM
    scheduler.add_job(
        collect_and_send_weekly,
        CronTrigger(day_of_week='mon', hour=9, minute=0),
        id='weekly_paper_collection',
        name='Weekly paper collection',
        replace_existing=True
    )

    logger.info("Scheduler started. Task will run every Monday at 9:00 AM")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
        scheduler.shutdown()


if __name__ == '__main__':
    # For testing: run immediately
    print("Testing the weekly task...")
    collect_and_send_weekly()
