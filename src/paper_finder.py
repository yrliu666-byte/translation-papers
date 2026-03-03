"""
Paper Finder Module
Search for Chinese Translation Studies papers from various sources
"""

import os
import re
import json
import requests
import feedparser
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# Search period: 30 days for more results (for demo/testing)
# In production, this should be 7 days
SEARCH_DAYS = 30


def is_valid_date(publish_date_str):
    """
    Validate that the date is within the last 7 days
    Returns True if valid, False otherwise
    """
    if not publish_date_str:
        return False

    try:
        # Parse the date
        date_parts = publish_date_str.split('-')
        if len(date_parts) < 1:
            return False

        year = int(date_parts[0])

        # Check if year is reasonable (between 1900 and current year)
        current_year = datetime.now().year
        if year < 1900 or year > current_year:
            return False

        # If we have month and day, check if within last 7 days
        if len(date_parts) >= 3:
            month = int(date_parts[1])
            day = int(date_parts[2])
            pub_date = datetime(year, month, day)
            now = datetime.now()
            # Reject future dates
            if pub_date > now:
                return False
            cutoff = now - timedelta(days=30)
            return pub_date >= cutoff
        elif len(date_parts) >= 2:
            # If only year and month, check if within last 7 days of the month
            month = int(date_parts[1])
            if year == current_year and month == datetime.now().month:
                return True
            # For older dates, check if within the last 7 days
            pub_date = datetime(year, month, 1)
            cutoff = datetime.now() - timedelta(days=30)
            return pub_date >= cutoff

        # If only year, check if it's the current year
        return year == current_year

    except (ValueError, IndexError):
        return False


# Search keywords for Chinese Translation Studies (Chinese Translation History)
# 中国翻译史研究范围：文学翻译、宗教翻译、法律翻译、知识翻译、外交翻译等
SEARCH_KEYWORDS = [
    # English keywords
    'Chinese translation history',
    'translation history China',
    'Chinese translator history',
    'Chinese literary translation history',
    'Chinese religious translation',
    'Chinese legal translation',
    'translation China 19th century',
    'translation China 20th century',
    'late Qing translation',
    'Ming Qing translation',
    'Republican era translation',
    'Hong Kong translation studies',
    'Taiwan translation studies',
    # Chinese keywords - 翻译史
    '中国翻译史',
    '翻译史 研究',
    '近代翻译史',
    '清代翻译史',
    '民国翻译史',
    # 各类翻译历史
    '中国文学翻译史',
    '中国宗教翻译史',
    '中国法律翻译史',
    '中国知识翻译',
    '中国外交翻译',
    '中国佛经翻译',
    '中国西学翻译',
    '中国科技翻译史',
    # 香港台湾
    '香港翻译史',
    '台湾翻译研究',
    '翻译学报',
    '编译论丛',
]

# Exclude medical/biological/computational terms
EXCLUDE_TERMS = [
    'protein', 'gene', 'DNA', 'RNA', 'cell', 'medical', 'medicine',
    'clinical', 'drug', 'therapy', 'treatment', 'diagnosis',
    'genetic', 'molecular', 'biology', 'biochemistry', 'pharmacology',
    'cancer', 'tumor', 'disease', 'patient', 'clinical trial',
    'messenger RNA', 'mRNA', 'translation initiation',
    'neural', 'convolutional', 'deep learning', 'machine learning',
    'artificial intelligence', 'AI model', 'BERT', 'GPT',
    'biologically', 'neuro', 'brain',
]

# Translation Studies Journals to focus on
TRANSLATION_JOURNALS = [
    'Target',
    'The Translator',
    'Translation Studies',
    'Meta',
    'Interpreting and Translation Studies',
    'Translation Literature',
    'Perspectives',
    'Babel',
    'Across Languages and Cultures',
    'Translator',
    'TTR',
    'RIEL',
]

