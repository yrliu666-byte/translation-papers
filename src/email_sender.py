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
    # Resend free tier only allows sending to the registered email
    # Once domain is verified, change this back to get_all_recipients()
    recipients = ['yrliu666@gmail.com']

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "from": "论文管理系统 <onboarding@resend.dev>",
        "to": recipients,
        "subject": subject,
        "html": html_content
    }

    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        if response.status_code == 200:
            print(f"Email sent via Resend to {recipients}")
            return True
        else:
            raise RuntimeError(f"Resend API 错误 {response.status_code}：{response.text}")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Resend 请求失败：{e}")


async def send_email_async(subject, html_content):
    """Send email - uses Resend if configured, otherwise SMTP"""

    # Use Resend if API key is set
    if RESEND_API_KEY:
        await send_via_resend(subject, html_content)
        return True

    # Fall back to SMTP only if Resend not configured
    if not SMTP_PASSWORD:
        raise RuntimeError(
            "未配置邮件发送方式：请在 Railway 中设置 RESEND_API_KEY 或 SMTP_PASSWORD"
        )

    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    recipients = get_all_recipients()
    if not recipients:
        raise RuntimeError("没有收件人，请先添加订阅者")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            for recipient in recipients:
                msg_copy = MIMEMultipart('alternative')
                msg_copy['Subject'] = subject
                msg_copy['From'] = f'论文管理系统 <{EMAIL_FROM}>'
                msg_copy['To'] = recipient
                msg_copy.attach(MIMEText(html_content, 'html', 'utf-8'))
                server.send_message(msg_copy)
        print(f"Email sent successfully via SMTP to {recipients}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        raise RuntimeError(f"SMTP 认证失败，请检查用户名和密码：{e}")
    except smtplib.SMTPConnectError as e:
        raise RuntimeError(f"无法连接到 SMTP 服务器 {SMTP_HOST}:{SMTP_PORT}：{e}")
    except Exception as e:
        raise RuntimeError(f"SMTP 发送失败：{e}")


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
