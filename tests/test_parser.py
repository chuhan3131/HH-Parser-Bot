import pytest
import sys
import os
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from parser import (
    parse_vacancies_html, 
    similarity_check, 
    format_vacancy_message,
    send_telegram_message,
    connect_db,
    is_vacancy_sent,
    mark_vacancy_sent
)

class TestParser:
    
    def test_parse_vacancies_html_valid(self):
        html_content = """
        <div data-qa="vacancy-serp__vacancy">
            <a data-qa="serp-item__title" href="/vacancy/123">Python Developer</a>
            <div data-qa="vacancy-serp__vacancy-employer">Test Company</div>
            <div data-qa="vacancy-serp__vacancy-address">Москва</div>
        </div>
        """
        
        vacancies = parse_vacancies_html(html_content)
        
        assert len(vacancies) == 1
        assert vacancies[0]['title'] == 'Python Developer'
        assert vacancies[0]['company'] == 'Test Company'
        assert vacancies[0]['address'] == 'Москва'
        assert 'hh.ru/vacancy/123' in vacancies[0]['href']
    
    def test_parse_vacancies_html_empty(self):
        vacancies = parse_vacancies_html("<html></html>")
        assert vacancies == []
    
    def test_parse_vacancies_html_none(self):
        vacancies = parse_vacancies_html(None)
        assert vacancies == []
    
    def test_similarity_check_high_similarity(self):
        vacancy_data = {"title": "Senior Python Developer", "company": "", "description": ""}
        is_similar, score = similarity_check("Python Developer", vacancy_data, 70)
        assert is_similar == True
        assert score >= 70
    
    def test_similarity_check_low_similarity(self):
        vacancy_data = {"title": "Бухгалтер", "company": "", "description": ""}
        is_similar, score = similarity_check("Python Developer", vacancy_data, 70)
        assert is_similar == False
        assert score < 70
    
    def test_similarity_check_very_low_threshold(self):
        vacancy_data = {"title": "Java Developer", "company": "", "description": ""}
        is_similar, score = similarity_check("Python Developer", vacancy_data, 10)
        assert is_similar == True
    
    def test_similarity_check_exact_match(self):
        vacancy_data = {"title": "Python Developer", "company": "", "description": ""}
        is_similar, score = similarity_check("Python Developer", vacancy_data, 70)
        assert is_similar == True
        assert score >= 95
    
    def test_similarity_check_company_match(self):
        vacancy_data = {"title": "Разработчик", "company": "Python Solutions", "description": ""}
        is_similar, score = similarity_check("Python", vacancy_data, 70)
        assert is_similar == True
    
    def test_format_vacancy_message_complete(self):
        vacancy = {
            'title': 'Python Developer',
            'company': 'Test Corp',
            'salary': '100 000 ₽',
            'address': 'Москва',
            'experience': '1-3 года',
            'href': 'https://hh.ru/vacancy/123'
        }
        
        message = format_vacancy_message(vacancy)
        
        assert '<b>Python Developer</b>' in message
        assert '🏢 <b>Компания:</b> Test Corp' in message
        assert '💰 <b>Зарплата:</b> 100 000 ₽' in message
    
    def test_format_vacancy_message_minimal(self):
        vacancy = {
            'title': 'Developer',
            'company': 'Company',
            'href': 'https://hh.ru/vacancy/123'
        }
        
        message = format_vacancy_message(vacancy)
        assert '<b>Developer</b>' in message
        assert '🏢 <b>Компания:</b> Company' in message
    
    @patch('parser.requests.post')
    def test_send_telegram_message_success(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        vacancy = {
            'title': 'Test',
            'company': 'Test Co',
            'href': 'https://test.com'
        }
        
        success = send_telegram_message('token', 'chat123', vacancy)
        
        assert success == True
        mock_post.assert_called_once()
    
    @patch('parser.requests.post')
    def test_send_telegram_message_failure(self, mock_post):
        mock_post.side_effect = Exception("Network error")
        
        vacancy = {'title': 'Test', 'company': 'Test', 'href': 'https://test.com'}
        success = send_telegram_message('token', 'chat123', vacancy)
        
        assert success == False
    
    @patch('parser.mysql.connector.connect')
    def test_connect_db_success(self, mock_connect):
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        conn = connect_db()
        
        assert conn == mock_conn
        mock_connect.assert_called_once()
    
    @patch('parser.mysql.connector.connect')
    def test_connect_db_failure(self, mock_connect):
        mock_connect.side_effect = Exception("DB error")
        
        conn = connect_db()
        
        assert conn is None
    
    def test_is_vacancy_sent_with_connection(self):
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [1]
        
        result = is_vacancy_sent(mock_conn, 'https://test.com/vacancy/123')
        
        assert result == True
    
    def test_is_vacancy_sent_no_connection(self):
        result = is_vacancy_sent(None, 'https://test.com/vacancy/123')
        assert result == False
    
    def test_is_vacancy_sent_not_found(self):
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        result = is_vacancy_sent(mock_conn, 'https://test.com/vacancy/999')
        
        assert result == False