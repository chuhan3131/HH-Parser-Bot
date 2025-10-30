import json
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
import mysql.connector
import datetime
from datetime import timezone, timedelta

def get_time():
    """Получаем текущее время"""
    tz = timezone(timedelta(hours=3))
    return datetime.datetime.now(tz)

def collect_statistics(db_conn):
    """Сбор ежедневной статистики"""
    if db_conn is None:
        print("БД не подключена - статистика недоступна")
        return None
        
    cursor = db_conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*) as total_today 
            FROM sent_vacancies 
            WHERE DATE(sent_date) = CURDATE()
        """)
        total_today = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) as total_yesterday 
            FROM sent_vacancies 
            WHERE DATE(sent_date) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
        """)
        total_yesterday = cursor.fetchone()[0]

        cursor.execute("""
            SELECT company, COUNT(*) as count 
            FROM sent_vacancies 
            WHERE DATE(sent_date) = CURDATE()
            GROUP BY company 
            ORDER BY count DESC 
            LIMIT 5
        """)
        top_companies = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM sent_vacancies")
        total_all = cursor.fetchone()[0]
        
        return {
            'total_today': total_today,
            'total_yesterday': total_yesterday,
            'top_companies': top_companies,
            'total_all': total_all,
            'date': get_time().strftime('%d.%m.%Y')
        }
    except Exception as e:
        print(f"Ошибка сбора статистики: {e}")
        return None
    finally:
        cursor.close()

def format_statistics_message(stats):
    """Форматирование сообщения со статистикой"""
    if not stats:
        return "❌ Не удалось собрать статистику"
    
    message = f"📊 <b>Статистика за {stats['date']}</b>\n\n"

    diff = stats['total_today'] - stats['total_yesterday']
    if diff > 0:
        trend = f"📈 +{diff}"
    elif diff < 0:
        trend = f"📉 {diff}"
    else:
        trend = "➡️ 0"
    
    message += f"<b>Сегодня найдено:</b> {stats['total_today']} вакансий {trend}\n"
    message += f"<b>Всего в базе:</b> {stats['total_all']} вакансий\n\n"

    if stats['top_companies']:
        message += "<b>🏢 Топ компаний сегодня:</b>\n"
        for i, (company, count) in enumerate(stats['top_companies'], 1):
            message += f"{i}. {company}: {count} вакансий\n"
    else:
        message += "<i>Сегодня вакансий не найдено</i>\n"
    
    message += f"\n⏰ Отчет сгенерирован: {get_time().strftime('%H:%M')}"
    
    return message

def send_statistics(db_conn, bot_token, chat_id):
    """Отправка ежедневной статистики"""
    try:
        stats = collect_statistics(db_conn)
        if stats is None:
            return False
            
        message = format_statistics_message(stats)
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        print(f"Ежедневная статистика отправлена в {get_time().strftime('%H:%M')}")
        return True
        
    except Exception as e:
        print(f"Ошибка отправки статистики: {e}")
        return False