# Journal RSS feeds - Updated with working URLs
# 包含港台及国际翻译学期刊
JOURNAL_RSS = {
    # 国际期刊
    'Target': 'https://benjamins.com/catalog/target.rss',
    'The Translator': 'https://www.tandfonline.com/doi/cmtrss/a',
    'Translation Studies': 'https://www.tandfonline.com/ji/trst',
    'Meta': 'https://www.erudit.org/en/journals/meta/rss/meta.xml',
    'Translation Literature': 'https://www.tandfonline.com/ji/tl',
    'Perspectives': 'https://www.tandfonline.com/ji/perspectives',
    'Babel': 'https://www.erudit.org/en/journals/babel/rss/babel.xml',
    'Interpreter and Translator Trainer': 'https://www.tandfonline.com/ji/ittt',
    'Across Languages and Cultures': 'https://www.erudit.org/en/journals/alc/',
    # 香港期刊
    'Translate Today': 'https://www.hkts.org.hk/rss',
    # 台湾期刊 - 通常需要手动搜索，暂无公开RSS
    # '编译论丛': '',
    # 中国大陆期刊
    '中国翻译': 'http://www.ccti.org.cn/rss',
}

# Chinese Translation Studies journals (for reference, may need manual search)
# 中国翻译史相关中文期刊:
# - 《中国翻译》
# - 《翻译学报》
# - 《外语与外语教学》
# - 《外国语》
# - 《北京外国语大学学报》
# - 《复旦外国语言文学论丛》


def is_relevant_paper(title, abstract, journal=''):
    """Check if paper is relevant to Chinese Translation History (中国翻译史)"""
    text = (title + ' ' + (abstract or '') + ' ' + (journal or '')).lower()
    title_lower = title.lower()

    # Exclude medical/biological papers
    for term in EXCLUDE_TERMS:
        if term.lower() in text:
            return False

    # Exclude modern translation market/industry/training papers
    exclude_terms = [
        'translation market', 'translation industry', 'translation service',
        'translation company', 'localization industry', 'translation business',
        'translator training', 'translation pedagogy', 'interpreter training',
        'MTI', 'translation teaching', 'curriculum', '教学', '课程',
        'machine translation', 'neural machine translation', 'NMT',
        'subtitling', 'dubbing', 'audiovisual', 'film translation',
        'localization', 'software localization', 'game localization',
        'quality assessment', 'translation quality', 'translation evaluation',
        'news interpretation', 'court interpretation', 'conference interpretation',
    ]
    for term in exclude_terms:
        if term in text:
            return False

    # Check if it's a Chinese language paper
    has_chinese_chars = any('\u4e00' <= c <= '\u9fff' for c in title + (journal or ''))

    # 必须有中国/历史相关术语
    china_terms = [
        'china', 'chinese', 'sinitic', 'sinology', 'sinological',
        'hong kong', 'taiwan', 'taipei',
        '中国', '中文', '近代', '清代', '民国', '古代', '香港', '台湾', '台北',
        'qing dynasty', 'ming dynasty', 'late qing', 'republican',
        'late imperial', 'pre-modern', 'colonial', 'imperial china'
    ]
    has_china_related = any(term in text for term in china_terms)

    # 必须有翻译相关术语
    translation_terms = [
        'translation', 'translator', 'translator', 'interpreting',
        'rendering', 'interpretation', 'translating', 'rendition',
        '翻译', '译本', '译者', '口译', '译介', '译学'
    ]
    has_translation = any(term in text for term in translation_terms)

    # 必须有历史/文化/宗教/知识相关的翻译类型
    historical_types = [
        'history', 'historical', 'literary', 'literature', 'novel',
        'religious', 'religion', 'buddhist', 'bible', 'christian',
        'confucian', 'taoist', 'islamic',
        'western learning', 'science', 'knowledge',
        'diplomatic', 'diplomacy', 'treaty',
        'philosophy', 'classics', 'poetry', 'poem',
        'buddhist scripture', 'sutras', 'canon',
        '文学', '宗教', '佛经', '圣经', '西学', '知识', '外交',
        '哲学', '经典', '诗歌', '古籍', '典籍'
    ]
    has_historical_type = any(term in text for term in historical_types)

    # 逻辑：
    # 1. 必须有翻译
    # 2. 必须有中国/历史关联
    # 3. 必须是历史/文化/宗教类翻译（不是现代应用翻译）

    if not (has_translation and has_china_related):
        return False

    return has_historical_type


