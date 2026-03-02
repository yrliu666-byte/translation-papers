"""
Email sender module
Send paper notifications via email
Supports both SMTP and Resend API
"""

import os
import asyncio
import requests
from dotenv import load_dotenv

load_dotenv()

# Email configuration
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.cuhk.edu.hk')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', 'yunrouliu@cuhk.edu.hk')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
EMAIL_FROM = os.getenv('EMAIL_FROM', 'yunrouliu@cuhk.edu.hk')
EMAIL_TO = os.getenv('EMAIL_TO', 'yrliu666@gmail.com,ruoze.huang@xmu.edu.cn')

# Resend API configuration (alternative to SMTP)
RESEND_API_KEY = os.getenv('RESEND_API_KEY', '')

# Default recipients from config
DEFAULT_RECIPIENTS = os.getenv('EMAIL_TO', 'yrliu666@gmail.com,ruoze.huang@xmu.edu.cn')


def get_all_recipients():
    """Get all recipients: default + subscribers"""
    from src.database import get_subscribers

    # Get default recipients
    recipients = [e.strip() for e in DEFAULT_RECIPIENTS.split(',') if e.strip()]

    # Add subscribers from database
    try:
        subscribers = get_subscribers()
        for sub in subscribers:
            if sub.email not in recipients:
                recipients.append(sub.email)
    except:
        pass

    return recipients


def format_email_content(papers):
    """Format papers into email content"""
    if not papers:
        return """<html>
<body>
<h2>本周翻译史论文简报</h2>
<p>本周没有发现新的相关论文。</p>
<p>此邮件由系统自动发送。</p>
</body>
</html>"""

    content_lines = []
    for i, paper in enumerate(papers, 1):
        title = paper.get('title', 'No title')
        authors = paper.get('authors', 'Unknown')
        if isinstance(authors, list):
            authors = ', '.join(authors)
        journal = paper.get('journal', 'Unknown journal')
        publish_date = paper.get('publish_date', 'Unknown')
        url = paper.get('url', '#')
        abstract = paper.get('abstract', 'No abstract available')
        if isinstance(abstract, str):
            # Remove HTML tags from abstract
            import re
            abstract = re.sub(r'<[^>]+>', '', abstract)
            abstract = abstract[:300] + '...' if len(abstract) > 300 else abstract

        content_lines.append(f"""
<div style="margin-bottom: 20px; padding: 15px; border-left: 3px solid #4CAF50; background-color: #f9f9f9;">
<h3 style="margin-top: 0;">{i}. {title}</h3>
<p><strong>作者：</strong>{authors}</p>
<p><strong>期刊：</strong>{journal} | <strong>日期：</strong>{publish_date}</p>
<p><strong>摘要：</strong>{abstract}</p>
<p><a href="{url}" style="color: #2196F3;">查看原文</a></p>
</div>
""")

    html_content = f"""<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 中国翻译史研究论文简报</h1>
        <p>本期共收集到 <strong>{len(papers)}</strong> 篇相关论文：</p>

        {''.join(content_lines)}

        <div class="footer">
            <p>此邮件由系统自动发送。每周一定期推送。</p>
            <p>如需调整订阅，请联系管理员。</p>
        </div>
    </div>
</body>
</html>"""

    return html_content


async def send_via_resend(subject, html_content):
    """Send email via Resend API"""
    if not RESEND_API_KEY:
        print("RESEND_API_KEY not set")
        return False

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "from": "中国翻译史论文 <onboarding@resend.dev>",
        "to": [EMAIL_TO],
        "subject": subject,
        "html": html_content
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        if response.status_code == 200:
            print(f"Email sent successfully via Resend to {EMAIL_TO}")
            return True
        else:
            print(f"Resend API error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error sending via Resend: {e}")
        return False


async def send_email_async(subject, html_content):
    """Send email - tries Resend first, then falls back to SMTP"""

    # Try Resend API first
    if RESEND_API_KEY:
        success = await send_via_resend(subject, html_content)
        if success:
            return True

    # Fall back to SMTP if Resend not configured
    if not SMTP_PASSWORD:
        print("No email method configured (neither RESEND_API_KEY nor SMTP_PASSWORD)")
        return False

    # SMTP sending (simplified without aiosmtplib for now)
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # Get all recipients (default + subscribers)
    recipients = get_all_recipients()

    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['From'] = EMAIL_FROM
    message['To'] = ', '.join(recipients)

    html_part = MIMEText(html_content, 'html', 'utf-8')
    message.attach(html_part)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            # Send to each recipient individually
            for recipient in recipients:
                msg_copy = MIMEMultipart('alternative')
                msg_copy['Subject'] = subject
                msg_copy['From'] = EMAIL_FROM
                msg_copy['To'] = recipient
                msg_copy.attach(MIMEText(html_content, 'html', 'utf-8'))
                server.send_message(msg_copy)
        print(f"Email sent successfully via SMTP to {recipients}")
        return True
    except Exception as e:
        print(f"Error sending email via SMTP: {e}")
        return False


def send_email(papers):
    """Send email with paper list"""
    subject = f"【第{get_week_number()}期】中国翻译史研究论文简报"

    # If papers is a list of Paper objects, convert to dicts
    if papers and hasattr(papers[0], 'to_dict'):
        papers = [p.to_dict() for p in papers]

    html_content = format_email_content(papers)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(send_email_async(subject, html_content))


def get_week_number():
    """Get current week number of the year"""
    from datetime import datetime
    now = datetime.now()
    return now.isocalendar()[1]