def html_from_urlfetch_(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Ошибка загрузки HTML: {e}")
        return None

def parse_vacancies_html(html_content):
    if html_content is None:
        return []
        
    soup = BeautifulSoup(html_content, 'html.parser')
    vacancies = []

    vacancy_blocks = soup.select('[data-qa="vacancy-serp__vacancy"]')
    
    print(f"Найдено блоков вакансий: {len(vacancy_blocks)}")

    for block in vacancy_blocks:
        try:
            #название вакансии
            title_tag = block.select_one('[data-qa="serp-item__title"]')
            if not title_tag:
                continue
                
            title = title_tag.get_text(strip=True)
            
            #ссылка
            href = title_tag.get('href', '')
            if href and 'hh.ru' not in href:
                href = 'https://hh.ru' + href.split('?')[0]

            #компания
            company_tag = block.select_one('[data-qa="vacancy-serp__vacancy-employer"]')
            company = company_tag.get_text(strip=True) if company_tag else ""

            #поиск зарплаты
            salary = ""
            salary_tags = block.select('.magritte-text_typography-label-1-regular___pi3R-_4-2-3')
            for tag in salary_tags:
                text = tag.get_text(strip=True)
                if 'Br' in text or 'руб' in text.lower():
                    salary = text
                    break

            #адрес
            address_tag = block.select_one('[data-qa="vacancy-serp__vacancy-address"]')
            address = address_tag.get_text(strip=True) if address_tag else ""

            #опыт
            experience = ""
            exp_tag = block.select_one('[data-qa*="vacancy-work-experience"]')
            if exp_tag:
                experience = exp_tag.get_text(strip=True)

            vacancy_data = {
                'title': title,
                'href': href,
                'company': company,
                'salary': salary,
                'address': address,
                'experience': experience,
                'description': "" 
            }

            vacancies.append(vacancy_data)
            print(f"{title} - {company}")

        except Exception as e:
            print(f"Ошибка парсинга вакансии: {e}")
            continue

    return vacancies

def parse_vacancies_from_url(url):
    html = html_from_urlfetch_(url)
    if html:
        return parse_vacancies_html(html)
    return []

def similarity_check(search_text, vacancy_data, threshold=70):
    """Проверяет схожесть вакансии с поисковым запросом"""
    title = vacancy_data.get('title', '')
    company = vacancy_data.get('company', '')
    description = vacancy_data.get('description', '')

    title_score = fuzz.partial_ratio(search_text.lower(), title.lower())
    company_score = fuzz.partial_ratio(search_text.lower(), company.lower())
    desc_score = fuzz.partial_ratio(search_text.lower(), description.lower())
    
    max_score = max(title_score, company_score, desc_score)

    is_similar = max_score >= threshold
    return is_similar, max_score

def format_vacancy_message(vacancy):
    message = f"<b>{vacancy['title']}</b>\n"
    message += f"🏢 <b>Компания:</b> {vacancy['company']}\n"
    
    if vacancy.get('salary'):
        message += f"💰 <b>Зарплата:</b> {vacancy['salary']}\n"
    
    if vacancy.get('address'):
        message += f"📍 <b>Адрес:</b> {vacancy['address']}\n"
    
    if vacancy.get('experience'):
        message += f"📊 <b>Опыт:</b> {vacancy['experience']}\n"
    
    message += f"🔗 <a href='{vacancy['href']}'>Ссылка на вакансию</a>"
    
    return message

def send_telegram_message(bot_token, chat_id, vacancy):
    try:
        message = format_vacancy_message(vacancy)
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': False
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        print(f"Сообщение отправлено в Telegram: {vacancy['title']}")
        return True
        
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")
        return False

def connect_db():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='chuhan',
            password='pass',
            database='headhunter_db'
        )
        print("Успешное подключение к БД")
        return conn
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        return None

def create_table_if_not_exists(db_conn):
    if db_conn is None:
        print("Нет подключения к БД")
        return
        
    cursor = db_conn.cursor()
    create_table_query = """
    CREATE TABLE IF NOT EXISTS sent_vacancies (
        id INT AUTO_INCREMENT PRIMARY KEY,
        url VARCHAR(500) UNIQUE NOT NULL,
        title VARCHAR(500),
        company VARCHAR(255),
        sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    try:
        cursor.execute(create_table_query)
        db_conn.commit()
        print("Таблица sent_vacancies создана или уже существует")
    except Exception as e:
        print(f"Ошибка создания таблицы: {e}")
    finally:
        cursor.close()

def is_vacancy_sent(db_conn, url):
    if db_conn is None:
        return False
        
    cursor = db_conn.cursor()
    try:
        cursor.execute("SELECT id FROM sent_vacancies WHERE url = %s", (url,))
        result = cursor.fetchone()
        return result is not None
    except Exception as e:
        print(f"Ошибка проверки вакансии в БД: {e}")
        return False
    finally:
        cursor.close()

def mark_vacancy_sent(db_conn, url, title="", company=""):
    if db_conn is None:
        return
        
    cursor = db_conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO sent_vacancies (url, title, company) VALUES (%s, %s, %s)", 
            (url, title, company)
        )
        db_conn.commit()
        print(f"Вакансия добавлена в БД: {title}")
    except mysql.connector.errors.IntegrityError:
        pass 
    except Exception as e:
        print(f"Ошибка добавления в БД: {e}")
    finally:
        cursor.close()