def search_google_scholar(keywords=None, days=SEARCH_DAYS):
    """
    Search CrossRef for Chinese Translation Studies papers
    """
    papers = []
    keywords = keywords or SEARCH_KEYWORDS

    # Use CrossRef API as a more reliable alternative
    for keyword in keywords:
        try:
            # Search CrossRef for recent papers (past 7 days only)
            from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            query = keyword.replace('"', '')
            url = f"https://api.crossref.org/works"
            params = {
                'query': query,
                'filter': f'from-pub-date:{from_date}',
                'rows': 30,
                'select': 'title,author,container-title,published,URL,abstract'
            }

            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('message', {}).get('items', []):
                    title = item.get('title', [''])[0] if item.get('title') else ''
                    abstract = item.get('abstract', '')
                    journal = item.get('container-title', [''])[0] if item.get('container-title') else ''

                    # Filter: exclude medical, must be China-related translation
                    if not is_relevant_paper(title, abstract, journal):
                        continue

                    # Convert authors list to string
                    authors_list = [a.get('family', '') for a in item.get('author', [])]
                    authors_str = ', '.join(authors_list)

                    # Convert publish_date to string (zero-padded for proper sorting)
                    date_parts = item.get('published', {}).get('date-parts', [[None]])[0]
                    if date_parts and len(date_parts) >= 2:
                        year = date_parts[0]
                        month = date_parts[1] if len(date_parts) > 1 else 1
                        day = date_parts[2] if len(date_parts) > 2 else 1
                        publish_date_str = f"{year}-{month:02d}-{day:02d}" if year else ''
                    else:
                        publish_date_str = ''

                    # Skip papers with invalid dates or dates outside the search range
                    if not is_valid_date(publish_date_str):
                        continue

                    paper = {
                        'title': title,
                        'authors': authors_str,
                        'journal': journal,
                        'publish_date': publish_date_str,
                        'url': item.get('URL', ''),
                        'abstract': abstract,
                        'source': 'CrossRef'
                    }
                    papers.append(paper)
        except Exception as e:
            print(f"Error searching CrossRef for '{keyword}': {e}")

    return papers


def get_journal_rss_papers():
    """Fetch papers from journal RSS feeds"""
    papers = []
    # Use 7 days for journal RSS
    cutoff_date = datetime.now() - timedelta(days=30)

    for journal_name, rss_url in JOURNAL_RSS.items():
        try:
            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:10]:  # Get recent 10 entries
                # Parse publication date
                pub_date = None
                if hasattr(entry, 'published'):
                    try:
                        pub_date = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                elif hasattr(entry, 'updated'):
                    try:
                        pub_date = datetime(*entry.updated_parsed[:6])
                    except:
                        pass

                # Skip if too old
                if pub_date and pub_date < cutoff_date:
                    continue

                paper = {
                    'title': entry.get('title', ''),
                    'authors': [],
                    'journal': journal_name,
                    'publish_date': pub_date.strftime('%Y-%m-%d') if pub_date else '',
                    'url': entry.get('link', ''),
                    'abstract': entry.get('summary', '')[:500],
                    'source': f'RSS:{journal_name}'
                }
                papers.append(paper)

        except Exception as e:
            print(f"Error fetching RSS from {journal_name}: {e}")

    return papers


# Chinese Translation Studies Journals (Taiwan/Hong Kong)
# 翻译学报: https://journal.ncl.edu.tw/tts
# 编译论丛: https://ctr.nccu.edu.tw/
CHINESE_JOURNAL_KEYWORDS = [
    '翻译学报',
    '编译论丛',
]


