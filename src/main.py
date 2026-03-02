"""
Main application entry point
Flask web app with scheduler
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import threading
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import modules
from src.database import init_db, get_all_papers, get_email_logs, log_email
from src.paper_finder import search_translation_studies_papers
from src.email_sender import send_email
from src.database import save_paper, get_unsent_papers, mark_papers_as_sent
from src.database import add_subscriber, remove_subscriber, get_all_subscribers
from src.scheduler import collect_and_send_weekly

# Create Flask app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize database
init_db()


# Start scheduler in background
def start_scheduler_thread():
    """Start the scheduler in a separate thread"""
    import scheduler as sched_module
    thread = threading.Thread(target=sched_module.run_scheduler, daemon=True)
    thread.start()
    print("Scheduler thread started")


# Routes
@app.route('/')
def index():
    """Home page"""
    papers = get_all_papers(limit=20)
    logs = get_email_logs(limit=10)
    subscribers = get_all_subscribers()
    return render_template('index.html', papers=papers, logs=logs, subscribers=subscribers)


@app.route('/api/papers')
def api_papers():
    """API: Get all papers"""
    papers = get_all_papers(limit=50)
    return jsonify([p.to_dict() for p in papers])


@app.route('/api/logs')
def api_logs():
    """API: Get email logs"""
    logs = get_email_logs(limit=20)
    return jsonify([log.to_dict() for log in logs])


@app.route('/api/search', methods=['POST'])
def api_search():
    """API: Manual search trigger"""
    try:
        papers = search_translation_studies_papers()
        saved_count = 0

        for paper in papers:
            saved = save_paper(paper)
            if saved:
                saved_count += 1

        return jsonify({
            'success': True,
            'message': f'Found {len(papers)} papers, saved {saved_count} new'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/send', methods=['POST'])
def api_send():
    """API: Manual send trigger"""
    try:
        unsent_papers = get_unsent_papers()

        if not unsent_papers:
            return jsonify({
                'success': True,
                'message': 'No new papers to send'
            })

        success = send_email(unsent_papers)

        if success:
            mark_papers_as_sent(unsent_papers)
            log_email(len(unsent_papers), 'success', 'Manual trigger')

        return jsonify({
            'success': success,
            'message': f'Sent {len(unsent_papers)} papers'
        })
    except Exception as e:
        log_email(0, 'error', str(e))
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'})


@app.route('/api/subscribe', methods=['POST'])
def api_subscribe():
    """API: Add subscriber"""
    data = request.get_json()
    email = data.get('email', '').strip()

    if not email or '@' not in email:
        return jsonify({
            'success': False,
            'message': 'Invalid email address'
        }), 400

    try:
        add_subscriber(email)
        return jsonify({
            'success': True,
            'message': f'Subscribed {email} successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/unsubscribe', methods=['POST'])
def api_unsubscribe():
    """API: Remove subscriber"""
    data = request.get_json()
    email = data.get('email', '').strip()

    try:
        remove_subscriber(email)
        return jsonify({
            'success': True,
            'message': f'Unsubscribed {email}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/subscribers')
def api_subscribers():
    """API: Get all subscribers"""
    subscribers = get_all_subscribers()
    return jsonify([s.to_dict() for s in subscribers])


def create_app():
    """Create and configure the Flask app"""
    return app


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))

    # Start scheduler in background (comment out for testing)
    # start_scheduler_thread()

    # Run Flask app
    app.run(host='0.0.0.0', port=port, debug=True)