def search_chinese_journals():
    """
    Search for papers from Taiwanese/Hong Kong translation journals
    搜索台湾和香港的翻译学期刊
    """
    papers = []

    # Search CrossRef for Chinese translation journals
    journal_names = ['翻译学报', '编译论丛']

    for journal_name in journal_names:
        try:
            # Search CrossRef for the journal name
            url = "https://api.crossref.org/works"
            params = {
                'query': journal_name,
                'filter': f'from-pub-date:{(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")}',
                'rows': 20,
                'select': 'title,author,container-title,published,URL,abstract'
            }

            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('message', {}).get('items', []):
                    title = item.get('title', [''])[0] if item.get('title') else ''
                    abstract = item.get('abstract', '')
                    journal = item.get('container-title', [''])[0] if item.get('container-title') else ''

                    # Check if the journal name is in the result
                    if journal_name not in journal and journal_name not in title:
                        continue

                    # Check if it's relevant to Chinese translation history
                    if not is_relevant_paper(title, abstract, journal):
                        continue

                    # Convert authors list to string
                    authors_list = [a.get('family', '') for a in item.get('author', [])]
                    authors_str = ', '.join(authors_list)

                    # Convert publish_date to string (zero-padded for proper sorting)
                    date_parts = item.get('published', {}).get('date-parts', [[None]])[0]
                    if date_parts and len(date_parts) >= 2:
                        year = date_parts[0]
                        month = date_parts[1] if len(date_parts) > 1 else 1
                        day = date_parts[2] if len(date_parts) > 2 else 1
                        publish_date_str = f"{year}-{month:02d}-{day:02d}" if year else ''
                    else:
                        publish_date_str = ''

                    # Skip papers with invalid dates or dates outside the search range
                    if not is_valid_date(publish_date_str):
                        continue

                    paper = {
                        'title': title,
                        'authors': authors_str,
                        'journal': journal,
                        'publish_date': publish_date_str,
                        'url': item.get('URL', ''),
                        'abstract': abstract,
                        'source': f'ChineseJournal:{journal_name}'
                    }
                    papers.append(paper)
        except Exception as e:
            print(f"Error searching Chinese journal '{journal_name}': {e}")

    return papers


def search_translation_studies_papers():
    """
    Search for Chinese Translation Studies papers
    Uses multiple strategies:
    1. CrossRef API for English papers
    2. Journal RSS feeds
    3. Taiwanese/Hong Kong Chinese translation journals
    Returns papers sorted from oldest to newest
    """
    all_papers = []

    # Method 1: Search with specific Chinese translation history keywords (English)
    all_papers.extend(search_google_scholar())

    # Method 2: Journal RSS feeds (Target, The Translator, etc.)
    all_papers.extend(get_journal_rss_papers())

    # Method 3: Additional targeted search (English)
    additional_keywords = [
        'China translation history',
        'Chinese translator literature',
        'translation Chinese culture',
        'Chinese interpreting social',
    ]
    all_papers.extend(search_google_scholar(keywords=additional_keywords))

    # Method 4: Search Chinese journals (翻译学报, 编译论丛)
    all_papers.extend(search_chinese_journals())

    # Deduplicate by title
    seen_titles = set()
    unique_papers = []
    for paper in all_papers:
        title_normalized = paper['title'].lower().strip()
        if title_normalized and title_normalized not in seen_titles:
            # Final filter check
            if is_relevant_paper(paper['title'], paper.get('abstract', ''), paper.get('journal', '')):
                seen_titles.add(title_normalized)
                unique_papers.append(paper)

    # Sort papers from oldest to newest (publish_date ascending)
    # Papers without date will be placed at the end
    unique_papers.sort(key=lambda p: p.get('publish_date', '9999-99-99'))

    return unique_papers


def format_paper_for_email(paper):
    """Format a paper for email display"""
    title = paper.get('title', 'No title')
    authors = ', '.join(paper.get('authors', ['Unknown']))
    journal = paper.get('journal', 'Unknown journal')
    publish_date = paper.get('publish_date', 'Unknown date')
    url = paper.get('url', '')
    abstract = paper.get('abstract', '')[:300] if paper.get('abstract') else 'No abstract available'

    return f"""
【标题】{title}
【作者】{authors}
【期刊】{journal}
【日期】{publish_date}
【摘要】{abstract}...
【链接】{url}
"""


if __name__ == '__main__':
    # Test the module
    print("Testing paper finder...")
    papers = search_translation_studies_papers()
    print(f"Found {len(papers)} papers")
    for p in papers[:3]:
        print(f"- {p.get('title', 'No title')[:50]}...")
